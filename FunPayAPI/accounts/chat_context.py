from bs4 import BeautifulSoup

from FunPayAPI.accounts.constants import (
    CHAT_MEMBER_INVALID,
    CHAT_NOT_FOUND,
    CHAT_PLACEHOLDER_NAMES,
)


def chat_page_details(parser: BeautifulSoup):
    header = parser.select_one(".chat-header .media-user-name a")
    name = header.get_text(strip=True) if header else None
    if not name or name in CHAT_PLACEHOLDER_NAMES:
        raise ValueError(CHAT_NOT_FOUND)
    panel = parser.select_one("div.param-item.chat-panel a[href]")
    return name, panel.get_text() if panel else None, panel["href"] if panel else None


def private_chat_member(account_id, name: str) -> int:
    members = name.split("-")
    if len(members) != 3 or members[0] != "users":
        raise ValueError(CHAT_MEMBER_INVALID)
    identifiers = members[1:]
    if len(set(identifiers)) != 2:
        raise ValueError(CHAT_MEMBER_INVALID)
    if not all(value.isascii() and value.isdecimal() for value in identifiers):
        raise ValueError(CHAT_MEMBER_INVALID)
    if str(account_id) not in identifiers:
        raise ValueError(CHAT_MEMBER_INVALID)
    identifiers.remove(str(account_id))
    return int(identifiers[0])


def history_context(account, node: dict, name: str | None):
    if node["silent"]:
        return None, name
    member_id = private_chat_member(account.id, node["name"])
    if name:
        return member_id, name
    shortcut = account.get_chat_by_id(node["id"])
    return member_id, shortcut.name if shortcut else None


def parse_history_response(account, data: dict, name: str | None, from_id: int):
    chat = data.get("chat")
    if not chat or not chat.get("messages"):
        return []
    node = chat["node"]
    member_id, name = history_context(account, node, name)
    return account._Account__parse_messages(
        chat["messages"], node["id"], member_id, name, from_id, not node["silent"]
    )


def result_keys(identifier, requested: set) -> set:
    if isinstance(identifier, int) or (
        isinstance(identifier, str) and identifier.isascii() and identifier.isdecimal()
    ):
        return {int(identifier), str(identifier)} & requested
    return {identifier} & requested


def node_history(account, obj, chats_data, result_id):
    node = obj["data"]["node"]
    name = chats_data.get(result_id) if isinstance(chats_data, dict) else None
    member_id, name = history_context(account, node, name)
    if node["silent"]:
        name = None
    return account._Account__parse_messages(
        obj["data"]["messages"],
        node["id"],
        member_id,
        name,
        is_private=not node["silent"],
        tag=obj["tag"],
    )


def parse_histories(account, chats_data, objects):
    result = {}
    requested = set(chats_data)
    for obj in objects:
        if obj.get("type") != "chat_node":
            continue
        if not obj.get("data"):
            result.update({key: [] for key in result_keys(obj.get("id"), requested)})
            continue
        node = obj["data"]["node"]
        matching = result_keys(node["id"], requested) | ({node["name"]} & requested)
        for key in matching:
            result[key] = node_history(account, obj, chats_data, key)
    return result
