import base64
import mimetypes
from typing import List, Optional, Any, Dict
from pathlib import Path
import re

from bs4 import BeautifulSoup
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.auth.exceptions import RefreshError
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from rich.console import Console
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
import markdown

from astropost.models import Email
from email.message import EmailMessage
from email import message_from_bytes

console = Console()

# Scopes required for both reading and sending
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
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

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(HttpError),
    )
    def list_emails(
        self,
        max_results: int = 10,
        query: Optional[str] = None,
        label_ids: Optional[List[str]] = None,
    ) -> List[Email]:
        try:
            kwargs: Dict[str, Any] = {"userId": "me", "maxResults": max_results}
            if query:
                kwargs["q"] = query
            elif label_ids:
                kwargs["labelIds"] = label_ids
            else:
                kwargs["labelIds"] = ["INBOX"]

            results = self.service.users().messages().list(**kwargs).execute()
            messages = results.get("messages", [])

            email_list = []
            for msg_ref in messages:
                details = self.get_email_details(msg_ref["id"])
                if details:
                    email_list.append(details)
            return email_list
        except HttpError as e:
            if e.resp.status == 403:
                console.print(
                    "[red]Permission denied. You may need to delete your token.json to re-authorize with new scopes.[/red]"
                )
                raise
            else:
                raise
            return []

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(HttpError),
    )
    def get_email_details(self, msg_id: str) -> Optional[Email]:
        try:
            msg = (
                self.service.users()
                .messages()
                .get(userId="me", id=msg_id, format="raw")
                .execute()
            )
            msg_raw = base64.urlsafe_b64decode(msg["raw"].encode("ASCII"))
            email_message = message_from_bytes(msg_raw)

            subject = email_message["subject"] or "(No Subject)"
            sender = email_message["from"] or "Unknown"
            date = email_message["date"] or ""
            snippet = msg.get("snippet", "")

            return Email(
                id=msg_id,
                threadId=msg["threadId"],
                **{"from": sender},
                subject=subject,
                date=date,
                snippet=snippet,
                body=self._get_email_body(email_message),
            )
        except HttpError as e:
            console.print(f"[red]Error fetching email {msg_id}: {e}[/red]")
            return None

    def _get_email_body(self, email_message: Any) -> str:
        html_part: Optional[str] = None
        text_part: Optional[str] = None

        if email_message.is_multipart():
            for part in email_message.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))

                if "attachment" in content_disposition:
                    continue

                payload = part.get_payload(decode=True)
                if not payload:
                    continue

                decoded_payload = str(payload.decode(errors="replace"))

                if content_type == "text/plain":
                    text_part = decoded_payload
                elif content_type == "text/html":
                    html_part = decoded_payload
        else:
            payload = email_message.get_payload(decode=True)
            if payload:
                decoded = str(payload.decode(errors="replace"))
                if email_message.get_content_type() == "text/html":
                    html_part = decoded
                else:
                    text_part = decoded

        if text_part:
            return text_part.strip()
        elif html_part:
            soup: Any = BeautifulSoup(html_part, "html.parser")
            for script in soup(["script", "style"]):
                script.decompose()
            cleaned_text = soup.get_text(separator="\n").strip()
            ret: str = str(cleaned_text)
            return ret  # type: ignore[no-any-return, unused-ignore]

        return ""

    def _sanitize_body(self, text: str) -> str:
        """
        Cleans LLM-generated text.
        1. If a markdown code block (``` ... ```) is found, extracts the content inside.
        2. Otherwise, returns the text stripped of whitespace.
        """
        # Regex to match ```language ... ``` or just ``` ... ```
        # DOTALL matches newlines
        match = re.search(r"```(?:\w+)?\n(.*?)```", text, re.DOTALL)
        if match:
            return match.group(1).strip()

        return text.strip()

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
            if original:
                thread_id = original.threadId

                if not subject:
                    original_subject = original.subject
                    if not original_subject.lower().startswith("re:"):
                        subject = f"Re: {original_subject}"
                    else:
                        subject = original_subject

                quoted_info = f"\n\nOn {original.date}, {original.sender} wrote:\n{original.snippet}"

        elif forward_id:
            original = self.get_email_details(forward_id)
            if original:
                if not subject:
                    original_subject = original.subject
                    if not original_subject.lower().startswith("fwd:"):
                        subject = f"Fwd: {original_subject}"
                    else:
                        subject = original_subject
                quoted_info = f"\n\n---------- Forwarded message ---------\nFrom: {original.sender}\nDate: {original.date}\nSubject: {original.subject}\n\n{original.body}"

        # Sanitize and Render
        clean_body = self._sanitize_body(body)
        full_text_body = clean_body + (quoted_info if quoted_info else "")

        # 1. Plain Text Part (Cleaned but not HTML rendered)
        message.set_content(full_text_body)

        # 2. HTML Part (Rendered Markdown)
        # We render only the new body content, preserving the quoted info as simple text block if needed,
        # or we could render the whole thing. Rendering the whole thing is safer for consistency.
        html_rendered = markdown.markdown(clean_body)

        if quoted_info:
            # Wrap quoted info in a blockquote or similar for HTML
            quoted_html = f"<br><br><blockquote style='border-left: 2px solid #ccc; padding-left: 10px; color: #555;'>{quoted_info.replace(chr(10), '<br>')}</blockquote>"
            full_html = html_rendered + quoted_html
        else:
            full_html = html_rendered

        html_wrapper = self._create_html_wrapper(full_html)
        message.add_alternative(html_wrapper, subtype="html")

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

    def _create_html_wrapper(self, html_content: str) -> str:
        return f"""
        <html>
          <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto;">
              {html_content}
            </div>
          </body>
        </html>
        """

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(HttpError),
    )
    def modify_labels(
        self, msg_id: str, add_labels: List[str] = [], remove_labels: List[str] = []
    ) -> bool:
        try:
            body = {"addLabelIds": add_labels, "removeLabelIds": remove_labels}
            self.service.users().messages().modify(
                userId="me", id=msg_id, body=body
            ).execute()
            return True
        except HttpError as e:
            console.print(f"[red]Error modifying labels for {msg_id}: {e}[/red]")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(HttpError),
    )
    def trash_email(self, msg_id: str) -> bool:
        try:
            self.service.users().messages().trash(userId="me", id=msg_id).execute()
            return True
        except HttpError as e:
            console.print(f"[red]Error trashing email {msg_id}: {e}[/red]")
            raise
