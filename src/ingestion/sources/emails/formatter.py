"""Module for formatting email data for embeddings."""

__all__ = ["create_embedding_text", "create_embeddings_text"]


def create_embedding_text(email_data):
    """Create embedding text for a single email.

    Args:
        email_data (dict): Email dictionary with subject, from, to, date, and body.

    Returns:
        str: Formatted embedding text combining email information.
    """
    parts = [
        f"Subject: {email_data.get('subject', '')}",
        f"From: {email_data.get('from', '')}",
        f"To: {email_data.get('to', '')}",
        f"Date: {email_data.get('date', '')}",
        f"Body:\n{email_data.get('body', '')}",
    ]

    return "\n".join(parts).strip()


def create_embeddings_text(emails):
    """Create embedding text for all emails.

    Args:
        emails (list): List of email dictionaries.

    Returns:
        list: List of embedding text strings, one per email.
    """
    return [create_embedding_text(email_data) for email_data in emails]
