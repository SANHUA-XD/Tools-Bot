import logging
from pyrogram import Client, filters, enums
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from Nobara import app
from config import config
from Nobara.decorator.botadmin import hokage
from Nobara.decorator.errors import error
from Nobara.decorator.save import save
from Nobara.database.blockedchatsdb import (
    block_chat, unblock_chat, is_chat_blocked, get_all_blocked_chats
)
from Nobara.database.total_user_chat_db import remove_chat

log = logging.getLogger(__name__)

# ==========================================
# 🚫 ব্ল্যাকলিস্টেড গ্রুপ লিভ প্রসেস (INSTANT)
# ==========================================

async def process_leave_blocked_group(client: Client, chat_id: int):
    """ব্ল্যাকলিস্টেড গ্রুপ থেকে কন্ট্যাক্ট-বাটনসহ মেসেজ দিয়ে সাথে সাথে লিভ নেয়"""
    try:
        buttons = InlineKeyboardMarkup(
            [[InlineKeyboardButton("👨‍💻 𝖢𝗈𝗇𝗍𝖺𝖼𝗍 𝖠𝖽𝗆𝗂𝗇", url=config.SUPPORT_CHAT_LINK)]]
        )

        try:
            await client.send_message(
                chat_id,
                "❌ **𝖳𝗁𝗂𝗌 𝗀𝗋𝗈𝗎𝗉 𝗂𝗌 𝖻𝗅𝖺𝖼𝗄𝗅𝗂𝗌𝗍𝖾𝖽! 𝖨 𝖼𝖺𝗇𝗇𝗈𝗍 𝗌𝗍𝖺𝗒 𝗁𝖾𝗋𝖾.**",
                reply_markup=buttons
            )
        except Exception:
            pass

        await client.leave_chat(chat_id)
        await remove_chat(chat_id)

        log.info(f"Auto-left blacklisted group: {chat_id}")
    except Exception as e:
        log.error(f"Leave error for blocked group {chat_id}: {e}")


# ——————————————————————————————————————————————————————————————
# 🚫 নতুন গ্রুপে অ্যাড হলে সাথে সাথে চেক করে - ব্ল্যাকলিস্টেড হলে লিভ
# ——————————————————————————————————————————————————————————————

@app.on_message(filters.group & filters.new_chat_members)
@error
async def instant_leave_blocked_groups(client: Client, message: Message):
    bot = await client.get_me()
    for member in message.new_chat_members:
        if member.id == bot.id:
            chat_id = message.chat.id
            if await is_chat_blocked(chat_id):
                await process_leave_blocked_group(client, chat_id)
            break


# ——————————————————————————————————————————————————————————————
# 🛠 বট-ওনার/হোকাগে-অনলি কমান্ডস
# ——————————————————————————————————————————————————————————————

@app.on_message(filters.command("leave", prefixes=config.COMMAND_PREFIXES))
@hokage
@error
@save
async def leave_group_cmd(client: Client, message: Message):
    chat_id = message.chat.id

    if len(message.command) > 1:
        try:
            chat_id = int(message.command[1])
        except ValueError:
            await message.reply("❗ **𝖨𝗇𝗏𝖺𝗅𝗂𝖽 𝖼𝗁𝖺𝗍 𝖨𝖣.**")
            return

    try:
        if chat_id != message.from_user.id:
            try:
                await client.send_message(chat_id, "👋 **𝖬𝗒 𝖺𝖽𝗆𝗂𝗇 𝖺𝗌𝗄𝖾𝖽 𝗆𝖾 𝗍𝗈 𝗅𝖾𝖺𝗏𝖾 𝗍𝗁𝗂𝗌 𝗀𝗋𝗈𝗎𝗉. 𝖦𝗈𝗈𝖽𝖻𝗒𝖾!**")
            except Exception:
                pass

        await client.leave_chat(chat_id)
        await remove_chat(chat_id)

        if message.chat.id != chat_id:
            await message.reply(f"✅ **𝖲𝗎𝖼𝖼𝖾𝗌𝗌𝖿𝗎𝗅𝗅𝗒 𝗅𝖾𝖿𝗍:** `{chat_id}`")
    except Exception as e:
        await message.reply(f"❌ **𝖤𝗋𝗋𝗈𝗋:** `{e}`")


@app.on_message(filters.command("blockchat", prefixes=config.COMMAND_PREFIXES))
@hokage
@error
@save
async def block_group_cmd(client: Client, message: Message):
    chat_id = message.chat.id

    if len(message.command) > 1:
        try:
            chat_id = int(message.command[1])
        except ValueError:
            await message.reply("❗ **𝖯𝗅𝖾𝖺𝗌𝖾 𝗉𝗋𝗈𝗏𝗂𝖽𝖾 𝖺 𝗏𝖺𝗅𝗂𝖽 𝗇𝗎𝗆𝖾𝗋𝗂𝖼 𝖼𝗁𝖺𝗍 𝖨𝖣.**")
            return
    elif message.chat.type == enums.ChatType.PRIVATE:
        await message.reply("💡 **𝖴𝗌𝖺𝗀𝖾 𝗂𝗇 𝖯𝖬:** `/blockchat <chat_id>`")
        return

    try:
        await block_chat(chat_id)
        await process_leave_blocked_group(client, chat_id)

        if message.chat.id != chat_id:
            await message.reply(f"✅ **𝖢𝗁𝖺𝗍 𝖻𝗅𝗈𝖼𝗄𝖾𝖽 & 𝗅𝖾𝖿𝗍 𝗉𝖾𝗋𝗆𝖺𝗇𝖾𝗇𝗍𝗅𝗒:** `{chat_id}`")
        else:
            try:
                await client.send_message(message.from_user.id, f"✅ **𝖢𝗁𝖺𝗍 𝖻𝗅𝗈𝖼𝗄𝖾𝖽 & 𝗅𝖾𝖿𝗍 𝗉𝖾𝗋𝗆𝖺𝗇𝖾𝗇𝗍𝗅𝗒:** `{chat_id}`")
            except Exception:
                pass
    except Exception as e:
        await message.reply(f"❌ **𝖤𝗋𝗋𝗈𝗋:** `{e}`")


@app.on_message(filters.command("unblockchat", prefixes=config.COMMAND_PREFIXES))
@hokage
@error
@save
async def unblock_group_cmd(client: Client, message: Message):
    chat_id = message.chat.id

    if len(message.command) > 1:
        try:
            chat_id = int(message.command[1])
        except ValueError:
            await message.reply("❗ **𝖯𝗅𝖾𝖺𝗌𝖾 𝗉𝗋𝗈𝗏𝗂𝖽𝖾 𝖺 𝗏𝖺𝗅𝗂𝖽 𝗇𝗎𝗆𝖾𝗋𝗂𝖼 𝖼𝗁𝖺𝗍 𝖨𝖣.**")
            return
    elif message.chat.type == enums.ChatType.PRIVATE:
        await message.reply("💡 **𝖴𝗌𝖺𝗀𝖾 𝗂𝗇 𝖯𝖬:** `/unblockchat <chat_id>`")
        return

    try:
        await unblock_chat(chat_id)
        await message.reply(f"✅ **𝖢𝗁𝖺𝗍 𝗎𝗇𝖻𝗅𝗈𝖼𝗄𝖾𝖽 𝗌𝗎𝖼𝖼𝖾𝗌𝗌𝖿𝗎𝗅𝗅𝗒:** `{chat_id}`")
    except Exception as e:
        await message.reply(f"❌ **𝖤𝗋𝗋𝗈𝗋:** `{e}`")


@app.on_message(filters.command(["blocklist", "blockedchats"], prefixes=config.COMMAND_PREFIXES))
@hokage
@error
@save
async def view_blocklist_cmd(client: Client, message: Message):
    try:
        blocked = await get_all_blocked_chats()

        if not blocked:
            await message.reply("✅ **𝖭𝗈 𝗀𝗋𝗈𝗎𝗉𝗌 𝖺𝗋𝖾 𝖼𝗎𝗋𝗋𝖾𝗇𝗍𝗅𝗒 𝖻𝗅𝖺𝖼𝗄𝗅𝗂𝗌𝗍𝖾𝖽.**")
            return

        text = "🚫 **𝖡𝗅𝖺𝖼𝗄𝗅𝗂𝗌𝗍𝖾𝖽 𝖦𝗋𝗈𝗎𝗉𝗌 𝖫𝗂𝗌𝗍:**\n━━━━━━━━━━━━━━━━━━━━\n"
        for idx, chat in enumerate(blocked, start=1):
            text += f"**{idx}.**  `{chat['chat_id']}`\n"
        text += "━━━━━━━━━━━━━━━━━━━━\n💡 *𝖴𝗌𝖾* `/unblockchat <id>` *𝗍𝗈 𝗋𝖾𝗆𝗈𝗏𝖾.*"

        await message.reply(text)
    except Exception as e:
        await message.reply(f"❌ **𝖤𝗋𝗋𝗈𝗋 𝖿𝖾𝗍𝖼𝗁𝗂𝗇𝗀 𝗅𝗂𝗌𝗍:** `{e}`")


__module__ = "𝖦𝖢 𝖫𝖾𝖺𝗏𝖾"


__help__ = """**𝖮𝗐𝗇𝖾𝗋/𝖧𝗈𝗄𝖺𝗀𝖾 𝖢𝗈𝗆𝗆𝖺𝗇𝖽𝗌:**
   ✧ `/𝗅𝖾𝖺𝗏𝖾 [𝖼𝗁𝖺𝗍_𝗂𝖽]`**:** 𝖬𝖺𝗄𝖾𝗌 𝗍𝗁𝖾 𝖻𝗈𝗍 𝗅𝖾𝖺𝗏𝖾 𝗍𝗁𝖾 𝖼𝗎𝗋𝗋𝖾𝗇𝗍 𝗀𝗋𝗈𝗎𝗉, 𝗈𝗋 𝖺 𝗌𝗉𝖾𝖼𝗂𝖿𝗂𝖾𝖽 𝗈𝗇𝖾.
   ✧ `/𝖻𝗅𝗈𝖼𝗄𝖼𝗁𝖺𝗍 [𝖼𝗁𝖺𝗍_𝗂𝖽]`**:** 𝖡𝗅𝖺𝖼𝗄𝗅𝗂𝗌𝗍𝗌 𝖺 𝗀𝗋𝗈𝗎𝗉 𝖺𝗇𝖽 𝗅𝖾𝖺𝗏𝖾𝗌 𝗂𝗍 𝗂𝗆𝗆𝖾𝖽𝗂𝖺𝗍𝖾𝗅𝗒. 𝖳𝗁𝖾 𝖻𝗈𝗍 𝖺𝗎𝗍𝗈-𝗅𝖾𝖺𝗏𝖾𝗌 𝗂𝖿 𝖾𝗏𝖾𝗋 𝗋𝖾-𝖺𝖽𝖽𝖾𝖽 𝗍𝗈 𝗂𝗍.
   ✧ `/𝗎𝗇𝖻𝗅𝗈𝖼𝗄𝖼𝗁𝖺𝗍 <𝖼𝗁𝖺𝗍_𝗂𝖽>`**:** 𝖱𝖾𝗆𝗈𝗏𝖾𝗌 𝖺 𝗀𝗋𝗈𝗎𝗉 𝖿𝗋𝗈𝗆 𝗍𝗁𝖾 𝖻𝗅𝖺𝖼𝗄𝗅𝗂𝗌𝗍.
   ✧ `/𝖻𝗅𝗈𝖼𝗄𝗅𝗂𝗌𝗍` 𝗈𝗋 `/𝖻𝗅𝗈𝖼𝗄𝖾𝖽𝖼𝗁𝖺𝗍𝗌`**:** 𝖲𝗁𝗈𝗐𝗌 𝖺𝗅𝗅 𝖼𝗎𝗋𝗋𝖾𝗇𝗍𝗅𝗒 𝖻𝗅𝖺𝖼𝗄𝗅𝗂𝗌𝗍𝖾𝖽 𝗀𝗋𝗈𝗎𝗉𝗌.

𝖮𝗇𝗅𝗒 𝗍𝗁𝖾 𝖻𝗈𝗍 𝗈𝗐𝗇𝖾𝗋 𝖺𝗇𝖽 𝖧𝗈𝗄𝖺𝗀𝖾-𝗋𝗈𝗅𝖾 𝗎𝗌𝖾𝗋𝗌 𝖼𝖺𝗇 𝗎𝗌𝖾 𝗍𝗁𝖾𝗌𝖾 𝖼𝗈𝗆𝗆𝖺𝗇𝖽𝗌.
"""
