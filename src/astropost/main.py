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


def spawn_editor(initial_content: str = "") -> str:
    import subprocess
    import tempfile

    editor = os.environ.get("EDITOR", "nano")
    with tempfile.NamedTemporaryFile(
        suffix=".md", delete=False, mode="w+", encoding="utf-8"
    ) as temp_file:
        temp_file.write(initial_content)
        temp_file_path = temp_file.name

    try:
        subprocess.run([editor, temp_file_path], check=True)
        with open(temp_file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        console.print(f"[red]Error invoking editor {editor}: {e}[/red]")
        return initial_content
    finally:
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)


def cmd_list(args: argparse.Namespace) -> None:
    client = get_client()
    with console.status("[bold green]Fetching emails..."):
        emails = client.list_emails(max_results=args.count)

    if args.json:
        import json

        json_output = json.dumps(
            [e.model_dump(by_alias=True) for e in emails], indent=2
        )
        print(json_output)
    else:
        render_email_table(emails, f"Latest {len(emails)} Emails")


def cmd_search(args: argparse.Namespace) -> None:
    client = get_client()
    query = " ".join(args.query)

    with console.status(f"[bold green]Searching for '{query}'..."):
        emails = client.list_emails(max_results=args.count, query=query)

    render_email_table(emails, f"Search Results: {len(emails)} found")


def cmd_summarize(args: argparse.Namespace) -> None:
    if not ENV_PATH.exists():
        console.print(f"[red]Error: .env file not found at {ENV_PATH}.[/red]")
        console.print("Please create it with: GEMINI_API_KEY=your_key_here")
        return

    load_dotenv(ENV_PATH)
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        console.print("[red]Error: GEMINI_API_KEY not found in .env file.[/red]")
        return

    ai_client = genai.Client(api_key=api_key)
    client = get_client()

    with console.status(
        f"[bold green]Fetching last {args.count} unread emails in Inbox..."
    ):
        emails = client.list_emails(
            max_results=args.count, label_ids=["UNREAD", "INBOX"]
        )

    if not emails:
        console.print("[yellow]No unread emails found in Inbox to summarize.[/yellow]")
        return
    console.print(
        f"[green]Found {len(emails)} unread emails. Generating summary...[/green]"
    )

    prompt_content = "Please summarize the following emails into a useful daily briefing. Group by topic if possible.\n\n"
    for email in emails:
        prompt_content += f"--- EMAIL ---\nFrom: {email.sender}\nSubject: {email.subject}\nDate: {email.date}\nBody:\n{email.body[:1500]}\n\n"

    try:
        with console.status("[bold cyan]Querying Gemini 3.5 Flash..."):
            response = ai_client.models.generate_content(
                model="gemini-3.5-flash", contents=prompt_content
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

    if args.json:
        print(email.model_dump_json(indent=2, by_alias=True))
    else:
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
    body = Prompt.ask(
        "Enter your reply [dim](or press Enter to open editor, 'cancel' to abort)[/dim]",
        default="",
    )

    if body.lower() == "cancel":
        return

    if not body:
        body = spawn_editor()
        if not body or body.strip() == "":
            console.print("[yellow]Empty reply body. Aborting reply.[/yellow]")
            return

    try:
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
        elif choice == "r" and len(choice) == 1:
            continue
        elif not choice:
            continue

        parts = choice.split()
        cmd = parts[0]

        indices: List[int] = []
        action = "unknown"

        if cmd.isdigit():
            indices = [int(cmd)]
            action = "read"
        elif len(parts) > 1:
            action = cmd
            for p in parts[1:]:
                if p.isdigit():
                    indices.append(int(p))

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
        with console.status("[bold green]Reading from stdin..."):
            body = sys.stdin.read()
    else:
        body = spawn_editor()

    if not body and not args.reply_to_id and not args.forward_id:
        if not args.yes:
            console.print("[yellow]Warning: Sending email with empty body.[/yellow]")

    sender = args.from_address if args.from_address else DEFAULT_FROM

    if not args.yes:
        cc_list = list(args.cc) if args.cc else []
        if "forsythc@ucr.edu" not in cc_list:
            cc_list.append("forsythc@ucr.edu")

        preview_lines = [
            f"[bold cyan]From:[/bold cyan]        {sender}",
            f"[bold cyan]To:[/bold cyan]          {', '.join(args.recipients)}",
        ]
        if args.subject:
            preview_lines.append(f"[bold cyan]Subject:[/bold cyan]     {args.subject}")
        if cc_list:
            preview_lines.append(
                f"[bold cyan]Cc:[/bold cyan]          {', '.join(cc_list)}"
            )
        if args.bcc:
            preview_lines.append(
                f"[bold cyan]Bcc:[/bold cyan]         {', '.join(args.bcc)}"
            )
        if args.attach:
            preview_lines.append(
                f"[bold cyan]Attachments:[/bold cyan] {', '.join(args.attach)}"
            )

        preview_lines.append("\n[bold underline]Body Content Preview:[/bold underline]")
        preview_lines.append(body if body else "[dim](Empty body)[/dim]")

        console.print(
            Panel(
                "\n".join(preview_lines),
                title="[bold yellow]✉️ Outbound Email Draft Preview[/bold yellow]",
                border_style="yellow",
                expand=False,
            )
        )

        if not Confirm.ask("Send this email?"):
            console.print("[yellow]Cancelled sending email.[/yellow]")
            return

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


def cmd_drafts(args: argparse.Namespace) -> None:
    client = get_client()
    if args.draft_action in ["list", "ls"]:
        count = getattr(args, "count", 10)
        with console.status("[bold green]Fetching drafts..."):
            drafts = client.list_drafts(max_results=count)
        if not drafts:
            console.print("[yellow]No drafts found.[/yellow]")
            return
        table = Table(title="Gmail Drafts")
        table.add_column("Draft ID", style="cyan", no_wrap=True)
        table.add_column("Subject", style="white")
        table.add_column("From/Sender", style="green")
        for d in drafts:
            details = d["details"]
            subj = details.subject if details else "(Unknown)"
            sender = details.sender if details else "(Unknown)"
            table.add_row(d["id"], subj[:60], sender[:40])
        console.print(table)

    elif args.draft_action in ["create", "write"]:
        body = ""
        if args.input_file:
            with open(args.input_file, "r") as f:
                body = f.read()
        elif args.body:
            body = args.body
        elif not sys.stdin.isatty():
            with console.status("[bold green]Reading from stdin..."):
                body = sys.stdin.read()
        else:
            body = spawn_editor()

        sender = args.from_address if args.from_address else DEFAULT_FROM

        with console.status(f"[bold green]Creating draft from {sender}..."):
            draft_id = client.create_draft(
                recipients=args.recipients,
                subject=args.subject if args.subject else "",
                body=body,
                cc=args.cc,
                bcc=args.bcc,
                attachments=args.attach,
                from_address=sender,
            )
        console.print(
            f"[bold green]Draft created successfully! ID: {draft_id}[/bold green]"
        )

    elif args.draft_action == "send":
        with console.status("[bold green]Fetching draft details..."):
            drafts = client.list_drafts(max_results=50)
            target_draft = None
            for d in drafts:
                if d["id"] == args.id:
                    target_draft = d
                    break

        if not target_draft:
            console.print(f"[red]Draft with ID {args.id} not found.[/red]")
            return

        details = target_draft["details"]

        if not args.yes:
            preview_lines = [
                f"[bold cyan]Draft ID:[/bold cyan]    {args.id}",
            ]
            if details:
                preview_lines.extend(
                    [
                        f"[bold cyan]From:[/bold cyan]        {details.sender}",
                        f"[bold cyan]Subject:[/bold cyan]     {details.subject}",
                        "\n[bold underline]Body Content Preview:[/bold underline]",
                        details.body if details.body else "[dim](Empty body)[/dim]",
                    ]
                )
            else:
                preview_lines.append("[dim]No details available for preview.[/dim]")

            console.print(
                Panel(
                    "\n".join(preview_lines),
                    title="[bold yellow]✉️ Draft Send Preview[/bold yellow]",
                    border_style="yellow",
                    expand=False,
                )
            )

            if not Confirm.ask("Send this draft?"):
                console.print("[yellow]Cancelled draft sending.[/yellow]")
                return

        with console.status(f"[bold green]Sending draft {args.id}..."):
            sent_msg_id = client.send_draft(args.id)
        console.print(
            f"[bold green]Draft sent successfully! Message ID: {sent_msg_id}[/bold green]"
        )


def cmd_labels(args: argparse.Namespace) -> None:
    client = get_client()
    if args.label_action in ["list", "ls"]:
        with console.status("[bold green]Fetching labels..."):
            labels = client.list_labels()
        if not labels:
            console.print("[yellow]No labels found.[/yellow]")
            return
        table = Table(title="Gmail Labels")
        table.add_column("Label ID", style="cyan", no_wrap=True)
        table.add_column("Name", style="white")
        table.add_column("Type", style="magenta")
        for lbl in labels:
            table.add_row(lbl["id"], lbl["name"], lbl["type"])
        console.print(table)

    elif args.label_action == "create":
        with console.status(f"[bold green]Creating label '{args.name}'..."):
            label_id = client.create_label(args.name)
        console.print(
            f"[bold green]Label '{args.name}' created successfully! ID: {label_id}[/bold green]"
        )

    elif args.label_action == "add":
        with console.status(
            f"[bold green]Adding label '{args.name}' to message {args.msg_id}..."
        ):
            client.add_label_to_email(args.msg_id, args.name)
        console.print(
            f"[bold green]Label '{args.name}' added successfully to message {args.msg_id}.[/bold green]"
        )

    elif args.label_action == "remove":
        with console.status(
            f"[bold green]Removing label '{args.name}' from message {args.msg_id}..."
        ):
            client.remove_label_from_email(args.msg_id, args.name)
        console.print(
            f"[bold green]Label '{args.name}' removed successfully from message {args.msg_id}.[/bold green]"
        )


def cmd_attachments(args: argparse.Namespace) -> None:
    client = get_client()
    if args.attach_action in ["download", "get"]:
        with console.status(
            f"[bold green]Downloading attachments from message {args.msg_id}..."
        ):
            saved_paths = client.download_attachments(
                args.msg_id, output_dir=args.output_dir
            )
        if not saved_paths:
            console.print("[yellow]No attachments found in this message.[/yellow]")
        else:
            console.print(
                f"[bold green]Successfully downloaded {len(saved_paths)} attachments:[/bold green]"
            )
            for p in saved_paths:
                console.print(f" - {p}")


def cmd_thread(args: argparse.Namespace) -> None:
    client = get_client()
    if args.thread_action in ["show", "view"]:
        with console.status(f"[bold green]Fetching thread {args.thread_id}..."):
            emails = client.get_thread_details(args.thread_id)
        if not emails:
            console.print(
                f"[yellow]No messages found in thread {args.thread_id}.[/yellow]"
            )
            return

        console.print(
            f"\n[bold magenta]Thread Conversation (ID: {args.thread_id})[/bold magenta]"
        )
        console.print(f"Total messages: {len(emails)}\n")

        for idx, email in enumerate(emails, 1):
            console.print(
                Panel(
                    f"[bold green]From:[/bold green]    {email.sender}\n"
                    f"[bold green]Date:[/bold green]    {email.date}\n"
                    f"[bold green]Subject:[/bold green] {email.subject}\n\n"
                    f"{email.body}",
                    title=f"Message #{idx} (ID: {email.id})",
                    border_style="cyan" if idx % 2 == 0 else "blue",
                    expand=False,
                )
            )


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
    parser_list.add_argument(
        "--json", action="store_true", help="Output in JSON format"
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
    parser_show.add_argument(
        "--json", action="store_true", help="Output in JSON format"
    )
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
        "--yes", "-y", action="store_true", help="Skip confirmation"
    )
    parser_send.set_defaults(func=cmd_send)

    # DRAFTS
    parser_drafts = subparsers.add_parser("drafts", help="Manage email drafts")
    draft_subparsers = parser_drafts.add_subparsers(
        dest="draft_action", required=True, help="Draft action"
    )

    dp_list = draft_subparsers.add_parser(
        "list", help="List current drafts", aliases=["ls"]
    )
    dp_list.add_argument(
        "count", type=int, nargs="?", default=10, help="Number of drafts to list"
    )

    dp_create = draft_subparsers.add_parser(
        "create", help="Create a new draft", aliases=["write"]
    )
    dp_create.add_argument(
        "--to", dest="recipients", nargs="+", required=True, help="Recipient(s)"
    )
    dp_create.add_argument("--subject", "-s", help="Subject line")
    dp_create.add_argument("--body", "-b", help="Body text")
    dp_create.add_argument(
        "--file", "-f", dest="input_file", help="File containing body text"
    )
    dp_create.add_argument("--from", "-F", dest="from_address", help="Sender address")
    dp_create.add_argument("--attach", "-a", nargs="*", help="Attachments")
    dp_create.add_argument("--cc", nargs="*", help="CC recipients")
    dp_create.add_argument("--bcc", nargs="*", help="BCC recipients")

    dp_send = draft_subparsers.add_parser("send", help="Send an existing draft")
    dp_send.add_argument("id", help="Draft ID to send")
    dp_send.add_argument("--yes", "-y", action="store_true", help="Skip confirmation")

    parser_drafts.set_defaults(func=cmd_drafts)

    # LABELS
    parser_labels = subparsers.add_parser("labels", help="Manage labels")
    label_subparsers = parser_labels.add_subparsers(
        dest="label_action", required=True, help="Label action"
    )

    label_subparsers.add_parser("list", help="List all labels", aliases=["ls"])

    lp_create = label_subparsers.add_parser("create", help="Create a new label")
    lp_create.add_argument("name", help="Name of the label")

    lp_add = label_subparsers.add_parser("add", help="Add a label to a message")
    lp_add.add_argument("msg_id", help="Message ID")
    lp_add.add_argument("name", help="Label name")

    lp_remove = label_subparsers.add_parser(
        "remove", help="Remove a label from a message"
    )
    lp_remove.add_argument("msg_id", help="Message ID")
    lp_remove.add_argument("name", help="Label name")

    parser_labels.set_defaults(func=cmd_labels)

    # ATTACHMENTS
    parser_attachments = subparsers.add_parser("attachments", help="Manage attachments")
    attach_subparsers = parser_attachments.add_subparsers(
        dest="attach_action", required=True, help="Attachment action"
    )

    ap_download = attach_subparsers.add_parser(
        "download", help="Download attachments from an email", aliases=["get"]
    )
    ap_download.add_argument("msg_id", help="Message ID")
    ap_download.add_argument("--output-dir", "-o", default=".", help="Output directory")

    parser_attachments.set_defaults(func=cmd_attachments)

    # THREAD
    parser_thread = subparsers.add_parser("thread", help="View conversation threads")
    thread_subparsers = parser_thread.add_subparsers(
        dest="thread_action", required=True, help="Thread action"
    )

    tp_show = thread_subparsers.add_parser(
        "show", help="Show all emails in a thread", aliases=["view"]
    )
    tp_show.add_argument("thread_id", help="Thread ID")

    parser_thread.set_defaults(func=cmd_thread)

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
