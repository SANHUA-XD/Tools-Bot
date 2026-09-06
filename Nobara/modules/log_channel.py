from pyrogram import Client, filters
from pyrogram.types import Message
from Nobara.database.log_channel_db import set_log_channel, get_log_channel, remove_log_channel
from Nobara import app , LOG_GROUP , CHAT_MEMBER_LOG_GROUP
from Nobara.decorator.chatadmin import can_change_info
from Nobara.helper.log_helper import format_log, send_log
from pyrogram.types import ChatMemberUpdated
from pyrogram.enums import ChatMemberStatus
from config import config
from Nobara.decorator.save import save 
from Nobara.decorator.errors import error

logchannelsetting_state = {}

@app.on_message(filters.command("setlog" , prefixes=config.COMMAND_PREFIXES) & filters.group)
@can_change_info
@error
@save
async def set_log_channel_command(client: Client, message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    # Check if a log channel is already set
    current_log_channel = await get_log_channel(chat_id)
    if current_log_channel:
        # Fetch the title of the current log channel
        log_channel_title = await get_chat_title(client, current_log_channel)
        await message.reply_text(
            f"𝖠 𝗅𝗈𝗀 𝖼𝗁𝖺𝗇𝗇𝖾𝗅 𝗂𝗌 𝖺𝗅𝗋𝖾𝖺𝖽𝗒 𝖼𝗈𝗇𝖿𝗂𝗀𝗎𝗋𝖾𝖽 𝖿𝗈𝗋 𝗍𝗁𝗂𝗌 𝗀𝗋𝗈𝗎𝗉: **{log_channel_title}**.\n\n"
            f"𝖳𝗈 𝖼𝗁𝖺𝗇𝗀𝖾 𝗂𝗍, 𝗉𝗅𝖾𝖺𝗌𝖾 𝗋𝖾𝗌𝖾𝗍 𝗍𝗁𝖾 𝖼𝗎𝗋𝗋𝖾𝗇𝗍 𝗅𝗈𝗀 𝖼𝗁𝖺𝗇𝗇𝖾𝗅 𝗎𝗌𝗂𝗇𝗀 𝗍𝗁𝖾 /𝖼𝗅𝖾𝖺𝗋𝗅𝗈𝗀 𝖼𝗈𝗆𝗆𝖺𝗇𝖽."
        )
        return

    # Easier path: /setlog @channelusername or /setlog -100xxxxxxxxxx,
    # skips the whole forward-a-message flow entirely if the bot's already
    # an admin there.
    if len(message.command) > 1:
        target = message.command[1]
        try:
            channel_id = int(target) if target.lstrip("-").isdigit() else target
            chat = await client.get_chat(channel_id)
            member = await client.get_chat_member(chat.id, "me")
            if not (member.privileges and member.privileges.can_post_messages):
                await message.reply_text("𝖨 𝗇𝖾𝖾𝖽 𝗍𝗈 𝖻𝖾 𝖺𝗇 𝖺𝖽𝗆𝗂𝗇 𝗂𝗇 𝗍𝗁𝖺𝗍 𝖼𝗁𝖺𝗇𝗇𝖾𝗅 𝗐𝗂𝗍𝗁 𝗉𝖾𝗋𝗆𝗂𝗌𝗌𝗂𝗈𝗇 𝗍𝗈 𝗉𝗈𝗌𝗍 𝗆𝖾𝗌𝗌𝖺𝗀𝖾𝗌.")
                return
            await set_log_channel(chat_id, chat.id)
            await message.reply_text(f"✅ 𝖲𝗎𝖼𝖼𝖾𝗌𝗌𝖿𝗎𝗅𝗅𝗒 𝗌𝖾𝗍 𝗍𝗁𝖾 𝗅𝗈𝗀 𝖼𝗁𝖺𝗇𝗇𝖾𝗅 𝖿𝗈𝗋 𝗍𝗁𝗂𝗌 𝖼𝗁𝖺𝗍 𝗍𝗈 **{chat.title}**.")
        except Exception as e:
            await message.reply_text(
                f"⚠️ 𝖢𝗈𝗎𝗅𝖽𝗇'𝗍 𝗎𝗌𝖾 𝗍𝗁𝖺𝗍 𝖼𝗁𝖺𝗇𝗇𝖾𝗅 (`{e}`).\n"
                "𝖬𝖺𝗄𝖾 𝗌𝗎𝗋𝖾 𝗍𝗁𝖾 𝖻𝗈𝗍 𝗂𝗌 𝖺𝗅𝗋𝖾𝖺𝖽𝗒 𝖺𝗇 𝖺𝖽𝗆𝗂𝗇 𝗍𝗁𝖾𝗋𝖾, 𝗈𝗋 𝗃𝗎𝗌𝗍 𝗋𝗎𝗇 `/setlog` 𝗐𝗂𝗍𝗁 𝗇𝗈 𝖺𝗋𝗀𝗎𝗆𝖾𝗇𝗍𝗌 𝗍𝗈 𝗌𝖾𝗍 𝗂𝗍 𝗎𝗉 𝖻𝗒 𝖿𝗈𝗋𝗐𝖺𝗋𝖽𝗂𝗇𝗀 𝖺 𝗆𝖾𝗌𝗌𝖺𝗀𝖾 𝗂𝗇𝗌𝗍𝖾𝖺𝖽."
            )
        return

    # Add user to log channel setup state
    logchannelsetting_state[(chat_id, user_id)] = True

    await message.reply_text(
        "𝖴𝗇𝖽𝖾𝗋𝗌𝗍𝗈𝗈𝖽! 𝖤𝗂𝗍𝗁𝖾𝗋:\n"
        "• 𝖱𝗎𝗇 `/setlog @channelusername` (𝗈𝗋 𝗂𝗍𝗌 𝖨𝖣) 𝗂𝖿 𝖨'𝗆 𝖺𝗅𝗋𝖾𝖺𝖽𝗒 𝖺𝗇 𝖺𝖽𝗆𝗂𝗇 𝗍𝗁𝖾𝗋𝖾, 𝗈𝗋\n"
        "• 𝖬𝖺𝗄𝖾 𝗆𝖾 𝖺𝗇 𝖺𝖽𝗆𝗂𝗇 𝗂𝗇 𝗍𝗁𝖾 𝖽𝖾𝗌𝗂𝗋𝖾𝖽 𝗅𝗈𝗀 𝖼𝗁𝖺𝗇𝗇𝖾𝗅, 𝗌𝖾𝗇𝖽 𝖺𝗇𝗒 𝗆𝖾𝗌𝗌𝖺𝗀𝖾 𝗍𝗁𝖾𝗋𝖾, 𝖺𝗇𝖽 𝖿𝗈𝗋𝗐𝖺𝗋𝖽 𝗂𝗍 𝗁𝖾𝗋𝖾."
    )


async def get_chat_title(client: Client, chat_id: int) -> str:
    """Fetch and return the title of a chat."""
    try:
        chat = await client.get_chat(chat_id)
        return chat.title or "Unknown Chat"
    except Exception as e:
        return "Unknown Chat"


# Listener for forwarded messages to detect log channel
@app.on_message(filters.forwarded & filters.group , group=LOG_GROUP)
@error
@save
async def detect_log_channel(client: Client, message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if not message.from_user :
        return

    # Check if the user is in log channel setting state
    if not logchannelsetting_state.get((chat_id, user_id)):
        return

    original_chat_id = message.forward_from_chat.id if message.forward_from_chat else None
    if not original_chat_id:
        await message.reply_text("𝖨𝗇𝗏𝖺𝗅𝗂𝖽 𝗅𝗈𝗀 𝖼𝗁𝖺𝗇𝗇𝖾𝗅. 𝖯𝗅𝖾𝖺𝗌𝖾 𝗍𝗋𝗒 𝖺𝗀𝖺𝗂𝗇.")
        return

    # Verify bot is an admin in the channel
    try:
        member = await client.get_chat_member(original_chat_id, "me")
        if not member.privileges.can_post_messages:
            await message.reply_text(
                "𝖨 𝗇𝖾𝖾𝖽 𝗍𝗈 𝖻𝖾 𝖺𝗇 𝖺𝖽𝗆𝗂𝗇 𝗂𝗇 𝗍𝗁𝖾 𝖼𝗁𝖺𝗇𝗇𝖾𝗅 𝗐𝗂𝗍𝗁 𝗉𝖾𝗋𝗆𝗂𝗌𝗌𝗂𝗈𝗇 𝗍𝗈 𝗉𝗈𝗌𝗍 𝗆𝖾𝗌𝗌𝖺𝗀𝖾𝗌."
            )
            return
    except Exception as e:
        await message.reply_text(f"Error: {e}")
        return

    # Save the log channel ID to the database
    await set_log_channel(chat_id, original_chat_id)
    del logchannelsetting_state[(chat_id, user_id)]  # Remove from state
    await message.reply_text(
        f"𝖲𝗎𝖼𝖼𝖾𝗌𝗌𝖿𝗎𝗅𝗅𝗒 𝗌𝖾𝗍 𝗍𝗁𝖾 𝗅𝗈𝗀 𝖼𝗁𝖺𝗇𝗇𝖾𝗅 𝖿𝗈𝗋 𝗍𝗁𝗂𝗌 𝖼𝗁𝖺𝗍 𝗍𝗈 {message.forward_from_chat.title}."
    )

# Command to clear log channel
@app.on_message(filters.command("clearlog" , prefixes=config.COMMAND_PREFIXES) & filters.group)
@can_change_info
@error
@save
async def clear_log_channel_command(client: Client, message: Message):
    chat_id = message.chat.id

    # Check if log channel is set
    current_log_channel = await get_log_channel(chat_id)
    if not current_log_channel:
        await message.reply_text("𝖭𝗈 𝗅𝗈𝗀 𝖼𝗁𝖺𝗇𝗇𝖾𝗅 𝗂𝗌 𝖼𝗎𝗋𝗋𝖾𝗇𝗍𝗅𝗒 𝗌𝖾𝗍 𝖿𝗈𝗋 𝗍𝗁𝗂𝗌 𝖼𝗁𝖺𝗍.")
        return

    # Clear the log channel
    await remove_log_channel(chat_id)
    await message.reply_text("𝖳𝗁𝖾 𝗅𝗈𝗀 𝖼𝗁𝖺𝗇𝗇𝖾𝗅 𝗁𝖺𝗌 𝖻𝖾𝖾𝗇 𝖼𝗅𝖾𝖺𝗋𝖾𝖽. 𝖸𝗈𝗎 𝖼𝖺𝗇 𝗌𝖾𝗍 𝖺 𝗇𝖾𝗐 𝗈𝗇𝖾 𝗎𝗌𝗂𝗇𝗀 /𝗌𝖾𝗍𝗅𝗈𝗀.")


@app.on_chat_member_updated(~filters.me,group=CHAT_MEMBER_LOG_GROUP)
@error
@save
async def log_chat_member_updates(client: Client, chat_member_updated: ChatMemberUpdated): 
    try :
            chat_id = chat_member_updated.chat.id
        
            # Get the log channel ID
            log_channel_id = await get_log_channel(chat_id)
            if not log_channel_id:
                return  # No log channel set, skip logging
        
            # Determine if the event is a join or leave
            old_status = chat_member_updated.old_chat_member.status if chat_member_updated.old_chat_member else None
            new_status = chat_member_updated.new_chat_member.status
        
            if old_status in {None, ChatMemberStatus.LEFT} and new_status == ChatMemberStatus.MEMBER:
                # User joined or rejoined the chat
                user = chat_member_updated.new_chat_member.user
                log_message = await format_log(
                    tag="JOINED",
                    chat=chat_member_updated.chat.title or "Unknown Chat",
                    user=(user.first_name or "User", user.id),
                )
            
            elif old_status == ChatMemberStatus.MEMBER and new_status in {ChatMemberStatus.LEFT, None}:
                # User left the chat
                user = chat_member_updated.old_chat_member.user
                log_message = await format_log(
                    tag="LEFT",
                    chat=chat_member_updated.chat.title or "Unknown Chat",
                    user=(user.first_name or "User", user.id),
                )
            else:
                return  # No relevant status change, skip logging
        
            # Queue the log message (batched + rate-limit-safe, see log_helper.py)
            await send_log(chat_id, log_message)
    except Exception:
        return


# A few more common, generic group events - these apply to every group
# regardless of which other modules are active, so they live here directly.
@app.on_message(filters.new_chat_title & filters.group)
@error
async def log_title_change(client: Client, message: Message):
    admin = (message.from_user.first_name, message.from_user.id) if message.from_user else None
    log_message = await format_log(
        tag="TITLE",
        chat=message.chat.title or "Unknown Chat",
        admin=admin,
        note=f"New title: {message.new_chat_title}"
    )
    await send_log(message.chat.id, log_message)


@app.on_message((filters.new_chat_photo | filters.delete_chat_photo) & filters.group)
@error
async def log_photo_change(client: Client, message: Message):
    tag = "PHOTOREMOVED" if message.delete_chat_photo else "PHOTOCHANGED"
    admin = (message.from_user.first_name, message.from_user.id) if message.from_user else None
    log_message = await format_log(
        tag=tag,
        chat=message.chat.title or "Unknown Chat",
        admin=admin,
    )
    await send_log(message.chat.id, log_message)


@app.on_message(filters.pinned_message & filters.group)
@error
async def log_pinned_message(client: Client, message: Message):
    pinned = message.pinned_message
    link = pinned.link if pinned and hasattr(pinned, "link") else None
    admin = (message.from_user.first_name, message.from_user.id) if message.from_user else None
    log_message = await format_log(
        tag="PIN",
        chat=message.chat.title or "Unknown Chat",
        admin=admin,
        message_link=link,
    )
    await send_log(message.chat.id, log_message)
    
__module__ = "𝖫𝗈𝗀 𝖢𝗁𝖺𝗇𝗇𝖾𝗅"


__help__ = """**𝖫𝗈𝗀 𝖢𝗁𝖺𝗇𝗇𝖾𝗅 𝖬𝖺𝗇𝖺𝗀𝖾𝗆𝖾𝗇𝗍 :**

- **𝖢𝗈𝗆𝗆𝖺𝗇𝖽𝗌:**

 ✧ `/𝗌𝖾𝗍𝗅𝗈𝗀 @channelusername` : 𝖤𝖺𝗌𝗂𝖾𝗌𝗍 𝗐𝖺𝗒 - 𝗅𝗂𝗇𝗄𝗌 𝗂𝗇𝗌𝗍𝖺𝗇𝗍𝗅𝗒 𝗂𝖿 𝗍𝗁𝖾 𝖻𝗈𝗍 𝗂𝗌 𝖺𝗅𝗋𝖾𝖺𝖽𝗒 𝖺𝗇 𝖺𝖽𝗆𝗂𝗇 𝗍𝗁𝖾𝗋𝖾.
 ✧ `/𝗌𝖾𝗍𝗅𝗈𝗀` (𝗇𝗈 𝖺𝗋𝗀𝗎𝗆𝖾𝗇𝗍𝗌) : 𝖮𝗋 𝗆𝖺𝗄𝖾 𝗆𝖾 𝖺𝗇 𝖺𝖽𝗆𝗂𝗇 𝗂𝗇 𝗍𝗁𝖾 𝖽𝖾𝗌𝗂𝗋𝖾𝖽 𝖼𝗁𝖺𝗇𝗇𝖾𝗅, 𝗍𝗁𝖾𝗇 𝖿𝗈𝗋𝗐𝖺𝗋𝖽 𝖺𝗇𝗒 𝗆𝖾𝗌𝗌𝖺𝗀𝖾 𝖿𝗋𝗈𝗆 𝗂𝗍 𝗁𝖾𝗋𝖾.
     
 ✧ `/𝖼𝗅𝖾𝖺𝗋𝗅𝗈𝗀` : 𝖴𝗇𝗅𝗂𝗇𝗄 𝗍𝗁𝖾 𝖼𝗎𝗋𝗋𝖾𝗇𝗍𝗅𝗒 𝗌𝖾𝗍 𝗅𝗈𝗀 𝖼𝗁𝖺𝗇𝗇𝖾𝗅 𝖿𝗈𝗋 𝗍𝗁𝖾 𝗀𝗋𝗈𝗎𝗉.
 
- **𝖥𝗎𝗇𝖼𝗍𝗂𝗈𝗇𝖺𝗅𝗂𝗍𝗒:**

 ✧ 𝖮𝗇𝖼𝖾 𝖺 𝗅𝗈𝗀 𝖼𝗁𝖺𝗇𝗇𝖾𝗅 𝗂𝗌 𝗌𝖾𝗍, 𝗍𝗁𝖾 𝖻𝗈𝗍 𝗐𝗂𝗅𝗅 𝗅𝗈𝗀 𝗄𝖾𝗒 𝖾𝗏𝖾𝗇𝗍𝗌 𝗂𝗇 𝗍𝗁𝖾 𝗀𝗋𝗈𝗎𝗉 𝗍𝗈 𝗍𝗁𝖾 𝗅𝗂𝗇𝗄𝖾𝖽 𝖼𝗁𝖺𝗇𝗇𝖾𝗅.
 ✧ 𝖫𝗈𝗀𝗌 𝖺𝗋𝖾 𝖻𝖺𝗍𝖼𝗁𝖾𝖽 𝖺𝗇𝖽 𝗌𝖾𝗇𝗍 𝖾𝗏𝖾𝗋𝗒 ~𝟤𝟢 𝗌𝖾𝖼𝗈𝗇𝖽𝗌 𝗋𝖺𝗍𝗁𝖾𝗋 𝗍𝗁𝖺𝗇 𝗈𝗇𝖾-𝖻𝗒-𝗈𝗇𝖾 𝗂𝗇𝗌𝗍𝖺𝗇𝗍𝗅𝗒, 𝗌𝗈 𝖺 𝖻𝗎𝗌𝗒 𝗀𝗋𝗈𝗎𝗉 𝖽𝗈𝖾𝗌𝗇'𝗍 𝗋𝗂𝗌𝗄 𝗁𝗂𝗍𝗍𝗂𝗇𝗀 𝖳𝖾𝗅𝖾𝗀𝗋𝖺𝗆'𝗌 𝗋𝖺𝗍𝖾 𝗅𝗂𝗆𝗂𝗍𝗌.
  ✧ 𝖫𝗈𝗀𝗀𝖾𝖽 𝖾𝗏𝖾𝗇𝗍𝗌 𝗂𝗇𝖼𝗅𝗎𝖽𝖾:
    - 𝖬𝖾𝗆𝖻𝖾𝗋𝗌 𝗃𝗈𝗂𝗇𝗂𝗇𝗀 𝗈𝗋 𝗅𝖾𝖺𝗏𝗂𝗇𝗀 𝗍𝗁𝖾 𝗀𝗋𝗈𝗎𝗉.
    - 𝖦𝗋𝗈𝗎𝗉 𝗍𝗂𝗍𝗅𝖾/𝗉𝗁𝗈𝗍𝗈 𝖼𝗁𝖺𝗇𝗀𝖾𝗌, 𝗉𝗂𝗇𝗇𝖾𝖽 𝗆𝖾𝗌𝗌𝖺𝗀𝖾𝗌.
    - 𝖠𝖽𝗆𝗂𝗇 𝖺𝖼𝗍𝗂𝗈𝗇𝗌 𝖺𝖼𝗋𝗈𝗌𝗌 𝗆𝗈𝗌𝗍 𝗈𝗍𝗁𝖾𝗋 𝗆𝗈𝖽𝗎𝗅𝖾𝗌 (𝖻𝖺𝗇𝗌, 𝗐𝖺𝗋𝗇𝗌, 𝖻𝗅𝖺𝖼𝗄𝗅𝗂𝗌𝗍 𝗁𝗂𝗍𝗌, 𝖺𝗉𝗉𝗋𝗈𝗏𝖺𝗅𝗌, 𝖼𝗅𝖾𝖺𝗇𝖾𝗋, 𝗇𝗂𝗀𝗁𝗍𝗆𝗈𝖽𝖾, 𝖺𝗇𝗇𝗈𝗎𝗇𝖼𝖾𝗆𝖾𝗇𝗍𝗌, 𝖺𝗇𝗍𝗂𝖼𝗁𝖺𝗇𝗇𝖾𝗅, 𝖺𝗇𝖽 𝗆𝗈𝗋𝖾).
"""
