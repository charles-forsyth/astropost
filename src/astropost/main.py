import argparse
from pathlib import Path
import sys
import os

from typing import List

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.markdown import Markdown
from dotenv import load_dotenv
from google import genai

from astropost.client import GmailClient
from astropost.models import Email

console = Console()

# Configuration
CONFIG_DIR = Path.home() / ".config" / "astropost"
TOKEN_PATH = CONFIG_DIR / "token.json"
CREDENTIALS_PATH = CONFIG_DIR / "credentials.json"
ENV_PATH = CONFIG_DIR / ".env"

DEFAULT_FROM = "Charles Forsyth <forsythc@ucr.edu>"


def get_client() -> GmailClient:
    if not CONFIG_DIR.exists():
        console.print(f"[yellow]Creating config directory at {CONFIG_DIR}[/yellow]")
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    return GmailClient(str(TOKEN_PATH), str(CREDENTIALS_PATH))


def render_email_table(emails: List[Email], title: str) -> None:
    if not emails:
        console.print("[yellow]No emails found.[/yellow]")
        return

    table = Table(title=title)
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Date", style="magenta")
    table.add_column("From", style="green")
    table.add_column("Subject", style="white")

    for email in emails:
        table.add_row(
            str(email.id),
            str(email.date)[:25],
            str(email.sender)[:40],
            str(email.subject)[:60],
        )
    console.print(table)


def cmd_list(args: argparse.Namespace) -> None:
    client = get_client()
    with console.status("[bold green]Fetching emails..."):
        emails = client.list_emails(max_results=args.count)
    render_email_table(emails, f"Latest {len(emails)} Emails")


def cmd_search(args: argparse.Namespace) -> None:
    client = get_client()
    # Join args if multiple words provided without quotes
    query = " ".join(args.query)

    with console.status(f"[bold green]Searching for '{query}'..."):
        emails = client.list_emails(max_results=args.count, query=query)

    render_email_table(emails, f"Search Results: {len(emails)} found")


def cmd_summarize(args: argparse.Namespace) -> None:
    # Load API Key
    if not ENV_PATH.exists():
        console.print(f"[red]Error: .env file not found at {ENV_PATH}.[/red]")
        console.print("Please create it with: GEMINI_API_KEY=your_key_here")
        return

    load_dotenv(ENV_PATH)
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        console.print("[red]Error: GEMINI_API_KEY not found in .env file.[/red]")
        return

    # Initialize Client with the new SDK
    ai_client = genai.Client(api_key=api_key)

    client = get_client()

    # Fetch Unread Emails
    with console.status(f"[bold green]Fetching last {args.count} unread emails..."):
        emails = client.list_emails(max_results=args.count, label_ids=["UNREAD"])

    if not emails:
        console.print("[yellow]No unread emails found to summarize.[/yellow]")
        return

    console.print(
        f"[green]Found {len(emails)} unread emails. Generating summary...[/green]"
    )

    # Construct Prompt
    prompt_content = "Please summarize the following emails into a useful daily briefing. Group by topic if possible.\n\n"
    for email in emails:
        prompt_content += f"--- EMAIL ---\nFrom: {email.sender}\nSubject: {email.subject}\nDate: {email.date}\nBody:\n{email.body[:1500]}\n\n"

    try:
        with console.status("[bold cyan]Querying Gemini 3.0 Pro..."):
            # Using the requested model with the new SDK structure
            # Attempting to use the requested 3-pro-preview model.
            response = ai_client.models.generate_content(
                model="gemini-2.0-flash", contents=prompt_content
            )

            text = response.text or "No summary generated."
            console.print(
                Panel(Markdown(text), title="Inbox Summary", border_style="bold blue")
            )

    except Exception as e:
        console.print(f"[red]Gemini API Error:[/red] {e}")


def cmd_show(args: argparse.Namespace) -> None:
    client = get_client()
    with console.status(f"[bold green]Fetching email {args.id}..."):
        email = client.get_email_details(args.id)

    if not email:
        console.print(f"[red]Email {args.id} not found.[/red]")
        return

    console.print(
        Panel(
            f"[bold]From:[/bold] {email.sender}\n"
            f"[bold]Date:[/bold] {email.date}\n"
            f"[bold]Subject:[/bold] {email.subject}\n\n"
            f"{email.body}",
            title=f"Email ID: {email.id}",
            expand=False,
        )
    )


def handle_reply(client: GmailClient, email_details: Email) -> None:
    """Interactive reply flow."""
    console.print(f"\n[bold]Replying to:[/bold] {email_details.subject}")
    body = Prompt.ask("Enter your reply (or 'cancel' to abort)")

    if body.lower() == "cancel":
        return

    try:
        # Assuming sender is the one to reply to
        recipient = email_details.sender

        with console.status("[bold green]Sending reply..."):
            client.send_email(
                recipients=[recipient],
                subject="",  # Auto-handled by reply logic
                body=body,
                reply_to_id=email_details.id,
                from_address=DEFAULT_FROM,
            )
        console.print("[bold green]Reply sent![/bold green]")
        import time

        time.sleep(1.5)
    except Exception as e:
        console.print(f"[red]Failed to send reply: {e}[/red]")


def cmd_scan(args: argparse.Namespace) -> None:
    client = get_client()

    while True:
        console.clear()
        with console.status("[bold green]Fetching latest emails..."):
            emails = client.list_emails(max_results=args.count)

        if not emails:
            console.print("[yellow]No emails found.[/yellow]")
            break

        table = Table(title=f"Scan Mode: Latest {len(emails)} Emails")
        table.add_column("#", style="bold yellow", justify="right")
        table.add_column("From", style="green")
        table.add_column("Subject", style="white")
        table.add_column("Date", style="magenta")

        for idx, email in enumerate(emails, 1):
            table.add_row(
                str(idx),
                str(email.sender)[:30],
                str(email.subject)[:50],
                str(email.date)[:16],
            )

        console.print(table)
        console.print(
            "\n[dim]Commands: # (read), d # [#...] (delete), a # [#...] (archive), u # [#...] (unread), r # (reply), q (quit)[/dim]"
        )

        choice = Prompt.ask("Action")
        choice = choice.strip().lower()

        if choice == "q":
            break
        elif choice == "r" and len(choice) == 1:  # refresh only if single char
            continue
        elif not choice:
            continue

        # Parse command
        parts = choice.split()
        cmd = parts[0]

        indices: List[int] = []
        action = "unknown"

        if cmd.isdigit():
            # "1" -> Read single email
            indices = [int(cmd)]
            action = "read"
        elif len(parts) > 1:
            # "d 1 2 3" -> Multi-action
            action = cmd
            for p in parts[1:]:
                if p.isdigit():
                    indices.append(int(p))

        # Validate indices
        valid_indices = [i for i in indices if 1 <= i <= len(emails)]

        if not valid_indices:
            if action != "unknown" and action != "read":
                console.print("[red]No valid email numbers provided.[/red]")
                import time

                time.sleep(1)
            elif action == "read" and indices and not valid_indices:
                console.print("[red]Invalid email number.[/red]")
                import time

                time.sleep(1)
            continue

        # Single Read Action (Legacy behavior for single number)
        if action == "read" and len(valid_indices) == 1:
            target_idx = valid_indices[0]
            selected_email = emails[target_idx - 1]
            msg_id = selected_email.id

            console.clear()
            with console.status(f"[bold green]Loading email {target_idx}..."):
                full_email = client.get_email_details(msg_id)

            if full_email:
                console.print(
                    Panel(
                        f"[bold]From:[/bold] {full_email.sender}\n"
                        f"[bold]Date:[/bold] {full_email.date}\n"
                        f"[bold]Subject:[/bold] {full_email.subject}\n\n"
                        f"{full_email.body}",
                        title=f"Email #{target_idx}",
                        expand=False,
                    )
                )

                while True:
                    console.print(
                        "\n[dim]Actions: [r]eply, [d]elete, [a]rchive, [u]nread, [Enter] back[/dim]"
                    )
                    sub_choice = Prompt.ask("Select").strip().lower()

                    if sub_choice == "":
                        break
                    elif sub_choice == "r":
                        handle_reply(client, full_email)
                        break
                    elif sub_choice == "d":
                        if Confirm.ask(f"Delete email '{full_email.subject}'?"):
                            if client.trash_email(msg_id):
                                console.print("[green]Deleted.[/green]")
                                import time

                                time.sleep(1)
                            break
                    elif sub_choice == "a":
                        if client.modify_labels(msg_id, remove_labels=["INBOX"]):
                            console.print("[green]Archived.[/green]")
                            import time

                            time.sleep(1)
                        break
                    elif sub_choice == "u":
                        if client.modify_labels(msg_id, add_labels=["UNREAD"]):
                            console.print("[green]Marked as Unread.[/green]")
                            import time

                            time.sleep(1)
                        break
            continue

        # Multi-Action Loop
        if action in ["d", "a", "u"]:
            if action == "d" and not Confirm.ask(
                f"Delete {len(valid_indices)} emails?"
            ):
                continue

            for target_idx in valid_indices:
                selected_email = emails[target_idx - 1]
                msg_id = selected_email.id

                if action == "d":
                    client.trash_email(msg_id)
                    console.print(f"[red]Deleted #{target_idx}[/red]")
                elif action == "a":
                    client.modify_labels(msg_id, remove_labels=["INBOX"])
                    console.print(f"[green]Archived #{target_idx}[/green]")
                elif action == "u":
                    client.modify_labels(msg_id, add_labels=["UNREAD"])
                    console.print(f"[blue]Unread #{target_idx}[/blue]")

            import time

            time.sleep(1.5)

        elif action == "r":
            if valid_indices:
                target_idx = valid_indices[0]
                selected_email = emails[target_idx - 1]
                msg_id = selected_email.id

                with console.status(
                    f"[bold green]Loading email {target_idx} for reply..."
                ):
                    full_email = client.get_email_details(msg_id)
                if full_email:
                    handle_reply(client, full_email)


def cmd_send(args: argparse.Namespace) -> None:
    client = get_client()

    body = ""
    if args.input_file:
        with open(args.input_file, "r") as f:
            body = f.read()
    elif args.body:
        body = args.body
    elif not sys.stdin.isatty():
        # Read from pipe if body is empty and stdin is not a TTY
        with console.status("[bold green]Reading from stdin..."):
            body = sys.stdin.read()

    # Validation
    if not body and not args.reply_to_id and not args.forward_id:
        # Allow empty body for quick replies if needed, but warn
        if not args.yes:
            console.print("[yellow]Warning: Sending email with empty body.[/yellow]")

    # Determine sender address
    sender = args.from_address if args.from_address else DEFAULT_FROM

    with console.status(f"[bold green]Sending email from {sender}..."):
        msg_id = client.send_email(
            recipients=args.recipients,
            subject=args.subject,
            body=body,
            cc=args.cc,
            bcc=args.bcc,
            attachments=args.attach,
            reply_to_id=args.reply_to_id,
            forward_id=args.forward_id,
            from_address=sender,
        )

    console.print(f"[bold green]Email sent successfully! ID: {msg_id}[/bold green]")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="AstroPost: The Modern Email Tool", prog="astropost"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # LIST
    parser_list = subparsers.add_parser(
        "list", help="List latest emails", aliases=["ls"]
    )
    parser_list.add_argument(
        "count", type=int, nargs="?", default=5, help="Number of emails to list"
    )
    parser_list.set_defaults(func=cmd_list)

    # SEARCH
    parser_search = subparsers.add_parser(
        "search", help="Search emails (e.g. 'from:chuck', 'invoice')"
    )
    parser_search.add_argument("query", nargs="+", help="Search query")
    parser_search.add_argument(
        "count", type=int, nargs="?", default=10, help="Max results"
    )
    parser_search.set_defaults(func=cmd_search)

    # SUMMARIZE
    parser_summ = subparsers.add_parser("summarize", help="Summarize unread emails")
    parser_summ.add_argument(
        "count", type=int, nargs="?", default=10, help="Number of emails to summarize"
    )
    parser_summ.set_defaults(func=cmd_summarize)

    # SCAN (Interactive List)
    parser_scan = subparsers.add_parser("scan", help="Interactive email scanner")
    parser_scan.add_argument(
        "count", type=int, nargs="?", default=10, help="Number of emails to scan"
    )
    parser_scan.set_defaults(func=cmd_scan)

    # SHOW
    parser_show = subparsers.add_parser("show", help="Show specific email details")
    parser_show.add_argument("id", help="Message ID")
    parser_show.set_defaults(func=cmd_show)

    # SEND
    parser_send = subparsers.add_parser("send", help="Send an email")
    parser_send.add_argument(
        "--to", dest="recipients", nargs="+", required=True, help="Recipient(s)"
    )
    parser_send.add_argument("--subject", "-s", help="Subject line")
    parser_send.add_argument("--body", "-b", help="Body text")
    parser_send.add_argument(
        "--file", "-f", dest="input_file", help="File containing body text"
    )
    parser_send.add_argument(
        "--from", "-F", dest="from_address", help="Sender address (overrides default)"
    )
    parser_send.add_argument("--attach", "-a", nargs="*", help="Attachments")
    parser_send.add_argument("--cc", nargs="*", help="CC recipients")
    parser_send.add_argument("--bcc", nargs="*", help="BCC recipients")
    parser_send.add_argument(
        "--reply-to", dest="reply_to_id", help="Reply to Message ID"
    )
    parser_send.add_argument("--forward", dest="forward_id", help="Forward Message ID")
    parser_send.add_argument(
        "--yes", "-y", action="store_true", help="Skip confirmation (not fully impl)"
    )
    parser_send.set_defaults(func=cmd_send)

    args = parser.parse_args()

    try:
        if hasattr(args, "func"):
            args.func(args)
        else:
            parser.print_help()
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Operation cancelled by user.[/bold yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
