## Примеры использования

### 1. Инициализация клиента

```python
from simple_mail import SimpleEmail

client = SimpleEmail(
    email_address="user@example.com",
    smtp_server="smtp.example.com",
    login_smtp="user@example.com",
    password_smtp="your_app_password",
    imap_server="imap.example.com",
    login_imap="user@example.com",
    password_imap="your_app_password",
)
result = client.send_email(
    to_address="recipient@example.com",
    subject="Привет из Python!",
    body="Это тестовое сообщение"
)
client.save_to_folder_by_name(
    to_address="client@example.com",
    subject="Копия коммерческого предложения",
    body="Текст предложения...",
    folder_name="Sent",
    flags="\\Seen"
)

client.save_to_folder_by_name(
    to_address="you@gmail.com",
    subject="Черновик: Приглашение на встречу",
    body="Напоминание: обсудить проект...",
    folder_name="Drafts",
    flags="\\Draft"
)
```