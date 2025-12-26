import time
import sys
from pathlib import Path
from astropost.client import GmailClient

# Setup paths
CONFIG_DIR = Path.home() / ".config" / "astropost"
TOKEN_PATH = CONFIG_DIR / "token.json"
CREDENTIALS_PATH = CONFIG_DIR / "credentials.json"

TEST_EMAIL = "chuck.forsyth@gmail.com"  # Or forsythc@ucr.edu
SENDER_ALIAS = "AstroPost Test Bot <forsythc@ucr.edu>"


def run_tests():
    print("🚀 Starting Comprehensive AstroPost Tests...")
    client = GmailClient(str(TOKEN_PATH), str(CREDENTIALS_PATH))

    # --- Test 1: Listing ---
    print("\n[1/6] Testing List...")
    try:
        emails = client.list_emails(max_results=5)
        print(f"✅ Listed {len(emails)} emails.")
        if len(emails) > 0:
            print(f"   Sample: {emails[0].subject}")
    except Exception as e:
        print(f"❌ List failed: {e}")
        sys.exit(1)

    # --- Test 2: Sending Simple ---
    print("\n[2/6] Testing Simple Send...")
    subject_simple = f"AstroPost Test Simple {int(time.time())}"
    try:
        msg_id_simple = client.send_email(
            recipients=[TEST_EMAIL],
            subject=subject_simple,
            body="This is a simple test body.",
            from_address=SENDER_ALIAS,
        )
        print(f"✅ Sent simple email. ID: {msg_id_simple}")
    except Exception as e:
        print(f"❌ Simple send failed: {e}")
        sys.exit(1)

    # --- Test 3: Sending HTML ---
    print("\n[3/6] Testing HTML Send...")
    html_content = "<h1>Hello</h1><p>This is <b>HTML</b>.</p>"
    # Write temp file
    Path("test_html_body.html").write_text(html_content)
    subject_html = f"AstroPost Test HTML {int(time.time())}"
    try:
        # We need to manually handle file reading here as main.py does it,
        # but client.send_email takes string body.
        # Wait, main.py reads file and passes content to body.
        msg_id_html = client.send_email(
            recipients=[TEST_EMAIL],
            subject=subject_html,
            body=html_content,  # Simulating main.py reading file
            from_address=SENDER_ALIAS,
        )
        print(f"✅ Sent HTML email. ID: {msg_id_html}")
    except Exception as e:
        print(f"❌ HTML send failed: {e}")
    finally:
        if Path("test_html_body.html").exists():
            Path("test_html_body.html").unlink()

    # --- Test 4: Attachment ---
    print("\n[4/6] Testing Attachment Send...")
    Path("test_attach.txt").write_text("Attachment content.")
    subject_attach = f"AstroPost Test Attach {int(time.time())}"
    try:
        msg_id_attach = client.send_email(
            recipients=[TEST_EMAIL],
            subject=subject_attach,
            body="See attached.",
            attachments=["test_attach.txt"],
            from_address=SENDER_ALIAS,
        )
        print(f"✅ Sent attachment email. ID: {msg_id_attach}")
    except Exception as e:
        print(f"❌ Attachment send failed: {e}")
    finally:
        if Path("test_attach.txt").exists():
            Path("test_attach.txt").unlink()

    # --- Wait for propagation ---
    print("\n⏳ Waiting 5 seconds for emails to propagate...")
    time.sleep(5)

    # --- Test 5: Actions (Unread, Archive, Trash) on the Simple Email ---
    print(f"\n[5/6] Testing Actions on {msg_id_simple}...")

    # Verify it exists first
    details = client.get_email_details(msg_id_simple)
    if not details:
        print("❌ Could not find sent email to test actions.")
    else:
        # Unread
        if client.modify_labels(msg_id_simple, add_labels=["UNREAD"]):
            print("✅ Marked Unread.")
        else:
            print("❌ Failed to Mark Unread.")

        # Archive (Remove Inbox)
        if client.modify_labels(msg_id_simple, remove_labels=["INBOX"]):
            print("✅ Archived.")
        else:
            print("❌ Failed to Archive.")

        # Trash
        if client.trash_email(msg_id_simple):
            print("✅ Trashed.")
        else:
            print("❌ Failed to Trash.")

    # --- Test 6: Reply ---
    print("\n[6/6] Testing Reply...")
    # We will reply to the HTML email we sent
    try:
        reply_subject = ""  # Auto-handled
        msg_id_reply = client.send_email(
            recipients=[TEST_EMAIL],
            subject=reply_subject,
            body="This is a reply to the HTML test.",
            reply_to_id=msg_id_html,
            from_address=SENDER_ALIAS,
        )
        print(f"✅ Sent reply. ID: {msg_id_reply}")

        # Cleanup HTML email too
        client.trash_email(msg_id_html)
        client.trash_email(msg_id_attach)  # Cleanup attach email
        client.trash_email(msg_id_reply)  # Cleanup reply
        print("✅ Cleaned up remaining test emails.")

    except Exception as e:
        print(f"❌ Reply failed: {e}")

    print("\n🎉 All Tests Completed.")


if __name__ == "__main__":
    run_tests()
