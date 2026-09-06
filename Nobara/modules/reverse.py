from pyrogram import filters
import requests
from Nobara import app
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup , Message
from Nobara.helper.googlesearch import GoogleReverseImageSearch
from config import config
from Nobara.decorator.save import save 
from Nobara.decorator.errors import error

bot_token = config.BOT_TOKEN

MAX_FILE_SIZE = 3145728
ALLOWED_MIME_TYPES = ["image/png", "image/jpeg"]

google_search = GoogleReverseImageSearch()


async def get_file_id_from_message(msg : Message):
    message = msg.reply_to_message
    if not message:
        return None

    if message.document:
        if (
            int(message.document.file_size) > MAX_FILE_SIZE
            or message.document.mime_type not in ALLOWED_MIME_TYPES
        ):
            return None
        return message.document.file_id

    if message.sticker:
        if message.sticker.is_animated:
            if not message.sticker.thumbs:
                return None
            return message.sticker.thumbs[0].file_id
        else:
            return message.sticker.file_id

    if message.photo:
        return message.photo.file_id

    if message.animation:
        if not message.animation.thumbs:
            return None
        return message.animation.thumbs[0].file_id

    if message.video:
        if not message.video.thumbs:
            return None
        return message.video.thumbs[0].file_id

    return None


@app.on_message(filters.command(["pp", "grs", "reverse", "p"] , prefixes=config.COMMAND_PREFIXES))
@error
@save
async def reverse_image(_, msg):
    text = await msg.reply("**Plzz Wait...**")
    file_id = await get_file_id_from_message(msg)

    if not file_id:
        return await text.edit("**Reply to supported media types!**")

    await text.edit("**Searching On Google....**")

    r = requests.post(
        f"https://api.telegram.org/bot{bot_token}/getFile?file_id={file_id}"
    ).json()
    file_path = r["result"]["file_path"]
    img = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"
    result = google_search.reverse_search_image(address=img)
    if not result.get("similar"):
        return await text.edit("Couldn't perform the search right now. Please try again later.")

    if result.get("output"):
        caption = f"🔍 **Possible match:** [{result['output']}]({result['similar']})"
    else:
        caption = "🔍 **Reverse image search results are ready.** Tap below to view them."

    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Open Link", url=result["similar"])]]
    )

    await text.edit(caption, reply_markup=keyboard)
    
__module__ = "𝖱𝖾𝗏𝖾𝗋𝗌𝖾 𝖲𝖾𝖺𝗋𝖼𝗁"


__help__ = """**𝖱𝖾𝗏𝖾𝗋𝗌𝖾 𝖨𝗆𝖺𝗀𝖾 𝖲𝖾𝖺𝗋𝖼𝗁:**

- **𝖢𝗈𝗆𝗆𝖺𝗇𝖽𝗌:**
 ✧ `/𝗉𝗉`, `/𝗀𝗋𝗌`, `/𝗋𝖾𝗏𝖾𝗋𝗌𝖾`, 𝗈𝗋 `/𝗉` **:** 𝖱𝖾𝗉𝗅𝗒 𝗍𝗈 𝖺𝗇 𝗂𝗆𝖺𝗀𝖾, 𝗌𝗍𝗂𝖼𝗄𝖾𝗋, 𝗈𝗋 𝗌𝗎𝗉𝗉𝗈𝗋𝗍𝖾𝖽 𝗆𝖾𝖽𝗂𝖺 𝗍𝗒𝗉𝖾 𝗍𝗈 𝗉𝖾𝗋𝖿𝗈𝗋𝗆 𝖺 𝖦𝗈𝗈𝗀𝗅𝖾 𝖱𝖾𝗏𝖾𝗋𝗌𝖾 𝖨𝗆𝖺𝗀𝖾 𝖲𝖾𝖺𝗋𝖼𝗁.
 
- **𝖲𝗎𝗉𝗉𝗈𝗋𝗍𝖾𝖽 𝖬𝖾𝖽𝗂𝖺 𝖳𝗒𝗉𝖾𝗌:**
 ✧ 𝖨𝗆𝖺𝗀𝖾𝗌 (𝖩𝖯𝖤𝖦, 𝖯𝖭𝖦) 𝗅𝖾𝗌𝗌 𝗍𝗁𝖺𝗇 𝟥 𝖬𝖡 𝗂𝗇 𝗌𝗂𝗓𝖾.
 ✧ 𝖲𝗍𝗂𝖼𝗄𝖾𝗋𝗌 (𝗌𝗍𝖺𝗍𝗂𝖼 𝗈𝗋 𝖺𝗇𝗂𝗆𝖺𝗍𝖾𝖽 𝗍𝗁𝗎𝗆𝖻𝗇𝖺𝗂𝗅𝗌).
 ✧ 𝖯𝗁𝗈𝗍𝗈𝗌 𝖺𝗇𝖽 𝗍𝗁𝗎𝗆𝖻𝗇𝖺𝗂𝗅𝗌 𝗈𝖿 𝖺𝗇𝗂𝗆𝖺𝗍𝗂𝗈𝗇𝗌 𝗈𝗋 𝗏𝗂𝖽𝖾𝗈𝗌.
 
- **𝖧𝗈𝗐 𝖨𝗍 𝖶𝗈𝗋𝗄𝗌:**
   𝟣. 𝖱𝖾𝗉𝗅𝗒 𝗍𝗈 𝖺 𝗌𝗎𝗉𝗉𝗈𝗋𝗍𝖾𝖽 𝗆𝖾𝖽𝗂𝖺 𝗍𝗒𝗉𝖾 𝗐𝗂𝗍𝗁 𝗈𝗇𝖾 𝗈𝖿 𝗍𝗁𝖾 𝖼𝗈𝗆𝗆𝖺𝗇𝖽𝗌.
   𝟤. 𝖳𝗁𝖾 𝖻𝗈𝗍 𝖿𝖾𝗍𝖼𝗁𝖾𝗌 𝗍𝗁𝖾 𝗆𝖾𝖽𝗂𝖺 𝖺𝗇𝖽 𝗎𝗌𝖾𝗌 𝖦𝗈𝗈𝗀𝗅𝖾 𝖱𝖾𝗏𝖾𝗋𝗌𝖾 𝖨𝗆𝖺𝗀𝖾 𝖲𝖾𝖺𝗋𝖼𝗁 𝗍𝗈 𝖿𝗂𝗇𝖽 𝗌𝗂𝗆𝗂𝗅𝖺𝗋 𝗈𝗋 𝗋𝖾𝗅𝖺𝗍𝖾𝖽 𝗂𝗆𝖺𝗀𝖾𝗌.
   𝟥. 𝖠 𝗅𝗂𝗇𝗄 𝗍𝗈 𝗍𝗁𝖾 𝗌𝖾𝖺𝗋𝖼𝗁 𝗋𝖾𝗌𝗎𝗅𝗍𝗌 𝗐𝗂𝗅𝗅 𝖻𝖾 𝗉𝗋𝗈𝗏𝗂𝖽𝖾𝖽, 𝖺𝗅𝗈𝗇𝗀 𝗐𝗂𝗍𝗁 𝖺 𝖻𝗎𝗍𝗍𝗈𝗇 𝗍𝗈 𝗈𝗉𝖾𝗇 𝗍𝗁𝖾 𝗅𝗂𝗇𝗄.
 
- **𝖮𝗎𝗍𝗉𝗎𝗍:**
 ✧ 𝖳𝗁𝖾 𝖻𝗈𝗍 𝗐𝗂𝗅𝗅 𝗋𝖾𝗍𝗎𝗋𝗇 𝗍𝗁𝖾 𝖼𝗅𝗈𝗌𝖾𝗌𝗍 𝗆𝖺𝗍𝖼𝗁 𝖿𝗈𝗎𝗇𝖽 𝗈𝗇 𝖦𝗈𝗈𝗀𝗅𝖾, 𝗈𝗋 𝗇𝗈𝗍𝗂𝖿𝗒 𝗂𝖿 𝗇𝗈 𝗆𝖺𝗍𝖼𝗁𝖾𝗌 𝖺𝗋𝖾 𝖿𝗈𝗎𝗇𝖽.
 
"""