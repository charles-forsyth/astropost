# AstroPost - Project Context

## Project Overview
**AstroPost** is a modern, terminal-centric email CLI tool designed to replace scattered Python scripts for Gmail interactions. It consolidates email retrieval, sending, reporting, and management into a unified, robust application.

- **Language:** Python 3.12+
- **Manager:** `uv` (Unified Python packaging)
- **Key Libraries:** `google-api-python-client` (Gmail API), `rich` (TUI/formatting), `argparse` (CLI), `pydantic`.
- **Repo:** [github.com/charles-forsyth/astropost](https://github.com/charles-forsyth/astropost)

## Architecture
The project follows a standard `src`-layout structure:

- **`src/astropost/`**: Source code.
    - `main.py`: CLI entry point, argument parsing, and command routing.
    - `client.py`: `GmailClient` class encapsulation OAuth2 authentication (`google-auth`) and Gmail API interactions.
- **`legacy/`**: Archived scripts (`get_emails.py`, `send_email.py`, etc.) that have been superseded by AstroPost.
- **`tests/`**: `pytest` suite.
- **`pyproject.toml`**: Project configuration, dependencies, and build settings (Hatchling backend).

## Configuration & Authentication
AstroPost uses a persistent configuration directory:

- **Config Path:** `~/.config/astropost/`
- **Credentials:** `~/.config/astropost/credentials.json` (OAuth Client ID/Secret)
- **Token:** `~/.config/astropost/token.json` (Generated Oauth2 Session)
- **Default Sender:** `Charles Forsyth <forsythc@ucr.edu>`

Authentication is handled via `google-auth-oauthlib`. On the first run, it initiates a local server flow to generate the `token.json`.

---

## ⚔️ The Skywalker Development Workflow

**Core Philosophy**

"Do or do not. There is no try." Code must be perfect before it leaves your local machine.

**Required Arsenal (The Stack)** To execute this workflow, the following tools are mandatory in your project:

- **uv**: The unified Python package and project manager (replaces pip, poetry, venv).
- **ruff**: An extremely fast Python linter and formatter (replaces flake8, black, isort).
- **mypy**: Static type checker for Python.
- **pytest**: The testing framework.
- **gh (GitHub CLI)**: For managing Pull Requests from the terminal.
- **pydantic (v2)**: For robust data validation and settings management (standard in your projects like roam and datum).

**The Workflow Steps**

1. **Branch & Bump**
   Never work on main. Start every task by isolating it and incrementing the version immediately.
   - Action: Create a descriptive feature branch.
   - Action: Update the version in pyproject.toml.
   ```bash
   git checkout -b feature/your-feature-name
   # Edit pyproject.toml to increment version (e.g., 0.1.24 -> 0.1.25)
   ```

2. **The Local Gauntlet (Iterative)**
   This is the most critical step. You must run this repeatedly during development. Do not proceed until all checks pass.
   - **Lint & Fix**: Auto-fix simple style issues. `uv run ruff check . --fix`
   - **Format**: Enforce standard code style. `uv run ruff format .`
   - **Type Check**: Ensure strict typing compliance. `uv run mypy src`
   - **Test**: Run the unit test suite. `uv run pytest`

3. **Push & PR**
   Once the Gauntlet is passed locally, push your changes and open a Pull Request.
   ```bash
   git add .
   git commit -m "Feature: Description of change"
   git push -u origin feature/your-feature-name
   gh pr create --fill
   ```

4. **The Gatekeeper (CI)**
   Watch the remote Continuous Integration checks. This confirms that your code works in a clean environment, not just your machine.
   ```bash
   gh pr checks --watch
   ```

5. **Merge**
   Merge via the PR (Squash & Merge is preferred for clean history). Never merge locally with git merge unless explicitly instructed to bypass CI.
   ```bash
   gh pr merge --merge --delete-branch
   ```

6. **Release & Sync**
   Finalize the versioning and update your local tools to use the new code.
   ```bash
   git pull origin main
   git tag v0.1.25  # Use the version you set in step 1
   git push origin v0.1.25
   gh release create v0.1.25 --title "v0.1.25" --notes "Feature notes..."
   ```

   **Self-Update (if CLI):**
   ```bash
   uv tool upgrade your-tool-name
   ```

7. **Final Verification**
   Run a functional test of the installed tool to ensure the end-user experience is correct.
   Example: `roam "Las Vegas" -W` (or `astropost list`)

**Summary Checklist**
- [ ] Branch (git checkout -b)
- [ ] Bump (pyproject.toml)
- [ ] Gauntlet (ruff, mypy, pytest) — Loop until pass
- [ ] PR (gh pr create)
- [ ] CI (gh pr checks)
- [ ] Merge (gh pr merge)
- [ ] Release (gh release create)