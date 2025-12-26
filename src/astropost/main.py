import argparse
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt

from astropost.client import GmailClient

console = Console()

# Configuration
CONFIG_DIR = Path.home() / ".config" / "astropost"
TOKEN_PATH = CONFIG_DIR / "token.json"
CREDENTIALS_PATH = CONFIG_DIR / "credentials.json"

DEFAULT_FROM = "Charles Forsyth <forsythc@ucr.edu>"


def get_client() -> GmailClient:
    if not CONFIG_DIR.exists():
        console.print(f"[yellow]Creating config directory at {CONFIG_DIR}[/yellow]")
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    return GmailClient(str(TOKEN_PATH), str(CREDENTIALS_PATH))


def cmd_list(args: argparse.Namespace) -> None:
    client = get_client()
    with console.status("[bold green]Fetching emails..."):
        emails = client.list_emails(max_results=args.count)

    if not emails:
        console.print("[yellow]No emails found.[/yellow]")
        return

    table = Table(title=f"Latest {len(emails)} Emails")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Date", style="magenta")
    table.add_column("From", style="green")
    table.add_column("Subject", style="white")

    for email in emails:
        table.add_row(
            str(email["id"]),
            str(email["date"])[:25],  # Truncate date for display
            str(email["from"])[:40],
            str(email["subject"])[:60],
        )

    console.print(table)


def cmd_show(args: argparse.Namespace) -> None:
    client = get_client()
    with console.status(f"[bold green]Fetching email {args.id}..."):
        email = client.get_email_details(args.id)

    if not email:
        console.print(f"[red]Email {args.id} not found.[/red]")
        return

    console.print(
        Panel(
            f"[bold]From:[/bold] {email['from']}\n"
            f"[bold]Date:[/bold] {email['date']}\n"
            f"[bold]Subject:[/bold] {email['subject']}\n\n"
            f"{email['body']}",
            title=f"Email ID: {email['id']}",
            expand=False,
        )
    )


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
                str(email["from"])[:30],
                str(email["subject"])[:50],
                str(email["date"])[:16],
            )

        console.print(table)
        console.print("\n[dim]Enter # to read, 'r' to refresh, or 'q' to quit[/dim]")

        choice = Prompt.ask("Select")

        if choice.lower() == "q":
            break
        elif choice.lower() == "r":
            continue

        try:
            idx = int(choice)
            if 1 <= idx <= len(emails):
                selected_email = emails[idx - 1]
                console.clear()

                # Re-fetch full details to ensure body is fresh/clean
                with console.status(
                    f"[bold green]Loading email {selected_email['id']}..."
                ):
                    full_email = client.get_email_details(selected_email["id"])

                if full_email:
                    console.print(
                        Panel(
                            f"[bold]From:[/bold] {full_email['from']}\n"
                            f"[bold]Date:[/bold] {full_email['date']}\n"
                            f"[bold]Subject:[/bold] {full_email['subject']}\n\n"
                            f"{full_email['body']}",
                            title=f"Email #{idx}: {full_email['subject']}",
                            expand=False,
                        )
                    )
                else:
                    console.print("[red]Failed to load email details.[/red]")

                Prompt.ask("\n[bold]Press Enter to return to list[/bold]")
            else:
                console.print("[red]Invalid number.[/red]")
                import time

                time.sleep(1)
        except ValueError:
            pass


def cmd_send(args: argparse.Namespace) -> None:
    client = get_client()

    body = ""
    if args.input_file:
        with open(args.input_file, "r") as f:
            body = f.read()
    elif args.body:
        body = args.body

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

    if hasattr(args, "func"):
        try:
            args.func(args)
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}")
            import traceback

            traceback.print_exc()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
