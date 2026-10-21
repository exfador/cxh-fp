import hashlib
from pathlib import Path

from app.updates.store import load_state, write_state, checked_state_path
from Utils.cardinal_tools import get_products_file_lock
from Utils.products_storage import write_products
from Utils.exceptions import NoProductsError, NotEnoughProductsError
from cardinal_core.order_journal import journal


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def stock_path(filename):
    root = checked_state_path(Path.cwd() / "storage/products").resolve()
    path = checked_state_path(root / filename)
    if not path.resolve().is_relative_to(root):
        raise ValueError("Product path escapes storage")
    return path


def reservation_directory(cardinal, path):
    key = digest(path.relative_to(Path("storage/products").resolve()).as_posix())
    return journal(cardinal).root / "storage/core/reservations" / key


def recover(directory, path):
    for receipt in directory.glob("*.json"):
        data = load_state(receipt)
        if data.get("state") != "prepared":
            continue
        current = path.read_text(encoding="utf-8")
        if digest(current) == data["before"]:
            remaining = "\n".join(
                [item for item in current.split("\n") if item][data["amount"] :]
            )
            if digest(remaining) != data["after"]:
                raise ValueError("Stock reservation checksum mismatch")
            write_products(path, remaining)
        elif digest(current) != data["after"]:
            raise ValueError("Stock reservation needs manual reconciliation")
        data["state"] = "reserved"
        write_state(receipt, data)


def reserve(cardinal, order_id, filename, amount):
    if type(amount) is not int or amount < 1:
        raise ValueError("Invalid product amount")
    store = journal(cardinal)
    store.path(order_id)
    path = stock_path(filename)
    directory = reservation_directory(cardinal, path)
    with get_products_file_lock(str(path)):
        recover(directory, path)
        receipt = directory / (store.seller + "-" + str(order_id) + ".json")
        if receipt.exists():
            raise ValueError("Order already has a product reservation")
        content = path.read_text(encoding="utf-8")
        products = [item for item in content.split("\n") if item]
        if not products:
            raise NoProductsError(str(path))
        if len(products) < amount:
            raise NotEnoughProductsError(str(path), len(products), amount)
        selected, left = products[:amount], products[amount:]
        write_state(
            receipt,
            {
                "state": "prepared",
                "before": digest(content),
                "after": digest("\n".join(left)),
                "amount": amount,
                "products": selected,
                "order": str(order_id),
                "seller": store.seller,
            },
        )
        recover(directory, path)
        store.save(order_id, "reserved")
        return selected, len(left)


def receipt_products(cardinal, order_id):
    store = journal(cardinal)
    store.path(order_id)
    result = []
    root = store.root / "storage/core/reservations"
    for path in root.glob("*/" + store.seller + "-" + str(order_id) + ".json"):
        data = load_state(path)
        if data.get("order") == str(order_id) and data.get("seller") == store.seller:
            result.extend(data.get("products", []))
    return result
