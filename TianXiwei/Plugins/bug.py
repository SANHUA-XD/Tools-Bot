from pyrogram import filters
from pyrogram.enums import ParseMode
from TianXiwei import app
from config import config 


@app.on_message(filters.command("bug", prefixes=config.COMMAND_PREFIXES))
async def bug_command_handler(client, message):

    if message.reply_to_message:

        replied_message = message.reply_to_message


        content = replied_message.text or replied_message.caption


        media_type = (
            "**Media content included**"
            if replied_message.photo
            or replied_message.document
            or replied_message.video
            or replied_message.audio
            or replied_message.animation
            else "**No media content included**"
        )


        if message.from_user.username :
            
            report_message = f"**Bug reported by @{message.from_user.username}:**\n\n{content}\n\n{media_type}\n\n**Message Link:** {replied_message.link}"
        else :
            report_message = f"**Bug reported by {message.from_user.mention}:**\n\n{content}\n\n{media_type}\n\n**Message Link:** {replied_message.link}"

        await client.send_message(config.LOG_CHANNEL, report_message, parse_mode=ParseMode.MARKDOWN
        )
    else:

        await client.send_message(
            message.chat.id,
            "To report a bug, please reply to the message with **/ bug** cmd.",
            parse_mode=ParseMode.MARKDOWN,
        )