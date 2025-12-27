from astropost.client import GmailClient
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "astropost"
TOKEN_PATH = CONFIG_DIR / "token.json"
CREDENTIALS_PATH = CONFIG_DIR / "credentials.json"

client = GmailClient(str(TOKEN_PATH), str(CREDENTIALS_PATH))

# Find the test emails
subjects = [
    "Project Update",
    "Invoice #12345",
    "Weekend Plans",
    "Server Alert",
    "Lunch?",
    "Newsletter: AI Trends",
]

print("Marking test emails as UNREAD...")
for sub in subjects:
    # Use q parameter to find exact subject matches sent today
    query = f'subject:"{sub}" is:read'  # Only find read ones to toggle
    emails = client.list_emails(max_results=1, query=query)

    if emails:
        email = emails[0]
        print(f"Found: {email.subject} ({email.id}). Marking UNREAD.")
        client.modify_labels(email.id, add_labels=["UNREAD"])
    else:
        print(f"Could not find read email with subject: {sub}")
