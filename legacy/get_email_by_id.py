#!/usr/bin/env python3
"""
This script retrieves a specific email from a user's Gmail inbox using its message ID.

It uses the Gmail API with OAuth 2.0 for authentication. The first time it runs,
it will open a browser window for the user to authorize access. Subsequent runs
will use the stored credentials in 'token.json'.

Usage:
    python3 get_email_by_id.py <message_id>
"""

import os.path
import base64
from email import message_from_bytes

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.auth.exceptions import RefreshError
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Scopes must match those used for the token.
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
TOKEN_PATH = "/home/chuck/Scripts/token_read.json"
CREDENTIALS_PATH = "/home/chuck/Scripts/credentials.json"


def get_credentials():
    """
    Gets user credentials from a local file, refreshing them if necessary.
    Initiates the OAuth2 flow if no valid credentials are found.
    """
    creds = None
    if os.path.exists(TOKEN_PATH):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
        except ValueError:
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except RefreshError:
                os.remove(TOKEN_PATH)
                return get_credentials()
        else:
            if not os.path.exists(CREDENTIALS_PATH):
                print(f"Error: Credentials file not found at {CREDENTIALS_PATH}")
                return None
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_PATH, "w") as token:
            token.write(creds.to_json())
    return creds


def get_email_body(email_message):
    """
    Parses the email message object to extract the body.
    It prioritizes HTML content, falling back to plain text.
    """
    if email_message.is_multipart():
        # Iterate over each part of the email
        for part in email_message.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))

            # Look for the main body, ignore attachments
            if content_type == "text/html" and "attachment" not in content_disposition:
                return part.get_payload(decode=True).decode()
            elif (
                content_type == "text/plain" and "attachment" not in content_disposition
            ):
                # Store plain text as a fallback
                fallback_body = part.get_payload(decode=True).decode()
    else:
        # Not a multipart message, just get the payload
        return email_message.get_payload(decode=True).decode()

    return fallback_body  # Return plain text if no HTML found


def get_email_by_id(message_id):
    """
    Retrieves and displays a single email by its ID.
    """
    creds = get_credentials()
    if not creds:
        print("Could not retrieve credentials. Exiting.")
        return

    try:
        service = build("gmail", "v1", credentials=creds)

        # Get the full message details using the message ID
        msg = (
            service.users()
            .messages()
            .get(userId="me", id=message_id, format="raw")
            .execute()
        )

        msg_raw = base64.urlsafe_b64decode(msg["raw"].encode("ASCII"))
        email_message = message_from_bytes(msg_raw)

        # Extract headers and body
        subject = email_message["subject"]
        sender = email_message["from"]
        recipient = email_message["to"]
        body = get_email_body(email_message)

        print("-" * 50)
        print(f"From: {sender}")
        print(f"To: {recipient}")
        print(f"Subject: {subject}")
        print("-" * 50)
        print("Body:")
        print(body)
        print("-" * 50)

    except HttpError as error:
        print(f"An error occurred: {error}")
        if error.resp.status == 404:
            print(f"Message with ID '{message_id}' not found.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Get a specific email from your Gmail inbox by its ID."
    )
    parser.add_argument("message_id", help="The ID of the email to retrieve.")
    args = parser.parse_args()

    get_email_by_id(args.message_id)
