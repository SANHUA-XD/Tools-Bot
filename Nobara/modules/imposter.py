from Nobara import app, IMPOSTER_GROUP
from Nobara.database.imposterdb import (
    save_or_check_user,
    is_imposter_enabled,
    enable_imposter,
    disable_imposter,
)
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from config import config
from Nobara.decorator.chatadmin import chatadmin
from Nobara.decorator.save import save 
from Nobara.decorator.errors import error

# Command to toggle imposter status
@app.on_message(filters.command("imposter", prefixes=config.COMMAND_PREFIXES) & filters.group)
@chatadmin
@error
@save
async def imposter_handler(client: Client, message: Message):
    chat_id = message.chat.id

    if await is_imposter_enabled(chat_id):
        # If already enabled, send a button to disable
        button = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("🔴 Disable 𝖨𝗆𝗉𝗈𝗌𝗍𝖾𝗋", callback_data=f"disable_imposter:{chat_id}")],
                [InlineKeyboardButton("🗑️", callback_data="delete")]
            ]
        )
        await message.reply_text("**📢 𝖨𝗆𝗉𝗈𝗌𝗍𝖾𝗋 is enabled in this chat.**", reply_markup=button)
    else:
        # If not enabled, send a button to enable
        button = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("🟢 Enable 𝖨𝗆𝗉𝗈𝗌𝗍𝖾𝗋", callback_data=f"enable_imposter:{chat_id}")],
                [InlineKeyboardButton("🗑️", callback_data="delete")]
            ]
        )
        await message.reply_text("**📢 𝖨𝗆𝗉𝗈𝗌𝗍𝖾𝗋 is disabled in this chat.**", reply_markup=button)


# Callback query handler for enabling/disabling imposter
@app.on_callback_query(filters.regex("^(enable_imposter|disable_imposter):"))
@chatadmin
@error
async def toggle_imposters(client: Client, callback_query: CallbackQuery):
    action, chat_id = callback_query.data.split(":")
    chat_id = int(chat_id)
    chat = await client.get_chat(chat_id)

    if action == "enable_imposter":
        await enable_imposter(chat_id, chat.title, chat.username)
        await callback_query.message.edit_text("**🟢 𝖨𝗆𝗉𝗈𝗌𝗍𝖾𝗋 has been enabled for this chat.**")
    elif action == "disable_imposter":
        await disable_imposter(chat_id)
        await callback_query.message.edit_text("**🔴 𝖨𝗆𝗉𝗈𝗌𝗍𝖾𝗋 has been enabled for this chat.**")


# Text message handler to save or announce changes in user details
@app.on_message(filters.group, group=IMPOSTER_GROUP)
@error
@save
async def imposter_text_handler(client: Client, message: Message):
    chat_id = message.chat.id

    # Check if imposter is enabled in this chat
    if not await is_imposter_enabled(chat_id):
        return

    user = message.from_user
    if not user:
        return  # Skip if there's no user info

    # Save or check user details
    changes = await save_or_check_user(user)
    if changes:
        # Create a professional announcement for multiple changes
        change_details = "\n".join(
            f"• **{field.capitalize()}:**\n"
            f"   - **𝖯𝗋𝖾𝗏𝗂𝗈𝗎𝗌:** {old if old else 'None'}\n"
            f"   - **𝖴𝗉𝖽𝖺𝗍𝖾𝖽:** {new if new else 'None'}"
            for field, old, new in changes
        )
        
        announcement = (
            f"🔔 **𝖴𝗌𝖾𝗋 𝖯𝗋𝗈𝖿𝗂𝗅𝖾 𝖴𝗉𝖽𝖺𝗍𝖾 𝖣𝖾𝗍𝖾𝖼𝗍𝖾𝖽**\n\n"
            f"👤 **𝖴𝗌𝖾𝗋:** {user.mention()} ({user.id})\n\n"
            f"{change_details}"
        )
        
        # Send the announcement in the chat
        await message.reply_text(announcement, disable_web_page_preview=True)


__module__ = "𝖨𝗆𝗉𝗈𝗌𝗍𝖾𝗋"


__help__ = """**𝖯𝗎𝗋𝗉𝗈𝗌𝖾:**
𝖳𝗁𝗂𝗌 𝗆𝗈𝖽𝗎𝗅𝖾 𝗆𝗈𝗇𝗂𝗍𝗈𝗋𝗌 𝖼𝗁𝖺𝗇𝗀𝖾𝗌 𝗂𝗇 𝗎𝗌𝖾𝗋 𝗂𝗇𝖿𝗈𝗋𝗆𝖺𝗍𝗂𝗈𝗇 (𝗎𝗌𝖾𝗋𝗇𝖺𝗆𝖾, 𝖿𝗂𝗋𝗌𝗍 𝗇𝖺𝗆𝖾, 𝗈𝗋 𝗅𝖺𝗌𝗍 𝗇𝖺𝗆𝖾) 𝗂𝗇 𝗀𝗋𝗈𝗎𝗉 𝖼𝗁𝖺𝗍𝗌 𝖺𝗇𝖽 𝗇𝗈𝗍𝗂𝖿𝗂𝖾𝗌 𝗍𝗁𝖾 𝗀𝗋𝗈𝗎𝗉 𝖺𝖻𝗈𝗎𝗍 𝖺𝗇𝗒 𝖽𝖾𝗍𝖾𝖼𝗍𝖾𝖽 𝗎𝗉𝖽𝖺𝗍𝖾𝗌.
 
**𝖥𝖾𝖺𝗍𝗎𝗋𝖾𝗌:**
  ✧ 𝖳𝗋𝖺𝖼𝗄𝗌 𝖼𝗁𝖺𝗇𝗀𝖾𝗌 𝗂𝗇:
    - 𝖴𝗌𝖾𝗋𝗇𝖺𝗆𝖾
    - 𝖥𝗂𝗋𝗌𝗍 𝖭𝖺𝗆𝖾
    - 𝖫𝖺𝗌𝗍 𝖭𝖺𝗆𝖾
  ✧ 𝖲𝖾𝗇𝖽𝗌 𝖺𝗇 𝖺𝗇𝗇𝗈𝗎𝗇𝖼𝖾𝗆𝖾𝗇𝗍 𝗍𝗈 𝗍𝗁𝖾 𝗀𝗋𝗈𝗎𝗉 𝗐𝗁𝖾𝗇 𝖺 𝗎𝗌𝖾𝗋 𝗎𝗉𝖽𝖺𝗍𝖾𝗌 𝖺𝗇𝗒 𝗈𝖿 𝗍𝗁𝖾𝗌𝖾 𝖽𝖾𝗍𝖺𝗂𝗅𝗌.
  ✧ 𝖯𝗋𝗈𝗏𝗂𝖽𝖾𝗌 𝖼𝗅𝖾𝖺𝗋 𝖺𝗇𝖽 𝖿𝗈𝗋𝗆𝖺𝗍𝗍𝖾𝖽 𝗇𝗈𝗍𝗂𝖿𝗂𝖼𝖺𝗍𝗂𝗈𝗇𝗌 𝗍𝗈 𝖾𝗇𝗌𝗎𝗋𝖾 𝗍𝗋𝖺𝗇𝗌𝗉𝖺𝗋𝖾𝗇𝖼𝗒.
 """