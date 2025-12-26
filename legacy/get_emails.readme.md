# `get_emails.py`

This script retrieves a specified number of the most recent emails from your Gmail inbox.

## Description

The script connects to the Gmail API using your credentials, fetches the latest emails from the "INBOX", and prints key information for each email, including the Message ID, sender, and subject.

The output of this script is designed to be used with `get_email_by_id.py`, which can retrieve the full content of a specific email using its Message ID.

## Usage

To run the script, use the following command:

```bash
./get_emails.py [number_of_emails]
```

Or:

```bash
python3 /home/chuck/Scripts/get_emails.py [number_of_emails]
```

-   `[number_of_emails]` (optional): The number of recent emails you want to retrieve. If you don't provide a number, it defaults to 5.

### Example

To get the 10 latest emails:

```bash
./get_emails.py 10
```

## Authentication

This script uses OAuth 2.0 to access your Gmail account. The required scopes are `https://www.googleapis.com/auth/gmail.readonly`.

### First-Time Setup

The first time you run this script (or after deleting `token.json`), it will:
1.  Open a new tab in your web browser.
2.  Ask you to log in to your Google account.
3.  Prompt you to grant permission for the script to read your emails.

After you grant permission, the script will create a `token.json` file in the `/home/chuck/Scripts/` directory. This file stores your authorization and will be used for future runs, so you won't have to log in every time.

### Required Files

-   `credentials.json`: This file contains your Google Cloud project's client ID and secret. It must be located at `/home/chuck/Scripts/credentials.json`.
-   `token.json`: This file is generated automatically after successful authorization and is stored at `/home/chuck/Scripts/token.json`.

## Dependencies

The script requires the following Python libraries:
-   `google-api-python-client`
-   `google-auth-httplib2`
-   `google-auth-oauthlib`

You can install them using pip:
```bash
pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib
```
