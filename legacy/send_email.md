# Gmail API Email Sender

This Python script, `send_email.py`, allows you to send emails through the Gmail API using your own Gmail account. It supports professional HTML formatting, multiple recipients, CC/BCC, and multiple attachments.

## 1. Setup

### Dependencies

The script requires the Google Client Library for Python. If you haven't already, install it using pip:

```bash
pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

### Credentials

This script requires a `credentials.json` file from the Google Cloud Platform to authenticate with the Gmail API.

1.  **Create a GCP Project:** Go to the [Google Cloud Console](https://console.cloud.google.com/) and create a new project.
2.  **Enable the Gmail API:** In your project's dashboard, go to "APIs & Services" > "Enabled APIs & Services", click "+ ENABLE APIS AND SERVICES", search for "Gmail API", and enable it.
3.  **Create OAuth Credentials:**
    *   Go to "APIs & Services" > "Credentials".
    *   Click "+ CREATE CREDENTIALS" and select "OAuth client ID".
    *   Choose "Web application" for the application type.
    *   Under "Authorized redirect URIs", add `http://localhost:5678/rest/oauth2-credential/callback`.
    *   Click "Create".
    *   A dialog will appear with your client ID and client secret. Click the "DOWNLOAD JSON" button and save this file as `credentials.json` in the same directory as the script.

## 2. First-Time Authorization

The first time you run the script, it will need to get your permission to send emails on your behalf.

1.  Run the script from your terminal.
2.  It will print a URL. Copy this URL and paste it into your web browser.
3.  Choose the Google account you want to send emails from.
4.  You may see a "Google hasn't verified this app" warning. This is expected because it's your own personal script. Click "Advanced" and then "Go to (your project name) (unsafe)".
5.  Grant the script permission to "Send email on your behalf".
6.  After you approve, the script will complete the authentication, and a `token.json` file will be created in the script's directory. This file stores your authorization and will be used for future runs, so you won't have to authorize again unless you revoke the permission or delete the `token.json` file.

## 3. Usage

To send an email, run the script from your terminal with the required arguments.

### Syntax

```bash
python3 send_email.py recipients [recipients ...] subject [body] [options]
```

### Options

*   `recipients`: Space-separated list of recipient email addresses.
*   `subject`: The subject line of the email.
*   `body`: The body text of the email (optional if using `--input-file`).
*   `--cc`: Space-separated list of CC email addresses.
*   `--bcc`: Space-separated list of BCC email addresses.
*   `--from-address`: The email address to use as the sender (defaults to your authenticated Gmail account).
*   `--reply-to-id`: The Message ID of the email you want to reply to (handles threading automatically).
*   `--forward-id`: The Message ID of the email you want to forward.
*   `--attach`: Space-separated list of file paths to attach.
*   `--input-file`: Path to a file containing the email body text (replaces the `body` argument).

### Reply and Forward

**5. Replying to an Email:**
When replying, the script automatically threads the email and sets the subject (e.g., "Re: Original Subject").
```bash
python3 /home/chuck/Scripts/send_email.py "recipient@example.com" \
  --reply-to-id "19234abcde12345" \
  --body "Got it, thanks!"
```
*Note: You can omit the subject argument when replying.*

**6. Forwarding an Email:**
When forwarding, the script sets the subject (e.g., "Fwd: Original Subject") and quotes the original details.
```bash
python3 /home/chuck/Scripts/send_email.py "new_recipient@example.com" \
  --forward-id "19234abcde12345" \
  --body "FYI, see below."
```

## Important Note on Permissions
This script now requires permission to **read** your emails (to fetch details for replies/forwards) as well as send them. If you updated this script from an older version, you may get a permissions error. If so, simply delete the `token_send.json` file in the script's directory and run the script again to re-authorize with the new permissions.


### Examples

**1. Simple Email (automatically formatted as professional HTML):**
```bash
python3 /home/chuck/Scripts/send_email.py "jane.doe@example.com" "Project Update" "Hi Jane, Just a quick update on the project."
```

**4. Specifying a Custom Sender Address:**
```bash
python3 \
  "recipient@example.com" \
  "Important Notice" \
  "This email is sent from a custom address." \
  --from-address "noreply@yourdomain.com"
```

**2. Multiple Recipients and Attachments:**
```bash
python3 \
  "jane.doe@example.com" "john.smith@example.com" \
  "Meeting Notes" \
  "Here are the notes from today's meeting." \
  --attach "/home/chuck/Documents/notes.pdf" "/home/chuck/Documents/chart.png"
```

**3. Using CC, BCC, and an Input File:**
```bash
python3 \
  "team-lead@example.com" \
  "Weekly Report" \
  --input-file "/home/chuck/reports/weekly_summary.txt" \
  --cc "manager@example.com" \
  --bcc "archive@example.com"
```

If the email is sent successfully, the script will print the `Message Id` of the sent email.