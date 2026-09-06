import asyncio
from datetime import datetime, timezone
from urllib.parse import urlparse

from motor.motor_asyncio import AsyncIOMotorClient
from pyrogram import filters, enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from Nobara import app, scheduler
from Nobara.decorator.save import save
from Nobara.decorator.errors import error
from Nobara.database.mongolivedb import (
    add_entry,
    count_entries,
    decrypt_uri,
    delete_entry,
    get_all_entries,
    get_entries,
    get_entry,
    update_status,
)
from config import config

PAGE_SIZE = 5
PING_TIMEOUT_MS = 8000
SWEEP_CONCURRENCY = 5
SWEEP_INTERVAL_HOURS = 6  # Atlas free-tier clusters pause after ~60 days of
                          # zero activity - checking every few hours is
                          # already massive overkill margin, kept low mainly
                          # so /mongolive's "Live?" status stays fresh.


def _parse_db_name(uri: str):
    try:
        path = urlparse(uri).path.lstrip("/")
        return path.split("?")[0] or None
    except Exception:
        return None


async def ping_uri(uri: str, db_name):
    """Issue a single, harmless `ping` admin command. Never reads, writes,
    creates, or drops anything in the user's actual collections."""
    client = None
    try:
        client = AsyncIOMotorClient(
            uri,
            serverSelectionTimeoutMS=PING_TIMEOUT_MS,
            connectTimeoutMS=PING_TIMEOUT_MS,
            socketTimeoutMS=PING_TIMEOUT_MS,
        )
        await client[db_name or "admin"].command("ping")
        return True, None
    except Exception as e:
        return False, str(e)[:180]
    finally:
        if client:
            client.close()


# ——————————————————————————————————————————————————————————————
# Quick one-off connection tester: /mongo <url>
#
# (Rewritten to use the async Motor client instead of a synchronous
# pymongo.MongoClient().server_info() call - that was blocking the entire
# bot's event loop for the whole timeout window on every use.)
# ——————————————————————————————————————————————————————————————

@app.on_message(filters.command("mongo", prefixes=config.COMMAND_PREFIXES))
@error
@save
async def mongo_command(client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text(
            "⚠️ **𝖯𝗅𝖾𝖺𝗌𝖾 𝗉𝗋𝗈𝗏𝗂𝖽𝖾 𝗒𝗈𝗎𝗋 𝖬𝗈𝗇𝗀𝗈𝖣𝖡 𝖴𝖱𝖫!**\n\n📌 **𝖤𝗑𝖺𝗆𝗉𝗅𝖾:** `/mongo your_url`\n\n"
            "𝖳𝗂𝗉: 𝗍𝗈 𝗄𝖾𝖾𝗉 𝖺 𝖽𝖺𝗍𝖺𝖻𝖺𝗌𝖾 𝖺𝗅𝗂𝗏𝖾 𝗅𝗈𝗇𝗀-𝗍𝖾𝗋𝗆 𝗂𝗇𝗌𝗍𝖾𝖺𝖽 𝗈𝖿 𝗃𝗎𝗌𝗍 𝗍𝖾𝗌𝗍𝗂𝗇𝗀 𝗂𝗍 𝗈𝗇𝖼𝖾, 𝗍𝗋𝗒 /mongolive."
        )
    if message.chat.type != enums.ChatType.PRIVATE:
        return await message.reply_text(
            "🔒 𝖯𝗅𝖾𝖺𝗌𝖾 𝗎𝗌𝖾 /mongo 𝗂𝗇 𝖺 𝗉𝗋𝗂𝗏𝖺𝗍𝖾 𝗆𝖾𝗌𝗌𝖺𝗀𝖾 - 𝖼𝗈𝗇𝗇𝖾𝖼𝗍𝗂𝗈𝗇 𝗌𝗍𝗋𝗂𝗇𝗀𝗌 𝗌𝗁𝗈𝗎𝗅𝖽𝗇'𝗍 𝖻𝖾 𝗉𝗈𝗌𝗍𝖾𝖽 𝗂𝗇 𝗀𝗋𝗈𝗎𝗉𝗌."
        )

    mongo_url = message.command[1]
    if not (mongo_url.startswith("mongodb://") or mongo_url.startswith("mongodb+srv://")):
        return await message.reply_text("❌ **𝖨𝗇𝗏𝖺𝗅𝗂𝖽 𝖬𝗈𝗇𝗀𝗈𝖣𝖡 𝖴𝖱𝖫 𝖿𝗈𝗋𝗆𝖺𝗍!**")

    status = await message.reply_text("⏳ **𝖢𝗁𝖾𝖼𝗄𝗂𝗇𝗀 𝖼𝗈𝗇𝗇𝖾𝖼𝗍𝗂𝗈𝗇...**")
    ok, err = await ping_uri(mongo_url, _parse_db_name(mongo_url))
    if ok:
        await status.edit_text("✅ **𝖬𝗈𝗇𝗀𝗈𝖣𝖡 𝖼𝗈𝗇𝗇𝖾𝖼𝗍𝗂𝗈𝗇 𝗌𝗎𝖼𝖼𝖾𝗌𝗌𝖿𝗎𝗅!**")
    else:
        await status.edit_text(f"❌ **𝖥𝖺𝗂𝗅𝖾𝖽 𝗍𝗈 𝖼𝗈𝗇𝗇𝖾𝖼𝗍:**\n`{err}`")


# ——————————————————————————————————————————————————————————————
# MongoDB Live: /mongolive - unlimited monitored URLs, kept alive with a
# periodic background ping so free-tier clusters never go idle long enough
# to be auto-paused/deleted. Never touches the user's actual data.
# ——————————————————————————————————————————————————————————————

def _status_emoji(entry) -> str:
    return {"live": "✅", "down": "❌"}.get(entry.get("last_status", "unknown"), "⚪")


def _fmt_ago(dt) -> str:
    if not dt:
        return "Never"
    secs = (datetime.now(timezone.utc) - dt).total_seconds()
    if secs < 60:
        return "Just now"
    if secs < 3600:
        return f"{int(secs // 60)}m ago"
    if secs < 86400:
        return f"{int(secs // 3600)}h ago"
    return f"{int(secs // 86400)}d ago"


async def _render_menu(user_id: int):
    count = await count_entries(user_id)
    text = (
        "🗄 **𝖬𝗈𝗇𝗀𝗈𝖣𝖡 𝖫𝗂𝗏𝖾**\n\n"
        "Keeps your MongoDB clusters (Atlas free-tier, etc.) from going idle and getting "
        "auto-paused or wiped. I only ever send a harmless `ping` - your actual data and "
        "collections are never touched.\n\n"
        f"📊 You're monitoring **{count}** database{'s' if count != 1 else ''}."
    )
    rows = [
        [InlineKeyboardButton("➕ 𝖠𝖽𝖽 𝖣𝖺𝗍𝖺𝖻𝖺𝗌𝖾", callback_data="mgl:add")],
        [InlineKeyboardButton(f"📋 𝖬𝗒 𝖣𝖺𝗍𝖺𝖻𝖺𝗌𝖾𝗌 ({count})", callback_data="mgl:list:0")],
        [InlineKeyboardButton("❌ 𝖢𝗅𝗈𝗌𝖾", callback_data="mgl:close")],
    ]
    return text, InlineKeyboardMarkup(rows)


async def _render_list(user_id: int, page: int = 0):
    entries = await get_entries(user_id)
    if not entries:
        return None, None
    total_pages = (len(entries) - 1) // PAGE_SIZE + 1
    page = max(0, min(page, total_pages - 1))
    chunk = entries[page * PAGE_SIZE: (page + 1) * PAGE_SIZE]

    rows = [
        [InlineKeyboardButton(f"{_status_emoji(e)} {e['label']}", callback_data=f"mgl:view:{e['_id']}")]
        for e in chunk
    ]
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀ 𝖯𝗋𝖾𝗏", callback_data=f"mgl:list:{page - 1}"))
    if total_pages > 1:
        nav.append(InlineKeyboardButton(f"{page + 1}/{total_pages}", callback_data="mgl:noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("𝖭𝖾𝗑𝗍 ▶", callback_data=f"mgl:list:{page + 1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton("➕ 𝖠𝖽𝖽 𝖣𝖺𝗍𝖺𝖻𝖺𝗌𝖾", callback_data="mgl:add")])
    rows.append([
        InlineKeyboardButton("🔙 𝖬𝖾𝗇𝗎", callback_data="mgl:menu"),
        InlineKeyboardButton("❌ 𝖢𝗅𝗈𝗌𝖾", callback_data="mgl:close"),
    ])
    text = "📋 **𝖸𝗈𝗎𝗋 𝖬𝗈𝗇𝗂𝗍𝗈𝗋𝖾𝖽 𝖣𝖺𝗍𝖺𝖻𝖺𝗌𝖾𝗌**\n𝖳𝖺𝗉 𝗈𝗇𝖾 𝗍𝗈 𝗌𝖾𝖾 𝖽𝖾𝗍𝖺𝗂𝗅𝗌."
    return text, InlineKeyboardMarkup(rows)


async def _render_view(user_id: int, entry_id: str):
    entry = await get_entry(user_id, entry_id)
    if not entry:
        return None, None
    status = entry.get("last_status", "unknown")
    text = (
        f"{_status_emoji(entry)} **{entry['label']}**\n\n"
        f"🗂 𝖣𝖺𝗍𝖺𝖻𝖺𝗌𝖾: `{entry.get('db_name') or 'admin'}`\n"
        f"📅 𝖠𝖽𝖽𝖾𝖽: {entry['added_at'].strftime('%Y-%m-%d')}\n"
        f"🔍 𝖫𝖺𝗌𝗍 𝖼𝗁𝖾𝖼𝗄𝖾𝖽: {_fmt_ago(entry.get('last_checked'))}\n"
        f"📶 𝖲𝗍𝖺𝗍𝗎𝗌: {status.capitalize()}"
    )
    if entry.get("last_error"):
        text += f"\n⚠️ `{entry['last_error']}`"
    if entry.get("fail_count", 0) >= 3:
        text += (
            f"\n\n🔴 𝖥𝖺𝗂𝗅𝖾𝖽 {entry['fail_count']} 𝖼𝗁𝖾𝖼𝗄𝗌 𝗂𝗇 𝖺 𝗋𝗈𝗐 - 𝖽𝗈𝗎𝖻𝗅𝖾-𝖼𝗁𝖾𝖼𝗄 𝗒𝗈𝗎𝗋 𝖠𝗍𝗅𝖺𝗌 "
            "𝖭𝖾𝗍𝗐𝗈𝗋𝗄 𝖠𝖼𝖼𝖾𝗌𝗌 (𝖨𝖯 𝖺𝗅𝗅𝗈𝗐𝗅𝗂𝗌𝗍) 𝗈𝗋 𝖼𝗋𝖾𝖽𝖾𝗇𝗍𝗂𝖺𝗅𝗌."
        )
    rows = [
        [InlineKeyboardButton("🔄 𝖱𝖾𝖿𝗋𝖾𝗌𝗁 𝖭𝗈𝗐", callback_data=f"mgl:ref:{entry_id}")],
        [InlineKeyboardButton("🗑 𝖱𝖾𝗆𝗈𝗏𝖾", callback_data=f"mgl:del:{entry_id}")],
        [InlineKeyboardButton("🔙 𝖡𝖺𝖼𝗄 𝗍𝗈 𝖫𝗂𝗌𝗍", callback_data="mgl:list:0")],
    ]
    return text, InlineKeyboardMarkup(rows)


@app.on_message(filters.command(["mongolive", "mongodb"], prefixes=config.COMMAND_PREFIXES))
@error
@save
async def mongolive_cmd(client, message):
    if message.chat.type != enums.ChatType.PRIVATE:
        return await message.reply(
            "🔒 𝖥𝗈𝗋 𝗒𝗈𝗎𝗋 𝖽𝖺𝗍𝖺𝖻𝖺𝗌𝖾'𝗌 𝗌𝖺𝖿𝖾𝗍𝗒, 𝗉𝗅𝖾𝖺𝗌𝖾 𝗎𝗌𝖾 /mongolive 𝗂𝗇 𝖺 𝗉𝗋𝗂𝗏𝖺𝗍𝖾 𝗆𝖾𝗌𝗌𝖺𝗀𝖾 𝗐𝗂𝗍𝗁 𝗆𝖾 - "
            "𝖼𝗈𝗇𝗇𝖾𝖼𝗍𝗂𝗈𝗇 𝗌𝗍𝗋𝗂𝗇𝗀𝗌 𝗌𝗁𝗈𝗎𝗅𝖽𝗇'𝗍 𝖻𝖾 𝗉𝗈𝗌𝗍𝖾𝖽 𝗂𝗇 𝗀𝗋𝗈𝗎𝗉𝗌."
        )
    text, kb = await _render_menu(message.from_user.id)
    await message.reply(text, reply_markup=kb)


@app.on_callback_query(filters.regex(r"^mgl:menu$"))
async def mgl_menu_cb(client, query):
    await query.answer()
    text, kb = await _render_menu(query.from_user.id)
    try:
        await query.message.edit_text(text, reply_markup=kb)
    except Exception:
        pass


@app.on_callback_query(filters.regex(r"^mgl:close$"))
async def mgl_close_cb(client, query):
    await query.answer()
    try:
        await query.message.delete()
    except Exception:
        pass


@app.on_callback_query(filters.regex(r"^mgl:noop$"))
async def mgl_noop_cb(client, query):
    await query.answer()


@app.on_callback_query(filters.regex(r"^mgl:list:"))
async def mgl_list_cb(client, query):
    await query.answer()
    page = int(query.data.split(":")[-1])
    text, kb = await _render_list(query.from_user.id, page)
    if not kb:
        menu_text, menu_kb = await _render_menu(query.from_user.id)
        try:
            await query.message.edit_text(
                "📋 𝖸𝗈𝗎 𝖽𝗈𝗇'𝗍 𝗁𝖺𝗏𝖾 𝖺𝗇𝗒 𝖽𝖺𝗍𝖺𝖻𝖺𝗌𝖾𝗌 𝗒𝖾𝗍.\n\n" + menu_text, reply_markup=menu_kb
            )
        except Exception:
            pass
        return
    try:
        await query.message.edit_text(text, reply_markup=kb)
    except Exception:
        pass


@app.on_callback_query(filters.regex(r"^mgl:view:"))
async def mgl_view_cb(client, query):
    await query.answer()
    entry_id = query.data.split(":", 2)[2]
    text, kb = await _render_view(query.from_user.id, entry_id)
    if not text:
        return await query.answer("𝖭𝗈𝗍 𝖿𝗈𝗎𝗇𝖽 (𝗆𝖺𝗒𝖻𝖾 𝖺𝗅𝗋𝖾𝖺𝖽𝗒 𝗋𝖾𝗆𝗈𝗏𝖾𝖽).", show_alert=True)
    try:
        await query.message.edit_text(text, reply_markup=kb)
    except Exception:
        pass


@app.on_callback_query(filters.regex(r"^mgl:ref:"))
async def mgl_refresh_cb(client, query):
    entry_id = query.data.split(":", 2)[2]
    entry = await get_entry(query.from_user.id, entry_id)
    if not entry:
        return await query.answer("𝖭𝗈𝗍 𝖿𝗈𝗎𝗇𝖽.", show_alert=True)
    await query.answer("🔄 𝖢𝗁𝖾𝖼𝗄𝗂𝗇𝗀...")
    uri = decrypt_uri(entry["uri_enc"])
    ok, err = await ping_uri(uri, entry.get("db_name"))
    await update_status(entry_id, "live" if ok else "down", err)
    text, kb = await _render_view(query.from_user.id, entry_id)
    try:
        await query.message.edit_text(text, reply_markup=kb)
    except Exception:
        pass


@app.on_callback_query(filters.regex(r"^mgl:del:"))
async def mgl_del_confirm_cb(client, query):
    await query.answer()
    entry_id = query.data.split(":", 2)[2]
    entry = await get_entry(query.from_user.id, entry_id)
    if not entry:
        return await query.answer("𝖭𝗈𝗍 𝖿𝗈𝗎𝗇𝖽.", show_alert=True)
    rows = [[
        InlineKeyboardButton("✅ 𝖸𝖾𝗌, 𝗋𝖾𝗆𝗈𝗏𝖾", callback_data=f"mgl:delyes:{entry_id}"),
        InlineKeyboardButton("❌ 𝖢𝖺𝗇𝖼𝖾𝗅", callback_data=f"mgl:view:{entry_id}"),
    ]]
    try:
        await query.message.edit_text(
            f"🗑 𝖱𝖾𝗆𝗈𝗏𝖾 **{entry['label']}** 𝖿𝗋𝗈𝗆 𝗆𝗈𝗇𝗂𝗍𝗈𝗋𝗂𝗇𝗀? 𝖨'𝗅𝗅 𝗌𝗍𝗈𝗉 𝗉𝗂𝗇𝗀𝗂𝗇𝗀 𝗂𝗍 "
            "(𝗍𝗁𝗂𝗌 𝖽𝗈𝖾𝗌𝗇'𝗍 𝗍𝗈𝗎𝖼𝗁 𝗒𝗈𝗎𝗋 𝖺𝖼𝗍𝗎𝖺𝗅 𝖽𝖺𝗍𝖺𝖻𝖺𝗌𝖾 𝗈𝗋 𝗂𝗍𝗌 𝖽𝖺𝗍𝖺).",
            reply_markup=InlineKeyboardMarkup(rows),
        )
    except Exception:
        pass


@app.on_callback_query(filters.regex(r"^mgl:delyes:"))
async def mgl_del_yes_cb(client, query):
    entry_id = query.data.split(":", 2)[2]
    ok = await delete_entry(query.from_user.id, entry_id)
    await query.answer("🗑 𝖱𝖾𝗆𝗈𝗏𝖾𝖽." if ok else "𝖠𝗅𝗋𝖾𝖺𝖽𝗒 𝗋𝖾𝗆𝗈𝗏𝖾𝖽.", show_alert=True)
    text, kb = await _render_list(query.from_user.id, 0)
    if not kb:
        text, kb = await _render_menu(query.from_user.id)
    try:
        await query.message.edit_text(text, reply_markup=kb)
    except Exception:
        pass


@app.on_callback_query(filters.regex(r"^mgl:add$"))
async def mgl_add_cb(client, query):
    await query.answer()
    chat_id = query.message.chat.id
    user_id = query.from_user.id

    try:
        uri_msg = await client.ask(
            chat_id,
            "🔗 𝖲𝖾𝗇𝖽 𝗒𝗈𝗎𝗋 𝖬𝗈𝗇𝗀𝗈𝖣𝖡 𝖼𝗈𝗇𝗇𝖾𝖼𝗍𝗂𝗈𝗇 𝗌𝗍𝗋𝗂𝗇𝗀 (`mongodb://` 𝗈𝗋 `mongodb+srv://`).\n\n"
            "⚠️ 𝖨'𝗅𝗅 𝗈𝗇𝗅𝗒 𝖾𝗏𝖾𝗋 𝗉𝗂𝗇𝗀 𝗂𝗍 𝗍𝗈 𝗄𝖾𝖾𝗉 𝗂𝗍 𝖺𝗐𝖺𝗄𝖾 - 𝗇𝖾𝗏𝖾𝗋 𝗋𝖾𝖺𝖽 𝗈𝗋 𝗐𝗋𝗂𝗍𝖾 𝗒𝗈𝗎𝗋 𝖼𝗈𝗅𝗅𝖾𝖼𝗍𝗂𝗈𝗇𝗌.\n\n"
            "𝖲𝖾𝗇𝖽 /cancel 𝗍𝗈 𝗌𝗍𝗈𝗉.",
            filters=filters.text,
            timeout=180,
        )
    except asyncio.TimeoutError:
        return await client.send_message(chat_id, "⌛ 𝖳𝗂𝗆𝖾𝖽 𝗈𝗎𝗍. 𝖳𝖺𝗉 ➕ 𝖠𝖽𝖽 𝖣𝖺𝗍𝖺𝖻𝖺𝗌𝖾 𝖺𝗀𝖺𝗂𝗇 𝗐𝗁𝖾𝗇 𝗋𝖾𝖺𝖽𝗒.")

    raw_uri = uri_msg.text.strip()
    # Best-effort: scrub the raw credential out of the visible chat history.
    try:
        await uri_msg.delete()
    except Exception:
        pass

    if raw_uri.lower() in ("/cancel", "cancel"):
        return await client.send_message(chat_id, "❌ 𝖢𝖺𝗇𝖼𝖾𝗅𝗅𝖾𝖽.")
    if not (raw_uri.startswith("mongodb://") or raw_uri.startswith("mongodb+srv://")):
        return await client.send_message(
            chat_id,
            "⚠️ 𝖳𝗁𝖺𝗍 𝖽𝗈𝖾𝗌𝗇'𝗍 𝗅𝗈𝗈𝗄 𝗅𝗂𝗄𝖾 𝖺 𝖬𝗈𝗇𝗀𝗈𝖣𝖡 𝖼𝗈𝗇𝗇𝖾𝖼𝗍𝗂𝗈𝗇 𝗌𝗍𝗋𝗂𝗇𝗀 "
            "(𝗌𝗁𝗈𝗎𝗅𝖽 𝗌𝗍𝖺𝗋𝗍 𝗐𝗂𝗍𝗁 `mongodb://` 𝗈𝗋 `mongodb+srv://`). 𝖳𝖺𝗉 ➕ 𝖠𝖽𝖽 𝖣𝖺𝗍𝖺𝖻𝖺𝗌𝖾 𝗍𝗈 𝗍𝗋𝗒 𝖺𝗀𝖺𝗂𝗇.",
        )

    db_name = _parse_db_name(raw_uri)

    try:
        label_msg = await client.ask(
            chat_id,
            "🏷 𝖲𝖾𝗇𝖽 𝖺 𝗌𝗁𝗈𝗋𝗍 𝗇𝗂𝖼𝗄𝗇𝖺𝗆𝖾 𝖿𝗈𝗋 𝗍𝗁𝗂𝗌 𝖽𝖺𝗍𝖺𝖻𝖺𝗌𝖾 (𝖾.𝗀. `𝖬𝗒 𝖡𝗈𝗍 𝖯𝗋𝗈𝖽`), 𝗈𝗋 𝗌𝖾𝗇𝖽 `skip` 𝗍𝗈 𝖺𝗎𝗍𝗈-𝗇𝖺𝗆𝖾 𝗂𝗍.",
            filters=filters.text,
            timeout=120,
        )
    except asyncio.TimeoutError:
        return await client.send_message(chat_id, "⌛ 𝖳𝗂𝗆𝖾𝖽 𝗈𝗎𝗍. 𝖳𝖺𝗉 ➕ 𝖠𝖽𝖽 𝖣𝖺𝗍𝖺𝖻𝖺𝗌𝖾 𝖺𝗀𝖺𝗂𝗇 𝗐𝗁𝖾𝗇 𝗋𝖾𝖺𝖽𝗒.")

    label_text = label_msg.text.strip()
    if label_text.lower() in ("/cancel", "cancel"):
        return await client.send_message(chat_id, "❌ 𝖢𝖺𝗇𝖼𝖾𝗅𝗅𝖾𝖽.")
    label = (db_name or "Unnamed DB") if label_text.lower() == "skip" or not label_text else label_text[:64]

    status_msg = await client.send_message(chat_id, "🔄 𝖳𝖾𝗌𝗍𝗂𝗇𝗀 𝖼𝗈𝗇𝗇𝖾𝖼𝗍𝗂𝗈𝗇...")
    ok, err = await ping_uri(raw_uri, db_name)
    entry_id = await add_entry(user_id, label, raw_uri, db_name)
    await update_status(entry_id, "live" if ok else "down", err)

    back_kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 𝖬𝖾𝗇𝗎", callback_data="mgl:menu")]])
    if ok:
        await status_msg.edit(
            f"✅ **{label}** 𝖺𝖽𝖽𝖾𝖽 𝖺𝗇𝖽 𝗂𝗌 𝗅𝗂𝗏𝖾! 𝖨'𝗅𝗅 𝗄𝖾𝖾𝗉 𝗉𝗂𝗇𝗀𝗂𝗇𝗀 𝗂𝗍 𝗉𝖾𝗋𝗂𝗈𝖽𝗂𝖼𝖺𝗅𝗅𝗒 𝗌𝗈 𝗂𝗍 𝗇𝖾𝗏𝖾𝗋 𝗀𝗈𝖾𝗌 𝗂𝖽𝗅𝖾.",
            reply_markup=back_kb,
        )
    else:
        await status_msg.edit(
            f"⚠️ **{label}** 𝗐𝖺𝗌 𝗌𝖺𝗏𝖾𝖽, 𝖻𝗎𝗍 𝖨 𝖼𝗈𝗎𝗅𝖽𝗇'𝗍 𝖼𝗈𝗇𝗇𝖾𝖼𝗍 𝗃𝗎𝗌𝗍 𝗇𝗈𝗐:\n`{err}`\n\n"
            "𝖳𝗁𝗂𝗌 𝗂𝗌 𝗎𝗌𝗎𝖺𝗅𝗅𝗒 𝖺𝗇 𝖨𝖯 𝖺𝗅𝗅𝗈𝗐𝗅𝗂𝗌𝗍 𝗂𝗌𝗌𝗎𝖾 - 𝗂𝗇 𝖠𝗍𝗅𝖺𝗌, 𝗀𝗈 𝗍𝗈 𝖭𝖾𝗍𝗐𝗈𝗋𝗄 𝖠𝖼𝖼𝖾𝗌𝗌 𝖺𝗇𝖽 𝖺𝗅𝗅𝗈𝗐 "
            "𝖺𝖼𝖼𝖾𝗌𝗌 𝖿𝗋𝗈𝗆 𝖺𝗇𝗒𝗐𝗁𝖾𝗋𝖾 (0.0.0.0/0), 𝗈𝗋 𝖺𝖽𝖽 𝗍𝗁𝗂𝗌 𝗌𝖾𝗋𝗏𝖾𝗋'𝗌 𝖨𝖯. 𝖨'𝗅𝗅 𝗄𝖾𝖾𝗉 𝗋𝖾𝗍𝗋𝗒𝗂𝗇𝗀 𝖺𝗎𝗍𝗈𝗆𝖺𝗍𝗂𝖼𝖺𝗅𝗅𝗒.",
            reply_markup=back_kb,
        )


async def _keepalive_sweep():
    entries = await get_all_entries()
    if not entries:
        return
    sem = asyncio.Semaphore(SWEEP_CONCURRENCY)

    async def _check(entry):
        async with sem:
            try:
                uri = decrypt_uri(entry["uri_enc"])
            except Exception:
                return
            ok, err = await ping_uri(uri, entry.get("db_name"))
            await update_status(str(entry["_id"]), "live" if ok else "down", err)

    await asyncio.gather(*[_check(e) for e in entries], return_exceptions=True)


# Registered at import time - same pattern as the other periodic jobs in
# this codebase (see log_helper.py, nightmode.py, backup.py).
scheduler.add_job(
    _keepalive_sweep,
    "interval",
    hours=SWEEP_INTERVAL_HOURS,
    id="mongolive_keepalive_sweep",
    replace_existing=True,
)


__module__ = "𝖬𝗈𝗇𝗀𝗈𝖣𝖡"
__help__ = """**𝖬𝗈𝗇𝗀𝗈𝖣𝖡 𝖢𝗈𝗆𝗆𝖺𝗇𝖽𝗌:**

✧ `/mongo <url>` **:** 𝖰𝗎𝗂𝖼𝗄 𝗈𝗇𝖾-𝗈𝖿𝖿 𝖼𝗁𝖾𝖼𝗄 𝗐𝗁𝖾𝗍𝗁𝖾𝗋 𝖺 𝖬𝗈𝗇𝗀𝗈𝖣𝖡 𝖴𝖱𝖫 𝗂𝗌 𝗏𝖺𝗅𝗂𝖽 𝖺𝗇𝖽 𝗋𝖾𝖺𝖼𝗁𝖺𝖻𝗅𝖾 (𝖯𝖬 𝗈𝗇𝗅𝗒).

✧ `/𝗆𝗈𝗇𝗀𝗈𝗅𝗂𝗏𝖾` 𝗈𝗋 `/𝗆𝗈𝗇𝗀𝗈𝖽𝖻` (𝖯𝖬 𝗈𝗇𝗅𝗒) **:** 𝖮𝗉𝖾𝗇 𝗍𝗁𝖾 𝖬𝗈𝗇𝗀𝗈𝖣𝖡 𝖫𝗂𝗏𝖾 𝗆𝖾𝗇𝗎.
𝖠𝖽𝖽 𝖺𝗇𝗒 𝗇𝗎𝗆𝖻𝖾𝗋 𝗈𝖿 𝖬𝗈𝗇𝗀𝗈𝖣𝖡 𝖼𝗈𝗇𝗇𝖾𝖼𝗍𝗂𝗈𝗇 𝗌𝗍𝗋𝗂𝗇𝗀𝗌 (𝖾.𝗀. 𝖠𝗍𝗅𝖺𝗌 𝖿𝗋𝖾𝖾-𝗍𝗂𝖾𝗋 𝖼𝗅𝗎𝗌𝗍𝖾𝗋𝗌) 𝖺𝗇𝖽 𝖨'𝗅𝗅 𝗉𝖾𝗋𝗂𝗈𝖽𝗂𝖼𝖺𝗅𝗅𝗒
𝗉𝗂𝗇𝗀 𝗍𝗁𝖾𝗆 𝗌𝗈 𝗍𝗁𝖾𝗒 𝗇𝖾𝗏𝖾𝗋 𝗀𝖾𝗍 𝖺𝗎𝗍𝗈-𝗉𝖺𝗎𝗌𝖾𝖽/𝗐𝗂𝗉𝖾𝖽 𝖿𝗈𝗋 𝗂𝗇𝖺𝖼𝗍𝗂𝗏𝗂𝗍𝗒 - 𝗐𝗂𝗍𝗁𝗈𝗎𝗍 𝖾𝗏𝖾𝗋 𝗋𝖾𝖺𝖽𝗂𝗇𝗀 𝗈𝗋
𝗐𝗋𝗂𝗍𝗂𝗇𝗀 𝗒𝗈𝗎𝗋 𝖺𝖼𝗍𝗎𝖺𝗅 𝖽𝖺𝗍𝖺.
   ✧ ➕ 𝖠𝖽𝖽, 🗑 𝖱𝖾𝗆𝗈𝗏𝖾, 🔄 𝖱𝖾𝖿𝗋𝖾𝗌𝗁, 𝖺𝗇𝖽 ❌ 𝖢𝗅𝗈𝗌𝖾 𝖻𝗎𝗍𝗍𝗈𝗇𝗌.
   ✧ 𝖲𝖾𝖾 𝗁𝗈𝗐 𝗆𝖺𝗇𝗒 𝖽𝖺𝗍𝖺𝖻𝖺𝗌𝖾𝗌 𝗒𝗈𝗎'𝗋𝖾 𝗆𝗈𝗇𝗂𝗍𝗈𝗋𝗂𝗇𝗀 𝖺𝗇𝖽 𝗐𝗁𝖾𝗍𝗁𝖾𝗋 𝖾𝖺𝖼𝗁 𝗈𝗇𝖾 𝗂𝗌 𝖼𝗎𝗋𝗋𝖾𝗇𝗍𝗅𝗒 𝗅𝗂𝗏𝖾.
   ✧ 𝖸𝗈𝗎𝗋 𝗅𝗂𝗌𝗍 𝗂𝗌 𝗉𝗋𝗂𝗏𝖺𝗍𝖾 - 𝗇𝗈 𝗈𝗇𝖾 𝖾𝗅𝗌𝖾 𝖼𝖺𝗇 𝗌𝖾𝖾 𝗈𝗋 𝗍𝗈𝗎𝖼𝗁 𝗂𝗍.
"""
