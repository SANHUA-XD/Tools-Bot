from pyrogram import Client, filters
from pyrogram.types import Message
from config import config 
from TianXiwei import app
from TianXiwei.Extra.botadmin import botadmin

@app.on_message(filters.command("snipe" , config.COMMAND_PREFIXES))
@botadmin
async def snipe_message(client: Client, message: Message):
    try:
        args = message.text.split(maxsplit=2)
        
        if len(args) < 2:
            await message.reply_text("Usage: `/snipe <chat_id> <text>` or reply to a message and use `/snipe <chat_id>`.", quote=True)
            return

        chat_id = args[1]  
        

        if message.reply_to_message:
            await message.reply_to_message.copy(chat_id=chat_id)
            await message.reply_text(f"Replied message sent to {chat_id}.", quote=True)
        else:

            if len(args) < 3:
                await message.reply_text("Please provide a message text to send.", quote=True)
                return
            
            text = args[2]
            await client.send_message(chat_id=chat_id, text=text)
            await message.reply_text(f"Message sent to {chat_id}.", quote=True)
    except Exception as e:
        await message.reply_text(f"An error occurred: {e}", quote=True)

