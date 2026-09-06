"""
WordSeek persistence layer.

Previously ALL WordSeek state (active games, daily games, auth lists, topic
settings, streaks, and the entire score-event history that powers the
leaderboards) lived only in plain Python dicts inside wordseek.py. That
means every bot restart - which happens often on Heroku (deploys, dyno
cycling, crashes) - silently wiped every active game, every user's streak,
and the whole leaderboard history. Everything here is backed by MongoDB
instead, in its own collection (like fast_typing's), and win events feed
XP into the SAME shared wallet used by games.py / fast_typing.py.
"""

import time
from cachetools import TTLCache
from Nobara.database import gamesdb
from Nobara.database.game_db import add_xp

wsdb = gamesdb.database['WordSeek']


# ——————————————————————————————————————————————————————————————
# Indexes - CRITICAL for performance.
#
# `wsdb` mixes many doc "type"s (game/daily/history/auth/topic/streak/
# score_event/paused_daily) in one collection, and `process_guess` in
# wordseek.py runs `get_game()`/`get_daily()`/`is_daily_paused()` on
# *every single text message* sent anywhere the bot can see (there was no
# `filters.group` restriction, so this fires in DMs too). Without indexes,
# every one of those find_one() calls was a full COLLECTION SCAN. As
# score_event docs pile up (one per WordSeek win, across every group,
# forever) that scan gets slower and slower over time - this is almost
# certainly why the bot has been feeling slower the longer it runs and the
# more groups/games it has. Call setup_wordseek_indexes() once at startup.
# ——————————————————————————————————————————————————————————————

async def setup_wordseek_indexes():
    await wsdb.create_index([("type", 1), ("chat_id", 1)])
    await wsdb.create_index([("type", 1), ("user_id", 1)])
    await wsdb.create_index([("type", 1), ("chat_id", 1), ("topic_id", 1)])
    await wsdb.create_index([("type", 1), ("chat_id", 1), ("len", 1), ("ts", 1)])
    await wsdb.create_index([("type", 1), ("user_id", 1), ("len", 1)])


# In-memory cache of chat_ids that are KNOWN to have no active game right
# now. process_guess() hits get_game() on every message in every group; for
# the (usual) case of "no game running here", this lets it skip the DB
# round-trip entirely instead of querying Mongo per-message. Kept small and
# short-lived on purpose - it only ever shortcuts to `None`, so a stale
# entry just means "one extra DB check next message", never wrong game data.
_no_active_game = TTLCache(maxsize=20000, ttl=120)


# ——————————————————————————————————————————————————————————————
# Active group games
# ——————————————————————————————————————————————————————————————

async def get_game(chat_id: int):
    if chat_id in _no_active_game:
        return None
    doc = await wsdb.find_one({"type": "game", "chat_id": chat_id})
    if doc:
        doc["guessed_words"] = set(doc.get("guessed_words", []))
        return doc
    _no_active_game[chat_id] = True
    return None


async def save_game(chat_id: int, game: dict):
    to_save = dict(game)
    to_save["guessed_words"] = list(to_save.get("guessed_words", []))
    to_save["type"] = "game"
    to_save["chat_id"] = chat_id
    await wsdb.update_one({"type": "game", "chat_id": chat_id}, {"$set": to_save}, upsert=True)
    if game.get("status"):
        _no_active_game.pop(chat_id, None)
    else:
        _no_active_game[chat_id] = True


async def clear_game(chat_id: int):
    await wsdb.delete_one({"type": "game", "chat_id": chat_id})
    _no_active_game[chat_id] = True


# ——————————————————————————————————————————————————————————————
# Daily (private chat) games
# ——————————————————————————————————————————————————————————————

async def get_daily(user_id: int):
    doc = await wsdb.find_one({"type": "daily", "user_id": user_id})
    if doc:
        doc["guessed_words"] = set(doc.get("guessed_words", []))
    return doc


async def save_daily(user_id: int, game: dict):
    to_save = dict(game)
    to_save["guessed_words"] = list(to_save.get("guessed_words", []))
    to_save["type"] = "daily"
    to_save["user_id"] = user_id
    await wsdb.update_one({"type": "daily", "user_id": user_id}, {"$set": to_save}, upsert=True)


async def is_daily_paused(user_id: int) -> bool:
    doc = await wsdb.find_one({"type": "paused_daily", "user_id": user_id})
    return bool(doc and doc.get("paused"))


async def set_daily_paused(user_id: int, paused: bool):
    await wsdb.update_one(
        {"type": "paused_daily", "user_id": user_id},
        {"$set": {"paused": paused}},
        upsert=True
    )


# ——————————————————————————————————————————————————————————————
# Per-chat word history (so the same word doesn't repeat too soon)
# ——————————————————————————————————————————————————————————————

async def get_word_history(chat_id: int):
    doc = await wsdb.find_one({"type": "history", "chat_id": chat_id})
    return doc.get("words", []) if doc else []


async def add_word_history(chat_id: int, word: str):
    await wsdb.update_one(
        {"type": "history", "chat_id": chat_id},
        {"$push": {"words": {"$each": [word], "$slice": -50}}},
        upsert=True
    )


# ——————————————————————————————————————————————————————————————
# Per-chat authorized users (who can /end a game besides admins)
# ——————————————————————————————————————————————————————————————

async def get_auth_users(chat_id: int) -> set:
    doc = await wsdb.find_one({"type": "auth", "chat_id": chat_id})
    return set(doc.get("user_ids", [])) if doc else set()


async def add_auth_user(chat_id: int, user_id: int):
    await wsdb.update_one(
        {"type": "auth", "chat_id": chat_id},
        {"$addToSet": {"user_ids": user_id}},
        upsert=True
    )


async def remove_auth_user(chat_id: int, user_id: int):
    await wsdb.update_one({"type": "auth", "chat_id": chat_id}, {"$pull": {"user_ids": user_id}})


# ——————————————————————————————————————————————————————————————
# Per-topic settings (restrict games to a topic, allowed lengths, etc.)
# ——————————————————————————————————————————————————————————————

async def get_topic_settings(chat_id: int, topic_id):
    return await wsdb.find_one({"type": "topic", "chat_id": chat_id, "topic_id": topic_id})


async def get_all_topics(chat_id: int) -> dict:
    result = {}
    async for doc in wsdb.find({"type": "topic", "chat_id": chat_id}):
        result[doc["topic_id"]] = doc
    return result


async def set_topic_settings(chat_id: int, topic_id, **fields):
    await wsdb.update_one(
        {"type": "topic", "chat_id": chat_id, "topic_id": topic_id},
        {
            "$set": fields,
            "$setOnInsert": {"lens": [4, 5, 6], "def": 5, "recreate": False},
        },
        upsert=True
    )


async def delete_topic_settings(chat_id: int, topic_id):
    await wsdb.delete_one({"type": "topic", "chat_id": chat_id, "topic_id": topic_id})


# ——————————————————————————————————————————————————————————————
# Daily streaks
# ——————————————————————————————————————————————————————————————

async def get_streak(user_id: int) -> int:
    doc = await wsdb.find_one({"type": "streak", "user_id": user_id})
    return doc.get("count", 0) if doc else 0


async def bump_streak(user_id: int) -> int:
    await wsdb.update_one({"type": "streak", "user_id": user_id}, {"$inc": {"count": 1}}, upsert=True)
    doc = await wsdb.find_one({"type": "streak", "user_id": user_id})
    return doc.get("count", 0) if doc else 0


async def reset_streak(user_id: int):
    await wsdb.update_one({"type": "streak", "user_id": user_id}, {"$set": {"count": 0}}, upsert=True)


# ——————————————————————————————————————————————————————————————
# Score events - feeds both the leaderboards AND the shared XP wallet
# ——————————————————————————————————————————————————————————————

async def record_score_event(chat_id, user_id: int, length: int, xp: int, username: str = None):
    await wsdb.insert_one({
        "type": "score_event",
        "chat_id": chat_id,
        "user_id": user_id,
        "len": length,
        "xp": xp,
        "ts": time.time(),
    })
    # This is what actually makes WordSeek wins spendable XP alongside
    # games.py's economy and fast-typing wins - one shared wallet.
    await add_xp(user_id, xp, username)


async def get_leaderboard(scope: str, chat_id, length: str, period: str, limit: int = 10):
    now = time.time()
    period_seconds = {"tdy": 86400, "wk": 86400 * 7, "mo": 86400 * 30, "yr": 86400 * 365}

    query = {"type": "score_event", "len": int(length)}
    if scope == "grp":
        query["chat_id"] = chat_id
    if period in period_seconds:
        query["ts"] = {"$gte": now - period_seconds[period]}

    scores = {}
    async for ev in wsdb.find(query):
        scores[ev["user_id"]] = scores.get(ev["user_id"], 0) + 1

    return sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:limit]


async def get_user_totals(user_id: int):
    """Returns (wins_4, wins_5, wins_6, total_xp) for a user's WordSeek profile."""
    w4 = w5 = w6 = xp_total = 0
    async for ev in wsdb.find({"type": "score_event", "user_id": user_id}):
        if ev["len"] == 4:
            w4 += 1
        elif ev["len"] == 5:
            w5 += 1
        elif ev["len"] == 6:
            w6 += 1
        xp_total += ev.get("xp", 0)
    return w4, w5, w6, xp_total
