import random
import asyncio
import aiohttp
import pyjokes
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode

from Nobara import app
from Nobara.vars import FLIRT as FLIRT_STRINGS, TOSS as TOSS_STRINGS, EYES, MOUTHS, EARS, DECIDE as DECIDE_STRINGS, weebyfont, normiefont 
from config import config
from Nobara.decorator.save import save 
from Nobara.decorator.errors import error

# Helper function for API requests
async def fetch_from_api(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=5) as response:
            response.raise_for_status()
            return await response.json()

@app.on_message(filters.command("pickwinner", prefixes=config.COMMAND_PREFIXES))
@error
@save
async def pick_winner(client: Client, message: Message):
    participants = message.text.split()[1:]
    if len(participants) < 2:
        return await message.reply_text("⚠️ **𝖯𝗅𝖾𝖺𝗌𝖾 𝗉𝗋𝗈𝗏𝗂𝖽𝖾 𝖺𝗍 𝗅𝖾𝖺𝗌𝗍 𝟤 𝗉𝖺𝗋𝗍𝗂𝖼𝗂𝗉𝖺𝗇𝗍𝗌.**\n📌 `𝖤𝗑: /pickwinner Nobita Shizuka Doraemon`")
    
    m = await message.reply_text("🔄 **𝖲𝗁𝗎𝖿𝖿𝗅𝗂𝗇𝗀 𝗉𝖺𝗋𝗍𝗂𝖼𝗂𝗉𝖺𝗇𝗍𝗌...**")
    await asyncio.sleep(1.5)
    winner = random.choice(participants)
    await m.edit_text(f"🎉 **𝖳𝗁𝖾 𝗐𝗂𝗇𝗇𝖾𝗋 𝗂𝗌:** ✨ {winner} ✨")

@app.on_message(filters.command("hyperlink", prefixes=config.COMMAND_PREFIXES))
@error
@save
async def hyperlink_command(client: Client, message: Message):
    args = message.text.split()[1:]
    if len(args) >= 2:
        text = " ".join(args[:-1])
        link = args[-1]
        hyperlink = f"[{text}]({link})"
        await message.reply_text(hyperlink, disable_web_page_preview=True, parse_mode=ParseMode.MARKDOWN)
    else:
        await message.reply_text("⚠️ **𝖨𝗇𝗏𝖺𝗅𝗂𝖽 𝖿𝗈𝗋𝗆𝖺𝗍!**\n📌 `𝖴𝗌𝖾: /hyperlink <text> <link>`")

@app.on_message(filters.command("joke", prefixes=config.COMMAND_PREFIXES))
@app.on_message(filters.regex(r"(?i)^Yumeko Ek Joke Sunao$"))
@error
@save
async def joke(client: Client, message: Message):
    # Fixed using pyjokes (Offline and 100% reliable)
    joke_text = pyjokes.get_joke()
    await message.reply_text(f"😂 **𝖧𝖾𝗋𝖾'𝗌 𝖺 𝗃𝗈𝗄𝖾 𝖿𝗈𝗋 𝗒𝗈𝗎:**\n\n👉 `{joke_text}`", parse_mode=ParseMode.MARKDOWN)

@app.on_message(filters.command("truth", prefixes=config.COMMAND_PREFIXES))
@error
@save
async def truth(client: Client, message: Message):
    local_truths = [
        "𝖶𝗁𝖾𝗇 𝗐𝖺𝗌 𝗍𝗁𝖾 𝗅𝖺𝗌𝗍 𝗍𝗂𝗆𝖾 𝗒𝗈𝗎 𝗅𝗂𝖾𝖽?",
        "𝖶𝗁𝖺𝗍 𝗂𝗌 𝗍𝗁𝖾 𝗆𝗈𝗌𝗍 𝖾𝗆𝖻𝖺𝗋𝗋𝖺𝗌𝗌𝗂𝗇𝗀 𝗍𝗁𝗂𝗇𝗀 𝗒𝗈𝗎'𝗏𝖾 𝖾𝗏𝖾𝗋 𝗌𝖺𝗂𝖽 𝗍𝗈 𝖺 𝖼𝗋𝗎𝗌𝗁?",
        "𝖧𝖺𝗏𝖾 𝗒𝗈𝗎 𝖾𝗏𝖾𝗋 𝗌𝗍𝖺𝗅𝗄𝖾𝖽 𝗌𝗈𝗆𝖾𝗈𝗇𝖾'𝗌 𝖳𝖾𝗅𝖾𝗀𝗋𝖺𝗆 𝗉𝗋𝗈𝖿𝗂𝗅𝖾?",
        "𝖶𝗁𝗈 𝗂𝗌 𝗒𝗈𝗎𝗋 𝖿𝖺𝗏𝗈𝗋𝗂𝗍𝖾 𝗉𝖾𝗋𝗌𝗈𝗇 𝗂𝗇 𝗍𝗁𝗂𝗌 𝗀𝗋𝗈𝗎𝗉?",
        "𝖧𝖺𝗏𝖾 𝗒𝗈𝗎 𝖾𝗏𝖾𝗋 𝗉𝗋𝖾𝗍𝖾𝗇𝖽𝖾𝖽 𝗍𝗈 𝖻𝖾 𝖠𝖥𝖪 𝗍𝗈 𝗂𝗀𝗇𝗈𝗋𝖾 𝗌𝗈𝗆𝖾𝗈𝗇𝖾?"
    ]
    try:
        truth_question = await fetch_from_api("https://api.truthordarebot.xyz/v1/truth")
        q = truth_question["question"]
    except Exception:
        # Auto Fallback to local list if API is down
        q = random.choice(local_truths)
        
    await message.reply_text(f"🗣️ **𝖳𝗋𝗎𝗍𝗁:**\n\n👉 `{q}`", parse_mode=ParseMode.MARKDOWN)

@app.on_message(filters.command("dare", prefixes=config.COMMAND_PREFIXES))
@error
@save
async def dare(client: Client, message: Message):
    local_dares = [
        "𝖢𝗁𝖺𝗇𝗀𝖾 𝗒𝗈𝗎𝗋 𝖳𝖾𝗅𝖾𝗀𝗋𝖺𝗆 𝖻𝗂𝗈 𝗍𝗈 '𝖨 𝗅𝗈𝗏𝖾 𝖾𝖺𝗍𝗂𝗇𝗀 𝖻𝗎𝗀𝗌' 𝖿𝗈𝗋 𝟤𝟦 𝗁𝗈𝗎𝗋𝗌.",
        "𝖲𝖾𝗇𝖽 𝖺 𝗏𝗈𝗂𝖼𝖾 𝗇𝗈𝗍𝖾 𝗌𝗂𝗇𝗀𝗂𝗇𝗀 𝗍𝗁𝖾 𝖼𝗁𝗈𝗋𝗎𝗌 𝗈𝖿 𝗒𝗈𝗎𝗋 𝖿𝖺𝗏𝗈𝗋𝗂𝗍𝖾 𝗌𝗈𝗇𝗀.",
        "𝖲𝖾𝗍 𝗒𝗈𝗎𝗋 𝗉𝗋𝗈𝖿𝗂𝗅𝖾 𝗉𝗂𝖼𝗍𝗎𝗋𝖾 𝗍𝗈 𝖺 𝖿𝗎𝗇𝗇𝗒 𝗆𝖾𝗆𝖾 𝖿𝗈𝗋 𝗍𝗁𝖾 𝗇𝖾𝗑𝗍 𝟤 𝗁𝗈𝗎𝗋𝗌.",
        "𝖳𝖺𝗀 𝖺 𝗋𝖺𝗇𝖽𝗈𝗆 𝗉𝖾𝗋𝗌𝗈𝗇 𝗂𝗇 𝗍𝗁𝖾 𝗀𝗋𝗈𝗎𝗉 𝖺𝗇𝖽 𝗌𝖺𝗒 '𝖶𝗁𝗒 𝖺𝗋𝖾 𝗒𝗈𝗎 𝗌𝗈 𝖼𝗎𝗍𝖾?'",
        "𝖲𝗉𝖾𝖺𝗄 𝗈𝗇𝗅𝗒 𝗂𝗇 𝖾𝗆𝗈𝗃𝗂𝗌 𝖿𝗈𝗋 𝗒𝗈𝗎𝗋 𝗇𝖾𝗑𝗍 𝟧 𝗆𝖾𝗌𝗌𝖺𝗀𝖾𝗌."
    ]
    try:
        dare_question = await fetch_from_api("https://api.truthordarebot.xyz/v1/dare")
        q = dare_question["question"]
    except Exception:
        # Auto Fallback to local list if API is down
        q = random.choice(local_dares)
        
    await message.reply_text(f"🔥 **𝖣𝖺𝗋𝖾:**\n\n👉 `{q}`", parse_mode=ParseMode.MARKDOWN)

@app.on_message(filters.command("roll", prefixes=config.COMMAND_PREFIXES))
@error
@save
async def roll(client: Client, message: Message):
    # Upgraded: Sends Native Telegram Dice Animation
    await client.send_dice(message.chat.id, emoji="🎲")

@app.on_message(filters.command("flirt", prefixes=config.COMMAND_PREFIXES))
@app.on_message(filters.regex(r"(?i)^Yumeko flirt$"))
@error
@save
async def flirt(client: Client, message: Message):
    await message.reply_text(random.choice(FLIRT_STRINGS))

@app.on_message(filters.command("toss", prefixes=config.COMMAND_PREFIXES))
@app.on_message(filters.regex(r"(?i)^Yumeko toss$"))
@error
@save
async def toss(client: Client, message: Message):
    result = random.choice(TOSS_STRINGS)
    await message.reply_text(f"🪙 **𝖢𝗈𝗂𝗇 𝖳𝗈𝗌𝗌𝖾𝖽!**\n\n𝖨𝗍'𝗌 **{result}**!")

@app.on_message(filters.command("shrug", prefixes=config.COMMAND_PREFIXES))
@error
@save
async def shrug(client: Client, message: Message):
    await message.reply_text(r"¯\_(ツ)_/¯")

@app.on_message(filters.command("bluetext", prefixes=config.COMMAND_PREFIXES))
@error
@save
async def bluetext(client: Client, message: Message):
    await message.reply_text("/BLUE /TEXT\n/MUST /CLICK\n/I /AM /A /STUPID /ANIMAL /THAT /IS /ATTRACTED /TO /COLORS")

@app.on_message(filters.command("rlg", prefixes=config.COMMAND_PREFIXES))
@error
@save
async def rlg(client: Client, message: Message):
    eyes = random.choice(EYES)
    mouth = random.choice(MOUTHS)
    ears = random.choice(EARS)
    face = f"{ears[0]}{eyes}{mouth}{eyes}{ears[1]}"
    await message.reply_text(face)

@app.on_message(filters.command("decide", prefixes=config.COMMAND_PREFIXES))
@app.on_message(filters.regex(r"(?i)^Yumeko decide$"))
@error
@save
async def decide(client: Client, message: Message):
    decision = random.choice(DECIDE_STRINGS)
    await message.reply_text(f"🤔 **𝖬𝗒 𝖣𝖾𝖼𝗂𝗌𝗂𝗈𝗇:** {decision}")

@app.on_message(filters.command("weebify", prefixes=config.COMMAND_PREFIXES))
@error
@save
async def webify(client: Client, message: Message):
    args = message.command[1:]
    string = ""

    if message.reply_to_message and message.reply_to_message.text:
        string = message.reply_to_message.text.lower().replace(" ", "  ")

    if args:
        string = "  ".join(args).lower()

    if not string:
        await message.reply_text("⚠️ **𝖴𝗌𝖺𝗀𝖾:** `/weebify <text>`")
        return

    for normiecharacter in string:
        if normiecharacter in normiefont:
            weebycharacter = weebyfont[normiefont.index(normiecharacter)]
            string = string.replace(normiecharacter, weebycharacter)

    if message.reply_to_message:
        await message.reply_to_message.reply_text(string)
    else:
        await message.reply_text(string)

__module__ = "𝖤𝗑𝗍𝗋𝖺𝗌"

__help__ = """**𝖥𝗎𝗇 𝖢𝗈𝗆𝗆𝖺𝗇𝖽𝗌:**

- **𝖯𝗂𝖼𝗄 𝖺 𝖶𝗂𝗇𝗇𝖾𝗋:**
  ✧ `/𝗉𝗂𝖼𝗄𝗐𝗂𝗇𝗇𝖾𝗋 <𝗉𝖺𝗋𝗍𝗂𝖼𝗂𝗉𝖺𝗇𝗍𝟣> <𝗉𝖺𝗋𝗍𝗂𝖼𝗂𝗉𝖺𝗇𝗍𝟤>...` **:** 𝖲𝖾𝗅𝖾𝖼𝗍 𝖺 𝗋𝖺𝗇𝖽𝗈𝗆 𝗐𝗂𝗇𝗇𝖾𝗋 𝖿𝗋𝗈𝗆 𝗍𝗁𝖾 𝗅𝗂𝗌𝗍 𝗈𝖿 𝗉𝖺𝗋𝗍𝗂𝖼𝗂𝗉𝖺𝗇𝗍𝗌.
 
- **𝖧𝗒𝗉𝖾𝗋𝗅𝗂𝗇𝗄 𝖢𝗋𝖾𝖺𝗍𝗂𝗈𝗇:**
  ✧ `/𝗁𝗒𝗉𝖾𝗋𝗅𝗂𝗇𝗄 <𝗍𝖾𝗑𝗍> <𝗅𝗂𝗇𝗄>` **:** 𝖢𝗋𝖾𝖺𝗍𝖾 𝖺 𝖼𝗅𝗂𝖼𝗄𝖺𝖻𝗅𝖾 𝗁𝗒𝗉𝖾𝗋𝗅𝗂𝗇𝗄 𝗂𝗇 𝗍𝗁𝖾 𝖿𝗈𝗋𝗆𝖺𝗍 `[𝗍𝖾𝗑𝗍](𝗅𝗂𝗇𝗄)`.
 
- **𝖩𝗈𝗄𝖾𝗌:**
  ✧ `/𝗃𝗈𝗄𝖾` **:** 𝖦𝖾𝗍 𝖺 𝗋𝖺𝗇𝖽𝗈𝗆 𝗃𝗈𝗄𝖾.
 
- **𝖣𝗂𝖼𝖾 𝖱𝗈𝗅𝗅:**
  ✧ `/𝗋𝗈𝗅𝗅` **:** 𝖱𝗈𝗅𝗅 𝖺 𝖽𝗂𝖼𝖾 𝖺𝗇𝖽 𝗀𝖾𝗍 𝖺 𝗋𝖺𝗇𝖽𝗈𝗆 𝗇𝗎𝗆𝖻𝖾𝗋 𝖻𝖾𝗍𝗐𝖾𝖾𝗇 𝟣 𝖺𝗇𝖽 𝟨.
 
- **𝖥𝗅𝗂𝗋𝗍:**
  ✧ `/𝖿𝗅𝗂𝗋𝗍` **:** 𝖦𝖾𝗍 𝖺 𝗋𝖺𝗇𝖽𝗈𝗆 𝖿𝗅𝗂𝗋𝗍𝖺𝗍𝗂𝗈𝗎𝗌 𝗋𝖾𝗌𝗉𝗈𝗇𝗌𝖾.
 
- **𝖳𝗈𝗌𝗌:**
  ✧ `/𝗍𝗈𝗌𝗌` **:** 𝖳𝗈𝗌𝗌 𝖺 𝖼𝗈𝗂𝗇 𝖺𝗇𝖽 𝗀𝖾𝗍 𝖾𝗂𝗍𝗁𝖾𝗋 "𝖧𝖾𝖺𝖽𝗌" 𝗈𝗋 "𝖳𝖺𝗂𝗅𝗌."

- **𝖲𝗁𝗋𝗎𝗀 𝖤𝗆𝗈𝗃𝗂:**
  ✧ `/𝗌𝗁𝗋𝗎𝗀` **:** 𝖦𝖾𝗍 𝗍𝗁𝖾 𝗌𝗁𝗋𝗎𝗀 𝖾𝗆𝗈𝗃𝗂 `(¯\\_(ツ)_/¯)`.
 
- **𝖡𝗅𝗎𝖾 𝖳𝖾𝗑𝗍:**
  ✧ `/𝖻𝗅𝗎𝖾𝗍𝖾𝗑𝗍` **:** 𝖦𝖾𝗍 𝖺 𝗋𝖺𝗇𝖽𝗈𝗆 "𝖻𝗅𝗎𝖾 𝗍𝖾𝗑𝗍" 𝗋𝖾𝗌𝗉𝗈𝗇𝗌𝖾.
 
- **𝖱𝖺𝗇𝖽𝗈𝗆 𝖫𝖾𝗍𝗍𝖾𝗋𝗌 𝖦𝖾𝗇𝖾𝗋𝖺𝗍𝗈𝗋 (𝖱𝖫𝖦):**
  ✧ `/𝗋𝗅𝗀` **:** 𝖦𝖾𝗇𝖾𝗋𝖺𝗍𝖾 𝖺 𝗋𝖺𝗇𝖽𝗈𝗆 𝖼𝗈𝗆𝖻𝗂𝗇𝖺𝗍𝗂𝗈𝗇 𝗈𝖿 𝖾𝗒𝖾𝗌, 𝗆𝗈𝗎𝗍𝗁, 𝖺𝗇𝖽 𝖾𝖺𝗋𝗌 𝗍𝗈 𝖼𝗋𝖾𝖺𝗍𝖾 𝖺 𝖿𝖺𝖼𝖾.
 
- **𝖣𝖾𝖼𝗂𝗌𝗂𝗈𝗇 𝖬𝖺𝗄𝗂𝗇𝗀:**
  ✧ `/𝖽𝖾𝖼𝗂𝖽𝖾` **:** 𝖦𝖾𝗍 𝖺 𝗋𝖺𝗇𝖽𝗈𝗆 𝖽𝖾𝖼𝗂𝗌𝗂𝗈𝗇-𝗆𝖺𝗄𝗂𝗇𝗀 𝗋𝖾𝗌𝗉𝗈𝗇𝗌𝖾 (𝖾.𝗀., "𝖸𝖾𝗌", "𝖭𝗈", 𝖾𝗍𝖼.).
 
- **𝖶𝖾𝖾𝖻𝗂𝖿𝗒 𝖳𝖾𝗑𝗍:**
  ✧ `/𝗐𝖾𝖾𝖻𝗂𝖿𝗒 <𝗍𝖾𝗑𝗍>` **:** 𝖢𝗈𝗇𝗏𝖾𝗋𝗍 𝗍𝖾𝗑𝗍 𝗂𝗇𝗍𝗈 𝖺 "𝗐𝖾𝖾𝖻𝗂𝖿𝗂𝖾𝖽" 𝖿𝗈𝗇𝗍.
 
- **𝖳𝗋𝗎𝗍𝗁:**
  ✧ `/𝗍𝗋𝗎𝗍𝗁` **:** 𝖦𝖾𝗍 𝖺 𝗋𝖺𝗇𝖽𝗈𝗆 𝗍𝗋𝗎𝗍𝗁 𝗊𝗎𝖾𝗌𝗍𝗂𝗈𝗇.
- **𝖣𝖺𝗋𝖾:**
  ✧ `/𝖽𝖺𝗋𝖾` **:** 𝖦𝖾𝗍 𝖺 𝗋𝖺𝗇𝖽𝗈𝗆 𝖽𝖺𝗋𝖾 𝗊𝗎𝖾𝗌𝗍𝗂𝗈𝗇.
"""
