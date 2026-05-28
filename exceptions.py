"""Exceptions raised by the simple_email package."""


class SimpleEmailError(Exception):
    """Base exception for all simple_email failures."""


class ConfigurationError(SimpleEmailError):
    """Raised when required client settings are missing or invalid."""


class MessageBuildError(SimpleEmailError):
    """Raised when a message cannot be created."""


class AttachmentError(MessageBuildError):
    """Raised when an attachment cannot be read."""


class SMTPConnectionError(SimpleEmailError):
    """Raised when an SMTP connection cannot be established."""


class SMTPAuthenticationError(SimpleEmailError):
    """Raised when SMTP authentication fails."""


class SMTPSendError(SimpleEmailError):
    """Raised when SMTP accepts the connection but sending fails."""


class IMAPConnectionError(SimpleEmailError):
    """Raised when an IMAP connection cannot be established."""


class IMAPAuthenticationError(SimpleEmailError):
    """Raised when IMAP authentication fails."""


class IMAPFolderError(SimpleEmailError):
    """Raised when an IMAP folder cannot be found, selected, or created."""


class IMAPAppendError(SimpleEmailError):
    """Raised when a message cannot be appended to an IMAP folder."""
