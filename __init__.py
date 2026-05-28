from .client import SimpleEmail
from .exceptions import (
    AttachmentError,
    ConfigurationError,
    IMAPAppendError,
    IMAPAuthenticationError,
    IMAPConnectionError,
    IMAPFolderError,
    MessageBuildError,
    SMTPAuthenticationError,
    SMTPConnectionError,
    SMTPSendError,
    SimpleEmailError,
)

__all__ = [
    "SimpleEmail",
    "SimpleEmailError",
    "ConfigurationError",
    "MessageBuildError",
    "AttachmentError",
    "SMTPConnectionError",
    "SMTPAuthenticationError",
    "SMTPSendError",
    "IMAPConnectionError",
    "IMAPAuthenticationError",
    "IMAPFolderError",
    "IMAPAppendError",
]
