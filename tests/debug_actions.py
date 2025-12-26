from astropost.client import GmailClient, SCOPES
from pathlib import Path
import time

# Setup paths
CONFIG_DIR = Path.home() / ".config" / "astropost"
TOKEN_PATH = CONFIG_DIR / "token.json"
CREDENTIALS_PATH = CONFIG_DIR / "credentials.json"


def test_actions():
    print(f"Scopes defined in code: {SCOPES}")
    client = GmailClient(str(TOKEN_PATH), str(CREDENTIALS_PATH))

    # 1. Send Test Email
    print("Sending test email...")
    subject = f"AstroPost Action Test {int(time.time())}"
    try:
        msg_id = client.send_email(
            recipients=["forsythc@ucr.edu"],  # Sending to self
            subject=subject,
            body="Testing archive and delete actions.",
        )
        print(f"Sent email ID: {msg_id}")
    except Exception as e:
        print(f"Failed to send: {e}")
        return

    # Wait for propagation
    time.sleep(5)

    # 2. Check details (should be in SENT, but also INBOX if to self? Maybe not immediately.)
    # Let's list messages to find it in Inbox.
    # Actually, sending to self usually lands in Inbox.
    print("Checking if email is in Inbox...")
    found = False
    for i in range(5):
        emails = client.list_emails(max_results=20)
        for email in emails:
            if email["id"] == msg_id:
                print("Found email in list.")
                found = True
                break
        if found:
            break
        time.sleep(2)

    if not found:
        print(
            "Email not found in Inbox (might be slow or filtered). skipping archive test on this specific msg."
        )
        # Try to find ANY email to test on? No, unsafe.
        return

    # 3. Test Archive (Remove INBOX)
    print("Testing Archive (Remove INBOX)...")
    success = client.modify_labels(msg_id, remove_labels=["INBOX"])
    if success:
        print("Archive call returned True.")
    else:
        print("Archive call returned False.")

    # 4. Test Unread (Add UNREAD)
    print("Testing Mark Unread...")
    success = client.modify_labels(msg_id, add_labels=["UNREAD"])
    if success:
        print("Unread call returned True.")
    else:
        print("Unread call returned False.")

    # 5. Test Trash
    print("Testing Trash...")
    success = client.trash_email(msg_id)
    if success:
        print("Trash call returned True.")
    else:
        print("Trash call returned False.")


if __name__ == "__main__":
    test_actions()
