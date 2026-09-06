from gpytranslate import Translator
from pyrogram import Client, filters
from pyrogram.types import Message
from Nobara import app
from pyrogram.enums import ParseMode
from config import config
from Nobara.decorator.save import save 
from Nobara.decorator.errors import error

trans = Translator()

@app.on_message(filters.command(["tr", "tl" , "translate"]  , prefixes=config.COMMAND_PREFIXES))
@error
@save
async def translate_handler(client: Client, message: Message):
    reply_msg = message.reply_to_message

    if not reply_msg:
        await message.reply_text(
            "**𝖱𝖾𝗉𝗅𝗒 𝗍𝗈 𝖺 𝗆𝖾𝗌𝗌𝖺𝗀𝖾 𝗍𝗈 𝗍𝗋𝖺𝗇𝗌𝗅𝖺𝗍𝖾 𝗂𝗍!**"
        )
        return

    # Determine the text to translate
    to_translate = reply_msg.caption or reply_msg.text
    if not to_translate:
        await message.reply_text(
            "**𝖳𝖾𝗑𝗍 𝗍𝗈 𝗍𝗋𝖺𝗇𝗌𝗅𝖺𝗍𝖾 𝗇𝗈𝗍 𝖿𝗈𝗎𝗇𝖽!**"
        )
        return

    # Parse the command arguments
    try:
        args = message.text.split()[1] if len(message.command) > 1 else None
        if args and "//" in args:
            source, dest = args.split("//")
        else:
            source = await trans.detect(to_translate)  # Returns the detected language code
            dest = args or "en"  # Default to English if no target language is specified
    except Exception as e:
        await message.reply_text(f"𝖤𝗋𝗋𝗈𝗋 𝗉𝖺𝗋𝗌𝗂𝗇𝗀 𝖺𝗋𝗀𝗎𝗆𝖾𝗇𝗍𝗌: {e}")
        return

    # Perform the translation
    try:
        translation = await trans.translate(
            to_translate, sourcelang=source, targetlang=dest
        )
        reply = (
            f"<b>𝖳𝗋𝖺𝗇𝗌𝗅𝖺𝗍𝖾𝖽 𝖿𝗋𝗈𝗆 {source} 𝗍𝗈 {dest}</b>:\n"
            f"<code>{translation.text}</code>"
        )
        await message.reply_text(
            reply,
            parse_mode=ParseMode.HTML,
        )
    except Exception as e:
        await message.reply_text(
            f"𝖠𝗇 𝖾𝗋𝗋𝗈𝗋 𝗈𝖼𝖼𝗎𝗋𝗋𝖾𝖽 𝖽𝗎𝗋𝗂𝗇𝗀 𝗍𝗋𝖺𝗇𝗌𝗅𝖺𝗍𝗂𝗈𝗇: {e}",
        )

@app.on_message(filters.command(["lang", "languages"]  , prefixes=config.COMMAND_PREFIXES) & (filters.private | filters.group))
async def languages_handler(client: Client, message: Message):
    await message.reply_text(
        "𝖢𝗅𝗂𝖼𝗄 [𝗁𝖾𝗋𝖾](https://telegra.ph/Lang-Codes-03-19-3) 𝗍𝗈 𝗌𝖾𝖾 𝗍𝗁𝖾 𝗅𝗂𝗌𝗍 𝗈𝖿 𝗌𝗎𝗉𝗉𝗈𝗋𝗍𝖾𝖽 𝗅𝖺𝗇𝗀𝗎𝖺𝗀𝖾 𝖼𝗈𝖽𝖾𝗌!",
        disable_web_page_preview=True,
        parse_mode=ParseMode.MARKDOWN,
    )


# Module information
__module__ = "𝖳𝗋𝖺𝗇𝗌𝗅𝖺𝗍𝗂𝗈𝗇"

__help__ = """**𝖴𝗌𝖾𝗋 𝖢𝗈𝗆𝗆𝖺𝗇𝖽𝗌:**
  ✧ `/𝗍𝗋 <𝗅𝖺𝗇𝗀_𝖼𝗈𝖽𝖾>//<𝗅𝖺𝗇𝗀_𝖼𝗈𝖽𝖾>`**:** 𝖳𝗋𝖺𝗇𝗌𝗅𝖺𝗍𝖾 𝗍𝗁𝖾 𝗋𝖾𝗉𝗅𝗂𝖾𝖽 𝗆𝖾𝗌𝗌𝖺𝗀𝖾 𝖿𝗋𝗈𝗆 𝗌𝗈𝗎𝗋𝖼𝖾 𝗍𝗈 𝗍𝖺𝗋𝗀𝖾𝗍 𝗅𝖺𝗇𝗀𝗎𝖺𝗀𝖾. 
      𝖤𝗑𝖺𝗆𝗉𝗅𝖾: `/𝗍𝗋 𝖾𝗇//𝖿𝗋` 𝗍𝗋𝖺𝗇𝗌𝗅𝖺𝗍𝖾𝗌 𝖿𝗋𝗈𝗆 𝖤𝗇𝗀𝗅𝗂𝗌𝗁 𝗍𝗈 𝖥𝗋𝖾𝗇𝖼𝗁.
   ✧ `/𝗍𝗋 <𝗅𝖺𝗇𝗀_𝖼𝗈𝖽𝖾>`**:** 𝖳𝗋𝖺𝗇𝗌𝗅𝖺𝗍𝖾 𝗍𝗁𝖾 𝗋𝖾𝗉𝗅𝗂𝖾𝖽 𝗆𝖾𝗌𝗌𝖺𝗀𝖾 𝗍𝗈 𝗍𝗁𝖾 𝗌𝗉𝖾𝖼𝗂𝖿𝗂𝖾𝖽 𝗅𝖺𝗇𝗀𝗎𝖺𝗀𝖾. 𝖠𝗎𝗍𝗈-𝖽𝖾𝗍𝖾𝖼𝗍𝗌 𝗍𝗁𝖾 𝗌𝗈𝗎𝗋𝖼𝖾 𝗅𝖺𝗇𝗀𝗎𝖺𝗀𝖾. 
      𝖤𝗑𝖺𝗆𝗉𝗅𝖾: `/𝗍𝗋 𝖾𝗇` 𝗍𝗋𝖺𝗇𝗌𝗅𝖺𝗍𝖾𝗌 𝗍𝗈 𝖤𝗇𝗀𝗅𝗂𝗌𝗁.
   ✧ `/𝗍𝗅`**:** 𝖠𝗅𝗂𝖺𝗌 𝖿𝗈𝗋 `/𝗍𝗋`.
 
**𝖠𝖽𝖽𝗂𝗍𝗂𝗈𝗇𝖺𝗅 𝖢𝗈𝗆𝗆𝖺𝗇𝖽𝗌:**
  ✧ `/𝗅𝖺𝗇𝗀𝗎𝖺𝗀𝖾𝗌`**:** 𝖵𝗂𝖾𝗐 𝗍𝗁𝖾 𝗅𝗂𝗌𝗍 𝗈𝖿 𝗌𝗎𝗉𝗉𝗈𝗋𝗍𝖾𝖽 𝗅𝖺𝗇𝗀𝗎𝖺𝗀𝖾 𝖼𝗈𝖽𝖾𝗌.
 """
