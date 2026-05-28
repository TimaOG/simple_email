# simple_email

`simple_email` is a small copy-and-use SMTP/IMAP email client for Python projects.
It can:

- send email through SMTP;
- save messages to IMAP folders;
- create an IMAP folder before saving if it does not exist;
- handle non-ASCII IMAP folder names through IMAP modified UTF-7.

The package has no dependency on the parent project. Copy the whole `simple_email`
directory into another project and import `SimpleEmail` from it.

## Public API

Public methods return `None` on success and raise a typed exception on failure.

```python
from simple_email import SimpleEmail
from simple_email import SimpleEmailError

client = SimpleEmail(
    email_address="sender@example.com",
    smtp_server="smtp.example.com",
    smtp_port=465,
    login_smtp="sender@example.com",
    password_smtp="smtp-password",
    imap_server="imap.example.com",
    imap_port=993,
    login_imap="sender@example.com",
    password_imap="imap-password",
)

try:
    client.send_email(
        to_address="recipient@example.com",
        subject="Monthly report",
        body="Hello,\nPlease find the report attached.",
        attachments=["report.xlsx"],
    )
except SimpleEmailError as exc:
    print(f"Email operation failed: {exc}")
```

## Save To IMAP Folder

Use `list_folders()` to inspect the exact IMAP folder names visible to the
authenticated user. This is especially useful for shared mailboxes, where the
folder path can include a server-specific namespace.

```python
for folder in client.list_folders():
    print(folder)
```

Example output:

```text
INBOX
Черновики
Отправленные
Общие ящики/somemail/Черновики
Общие ящики/somemail/Отправленные
```

`save_to_folder_by_name` checks the target folder before saving. If the folder
exists, it selects it. If it does not exist, it creates it and then selects it.

Folder names are encoded with IMAP modified UTF-7, so names such as `Черновики`
and `Отправленные` are safe.

```python
client.save_to_folder_by_name(
    to_address="recipient@example.com",
    subject="Draft message",
    body="Draft body",
    folder_name="Черновики",
    flags="\\Draft",
)

client.save_to_folder_by_name(
    to_address="recipient@example.com",
    subject="Sent copy",
    body="Sent body",
    folder_name="Отправленные",
    flags="\\Seen",
)
```

The historical misspelled method `save_to_folde_by_name` is kept as a
backward-compatible alias. New code should use `save_to_folder_by_name`.

## Exceptions

All package exceptions inherit from `SimpleEmailError`.

- `ConfigurationError`: required settings are missing or invalid.
- `MessageBuildError`: the MIME message cannot be created.
- `AttachmentError`: an attachment does not exist or cannot be read.
- `SMTPConnectionError`: SMTP connection or TLS setup failed.
- `SMTPAuthenticationError`: SMTP login failed.
- `SMTPSendError`: SMTP connected, but message sending failed.
- `IMAPConnectionError`: IMAP connection or TLS setup failed.
- `IMAPAuthenticationError`: IMAP login failed.
- `IMAPFolderError`: an IMAP folder cannot be listed, created, or selected.
- `IMAPAppendError`: a message cannot be appended to the selected IMAP folder.

## Notes

- If `smtp_port` is omitted, the default is `465` with SSL and `25` without SSL.
- If `imap_port` is omitted, the default is `993` with SSL and `143` without SSL.
- If `certifi` is installed, its CA bundle is used for TLS. Otherwise Python's
  default SSL context is used.
- `is_html=True` sends the body as HTML and converts line breaks to `<br>`.
