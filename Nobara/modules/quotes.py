import random
from pyrogram import filters , Client 
from pyrogram.types import Message , CallbackQuery
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from Nobara import app as pgram 
from Nobara.vars import quotes , QUOTES_IMG
from pyrogram.enums import ParseMode
from pyrogram.types import InputMediaPhoto
import requests
from config import config 
from Nobara.decorator.save import save 
from Nobara.decorator.errors import error


# Anime quotes
def anime_quote():
    quote, character, anime = random.choice(quotes)
    return quote, character, anime

# Command: /quote - Sends a text-based anime quote
@pgram.on_message(filters.command(["animequote" , "aquote"]  , prefixes=config.COMMAND_PREFIXES))
@error
@save
async def text_quote(_, message):
    quote, character, anime = anime_quote()
    text = f"<i>❝ {quote} ❞</i>\n\n<b>{character}</b> from <b>{anime}</b>"
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("𝖢𝗁𝖺𝗇𝗀𝖾 🔁", callback_data="change_quote")]]
    )
    await message.reply_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)

# Command: /animequotes - Sends an image-based anime quote
@pgram.on_message(filters.command("iaquotes"  , prefixes=config.COMMAND_PREFIXES))
@error
@save
async def image_quote(_, message):
    random_image = random.choice(QUOTES_IMG)
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("𝖢𝗁𝖺𝗇𝗀𝖾 🔁", callback_data="change_image_quote")]]
    )
    await message.reply_photo(photo=random_image, reply_markup=keyboard)

# Callback query for changing text-based quotes
@pgram.on_callback_query(filters.regex("change_quote"))
@error
async def change_text_quote(_, callback_query):
    quote, character, anime = anime_quote()
    text = f"<i>❝ {quote} ❞</i>\n\n<b>{character}</b> from <b>{anime}</b>"
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("𝖢𝗁𝖺𝗇𝗀𝖾 🔁", callback_data="change_quote")]]
    )
    await callback_query.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)

@pgram.on_callback_query(filters.regex("change_image_quote"))
@error
async def change_image_quote(_, callback_query):
    random_image = random.choice(QUOTES_IMG)
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("𝖢𝗁𝖺𝗇𝗀𝖾 🔁", callback_data="change_image_quote")]]
    )
    await callback_query.message.edit_media(
        InputMediaPhoto(media=random_image),
        reply_markup=keyboard
    )

# Function to fetch Shayri from the API
def get_random_shayri():
    try:
        response = requests.get(config.shayri_api_url)
        if response.status_code == 200:
            data = response.json()
            shayri = data.get("quote", "शायरी प्राप्त करने में त्रुटि हुई!")
            shayri_type = data.get("type", "अनजान प्रकार")
            return shayri, shayri_type
        else:
            return "⚠️ शायरी प्राप्त करने में त्रुटि हुई। कृपया बाद में प्रयास करें।", None
    except Exception as e:
        return f"⚠️ त्रुटि: {str(e)}", None

# Command to send Shayri with a button
@pgram.on_message(filters.command("shayri"  , prefixes=config.COMMAND_PREFIXES))
@pgram.on_message(filters.regex(r"(?i)^Yumeko Ek Shayri Sunao$") & filters.group)
@error
@save
async def fetch_shayri(client: Client, message: Message):
    shayri, shayri_type = get_random_shayri()
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("🔁 𝖢𝗁𝖺𝗇𝗀𝖾", callback_data="change_shayri")]]
    )
    if shayri_type:
        await message.reply_text(
            f"**शायरी का प्रकार**: {shayri_type.capitalize()}\n\n❝{shayri}❞",
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await message.reply_text(shayri)

# Callback to change Shayri
@pgram.on_callback_query(filters.regex("change_shayri"))
@error
async def change_shayri(client: Client, callback_query: CallbackQuery):
    shayri, shayri_type = get_random_shayri()
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("🔁 Change", callback_data="change_shayri")]]
    )
    if shayri_type:
        await callback_query.message.edit_text(
            f"**शायरी का प्रकार**: {shayri_type.capitalize()}\n\n❝{shayri}❞",
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await callback_query.answer(shayri, show_alert=True)
        
__module__ = "𝖰𝗎𝗈𝗍𝖾𝗌"



__help__ = """ ✧ `/𝖺𝗊𝗎𝗈𝗍𝖾` **:** 𝖦𝖾𝗍 𝖱𝖺𝗇𝖽𝗈𝗆 𝖠𝗇𝗂𝗆𝖾 𝖰𝗎𝗈𝗍𝖾𝗌.
   ✧ `/𝗂𝖺𝗊𝗎𝗈𝗍𝖾𝗌` **:** 𝖦𝖾𝗍 𝖱𝖺𝗇𝖽𝗈𝗆 𝖠𝗇𝗂𝗆𝖾 𝖰𝗎𝗈𝗍𝖾𝗌 𝖳𝗁𝗋𝗈𝗎𝗀𝗁 𝖨𝗆𝖺𝗀𝖾.
   ✧ `/𝗌𝗁𝖺𝗒𝗋𝗂` **:** 𝖦𝖾𝗍 𝖱𝖺𝗇𝖽𝗈𝗆 𝖧𝗂𝗇𝖽𝗂 𝖲𝗁𝖺𝗒𝗋𝗂𝗌.
 """
