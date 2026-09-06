from datetime import datetime, timezone
from Nobara.database import sticker_packs_collection


async def add_pack(user_id: int, short_name: str, title: str, kind: str):
    """kind is one of 'static', 'video', 'animated' - packs can't mix types
    on Telegram's side, same restriction @Stickers enforces."""
    await sticker_packs_collection.update_one(
        {"user_id": user_id, "short_name": short_name},
        {
            "$set": {
                "user_id": user_id,
                "short_name": short_name,
                "title": title,
                "kind": kind,
                "created_at": datetime.now(timezone.utc),
            }
        },
        upsert=True,
    )


async def get_packs(user_id: int, kind: str | None = None):
    query = {"user_id": user_id}
    if kind:
        query["kind"] = kind
    cursor = sticker_packs_collection.find(query).sort("created_at", 1)
    return [doc async for doc in cursor]


async def get_pack(user_id: int, short_name: str):
    return await sticker_packs_collection.find_one({"user_id": user_id, "short_name": short_name})


async def delete_pack(user_id: int, short_name: str) -> bool:
    result = await sticker_packs_collection.delete_one({"user_id": user_id, "short_name": short_name})
    return result.deleted_count > 0
