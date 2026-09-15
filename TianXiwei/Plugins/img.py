from pyrogram import filters
import requests
import re
import json
import urllib.parse
from TianXiwei import app
from pyrogram.enums import ParseMode
from pyrogram.types import InputMediaPhoto, Message
from config import config 
from TianXiwei.Extra.save import save
from TianXiwei.Extra.errors import error

def get_pinterest_images(query, limit=8):
    try:
        res = requests.get(f"https://in.pinterest.com/search/pins/?q={urllib.parse.quote(query)}")
        html = res.text
        match = re.search(r'<script id="__PWS_DATA__" type="application/json">(.*?)</script>', html, re.DOTALL)
        images = []
        if match:
            data = json.loads(match.group(1))
            try:
                pins = data['props']['initialReduxState']['pins']
                for pin_id, pin_data in pins.items():
                    if "images" in pin_data and "orig" in pin_data["images"]:
                        images.append(pin_data["images"]["orig"]["url"])
                    if len(images) >= limit:
                        break
            except KeyError:
                pass


        if not images:
            fallback = re.findall(r'https://i\.pinimg\.com/originals/[0-9a-f]+/[0-9a-f]+/[0-9a-f]+/[0-9a-f]+\.jpg', html)
            if not fallback:
                fallback = re.findall(r'https://i\.pinimg\.com/736x/[0-9a-f]+/[0-9a-f]+/[0-9a-f]+/[0-9a-f]+\.jpg', html)
            images = list(set(fallback))[:limit]

        return images
    except Exception as e:
        print(f"Pinterest Search Error: {e}")
        return []


@app.on_message(filters.command("img", prefixes=config.COMMAND_PREFIXES))
@error
@save
async def download_images(client, message: Message):
    if len(message.command) < 2:
        await message.reply("𝖴𝗌𝖺𝗀𝖾: `/𝗂𝗆𝗀 <𝗊𝗎𝖾𝗋𝗒>`\n𝖤𝗑𝖺𝗆𝗉𝗅𝖾: `/𝗂𝗆𝗀 𝖼𝖺𝗍𝗌`", parse_mode=ParseMode.MARKDOWN)
        return
    
    query = " ".join(message.command[1:])
    limit = 8

    a = await message.reply_text("🔎")
    

    try:
        images = get_pinterest_images(query, limit)

        if images:
            media_group = [
                InputMediaPhoto(media=img_url) for img_url in images
            ]


            await a.delete()
            
            try:
                await message.reply_media_group(media=media_group)
            except Exception as e:
                if "topics" not in str(e):
                    raise e
        else:
            await a.edit_text("𝖭𝗈 𝗂𝗆𝖺𝗀𝖾𝗌 𝗐𝖾𝗋𝖾 𝖿𝗈𝗎𝗇𝖽 𝗍𝗈 𝗌𝖾𝗇𝖽.")

    except Exception as e:
        await message.reply(f"𝖠𝗇 𝖾𝗋𝗋𝗈𝗋 𝗈𝖼𝖼𝗎𝗋𝗋𝖾𝖽 : {e}")

__module__ = "𝖨𝗆𝖺𝗀𝖾"

__help__ = """**𝖴𝗌𝖾𝗋 𝖢𝗈𝗆𝗆𝖺𝗇𝖽𝗌:**
  ✧ `/𝗂𝗆𝗀` (𝗊𝗎𝖾𝗋𝗒) **:** 𝖣𝗈𝗐𝗇𝗅𝗈𝖺𝖽𝗌 𝖺𝗇𝖽 𝗌𝖾𝗇𝖽𝗌 𝗂𝗆𝖺𝗀𝖾𝗌 𝖿𝗋𝗈𝗆 𝖡𝗂𝗇𝗀 𝖿𝗈𝗋 𝗍𝗁𝖾 𝗀𝗂𝗏𝖾𝗇 𝗊𝗎𝖾𝗋𝗒.
 
*𝖤𝗑𝖺𝗆𝗉𝗅𝖾𝗌:*
  ✧ `/𝗂𝗆𝗀 𝖼𝖺𝗍𝗌` **:** 𝖥𝖾𝗍𝖼𝗁𝖾𝗌 𝗂𝗆𝖺𝗀𝖾𝗌 𝗈𝖿 𝖼𝖺𝗍𝗌.
   ✧ `/𝗂𝗆𝗀 𝗌𝗎𝗇𝗌𝖾𝗍` **:** 𝖥𝖾𝗍𝖼𝗁𝖾𝗌 𝗂𝗆𝖺𝗀𝖾𝗌 𝗈𝖿 𝗌𝗎𝗇𝗌𝖾𝗍𝗌.
 """
