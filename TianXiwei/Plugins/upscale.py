import os
from pyrogram import filters
from TianXiwei import app
from TianXiwei.Functions.upscale_helper import getFile, UpscaleImages
from config import config 
from TianXiwei.Extra.save import save
from TianXiwei.Extra.errors import error

@app.on_message(filters.command(["upscale", "enhance"], prefixes=config.COMMAND_PREFIXES))
@error
@save
async def upscaleImages(_, message):

    file = await getFile(message)
    if file is None:
        return await message.reply_text("𝖱𝖾𝗉𝗅𝗒 𝗍𝗈 𝖺𝗇 𝗂𝗆𝖺𝗀𝖾 𝗍𝗈 𝗎𝗉𝗌𝖼𝖺𝗅𝖾 𝗂𝗍.")
    
    msg = await message.reply("𝖴𝗉𝗌𝖼𝖺𝗅𝗂𝗇𝗀 𝗒𝗈𝗎𝗋 𝗂𝗆𝖺𝗀𝖾...")
    
    try:

        upscaledImage = await UpscaleImages(file)
        
        if upscaledImage:

            await message.reply_document(document=upscaledImage, caption="ɪᴍᴀɢᴇ ᴜᴘꜱᴄᴀʟᴇᴅ ꜱᴜᴄᴄᴇꜱꜰᴜʟʟʏ")
            await msg.delete()
            

            if os.path.exists(upscaledImage):
                os.remove(upscaledImage)
        else:
            await msg.edit("𝖥𝖺𝗂𝗅𝖾𝖽 𝗍𝗈 𝗎𝗉𝗌𝖼𝖺𝗅𝖾 𝗍𝗁𝖾 𝗂𝗆𝖺𝗀𝖾. 𝖯𝗅𝖾𝖺𝗌𝖾 𝗍𝗋𝗒 𝖺𝗀𝖺𝗂𝗇.")
            
    except Exception as e:
        await msg.edit(f"𝖥𝖺𝗂𝗅𝖾𝖽 𝗍𝗈 𝗎𝗉𝗌𝖼𝖺𝗅𝖾 𝗍𝗁𝖾 𝗂𝗆𝖺𝗀𝖾: {e}")
    finally:

        if file and os.path.exists(file):
            os.remove(file)

__module__ = "𝖴𝗉𝗌𝖼𝖺𝗅𝖾"


__help__ = """- **𝖢𝗈𝗆𝗆𝖺𝗇𝖽**:***
  ✧ `/upscale or /enhance <reply>` **:** 𝖱𝖾𝗉𝗅𝗒 𝖳𝗈 𝖠𝗇 𝖨𝗆𝖺𝗀𝖾 𝖶𝗂𝗍𝗁 𝖳𝗁𝗂𝗌 𝖢𝗆𝖽 𝖳𝗈 𝖤𝗇𝗁𝖺𝗇𝖼𝖾.
 """
