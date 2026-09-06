from Nobara.database import afk_collection

# In-memory set of currently-AFK user_ids. AFK status is checked on EVERY
# single message in every chat (to detect mentions/replies to AFK users,
# and to auto-clear AFK when they come back) - hitting MongoDB for that on
# every message added real, noticeable latency to the whole bot. This set
# lets both hot-path checks in Nobara/modules/afk.py be a plain in-memory
# lookup instead, only touching the DB for the (rare) cases where someone
# actually is AFK.
_afk_user_ids: set[int] = set()
_cache_loaded = False


async def _ensure_cache_loaded():
    global _cache_loaded
    if _cache_loaded:
        return
    async for doc in afk_collection.find({}, {"user_id": 1}):
        _afk_user_ids.add(doc["user_id"])
    _cache_loaded = True


async def is_afk_cached(user_id: int) -> bool:
    """Fast, DB-free check - use this to short-circuit before any DB call."""
    await _ensure_cache_loaded()
    return user_id in _afk_user_ids


async def any_afk_cached() -> bool:
    await _ensure_cache_loaded()
    return bool(_afk_user_ids)


async def set_afk(user_id: int, user_first_name: str, username: str, afk_reason: str, afk_start_time: str , media_id: str = None):
    """Set AFK details for a specific user."""
    await afk_collection.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "user_first_name": user_first_name,
                "username": username,
                "afk_reason": afk_reason,
                "afk_start_time": afk_start_time,
                "media_id": media_id
            }
        },
        upsert=True
    )
    _afk_user_ids.add(user_id)

async def get_afk(user_id: int):
    """Get the AFK details for a specific user."""
    user_data = await afk_collection.find_one({"user_id": user_id})
    return user_data if user_data else None

async def clear_afk(user_id: int):
    """Clear AFK details for a specific user."""
    await afk_collection.delete_one({"user_id": user_id})
    _afk_user_ids.discard(user_id)

async def get_afk_by_username(username: str):
    """Get the AFK details for a specific user by username."""
    user_data = await afk_collection.find_one({"username": username})  # Await the coroutine
    if user_data:
        return {
            "user_id": user_data["user_id"],
            "user_first_name": user_data["user_first_name"],
            "afk_start_time": user_data["afk_start_time"],
            "afk_reason": user_data.get("afk_reason"),
            "media_id": user_data.get("media_id"),
        }
    return None

async def is_user_afk(user_id: int) -> bool:
    """Check if a user is currently AFK."""
    user_data = await afk_collection.find_one({"user_id": user_id})
    return bool(user_data)
