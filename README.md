# AstroPost

**AstroPost** (`v0.1.22`) is a Python CLI for Gmail reading, searching, AI summarization, interactive inbox triage, Markdown-to-HTML email composition, draft/label management, thread viewing, and attachment handling.

See [SPEC.md](SPEC.md) for the full system specification, architecture, OAuth scopes, and requirement traceability.

## Features

* **Inbox Listing & Search (`list`, `search`):** View latest or unread messages and run full Gmail search queries (`from:`, `subject:`, `has:attachment`, etc.) with Rich tables or `--json` output.
* **AI Summarization (`summarize`, `show --ai`):** Generate executive summaries of unread emails or individual messages using Google Gemini.
* **Interactive Inbox Scanner (`scan`):** Step through unread emails in the terminal with one-key actions (read full body, AI summary, mark read, archive, delete, skip).
* **Markdown-to-HTML Sending & Drafts (`send`, `drafts`):** Write emails in Markdown (inline `--body`, `--body-file`, or `$EDITOR` via `--editor`) and send or save as Gmail drafts with automatic responsive HTML formatting and file attachments (`--attach`).
* **Labels, Threads & Attachments (`labels`, `thread`, `attachments`):** Create/apply/remove Gmail labels, view full conversation threads, and inspect or download message attachments.

## Installation

```bash
uv tool install --python 3.12 git+https://github.com/charles-forsyth/astropost.git
```

## Configuration

AstroPost stores its configuration and OAuth credentials in `~/.config/astropost/` (`0600` permissions):

1. **`~/.config/astropost/credentials.json`**: Google Cloud OAuth 2.0 Desktop Client credentials with the Gmail API enabled.
2. **`~/.config/astropost/token.json`**: Created automatically on first sign-in and refreshed silently on subsequent runs.
3. **`~/.config/astropost/.env`**:
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   ```

## Usage Examples

### 1. List & Search Emails
```bash
astropost list
astropost list --unread --max-results 10
astropost search "from:support subject:incident" --max-results 5
astropost list --json
```

### 2. Inspect a Message, Thread, or Attachments
```bash
astropost show 1a159f2d15915977 --ai --mark-read
astropost thread 1a159f2d15915977
astropost attachments 1a159f2d15915977 --download --output-dir ./downloads
```

### 3. AI Unread Summary & Interactive Triage
```bash
astropost summarize --max-results 10
astropost scan
```

### 4. Send Email or Manage Drafts
```bash
# Send Markdown email with attachment
astropost send --to colleague@example.edu \
               --subject "Weekly Status Report" \
               --body-file report.md \
               --attach summary.pdf

# Create, list, and send drafts
astropost drafts create --to colleague@example.edu --subject "Draft Note" --body "Checking in."
astropost drafts list
astropost drafts send <DRAFT_ID>
```

### 5. Manage Labels
```bash
astropost labels list
astropost labels create "Project-X"
astropost labels add <EMAIL_ID> --label "Project-X"
```

## Development

```bash
uv sync --python 3.12
uv run --python 3.12 pytest
uv run --python 3.12 ruff check src tests
```
