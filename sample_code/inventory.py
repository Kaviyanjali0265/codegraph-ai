"""Inventory management — stock checks, reservations, releases."""

from database import get_product, update_product_stock

# Temporary in-memory reservations
_reservations: dict[str, int] = {}


def check_stock(product_id: str, quantity: int) -> bool:
    product = get_product(product_id)
    if not product:
        return False
    available = product["stock"] - _reservations.get(product_id, 0)
    return available >= quantity


def reserve_item(product_id: str, quantity: int) -> bool:
    if not check_stock(product_id, quantity):
        return False
    _reservations[product_id] = _reservations.get(product_id, 0) + quantity
    return True


def release_item(product_id: str, quantity: int):
    current = _reservations.get(product_id, 0)
    _reservations[product_id] = max(0, current - quantity)


def update_stock(product_id: str, quantity_sold: int):
    product = get_product(product_id)
    if product:
        new_stock = product["stock"] - quantity_sold
        update_product_stock(product_id, new_stock)
        release_item(product_id, quantity_sold)
