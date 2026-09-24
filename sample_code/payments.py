"""Payment processing — charge, refund, validation."""

import uuid


def validate_payment(card_number: str, amount: float) -> bool:
    if not card_number or len(card_number) < 12:
        return False
    if amount <= 0:
        return False
    return True


def charge_card(card_number: str, amount: float) -> dict:
    if not validate_payment(card_number, amount):
        return {"success": False, "error": "Invalid payment details"}
    transaction_id = str(uuid.uuid4())
    return {"success": True, "transaction_id": transaction_id, "amount": amount}


def refund(transaction_id: str, amount: float) -> dict:
    if not transaction_id:
        return {"success": False, "error": "Missing transaction ID"}
    refund_id = str(uuid.uuid4())
    return {"success": True, "refund_id": refund_id, "amount": amount}


def send_receipt(user_email: str, order_id: str, amount: float) -> bool:
    print(f"Receipt sent to {user_email} for order {order_id}: ${amount}")
    return True
