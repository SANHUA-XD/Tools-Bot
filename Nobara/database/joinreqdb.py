from Nobara.database import joinreq_collection


async def set_auto_accept(chat_id: int, enabled: bool):
    await joinreq_collection.update_one(
        {"chat_id": chat_id},
        {"$set": {"chat_id": chat_id, "auto_accept": enabled}},
        upsert=True
    )


async def is_auto_accept_enabled(chat_id: int) -> bool:
    doc = await joinreq_collection.find_one({"chat_id": chat_id})
    return bool(doc and doc.get("auto_accept", False))
