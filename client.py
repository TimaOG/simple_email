"""Small SMTP/IMAP email client with IMAP modified UTF-7 folder support."""

import imaplib
import mimetypes
import smtplib
import ssl
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional, Sequence

from . import imap_utf7
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
)


class SimpleEmail:
    """Reusable SMTP/IMAP client.

    Public methods return ``None`` on success and raise a typed exception on failure.
    This makes the package easy to copy into another project without coupling it to
    a particular result-dict format.
    """

    def __init__(
        self,
        email_address: str,
        smtp_server: Optional[str] = None,
        login_smtp: Optional[str] = None,
        login_imap: Optional[str] = None,
        password_smtp: Optional[str] = None,
        password_imap: Optional[str] = None,
        smtp_port: Optional[int] = None,
        imap_server: Optional[str] = None,
        imap_port: Optional[int] = None,
        timeout: float = 10.0,
        use_ssl_smtp: bool = True,
        use_ssl_imap: bool = True,
    ):
        self.email_address = self._required_text(email_address, "email_address")
        self.login_smtp = login_smtp
        self.login_imap = login_imap
        self.password_smtp = password_smtp
        self.password_imap = password_imap
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port if smtp_port is not None else (465 if use_ssl_smtp else 25)
        self.imap_server = imap_server
        self.imap_port = imap_port if imap_port is not None else (993 if use_ssl_imap else 143)
        self.timeout = timeout
        self.use_ssl_smtp = use_ssl_smtp
        self.use_ssl_imap = use_ssl_imap

        if self.timeout <= 0:
            raise ConfigurationError("timeout must be greater than zero")

    @staticmethod
    def _required_text(value: Optional[str], field_name: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ConfigurationError(f"{field_name} is required")
        return value.strip()

    @staticmethod
    def _ssl_context():
        try:
            import certifi

            return ssl.create_default_context(cafile=certifi.where())
        except Exception:
            return ssl.create_default_context()

    def _create_message(
        self,
        to_address: str,
        subject: str,
        body: str,
        is_html: bool = False,
        attachments: Optional[Sequence[str]] = None,
    ) -> MIMEMultipart:
        """Create a MIME message ready for SMTP send or IMAP append."""
        to_address = self._required_text(to_address, "to_address")
        subject = self._required_text(subject, "subject")
        if body is None:
            raise MessageBuildError("body is required")

        try:
            msg = MIMEMultipart()
            msg["From"] = self.email_address
            msg["To"] = to_address
            msg["Subject"] = subject

            subtype = "html" if is_html else "plain"
            msg.attach(
                MIMEText(
                    str(body).replace("\n", "<br>") if is_html else str(body), subtype, "utf-8"
                )
            )
            self._attach_files(msg, attachments or [])
            return msg
        except MessageBuildError:
            raise
        except Exception as exc:
            raise MessageBuildError(f"Failed to build email message: {exc}") from exc

    def _attach_files(self, msg: MIMEMultipart, attachments: Sequence[str]) -> None:
        for file_path in attachments:
            path = Path(file_path)
            if not path.is_file():
                raise AttachmentError(f"Attachment not found: {path}")

            content_type, _ = mimetypes.guess_type(path.name)
            maintype, subtype = (content_type or "application/octet-stream").split("/", 1)

            try:
                with path.open("rb") as file:
                    part = MIMEBase(maintype, subtype)
                    part.set_payload(file.read())
            except OSError as exc:
                raise AttachmentError(f"Cannot read attachment {path}: {exc}") from exc

            encoders.encode_base64(part)
            part.add_header("Content-Disposition", "attachment", filename=path.name)
            msg.attach(part)

    def _connect_smtp(self):
        if not self.smtp_server:
            raise ConfigurationError("smtp_server is required for sending email")

        ssl_context = self._ssl_context() if self.use_ssl_smtp else None
        server = None

        try:
            if self.use_ssl_smtp and self.smtp_port == 465:
                server = smtplib.SMTP_SSL(
                    self.smtp_server,
                    self.smtp_port,
                    context=ssl_context,
                    timeout=self.timeout,
                )
            else:
                server = smtplib.SMTP(
                    self.smtp_server,
                    self.smtp_port,
                    timeout=self.timeout,
                )
                if self.use_ssl_smtp:
                    server.starttls(context=ssl_context)

            if self.password_smtp:
                server.login(self.login_smtp or self.email_address, self.password_smtp)
            return server
        except (smtplib.SMTPAuthenticationError, UnicodeEncodeError) as exc:
            self._disconnect_smtp(server)
            raise SMTPAuthenticationError("SMTP authentication failed") from exc
        except (OSError, TimeoutError, smtplib.SMTPConnectError) as exc:
            self._disconnect_smtp(server)
            raise SMTPConnectionError(f"Cannot connect to SMTP server {self.smtp_server}") from exc
        except smtplib.SMTPException as exc:
            self._disconnect_smtp(server)
            raise SMTPConnectionError(f"SMTP connection failed: {exc}") from exc

    def _connect_imap(self):
        if not self.imap_server:
            raise ConfigurationError("imap_server is required for IMAP operations")

        ssl_context = self._ssl_context() if self.use_ssl_imap else None
        imap = None

        try:
            if self.use_ssl_imap and self.imap_port == 993:
                imap = imaplib.IMAP4_SSL(
                    self.imap_server,
                    self.imap_port,
                    ssl_context=ssl_context,
                )
            else:
                imap = imaplib.IMAP4(self.imap_server, self.imap_port)
                if self.use_ssl_imap:
                    imap.starttls(ssl_context)

            if self.password_imap:
                imap.login(self.login_imap or self.email_address, self.password_imap)
            return imap
        except UnicodeEncodeError as exc:
            self._disconnect_imap(imap, selected=False)
            raise IMAPAuthenticationError("IMAP authentication failed") from exc
        except imaplib.IMAP4.error as exc:
            self._disconnect_imap(imap, selected=False)
            error_text = str(exc).lower()
            if any(token in error_text for token in ("login", "auth", "authentication", "failed")):
                raise IMAPAuthenticationError("IMAP authentication failed") from exc
            raise IMAPConnectionError(f"IMAP connection failed: {exc}") from exc
        except (OSError, TimeoutError) as exc:
            self._disconnect_imap(imap, selected=False)
            raise IMAPConnectionError(f"Cannot connect to IMAP server {self.imap_server}") from exc

    @staticmethod
    def _encode_mailbox_arg(folder_name: str) -> bytes:
        encoded = imap_utf7.encode(SimpleEmail._required_text(folder_name, "folder_name"))
        return b'"' + encoded.replace(b"\\", b"\\\\").replace(b'"', b'\\"') + b'"'

    @staticmethod
    def _extract_mailbox_name(list_item) -> Optional[str]:
        if isinstance(list_item, str):
            list_item = list_item.encode("utf-8")
        if not isinstance(list_item, bytes):
            return None

        list_item = list_item.strip()
        if not list_item:
            return None

        if list_item.endswith(b'"'):
            i = len(list_item) - 2
            while i >= 0:
                if list_item[i] == ord('"') and (i == 0 or list_item[i - 1] != ord("\\")):
                    return imap_utf7.decode(list_item[i + 1 : -1].replace(b'\\"', b'"'))
                i -= 1

        mailbox = list_item.rsplit(b" ", 1)[-1]
        return imap_utf7.decode(mailbox.strip(b'"'))

    def _folder_exists(self, imap, folder_name: str) -> bool:
        status, folders = imap.list()
        if status != "OK":
            raise IMAPFolderError(f"Cannot list IMAP folders: {folders}")

        for item in folders or []:
            if self._extract_mailbox_name(item) == folder_name:
                return True
        return False

    def _ensure_folder_selected(self, imap, folder_name: str) -> bytes:
        folder_arg = self._encode_mailbox_arg(folder_name)

        if not self._folder_exists(imap, folder_name):
            status, response = imap.create(folder_arg)
            if status != "OK":
                raise IMAPFolderError(f"Cannot create IMAP folder '{folder_name}': {response}")

        status, response = imap.select(folder_arg)
        if status != "OK":
            raise IMAPFolderError(f"Cannot select IMAP folder '{folder_name}': {response}")
        return folder_arg

    def _append_to_folder(self, msg: MIMEMultipart, folder_name: str, flags: str = "") -> None:
        imap = self._connect_imap()
        selected = False
        try:
            folder_arg = self._ensure_folder_selected(imap, folder_name)
            selected = True
            status, response = imap.append(folder_arg, flags, None, msg.as_bytes())
            if status != "OK":
                raise IMAPAppendError(f"Cannot append email to '{folder_name}': {response}")
        finally:
            self._disconnect_imap(imap, selected)

    @staticmethod
    def _disconnect_imap(imap, selected: bool) -> None:
        if imap is None:
            return
        try:
            if selected:
                imap.close()
        except imaplib.IMAP4.error:
            pass
        finally:
            try:
                imap.logout()
            except imaplib.IMAP4.error:
                pass

    @staticmethod
    def _disconnect_smtp(server) -> None:
        if server is None:
            return
        try:
            server.quit()
        except (OSError, smtplib.SMTPException):
            pass

    def send_email(
        self,
        to_address: str,
        subject: str,
        body: str,
        is_html: bool = False,
        attachments: Optional[Sequence[str]] = None,
    ) -> None:
        """Send a message via SMTP.

        Raises:
            ConfigurationError, MessageBuildError, AttachmentError,
            SMTPAuthenticationError, SMTPConnectionError, SMTPSendError.
        """
        msg = self._create_message(to_address, subject, body, is_html, attachments)
        try:
            with self._connect_smtp() as server:
                server.send_message(msg)
        except (SMTPAuthenticationError, SMTPConnectionError):
            raise
        except smtplib.SMTPException as exc:
            raise SMTPSendError(f"SMTP send failed: {exc}") from exc
        except OSError as exc:
            raise SMTPSendError(f"SMTP socket error: {exc}") from exc

    def save_to_folder_by_name(
        self,
        to_address: str,
        subject: str,
        body: str,
        folder_name: str,
        flags: str = "",
        is_html: bool = False,
        attachments: Optional[Sequence[str]] = None,
    ) -> None:
        """Save a message to an IMAP folder, creating the folder if needed.

        Folder names are encoded with IMAP modified UTF-7, so non-ASCII names like
        ``Черновики`` and ``Отправленные`` are safe.
        """
        msg = self._create_message(to_address, subject, body, is_html, attachments)
        self._append_to_folder(msg, folder_name, flags)

    def list_folders(self) -> list[str]:
        """Return all IMAP folders visible to the authenticated user.

        Returned folder names are decoded from IMAP modified UTF-7 and can be
        passed back to ``save_to_folder_by_name`` as ``folder_name``.
        """
        imap = self._connect_imap()
        try:
            status, folders = imap.list()
            if status != "OK":
                raise IMAPFolderError(f"Cannot list IMAP folders: {folders}")

            result = []
            for item in folders or []:
                folder_name = self._extract_mailbox_name(item)
                if folder_name:
                    result.append(folder_name)
            return result
        finally:
            self._disconnect_imap(imap, selected=False)

    def save_to_folde_by_name(self, *args, **kwargs) -> None:
        """Backward-compatible alias for the historical misspelled method name."""
        self.save_to_folder_by_name(*args, **kwargs)
