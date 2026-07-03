import logging
import asyncio
from typing import List, Any
from langchain_core.messages import BaseMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from app.core.config import settings
from app.core.resilience import CircuitBreaker, AsyncRateLimiter

logger = logging.getLogger(__name__)


class LLMProvider:
    def __init__(self):
        self.primary_model = "gemini-2.5-flash"
        self.fallback_model = "llama-3.1-8b-instant"
        self.cerebras_model = "gpt-oss-120b"
        self.breakers = {
            "gemini": CircuitBreaker(failure_threshold=5, recovery_seconds=30),
            "groq": CircuitBreaker(failure_threshold=5, recovery_seconds=30),
            "cerebras": CircuitBreaker(failure_threshold=5, recovery_seconds=30),
        }
        self.rate_limiter = AsyncRateLimiter(max_calls=40, window_seconds=60)
        self.call_count = 0
        self.provider_stats = {
            "gemini": {"calls": 0, "successes": 0, "failures": 0},
            "groq": {"calls": 0, "successes": 0, "failures": 0},
            "cerebras": {"calls": 0, "successes": 0, "failures": 0},
        }

        self.llm = ChatGoogleGenerativeAI(
            model=self.primary_model,
            google_api_key=settings.GEMINI_API_KEY,
            temperature=0.7,
            max_retries=0,
            timeout=20.0,
        ) if settings.GEMINI_API_KEY else None

        self.llm_cerebras = ChatOpenAI(
            base_url="https://api.cerebras.ai/v1",
            api_key=settings.CEREBRAS_API_KEY,
            model=self.cerebras_model,
            temperature=0.7,
            max_retries=0,
            timeout=15.0,
        ) if settings.CEREBRAS_API_KEY else None

        self.llm_groq = ChatOpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=settings.GROQ_API_KEY,
            model=self.fallback_model,
            temperature=0.7,
            max_retries=0,
            timeout=15.0,
        ) if settings.GROQ_API_KEY else None

    async def generate(self, messages: List[BaseMessage], **kwargs) -> Any:
        """
        Error recovery chain:
          1. Try Gemini
          2. Try Cerebras (Free, 120B model)
          3. Try Groq
          4. If all fail → raise exception
        """
        max_rounds = 2
        last_error = None

        for round_num in range(max_rounds):
            # --- Try Gemini ---
            if self.llm and not self.breakers["gemini"].is_open:
                try:
                    self.provider_stats["gemini"]["calls"] += 1
                    await self.rate_limiter.acquire()
                    response = await asyncio.wait_for(
                        self.llm.ainvoke(messages, **kwargs), timeout=25.0
                    )
                    response._provider = "gemini"
                    response._model = self.primary_model
                    self.breakers["gemini"].record_success()
                    self.provider_stats["gemini"]["successes"] += 1
                    self.call_count += 1
                    return response
                except Exception as e:
                    self.breakers["gemini"].record_failure()
                    self.provider_stats["gemini"]["failures"] += 1
                    last_error = e
                    logger.warning(
                        f"Gemini failed (round {round_num + 1}): {str(e)[:200]}"
                    )

            # --- Try Cerebras ---
            if self.llm_cerebras and not self.breakers["cerebras"].is_open:
                try:
                    self.provider_stats["cerebras"]["calls"] += 1
                    await self.rate_limiter.acquire()
                    response = await asyncio.wait_for(
                        self.llm_cerebras.ainvoke(messages, **kwargs), timeout=20.0
                    )
                    response._provider = "cerebras"
                    response._model = self.cerebras_model
                    self.breakers["cerebras"].record_success()
                    self.provider_stats["cerebras"]["successes"] += 1
                    self.call_count += 1
                    return response
                except Exception as e:
                    self.breakers["cerebras"].record_failure()
                    self.provider_stats["cerebras"]["failures"] += 1
                    last_error = e
                    logger.warning(
                        f"Cerebras failed (round {round_num + 1}): {str(e)[:200]}"
                    )

            # --- Try Groq ---
            if self.llm_groq and not self.breakers["groq"].is_open:
                try:
                    self.provider_stats["groq"]["calls"] += 1
                    await self.rate_limiter.acquire()
                    response = await asyncio.wait_for(
                        self.llm_groq.ainvoke(messages, **kwargs), timeout=20.0
                    )
                    response._provider = "groq"
                    response._model = self.fallback_model
                    self.breakers["groq"].record_success()
                    self.provider_stats["groq"]["successes"] += 1
                    self.call_count += 1
                    return response
                except Exception as e:
                    self.breakers["groq"].record_failure()
                    self.provider_stats["groq"]["failures"] += 1
                    last_error = e
                    logger.warning(
                        f"Groq failed (round {round_num + 1}): {str(e)[:200]}"
                    )

            # If both failed this round, sleep before retrying
            if round_num < max_rounds - 1:
                wait = 15
                logger.info(f"All providers exhausted this round. Sleeping {wait}s before retry...")
                await asyncio.sleep(wait)

        # NO fake fallback. Raise so the node reports "failed" status.
        error_msg = f"All LLM providers exhausted after {max_rounds} rounds. Last error: {last_error}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    def health(self) -> dict:
        return {
            "gemini": {
                "configured": self.llm is not None,
                "available": not self.breakers["gemini"].is_open,
                "stats": self.provider_stats["gemini"],
            },
            "cerebras": {
                "configured": self.llm_cerebras is not None,
                "available": not self.breakers["cerebras"].is_open,
                "stats": self.provider_stats["cerebras"],
            },
            "groq": {
                "configured": self.llm_groq is not None,
                "available": not self.breakers["groq"].is_open,
                "stats": self.provider_stats["groq"],
            },
        }
