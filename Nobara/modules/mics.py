import asyncio
import re
import requests
from pyrogram import filters, Client, enums
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from Nobara import app 
from config import config
from Nobara.decorator.save import save 
from Nobara.decorator.errors import error
from Nobara.helper.ai_provider import get_ai_response

_genius_client = None


def _get_genius_client():
    """Lazily builds a lyricsgenius.Genius client, or None if no real token is configured."""
    global _genius_client
    token = getattr(config, "LYRICS_GENIUS_TOKEN", None)
    if not token or token in ("x-x", ""):
        return None
    if _genius_client is None:
        try:
            import lyricsgenius
            # Construct with just the token (always safe across lyricsgenius
            # versions), then set the rest as plain attributes afterward -
            # passing them as constructor kwargs crashed with "unexpected
            # keyword argument" on some installed versions.
            client = lyricsgenius.Genius(token)
            client.verbose = False
            client.remove_section_headers = False
            client.skip_non_songs = True
            client.timeout = 15
            client.retries = 1
            _genius_client = client
        except Exception:
            return None
    return _genius_client


def _clean_genius_lyrics(raw: str) -> str:
    """lyricsgenius includes a couple of Genius-page artifacts in the raw
    scrape - strip them so the output is just the lyrics."""
    text = re.sub(r"^\d+\s*Contributors?.*?Lyrics", "", raw, count=1, flags=re.S).strip()
    text = re.sub(r"\d*Embed$", "", text).strip()
    return text


async def fetch_lyrics_via_genius(query: str):
    """
    Looks the song up on Genius (a real, accurate lyrics database), instead
    of relying on an AI to recall lyrics from memory - LLMs are well known
    to hallucinate wrong/approximate lyrics or match the wrong song
    entirely, which is exactly the "gives the wrong song" symptom this
    replaces. Returns None (not an error) if no Genius token is configured
    or nothing is found, so the caller can fall back to AI.
    """
    client = _get_genius_client()
    if not client:
        return None
    try:
        song = await asyncio.to_thread(client.search_song, query)
    except Exception:
        return None
    if not song or not song.lyrics:
        return None
    lyrics = _clean_genius_lyrics(song.lyrics)
    if not lyrics:
        return None
    return f"🎵 {song.title}\n🎤 {song.artist}\n\n{lyrics}"


async def fetch_song_data_via_ai(query: str, request_type: str):
    """
    Uses the multi-provider AI to fetch song lyrics or metadata.
    This completely avoids Cloudflare blocks, scraping issues, and dead APIs.
    """
    if request_type == "lyrics":
        sys_prompt = "You are a highly accurate music database. Provide ONLY the full, official lyrics for the requested song. Do not add conversational text, disclaimers, or formatting other than the lyrics themselves. Put the Song Title and Artist at the very top."
        user_prompt = f"Provide the lyrics for the song: {query}"
    else:
        sys_prompt = "You are a highly accurate music database. Provide details for the requested song in this exact format:\n🎵 Song: [Title]\n🎤 Artist: [Artist]\n💿 Album: [Album]\n📅 Release Year: [Year]\n🏷️ Genre: [Genre]\n\nDo not add any other conversational text."
        user_prompt = f"Provide metadata for the song: {query}"

    try:
        response_text, provider = await get_ai_response(user_prompt, system_prompt=sys_prompt)
        if not response_text:
            return {"error": "All AI providers failed to process the request at this moment."}
        return {"data": response_text}
    except Exception as e:
        return {"error": f"An unexpected AI error occurred: {str(e)[:200]}"}

def fetch_gender(name: str):
    """
    Synchronously fetch gender prediction algorithms via the Genderize API.
    Wrapped in structural exception handling to prevent runtime crashes.
    """
    try:
        response = requests.get(f"https://api.genderize.io/?name={name}", timeout=10)
        if response.status_code == 200:
            data = response.json()
            return {
                "gender": data.get("gender"),
                "probability": data.get("probability"),
                "count": data.get("count")
            }
        else:
            return {"error": f"Genderize API returned anomalous status code {response.status_code}"}
    except Exception as e:
        return {"error": f"An unhandled exception occurred during resolution: {str(e)[:200]}"}

@app.on_message(filters.command("lyrics", config.COMMAND_PREFIXES))
@error
@save
async def send_lyrics(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("⚠️ **𝖲𝗒𝗇𝗍𝖺𝗑 𝖤𝗋𝗋𝗈𝗋:**\n𝖯𝗅𝖾𝖺𝗌𝖾 𝗉𝗋𝗈𝗏𝗂𝖽𝖾 𝖺 𝗏𝖺𝗅𝗂𝖽 𝗌𝗈𝗇𝗀 𝗇𝖺𝗆𝖾.\n\n📌 `𝖴𝗌𝖺𝗀𝖾: /lyrics [song name]`")

    song_name = " ".join(message.command[1:])
    status_msg = await message.reply_text("🔎 **𝖲𝖾𝖺𝗋𝖼𝗁𝗂𝗇𝗀 𝖿𝗈𝗋 𝗅𝗒𝗋𝗂𝖼𝗌...**")

    lyrics_text = await fetch_lyrics_via_genius(song_name)

    if not lyrics_text:
        # No Genius token configured, or nothing found there - fall back to AI.
        # (Less reliable: an AI can hallucinate/mismatch songs, which is
        # exactly why Genius is tried first.)
        await status_msg.edit_text("🔎 **𝖭𝗈𝗍 𝗈𝗇 𝖦𝖾𝗇𝗂𝗎𝗌, 𝗍𝗋𝗒𝗂𝗇𝗀 𝖠𝖨 𝖿𝖺𝗅𝗅𝖻𝖺𝖼𝗄...**")
        data = await fetch_song_data_via_ai(song_name, "lyrics")
        if "error" in data:
            return await status_msg.edit_text(f"❌ **𝖱𝖾𝗌𝗈𝗅𝗎𝗍𝗂𝗈𝗇 𝖥𝖺𝗂𝗅𝖾𝖽:**\n`{data['error']}`")
        lyrics_text = data["data"]

    # Telegram strictly enforces a 4096 character limit per discrete message entity.
    # The string must be chunked iteratively to guarantee full transmission of extensive lyrical content.
    if len(lyrics_text) > 4096:
        await status_msg.delete()
        for chunk in [lyrics_text[i:i + 4000] for i in range(0, len(lyrics_text), 4000)]:
            await message.reply_text(chunk, disable_web_page_preview=True)
            await asyncio.sleep(1.2) # Enforce a minor synthetic delay to bypass Telegram's strict FloodWait protocols
    else:
        await status_msg.edit_text(lyrics_text, disable_web_page_preview=True)
    
@app.on_message(filters.command("searchsong", config.COMMAND_PREFIXES))
@error
@save
async def search_song(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("⚠️ **𝖲𝗒𝗇𝗍𝖺𝗑 𝖤𝗋𝗋𝗈𝗋:**\n𝖯𝗅𝖾𝖺𝗌𝖾 𝗉𝗋𝗈𝗏𝗂𝖽𝖾 𝖺 𝗏𝖺𝗅𝗂𝖽 𝗌𝗈𝗇𝗀 𝗇𝖺𝗆𝖾.\n\n📌 `𝖴𝗌𝖺𝗀𝖾: /searchsong [song name]`")

    song_name = " ".join(message.command[1:])
    status_msg = await message.reply_text("🔎 **𝖰𝗎𝖾𝗋𝗒𝗂𝗇𝗀 𝖠𝖨 𝗆𝗎𝗌𝗂𝖼 𝗆𝖾𝗍𝖺𝖽𝖺𝗍𝖺 𝗋𝖾𝗀𝗂𝗌𝗍𝗋𝗒...**")

    data = await fetch_song_data_via_ai(song_name, "metadata")
    
    if "error" in data:
        return await status_msg.edit_text(f"❌ **𝖱𝖾𝗌𝗈𝗅𝗎𝗍𝗂𝗈𝗇 𝖥𝖺𝗂𝗅𝖾𝖽:**\n`{data['error']}`")

    await status_msg.edit_text(data["data"], disable_web_page_preview=True)
    
@app.on_message(filters.command("gender", config.COMMAND_PREFIXES))
@error
@save
async def gender_command(client: Client, message: Message):
    # Check if a name is provided or a user's message is replied to
    if len(message.command) >= 2:
        display_name = " ".join(message.command[1:])
        api_name = message.command[1]  # Use first word for better API prediction
    elif message.reply_to_message and message.reply_to_message.from_user:
        user = message.reply_to_message.from_user
        display_name = user.first_name
        if user.last_name:
            display_name += f" {user.last_name}"
        # Extract the first word of the first name for the API
        api_name = user.first_name.split()[0] if user.first_name else ""
    else:
        return await message.reply_text("⚠️ **𝖲𝗒𝗇𝗍𝖺𝗑 𝖤𝗋𝗋𝗈𝗋:**\n𝖯𝗅𝖾𝖺𝗌𝖾 𝗉𝗋𝗈𝗏𝗂𝖽𝖾 𝖺 𝗇𝖺𝗆𝖾 𝗈𝗋 𝗋𝖾𝗉𝗅𝗒 𝗍𝗈 𝖺 𝗎𝗌𝖾𝗋'𝗌 𝗆𝖾𝗌𝗌𝖺𝗀𝖾.\n\n📌 `𝖴𝗌𝖺𝗀𝖾: /gender [name]`")

    if not api_name:
        return await message.reply_text("❌ **𝖤𝗋𝗋𝗈𝗋:** 𝖢𝗈𝗎𝗅𝖽 𝗇𝗈𝗍 𝖾𝗑𝗍𝗋𝖺𝖼𝗍 𝖺 𝗏𝖺𝗅𝗂𝖽 𝗇𝖺𝗆𝖾.")

    status_msg = await message.reply_text("🔍 **𝖢𝗈𝗆𝗉𝗎𝗍𝗂𝗇𝗀 𝗀𝖾𝗇𝖽𝖾𝗋 𝗉𝗋𝗈𝖻𝖺𝖻𝗂𝗅𝗂𝗍𝗂𝖾𝗌 𝗏𝗂𝖺 𝗆𝖺𝖼𝗁𝗂𝗇𝖾 𝗅𝖾𝖺𝗋𝗇𝗂𝗇𝗀 𝗆𝗈𝖽𝖾𝗅...**")

    gender_info = fetch_gender(api_name)

    if "error" in gender_info:
        return await status_msg.edit_text(f"⚠️ **𝖲𝗒𝗌𝗍𝖾𝗆 𝖥𝖺𝗎𝗅𝗍:**\n`{gender_info['error']}`")

    if gender_info.get("gender") is None:
        return await status_msg.edit_text("❌ **𝖣𝖺𝗍𝖺 𝖣𝖾𝖿𝗂𝖼𝗂𝖾𝗇𝖼𝗒:**\n𝖨𝗇𝗌𝗎𝖿𝖿𝗂𝖼𝗂𝖾𝗇𝗍 𝗌𝗍𝖺𝗍𝗂𝗌𝗍𝗂𝖼𝖺𝗅 𝖽𝖺𝗍𝖺 𝖾𝗑𝗂𝗌𝗍𝗌 𝗍𝗈 𝗀𝖾𝗇𝖾𝗋𝖺𝗍𝖾 𝖺 𝗁𝗂𝗀𝗁-𝖼𝗈𝗇𝖿𝗂𝖽𝖾𝗇𝖼𝖾 𝗉𝗋𝖾𝖽𝗂𝖼𝗍𝗂𝗈𝗇 𝖿𝗈𝗋 𝗍𝗁𝗂𝗌 𝗌𝗉𝖾𝖼𝗂𝖿𝗂𝖼 𝗇𝗈𝗆𝖾𝗇𝖼𝗅𝖺𝗍𝗎𝗋𝖾.")

    gender = gender_info["gender"].capitalize()
    probability = gender_info["probability"] * 100
    count = gender_info["count"]

    response = (
        f"👤 **𝖳𝖺𝗋𝗀𝖾𝗍 𝖭𝖺𝗆𝖾:** {display_name}\n"
        f"🧭 **𝖯𝗋𝖾𝖽𝗂𝖼𝗍𝖾𝖽 𝖦𝖾𝗇𝖽𝖾𝗋:** {gender}\n"
        f"📊 **𝖠𝖼𝖼𝗎𝗋𝖺𝖼𝗒 𝖯𝗋𝗈𝖻𝖺𝖻𝗂𝗅𝗂𝗍𝗒:** {probability:.2f}%\n"
        f"🧮 **𝖲𝗍𝖺𝗍𝗂𝗌𝗍𝗂𝖼𝖺𝗅 𝖲𝖺𝗆𝗉𝗅𝖾 𝖲𝗂𝗓𝖾:** {count} 𝗂𝗇𝖽𝖾𝗉𝖾𝗇𝖽𝖾𝗇𝗍 𝗈𝖼𝖼𝗎𝗋𝗋𝖾𝗇𝖼𝖾𝗌"
    )

    await status_msg.edit_text(response)


# ——————————————————————————————————————————————————————————————
# /donate - support menu with per-network wallet addresses
# ——————————————————————————————————————————————————————————————
_DONATE_NETWORKS = {
    "dn_btc": ("₿ Bitcoin (BTC)", "DONATE_BTC_ADDRESS"),
    "dn_usdt": ("💲 USDT (TRC20)", "DONATE_USDT_TRC20_ADDRESS"),
    "dn_eth": ("💎 Ethereum (ETH)", "DONATE_ETH_ADDRESS"),
    "dn_bnb": ("🟡 BNB (BEP20)", "DONATE_BNB_BEP20_ADDRESS"),
}


def _donate_menu_markup():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("₿ Bitcoin", callback_data="dn_btc"),
            InlineKeyboardButton("💲 USDT (TRC20)", callback_data="dn_usdt"),
        ],
        [
            InlineKeyboardButton("💎 Ethereum", callback_data="dn_eth"),
            InlineKeyboardButton("🟡 BNB (BEP20)", callback_data="dn_bnb"),
        ],
        [InlineKeyboardButton("💳 Other Methods", callback_data="dn_others")],
        [InlineKeyboardButton("✗ Close ✗", callback_data="dn_close")],
    ])


_DONATE_TEXT = (
    "<b>💸 Support & Donate</b>\n\n"
    "Support the development of this project by contributing. "
    "Your small help keeps our servers alive and fast! 🚀\n\n"
    "──────────────────────\n"
    "<b>Select payment network 👇</b>"
)


@app.on_message(filters.command("donate", prefixes=config.COMMAND_PREFIXES) & (filters.group | filters.private))
@error
@save
async def donate_menu(client: Client, message: Message):
    await message.reply_text(
        text=_DONATE_TEXT,
        reply_markup=_donate_menu_markup(),
        disable_web_page_preview=True,
        quote=message.chat.type != enums.ChatType.PRIVATE,
    )


@app.on_callback_query(filters.regex(r"^dn_(btc|usdt|eth|bnb)$"))
@error
async def donate_network_callback(client: Client, query: CallbackQuery):
    label, attr = _DONATE_NETWORKS[query.data]
    address = getattr(config, attr, "") or ""

    if not address:
        await query.answer("This network isn't configured yet - ask the bot owner to add it.", show_alert=True)
        return

    text = (
        f"<b>{label} Address</b>\n\n"
        f"<code>{address}</code>\n\n"
        f"<i>Tap the address above to copy it.</i>\n\n"
        f"Thank you for your support! 💜"
    )
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data="dn_back")],
        [InlineKeyboardButton("✗ Close ✗", callback_data="dn_close")],
    ])
    await query.message.edit_text(text, reply_markup=markup, disable_web_page_preview=True)
    await query.answer()


@app.on_callback_query(filters.regex(r"^dn_others$"))
@error
async def donate_others_callback(client: Client, query: CallbackQuery):
    text = f"<b>💳 Other Methods</b>\n\n{getattr(config, 'DONATE_OTHER_METHODS', '')}"
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data="dn_back")],
        [InlineKeyboardButton("✗ Close ✗", callback_data="dn_close")],
    ])
    await query.message.edit_text(text, reply_markup=markup, disable_web_page_preview=True)
    await query.answer()


@app.on_callback_query(filters.regex(r"^dn_back$"))
@error
async def donate_back_callback(client: Client, query: CallbackQuery):
    await query.message.edit_text(_DONATE_TEXT, reply_markup=_donate_menu_markup(), disable_web_page_preview=True)
    await query.answer()


@app.on_callback_query(filters.regex(r"^dn_close$"))
@error
async def donate_close_callback(client: Client, query: CallbackQuery):
    try:
        await query.message.delete()
    except Exception:
        await query.answer("❌ Couldn't close this menu.", show_alert=True)


__module__ = "𝖬𝖨𝖢𝖲"

__help__ = """**𝖬𝗎𝗌𝗂𝖼 𝖠𝗇𝖽 𝖦𝖾𝗇𝖽𝖾𝗋 𝖳𝗈𝗈𝗅𝗌:**

✧ **Lyrics Finder:**
   - `/lyrics <song name>`: 𝖥𝗂𝗇𝖽 𝗅𝗒𝗋𝗂𝖼𝗌 𝖿𝗈𝗋 𝖺 𝗀𝗂𝗏𝖾𝗇 𝗌𝗈𝗇𝗀.

✧ **Song Search:**
   - `/searchsong <song name>`: 𝖲𝖾𝖺𝗋𝖼𝗁 𝗍𝗈 𝖿𝗂𝗇𝖽 𝗌𝗈𝗇𝗀 𝗂𝗇𝖿𝗈𝗋𝗆𝖺𝗍𝗂𝗈𝗇 𝗅𝗂𝗄𝖾 𝗍𝗂𝗍𝗅𝖾, 𝖺𝗋𝗍𝗂𝗌𝗍, 𝖺𝗅𝖻𝗎𝗆, 𝖺𝗇𝖽 𝗆𝗈𝗋𝖾.

✧ **Gender Prediction:**
   - `/gender <name>`: 𝖢𝗁𝖾𝖼𝗄 𝗀𝖾𝗇𝖽𝖾𝗋 𝗉𝗋𝖾𝖽𝗂𝖼𝗍𝗂𝗈𝗇 𝖿𝗈𝗋 𝖺 𝗇𝖺𝗆𝖾. (𝖸𝗈𝗎 𝖼𝖺𝗇 𝖺𝗅𝗌𝗈 𝗋𝖾𝗉𝗅𝗒 𝗍𝗈 𝖺 𝗎𝗌𝖾𝗋'𝗌 𝗆𝖾𝗌𝗌𝖺𝗀𝖾 𝗐𝗂𝗍𝗁 𝗍𝗁𝗂𝗌 𝖼𝗈𝗆𝗆𝖺𝗇𝖽!)

✧ **Support:**
   - `/donate`: 𝖮𝗉𝖾𝗇𝗌 𝖺 𝗆𝖾𝗇𝗎 𝗐𝗂𝗍𝗁 𝗐𝖺𝗅𝗅𝖾𝗍 𝖺𝖽𝖽𝗋𝖾𝗌𝗌𝖾𝗌 𝗍𝗈 𝗌𝗎𝗉𝗉𝗈𝗋𝗍 𝗍𝗁𝖾 𝗉𝗋𝗈𝗃𝖾𝖼𝗍.
"""
