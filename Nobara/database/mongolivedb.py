"""
Storage for the "MongoDB Live" keep-alive feature.

Each entry is one Mongo connection string a user wants the bot to
periodically ping so Atlas (or any provider that auto-pauses/deletes
inactive free clusters) never sees it go quiet. The bot only ever issues a
harmless `ping` admin command against it - it never reads, writes, or
touches any of the user's actual collections.

Connection strings are credentials, so they're encrypted at rest with a key
derived from the bot's own secrets (see `_fernet()` below) rather than
stored in plain text. Every query here is scoped by `user_id` so one user
can never see or touch another user's entries.
"""

import base64
import hashlib
from datetime import datetime, timezone

from bson import ObjectId
from cryptography.fernet import Fernet, InvalidToken

from Nobara.database import mongolive_collection
from config import config


def _fernet() -> Fernet:
    key_material = hashlib.sha256(
        f"{config.API_HASH}:{config.BOT_TOKEN}:mongolive".encode()
    ).digest()
    return Fernet(base64.urlsafe_b64encode(key_material))


def encrypt_uri(uri: str) -> str:
    return _fernet().encrypt(uri.encode()).decode()


def decrypt_uri(token: str) -> str:
    return _fernet().decrypt(token.encode()).decode()


async def add_entry(user_id: int, label: str, uri: str, db_name: str) -> str:
    doc = {
        "user_id": user_id,
        "label": label[:64],
        "uri_enc": encrypt_uri(uri),
        "db_name": db_name,
        "added_at": datetime.now(timezone.utc),
        "last_checked": None,
        "last_status": "unknown",
        "last_error": None,
        "fail_count": 0,
    }
    result = await mongolive_collection.insert_one(doc)
    return str(result.inserted_id)


async def get_entries(user_id: int) -> list:
    return [doc async for doc in mongolive_collection.find({"user_id": user_id}).sort("added_at", 1)]


async def get_entry(user_id: int, entry_id: str):
    try:
        oid = ObjectId(entry_id)
    except Exception:
        return None
    return await mongolive_collection.find_one({"_id": oid, "user_id": user_id})


async def count_entries(user_id: int) -> int:
    return await mongolive_collection.count_documents({"user_id": user_id})


async def delete_entry(user_id: int, entry_id: str) -> bool:
    try:
        oid = ObjectId(entry_id)
    except Exception:
        return False
    result = await mongolive_collection.delete_one({"_id": oid, "user_id": user_id})
    return result.deleted_count > 0


async def update_status(entry_id: str, status: str, error: str | None = None) -> None:
    try:
        oid = ObjectId(entry_id)
    except Exception:
        return
    update = {
        "$set": {
            "last_checked": datetime.now(timezone.utc),
            "last_status": status,
            "last_error": error,
        }
    }
    if status == "live":
        update["$set"]["fail_count"] = 0
    else:
        update["$inc"] = {"fail_count": 1}
    await mongolive_collection.update_one({"_id": oid}, update)


async def get_all_entries() -> list:
    """Used only by the background keep-alive job (all users, all entries)."""
    return [doc async for doc in mongolive_collection.find({})]
