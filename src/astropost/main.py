import argparse

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from astropost.client import GmailClient

console = Console()

# Configuration (could be moved to env vars or config file)
TOKEN_PATH = "/home/chuck/Scripts/token_combined.json"  # New unified token
CREDENTIALS_PATH = "/home/chuck/Scripts/credentials.json"


def get_client() -> GmailClient:
    return GmailClient(TOKEN_PATH, CREDENTIALS_PATH)


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

    with console.status("[bold green]Sending email..."):
        msg_id = client.send_email(
            recipients=args.recipients,
            subject=args.subject,
            body=body,
            cc=args.cc,
            bcc=args.bcc,
            attachments=args.attach,
            reply_to_id=args.reply_to_id,
            forward_id=args.forward_id,
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
