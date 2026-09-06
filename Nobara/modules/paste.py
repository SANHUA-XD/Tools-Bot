import os
import re

from httpx import AsyncClient
from telegraph import Telegraph
from pyrogram import filters
from pyrogram.types import Message

from Nobara import app

# Initialize Telegraph
telegraph = Telegraph()
telegraph.create_account(short_name="bot")


# Pastebins
class PasteBins:
    def __init__(self) -> None:
        # API Urls
        self.nekobin_api = "https://nekobin.com/api/documents"
        # Paste Urls
        self.nekobin = "https://nekobin.com"
    
    async def paste_text(self, paste_bin, text, user_data=None):
        if paste_bin == "telegraph":
            return self.paste_to_telegraph(text, user_data)
        elif paste_bin == "nekobin":
            return await self.paste_to_nekobin(text)
        else:
            return "`Invalid pastebin service selected!`"
    
    async def __check_status(self, resp_status, status_code: int = 201):
        if int(resp_status) != status_code:
            return "real shit"
        else:
            return "ok"

    async def paste_to_nekobin(self, text):
        async with AsyncClient() as nekoc:
            resp = await nekoc.post(self.nekobin_api, json={"content": str(text)})
            chck = await self.__check_status(resp.status_code)
            if not chck == "ok":
                return None
            else:
                jsned = resp.json()
                return f"{self.nekobin}/{jsned['result']['key']}"
    
    def paste_to_telegraph(self, text, user_data):
        first_name = user_data.get("first_name", "Unknown")
        username = user_data.get("username", None)
        title = f"Pasted by {first_name}"
        if username:
            title += f" (@{username})"
        try:
            response = telegraph.create_page(
                title=title,
                html_content=f"<pre>{text}</pre>"
            )
            return f"https://telegra.ph/{response['path']}"
        except Exception as e:
            return None


async def get_pastebin_service(text: str):
    if re.search(r'\btgt\b', text):
        pastebin = "telegraph"
    elif re.search(r'\bnekobin\b', text):
        pastebin = "nekobin"
    else:
        pastebin = "telegraph"
    return pastebin


def get_arg(message):
    msg = message.text
    msg = msg.replace(" ", "", 1) if msg[1] == " " else msg
    split = msg[1:].replace("\n", " \n").split(" ")
    if " ".join(split[1:]).strip() == "":
        return ""
    return " ".join(split[1:])


@app.on_message(filters.command(["paste", "nekobin"]))
async def paste_dis_text(_, message: Message):
    pstbin_serv = await get_pastebin_service(message.text.split(" ")[0])
    replied_msg = message.reply_to_message
    tex_t = get_arg(message)
    message_s = tex_t
    if not tex_t:
        if not replied_msg:
            return await message.reply("`𝖱𝖾𝗉𝗅𝗒 𝗍𝗈 𝖺 𝖿𝗂𝗅𝖾 𝗈𝗋 𝗌𝖾𝗇𝖽 𝗍𝗁𝗂𝗌 𝖼𝗈𝗆𝗆𝖺𝗇𝖽 𝗐𝗂𝗍𝗁 𝗍𝖾𝗑𝗍!`")
        if not replied_msg.text:
            file = await replied_msg.download()
            m_list = open(file, "r").read()
            message_s = m_list
            os.remove(file)
        elif replied_msg.text:
            message_s = replied_msg.text
    paste_cls = PasteBins()
    user_data = {
        "first_name": message.from_user.first_name,
        "username": message.from_user.username,
    }
    paste_msg = await message.reply(f"`𝖯𝖺𝗌𝗍𝗂𝗇𝗀 𝗍𝗈 {pstbin_serv.capitalize()}...`")
    pasted = await paste_cls.paste_text(pstbin_serv, message_s, user_data=user_data)
    if not pasted:
        return await paste_msg.reply("`𝖮𝗈𝗉𝗌, 𝗉𝖺𝗌𝗍𝗂𝗇𝗀 𝖿𝖺𝗂𝗅𝖾𝖽! 𝖯𝗅𝖾𝖺𝗌𝖾 𝗍𝗋𝗒 𝖼𝗁𝖺𝗇𝗀𝗂𝗇𝗀 𝗍𝗁𝖾 𝗉𝖺𝗌𝗍𝖾𝖻𝗂𝗇 𝗌𝖾𝗋𝗏𝗂𝖼𝖾!`")
    await paste_msg.edit(f"**𝖯𝖺𝗌𝗍𝖾𝖽 𝗍𝗈 {pstbin_serv.capitalize()}!** \n\n**𝖴𝗋𝗅:** {pasted}", disable_web_page_preview=True)

__module__ = "𝖯𝖺𝗌𝗍𝖾"


__help__ = """**𝖴𝗌𝖾𝗋 𝖢𝗈𝗆𝗆𝖺𝗇𝖽𝗌:**
  ✧ `/𝗉𝖺𝗌𝗍𝖾 <𝗍𝖾𝗑𝗍>` **:** 𝖯𝖺𝗌𝗍𝖾𝗌 𝗍𝗁𝖾 𝗉𝗋𝗈𝗏𝗂𝖽𝖾𝖽 𝗍𝖾𝗑𝗍 𝗍𝗈 𝖭𝖾𝗄𝗈𝖻𝗂𝗇 (𝖽𝖾𝖿𝖺𝗎𝗅𝗍 𝗌𝖾𝗋𝗏𝗂𝖼𝖾).
   ✧ `/𝗇𝖾𝗄𝗈𝖻𝗂𝗇 <𝗍𝖾𝗑𝗍>` **:** 𝖯𝖺𝗌𝗍𝖾𝗌 𝗍𝗁𝖾 𝗉𝗋𝗈𝗏𝗂𝖽𝖾𝖽 𝗍𝖾𝗑𝗍 𝗍𝗈 𝖭𝖾𝗄𝗈𝖻𝗂𝗇.
   ✧ `/𝗍𝗀𝗍 <𝗍𝖾𝗑𝗍>` **:** 𝖢𝗋𝖾𝖺𝗍𝖾𝗌 𝖺 𝖳𝖾𝗅𝖾𝗀𝗋𝖺𝗉𝗁 𝗉𝖺𝗀𝖾 𝗐𝗂𝗍𝗁 𝗍𝗁𝖾 𝗉𝗋𝗈𝗏𝗂𝖽𝖾𝖽 𝗍𝖾𝗑𝗍.
 
**𝖴𝗌𝖺𝗀𝖾 𝗐𝗂𝗍𝗁 𝖱𝖾𝗉𝗅𝗂𝖾𝗌:**
  ✧ 𝖱𝖾𝗉𝗅𝗒 𝗍𝗈 𝖺 𝗆𝖾𝗌𝗌𝖺𝗀𝖾 𝗈𝗋 𝖿𝗂𝗅𝖾 𝗐𝗂𝗍𝗁 `/𝗉𝖺𝗌𝗍𝖾`, `/𝗇𝖾𝗄𝗈𝖻𝗂𝗇`, 𝗈𝗋 `/𝗍𝗀𝗍` 𝗍𝗈 𝗉𝖺𝗌𝗍𝖾 𝗍𝗁𝖾 𝖼𝗈𝗇𝗍𝖾𝗇𝗍.
 
**𝖤𝗑𝖺𝗆𝗉𝗅𝖾𝗌:**
  ✧ `/𝗉𝖺𝗌𝗍𝖾 𝖳𝗁𝗂𝗌 𝗂𝗌 𝖺 𝗌𝖺𝗆𝗉𝗅𝖾 𝗍𝖾𝗑𝗍.`
  ✧ `/𝗇𝖾𝗄𝗈𝖻𝗂𝗇 𝖠𝗇𝗈𝗍𝗁𝖾𝗋 𝖾𝗑𝖺𝗆𝗉𝗅𝖾.`
  ✧ `/𝗍𝗀𝗍 𝖠 𝗍𝖾𝗑𝗍 𝖿𝗈𝗋 𝖳𝖾𝗅𝖾𝗀𝗋𝖺𝗉𝗁.`
"""