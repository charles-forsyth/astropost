#!/usr/bin/env python3
import os
import sys
import base64
import mimetypes
import argparse
from typing import List, Optional, Dict, Any
from email.message import EmailMessage
from email import message_from_bytes
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.auth.exceptions import RefreshError
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# --- Configuration ---
# Added 'readonly' scope to fetch message details for replies/forwards
SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
]
TOKEN_PATH = "/home/chuck/Scripts/token_send.json"
CREDENTIALS_PATH = "/home/chuck/Scripts/credentials.json"


def get_credentials():
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    # If creds are valid but might lack new scopes, we might get a 403 later.
    # However, Google auth often checks scopes on load.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except (RefreshError, Exception):
                # If refresh fails (e.g. scopes changed), remove token and re-auth
                print("Credentials invalid or expired. Re-authenticating...")
                if os.path.exists(TOKEN_PATH):
                    os.remove(TOKEN_PATH)
                return get_credentials()
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=5678)
        with open(TOKEN_PATH, "w") as token:
            token.write(creds.to_json())
    return creds


def create_html_content(text_content: str, quoted_content: Optional[str] = None) -> str:
    """
    Wraps plain text in a professional HTML template.
    If the text is not already HTML, it is parsed as Markdown to handle formatting
    (lists, bold, code blocks, etc.) and newlines (via nl2br).
    """
    stripped = text_content.strip()
    is_full_html = stripped.lower().startswith(
        "<!doctype html"
    ) or stripped.lower().startswith("<html")

    if is_full_html:
        # If user provided full HTML, we just append the quoted part if it exists
        if quoted_content:
            return text_content + "<br><br>" + quoted_content
        return text_content

    # Attempt to use markdown for robust formatting
    try:
        import markdown

        # 'nl2br' turns newlines into <br> (essential for email behavior)
        # 'extra' includes fenced_code, tables, etc.
        formatted_text = markdown.markdown(text_content, extensions=["nl2br", "extra"])
    except ImportError:
        # Fallback if markdown isn't installed
        formatted_text = text_content.replace("\n", "<br>")

    quoted_html = ""
    if quoted_content:
        # Simple quoting style
        quoted_html = f"""
        <div style=\"margin-top: 20px; padding-top: 20px; border-top: 1px solid #ddd; color: #666;\">
            {quoted_content.replace(chr(10), "<br>")}
        </div>
        """

    html_template = f"""
    <html>
      <body style="margin: 0; padding: 0; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background-color: #f4f4f4;">
        <div style="max-width: 600px; margin: 40px auto; background-color: #ffffff; padding: 40px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border: 1px solid #e0e0e0;">
          <div style="color: #333333; font-size: 16px; line-height: 1.6;">
            {formatted_text}
          </div>
          {quoted_html}
        </div>
      </body>
    </html>
    """
    return html_template


def sanitize_header(value: str) -> str:
    """Removes newlines and carriage returns from header values to prevent injection."""
    if value is None:
        return ""
    return value.replace("\r", "").replace("\n", "").strip()


def get_original_message(service, msg_id: str) -> Dict[str, Any]:
    """Fetches original message details for reply/forward context."""
    try:
        # Get raw to parse headers cleanly
        message = (
            service.users()
            .messages()
            .get(userId="me", id=msg_id, format="raw")
            .execute()
        )
        msg_bytes = base64.urlsafe_b64decode(message["raw"].encode("ASCII"))
        mime_msg = message_from_bytes(msg_bytes)

        return {
            "threadId": message["threadId"],
            "subject": mime_msg["Subject"] or "",
            "message_id": mime_msg["Message-ID"],
            "references": mime_msg["References"],
            "from": mime_msg["From"],
            "date": mime_msg["Date"],
            # Simple body extraction for quoting (could be improved to handle multipart)
            "snippet": message.get("snippet", "..."),
        }
    except HttpError as error:
        print(f"An error occurred fetching the original message: {error}")
        sys.exit(1)


def send_email(
    recipients: List[str],
    subject: str,
    body: Optional[str] = None,
    from_address: Optional[str] = None,
    cc: Optional[List[str]] = None,
    bcc: Optional[List[str]] = None,
    attachments: Optional[List[str]] = None,
    input_file: Optional[str] = None,
    reply_to_id: Optional[str] = None,
    forward_id: Optional[str] = None,
):
    # Validation
    if input_file and not os.path.exists(input_file):
        print(f"Error: Body input file '{input_file}' not found.")
        sys.exit(1)

    if attachments:
        for fpath in attachments:
            if not os.path.exists(fpath):
                print(f"Error: Attachment file '{fpath}' not found.")
                sys.exit(1)

    creds = get_credentials()
    if not creds:
        print("Could not retrieve credentials.")
        return

    try:
        service = build("gmail", "v1", credentials=creds)
        message = EmailMessage()

        # Determine body content
        email_body_content = ""
        if input_file:
            with open(input_file, "r") as f:
                email_body_content = f.read()
        elif body:
            email_body_content = body
        else:
            email_body_content = ""

        # Handle Reply/Forward Context
        thread_id = None
        quoted_info = None

        if reply_to_id:
            original = get_original_message(service, reply_to_id)
            thread_id = original["threadId"]

            # Auto-set Subject for Reply
            if not subject:
                original_subject = original.get("subject", "")
                if not original_subject.lower().startswith("re:"):
                    subject = f"Re: {original_subject}"
                else:
                    subject = original_subject

            # Set Headers for Threading
            message["In-Reply-To"] = sanitize_header(original["message_id"])
            references = original["references"] if original["references"] else ""
            message["References"] = sanitize_header(
                f"{references} {original['message_id']}".strip()
            )

            quoted_info = f"On {original['date']}, {original['from']} wrote:"

        elif forward_id:
            original = get_original_message(service, forward_id)

            # Auto-set Subject for Forward
            if not subject:
                original_subject = original.get("subject", "")
                if not original_subject.lower().startswith("fwd:"):
                    subject = f"Fwd: {original_subject}"
                else:
                    subject = original_subject

            quoted_info = f"---------- Forwarded message ---------\nFrom: {original['from']}\nDate: {original['date']}\nSubject: {original['subject']}"

        # Apply HTML formatting
        html_content = create_html_content(
            email_body_content, quoted_content=quoted_info
        )
        message.add_alternative(html_content, subtype="html")

        # Set headers
        message["To"] = ", ".join([sanitize_header(r) for r in recipients])
        message["From"] = sanitize_header(from_address) if from_address else "me"
        message["Subject"] = sanitize_header(subject)

        if cc:
            message["Cc"] = ", ".join([sanitize_header(c) for c in cc])
        if bcc:
            message["Bcc"] = ", ".join([sanitize_header(b) for b in bcc])

        # Process attachments
        if attachments:
            for attachment_path in attachments:
                ctype, encoding = mimetypes.guess_type(attachment_path)
                if ctype is None or encoding is not None:
                    ctype = "application/octet-stream"
                maintype, subtype = ctype.split("/", 1)

                with open(attachment_path, "rb") as fp:
                    file_data = fp.read()
                    filename = os.path.basename(attachment_path)
                    message.add_attachment(
                        file_data,
                        maintype=maintype,
                        subtype=subtype,
                        filename=sanitize_header(filename),
                    )

        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {"raw": encoded_message}

        if thread_id:
            create_message["threadId"] = thread_id

        send_message = (
            service.users().messages().send(userId="me", body=create_message).execute()
        )
        print(f"Message Id: {send_message['id']}")

    except HttpError as e:
        if e.resp.status == 403:
            print(
                "Error: Insufficient permissions. You may need to delete 'token_send.json' and re-run to authorize the new scopes."
            )
        else:
            print(f"An API error occurred: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Send, Reply, or Forward emails using the Gmail API.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Send a simple email
  python3 send_email.py --recipients user@example.com --subject "Hello" --body "This is a test."

  # Send to multiple recipients with CC and attachment
  python3 send_email.py --recipients user1@example.com user2@example.com \\
                        --subject "Report" --body "Attached is the report." \\
                        --cc manager@example.com --attach /path/to/report.pdf

  # Send using a file for the body
  python3 send_email.py --recipients user@example.com --subject "Newsletter" --input-file /path/to/newsletter.html

  # Reply to a message (subject is optional, defaults to Re: <Original Subject>)
  python3 send_email.py --recipients user@example.com --reply-to-id <MESSAGE_ID> --body "Got it, thanks!"

  # Forward a message
  python3 send_email.py --recipients new_user@example.com --forward-id <MESSAGE_ID> --body "FYI"
""",
    )

    parser.add_argument(
        "--recipients", nargs="+", help="List of recipient email addresses."
    )
    parser.add_argument(
        "--subject",
        default=None,
        help="Email subject line (optional for reply/forward).",
    )
    parser.add_argument(
        "--body", default=None, help="Email body text (optional if using --input-file)."
    )

    parser.add_argument("--cc", nargs="*", help="List of CC email addresses.")
    parser.add_argument("--bcc", nargs="*", help="List of BCC email addresses.")
    parser.add_argument("--attach", nargs="*", help="List of file paths to attach.")
    parser.add_argument("--input-file", help="Path to a file to use as the email body.")
    parser.add_argument("--from-address", help="Email address to use as the sender.")

    group = parser.add_mutually_exclusive_group()
    group.add_argument("--reply-to-id", help="Message ID of the email to reply to.")
    group.add_argument("--forward-id", help="Message ID of the email to forward.")

    args = parser.parse_args()

    # Validation logic tweaks for optional subject/body in reply/forward context
    if not args.reply_to_id and not args.forward_id:
        if not args.subject:
            parser.error("the following arguments are required: subject")

    # If replying/forwarding, body is optional (though usually desired)
    # The original check 'if not args.body and not args.input_file' needs to be relaxed if we just want to send a quick "Ack" reply or similar,
    # but let's keep it required or default to empty string if user provided nothing?
    # Actually, user might just want to forward without adding text.
    if (
        not args.body
        and not args.input_file
        and not args.forward_id
        and not args.reply_to_id
    ):
        parser.error("You must provide either a body text or an --input-file.")

    send_email(
        recipients=args.recipients,
        subject=args.subject,
        body=args.body,
        from_address=args.from_address,
        cc=args.cc,
        bcc=args.bcc,
        attachments=args.attach,
        input_file=args.input_file,
        reply_to_id=args.reply_to_id,
        forward_id=args.forward_id,
    )
