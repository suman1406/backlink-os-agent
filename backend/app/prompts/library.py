from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate

class PromptLibrary:
    WEBSITE_ANALYZER = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(
            "You are an expert SEO and business intelligence analyst. Return only valid JSON with keys: "
            "company_name, industry, audience, value_props, products, evidence, confidence. "
            "value_props/products/evidence are arrays. confidence is 0.0 to 1.0. Do not use markdown."
        ),
        HumanMessagePromptTemplate.from_template("Website Content: {content}\n\nExtract the business profile.")
    ])
    
    BUSINESS_INTELLIGENCE = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template("You are a business intelligence agent. Based on the website analysis, infer the company's business model, revenue streams, and potential partnership angles."),
        HumanMessagePromptTemplate.from_template("Website Analysis: {analysis}\n\nProvide business intelligence insights.")
    ])

    KEYWORD_EXTRACTION = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(
            "You are an SEO keyword researcher. Return only valid JSON with key keywords. "
            "keywords is an array of 5-10 objects with term, intent, relevance_score, and confidence. "
            "Scores are 0.0 to 1.0. Do not use markdown."
        ),
        HumanMessagePromptTemplate.from_template("Business Intelligence JSON: {bi_insights}\n\nExtract backlink outreach keywords.")
    ])

    SEARCH_STRATEGY = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template("You are a search strategist. Generate specific Google search queries using advanced operators to find backlink opportunities (e.g., guest posts, resource pages) based on the keywords."),
        HumanMessagePromptTemplate.from_template("Keywords: {keywords}\n\nGenerate search queries.")
    ])

    OPPORTUNITY_QUALIFICATION = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(
            "You are a backlink qualification expert. Return only valid JSON with keys: "
            "qualified, fit_score, confidence, reasons, risks, suggested_angle. "
            "qualified is boolean. fit_score is 1-10. reasons and risks are arrays. Do not use markdown."
        ),
        HumanMessagePromptTemplate.from_template("Target Website Content: {content}\nOur Business JSON: {our_business}\n\nQualify this opportunity.")
    ])

    PERSONALIZATION = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template("You are a relationship builder. Analyze the target website and our business to find unique personalization angles for outreach. Look for shared interests, recent news, or specific content to praise."),
        HumanMessagePromptTemplate.from_template("Target Content: {target_content}\nOur Business: {our_business}\n\nGenerate personalization angles.")
    ])

    OUTREACH_GENERATOR = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(
            "You are an expert outreach copywriter. Return only valid JSON with keys: "
            "subject, body, personalization_angle, call_to_action, confidence. "
            "Keep body concise, specific, and plain text. Do not use markdown."
        ),
        HumanMessagePromptTemplate.from_template("Target Info: {target_info}\nPersonalization: {personalization}\nOur Business JSON: {our_business}\n\nDraft the email.")
    ])

    REPLY_CLASSIFICATION = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template("You are an email assistant. Classify the reply from a backlink prospect into one of the following categories: POSITIVE, NEGATIVE, NOT_INTERESTED, REQUESTS_MORE_INFO, OUT_OF_OFFICE."),
        HumanMessagePromptTemplate.from_template("Reply Email: {email_content}\n\nClassify the reply.")
    ])
