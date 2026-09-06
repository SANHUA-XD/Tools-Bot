from Nobara.database import blocked_chats_collection


async def block_chat(chat_id: int):
    """Blacklist a chat - the bot will refuse to stay in / auto-leave it."""
    await blocked_chats_collection.update_one(
        {"chat_id": chat_id},
        {"$set": {"chat_id": chat_id}},
        upsert=True
    )


async def unblock_chat(chat_id: int):
    await blocked_chats_collection.delete_one({"chat_id": chat_id})


async def is_chat_blocked(chat_id: int) -> bool:
    doc = await blocked_chats_collection.find_one({"chat_id": chat_id})
    return doc is not None


async def get_all_blocked_chats():
    return await blocked_chats_collection.find().to_list(None)
