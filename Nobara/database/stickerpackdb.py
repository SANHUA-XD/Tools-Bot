"""
Named sticker pack registry for /newpack + /kang + /mypacks.

Telegram itself has no concept of a "pack you registered but haven't
created yet" - a sticker set only exists once it has at least one sticker
in it (CreateStickerSet requires a non-empty stickers list). So this just
tracks the user's chosen title/short_name ahead of time, and `created`
flips to True the first time /kang successfully calls CreateStickerSet
for it.
"""

from Nobara.database import stickerpack_collection


async def add_pack(user_id: int, short_name: str, title: str, kind: str) -> None:
    await stickerpack_collection.update_one(
        {"user_id": user_id, "short_name": short_name},
        {
            "$set": {
                "user_id": user_id,
                "short_name": short_name,
                "title": title,
                "kind": kind,
                "created": False,
            }
        },
        upsert=True,
    )


async def mark_created(user_id: int, short_name: str) -> None:
    await stickerpack_collection.update_one(
        {"user_id": user_id, "short_name": short_name},
        {"$set": {"created": True}},
    )


async def get_packs(user_id: int, kind: str | None = None) -> list:
    query = {"user_id": user_id}
    if kind:
        query["kind"] = kind
    return [doc async for doc in stickerpack_collection.find(query)]


async def get_pack(user_id: int, short_name: str):
    return await stickerpack_collection.find_one({"user_id": user_id, "short_name": short_name})


async def delete_pack(user_id: int, short_name: str) -> None:
    await stickerpack_collection.delete_one({"user_id": user_id, "short_name": short_name})


async def set_active_pack(user_id: int, short_name: str) -> None:
    doc = await stickerpack_collection.find_one({"user_id": user_id, "short_name": short_name})
    if not doc:
        return
    # Only one active pack per kind (static / video / animated) at a time,
    # since that's what /kang uses to decide where an un-numbered kang goes.
    await stickerpack_collection.update_many(
        {"user_id": user_id, "kind": doc["kind"]}, {"$set": {"active": False}}
    )
    await stickerpack_collection.update_one(
        {"user_id": user_id, "short_name": short_name}, {"$set": {"active": True}}
    )


async def get_active_pack(user_id: int, kind: str):
    return await stickerpack_collection.find_one(
        {"user_id": user_id, "kind": kind, "active": True}
    )
