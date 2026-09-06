import re
from pyrogram import Client, filters
from pyrogram.enums import ChatMembersFilter, ChatMemberStatus, ParseMode
from pyrogram.types import Message
from Nobara import app
from config import config
from Nobara.decorator.save import save
from Nobara.decorator.errors import error

# ==========================================
# 1. User Command: /report, @admin, @admins, @owner
# ==========================================
@app.on_message(
    (filters.command("report", prefixes=config.COMMAND_PREFIXES) | filters.regex(r"(?i)@(admin|admins|owner)\b"))
    & filters.group
)
@error
@save
async def handle_report(client: Client, message: Message):
    chat_id = message.chat.id
    text = message.text or message.caption or ""
    
    # Check if it was triggered by the /report command
    is_cmd = False
    for prefix in config.COMMAND_PREFIXES:
        if text.startswith(f"{prefix}report"):
            is_cmd = True
            break
            
    # /report must be a reply to a message
    if is_cmd and not message.reply_to_message:
        await message.reply("𝖸𝗈𝗎 𝗇𝖾𝖾𝖽 𝗍𝗈 𝗋𝖾𝗉𝗅𝗒 𝗍𝗈 𝖺 𝗆𝖾𝗌𝗌𝖺𝗀𝖾 𝗍𝗈 𝗋𝖾𝗉𝗈𝗋𝗍 𝗂𝗍.")
        return

    # Determine if reporting to owner only or all admins
    target = "owner" if "@owner" in text.lower() else "admins"
    
    human_admins = []
    admin_ids = []
    owner_id = None
    
    # Fetch all admins of the chat silently (No edit message)
    async for m in client.get_chat_members(chat_id, filter=ChatMembersFilter.ADMINISTRATORS):
        admin_ids.append(m.user.id)
        # Exclude bots from being tagged
        if not m.user.is_bot:
            human_admins.append(m.user.id)
            if m.status == ChatMemberStatus.OWNER:
                owner_id = m.user.id

    # Condition 1: Admins don't need to report, ignore their request silently
    if message.from_user and message.from_user.id in admin_ids:
        return 

    # Condition 2: You cannot report an admin (Applies only if a message is replied to)
    if message.reply_to_message:
        reported_msg = message.reply_to_message
        # Check if the reported user is an anonymous admin or a linked channel
        if reported_msg.sender_chat:
            await message.reply("𝖸𝗈𝗎 𝖼𝖺𝗇𝗇𝗈𝗍 𝗋𝖾𝗉𝗈𝗋𝗍 𝖺𝗇 𝖺𝖽𝗆𝗂𝗇.")
            return
        if reported_msg.from_user and reported_msg.from_user.id in admin_ids:
            await message.reply("𝖸𝗈𝗎 𝖼𝖺𝗇𝗇𝗈𝗍 𝗋𝖾𝗉𝗈𝗋𝗍 𝖺𝗇 𝖺𝖽𝗆𝗂𝗇.")
            return

    # Construct Hidden Mentions
    # Using \u200b (Zero-width space) and \u200c (Zero-width non-joiner) to prevent Telegram from dropping mentions
    mentions = ""
    if target == "owner":
        if owner_id:
            mentions += f"[\u200b](tg://user?id={owner_id})\u200c"
        else:
            await message.reply("𝖢𝗈𝗎𝗅𝖽𝗇'𝗍 𝖿𝗂𝗇𝖽 𝗍𝗁𝖾 𝗈𝗐𝗇𝖾𝗋 𝗈𝖿 𝗍𝗁𝗂𝗌 𝗀𝗋𝗈𝗎𝗉.")
            return
    else:
        for a_id in human_admins:
            mentions += f"[\u200b](tg://user?id={a_id})\u200c"

    # Direct Send Success Message with Hidden Mentions
    reply_text = f"**𝖱𝖾𝗉𝗈𝗋𝗍𝖾𝖽 𝖳𝗈 {target.capitalize()}!**{mentions}"
    await message.reply_text(reply_text, disable_web_page_preview=True, parse_mode=ParseMode.MARKDOWN)


__module__ = "𝖱𝖾𝗉𝗈𝗋𝗍𝗌"

__help__ = """**𝖱𝖾𝗉𝗈𝗋𝗍 𝖬𝖺𝗇𝖺𝗀𝖾𝗆𝖾𝗇𝗍:**

𝖶𝖾'𝗋𝖾 𝖺𝗅𝗅 𝖻𝗎𝗌𝗒 𝗉𝖾𝗈𝗉𝗅𝖾 𝗐𝗁𝗈 𝖽𝗈𝗇'𝗍 𝗁𝖺𝗏𝖾 𝗍𝗂𝗆𝖾 𝗍𝗈 𝗆𝗈𝗇𝗂𝗍𝗈𝗋 𝗈𝗎𝗋 𝗀𝗋𝗈𝗎𝗉𝗌 𝟤𝟦/𝟩. 𝖨𝖿 𝗌𝗈𝗆𝖾𝗈𝗇𝖾 𝗂𝗇 𝗒𝗈𝗎𝗋 𝗀𝗋𝗈𝗎𝗉 𝗇𝖾𝖾𝖽𝗌 𝗋𝖾𝗉𝗈𝗋𝗍𝗂𝗇𝗀, 𝗍𝗁𝖾𝗒 𝗇𝗈𝗐 𝗁𝖺𝗏𝖾 𝖺𝗇 𝖾𝖺𝗌𝗒 𝗐𝖺𝗒 𝗍𝗈 𝖼𝖺𝗅𝗅 𝖺𝗅𝗅 𝖺𝖽𝗆𝗂𝗇𝗌.

- **𝖴𝗌𝖾𝗋 𝖢𝗈𝗆𝗆𝖺𝗇𝖽𝗌:**
 ✧ `/𝗋𝖾𝗉𝗈𝗋𝗍` : 𝖱𝖾𝗉𝗅𝗒 𝗍𝗈 𝖺 𝗆𝖾𝗌𝗌𝖺𝗀𝖾 𝗍𝗈 𝗋𝖾𝗉𝗈𝗋𝗍 𝗂𝗍 𝖿𝗈𝗋 𝖺𝖽𝗆𝗂𝗇𝗌 𝗍𝗈 𝗋𝖾𝗏𝗂𝖾𝗐.
 ✧ `@𝖺𝖽𝗆𝗂𝗇𝗌` 𝗈𝗋 `@𝖺𝖽𝗆𝗂𝗇` : 𝖱𝖾𝗉𝗈𝗋𝗍𝗌 𝗍𝗈 𝖺𝗅𝗅 𝗁𝗎𝗆𝖺𝗇 𝖺𝖽𝗆𝗂𝗇𝗌 (𝖭𝗈 𝗋𝖾𝗉𝗅𝗒 𝗋𝖾𝗊𝗎𝗂𝗋𝖾𝖽).
 ✧ `@𝗈𝗐𝗇𝖾𝗋` : 𝖱𝖾𝗉𝗈𝗋𝗍𝗌 𝗈𝗇𝗅𝗒 𝗍𝗈 𝗍𝗁𝖾 𝗀𝗋𝗈𝗎𝗉 𝗈𝗐𝗇𝖾𝗋 (𝖭𝗈 𝗋𝖾𝗉𝗅𝗒 𝗋𝖾𝗊𝗎𝗂𝗋𝖾𝖽).
 """
