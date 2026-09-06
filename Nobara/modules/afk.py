from pyrogram import Client, filters
from pyrogram.types import Message
from datetime import datetime
from Nobara import app , AFK_REPLY_GROUP , AFK_RETURN_GROUP
from Nobara.database.afk_db import get_afk, set_afk, clear_afk , get_afk_by_username, is_afk_cached, any_afk_cached
from Nobara.helper.user import resolve_user_for_afk
from Nobara.vars import random_afk_message , random_afk_reply_message , random_back_online_message
import random
from Nobara.helper.time import format_time_delta
from pyrogram.enums import ParseMode
from config import config 
from Nobara.decorator.errors import error
from Nobara.decorator.save import save 

@app.on_message(
    filters.command(["afk", "brb"], prefixes=config.COMMAND_PREFIXES) 
    | filters.regex(r"(?i)^off(\s+.+)?$") 
    | filters.regex(r"(?i)^brb(\s+.+)?$")
)
@error
@save
async def afk_command(client: Client, message: Message):
    user_id = message.from_user.id
    user_first_name = message.from_user.first_name
    username = message.from_user.username or "Unknown"
    afk_reason = None
    media_id = None

    # Check if user is already AFK
    afk_data = await get_afk(user_id)
    if afk_data:
        afk_since = datetime.fromisoformat(afk_data["afk_start_time"])
        elapsed = datetime.now() - afk_since
        elapsed_str = format_time_delta(elapsed)
        random_msg = random.choice(random_back_online_message)

        msg = [
            f"{message.from_user.first_name} 𝗂𝗌 𝗇𝗈𝗐 𝖻𝖺𝖼𝗄 𝗈𝗇𝗅𝗂𝗇𝖾!",
            f"{message.from_user.first_name} 𝗁𝖺𝗌 𝗋𝖾𝗍𝗎𝗋𝗇𝖾𝖽. 𝖠𝖥𝖪 𝖽𝗎𝗋𝖺𝗍𝗂𝗈𝗇: {elapsed_str}.",
            f"𝖶𝖾𝗅𝖼𝗈𝗆𝖾 𝖻𝖺𝖼𝗄, {message.from_user.first_name}. {random_msg}.\n𝖸𝗈𝗎 𝗐𝖾𝗋𝖾 𝖠𝖥𝖪 𝖿𝗈𝗋 {elapsed_str}."
        ]

        r = random.choice(msg)
        await clear_afk(user_id)
        await message.reply(r, parse_mode=ParseMode.MARKDOWN)
        return

    # Extract AFK reason from the message
    if message.reply_to_message:
        # Handle media attachments
        if message.reply_to_message.video:
            media_id = message.reply_to_message.video.file_id
        elif message.reply_to_message.photo:
            media_id = message.reply_to_message.photo.file_id
        elif message.reply_to_message.animation:
            media_id = message.reply_to_message.animation.file_id
        elif message.reply_to_message.audio:
            media_id = message.reply_to_message.audio.file_id
        elif message.reply_to_message.voice:
            media_id = message.reply_to_message.voice.file_id
        elif message.reply_to_message.document:
            media_id = message.reply_to_message.document.file_id
        elif message.reply_to_message.video_note:
            media_id = message.reply_to_message.video_note.file_id

    # Handle reason if provided in the command (e.g., "brb bgmi")
    if message.text:
        command_split = message.text.split(" ", 1)
        if len(command_split) > 1:
            afk_reason = command_split[1]

    # Store AFK details
    afk_start_time = datetime.now().isoformat()
    await set_afk(user_id, user_first_name, username, afk_reason, afk_start_time, media_id)

    random_msg = random.choice(random_afk_message)

    afk_message = f"{user_first_name} 𝗂𝗌 𝗇𝗈𝗐 𝖠𝗐𝖺𝗒 𝖥𝗋𝗈𝗆 𝖪𝖾𝗒𝖻𝗈𝖺𝗋𝖽!\n{random_msg}"
    if afk_reason:
        afk_message += f"\n**Reason:** {afk_reason}"
    await message.reply(afk_message)



@app.on_message(filters.all & ~filters.me, group=AFK_REPLY_GROUP)
@error
@save
async def afk_mention_handler(client: Client, message: Message):
    if not message.from_user:
        return

    # Fast, DB-free short-circuit: skip all the resolve/lookup work below
    # when nobody in the whole bot is currently AFK (the overwhelmingly
    # common case) - this used to do real lookup work on every single
    # message regardless.
    if not await any_afk_cached():
        return

    user = await resolve_user_for_afk(client, message)

    if not user:
        if message.text:
            words = message.text.split()
            for word in words:
                if word.startswith("@"):  # Username format
                    username = word[1:]
                    afk_data = await get_afk_by_username(username)
                    if afk_data:
                        user = afk_data
                        break

    if not user:
        return

    user_id = user.id if not isinstance(user, dict) else user["user_id"]
    if not await is_afk_cached(user_id):
        return

    afk_data = await get_afk(user_id) if not isinstance(user, dict) else user
    if not afk_data:
        return

    afk_since = datetime.fromisoformat(afk_data["afk_start_time"])
    elapsed = datetime.now() - afk_since
    elapsed_str = format_time_delta(elapsed)

    random_msg = random.choice(random_afk_reply_message)
    if afk_data.get("afk_reason") and afk_data.get("media_id"):
        await client.send_cached_media(
            chat_id=message.chat.id,
            file_id=afk_data["media_id"],
            caption=f"{afk_data['user_first_name']} {random_msg}.\n**𝖠𝖥𝖪 𝖿𝗈𝗋** : {elapsed_str}\n**𝖱𝖾𝖺𝗌𝗈𝗇** : {afk_data['afk_reason']}"
        )
    elif afk_data.get("media_id"):
        await client.send_cached_media(
            chat_id=message.chat.id,
            file_id=afk_data["media_id"],
            caption=f"{afk_data['user_first_name']} {random_msg}.\n**𝖠𝖥𝖪 𝖿𝗈𝗋** : {elapsed_str}"
        )
    elif afk_data.get("afk_reason"):
        await message.reply(
            f"{afk_data['user_first_name']} {random_msg}.\n**𝖠𝖥𝖪 𝖿𝗈𝗋** : {elapsed_str}\n**𝖱𝖾𝖺𝗌𝗈𝗇** : {afk_data['afk_reason']}"
        )
    else:
        await message.reply(f"{afk_data['user_first_name']} {random_msg}.\n**𝖠𝖥𝖪 𝖿𝗈𝗋** : {elapsed_str}")


@app.on_message(filters.all & ~filters.me & ~filters.command(["afk" , "brb"] , prefixes=config.COMMAND_PREFIXES) & ~filters.regex(r"(?i)^off(\s+.+)?$")  & ~filters.regex(r"(?i)^brb(\s+.+)?$"), group=AFK_RETURN_GROUP)
@error
@save
async def clear_afk_handler(client: Client, message: Message):
    if not message.from_user:
        return

    user_id = message.from_user.id

    # Fast, DB-free short-circuit: the overwhelming majority of messages are
    # from users who were never AFK, so check the in-memory cache first
    # instead of hitting MongoDB on every single message in every chat.
    if not await is_afk_cached(user_id):
        return

    afk_data = await get_afk(user_id)

    if afk_data:
        afk_since = datetime.fromisoformat(afk_data["afk_start_time"])
        elapsed = datetime.now() - afk_since
        elapsed_str = format_time_delta(elapsed)
        random_msg = random.choice(random_back_online_message)

        msg = [
            f"{message.from_user.first_name} 𝗂𝗌 𝗇𝗈𝗐 𝖻𝖺𝖼𝗄 𝗈𝗇𝗅𝗂𝗇𝖾!",
            f"{message.from_user.first_name} 𝗁𝖺𝗌 𝗋𝖾𝗍𝗎𝗋𝗇𝖾𝖽. **𝖠𝖥𝖪 𝖽𝗎𝗋𝖺𝗍𝗂𝗈𝗇** : {elapsed_str}.",
            f"𝖶𝖾𝗅𝖼𝗈𝗆𝖾 𝖻𝖺𝖼𝗄, {message.from_user.first_name}. {random_msg}.\n𝖸𝗈𝗎 𝗐𝖾𝗋𝖾 **𝖠𝖥𝖪 𝖿𝗈𝗋 {elapsed_str}**."
        ]

        r = random.choice(msg)
        await clear_afk(user_id)
        await message.reply(r ,  parse_mode=ParseMode.MARKDOWN)

__module__ = "𝖠𝖿𝗄"
__help__ = "✧ /𝖺𝖿𝗄 𝗈𝗋 (𝖻𝗋𝖻) 𝗈𝗋 (𝗈𝖿𝖿) : 𝖳𝗈 𝖬𝖺𝗋𝗄 𝖸𝗈𝗎𝗋𝖲𝖾𝗅𝖿 𝖠𝗌 𝖠𝖥𝖪 𝖴𝗌𝖾𝗋."