import requests
import asyncio
from httpx import AsyncClient
from telegraph import Telegraph
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from Nobara import app
from config import config

# Separate Telegraph account just for this module (Nobara/modules/paste.py
# already creates its own account/instance for /paste, /nekobin - kept
# independent here so the two modules don't share mutable state).
telegraph = Telegraph()
telegraph.create_account(short_name="TgtUploaderBot")


class Upload:
    def __init__(self):
        # ImgBB API URL
        self.imgbb_url = "https://api.imgbb.com/1/upload"

        # config.py তে IMGBB_API_KEY থাকলে সেটি নেবে
        self.imgbb_api_key = getattr(config, "IMGBB_API_KEY", "")

    def upload_to_imgbb(self, file_bytes):
        payload = {
            "key": self.imgbb_api_key
        }
        # মেমরি (RAM) থেকে সরাসরি ছবি পাঠানো হচ্ছে
        files = {
            "image": ("image.jpg", file_bytes, "image/jpeg")
        }
        response = requests.post(self.imgbb_url, data=payload, files=files, timeout=30)

        if response.status_code == 200:
            data = response.json()
            return data["data"]["url"]
        else:
            raise Exception(f"Failed to upload file. Status code: {response.status_code}, Response: {response.text}")

    async def upload_text(self, content, title):
        """
        Uploads text using Telegraph first (proven reliable, already used
        elsewhere in this codebase - see Nobara/modules/paste.py), falling
        back to Nekobin if Telegraph is ever unreachable.

        Previously this only tried spaceb.in (an unofficial third-party
        Spacebin instance whose API endpoint isn't reliably reachable) and
        then Nekobin - which is why /tgt kept failing with
        "All Pastebin APIs failed."
        """
        try:
            response = await asyncio.to_thread(
                telegraph.create_page, title=title, html_content=f"<pre>{content}</pre>"
            )
            return f"https://telegra.ph/{response['path']}"
        except Exception:
            pass

        try:
            async with AsyncClient(timeout=10) as client:
                response = await client.post("https://nekobin.com/api/documents", json={"content": content})
                if response.status_code in (200, 201):
                    return f"https://nekobin.com/{response.json()['result']['key']}"
        except Exception:
            pass

        raise Exception("Both Telegraph and Nekobin failed. Please try again later.")


uploader = Upload()

# /tgm command: Reply to an image and upload to ImgBB
@app.on_message(filters.command("tgm", prefixes=config.COMMAND_PREFIXES))
async def upload_to_imgbb_cmd(client: Client, message: Message):
    if not message.reply_to_message or not (message.reply_to_message.photo or message.reply_to_message.document or message.reply_to_message.animation):
        await message.reply("𝖯𝗅𝖾𝖺𝗌𝖾 𝗋𝖾𝗉𝗅𝗒 𝗍𝗈 𝖺𝗇 𝗂𝗆𝖺𝗀𝖾 𝗈𝗋 𝖦𝖨𝖥.")
        return

    if not uploader.imgbb_api_key:
        await message.reply(
            "❌ **𝖨𝗆𝗀𝖡𝖡 𝖠𝖯𝖨 𝗄𝖾𝗒 𝗂𝗌 𝗇𝗈𝗍 𝗌𝖾𝗍.**\n"
            "𝖠𝖽𝖽 `IMGBB_API_KEY` 𝗂𝗇 `config.py` (𝗀𝖾𝗍 𝖺 𝖿𝗋𝖾𝖾 𝗈𝗇𝖾 𝖺𝗍 https://api.imgbb.com/)."
        )
        return

    a = await message.reply_text("𝖣𝗈𝗐𝗇𝗅𝗈𝖺𝖽𝗂𝗇𝗀 𝖳𝗁𝖾 𝖥𝗂𝗅𝖾...")

    try:
        # in_memory=True ব্যবহার করা হয়েছে যাতে .temp এরর না দেয় এবং সার্ভারের স্টোরেজ বাঁচে
        file_obj = await message.reply_to_message.download(in_memory=True)
        if not file_obj:
            await a.edit_text("𝖥𝖺𝗂𝗅𝖾𝖽 𝗍𝗈 𝖽𝗈𝗐𝗇𝗅𝗈𝖺𝖽 𝗍𝗁𝖾 𝖿𝗂𝗅𝖾.")
            return

        file_bytes = file_obj.getvalue()

        await a.edit_text("𝖳𝗋𝗒𝗂𝗇𝗀 𝖳𝗈 𝖴𝗉𝗅𝗈𝖺𝖽 𝖳𝗈 𝖨𝗆𝗀𝖡𝖡....")

        # Asyncio.to_thread দিয়ে আপলোড যাতে বট ফ্রিজ না হয়
        imgbb_link = await asyncio.to_thread(uploader.upload_to_imgbb, file_bytes)
        share_url = f"https://telegram.me/share/url?url={imgbb_link}"

        buttons = InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔗 𝖲𝗁𝖺𝗋𝖾 𝖫𝗂𝗇𝗄", url=share_url)]]
        )

        # Tap to copy এর জন্য লিংকটি ` ` এর ভেতরে দেওয়া হয়েছে
        text = f"**𝖥𝗂𝗅𝖾 𝗎𝗉𝗅𝗈𝖺𝖽𝖾𝖽 𝗌𝗎𝖼𝖼𝖾𝗌𝗌𝖿𝗎𝗅𝗅𝗒!**\n\n**📥 𝖳𝖺𝗉 𝖳𝗈 𝖢𝗈𝗉𝗒 𝖫𝗂𝗇𝗄:**\n`{imgbb_link}`"

        await a.edit_text(text, disable_web_page_preview=True, reply_markup=buttons)

    except Exception as e:
        await a.edit_text(f"𝖥𝖺𝗂𝗅𝖾𝖽 𝗍𝗈 𝗎𝗉𝗅𝗈𝖺𝖽: {str(e)}\n\n*(Check your ImgBB API Key in config)*")


# /tgt command: Reply to a text and upload it (Telegraph, Nekobin fallback)
@app.on_message(filters.command("tgt", prefixes=config.COMMAND_PREFIXES))
async def upload_to_pastebin_cmd(client: Client, message: Message):
    if message.reply_to_message and message.reply_to_message.text:
        content = message.reply_to_message.text
    elif len(message.command) > 1:
        content = message.text.split(" ", 1)[1]
    else:
        await message.reply("𝖯𝗅𝖾𝖺𝗌𝖾 𝗉𝗋𝗈𝗏𝗂𝖽𝖾 𝗈𝗋 𝗋𝖾𝗉𝗅𝗒 𝗍𝗈 𝖺 𝗍𝖾𝗑𝗍.")
        return

    a = await message.reply_text("𝖳𝗋𝗒𝗂𝗇𝗀 𝖳𝗈 𝖴𝗉𝗅𝗈𝖺𝖽 𝖳𝖾𝗑𝗍...")

    try:
        title = f"Uploaded by {message.from_user.first_name}" if message.from_user else "Uploaded text"
        link = await uploader.upload_text(content, title)
        share_url = f"https://telegram.me/share/url?url={link}"

        buttons = InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔗 𝖲𝗁𝖺𝗋𝖾 𝖫𝗂𝗇𝗄", url=share_url)]]
        )

        # Tap to copy এর জন্য লিংকটি ` ` এর ভেতরে দেওয়া হয়েছে
        text = f"**𝖳𝖾𝗑𝗍 𝗎𝗉𝗅𝗈𝖺𝖽𝖾𝖽 𝗌𝗎𝖼𝖼𝖾𝗌𝗌𝖿𝗎𝗅𝗅𝗒!**\n\n**📥 𝖳𝖺𝗉 𝖳𝗈 𝖢𝗈𝗉𝗒 𝖫𝗂𝗇𝗄:**\n`{link}`"

        await a.edit_text(text, disable_web_page_preview=True, reply_markup=buttons)

    except Exception as e:
        await a.edit_text(f"𝖥𝖺𝗂𝗅𝖾𝖽 𝗍𝗈 𝗎𝗉𝗅𝗈𝖺𝖽 𝗍𝖾𝗑𝗍 : {str(e)}")


__module__ = "𝖴𝗉𝗅𝗈𝖺𝖽𝖾𝗋"

__help__ = """**𝖴𝗉𝗅𝗈𝖺𝖽𝖾𝗋 𝖡𝗈𝗍 𝖥𝖾𝖺𝗍𝗎𝗋𝖾𝗌:**

- **𝖢𝗈𝗆𝗆𝖺𝗇𝖽𝗌:**

 ✧ `/𝗍𝗀𝗆` : 𝖱𝖾𝗉𝗅𝗒 𝗍𝗈 𝖺𝗇 𝗂𝗆𝖺𝗀𝖾, 𝖺𝗇𝖽 𝗍𝗁𝖾 𝖻𝗈𝗍 𝗐𝗂𝗅𝗅 𝗎𝗉𝗅𝗈𝖺𝖽 𝗂𝗍 𝗍𝗈 𝖨𝗆𝗀𝖡𝖡 𝖺𝗇𝖽 𝗉𝗋𝗈𝗏𝗂𝖽𝖾 𝖺 𝗌𝗁𝖺𝗋𝖺𝖻𝗅𝖾 𝗅𝗂𝗇𝗄.
 
 ✧ `/𝗍𝗀𝗍` : 𝖯𝗋𝗈𝗏𝗂𝖽𝖾 𝗈𝗋 𝗋𝖾𝗉𝗅𝗒 𝗍𝗈 𝖺 𝗍𝖾𝗑𝗍 𝗆𝖾𝗌𝗌𝖺𝗀𝖾, 𝖺𝗇𝖽 𝗍𝗁𝖾 𝖻𝗈𝗍 𝗐𝗂𝗅𝗅 𝗎𝗉𝗅𝗈𝖺𝖽 𝗂𝗍 𝗍𝗈 𝖳𝖾𝗅𝖾𝗀𝗋𝖺𝗉𝗁 (𝖭𝖾𝗄𝗈𝖻𝗂𝗇 𝖺𝗌 𝖻𝖺𝖼𝗄𝗎𝗉) 𝖺𝗇𝖽 𝗉𝗋𝗈𝗏𝗂𝖽𝖾 𝖺 𝗌𝗁𝖺𝗋𝖺𝖻𝗅𝖾 𝗅𝗂𝗇𝗄.
 
- **𝖴𝗌𝖺𝗀𝖾:**

   𝟣. **𝖨𝗆𝖺𝗀𝖾 𝖴𝗉𝗅𝗈𝖺𝖽:**
      - 𝖱𝖾𝗉𝗅𝗒 𝗍𝗈 𝖺𝗇 𝗂𝗆𝖺𝗀𝖾 𝗎𝗌𝗂𝗇𝗀 𝗍𝗁𝖾 `/𝗍𝗀𝗆` 𝖼𝗈𝗆𝗆𝖺𝗇𝖽.
       - 𝖳𝗁𝖾 𝖻𝗈𝗍 𝖽𝗈𝗐𝗇𝗅𝗈𝖺𝖽𝗌 𝗍𝗁𝖾 𝗂𝗆𝖺𝗀𝖾 𝖺𝗇𝖽 𝗎𝗉𝗅𝗈𝖺𝖽𝗌 𝗂𝗍 𝗍𝗈 𝗍𝗁𝖾 𝖨𝗆𝗀𝖡𝖡 𝖠𝖯𝖨.
       - 𝖠 𝗅𝗂𝗇𝗄 𝗍𝗈 𝗍𝗁𝖾 𝗎𝗉𝗅𝗈𝖺𝖽𝖾𝖽 𝗂𝗆𝖺𝗀𝖾 𝗂𝗌 𝗋𝖾𝗍𝗎𝗋𝗇𝖾𝖽 𝖺𝗅𝗈𝗇𝗀 𝗐𝗂𝗍𝗁 𝖺 𝗌𝗁𝖺𝗋𝖾 𝖻𝗎𝗍𝗍𝗈𝗇.
 
   𝟤. **𝖳𝖾𝗑𝗍 𝖴𝗉𝗅𝗈𝖺𝖽:**
      - 𝖴𝗌𝖾 `/𝗍𝗀𝗍 <𝗍𝖾𝗑𝗍>` 𝗈𝗋 𝗋𝖾𝗉𝗅𝗒 𝗍𝗈 𝖺 𝗍𝖾𝗑𝗍 𝗆𝖾𝗌𝗌𝖺𝗀𝖾 𝗐𝗂𝗍𝗁 `/𝗍𝗀𝗍`.
       - 𝖳𝗁𝖾 𝖻𝗈𝗍 𝗎𝗉𝗅𝗈𝖺𝖽𝗌 𝗍𝗁𝖾 𝗉𝗋𝗈𝗏𝗂𝖽𝖾𝖽 𝗍𝖾𝗑𝗍 𝗍𝗈 𝖳𝖾𝗅𝖾𝗀𝗋𝖺𝗉𝗁 (𝖿𝖺𝗅𝗅𝗌 𝖻𝖺𝖼𝗄 𝗍𝗈 𝖭𝖾𝗄𝗈𝖻𝗂𝗇 𝗂𝖿 𝗇𝖾𝖾𝖽𝖾𝖽).
       - 𝖠 𝗅𝗂𝗇𝗄 𝗂𝗌 𝗋𝖾𝗍𝗎𝗋𝗇𝖾𝖽 𝖺𝗅𝗈𝗇𝗀 𝗐𝗂𝗍𝗁 𝖺 𝗌𝗁𝖺𝗋𝖾 𝖻𝗎𝗍𝗍𝗈𝗇.
 """
