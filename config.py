import os
from dotenv import load_dotenv
load_dotenv()

TELEGRAM_TOKEN   = os.environ["TELEGRAM_TOKEN"]
OPENAI_API_KEY   = os.environ["OPENAI_API_KEY"]
STAFF_CHAT_ID    = os.environ.get("STAFF_CHAT_ID", "")
WEBHOOK_URL      = os.environ.get("WEBHOOK_URL", "")   # e.g. https://yourapp.zeabur.app/webhook

# Google credentials — paste the full service-account JSON as one env var
GOOGLE_CREDS_JSON = os.environ["GOOGLE_CREDS_JSON"]

COURSE_SHEET_ID = "1GoGgabYrSXHTBuwHswklV1EeZnxccxXWNHhjLefdbDY"
DB_SHEET_ID     = "1sgvZdK-rWxdsRYki6PRgKDuXALujntsMRHZjBTLaK8k"

COURSE_TABS = [
    "BUSINESS", "DESIGN", "EDUCATION", "ENGINEERING",
    "FINANCE", "HOSPITALITY", "IT", "LAW",
    "MEDIA", "MEDICAL", "PSYCHOLOGY", "GENERAL",
]
