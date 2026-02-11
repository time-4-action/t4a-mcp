"""Module for loading emails via IMAP."""
import imaplib
import email
from email.header import decode_header
from datetime import datetime, timedelta

from src.config import GMAIL_EMAIL, GMAIL_APP_PASSWORD, GMAIL_IMAP_SERVER, GMAIL_IMAP_PORT

__all__ = ["get_emails"]


def decode_mime_header(header):
    """Decode MIME encoded email header.

    Args:
        header (str): Email header string that may be MIME encoded.

    Returns:
        str: Decoded header string.
    """
    if header is None:
        return ""

    decoded_parts = decode_header(header)
    decoded_string = ""

    for part, encoding in decoded_parts:
        if isinstance(part, bytes):
            decoded_string += part.decode(encoding or "utf-8", errors="ignore")
        else:
            decoded_string += part

    return decoded_string


def extract_body(msg):
    """Extract email body content.

    Args:
        msg: email.message.Message object.

    Returns:
        str: Email body text (prefers plain text, falls back to HTML).
    """
    body = ""

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition", ""))

            # Skip attachments
            if "attachment" in content_disposition:
                continue

            # Get plain text
            if content_type == "text/plain":
                try:
                    body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                    break  # Prefer plain text
                except Exception:
                    continue

            # Fallback to HTML
            elif content_type == "text/html" and not body:
                try:
                    body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                except Exception:
                    continue
    else:
        # Non-multipart message
        try:
            body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")
        except Exception:
            body = ""

    return body


def get_emails(folder="INBOX", days_back=30, max_emails=100):
    """Fetch emails from Gmail via IMAP.

    Args:
        folder (str): Email folder to read from (default: INBOX).
        days_back (int): Number of days back to fetch emails (default: 30).
        max_emails (int): Maximum number of emails to fetch (default: 100).

    Returns:
        list: List of email dictionaries with keys:
            - message_id: Unique message ID
            - subject: Email subject
            - from: Sender email address
            - to: Recipient email address(es)
            - date: Email date (as string)
            - body: Email body text

    Raises:
        imaplib.IMAP4.error: If IMAP connection or authentication fails.
        Exception: For other errors during email fetching.
    """
    # Connect to Gmail IMAP server
    mail = imaplib.IMAP4_SSL(GMAIL_IMAP_SERVER, GMAIL_IMAP_PORT)

    try:
        # Login
        mail.login(GMAIL_EMAIL, GMAIL_APP_PASSWORD)

        # Select mailbox
        mail.select(folder)

        # Calculate date threshold
        since_date = (datetime.now() - timedelta(days=days_back)).strftime("%d-%b-%Y")

        # Search for emails
        status, messages = mail.search(None, f'SINCE {since_date}')

        if status != "OK":
            raise Exception(f"Failed to search emails: {status}")

        # Get email IDs
        email_ids = messages[0].split()

        # Limit number of emails
        email_ids = email_ids[-max_emails:] if len(email_ids) > max_emails else email_ids

        emails = []

        for email_id in email_ids:
            # Fetch email
            status, msg_data = mail.fetch(email_id, "(RFC822)")

            if status != "OK":
                continue

            # Parse email
            msg = email.message_from_bytes(msg_data[0][1])

            # Extract email data
            email_dict = {
                "message_id": msg.get("Message-ID", ""),
                "subject": decode_mime_header(msg.get("Subject", "")),
                "from": decode_mime_header(msg.get("From", "")),
                "to": decode_mime_header(msg.get("To", "")),
                "date": msg.get("Date", ""),
                "body": extract_body(msg),
            }

            emails.append(email_dict)

        return emails

    finally:
        # Always close and logout
        try:
            mail.close()
            mail.logout()
        except Exception:
            pass
