import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime


def send_email(subject, body, to_email):
    # Email server configuration
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    smtp_user = "chuck.forsyth@gmail.com"  # Replace with your email
    smtp_password = "Tuckerdog27"  # Replace with your email password

    # Create the email
    msg = MIMEMultipart()
    msg["From"] = smtp_user
    msg["To"] = to_email
    msg["Subject"] = subject

    # Attach the email body
    msg.attach(MIMEText(body, "plain"))

    # Connect to the server and send the email
    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, to_email, msg.as_string())
        server.quit()
        print(f"Email sent to {to_email} successfully!")
    except Exception as e:
        print(f"Failed to send email. Error: {e}")


def generate_report():
    # Generate your daily report here
    # For this example, we'll just create a simple text report
    report = f"Daily Report - {datetime.now().strftime('%Y-%m-%d')}\n\n"
    report += "Everything is running smoothly.\n"
    report += "No issues reported."

    return report


if __name__ == "__main__":
    subject = "Daily Report"
    body = generate_report()
    to_email = "recipient@example.com"  # Replace with the recipient's email

    send_email(subject, body, to_email)
