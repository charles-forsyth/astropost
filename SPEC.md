# astropost specification

Version 0.1.22 (2026-10-20; code 0.1.22). Owner: Chuck Forsyth.
Repository: `charles-forsyth/astropost` (local checkout `~/Projects/astropost`). License: MIT.

## 1. Purpose and scope

`astropost` is a modern Python CLI for Gmail reading, searching, AI summarization, interactive inbox triage (`scan`), Markdown-to-HTML email composition (`send`, `drafts`), label management (`labels`), thread inspection (`thread`), and attachment downloading (`attachments`). It combines:

- **Gmail REST API v1 (`google-api-python-client`)** authenticated via OAuth 2.0 user credentials (`~/.config/astropost/credentials.json` and `~/.config/astropost/token.json`) with exponential-backoff retries (`tenacity`).
- **Google Gemini (`google-genai`, `gemini-2.0-flash`)** authenticated via `GEMINI_API_KEY` in `~/.config/astropost/.env` for unread inbox executive summaries (`astropost summarize`) and single-message AI summaries (`astropost show <id> --ai` / `scan`).
- **Rich TUI & JSON dual output (`--json`)** so every read/write subcommand works both interactively for a human operator and programmatically inside scripts or agent pipelines.

## 2. Design decisions

| # | Decision | Rationale |
|---|---|---|
| D1 | Dedicated per-tool config directory `~/.config/astropost/` (`0600` `.env`, `credentials.json`, `token.json`) | Isolates Gmail OAuth tokens and `GEMINI_API_KEY` from other tools. |
| D2 | Automatic OAuth token refresh with corrupt/revoked token recovery (`GmailClient._get_credentials`) | When `token.json` expires, `creds.refresh(Request())` renews it silently; if `RefreshError` occurs, `token.json` is unlinked and the local loopback `InstalledAppFlow` re-runs cleanly. |
| D3 | Markdown-to-HTML multipart composition (`create_html_wrapper`) | Plain text/Markdown bodies passed to `send` or `drafts create` are converted via `markdown` (`nl2br`, `fenced_code`, `tables`) and wrapped in a clean, left-aligned responsive HTML stylesheet alongside the `text/plain` part. |
| D4 | Tenacity retry wrapper (`@retry_api`) on all Gmail API calls | Retries transient ` googleapiclient.errors.HttpError` and ` ssl.SSLError` up to 3 attempts with exponential backoff (`2s..10s`). |
| D5 | Machine-readable `--json` flag across subcommands | Every listing, search, show, draft, label, attachment, and thread command supports `--json` to emit structured JSON (`model_dump()`) instead of Rich tables. |

## 3. Architecture

```text
astropost CLI (src/astropost/main.py)
  |-- Config & Auth (~/.config/astropost/)
  |     |-- .env (GEMINI_API_KEY)
  |     |-- credentials.json (OAuth 2.0 Desktop Client)
  |     `-- token.json (Refreshed OAuth 2.0 User Token, scopes: readonly, send, modify, labels)
  |-- GmailClient (src/astropost/client.py)
  |     |-- list_messages() / get_message() / get_thread()
  |     |-- send_message() / create_draft() / list_drafts() / send_draft() / delete_draft()
  |     |-- list_labels() / create_label() / modify_message_labels()
  |     |-- get_attachments() / download_attachment()
  |     |-- mark_as_read() / archive_message() / delete_message()
  |     `-- create_html_wrapper() (Markdown -> styled HTML + plain text multipart)
  |-- Data Models (src/astropost/models.py)
  |     `-- Email, Draft, Label, Attachment, Thread (Pydantic / dataclass models)
  `-- AI Summarizer (main.py -> summarize_with_gemini())
        `-- google.genai.Client(api_key=GEMINI_API_KEY) -> gemini-2.0-flash
```

### Module map

| File | Responsibility |
|---|---|
| `src/astropost/main.py` | Argparse CLI defining 10 subcommands (`list`/`ls`, `search`, `summarize`, `scan`, `show`, `send`, `drafts`, `labels`, `attachments`, `thread`), Rich table/panel rendering, `$EDITOR` composition (`spawn_editor`), and Gemini summarization. |
| `src/astropost/client.py` | `GmailClient` wrapping Gmail v1 REST endpoints with `tenacity` retries, MIME parsing (`BeautifulSoup` HTML-to-text fallback), multipart Markdown-to-HTML message construction, attachment extraction, and label/draft/thread operations. |
| `src/astropost/models.py` | Structured models for `Email`, `Attachment`, `Draft`, `Label`, and `Thread`. |
| `legacy/` | Historical standalone scripts (`get_emails.py`, `send_email.py`, `email-report.py`) superseded by the unified `src/astropost` package. |

## 4. OAuth scopes and configuration (`~/.config/astropost/`)

Required Gmail OAuth 2.0 scopes (`SCOPES` in `src/astropost/client.py`):
- `https://www.googleapis.com/auth/gmail.readonly`
- `https://www.googleapis.com/auth/gmail.send`
- `https://www.googleapis.com/auth/gmail.modify`
- `https://www.googleapis.com/auth/gmail.labels`

Configuration files in `~/.config/astropost/`:
- `credentials.json` (`0600`): Google Cloud OAuth 2.0 Desktop Client secret JSON.
- `token.json` (`0600`): Authorized user refresh + access token JSON.
- `.env` (`0600`):
  ```env
  GEMINI_API_KEY=AIza...
  ```

## 5. CLI interface

```text
astropost <subcommand> [options]

Subcommands:
  list (ls)       [--max-results N] [--unread] [--label LABEL] [--json]
  search          QUERY [--max-results N] [--json]
  summarize       [--max-results N]
  scan            [--max-results N]
  show            EMAIL_ID [--raw] [--ai] [--mark-read] [--json]
  send            --to EMAIL [EMAIL ...] --subject TEXT [--body TEXT | --body-file FILE | --editor]
                  [--cc EMAIL ...] [--bcc EMAIL ...] [--attach FILE ...] [--from-addr ADDR] [--html]
  drafts          {list,create,send,delete} ... [--json]
  labels          {list,create,add,remove} ... [--json]
  attachments     EMAIL_ID [--download] [--output-dir DIR] [--json]
  thread          THREAD_ID [--json]
```

## 6. Requirements traceability

| ID | Requirement | Verified by |
|---|---|---|
| REQ-CLI-1 | `send` command parses multiple `--to`, `--cc`, `--bcc`, and `--attach` arguments cleanly. | `tests/test_cli.py::test_arg_parsing_send` |
| REQ-HTML-1 | `create_html_wrapper` renders Markdown to left-aligned responsive HTML (`text-align: left`, `margin: 0`). | `tests/test_client.py::test_create_html_wrapper_alignment` |
| REQ-JSON-1 | `--json` outputs valid JSON arrays/objects on `list` and `show`. | `tests/test_json_output.py::test_list_json`, `test_show_json` |
| REQ-DRAFT-1 | `drafts list`, `drafts create`, and `drafts send` manage Gmail drafts and support Rich/JSON output. | `tests/test_rich_additions.py::test_drafts_list`, `test_drafts_create`, `test_drafts_send` |
| REQ-LABEL-1 | `labels list`, `labels create`, `labels add`, and `labels remove` mutate and display Gmail labels. | `tests/test_rich_additions.py::test_labels_list`, `test_labels_create`, `test_labels_add`, `test_labels_remove` |
| REQ-ATT-1 | `attachments` lists and downloads message attachments to the target directory; `thread` renders full conversation threads. | `tests/test_rich_additions.py::test_attachments_download`, `test_thread_show` |

## 7. Known gaps and backlog

- **K1 (Confirmed):** `summarize_with_gemini()` in `src/astropost/main.py` hardcodes `model="gemini-2.0-flash"`; upgrading the default summarization model to `gemini-3.8-flash` (with an env override `ASTROPOST_MODEL`) will keep it current as 2.0 models retire.
- **K2 (Confirmed):** `legacy/` scripts in the repo root predate the `src/astropost` package and can be archived or removed in a future cleanup PR.
