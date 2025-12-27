from astropost.client import GmailClient
from pathlib import Path
import time

CONFIG_DIR = Path.home() / ".config" / "astropost"
TOKEN_PATH = CONFIG_DIR / "token.json"
CREDENTIALS_PATH = CONFIG_DIR / "credentials.json"
RECIPIENT = "chuck.forsyth@gmail.com"
SENDER = "AstroPost Test <forsythc@ucr.edu>"

client = GmailClient(str(TOKEN_PATH), str(CREDENTIALS_PATH))

emails = [
    (
        "Project Update",
        "Meeting postponed to Tuesday. Please review the attached slides.",
    ),
    ("Invoice #12345", "Your subscription has been renewed. Total: $49.99."),
    ("Weekend Plans", "Are we still on for hiking this Saturday? Weather looks good."),
    ("Server Alert", "CPU usage high on web-01. Please investigate immediately."),
    ("Lunch?", "Tacos at 12:30? Let me know."),
    (
        "Newsletter: AI Trends",
        "Top story: New Gemini model released. Python 3.14 features announced.",
    ),
]

print("Sending 6 test emails...")
for sub, body in emails:
    try:
        client.send_email([RECIPIENT], sub, body, from_address=SENDER)
        print(f"Sent: {sub}")
        time.sleep(1)  # Prevent rate limiting
    except Exception as e:
        print(f"Failed to send {sub}: {e}")
