from pyrogram import filters, Client
from pyrogram.types import Message, ChatJoinRequest, InlineKeyboardMarkup, InlineKeyboardButton

from Nobara import app, JOIN_UPDATE_GROUP
from Nobara.decorator.chatadmin import chatadmin
from Nobara.decorator.errors import error
from Nobara.decorator.save import save
from Nobara.database.joinreqdb import set_auto_accept, is_auto_accept_enabled
from Nobara.helper.log_helper import send_log, format_log
from config import config


# /autoaccept on|off - toggles automatic approval of join requests for this group
@app.on_message(filters.command("autoaccept", prefixes=config.COMMAND_PREFIXES) & filters.group)
@chatadmin
@error
@save
async def autoaccept_command(client: Client, message: Message):
    chat_id = message.chat.id

    if len(message.command) < 2 or message.command[1].lower() not in ("on", "off"):
        current = await is_auto_accept_enabled(chat_id)
        status = "𝖮𝖭 ✅" if current else "𝖮𝖥𝖥 ❌"
        await message.reply(
            f"𝖠𝗎𝗍𝗈 𝖩𝗈𝗂𝗇 𝖱𝖾𝗊𝗎𝖾𝗌𝗍 𝖠𝖼𝖼𝖾𝗉𝗍 𝗂𝗌 𝖼𝗎𝗋𝗋𝖾𝗇𝗍𝗅𝗒: {status}\n\n"
            "𝖴𝗌𝖺𝗀𝖾: `/autoaccept on` 𝗈𝗋 `/autoaccept off`"
        )
        return

    enable = message.command[1].lower() == "on"
    await set_auto_accept(chat_id, enable)

    if enable:
        await message.reply("✅ **𝖠𝗎𝗍𝗈 𝖩𝗈𝗂𝗇 𝖱𝖾𝗊𝗎𝖾𝗌𝗍 𝖠𝖼𝖼𝖾𝗉𝗍 𝗂𝗌 𝗇𝗈𝗐 𝖤𝗇𝖺𝖻𝗅𝖾𝖽.**\n𝖤𝗏𝖾𝗋𝗒 𝗇𝖾𝗐 𝗃𝗈𝗂𝗇 𝗋𝖾𝗊𝗎𝖾𝗌𝗍 𝗐𝗂𝗅𝗅 𝖻𝖾 𝖺𝗉𝗉𝗋𝗈𝗏𝖾𝖽 𝖺𝗎𝗍𝗈𝗆𝖺𝗍𝗂𝖼𝖺𝗅𝗅𝗒.")
    else:
        await message.reply("❌ **𝖠𝗎𝗍𝗈 𝖩𝗈𝗂𝗇 𝖱𝖾𝗊𝗎𝖾𝗌𝗍 𝖠𝖼𝖼𝖾𝗉𝗍 𝗂𝗌 𝗇𝗈𝗐 𝖣𝗂𝗌𝖺𝖻𝗅𝖾𝖽.**\n𝖩𝗈𝗂𝗇 𝗋𝖾𝗊𝗎𝖾𝗌𝗍𝗌 𝗐𝗂𝗅𝗅 𝗇𝗈 𝗅𝗈𝗇𝗀𝖾𝗋 𝖻𝖾 𝖺𝗎𝗍𝗈-𝖺𝗉𝗉𝗋𝗈𝗏𝖾𝖽.")


# Silently auto-approves join requests for groups where it's enabled, then
# DMs the user an approval notice. No "Join" button here (they're already
# approved) - instead a "Powered By" button pointing at the bot's own
# /start, so tapping it adds them to Nobara's user DB for future broadcasts.
@app.on_chat_join_request(group=JOIN_UPDATE_GROUP)
async def join_request_handler(c: Client, j: ChatJoinRequest):
    chat_id = j.chat.id

    # Log the request itself regardless of auto-accept status
    try:
        invite_from = None
        if j.invite_link and j.invite_link.creator:
            creator = j.invite_link.creator
            invite_from = f"{creator.first_name or 'Unknown'} (ID: {creator.id})"

        log_message = await format_log(
            tag="JOINREQUEST",
            chat=j.chat.title,
            user=(j.from_user.first_name or "User", j.from_user.id),
            extra={"Invitelink from": invite_from} if invite_from else None,
            note="User has requested to join the chat.",
        )
        await send_log(chat_id, log_message)
    except Exception:
        pass

    if not await is_auto_accept_enabled(chat_id):
        return

    try:
        await c.approve_chat_join_request(chat_id, j.from_user.id)
    except Exception:
        return

    try:
        bot_username = getattr(config, "BOT_USERNAME", None) or c.me.username
        powered_by = InlineKeyboardMarkup(
            [[InlineKeyboardButton("⚡ 𝖯𝗈𝗐𝖾𝗋𝖾𝖽 𝖡𝗒", url=f"https://t.me/{bot_username}?start=powered")]]
        )
        await c.send_message(
            j.from_user.id,
            f"✅ **𝖸𝗈𝗎𝗋 𝗋𝖾𝗊𝗎𝖾𝗌𝗍 𝗍𝗈 𝗃𝗈𝗂𝗇 {j.chat.title} 𝗁𝖺𝗌 𝖻𝖾𝖾𝗇 𝖺𝗉𝗉𝗋𝗈𝗏𝖾𝖽!**",
            reply_markup=powered_by
        )
    except Exception:
        pass  # user may have their DMs closed to the bot - that's fine, they're still approved


__module__ = "𝖩𝗈𝗂𝗇 𝖱𝖾𝗊𝗎𝖾𝗌𝗍"


__help__ = """**𝖢𝗁𝖺𝗍 𝖠𝖽𝗆𝗂𝗇 𝖢𝗈𝗆𝗆𝖺𝗇𝖽𝗌:**
   ✧ `/autoaccept on`**:** 𝖠𝗎𝗍𝗈𝗆𝖺𝗍𝗂𝖼𝖺𝗅𝗅𝗒 𝖺𝖼𝖼𝖾𝗉𝗍𝗌 𝖾𝗏𝖾𝗋𝗒 𝗇𝖾𝗐 𝗃𝗈𝗂𝗇 𝗋𝖾𝗊𝗎𝖾𝗌𝗍 𝗂𝗇 𝗍𝗁𝗂𝗌 𝗀𝗋𝗈𝗎𝗉 (𝗐𝗁𝖾𝗋𝖾 𝗆𝖾𝗆𝖻𝖾𝗋 𝖺𝗉𝗉𝗋𝗈𝗏𝖺𝗅 𝗂𝗌 𝖾𝗇𝖺𝖻𝗅𝖾𝖽), 𝗇𝗈 𝖺𝖽𝗆𝗂𝗇 𝖺𝖼𝗍𝗂𝗈𝗇 𝗇𝖾𝖾𝖽𝖾𝖽. 𝖳𝗁𝖾 𝗎𝗌𝖾𝗋 𝗀𝖾𝗍𝗌 𝖺 𝖣𝖬 𝖼𝗈𝗇𝖿𝗂𝗋𝗆𝗂𝗇𝗀 𝖺𝗉𝗉𝗋𝗈𝗏𝖺𝗅 (𝗐𝗂𝗍𝗁 𝖺 "Powered By" 𝖻𝗎𝗍𝗍𝗈𝗇, 𝗇𝗈 𝗃𝗈𝗂𝗇 𝖻𝗎𝗍𝗍𝗈𝗇 𝗌𝗂𝗇𝖼𝖾 𝗍𝗁𝖾𝗒'𝗋𝖾 𝖺𝗅𝗋𝖾𝖺𝖽𝗒 𝗂𝗇).
   ✧ `/autoaccept off`**:** 𝖳𝗎𝗋𝗇𝗌 𝗂𝗍 𝖻𝖺𝖼𝗄 𝗈𝖿𝖿.
   ✧ `/autoaccept`**:** 𝖲𝗁𝗈𝗐𝗌 𝗍𝗁𝖾 𝖼𝗎𝗋𝗋𝖾𝗇𝗍 𝗌𝗍𝖺𝗍𝗎𝗌 𝖿𝗈𝗋 𝗍𝗁𝗂𝗌 𝗀𝗋𝗈𝗎𝗉.

𝖮𝗇𝗅𝗒 𝗀𝗋𝗈𝗎𝗉 𝖺𝖽𝗆𝗂𝗇𝗌 𝖼𝖺𝗇 𝗎𝗌𝖾 𝗍𝗁𝗂𝗌 𝖼𝗈𝗆𝗆𝖺𝗇𝖽. 𝖤𝖺𝖼𝗁 𝗀𝗋𝗈𝗎𝗉'𝗌 𝗌𝖾𝗍𝗍𝗂𝗇𝗀 𝗂𝗌 𝗂𝗇𝖽𝖾𝗉𝖾𝗇𝖽𝖾𝗇𝗍.
"""
