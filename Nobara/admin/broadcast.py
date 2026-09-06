import asyncio
from pyrogram import filters , Client
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton , Message
from pyrogram.errors import FloodWait 
from Nobara import app
from Nobara.database import total_chats, total_users
from config import config

cancel_broadcast = False


async def broadcast_message(client : Client, message : Message , groups, users, pin_message=False, target='all'):
    global cancel_broadcast
    user_count, group_count = 0, 0

    if target in ('all', 'chat'):
        for group_id in groups:
            if cancel_broadcast:
                break
            try:
                sent_message = await message.forward(group_id)
                if pin_message:
                    await client.pin_chat_message(group_id, sent_message.id, disable_notification=False)
                group_count += 1
                await asyncio.sleep(1.5)
            except FloodWait as e:
                await asyncio.sleep(e.value)
            except Exception :
                pass

    if target in ('all', 'user'):
        for user_id in users:
            if cancel_broadcast:
                break
            try:
                await message.forward(user_id)
                user_count += 1
                await asyncio.sleep(1.5)
            except FloodWait as e:
                await asyncio.sleep(e.value)
            except Exception :
                pass

    return user_count, group_count


async def cancel_broadcast_callback(client, query):
    global cancel_broadcast
    if query.from_user.id != config.OWNER_ID:
        await query.answer("𝖸𝗈𝗎 𝖽𝗈 𝗇𝗈𝗍 𝗁𝖺𝗏𝖾 𝗉𝖾𝗋𝗆𝗂𝗌𝗌𝗂𝗈𝗇 𝗍𝗈 𝖼𝖺𝗇𝖼𝖾𝗅 𝗍𝗁𝖾 𝖻𝗋𝗈𝖺𝖽𝖼𝖺𝗌𝗍.", show_alert=True)
        return

    cancel_broadcast = True
    await query.message.edit_text("𝖳𝗁𝖾 𝖡𝗋𝗈𝖺𝖽𝖼𝖺𝗌𝗍 𝗁𝖺𝗌 𝖻𝖾𝖾𝗇 𝖼𝖺𝗇𝖼𝖾𝗅𝖾𝖽.")
    await query.answer("𝖡𝗋𝗈𝖺𝖽𝖼𝖺𝗌𝗍 𝖼𝖺𝗇𝖼𝖾𝗅𝗅𝖾𝖽.", show_alert=True)


@app.on_message(filters.command("ycast") & filters.user(config.OWNER_ID) & filters.reply)
@app.on_message(filters.regex(r"(?i)^Frieren Bcast$") & filters.user(config.OWNER_ID) & filters.reply)
async def start_broadcast(client: Client, message: Message):
    global cancel_broadcast
    cancel_broadcast = False

    # Extract command arguments from message text
    if message.command:
        command_args = message.command[1:]  # Skip the command itself
    else:
        # If triggered by regex, split the message text to simulate command arguments
        command_args = message.text.split()[1:]

    target = 'all'
    pin_message = False

    if '-user' in command_args:
        target = 'user'
    elif '-chat' in command_args:
        target = 'chat'

    if '-pin' in command_args:
        pin_message = True

    # Get groups and users from the database
    groups = [chat["chat_id"] for chat in await total_chats.find().to_list(None)]
    users = [user["user_id"] for user in await total_users.find().to_list(None)]

    # Send broadcast start message with cancel button
    cancel_button = InlineKeyboardMarkup([[InlineKeyboardButton("𝖢𝖺𝗇𝖼𝖾𝗅 𝖡𝗋𝗈𝖺𝖽𝖼𝖺𝗌𝗍", callback_data="cancel_broadcast")]])
    broadcast_message_status = await message.reply_text(
        "📡 𝖡𝗋𝗈𝖺𝖽𝖼𝖺𝗌𝗍 𝖨𝗇 𝖯𝗋𝗈𝗀𝗋𝖾𝗌𝗌", reply_markup=cancel_button
    )

    # Start broadcasting (forwarding the message)
    user_count, group_count = await broadcast_message(client, message.reply_to_message, groups, users, pin_message, target)

    # Edit the final broadcast message with a simple success message
    if not cancel_broadcast:
        await broadcast_message_status.edit_text("✅ 𝖡𝗋𝗈𝖺𝖽𝖼𝖺𝗌𝗍 𝖢𝗈𝗆𝗉𝗅𝖾𝗍𝖾𝖽 𝖲𝗎𝖼𝖼𝖾𝗌𝖿𝗎𝗅𝗅𝗒 !!")

    # Send detailed stats to the owner
    owner_message = (
        f"✅ 𝖡𝗋𝗈𝖺𝖽𝖼𝖺𝗌𝗍 𝖢𝗈𝗆𝗉𝗅𝖾𝗍𝖾𝖽!\n"
        f"👥 𝖴𝗌𝖾𝗋𝗌 𝖱𝖾𝖺𝖼𝗁𝖾𝖽: {user_count}\n"
        f"👥 𝖦𝗋𝗈𝗎𝗉𝗌 𝖱𝖾𝖺𝖼𝗁𝖾𝖽: {group_count}"
    )
    await client.send_message(config.OWNER_ID, owner_message)


@app.on_callback_query(filters.regex("cancel_broadcast"))
async def on_cancel_callback(client, query):
    await cancel_broadcast_callback(client, query)
