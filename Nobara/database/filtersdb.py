import random
from Nobara.database import filter_collection
from cachetools import TTLCache

# Per-chat filter cache. Filters are read on EVERY group message (hot path),
# so - matching the reference Filter-Bot-Dev's caching approach - we keep
# the whole per-chat document in memory and only hit MongoDB again after a
# write, or after the TTL expires as a safety net.
_doc_cache = TTLCache(maxsize=5000, ttl=300)


def _invalidate(chat_id: int):
    _doc_cache.pop(chat_id, None)


async def _get_doc(chat_id: int) -> dict:
    if chat_id in _doc_cache:
        return _doc_cache[chat_id]
    doc = await filter_collection.find_one({"chat_id": chat_id})
    if not doc:
        doc = {"chat_id": chat_id, "filters": {}}
    _doc_cache[chat_id] = doc
    return doc


async def _get_chat_filters(chat_id: int) -> dict:
    doc = await _get_doc(chat_id)
    return doc.get("filters", {})


# ——————————————————————————————————————————————————————————————
# Core filter CRUD
# ——————————————————————————————————————————————————————————————

async def add_filter(chat_id: int, trigger: str, reply: str, buttons: list, file_id, alerts: list = None):
    """
    Add or update a filter for a specific chat.
    :param trigger: the filter's keyword/trigger (lowercase)
    :param reply: reply text (HTML)
    :param buttons: button rows, see Nobara/helper/filter_buttons.py
    :param file_id: attached media file_id, or None
    :param alerts: list of alert popup strings referenced by the buttons (by index)
    """
    await filter_collection.update_one(
        {"chat_id": chat_id},
        {"$set": {
            f"filters.{trigger}": {
                "reply": reply or "",
                "buttons": buttons or [],
                "file": file_id,
                "alerts": alerts or [],
                "use_count": 0,
                "genre": None,
            }
        }},
        upsert=True
    )
    _invalidate(chat_id)


async def get_filter(chat_id: int, trigger: str):
    data = await _get_chat_filters(chat_id)
    return data.get(trigger)


async def get_filters(chat_id: int):
    """Returns a sorted list of trigger names for a chat."""
    data = await _get_chat_filters(chat_id)
    return sorted(data.keys())


async def count_filters(chat_id: int) -> int:
    data = await _get_chat_filters(chat_id)
    return len(data)


async def delete_filter(chat_id: int, trigger: str) -> bool:
    data = await _get_chat_filters(chat_id)
    if trigger not in data:
        return False
    await filter_collection.update_one(
        {"chat_id": chat_id},
        {"$unset": {f"filters.{trigger}": ""}}
    )
    _invalidate(chat_id)
    return True


async def remove_all_filters(chat_id: int) -> bool:
    result = await filter_collection.update_one(
        {"chat_id": chat_id},
        {"$set": {"filters": {}}}
    )
    _invalidate(chat_id)
    return result.modified_count > 0


async def match_filter(chat_id: int, normalized_text: str, normalize_fn):
    """
    Finds the best (longest) filter trigger contained in `normalized_text`.
    Substring matching (not just whole words) so multi-word triggers work,
    and the longest match wins so a more specific trigger beats a shorter one.
    """
    data = await _get_chat_filters(chat_id)
    if not data:
        return None
    for trigger in sorted(data.keys(), key=len, reverse=True):
        if normalize_fn(trigger) in normalized_text:
            return trigger, data[trigger]
    return None


async def increment_filter_count(chat_id: int, trigger: str):
    await filter_collection.update_one(
        {"chat_id": chat_id, f"filters.{trigger}": {"$exists": True}},
        {"$inc": {f"filters.{trigger}.use_count": 1}}
    )
    # best-effort cache patch so /topfilters reflects it without waiting for TTL
    doc = _doc_cache.get(chat_id)
    if doc and trigger in doc.get("filters", {}):
        doc["filters"][trigger]["use_count"] = doc["filters"][trigger].get("use_count", 0) + 1


async def get_top_filters(chat_id: int, limit: int = 15):
    data = await _get_chat_filters(chat_id)
    ranked = sorted(data.items(), key=lambda kv: kv[1].get("use_count", 0), reverse=True)
    return [{"text": trigger, "use_count": resp.get("use_count", 0)} for trigger, resp in ranked[:limit] if resp.get("use_count", 0) > 0]


async def get_alert_text(chat_id: int, trigger: str, index: int):
    resp = await get_filter(chat_id, trigger)
    if not resp:
        return None
    alerts = resp.get("alerts") or []
    if 0 <= index < len(alerts):
        return alerts[index]
    return None


# ——————————————————————————————————————————————————————————————
# Auto-delete settings
# ——————————————————————————————————————————————————————————————

async def set_autodelete_settings(chat_id: int, enabled: bool, seconds: int):
    await filter_collection.update_one(
        {"chat_id": chat_id},
        {"$set": {"autodelete": {"enabled": enabled, "seconds": seconds}}},
        upsert=True
    )
    _invalidate(chat_id)


async def get_autodelete_settings(chat_id: int):
    doc = await _get_doc(chat_id)
    settings = doc.get("autodelete", {})
    return settings.get("enabled", False), settings.get("seconds", 0)


# ——————————————————————————————————————————————————————————————
# Clone system
# ——————————————————————————————————————————————————————————————

async def set_clone_status(chat_id: int, enabled: bool):
    await filter_collection.update_one(
        {"chat_id": chat_id},
        {"$set": {"clone_enabled": enabled}},
        upsert=True
    )
    _invalidate(chat_id)


async def get_clone_status(chat_id: int) -> bool:
    doc = await _get_doc(chat_id)
    return doc.get("clone_enabled", False)


async def clone_all_filters(source_chat_id: int, target_chat_id: int):
    source_filters = await _get_chat_filters(source_chat_id)
    if not source_filters:
        return False, 0, []

    target_filters = await _get_chat_filters(target_chat_id)
    copied, skipped = 0, []

    for trigger, response in source_filters.items():
        if trigger in target_filters:
            skipped.append(trigger)
            continue
        await filter_collection.update_one(
            {"chat_id": target_chat_id},
            {"$set": {f"filters.{trigger}": response}},
            upsert=True
        )
        copied += 1

    _invalidate(target_chat_id)
    return True, copied, skipped


async def save_clone_history(source_chat_id: int, target_chat_id: int, target_title: str):
    await filter_collection.update_one(
        {"chat_id": source_chat_id},
        {"$push": {"clone_history": {"target_id": target_chat_id, "title": target_title}}},
        upsert=True
    )
    _invalidate(source_chat_id)


async def get_clone_history(chat_id: int):
    doc = await _get_doc(chat_id)
    return doc.get("clone_history", [])


# ——————————————————————————————————————————————————————————————
# Random / genre-based suggestion mode
# ——————————————————————————————————————————————————————————————

async def set_random_suggest_status(chat_id: int, enabled: bool):
    await filter_collection.update_one(
        {"chat_id": chat_id},
        {"$set": {"suggest_mode": enabled}},
        upsert=True
    )
    _invalidate(chat_id)


async def get_random_suggest_status(chat_id: int) -> bool:
    doc = await _get_doc(chat_id)
    return doc.get("suggest_mode", False)


async def set_filter_genre(chat_id: int, trigger: str, genres: list):
    await filter_collection.update_one(
        {"chat_id": chat_id, f"filters.{trigger}": {"$exists": True}},
        {"$set": {f"filters.{trigger}.genre": genres}}
    )
    _invalidate(chat_id)


async def get_filters_missing_genre(chat_id: int):
    data = await _get_chat_filters(chat_id)
    return [trigger for trigger, resp in data.items() if not resp.get("genre")]


async def get_random_filter(chat_id: int):
    data = await _get_chat_filters(chat_id)
    if not data:
        return None
    trigger = random.choice(list(data.keys()))
    return {**data[trigger], "text": trigger}


async def get_random_filter_by_genre(chat_id: int, genre: str):
    data = await _get_chat_filters(chat_id)
    matches = [
        (trigger, resp) for trigger, resp in data.items()
        if resp.get("genre") and genre in resp["genre"]
    ]
    if not matches:
        return None
    trigger, resp = random.choice(matches)
    return {**resp, "text": trigger}


# ——————————————————————————————————————————————————————————————
# Global stats
# ——————————————————————————————————————————————————————————————

async def get_filter_statistics():
    all_filters = await filter_collection.find({}).to_list(length=None)
    total_chats = len(all_filters)
    total_filters = sum(len(chat.get("filters", {})) for chat in all_filters)
    return {"total_chats": total_chats, "total_filters": total_filters}
