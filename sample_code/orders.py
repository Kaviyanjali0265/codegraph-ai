"""Order orchestration — the core of the e-commerce flow."""

import uuid
from payments import charge_card, refund, send_receipt
from inventory import check_stock, reserve_item, release_item, update_stock
from notifications import notify_user, notify_admin
from database import save_order, get_order, update_order_status


def place_order(user_id: str, product_id: str, quantity: int, card_number: str) -> dict:
    if not check_stock(product_id, quantity):
        return {"success": False, "error": "Insufficient stock"}

    if not reserve_item(product_id, quantity):
        return {"success": False, "error": "Could not reserve item"}

    amount = quantity * 10.0
    payment = charge_card(card_number, amount)
    if not payment["success"]:
        release_item(product_id, quantity)
        return {"success": False, "error": payment["error"]}

    order_id = str(uuid.uuid4())
    order = {
        "id": order_id,
        "user_id": user_id,
        "product_id": product_id,
        "quantity": quantity,
        "amount": amount,
        "transaction_id": payment["transaction_id"],
        "status": "confirmed",
    }
    save_order(order)
    notify_user(user_id, "Order Confirmed", f"Your order {order_id} is confirmed.")
    return {"success": True, "order_id": order_id}


def cancel_order(order_id: str) -> dict:
    order = get_order(order_id)
    if not order:
        return {"success": False, "error": "Order not found"}
    if order["status"] == "cancelled":
        return {"success": False, "error": "Already cancelled"}

    refund_result = refund(order["transaction_id"], order["amount"])
    if not refund_result["success"]:
        notify_admin("Refund Failed", f"Order {order_id} refund failed.")
        return {"success": False, "error": "Refund failed"}

    release_item(order["product_id"], order["quantity"])
    update_order_status(order_id, "cancelled")
    notify_user(order["user_id"], "Order Cancelled", f"Order {order_id} has been cancelled and refunded.")
    return {"success": True}


def complete_order(order_id: str, user_email: str) -> dict:
    order = get_order(order_id)
    if not order:
        return {"success": False, "error": "Order not found"}

    update_stock(order["product_id"], order["quantity"])
    update_order_status(order_id, "completed")
    send_receipt(user_email, order_id, order["amount"])
    notify_user(order["user_id"], "Order Shipped", f"Your order {order_id} has shipped!")
    return {"success": True}


def get_order_status(order_id: str) -> dict:
    order = get_order(order_id)
    if not order:
        return {"success": False, "error": "Order not found"}
    return {"success": True, "status": order["status"], "order": order}
