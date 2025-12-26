# `get_email_by_id.py`

This script retrieves the full content of a single email from your Gmail inbox using its unique Message ID.

## Description

The script connects to the Gmail API, fetches a specific email by its ID, and prints the key headers (From, To, Subject) and the full body of the message. It is designed to work in conjunction with `get_emails.py`, which provides the list of recent emails and their corresponding Message IDs.

The script is able to parse multipart emails and will prioritize displaying the HTML body if available, otherwise falling back to the plain text version.

## Usage

To run the script, use the following command:

```bash
./get_email_by_id.py <message_id>
```

Or:

```bash
python3 /home/chuck/Scripts/get_email_by_id.py <message_id>
```

-   `<message_id>` (required): The unique identifier of the email you want to retrieve. You can get this ID from the output of the `get_emails.py` script.

### Example

To get the email with the ID `197fabab1057bb96`:

```bash
./get_email_by_id.py 197fabab1057bb96
```

## Authentication

This script uses the same authentication method and credentials as `get_emails.py`. It relies on OAuth 2.0 and requires the `https://www.googleapis.com/auth/gmail.readonly` scope.

### First-Time Setup

If you have already run `get_emails.py` and authenticated, this script will automatically use the existing `token.json` and you will not need to re-authenticate.

If you are running this script for the first time without a `token.json` file present, it will initiate the same browser-based authentication flow described in the `get_emails.readme.md` file.

### Required Files

-   `credentials.json`: This file must be located at `/home/chuck/Scripts/credentials.json`.
-   `token.json`: This file is generated automatically after successful authorization and is stored at `/home/chuck/Scripts/token.json`.

## Dependencies

The script requires the same Python libraries as `get_emails.py`:
-   `google-api-python-client`
-   `google-auth-httplib2`
-   `google-auth-oauthlib`

If you have already installed them for the other script, you do not need to install them again.
```bash
pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib
```
