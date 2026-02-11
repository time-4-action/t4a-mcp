"""Module for cleaning email data."""

import re
import html

__all__ = ["clean_email_body", "clean_emails"]


def clean_email_body(body):
    """Clean email body text by removing HTML tags, normalizing whitespace, and removing common email artifacts.

    Args:
        body (str): Raw email body text (may contain HTML).

    Returns:
        str: Cleaned email body text.
    """
    if not body:
        return ""

    # Decode HTML entities
    text = html.unescape(body)

    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", text)

    # Remove inline CSS
    text = re.sub(r"style=\"[^\"]*\"", "", text)

    # Remove email headers/metadata (common patterns)
    text = re.sub(r"^(From|To|Cc|Subject|Date):.*$", "", text, flags=re.MULTILINE)

    # Remove URLs (optional - uncomment if needed)
    # text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)

    # Remove email addresses (optional - uncomment if needed)
    # text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '', text)

    # Remove excessive newlines (more than 2)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Normalize whitespace
    text = re.sub(r"[ \t]+", " ", text)

    # Remove leading/trailing whitespace from each line
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(line for line in lines if line)

    return text.strip()


def clean_emails(emails):
    """Clean email data by removing empty emails and cleaning body text.

    Args:
        emails (list): List of email dictionaries from loader.

    Returns:
        list: Cleaned emails with cleaned body text, excluding emails with empty bodies.
    """
    cleaned = []

    for email_data in emails:
        # Clean the body
        cleaned_body = clean_email_body(email_data.get("body", ""))

        # Skip emails with no body content
        if not cleaned_body:
            continue

        # Create cleaned email
        cleaned_email = email_data.copy()
        cleaned_email["body"] = cleaned_body

        cleaned.append(cleaned_email)

    return cleaned
