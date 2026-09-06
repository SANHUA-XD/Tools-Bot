import os
import cv2
from PIL import Image
from pyrogram import filters
from Nobara import app
from config import config
from Nobara.decorator.save import save 
from Nobara.decorator.errors import error

@app.on_message(filters.command("tiny" , prefixes=config.COMMAND_PREFIXES) & filters.reply)
@error
@save
async def tiny_command(client, message):
    reply = message.reply_to_message

    if not reply.media:
        await message.reply("`𝖯𝗅𝖾𝖺𝗌𝖾 𝗋𝖾𝗉𝗅𝗒 𝗍𝗈 𝖺 𝗌𝗍𝗂𝖼𝗄𝖾𝗋, 𝗂𝗆𝖺𝗀𝖾, 𝗈𝗋 𝗏𝗂𝖽𝖾𝗈.`")
        return

    processing_message = await message.reply("`Processing tiny...`")
    file_path = await client.download_media(reply)

    # Previously this loaded "Nobara/resources/transparent.png" from disk,
    # but that binary asset kept getting corrupted when zipping/uploading
    # through Telegram to GitHub. A blank 512x512 transparent canvas is
    # trivial to generate in-memory, so there's no need to depend on a
    # binary file surviving that pipeline at all anymore.
    im1 = Image.new("RGBA", (512, 512), (0, 0, 0, 0))

    try:
        # Determine file extension
        _, file_extension = os.path.splitext(file_path)
        file_extension = file_extension.lower()

        # Set output file name dynamically
        output_file = f"result{file_extension}"

        if file_extension == ".tgs":
            os.system(f"lottie_convert.py {file_path} json.json")
            with open("json.json", "r") as json_file:
                json_data = json_file.read()
            json_data = json_data.replace("512", "2000")
            with open("json.json", "w") as json_file:
                json_file.write(json_data)
            os.system("lottie_convert.py json.json result.tgs")
            output_file = "result.tgs"
            os.remove("json.json")
        elif file_extension in [".gif", ".mp4"]:
            cap = cv2.VideoCapture(file_path)
            ret, frame = cap.read()
            if ret:
                cv2.imwrite("frame.png", frame)
            cap.release()
            image_file = "frame.png"
        else:
            image_file = file_path

        # Resize image (preserving aspect ratio - no distortion) to fit
        # inside a 300x300 box, then center it on the 512x512 canvas.
        # Previously the resize used a formula that could go negative for
        # extreme aspect ratios (very tall/wide images) and didn't preserve
        # proportions, and the paste position was hardcoded to (150, 0)
        # regardless of the resized image's actual size - both together are
        # why the sticker's position/framing looked broken for some photos.
        im = Image.open(image_file).convert("RGBA")
        width, height = im.size

        max_dim = 300
        if width >= height:
            new_width = max_dim
            new_height = max(1, round(height * (max_dim / width)))
        else:
            new_height = max_dim
            new_width = max(1, round(width * (max_dim / height)))

        resized_image = im.resize((new_width, new_height), Image.LANCZOS)

        back_im = im1.copy()
        paste_x = (back_im.width - new_width) // 2
        paste_y = (back_im.height - new_height) // 2
        back_im.paste(resized_image, (paste_x, paste_y), resized_image)
        output_file = "result.webp"
        back_im.save(output_file, "WEBP", quality=95)

        # Send the processed file
        await client.send_document(
            chat_id=message.chat.id,
            document=output_file,
            reply_to_message_id=reply.id
        )
    finally:
        # Cleanup temporary files
        os.remove(file_path)
        if os.path.exists("frame.png"):
            os.remove("frame.png")
        if os.path.exists("resized.png"):
            os.remove("resized.png")
        if os.path.exists("result.webp"):
            os.remove("result.webp")
        if os.path.exists("result.tgs"):
            os.remove("result.tgs")

    await processing_message.delete()


__module__ = "𝖳𝗂𝗇𝗒"


__help__ = """ ✧ `/tiny` (𝗋𝖾𝗉𝗅𝗒 𝗍𝗈 𝖺 𝗌𝗍𝗂𝖼𝗄𝖾𝗋 , 𝗏𝗂𝖽𝖾𝗈 𝗈𝗋 𝗂𝗆𝖺𝗀𝖾) *:* 𝖢𝗈𝗇𝗏𝖾𝗋𝗍𝗌 𝖳𝗁𝖺𝗍 𝖲𝗍𝗂𝖼𝗄𝖾𝗋 , 𝖵𝗂𝖽𝖾𝗈 𝖮𝗋 𝖨𝗆𝖺𝗀𝖾 𝖳𝗈 𝖳𝗂𝗇𝗒 𝖲𝗂𝗓𝖾.
 """