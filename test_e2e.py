import urllib.request
import json
import sys

url = "http://localhost:8000/api/v1/campaign/start"
data = json.dumps({
    "our_url": "https://app.notion.com/",
    "campaign_id": "e2e-demo-1"
}).encode("utf-8")
headers = {"Content-Type": "application/json"}

print("Starting E2E Campaign Validation against secondorigin.vercel.app...")
req = urllib.request.Request(url, data=data, headers=headers, method="POST")

try:
    with urllib.request.urlopen(req) as response:
        for line in response:
            decoded_line = line.decode("utf-8").strip()
            if decoded_line:
                print(decoded_line)
                sys.stdout.flush()
    print("E2E Campaign Completed Successfully.")
except Exception as e:
    print(f"Error executing campaign: {e}")
