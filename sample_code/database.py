"""Simulated database layer for the e-commerce sample."""

import json
import os

DB_FILE = ".data/ecommerce_db.json"


def _load() -> dict:
    if not os.path.exists(DB_FILE):
        return {"orders": {}, "products": {}, "users": {}}
    with open(DB_FILE) as f:
        return json.load(f)


def _save(data: dict):
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=2)


def get_order(order_id: str) -> dict | None:
    return _load()["orders"].get(order_id)


def save_order(order: dict):
    db = _load()
    db["orders"][order["id"]] = order
    _save(db)


def update_order_status(order_id: str, status: str):
    db = _load()
    if order_id in db["orders"]:
        db["orders"][order_id]["status"] = status
        _save(db)


def get_product(product_id: str) -> dict | None:
    return _load()["products"].get(product_id)


def update_product_stock(product_id: str, quantity: int):
    db = _load()
    if product_id in db["products"]:
        db["products"][product_id]["stock"] = quantity
        _save(db)


def get_user(user_id: str) -> dict | None:
    return _load()["users"].get(user_id)
