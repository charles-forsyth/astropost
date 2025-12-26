import base64
import mimetypes
from typing import List, Optional, Dict, Any
from email.message import EmailMessage
from email import message_from_bytes
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.auth.exceptions import RefreshError
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from rich.console import Console

console = Console()

# Scopes required for both reading and sending
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]


class GmailClient:
    def __init__(self, token_path: str, credentials_path: str):
        self.token_path = Path(token_path)
        self.credentials_path = Path(credentials_path)
        self.creds = self._get_credentials()
        self.service = build("gmail", "v1", credentials=self.creds)

    def _get_credentials(self) -> Optional[Credentials]:
        creds: Optional[Credentials] = None
        if self.token_path.exists():
            try:
                creds = Credentials.from_authorized_user_file(
                    str(self.token_path), SCOPES
                )  # type: ignore
            except ValueError:
                creds = None

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())  # type: ignore
                except RefreshError:
                    if self.token_path.exists():
                        self.token_path.unlink()
                    return self._get_credentials()
            else:
                if not self.credentials_path.exists():
                    raise FileNotFoundError(
                        f"Credentials file not found at {self.credentials_path}"
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_path), SCOPES
                )
                creds = flow.run_local_server(port=0)

            with open(self.token_path, "w") as token:
                token.write(creds.to_json())
        return creds

    def list_emails(self, max_results: int = 10) -> List[Dict[str, Any]]:
        results = (
            self.service.users()
            .messages()
            .list(userId="me", labelIds=["INBOX"], maxResults=max_results)
            .execute()
        )
        messages = results.get("messages", [])

        email_list = []
        for msg_ref in messages:
            details = self.get_email_details(msg_ref["id"])
            if details:
                email_list.append(details)
        return email_list

    def get_email_details(self, msg_id: str) -> Dict[str, Any]:
        try:
            msg = (
                self.service.users()
                .messages()
                .get(userId="me", id=msg_id, format="raw")
                .execute()
            )
            msg_raw = base64.urlsafe_b64decode(msg["raw"].encode("ASCII"))
            email_message = message_from_bytes(msg_raw)

            subject = email_message["subject"]
            sender = email_message["from"]
            date = email_message["date"]
            snippet = msg.get("snippet", "")

            return {
                "id": msg_id,
                "threadId": msg["threadId"],
                "from": sender,
                "subject": subject,
                "date": date,
                "snippet": snippet,
                "body": self._get_email_body(email_message),
            }
        except HttpError as e:
            console.print(f"[red]Error fetching email {msg_id}: {e}[/red]")
            return {}

    def _get_email_body(self, email_message: Any) -> str:
        body = ""
        if email_message.is_multipart():
            for part in email_message.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))
                if (
                    content_type == "text/plain"
                    and "attachment" not in content_disposition
                ):
                    body = part.get_payload(decode=True).decode(errors="replace")
                    break
        else:
            body = email_message.get_payload(decode=True).decode(errors="replace")
        return body

    def send_email(
        self,
        recipients: List[str],
        subject: str,
        body: str,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        attachments: Optional[List[str]] = None,
        reply_to_id: Optional[str] = None,
        forward_id: Optional[str] = None,
        from_address: Optional[str] = None,
    ) -> str:
        message = EmailMessage()

        # Handle Reply/Forward Context
        thread_id = None
        quoted_info = None

        if reply_to_id:
            original = self.get_email_details(reply_to_id)
            thread_id = original.get("threadId")

            if not subject:
                original_subject = original.get("subject", "")
                if not original_subject.lower().startswith("re:"):
                    subject = f"Re: {original_subject}"
                else:
                    subject = original_subject

            quoted_info = f"\n\nOn {original.get('date')}, {original.get('from')} wrote:\n{original.get('snippet')}"

        elif forward_id:
            original = self.get_email_details(forward_id)
            if not subject:
                original_subject = original.get("subject", "")
                if not original_subject.lower().startswith("fwd:"):
                    subject = f"Fwd: {original_subject}"
                else:
                    subject = original_subject
            quoted_info = f"\n\n---------- Forwarded message ---------\nFrom: {original.get('from')}\nDate: {original.get('date')}\nSubject: {original.get('subject')}\n\n{original.get('body')}"

        full_body = body + (quoted_info if quoted_info else "")
        message.set_content(full_body)

        html_content = self._create_html_content(full_body)
        message.add_alternative(html_content, subtype="html")

        message["To"] = ", ".join(recipients)
        message["From"] = from_address if from_address else "me"
        message["Subject"] = subject

        if cc:
            message["Cc"] = ", ".join(cc)
        if bcc:
            message["Bcc"] = ", ".join(bcc)

        if attachments:
            for attachment_path in attachments:
                path = Path(attachment_path)
                if not path.exists():
                    console.print(
                        f"[yellow]Warning: Attachment {path} not found. Skipping.[/yellow]"
                    )
                    continue

                ctype, encoding = mimetypes.guess_type(path)
                if ctype is None or encoding is not None:
                    ctype = "application/octet-stream"
                maintype, subtype = ctype.split("/", 1)

                with open(path, "rb") as fp:
                    file_data = fp.read()
                    message.add_attachment(
                        file_data,
                        maintype=maintype,
                        subtype=subtype,
                        filename=path.name,
                    )

        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {"raw": encoded_message}

        if thread_id:
            create_message["threadId"] = thread_id

        send_message = (
            self.service.users()
            .messages()
            .send(userId="me", body=create_message)
            .execute()
        )
        return str(send_message["id"])

    def _create_html_content(self, text_content: str) -> str:
        return f"""
        <html>
          <body style="font-family: Arial, sans-serif;">
            <div style="white-space: pre-wrap;">{text_content}</div>
          </body>
        </html>
        """
