"""
Модуль для работы с почтой через SMTP и IMAP
Поддерживает работу с аутентификацией и без неё

Все публичные методы возвращают единый формат:
    {"success": bool, "error": str}
    - success=True, error="" — успех
    - success=False, error="описание" — ошибка
"""

import smtplib
import imaplib
import ssl

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from typing import Optional, List
from pathlib import Path


class SimpleEmail:
    """
    Класс для работы с почтовыми клиентами.

    Два основных метода:
        - send_email() — отправить письмо
        - save_to_folde_by_name() — сохранить в папку
    """

    def __init__(
        self,
        email_address: str,
        smtp_server: str,
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
        self.email_address = email_address
        self.login_smtp = login_smtp
        self.login_imap = login_imap
        self.password_smtp = password_smtp
        self.password_imap = password_imap
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.imap_server = imap_server
        self.imap_port = imap_port
        self.timeout = timeout
        self.use_ssl_smtp = use_ssl_smtp
        self.use_ssl_imap = use_ssl_imap

        if self.smtp_port is None:
            self.smtp_port = 465 if use_ssl_smtp else 25
        if self.imap_port is None:
            self.imap_port = 993 if use_ssl_imap else 143

    def _get_ssl_context_imap(self):
        """Создает SSL контекст."""
        if not self.use_ssl_imap:
            return None
        try:
            import certifi

            context = ssl.create_default_context(cafile=certifi.where())
            return context
        except Exception:
            return None

    def _get_ssl_context_smtp(self):
        """Создает SSL контекст."""
        if not self.use_ssl_smtp:
            return None
        try:
            import certifi

            context = ssl.create_default_context(cafile=certifi.where())
            return context
        except Exception:
            return None

    def _create_message(
        self,
        to_address: str,
        subject: str,
        body: str,
        is_html: bool = False,
        attachments: Optional[List[str]] = None,
    ):
        """Создаёт MIME-сообщение."""
        msg = MIMEMultipart()
        msg["From"] = self.email_address
        msg["To"] = to_address
        msg["Subject"] = subject

        if is_html:
            body = body.replace("\n", "<br>")

        msg.attach(MIMEText(body, "html", "utf-8"))

        if attachments:
            for file_path in attachments:
                with open(file_path, "rb") as f:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header(
                        "Content-Disposition",
                        f'attachment; filename="{Path(file_path).name}"',
                    )
                    msg.attach(part)

        return msg

    def _connect_smtp(self):
        """Подключение к SMTP серверу."""
        ssl_context = self._get_ssl_context_smtp()

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
            server.login(self.login_smtp, self.password_smtp)

        return server

    def _connect_imap(self):
        """Подключение к IMAP серверу."""
        ssl_context = self._get_ssl_context_imap()

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
            imap.login(self.login_imap, self.password_imap)
        return imap

    def _save_to_folder(self, message_string: str, folder_name: str, flags: str = ""):
        """Сохранение сообщения в папку IMAP."""
        imap = self._connect_imap()
        try:
            status, _ = imap.select(folder_name)
            if status != "OK":
                imap.create(folder_name)
                imap.select(folder_name)

            imap.append(
                folder_name,
                flags,
                None,
                message_string.encode("utf-8"),
            )
        finally:
            try:
                imap.close()
                imap.logout()
            except Exception:
                pass

    def send_email(
        self,
        to_address: str,
        subject: str,
        body: str,
        is_html: bool = False,
        attachments: Optional[List[str]] = None,
    ) -> dict:
        try:
            msg = self._create_message(to_address, subject, body, is_html, attachments)
            server = self._connect_smtp()
            with server:
                server.send_message(msg)
            return {"success": True, "error": ""}
        except smtplib.SMTPAuthenticationError as e:
            return {"success": False, "error": f"Ошибка аутентификации: {e}"}
        except smtplib.SMTPConnectError as e:
            return {"success": False, "error": f"Не удалось подключиться: {e}"}
        except smtplib.SMTPException as e:
            return {"success": False, "error": f"SMTP ошибка: {e}"}
        except FileNotFoundError as e:
            return {"success": False, "error": f"Файл не найден: {e}"}
        except Exception as e:
            return {"success": False, "error": f"{type(e).__name__}: {e}"}

    def save_to_folde_by_name(
        self,
        to_address: str,
        subject: str,
        body: str,
        folder_name: str,
        flags: str,
        is_html: bool = False,
        attachments: Optional[List[str]] = None,
    ) -> dict:
        if not self.imap_server:
            return {"success": False, "error": "IMAP сервер не настроен"}

        try:
            msg = self._create_message(to_address, subject, body, is_html, attachments)
            message_string = msg.as_string()
            self._save_to_folder(message_string, folder_name, flags=flags)
            return {"success": True, "error": ""}
        except imaplib.IMAP4.error as e:
            return {"success": False, "error": f"IMAP ошибка: {e}"}
        except FileNotFoundError as e:
            return {"success": False, "error": f"Файл не найден: {e}"}
        except Exception as e:
            return {"success": False, "error": f"{type(e).__name__}: {e}"}
