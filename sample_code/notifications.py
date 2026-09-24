"""Notification system — email, SMS, and combined user alerts."""

from database import get_user


def send_email(to: str, subject: str, body: str) -> bool:
    print(f"[EMAIL] To: {to} | Subject: {subject}")
    return True


def send_sms(phone: str, message: str) -> bool:
    print(f"[SMS] To: {phone} | Message: {message}")
    return True


def notify_user(user_id: str, subject: str, message: str):
    user = get_user(user_id)
    if not user:
        return
    if user.get("email"):
        send_email(user["email"], subject, message)
    if user.get("phone"):
        send_sms(user["phone"], message)


def notify_admin(subject: str, message: str):
    send_email("admin@store.com", subject, message)
    print(f"[ADMIN ALERT] {subject}: {message}")
