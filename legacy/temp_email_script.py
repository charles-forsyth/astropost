#!/usr/bin/env python3
import argparse
import glob
import subprocess
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="Send emails with content from text files."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be done without sending emails.",
    )
    args = parser.parse_args()

    my_email = "forsythc@ucr.edu"
    files_to_process = glob.glob("/home/chuck/Documents/email_to_*.txt")

    if not files_to_process:
        print("No email text files found in /home/chuck/Documents/")
        return

    for file_path in files_to_process:
        try:
            # Extract recipient name from filename for the subject
            recipient_name = Path(file_path).stem.replace("email_to_", "")
            subject = f"Update for {recipient_name.replace('_', ' ').title()}"

            with open(file_path, "r") as f:
                content = f.read()

            # Wrap the content in <pre> tags for basic HTML formatting
            html_content = f"<html><body><pre>{content}</pre></body></html>"

            email_script = "/home/chuck/Scripts/send_email.py"
            command = ["python3", email_script, my_email, subject, html_content]

            if args.dry_run:
                print(
                    f"DRY RUN: Would send email to '{my_email}' with subject '{subject}' from file '{file_path}'"
                )
            else:
                print(f"Sending email to '{my_email}' with subject '{subject}'...")
                result = subprocess.run(
                    command, check=True, capture_output=True, text=True
                )
                print("Email sent successfully.")
                print(f"Output:\n{result.stdout}")

        except subprocess.CalledProcessError as e:
            print(f"Error sending email for {file_path}:")
            print(f"Return code: {e.returncode}")
            print(f"Output:\n{e.stdout}")
            print(f"Error Output:\n{e.stderr}")
        except Exception as e:
            print(f"An unexpected error occurred while processing {file_path}: {e}")


if __name__ == "__main__":
    main()
