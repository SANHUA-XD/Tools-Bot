from pyrogram import Client, filters
from pyrogram.types import Message, ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from pyrogram.enums import ChatType, ChatMemberStatus

from TianXiwei import app
from TianXiwei.Database.lockdb import get_locks, set_lock, unset_lock
from TianXiwei.Functions.lock_helper import LOCKABLES, LOCK_CHAT_RESTRICTION, UNLOCK_CHAT_RESTRICTION
from TianXiwei.Database.approve_db import is_user_approved
from TianXiwei.Functions.user import is_user_admin
from config import config

@app.on_message(filters.command("lock", prefixes=config.COMMAND_PREFIXES) & filters.group)
async def lock_command(client: Client, message: Message):
    if not await is_user_admin(client, message.chat.id, message.from_user.id):
        await message.reply_text("🚫 You must be an administrator to use this command.")
        return

    if len(message.command) < 2:
        await message.reply_text("Please specify a lock type. Example: `/lock text`")
        return

    lock_type = message.command[1].lower()

    if lock_type not in LOCKABLES and lock_type != "all":
        await message.reply_text(f"Invalid lock type. Valid types are: {', '.join(LOCKABLES)}")
        return

    await set_lock(message.chat.id, lock_type)

    if lock_type == "all":
        await message.reply_text("All locks have been enabled.")
    else:
        await message.reply_text(f"Lock `{lock_type}` has been enabled.")

@app.on_message(filters.command("unlock", prefixes=config.COMMAND_PREFIXES) & filters.group)
async def unlock_command(client: Client, message: Message):
    if not await is_user_admin(client, message.chat.id, message.from_user.id):
        await message.reply_text("🚫 You must be an administrator to use this command.")
        return

    if len(message.command) < 2:
        await message.reply_text("Please specify a lock type. Example: `/unlock text`")
        return

    lock_type = message.command[1].lower()

    if lock_type not in LOCKABLES and lock_type != "all":
        await message.reply_text(f"Invalid lock type. Valid types are: {', '.join(LOCKABLES)}")
        return

    await unset_lock(message.chat.id, lock_type)

    if lock_type == "all":
        await message.reply_text("All locks have been disabled.")
    else:
        await message.reply_text(f"Lock `{lock_type}` has been disabled.")

@app.on_message(filters.command("locks", prefixes=config.COMMAND_PREFIXES) & filters.group)
async def locks_command(client: Client, message: Message):
    if not await is_user_admin(client, message.chat.id, message.from_user.id):
        await message.reply_text("🚫 You must be an administrator to use this command.")
        return

    locks = await get_locks(message.chat.id)

    if not locks:
        await message.reply_text("No locks are enabled in this chat.")
        return

    await message.reply_text(f"Enabled locks in this chat:\n\n{', '.join(locks)}")

@app.on_message(filters.command("locktypes", prefixes=config.COMMAND_PREFIXES) & filters.group)
async def locktypes_command(client: Client, message: Message):
    lockables = list(LOCKABLES.items())

    # Create rows of 3 buttons each
    keyboard = [
        [
            InlineKeyboardButton(
                text=lock_type.capitalize(),
                callback_data=f"locktype_{lock_type}"
            )
            for lock_type, _ in lockables[i:i + 3]
        ]
        for i in range(0, len(lockables), 3)
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await message.reply_text(
        "📜 *Available Lock Types:*\nTap a button to view the description.",
        reply_markup=reply_markup,
    )

@app.on_callback_query(filters.regex(r"^locktype_"))
async def locktype_description(client: Client, query: CallbackQuery):
    # Extract lock type from callback data
    lock_type = query.data.split("_", 1)[1]
    description = LOCKABLES.get(lock_type, "No description available.")    

    await query.answer(
        text=f"🔒 {lock_type.capitalize()} Lock:\n{description}",
        show_alert=True        
    )

@app.on_message(filters.group & ~filters.me)
async def lock_handler(client: Client, message: Message):
    if not message.from_user:
        return

    if await is_user_admin(client, message.chat.id, message.from_user.id):
        return

    locks = await get_locks(message.chat.id)

    if not locks:
        return

    if "all" in locks:
        await message.delete()
        return

    if "text" in locks and message.text:
        await message.delete()
        return

    if "photo" in locks and message.photo:
        await message.delete()
        return

    if "video" in locks and message.video:
        await message.delete()
        return

    if "audio" in locks and message.audio:
        await message.delete()
        return

    if "document" in locks and message.document:
        await message.delete()
        return

    if "sticker" in locks and message.sticker:
        await message.delete()
        return

    if "animation" in locks and message.animation:
        await message.delete()
        return

    if "voice" in locks and message.voice:
        await message.delete()
        return

    if "video_note" in locks and message.video_note:
        await message.delete()
        return

    if "contact" in locks and message.contact:
        await message.delete()
        return

    if "location" in locks and message.location:
        await message.delete()
        return

    if "poll" in locks and message.poll:
        await message.delete()
        return

    if "game" in locks and message.game:
        await message.delete()
        return

__module__ = "𝖫𝗈𝖼𝗄𝗌"

__help__ = """🔒 **𝖫𝗈𝖼𝗄𝗌 𝖬𝗈𝖽𝗎𝗅𝖾**:
𝖬𝖺𝗇𝖺𝗀𝖾 𝖼𝗁𝖺𝗍 𝗋𝖾𝗌𝗍𝗋𝗂𝖼𝗍𝗂𝗈𝗇𝗌 𝖾𝖿𝖿𝖾𝖼𝗍𝗂𝗏𝖾𝗅𝗒. 𝖫𝗈𝖼𝗄 𝗈𝗋 𝗎𝗇𝗅𝗈𝖼𝗄 𝗏𝖺𝗋𝗂𝗈𝗎𝗌 𝗍𝗒𝗉𝖾𝗌 𝗈𝖿 𝖼𝗈𝗇𝗍𝖾𝗇𝗍 𝗂𝗇 𝗍𝗁𝖾 𝖼𝗁𝖺𝗍.
 
**𝖠𝗏𝖺𝗂𝗅𝖺𝖻𝗅𝖾 𝖢𝗈𝗆𝗆𝖺𝗇𝖽𝗌**:
- `/𝗅𝗈𝖼𝗄 <𝗍𝗒𝗉𝖾(𝗌)>` - 𝖤𝗇𝖺𝖻𝗅𝖾 𝗅𝗈𝖼𝗄𝗌 𝖿𝗈𝗋 𝗌𝗉𝖾𝖼𝗂𝖿𝗂𝖼 𝖼𝗈𝗇𝗍𝖾𝗇𝗍 𝗍𝗒𝗉𝖾𝗌 (𝖾.𝗀., `/𝗅𝗈𝖼𝗄 𝗉𝗁𝗈𝗍𝗈`).
   - 𝖴𝗌𝖾 `/𝗅𝗈𝖼𝗄 𝖺𝗅𝗅` 𝗍𝗈 𝖾𝗇𝖺𝖻𝗅𝖾 𝖺𝗅𝗅 𝗅𝗈𝖼𝗄𝗌.
 - `/𝗎𝗇𝗅𝗈𝖼𝗄 <𝗍𝗒𝗉𝖾(𝗌)>` - 𝖣𝗂𝗌𝖺𝖻𝗅𝖾 𝗅𝗈𝖼𝗄𝗌 𝖿𝗈𝗋 𝗌𝗉𝖾𝖼𝗂𝖿𝗂𝖼 𝖼𝗈𝗇𝗍𝖾𝗇𝗍 𝗍𝗒𝗉𝖾𝗌 (𝖾.𝗀., `/𝗎𝗇𝗅𝗈𝖼𝗄 𝗏𝗂𝖽𝖾𝗈`).
   - 𝖴𝗌𝖾 `/𝗎𝗇𝗅𝗈𝖼𝗄 𝖺𝗅𝗅` 𝗍𝗈 𝖽𝗂𝗌𝖺𝖻𝗅𝖾 𝖺𝗅𝗅 𝗅𝗈𝖼𝗄𝗌.
 - `/𝗅𝗈𝖼𝗄𝗍𝗒𝗉𝖾𝗌` - 𝖵𝗂𝖾𝗐 𝖺𝗅𝗅 𝗅𝗈𝖼𝗄𝖺𝖻𝗅𝖾 𝖼𝗈𝗇𝗍𝖾𝗇𝗍 𝗍𝗒𝗉𝖾𝗌 𝖺𝗇𝖽 𝗍𝗁𝖾𝗂𝗋 𝖽𝖾𝗌𝖼𝗋𝗂𝗉𝗍𝗂𝗈𝗇𝗌.
 - `/𝗅𝗈𝖼𝗄𝗌` - 𝖢𝗁𝖾𝖼𝗄 𝖼𝗎𝗋𝗋𝖾𝗇𝗍𝗅𝗒 𝖺𝖼𝗍𝗂𝗏𝖾 𝗅𝗈𝖼𝗄𝗌 𝗂𝗇 𝗍𝗁𝖾 𝖼𝗁𝖺𝗍.
 
**𝖴𝗌𝖺𝗀𝖾 𝖤𝗑𝖺𝗆𝗉𝗅𝖾𝗌**:
- `/𝗅𝗈𝖼𝗄 𝗉𝗁𝗈𝗍𝗈 𝗏𝗂𝖽𝖾𝗈` - 𝖱𝖾𝗌𝗍𝗋𝗂𝖼𝗍 𝗎𝗌𝖾𝗋𝗌 𝖿𝗋𝗈𝗆 𝗌𝖾𝗇𝖽𝗂𝗇𝗀 𝗉𝗁𝗈𝗍𝗈𝗌 𝖺𝗇𝖽 𝗏𝗂𝖽𝖾𝗈𝗌.
 - `/𝗎𝗇𝗅𝗈𝖼𝗄 𝗍𝖾𝗑𝗍 𝖼𝗈𝗆𝗆𝖺𝗇𝖽` - 𝖠𝗅𝗅𝗈𝗐 𝗍𝖾𝗑𝗍 𝗆𝖾𝗌𝗌𝖺𝗀𝖾𝗌 𝖺𝗇𝖽 𝖼𝗈𝗆𝗆𝖺𝗇𝖽𝗌.
 
"""
