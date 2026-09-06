import re
import io
import asyncio
import difflib
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from pyrogram.enums import ParseMode, ChatType, ChatMemberStatus

from Nobara.database.filtersdb import (
    add_filter, get_filter, get_filters, delete_filter, remove_all_filters,
    match_filter, count_filters, increment_filter_count, get_alert_text,
    set_autodelete_settings, get_autodelete_settings,
    set_clone_status, get_clone_status, clone_all_filters,
    save_clone_history, get_clone_history, get_top_filters,
    set_random_suggest_status, get_random_suggest_status,
    set_filter_genre, get_filters_missing_genre,
    get_random_filter, get_random_filter_by_genre,
)
from Nobara.helper.filter_buttons import parse_buttons, build_markup, serialize_existing_markup
from Nobara.helper.genre_fetch import fetch_genres
from Nobara import app, FILTERS_GROUP, SUGGEST_MODE_GROUP
from Nobara.decorator.chatadmin import chatadmin, chatowner
from config import config
from Nobara.decorator.save import save
from Nobara.decorator.errors import error


# ——————————————————————————————————————————————————————————————
# Genre keywords for /suggestmode's fuzzy genre matching (ported from the
# reference Filter-Bot-Dev plugins/utils.py detect_genre()).
# ——————————————————————————————————————————————————————————————
GENRE_KEYWORDS = [
    "action", "adventure", "comedy", "drama", "fantasy", "horror", "romance",
    "mystery", "thriller", "sci-fi", "science fiction", "slice of life",
    "sports", "supernatural", "isekai", "school", "music", "historical",
    "war", "crime", "family", "psychological", "harem", "mecha",
    "action adventure",
]


def detect_genre(text: str, cutoff: float = 0.8):
    text = text.lower()
    for genre in GENRE_KEYWORDS:
        if genre in text:
            return genre
    for word in re.findall(r"[a-z\-]+", text):
        if len(word) < 4:
            continue
        match = difflib.get_close_matches(word, GENRE_KEYWORDS, n=1, cutoff=cutoff)
        if match:
            return match[0]
    return None


def _normalize(text: str) -> str:
    """Strips punctuation that shouldn't block a trigger match, and lowercases."""
    return re.sub(r"[:'\-_.,]", "", text.lower())


def _extract_media_response(msg: Message):
    for media_type in ("photo", "video", "audio", "sticker", "animation", "video_note", "voice"):
        media = getattr(msg, media_type, None)
        if media is not None:
            return {"type": media_type, "file_id": media.file_id}
    return None


async def _is_group_owner(client: Client, chat_id: int, user_id: int) -> bool:
    if user_id == config.OWNER_ID:
        return True
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status == ChatMemberStatus.OWNER
    except Exception:
        return False


async def _is_group_admin(client: Client, chat_id: int, user_id: int) -> bool:
    if user_id == config.OWNER_ID:
        return True
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)
    except Exception:
        return False


# ——————————————————————————————————————————————————————————————
# /add (alias /filter) - add a filter, with optional buttons/media/alerts
# ——————————————————————————————————————————————————————————————
@app.on_message(filters.command(["add", "filter"], config.COMMAND_PREFIXES) & filters.group)
@chatadmin
@error
@save
async def filter_command(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply(
            "𝖴𝗌𝖺𝗀𝖾:\n`/add trigger response`\n𝖮𝖱\n𝖱𝖾𝗉𝗅𝗒 𝗍𝗈 𝖺 𝗆𝖾𝖽𝗂𝖺/𝗍𝖾𝗑𝗍 𝗐𝗂𝗍𝗁 `/add trigger`\n\n"
            "𝖸𝗈𝗎 𝖼𝖺𝗇 𝖺𝗅𝗌𝗈 𝖺𝖽𝖽 𝖻𝗎𝗍𝗍𝗈𝗇𝗌 𝗂𝗇 𝗍𝗁𝖾 𝗋𝖾𝗌𝗉𝗈𝗇𝗌𝖾:\n"
            "`[button text](buttonurl:https://example.com)`\n"
            "`[same row](buttonurl:https://example.com:same)`\n"
            "`[popup](buttonalert:This shows as an alert!)`"
        )
        return

    trigger = message.command[1].lower()
    chat_id = message.chat.id
    title = message.chat.title

    reply_text, rows, alerts, file_id = "", [], [], None

    if message.reply_to_message:
        replied = message.reply_to_message
        extra = " ".join(message.command[2:]) if len(message.command) > 2 else ""

        if replied.reply_markup and replied.reply_markup.inline_keyboard:
            # Format: reply to a message that already has buttons attached
            rows = serialize_existing_markup(replied.reply_markup.inline_keyboard)
            media = _extract_media_response(replied)
            if media:
                file_id = media["file_id"]
                reply_text = replied.caption or ""
            else:
                reply_text = replied.text or ""
        else:
            media = _extract_media_response(replied)
            if media:
                file_id = media["file_id"]
                raw_text = replied.caption or extra
            else:
                raw_text = replied.text or extra
            reply_text, rows, alerts = parse_buttons(raw_text, trigger)

        if not reply_text and not file_id:
            await message.reply("𝖸𝗈𝗎 𝖼𝖺𝗇𝗇𝗈𝗍 𝗌𝖺𝗏𝖾 𝖻𝗎𝗍𝗍𝗈𝗇𝗌 𝖺𝗅𝗈𝗇𝖾! 𝖯𝗅𝖾𝖺𝗌𝖾 𝖺𝖽𝖽 𝗌𝗈𝗆𝖾 𝗍𝖾𝗑𝗍 𝗈𝗋 𝗆𝖾𝖽𝗂𝖺 𝖼𝖺𝗉𝗍𝗂𝗈𝗇.")
            return

    else:
        if len(message.command) < 3:
            await message.reply("𝖯𝗅𝖾𝖺𝗌𝖾 𝖺𝖽𝖽 𝗌𝗈𝗆𝖾 𝗍𝖾𝗑𝗍 𝗈𝗋 𝗋𝖾𝗉𝗅𝗒 𝗍𝗈 𝖺 𝗆𝖾𝗌𝗌𝖺𝗀𝖾 𝗍𝗈 𝗌𝖺𝗏𝖾 𝗍𝗁𝗂𝗌 𝖿𝗂𝗅𝗍𝖾𝗋!")
            return
        raw_text = " ".join(message.command[2:])
        media = _extract_media_response(message)
        if media:
            file_id = media["file_id"]
        reply_text, rows, alerts = parse_buttons(raw_text, trigger)

    await add_filter(chat_id, trigger, reply_text, rows, file_id, alerts)
    await message.reply(f"𝖥𝗂𝗅𝗍𝖾𝗋 𝖿𝗈𝗋 `{trigger}` 𝗁𝖺𝗌 𝖻𝖾𝖾𝗇 𝗌𝗎𝖼𝖼𝖾𝗌𝗌𝖿𝗎𝗅𝗅𝗒 𝖺𝖽𝖽𝖾𝖽 𝗍𝗈 **{title}**!")

    # Background genre tagging (TMDB -> AniList), doesn't block the reply above
    async def _tag_genre():
        try:
            genres = await fetch_genres(trigger)
            if genres:
                await set_filter_genre(chat_id, trigger, genres)
        except Exception as e:
            print(f"Genre fetch error (safe to ignore): {e}")
    asyncio.create_task(_tag_genre())


# ——————————————————————————————————————————————————————————————
# /filters - list all filters in this chat
# ——————————————————————————————————————————————————————————————
@app.on_message(filters.command("filters", config.COMMAND_PREFIXES) & filters.group)
@chatadmin
@error
@save
async def list_filters(client: Client, message: Message):
    chat_id = message.chat.id
    triggers = await get_filters(chat_id)
    count = len(triggers)

    if not count:
        await message.reply(f"𝖳𝗁𝖾𝗋𝖾 𝖺𝗋𝖾 𝗇𝗈 𝖺𝖼𝗍𝗂𝗏𝖾 𝖿𝗂𝗅𝗍𝖾𝗋𝗌 𝗂𝗇 **{message.chat.title}**")
        return

    filter_list = f"𝖳𝗈𝗍𝖺𝗅 𝗇𝗎𝗆𝖻𝖾𝗋 𝗈𝖿 𝖿𝗂𝗅𝗍𝖾𝗋𝗌 𝗂𝗇 {message.chat.title} : {count}\n\n"
    filter_list += "\n".join(f" ×  `{t}`" for t in triggers)

    if len(filter_list) > 4096:
        with io.BytesIO(filter_list.replace("`", "").encode()) as f:
            f.name = "filters.txt"
            await message.reply_document(document=f)
        return

    await message.reply(filter_list)


# ——————————————————————————————————————————————————————————————
# /stop - delete one filter
# ——————————————————————————————————————————————————————————————
@app.on_message(filters.command(["stop"], config.COMMAND_PREFIXES) & filters.group)
@chatadmin
@error
@save
async def stop_filter(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply(
            "𝖬𝖾𝗇𝗍𝗂𝗈𝗇 𝗍𝗁𝖾 𝖿𝗂𝗅𝗍𝖾𝗋𝗇𝖺𝗆𝖾 𝗐𝗁𝗂𝖼𝗁 𝗒𝗈𝗎 𝗐𝖺𝗇𝗍 𝗍𝗈 𝖽𝖾𝗅𝖾𝗍𝖾!\n\n`/stop filtername`\n\n𝖴𝗌𝖾 /filters 𝗍𝗈 𝗏𝗂𝖾𝗐 𝖺𝗅𝗅 𝖺𝗏𝖺𝗂𝗅𝖺𝖻𝗅𝖾 𝖿𝗂𝗅𝗍𝖾𝗋𝗌"
        )
        return

    trigger = message.command[1].lower()
    chat_id = message.chat.id

    removed = await delete_filter(chat_id, trigger)
    if removed:
        await message.reply(f"𝖱𝖾𝗆𝗈𝗏𝖾𝖽 𝖿𝗂𝗅𝗍𝖾𝗋 `{trigger}` 𝖿𝗋𝗈𝗆 **{message.chat.title}**.")
    else:
        await message.reply(f"𝖭𝗈 𝖿𝗂𝗅𝗍𝖾𝗋 𝖿𝗈𝗎𝗇𝖽 𝖿𝗈𝗋 `{trigger}` 𝗂𝗇 {message.chat.title}.")


# ——————————————————————————————————————————————————————————————
# /delall (alias /stopall) - remove every filter, owner only, with confirm
# ——————————————————————————————————————————————————————————————
@app.on_message(filters.command(["delall", "stopall"], config.COMMAND_PREFIXES) & filters.group)
@chatowner
@error
@save
async def stop_all_filters(client: Client, message: Message):
    confirmation_buttons = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("𝖢𝗈𝗇𝖿𝗂𝗋𝗆 𝖱𝖾𝗆𝗈𝗏𝖾 𝖠𝗅𝗅 𝖥𝗂𝗅𝗍𝖾𝗋𝗌", callback_data="confirm_remove_filters")],
            [InlineKeyboardButton("🗑️", callback_data="cancel")],
        ]
    )
    await message.reply(
        f"𝖠𝗋𝖾 𝗒𝗈𝗎 𝗌𝗎𝗋𝖾 𝗒𝗈𝗎 𝗐𝖺𝗇𝗍 𝗍𝗈 𝗋𝖾𝗆𝗈𝗏𝖾 𝖺𝗅𝗅 𝖿𝗂𝗅𝗍𝖾𝗋𝗌 𝖿𝗋𝗈𝗆 {message.chat.title}?",
        reply_markup=confirmation_buttons,
    )


@app.on_callback_query(filters.regex("^confirm_remove_filters"))
@chatowner
@error
async def confirm_remove_all(client: Client, callback_query: CallbackQuery):
    try:
        chat_id = callback_query.message.chat.id
        removed = await remove_all_filters(chat_id)
        if removed:
            await callback_query.message.edit_text(f"𝖠𝗅𝗅 𝖿𝗂𝗅𝗍𝖾𝗋𝗌 𝗁𝖺𝗏𝖾 𝖻𝖾𝖾𝗇 𝗋𝖾𝗆𝗈𝗏𝖾𝖽 𝗌𝗎𝖼𝖼𝖾𝗌𝗌𝖿𝗎𝗅𝗅𝗒 𝖿𝗋𝗈𝗆 {callback_query.message.chat.title}!")
        else:
            await callback_query.message.edit_text(f"𝖭𝗈 𝖿𝗂𝗅𝗍𝖾𝗋𝗌 𝖿𝗈𝗎𝗇𝖽 𝗍𝗈 𝗋𝖾𝗆𝗈𝗏𝖾 𝗂𝗇 {callback_query.message.chat.title}.")
        await callback_query.answer("All filters removed!", show_alert=False)
    except Exception as e:
        print(f"Error during callback processing: {e}")
        await callback_query.message.edit_text("𝖠𝗇 𝖾𝗋𝗋𝗈𝗋 𝗈𝖼𝖼𝗎𝗋𝗋𝖾𝖽 𝗐𝗁𝗂𝗅𝖾 𝗋𝖾𝗆𝗈𝗏𝗂𝗇𝗀 𝖿𝗂𝗅𝗍𝖾𝗋𝗌.")
        await callback_query.answer("Error occurred!", show_alert=True)


# ——————————————————————————————————————————————————————————————
# The actual keyword -> reply matching handler
# ——————————————————————————————————————————————————————————————
@app.on_message(filters.group & ~filters.command(["add", "filter", "mfilter"]), group=FILTERS_GROUP)
@error
@save
async def filter_response(client: Client, message: Message):
    chat_id = message.chat.id
    text = message.text or message.caption
    if not text:
        return

    normalized_msg = _normalize(text)
    matched = await match_filter(chat_id, normalized_msg, _normalize)
    if not matched:
        return

    trigger, response = matched
    await increment_filter_count(chat_id, trigger)

    reply_text = response.get("reply", "")
    file_id = response.get("file")
    rows = response.get("buttons") or []
    markup = build_markup(rows, trigger)

    reply_id = message.reply_to_message.id if message.reply_to_message else message.id

    sent_msg = None
    try:
        if file_id:
            sent_msg = await client.send_cached_media(
                chat_id, file_id, caption=reply_text or "", reply_markup=markup, reply_to_message_id=reply_id
            )
        else:
            sent_msg = await message.reply(
                reply_text or " ", reply_markup=markup, disable_web_page_preview=True, quote=True
            )
    except Exception as e:
        print(f"Error in filter: {e}")
        return

    is_autodel, del_time = await get_autodelete_settings(chat_id)
    if is_autodel and sent_msg:
        async def _auto_delete():
            await asyncio.sleep(del_time)
            try:
                await sent_msg.delete()
            except Exception:
                pass
        asyncio.create_task(_auto_delete())


# ——————————————————————————————————————————————————————————————
# Alert-button callback ("alertmessage:{index}:{trigger}")
# ——————————————————————————————————————————————————————————————
@app.on_callback_query(filters.regex(r"^alertmessage:"))
@error
async def filter_alert_callback(client: Client, callback_query: CallbackQuery):
    try:
        _, index_str, trigger = callback_query.data.split(":", 2)
        chat_id = callback_query.message.chat.id
        alert_text = await get_alert_text(chat_id, trigger, int(index_str))
        if alert_text:
            await callback_query.answer(alert_text, show_alert=True)
        else:
            await callback_query.answer("This alert is no longer available.", show_alert=True)
    except Exception as e:
        print(f"Error in filter_alert_callback: {e}")
        await callback_query.answer("Something went wrong.", show_alert=True)


# ——————————————————————————————————————————————————————————————
# /autodel on|off [seconds] - auto-delete filter replies after N seconds
# ——————————————————————————————————————————————————————————————
@app.on_message(filters.command("autodel", config.COMMAND_PREFIXES) & filters.group)
@chatadmin
@error
@save
async def set_autodel_cmd(client: Client, message: Message):
    args = message.text.split()
    if len(args) < 2:
        await message.reply(
            "**𝖴𝗌𝖺𝗀𝖾:**\n"
            "🟢 𝖳𝗈 𝗍𝗎𝗋𝗇 𝗈𝗇: `/autodel on [time_in_seconds]`\n"
            "🔴 𝖳𝗈 𝗍𝗎𝗋𝗇 𝗈𝖿𝖿: `/autodel off`\n\n"
            "𝖤𝗑𝖺𝗆𝗉𝗅𝖾: `/autodel on 300` (𝖽𝖾𝗅𝖾𝗍𝖾𝗌 𝖺𝖿𝗍𝖾𝗋 5 𝗆𝗂𝗇𝗎𝗍𝖾𝗌)"
        )
        return

    action = args[1].lower()
    if action == "off":
        _, current_time = await get_autodelete_settings(message.chat.id)
        await set_autodelete_settings(message.chat.id, False, current_time)
        await message.reply("🗑️ **𝖠𝗎𝗍𝗈 𝖽𝖾𝗅𝖾𝗍𝖾 𝗂𝗌 𝗇𝗈𝗐 𝖽𝗂𝗌𝖺𝖻𝗅𝖾𝖽 ❌**")
    elif action == "on":
        if len(args) < 3:
            await message.reply("❌ 𝖯𝗅𝖾𝖺𝗌𝖾 𝗉𝗋𝗈𝗏𝗂𝖽𝖾 𝗍𝗂𝗆𝖾 𝗂𝗇 𝗌𝖾𝖼𝗈𝗇𝖽𝗌! 𝖤𝗑: `/autodel on 30`")
            return
        try:
            seconds = int(args[2])
        except ValueError:
            await message.reply("❌ 𝖳𝗂𝗆𝖾 𝗆𝗎𝗌𝗍 𝖻𝖾 𝖺 𝗇𝗎𝗆𝖻𝖾𝗋 (𝖾.𝗀. 30, 60).")
            return
        await set_autodelete_settings(message.chat.id, True, seconds)
        await message.reply(f"🗑️ **𝖠𝗎𝗍𝗈 𝖽𝖾𝗅𝖾𝗍𝖾 𝗂𝗌 𝗇𝗈𝗐 𝖾𝗇𝖺𝖻𝗅𝖾𝖽 ✅**\n⏳ **𝖳𝗂𝗆𝖾𝗋:** `{seconds}` 𝗌𝖾𝖼𝗈𝗇𝖽𝗌")
    else:
        await message.reply("❓ **𝖨𝗇𝗏𝖺𝗅𝗂𝖽 𝖺𝖼𝗍𝗂𝗈𝗇.** 𝖴𝗌𝖾 `on` 𝗈𝗋 `off`.")


# ——————————————————————————————————————————————————————————————
# /fclone on|off (owner only, toggle) and /fclone source to target (admins)
# ——————————————————————————————————————————————————————————————
@app.on_message(filters.command("fclone", config.COMMAND_PREFIXES))
@error
@save
async def clone_filters_cmd(client: Client, message: Message):
    if not message.from_user:
        return
    userid = message.from_user.id
    args = message.text.split()

    if len(args) == 2 and args[1].lower() in ("on", "off"):
        if message.chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
            await message.reply("⚠️ 𝖯𝗅𝖾𝖺𝗌𝖾 𝗎𝗌𝖾 `/fclone on/off` 𝗂𝗇𝗌𝗂𝖽𝖾 𝗍𝗁𝖾 𝗀𝗋𝗈𝗎𝗉.")
            return
        grp_id = message.chat.id
        if not await _is_group_owner(client, grp_id, userid):
            await message.reply("❌ **𝖮𝗇𝗅𝗒 𝗍𝗁𝖾 𝗀𝗋𝗈𝗎𝗉 𝗈𝗐𝗇𝖾𝗋** 𝖼𝖺𝗇 𝖾𝗇𝖺𝖻𝗅𝖾/𝖽𝗂𝗌𝖺𝖻𝗅𝖾 𝖼𝗅𝗈𝗇𝗂𝗇𝗀!")
            return
        status = args[1].lower() == "on"
        await set_clone_status(grp_id, status)
        state = "𝗈𝗇 🟢" if status else "𝗈𝖿𝖿 🔴"
        await message.reply(f"🔄 **𝖢𝗅𝗈𝗇𝖾 𝖿𝖾𝖺𝗍𝗎𝗋𝖾 𝗂𝗌 𝗇𝗈𝗐 {state} 𝖿𝗈𝗋 𝗍𝗁𝗂𝗌 𝗀𝗋𝗈𝗎𝗉!**")
        return

    if len(args) == 4 and args[2].lower() == "to":
        try:
            source_id = int(args[1])
            target_id = int(args[3])
        except ValueError:
            await message.reply("❌ 𝖨𝗇𝗏𝖺𝗅𝗂𝖽 𝗀𝗋𝗈𝗎𝗉 𝗂𝖽 𝖿𝗈𝗋𝗆𝖺𝗍.")
            return

        if not await get_clone_status(source_id):
            await message.reply(f"🚫 𝖢𝗅𝗈𝗇𝗂𝗇𝗀 𝗂𝗌 **𝗈𝖿𝖿** 𝗂𝗇 𝗍𝗁𝖾 𝗌𝗈𝗎𝗋𝖼𝖾 𝗀𝗋𝗈𝗎𝗉 (`{source_id}`).\n𝖮𝗐𝗇𝖾𝗋 𝗆𝗎𝗌𝗍 𝗍𝗎𝗋𝗇 𝗂𝗍 `/fclone on` 𝖿𝗂𝗋𝗌𝗍.")
            return
        if not await get_clone_status(target_id):
            await message.reply(f"🚫 𝖢𝗅𝗈𝗇𝗂𝗇𝗀 𝗂𝗌 **𝗈𝖿𝖿** 𝗂𝗇 𝗍𝗁𝖾 𝗍𝖺𝗋𝗀𝖾𝗍 𝗀𝗋𝗈𝗎𝗉 (`{target_id}`).\n𝖮𝗐𝗇𝖾𝗋 𝗆𝗎𝗌𝗍 𝗍𝗎𝗋𝗇 𝗂𝗍 `/fclone on` 𝖿𝗂𝗋𝗌𝗍.")
            return

        if not await _is_group_admin(client, source_id, userid):
            await message.reply("❌ 𝖸𝗈𝗎 𝗆𝗎𝗌𝗍 𝖻𝖾 𝖺𝗇 **𝖺𝖽𝗆𝗂𝗇** 𝗈𝗋 **𝗈𝗐𝗇𝖾𝗋** 𝗈𝖿 𝗍𝗁𝖾 𝗌𝗈𝗎𝗋𝖼𝖾 𝗀𝗋𝗈𝗎𝗉!")
            return
        if not await _is_group_admin(client, target_id, userid):
            await message.reply("❌ 𝖸𝗈𝗎 𝗆𝗎𝗌𝗍 𝖻𝖾 𝖺𝗇 **𝖺𝖽𝗆𝗂𝗇** 𝗈𝗋 **𝗈𝗐𝗇𝖾𝗋** 𝗈𝖿 𝗍𝗁𝖾 𝗍𝖺𝗋𝗀𝖾𝗍 𝗀𝗋𝗈𝗎𝗉!")
            return

        wait_msg = await message.reply("⏳ 𝖢𝗅𝗈𝗇𝗂𝗇𝗀 𝖺𝗅𝗅 𝖿𝗂𝗅𝗍𝖾𝗋𝗌... 𝗉𝗅𝖾𝖺𝗌𝖾 𝗐𝖺𝗂𝗍!")
        success, count, skipped_filters = await clone_all_filters(source_id, target_id)

        if success:
            try:
                chat = await client.get_chat(target_id)
                target_title = chat.title
            except Exception:
                target_title = "Unknown group"
            await save_clone_history(source_id, target_id, target_title)

            result_msg = f"✅ **𝖲𝗎𝖼𝖼𝖾𝗌𝗌𝖿𝗎𝗅𝗅𝗒 𝖼𝗅𝗈𝗇𝖾𝖽 {count} 𝖿𝗂𝗅𝗍𝖾𝗋𝗌 𝗍𝗈 𝗍𝖺𝗋𝗀𝖾𝗍 𝗀𝗋𝗈𝗎𝗉!**"
            if skipped_filters:
                skip_text = ", ".join(skipped_filters)
                if len(skip_text) > 2000:
                    skip_text = skip_text[:2000] + "... (truncated)"
                result_msg += f"\n\n⚠️ **𝖲𝗄𝗂𝗉𝗉𝖾𝖽 {len(skipped_filters)} 𝖿𝗂𝗅𝗍𝖾𝗋𝗌 (𝖺𝗅𝗋𝖾𝖺𝖽𝗒 𝖾𝗑𝗂𝗌𝗍):**\n`{skip_text}`"
            await wait_msg.edit(result_msg)
        else:
            await wait_msg.edit("❌ **𝖥𝖺𝗂𝗅𝖾𝖽.** 𝖬𝖺𝗒𝖻𝖾 𝗍𝗁𝖾 𝗌𝗈𝗎𝗋𝖼𝖾 𝗀𝗋𝗈𝗎𝗉 𝗁𝖺𝗌 𝗇𝗈 𝖿𝗂𝗅𝗍𝖾𝗋𝗌.")
        return

    await message.reply(
        "**𝖴𝗌𝖺𝗀𝖾:**\n"
        "➤ `/fclone on/off` (𝗈𝗐𝗇𝖾𝗋 𝗈𝗇𝗅𝗒: 𝖺𝗅𝗅𝗈𝗐𝗌 𝖼𝗅𝗈𝗇𝗂𝗇𝗀)\n"
        "➤ `/fclone source_id to target_id` (𝖺𝖽𝗆𝗂𝗇𝗌: 𝖼𝗅𝗈𝗇𝖾 𝖿𝗂𝗅𝗍𝖾𝗋𝗌)\n"
        "➤ 𝖤𝗑𝖺𝗆𝗉𝗅𝖾: `/fclone -100xxxxxxxxxx to -100xxxxxxxxxx`"
    )


@app.on_message(filters.command("fclones", config.COMMAND_PREFIXES) & filters.group)
@chatowner
@error
@save
async def view_clones_cmd(client: Client, message: Message):
    history = await get_clone_history(message.chat.id)
    if not history:
        await message.reply("❌ 𝖭𝗈 𝖼𝗅𝗈𝗇𝖾 𝗁𝗂𝗌𝗍𝗈𝗋𝗒 𝖿𝗈𝗎𝗇𝖽 𝖿𝗈𝗋 𝗍𝗁𝗂𝗌 𝗀𝗋𝗈𝗎𝗉.")
        return
    text = "📋 **𝖢𝗅𝗈𝗇𝖾 𝗁𝗂𝗌𝗍𝗈𝗋𝗒 𝖿𝗈𝗋 𝗍𝗁𝗂𝗌 𝗀𝗋𝗈𝗎𝗉:**\n\n"
    for idx, row in enumerate(history, 1):
        text += f"{idx}. **{row['title']}**\n└ 𝗂𝖽: `{row['target_id']}`\n\n"
    await message.reply(text)


# ——————————————————————————————————————————————————————————————
# /topfilters - most-used filters in this chat
# ——————————————————————————————————————————————————————————————
@app.on_message(filters.command("topfilters", config.COMMAND_PREFIXES) & filters.group)
@chatadmin
@error
@save
async def top_filters_cmd(client: Client, message: Message):
    top = await get_top_filters(message.chat.id, limit=15)

    if not top:
        await message.reply(f"📉 𝖭𝗈 𝖿𝗂𝗅𝗍𝖾𝗋 𝗎𝗌𝖺𝗀𝖾 𝖽𝖺𝗍𝖺 𝖿𝗈𝗎𝗇𝖽 𝗂𝗇 **{message.chat.title}** 𝗒𝖾𝗍!")
        return

    text = f"🏆 **𝖳𝗈𝗉 𝗆𝗈𝗌𝗍 𝗎𝗌𝖾𝖽 𝖿𝗂𝗅𝗍𝖾𝗋𝗌 𝗂𝗇 {message.chat.title}** 🏆\n\n"
    for i, f in enumerate(top, 1):
        text += f"**{i}.** `{f['text']}` — 🔄 **{f['use_count']}** 𝗍𝗂𝗆𝖾𝗌\n"

    await message.reply(text)


# ——————————————————————————————————————————————————————————————
# /suggestmode on|off - random genre-based filter suggestions
# ——————————————————————————————————————————————————————————————
@app.on_message(filters.command("suggestmode", config.COMMAND_PREFIXES) & filters.group)
@chatadmin
@error
@save
async def suggest_mode_cmd(client: Client, message: Message):
    args = message.text.split()
    if len(args) < 2 or args[1].lower() not in ("on", "off"):
        await message.reply("**𝖴𝗌𝖺𝗀𝖾:** `/suggestmode on` 𝗈𝗋 `/suggestmode off`")
        return

    status = args[1].lower() == "on"
    await set_random_suggest_status(message.chat.id, status)
    state = "𝗈𝗇 🟢" if status else "𝗈𝖿𝖿 🔴"
    await message.reply(f"🎲 **𝖱𝖺𝗇𝖽𝗈𝗆 𝗌𝗎𝗀𝗀𝖾𝗌𝗍𝗂𝗈𝗇 𝗆𝗈𝖽𝖾 𝗂𝗌 𝗇𝗈𝗐 {state}!**")


# ——————————————————————————————————————————————————————————————
# /syncgenre - backfill genre tags for filters added before genre-tagging
# existed (or where the TMDB/AniList lookup failed at add-time)
# ——————————————————————————————————————————————————————————————
@app.on_message(filters.command("syncgenre", config.COMMAND_PREFIXES) & filters.group)
@chatadmin
@error
@save
async def sync_genre_cmd(client: Client, message: Message):
    chat_id = message.chat.id
    pending = await get_filters_missing_genre(chat_id)
    if not pending:
        await message.reply("✅ **𝖠𝗅𝗅 𝖿𝗂𝗅𝗍𝖾𝗋𝗌 𝖺𝗋𝖾 𝖺𝗅𝗋𝖾𝖺𝖽𝗒 𝗀𝖾𝗇𝗋𝖾-𝗍𝖺𝗀𝗀𝖾𝖽.** 𝖭𝗈𝗍𝗁𝗂𝗇𝗀 𝗍𝗈 𝖽𝗈!")
        return

    total = len(pending)
    status_msg = await message.reply(
        f"⏳ **𝖳𝖺𝗀𝗀𝗂𝗇𝗀 𝗀𝖾𝗇𝗋𝖾 𝖿𝗈𝗋 {total} 𝖿𝗂𝗅𝗍𝖾𝗋𝗌...**\n"
        f"𝖳𝗁𝗂𝗌 𝗆𝖺𝗒 𝗍𝖺𝗄𝖾 𝖺 𝗐𝗁𝗂𝗅𝖾, 𝗒𝗈𝗎 𝖽𝗈𝗇'𝗍 𝗇𝖾𝖾𝖽 𝗍𝗈 𝗐𝖺𝗂𝗍 -- 𝗍𝗁𝖾 𝖻𝗈𝗍 𝗐𝗂𝗅𝗅 𝗄𝖾𝖾𝗉 𝗋𝗎𝗇𝗇𝗂𝗇𝗀 𝗇𝗈𝗋𝗆𝖺𝗅𝗅𝗒."
    )

    async def _run_sync():
        tagged = 0
        for i, keyword in enumerate(pending, 1):
            try:
                genres = await fetch_genres(keyword)
                if genres:
                    await set_filter_genre(chat_id, keyword, genres)
                    tagged += 1
            except Exception as sync_error:
                print(f"syncgenre error for '{keyword}': {sync_error}")
            await asyncio.sleep(0.4)  # be gentle on TMDB/AniList rate limits
            if i % 15 == 0 or i == total:
                try:
                    await status_msg.edit_text(f"⏳ **{i}/{total}** 𝗉𝗋𝗈𝖼𝖾𝗌𝗌𝖾𝖽 • {tagged} 𝗍𝖺𝗀𝗀𝖾𝖽 𝗌𝗈 𝖿𝖺𝗋...")
                except Exception:
                    pass
        try:
            await status_msg.edit_text(
                f"✅ **𝖲𝗒𝗇𝖼 𝖼𝗈𝗆𝗉𝗅𝖾𝗍𝖾!**\n\n"
                f"📊 **𝖯𝗋𝗈𝖼𝖾𝗌𝗌𝖾𝖽:** {total}\n"
                f"🏷️ **𝖦𝖾𝗇𝗋𝖾 𝗍𝖺𝗀𝗀𝖾𝖽:** {tagged}\n"
                f"❌ **𝖭𝗈 𝗆𝖺𝗍𝖼𝗁 𝖿𝗈𝗎𝗇𝖽:** {total - tagged}\n\n"
                f"𝖭𝗈𝗐 `/suggestmode` 𝗀𝖾𝗇𝗋𝖾 𝗆𝖺𝗍𝖼𝗁𝗂𝗇𝗀 𝗐𝗂𝗅𝗅 𝗐𝗈𝗋𝗄 𝖿𝗈𝗋 𝗍𝗁𝖾𝗌𝖾 𝖿𝗂𝗅𝗍𝖾𝗋𝗌."
            )
        except Exception:
            pass

    asyncio.create_task(_run_sync())


# ——————————————————————————————————————————————————————————————
# Random genre-based suggestion trigger (only active when /suggestmode is on)
# ——————————————————————————————————————————————————————————————
@app.on_message(filters.group & filters.text, group=SUGGEST_MODE_GROUP)
@error
@save
async def random_suggest_trigger(client: Client, message: Message):
    chat_id = message.chat.id

    is_active = await get_random_suggest_status(chat_id)
    if not is_active:
        return

    text = message.text.lower()
    matched_genre = detect_genre(text)

    trigger_words = [
        "suggest", "best", "recommend", "recommendations", "suggestion",
        "any good", "any idea", "something new", "ki dekhabo", "kuch achha",
        "kuch naya", "koi achha", "kya dekhen",
    ]
    generic_trigger = any(word in text for word in trigger_words)

    if not matched_genre and not generic_trigger:
        return

    reply_id = message.reply_to_message.id if message.reply_to_message else message.id
    picked_filter = None
    label = "🎲 **𝖱𝖺𝗇𝖽𝗈𝗆 𝗌𝗎𝗀𝗀𝖾𝗌𝗍𝗂𝗈𝗇:**"

    if matched_genre:
        picked_filter = await get_random_filter_by_genre(chat_id, matched_genre)
        if picked_filter:
            label = f"🎯 **{matched_genre.title()} 𝗌𝗎𝗀𝗀𝖾𝗌𝗍𝗂𝗈𝗇:**"
        else:
            # Most filters simply have no genre tag yet - say so plainly
            # instead of silently falling back to an unrelated random filter.
            is_admin = False
            userid = message.from_user.id if message.from_user else None
            if userid:
                is_admin = await _is_group_admin(client, chat_id, userid)
            if is_admin:
                await message.reply(
                    f"😕 No filter is tagged with the `{matched_genre.title()}` genre yet.\n"
                    f"➤ Run `/syncgenre` to tag all older filters with their genre.",
                    quote=True
                )
            else:
                await message.reply(f"😕 No `{matched_genre.title()}` filter found right now. Try another genre!", quote=True)
            return

    if not picked_filter:
        picked_filter = await get_random_filter(chat_id)
    if not picked_filter:
        return

    reply_text = picked_filter.get("reply", "")
    file_id = picked_filter.get("file")
    rows = picked_filter.get("buttons") or []
    markup = build_markup(rows, picked_filter.get("text", ""))
    reply_text = f"{label}\n\n{reply_text}" if reply_text else label

    is_autodel, del_time = await get_autodelete_settings(chat_id)

    try:
        if file_id:
            sent_msg = await client.send_cached_media(chat_id, file_id, caption=reply_text, reply_markup=markup, reply_to_message_id=reply_id)
        else:
            sent_msg = await client.send_message(chat_id, reply_text, disable_web_page_preview=True, reply_markup=markup, reply_to_message_id=reply_id)

        if is_autodel and sent_msg:
            async def _auto_delete():
                await asyncio.sleep(del_time)
                try:
                    await sent_msg.delete()
                except Exception:
                    pass
            asyncio.create_task(_auto_delete())
    except Exception as e:
        print(f"Error in random suggestion: {e}")


__module__ = "𝖥𝗂𝗅𝗍𝖾𝗋𝗌"

__help__ = """**𝖴𝗌𝖾𝗋 𝖢𝗈𝗆𝗆𝖺𝗇𝖽𝗌 (𝖺𝖽𝗆𝗂𝗇𝗌):**
   ✧ `/add <keyword> <reply>` (𝖺𝗅𝗂𝖺𝗌 `/filter`) **:** 𝖲𝖾𝗍𝗌 𝖺 𝖿𝗂𝗅𝗍𝖾𝗋. 𝖠𝗅𝗌𝗈 𝗐𝗈𝗋𝗄𝗌 𝗈𝗇 𝗋𝖾𝗉𝗅𝗂𝖾𝗌 𝗍𝗈 𝗍𝖾𝗑𝗍/𝗆𝖾𝖽𝗂𝖺/𝖻𝗎𝗍𝗍𝗈𝗇𝗌.
   ✧ `/stop <keyword>` **:** 𝖱𝖾𝗆𝗈𝗏𝖾𝗌 𝗈𝗇𝖾 𝖿𝗂𝗅𝗍𝖾𝗋.
   ✧ `/filters` **:** 𝖫𝗂𝗌𝗍𝗌 𝖺𝗅𝗅 𝖺𝖼𝗍𝗂𝗏𝖾 𝖿𝗂𝗅𝗍𝖾𝗋𝗌.
   ✧ `/delall` (𝖺𝗅𝗂𝖺𝗌 `/stopall`, 𝗈𝗐𝗇𝖾𝗋 𝗈𝗇𝗅𝗒) **:** 𝖱𝖾𝗆𝗈𝗏𝖾𝗌 𝖤𝖵𝖤𝖱𝖸 𝖿𝗂𝗅𝗍𝖾𝗋 (𝖺𝗌𝗄𝗌 𝖿𝗈𝗋 𝖼𝗈𝗇𝖿𝗂𝗋𝗆𝖺𝗍𝗂𝗈𝗇).
   ✧ `/autodel on <seconds>` / `/autodel off` **:** 𝖠𝗎𝗍𝗈-𝖽𝖾𝗅𝖾𝗍𝖾 𝖿𝗂𝗅𝗍𝖾𝗋 𝗋𝖾𝗉𝗅𝗂𝖾𝗌 𝖺𝖿𝗍𝖾𝗋 𝖭 𝗌𝖾𝖼𝗈𝗇𝖽𝗌.
   ✧ `/topfilters` **:** 𝖲𝗁𝗈𝗐𝗌 𝗍𝗁𝖾 𝗆𝗈𝗌𝗍-𝗎𝗌𝖾𝖽 𝖿𝗂𝗅𝗍𝖾𝗋𝗌 𝗂𝗇 𝗍𝗁𝗂𝗌 𝖼𝗁𝖺𝗍.
   ✧ `/fclone on/off` **:** (𝗈𝗐𝗇𝖾𝗋 𝗈𝗇𝗅𝗒) 𝖠𝗅𝗅𝗈𝗐/𝖽𝗂𝗌𝖺𝗅𝗅𝗈𝗐 𝗍𝗁𝗂𝗌 𝗀𝗋𝗈𝗎𝗉'𝗌 𝖿𝗂𝗅𝗍𝖾𝗋𝗌 𝗍𝗈 𝖻𝖾 𝖼𝗅𝗈𝗇𝖾𝖽.
   ✧ `/fclone <source_id> to <target_id>` **:** 𝖢𝗅𝗈𝗇𝖾𝗌 𝖺𝗅𝗅 𝖿𝗂𝗅𝗍𝖾𝗋𝗌 𝖿𝗋𝗈𝗆 𝗈𝗇𝖾 𝗀𝗋𝗈𝗎𝗉 𝗍𝗈 𝖺𝗇𝗈𝗍𝗁𝖾𝗋 (𝗇𝖾𝖾𝖽𝗌 𝖼𝗅𝗈𝗇𝗂𝗇𝗀 𝗈𝗇 𝗂𝗇 𝖻𝗈𝗍𝗁).
   ✧ `/fclones` (𝗈𝗐𝗇𝖾𝗋 𝗈𝗇𝗅𝗒) **:** 𝖵𝗂𝖾𝗐𝗌 𝗍𝗁𝗂𝗌 𝗀𝗋𝗈𝗎𝗉'𝗌 𝖼𝗅𝗈𝗇𝖾 𝗁𝗂𝗌𝗍𝗈𝗋𝗒.
   ✧ `/suggestmode on/off` **:** 𝖱𝖺𝗇𝖽𝗈𝗆𝗅𝗒 𝗌𝗎𝗀𝗀𝖾𝗌𝗍𝗌 𝖺 𝖿𝗂𝗅𝗍𝖾𝗋 𝗐𝗁𝖾𝗇 𝗌𝗈𝗆𝖾𝗈𝗇𝖾 𝖺𝗌𝗄𝗌 𝖿𝗈𝗋 𝗋𝖾𝖼𝗈𝗆𝗆𝖾𝗇𝖽𝖺𝗍𝗂𝗈𝗇𝗌 𝗈𝗋 𝗆𝖾𝗇𝗍𝗂𝗈𝗇𝗌 𝖺 𝗀𝖾𝗇𝗋𝖾.
   ✧ `/syncgenre` **:** 𝖳𝖺𝗀𝗌 𝗀𝖾𝗇𝗋𝖾𝗌 𝗈𝗇𝗍𝗈 𝗈𝗅𝖽𝖾𝗋 𝖿𝗂𝗅𝗍𝖾𝗋𝗌 𝗌𝗈 `/suggestmode` 𝖼𝖺𝗇 𝗆𝖺𝗍𝖼𝗁 𝗍𝗁𝖾𝗆.

**𝖠𝖽𝖽𝗂𝗇𝗀 𝖡𝗎𝗍𝗍𝗈𝗇𝗌 𝗍𝗈 𝖺 𝖥𝗂𝗅𝗍𝖾𝗋:**
   ✧ `[button text](buttonurl:https://example.com)` **:** 𝖠𝖽𝖽𝗌 𝖺 𝗎𝗋𝗅 𝖻𝗎𝗍𝗍𝗈𝗇 𝗈𝗇 𝗂𝗍𝗌 𝗈𝗐𝗇 𝗋𝗈𝗐.
   ✧ `[text](buttonurl:https://example.com:same)` **:** 𝖠𝖽𝖽𝗌 𝗂𝗍 𝗇𝖾𝗑𝗍 𝗍𝗈 𝗍𝗁𝖾 𝗉𝗋𝖾𝗏𝗂𝗈𝗎𝗌 𝖻𝗎𝗍𝗍𝗈𝗇, 𝗌𝖺𝗆𝖾 𝗋𝗈𝗐.
   ✧ `[text](buttonalert:popup message)` **:** 𝖠𝖽𝖽𝗌 𝖺 𝖻𝗎𝗍𝗍𝗈𝗇 𝗍𝗁𝖺𝗍 𝗌𝗁𝗈𝗐𝗌 𝖺 𝗉𝗈𝗉𝗎𝗉 𝖺𝗅𝖾𝗋𝗍 𝗂𝗇𝗌𝗍𝖾𝖺𝖽 𝗈𝖿 𝗈𝗉𝖾𝗇𝗂𝗇𝗀 𝖺 𝗅𝗂𝗇𝗄.

𝖠𝖽𝗆𝗂𝗇𝗌 𝖺𝗇𝖽 𝗍𝗁𝖾 𝖼𝗁𝖺𝗍 𝗈𝗐𝗇𝖾𝗋 𝖼𝖺𝗇 𝗆𝖺𝗇𝖺𝗀𝖾 𝗍𝗁𝖾𝗌𝖾 𝖿𝗂𝗅𝗍𝖾𝗋𝗌 𝗍𝗈 𝖼𝗈𝗇𝗍𝗋𝗈𝗅 𝖺𝗇𝖽 𝖺𝗎𝗍𝗈𝗆𝖺𝗍𝖾 𝗋𝖾𝗌𝗉𝗈𝗇𝗌𝖾𝗌 𝗂𝗇 𝗍𝗁𝖾 𝖼𝗁𝖺𝗍.
"""
