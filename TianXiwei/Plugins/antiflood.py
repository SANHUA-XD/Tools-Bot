from pyrogram import Client, filters
from pyrogram.types import Message, ChatPermissions
from pyrogram.enums import ChatType, ChatMemberStatus
import time
from collections import defaultdict
from datetime import datetime, timedelta

from TianXiwei import app, ANTI_FLOOD_GROUP
from TianXiwei.Database.anti_flooddb import (
    get_antiflood_settings, set_flood_threshold, set_flood_action,
    set_flood_timer, set_delete_flood_messages, set_flood_action_duration,
    get_flood_action_duration
)
from TianXiwei.Functions.user import is_user_admin
from TianXiwei.Database.approve_db import is_user_approved
from config import config


def parse_duration(duration_str: str) -> timedelta:
    import re
    duration_str = duration_str.lower().strip()
    match = re.match(r'^(\d+)(d|h|m|s)$', duration_str)
    if not match:
        raise ValueError("Invalid duration format. Use e.g. 1d, 2h, 30m, 60s")

    value = int(match.group(1))
    unit = match.group(2)

    if unit == 'd':
        return timedelta(days=value)
    elif unit == 'h':
        return timedelta(hours=value)
    elif unit == 'm':
        return timedelta(minutes=value)
    elif unit == 's':
        return timedelta(seconds=value)
    else:
        raise ValueError("Invalid duration format. Use e.g. 1d, 2h, 30m, 60s")


flood_tracker = defaultdict(lambda: {"count": 0, "timestamps": [], "messages": []})

@app.on_message(filters.command("flood", prefixes=config.COMMAND_PREFIXES) & filters.group)
async def flood_command(client: Client, message: Message):
    if not await is_user_admin(client, message.chat.id, message.from_user.id):
        await message.reply_text("🚫 You must be an administrator to use this command.")
        return

    settings = await get_antiflood_settings(message.chat.id)

    msg = (f"Flood settings for this chat:\n\n"
           f"Limit: {settings['flood_threshold'] or 'Disabled'}\n"
           f"Mode: {settings['flood_action']}\n"
           f"Timer Count: {settings['flood_timer_count']}\n"
           f"Timer Duration: {settings['flood_timer_duration']}s")
    await message.reply_text(msg)

@app.on_message(filters.command("setflood", prefixes=config.COMMAND_PREFIXES) & filters.group)
async def setflood_command(client: Client, message: Message):
    if not await is_user_admin(client, message.chat.id, message.from_user.id):
        await message.reply_text("🚫 You must be an administrator to use this command.")
        return

    if len(message.command) < 2:
        await message.reply_text("Please specify a flood limit. Example: `/setflood 5`")
        return

    limit = message.command[1]
    
    if limit.lower() in ("off", "no", "0"):
        await set_flood_threshold(message.chat.id, 0)
        await message.reply_text("Flood control has been disabled.")
        return

    if not limit.isdigit():
        await message.reply_text("Please specify a valid number.")
        return

    await set_flood_threshold(message.chat.id, int(limit))
    await message.reply_text(f"Flood limit has been set to {limit}.")

@app.on_message(filters.command("setfloodtimer", prefixes=config.COMMAND_PREFIXES) & filters.group)
async def setfloodtimer_command(client: Client, message: Message):
    if not await is_user_admin(client, message.chat.id, message.from_user.id):
        await message.reply_text("🚫 You must be an administrator to use this command.")
        return

    if len(message.command) < 3:
        await message.reply_text("Please specify a flood timer count and duration. Example: `/setfloodtimer 3 10`")
        return

    count = message.command[1]
    duration = message.command[2]
    
    if not count.isdigit() or not duration.isdigit():
        await message.reply_text("Please specify valid numbers.")
        return

    await set_flood_timer(message.chat.id, int(count), int(duration))
    await message.reply_text(f"Timed Anti-Flood set to {count} messages in {duration} seconds.")

@app.on_message(filters.command("floodmode", prefixes=config.COMMAND_PREFIXES) & filters.group)
async def floodmode_command(client: Client, message: Message):
    if not await is_user_admin(client, message.chat.id, message.from_user.id):
        await message.reply_text("🚫 You must be an administrator to use this command.")
        return

    if len(message.command) < 2:
        await message.reply_text("Please specify a flood mode (ban, kick, mute, tban, tmute). Example: `/floodmode ban`")
        return

    mode = message.command[1].lower()
    valid_modes = ["ban", "kick", "mute", "tban", "tmute"]

    if mode not in valid_modes:
        await message.reply_text(f"Invalid mode. Valid modes are: {', '.join(valid_modes)}")
        return

    await set_flood_action(message.chat.id, mode)
    await message.reply_text(f"Flood mode has been set to {mode}.")

@app.on_message(filters.command("clearflood", prefixes=config.COMMAND_PREFIXES) & filters.group)
async def clearflood_command(client: Client, message: Message):
    if not await is_user_admin(client, message.chat.id, message.from_user.id):
        await message.reply_text("🚫 You must be an administrator to use this command.")
        return

    if len(message.command) < 2:
        await message.reply_text("Usage: `/clearflood <yes/no>`")
        return

    delete = message.command[1].lower() in ["yes", "on"]
    await set_delete_flood_messages(message.chat.id, delete)
    await message.reply_text(
        f"Flood messages will {'be deleted' if delete else 'not be deleted'}."
    )

@app.on_message(filters.command("actionduration", prefixes=config.COMMAND_PREFIXES) & filters.group)
async def actionduration_command(client: Client, message: Message):
    if not await is_user_admin(client, message.chat.id, message.from_user.id):
        await message.reply_text("🚫 You must be an administrator to use this command.")
        return

    if len(message.command) < 2:
        await message.reply_text("Usage: `/actionduration <duration>`\nExample: `/actionduration 1d`")
        return

    try:
        duration = parse_duration(" ".join(message.command[1:]))
        await set_flood_action_duration(message.chat.id, duration.total_seconds())
        await message.reply_text(
            f"Action duration set to {str(duration)}."
        )
    except ValueError as e:
        await message.reply_text(str(e))

@app.on_message(filters.group & ~filters.me, group=ANTI_FLOOD_GROUP)
async def flood_detection(client: Client, message: Message):
    chat_id = message.chat.id
    user = message.from_user

    if not user:
        return

    settings = await get_antiflood_settings(chat_id)
    if settings["flood_threshold"] == 0:
        return
    
    user_id = user.id
    
    if await is_user_approved(chat_id , user_id):
        return


    if await is_user_admin(client, chat_id, user_id):
        return


    flood_tracker[user_id]["count"] += 1
    flood_tracker[user_id]["timestamps"].append(message.date)
    flood_tracker[user_id]["messages"].append(message)


    if flood_tracker[user_id]["count"] >= settings["flood_threshold"]:
        await take_flood_action(client, message, settings, user_id)
        flood_tracker[user_id] = {"count": 0, "timestamps": [], "messages": []}


    elif settings["flood_timer_count"] > 0:
        timestamps = flood_tracker[user_id]["timestamps"]
        if len(timestamps) >= settings["flood_timer_count"] and           (timestamps[-1] - timestamps[-settings["flood_timer_count"]]).total_seconds() <= settings["flood_timer_duration"]:
            await take_flood_action(client, message, settings, user_id)
            flood_tracker[user_id] = {"count": 0, "timestamps": [], "messages": []}


async def take_flood_action(client: Client, message: Message, settings, user_id):
    action = settings["flood_action"]
    chat_id = message.chat.id
    duration_seconds = await get_flood_action_duration(chat_id)
    duration = timedelta(seconds=duration_seconds) if duration_seconds else timedelta(days=3)


    user_mention = message.from_user.mention
    announcement = (
        f" **Anti-Flood Alert** \n\n"
        f"User {user_mention} has been **{action.capitalize()}ed** for violating the anti-flood rules."
    )
    await message.chat.send_message(announcement)


    if action == "ban":
        await client.ban_chat_member(chat_id, user_id)
    elif action == "mute":
        await client.restrict_chat_member(chat_id, user_id, ChatPermissions())
    elif action == "kick":
        await client.ban_chat_member(chat_id, user_id)
        await client.unban_chat_member(chat_id, user_id)
    elif action == "tban":
        await client.ban_chat_member(chat_id, user_id, until_date=message.date + duration)
    elif action == "tmute":
        await client.restrict_chat_member(chat_id, user_id, ChatPermissions(), until_date=message.date + duration)


    if settings["delete_flood_messages"]:
        for msg in flood_tracker[user_id]["messages"]:
            try:
                await msg.delete()
            except:
                pass


__module__ = "𝖠𝗇𝗍𝗂𝖥𝗅𝗈𝗈𝖽"


__help__ = """**𝖠𝖽𝗆𝗂𝗇𝗌 𝗈𝗇𝗅𝗒:**
  ✧ `/𝖿𝗅𝗈𝗈𝖽` **:** 𝖣𝗂𝗌𝗉𝗅𝖺𝗒 𝖼𝗎𝗋𝗋𝖾𝗇𝗍 𝖺𝗇𝗍𝗂-𝖿𝗅𝗈𝗈𝖽 𝗌𝖾𝗍𝗍𝗂𝗇𝗀𝗌.
   ✧ `/𝗌𝖾𝗍𝖿𝗅𝗈𝗈𝖽 <𝗇𝗎𝗆𝖻𝖾𝗋/𝗈𝖿𝖿>` **:** 𝖲𝖾𝗍 𝗍𝗁𝖾 𝗇𝗎𝗆𝖻𝖾𝗋 𝗈𝖿 𝗆𝖾𝗌𝗌𝖺𝗀𝖾𝗌 𝗍𝗈 𝗍𝗋𝗂𝗀𝗀𝖾𝗋 𝖿𝗅𝗈𝗈𝖽 𝖺𝖼𝗍𝗂𝗈𝗇, 𝗈𝗋 𝖽𝗂𝗌𝖺𝖻𝗅𝖾 𝖺𝗇𝗍𝗂-𝖿𝗅𝗈𝗈𝖽.
   ✧ `/𝗌𝖾𝗍𝖿𝗅𝗈𝗈𝖽𝗍𝗂𝗆𝖾𝗋 <𝖼𝗈𝗎𝗇𝗍> <𝖽𝗎𝗋𝖺𝗍𝗂𝗈𝗇>` **:** 𝖲𝖾𝗍 𝗍𝗂𝗆𝖾𝖽 𝖿𝗅𝗈𝗈𝖽 𝗌𝖾𝗍𝗍𝗂𝗇𝗀𝗌 (𝖾.𝗀., `𝟥 𝗆𝖾𝗌𝗌𝖺𝗀𝖾𝗌 𝗂𝗇 𝟣𝟢 𝗌𝖾𝖼𝗈𝗇𝖽𝗌`).
   ✧ `/𝖿𝗅𝗈𝗈𝖽𝗆𝗈𝖽𝖾 <𝖻𝖺𝗇/𝗆𝗎𝗍𝖾/𝗄𝗂𝖼𝗄/𝗍𝖻𝖺𝗇/𝗍𝗆𝗎𝗍𝖾>` **:** 𝖲𝖾𝗍 𝗍𝗁𝖾 𝖺𝖼𝗍𝗂𝗈𝗇 𝗍𝗈 𝗍𝖺𝗄𝖾 𝗐𝗁𝖾𝗇 𝖿𝗅𝗈𝗈𝖽 𝖼𝗈𝗇𝗍𝗋𝗈𝗅 𝗂𝗌 𝗍𝗋𝗂𝗀𝗀𝖾𝗋𝖾𝖽.
   ✧ `/𝖺𝖼𝗍𝗂𝗈𝗇𝖽𝗎𝗋𝖺𝗍𝗂𝗈𝗇 <𝖽𝗎𝗋𝖺𝗍𝗂𝗈𝗇>` **:** 𝖲𝖾𝗍 𝗍𝗁𝖾 𝖽𝗎𝗋𝖺𝗍𝗂𝗈𝗇 𝗈𝖿 `𝗍𝗆𝗎𝗍𝖾` 𝗈𝗋 `𝗍𝖻𝖺𝗇` 𝖺𝖼𝗍𝗂𝗈𝗇𝗌 (𝖾.𝗀., `𝟣𝗁`, `𝟤𝖽 𝟥𝗁`, 𝖾𝗍𝖼.).
   ✧ `/𝖼𝗅𝖾𝖺𝗋𝖿𝗅𝗈𝗈𝖽 <𝗒𝖾𝗌/𝗇𝗈>` **:** 𝖤𝗇𝖺𝖻𝗅𝖾 𝗈𝗋 𝖽𝗂𝗌𝖺𝖻𝗅𝖾 𝗍𝗁𝖾 𝖽𝖾𝗅𝖾𝗍𝗂𝗈𝗇 𝗈𝖿 𝗆𝖾𝗌𝗌𝖺𝗀𝖾𝗌 𝗍𝗁𝖺𝗍 𝗍𝗋𝗂𝗀𝗀𝖾𝗋𝖾𝖽 𝗍𝗁𝖾 𝖺𝗇𝗍𝗂-𝖿𝗅𝗈𝗈𝖽.
 
*𝖤𝗑𝖺𝗆𝗉𝗅𝖾𝗌:*
  ✧ `/𝗌𝖾𝗍𝖿𝗅𝗈𝗈𝖽 𝟧` **:** 𝖳𝗋𝗂𝗀𝗀𝖾𝗋 𝖿𝗅𝗈𝗈𝖽 𝖺𝖼𝗍𝗂𝗈𝗇 𝖺𝖿𝗍𝖾𝗋 𝟧 𝗆𝖾𝗌𝗌𝖺𝗀𝖾𝗌.
   ✧ `/𝗌𝖾𝗍𝖿𝗅𝗈𝗈𝖽 𝗈𝖿𝖿` **:** 𝖣𝗂𝗌𝖺𝖻𝗅𝖾 𝖿𝗅𝗈𝗈𝖽 𝖼𝗈𝗇𝗍𝗋𝗈𝗅.
   ✧ `/𝗌𝖾𝗍𝖿𝗅𝗈𝗈𝖽𝗍𝗂𝗆𝖾𝗋 𝟥 𝟣𝟢` **:** 𝖳𝗋𝗂𝗀𝗀𝖾𝗋 𝖿𝗅𝗈𝗈𝖽 𝖺𝖼𝗍𝗂𝗈𝗇 𝗂𝖿 𝟥 𝗆𝖾𝗌𝗌𝖺𝗀𝖾𝗌 𝖺𝗋𝖾 𝗌𝖾𝗇𝗍 𝗐𝗂𝗍𝗁𝗂𝗇 𝟣𝟢 𝗌𝖾𝖼𝗈𝗇𝖽𝗌.
   ✧ `/𝖿𝗅𝗈𝗈𝖽𝗆𝗈𝖽𝖾 𝖻𝖺𝗇` **:** 𝖡𝖺𝗇 𝗎𝗌𝖾𝗋𝗌 𝗐𝗁𝗈 𝗍𝗋𝗂𝗀𝗀𝖾𝗋 𝖿𝗅𝗈𝗈𝖽 𝖼𝗈𝗇𝗍𝗋𝗈𝗅.
   ✧ `/𝖺𝖼𝗍𝗂𝗈𝗇𝖽𝗎𝗋𝖺𝗍𝗂𝗈𝗇 𝟤𝖽` **:** 𝖳𝖾𝗆𝗉𝗈𝗋𝖺𝗋𝗂𝗅𝗒 𝖻𝖺𝗇/𝗆𝗎𝗍𝖾 𝗎𝗌𝖾𝗋𝗌 𝖿𝗈𝗋 𝟤 𝖽𝖺𝗒𝗌 𝗐𝗁𝖾𝗇 𝖿𝗅𝗈𝗈𝖽 𝖼𝗈𝗇𝗍𝗋𝗈𝗅 𝗂𝗌 𝗍𝗋𝗂𝗀𝗀𝖾𝗋𝖾𝖽.
   ✧ `/𝖼𝗅𝖾𝖺𝗋𝖿𝗅𝗈𝗈𝖽 𝗒𝖾𝗌` **:** 𝖠𝗎𝗍𝗈𝗆𝖺𝗍𝗂𝖼𝖺𝗅𝗅𝗒 𝖽𝖾𝗅𝖾𝗍𝖾 𝖿𝗅𝗈𝗈𝖽-𝗍𝗋𝗂𝗀𝗀𝖾𝗋𝗂𝗇𝗀 𝗆𝖾𝗌𝗌𝖺𝗀𝖾𝗌.
 """
