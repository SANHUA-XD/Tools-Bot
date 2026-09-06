from pyrogram import Client, filters
from pyrogram.types import Message , InlineKeyboardButton , InlineKeyboardMarkup , CallbackQuery
from Nobara.database.approve_db import *   
from Nobara import app
from Nobara.helper.user import UNMUTE
from pyrogram.errors import ChatAdminRequired
from pyrogram.enums import ChatMemberStatus
from Nobara.decorator.chatadmin import can_change_info , chatadmin , chatowner
from Nobara.helper.log_helper import send_log, format_log
from Nobara.decorator.errors import error
from Nobara.decorator.save import save 

# Command: /approve
@app.on_message(filters.command("approve") & filters.group)
@can_change_info
@error
@save
async def approve_user_command(client: Client, message: Message):

    if not message.from_user:
        return

    user_id = None
    chat_id = message.chat.id
    user = None

    try:
        if message.reply_to_message:
            user = message.reply_to_message.from_user
            user_id = user.id
            user_name = user.first_name
        else:
            args = message.text.split(maxsplit=1)
            if len(args) < 2:
                await message.reply("𝖯𝗅𝖾𝖺𝗌𝖾 𝗌𝗉𝖾𝖼𝗂𝖿𝗒 𝖺 𝗎𝗌𝖾𝗋 𝖨𝖣 𝗈𝗋 𝗎𝗌𝖾𝗋𝗇𝖺𝗆𝖾 𝗍𝗈 𝖺𝗉𝗉𝗋𝗈𝗏𝖾.")
                return
            user_id = args[1]
            if user_id.isdigit():
                user_id = int(user_id)
                user = await client.get_chat_member(chat_id, user_id)
                user_name = user.user.first_name
            else:
                user = await client.get_chat_member(chat_id, user_id)
                user_id = user.user.id
                user_name = user.user.first_name

        # Improved admin check
        chat_member = await client.get_chat_member(chat_id, user_id)
        if chat_member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            await message.reply_text(
                f"{user_name} 𝗂𝗌 𝖺𝗅𝗋𝖾𝖺𝖽𝗒 𝖺𝗇 𝖺𝖽𝗆𝗂𝗇. 𝖫𝗈𝖼𝗄𝗌, 𝖺𝗇𝗍𝗂𝖿𝗅𝗈𝗈𝖽, 𝖺𝗇𝖽 𝖻𝗅𝗈𝖼𝗄𝗅𝗂𝗌𝗍𝗌 𝖽𝗈𝗇'𝗍 𝖺𝗉𝗉𝗅𝗒 𝗍𝗈 𝗍𝗁𝖾𝗆."
            )
            return

        if await is_user_approved(chat_id, user_id):
            await message.reply(f"{user_name} 𝗂𝗌 𝖺𝗅𝗋𝖾𝖺𝖽𝗒 𝖺𝗉𝗉𝗋𝗈𝗏𝖾𝖽. 𝖫𝗈𝖼𝗄𝗌, 𝖺𝗇𝗍𝗂𝖿𝗅𝗈𝗈𝖽, 𝖺𝗇𝖽 𝖻𝗅𝗈𝖼𝗄𝗅𝗂𝗌𝗍𝗌 𝗐𝗈𝗇'𝗍 𝖺𝗉𝗉𝗅𝗒 𝗍𝗈 𝗍𝗁𝖾𝗆 𝗂𝗇 {message.chat.title}.")
            return

        if await approve_user(chat_id, user_id, user_name):
            await message.reply(f"{user_name} 𝗁𝖺𝗌 𝖻𝖾𝖾𝗇 𝖺𝗉𝗉𝗋𝗈𝗏𝖾𝖽 𝗂𝗇 {message.chat.title}! 𝖳𝗁𝖾𝗒 𝗐𝗂𝗅𝗅 𝗇𝗈𝗐 𝖻𝖾 𝗂𝗀𝗇𝗈𝗋𝖾𝖽 𝖻𝗒 𝖺𝗎𝗍𝗈𝗆𝖺𝗍𝖾𝖽 𝖺𝖽𝗆𝗂𝗇 𝖺𝖼𝗍𝗂𝗈𝗇𝗌 𝗅𝗂𝗄𝖾 𝗅𝗈𝖼𝗄𝗌, 𝖻𝗅𝗈𝖼𝗄𝗅𝗂𝗌𝗍𝗌, 𝖺𝗇𝖽 𝖺𝗇𝗍𝗂𝖿𝗅𝗈𝗈𝖽.")

            # Log the approval
            log_message = await format_log(
                tag="APPROVE",
                chat=message.chat.title,
                admin=message.from_user.first_name,
                user=user_name,
            )
            await send_log(chat_id, log_message)

        try:
            await app.restrict_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                permissions=UNMUTE
            )
        except ChatAdminRequired:
            await message.reply_text("𝖨 𝗅𝖺𝖼𝗄 𝖺𝖽𝗆𝗂𝗇 𝗉𝗋𝗂𝗏𝗂𝗅𝖾𝗀𝖾𝗌 𝗁𝖾𝗋𝖾. 𝖯𝗅𝖾𝖺𝗌𝖾 𝗀𝗋𝖺𝗇𝗍 𝗆𝖾 '𝖼𝖺𝗇_𝗋𝖾𝗌𝗍𝗋𝗂𝖼𝗍_𝗆𝖾𝗆𝖻𝖾𝗋𝗌' 𝗋𝗂𝗀𝗁𝗍𝗌!")

    except ChatAdminRequired:
        await message.reply_text("𝖨 𝗅𝖺𝖼𝗄 𝖺𝖽𝗆𝗂𝗇 𝗉𝗋𝗂𝗏𝗂𝗅𝖾𝗀𝖾𝗌 𝗁𝖾𝗋𝖾!")
    except Exception as e:
        await message.reply_text(f"𝖠𝗇 𝖾𝗋𝗋𝗈𝗋 𝗈𝖼𝖼𝗎𝗋𝗋𝖾𝖽: {str(e)}")


# Command: /unapprove
@app.on_message(filters.command("unapprove") & filters.group)
@can_change_info
@error
@save
async def unapprove_user_command(client: Client, message: Message):
    try:
        if not message.from_user:
            return

        chat_id = message.chat.id
        if message.reply_to_message:
            user = message.reply_to_message.from_user
            user_id = user.id
            user_name = user.first_name
        else:
            args = message.text.split(maxsplit=1)
            if len(args) < 2:
                await message.reply("𝖯𝗅𝖾𝖺𝗌𝖾 𝗌𝗉𝖾𝖼𝗂𝖿𝗒 𝖺 𝗎𝗌𝖾𝗋 𝖨𝖣 𝗈𝗋 𝗎𝗌𝖾𝗋𝗇𝖺𝗆𝖾 𝗍𝗈 𝗎𝗇𝖺𝗉𝗉𝗋𝗈𝗏𝖾.")
                return

            user_id = args[1]
            if user_id.isdigit():
                user_id = int(user_id)
                user = await client.get_users(user_id)
                user_name = user.first_name
            else:
                user = await client.get_chat_member(chat_id, user_id)
                user_id = user.user.id
                user_name = user.user.first_name

        # Improved admin check
        chat_member = await client.get_chat_member(chat_id, user_id)
        if chat_member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            await message.reply_text(
                f"{user_name} 𝗂𝗌 𝖺𝗅𝗋𝖾𝖺𝖽𝗒 𝖺𝗇 𝖺𝖽𝗆𝗂𝗇. 𝖫𝗈𝖼𝗄𝗌, 𝖺𝗇𝗍𝗂𝖿𝗅𝗈𝗈𝖽, 𝖺𝗇𝖽 𝖻𝗅𝗈𝖼𝗄𝗅𝗂𝗌𝗍𝗌 𝖽𝗈𝗇'𝗍 𝖺𝗉𝗉𝗅𝗒 𝗍𝗈 𝗍𝗁𝖾𝗆."
            )
            return

        if not await is_user_approved(chat_id, user_id):
            await message.reply_text(f"{user_name} is not approved yet.")
            return

        await unapprove_user(chat_id, user_id)
        await message.reply(f"{user_name} 𝗂𝗌 𝗇𝗈 𝗅𝗈𝗇𝗀𝖾𝗋 𝖺𝗉𝗉𝗋𝗈𝗏𝖾𝖽 𝗂𝗇{message.chat.title}.")
        # Log the approval
        log_message = await format_log(
            tag="UNAPPROVE",
            chat=message.chat.title,
            admin=message.from_user.first_name,
            user=user_name,
        )
        await send_log(chat_id, log_message)

    except ChatAdminRequired:
        await message.reply_text("𝖨 𝗅𝖺𝖼𝗄 𝖺𝖽𝗆𝗂𝗇 𝗉𝗋𝗂𝗏𝗂𝗅𝖾𝗀𝖾𝗌 𝗁𝖾𝗋𝖾!")
    except Exception as e:
        await message.reply_text(f"𝖠𝗇 𝖾𝗋𝗋𝗈𝗋 𝗈𝖼𝖼𝗎𝗋𝗋𝖾𝖽:{str(e)}")


@app.on_message(filters.command("approved") & filters.group)
@chatadmin
@error
@save
async def approved_users_command(client: Client, message: Message):
    if not message.from_user:
        return

    chat_id = message.chat.id
    approved_users = await get_approved_users(chat_id)
    if not approved_users:
        await message.reply("𝖭𝗈 𝗎𝗌𝖾𝗋𝗌 𝖺𝗋𝖾 𝖼𝗎𝗋𝗋𝖾𝗇𝗍𝗅𝗒 𝖺𝗉𝗉𝗋𝗈𝗏𝖾𝖽 𝗂𝗇 𝗍𝗁𝗂𝗌 𝖼𝗁𝖺𝗍.")
    else:
        approved_list = "\n".join([f"- {user_name} (ID: {user_id})" for user_id, user_name in approved_users])
        await message.reply(f"𝖠𝗅𝗅 𝖢𝗎𝗋𝗋𝖾𝗇𝗍𝗅𝗒 𝖠𝗉𝗉𝗋𝗈𝗏𝖾𝖽 𝖴𝗌𝖾𝗋𝗌 𝖨𝗇 {message.chat.title} : \n{approved_list}")


@app.on_message(filters.command("unapproveall") & filters.group)
@chatowner
@error
@save
async def remove_all_approve_users(client: Client, message: Message):

    # Send confirmation message with an inline button
    confirmation_buttons = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("𝖴𝗇𝖺𝗉𝗉𝗋𝗈𝗏𝖾 𝖠𝗅𝗅", callback_data=f"confirm_remove_approved_users")],
            [InlineKeyboardButton("🗑️", callback_data="cancel")],
        ]
    )
    await message.reply(
        f"𝖠𝗋𝖾 𝗒𝗈𝗎 𝗌𝗎𝗋𝖾 𝗒𝗈𝗎 𝗐𝖺𝗇𝗍 𝗍𝗈 𝗋𝖾𝗆𝗈𝗏𝖾 𝖺𝗅𝗅 𝖺𝗉𝗉𝗋𝗈𝗏𝖾𝖽 𝗎𝗌𝖾𝗋𝗌 𝖿𝗋𝗈𝗆 {message.chat.title}?",
        reply_markup=confirmation_buttons,
    )



@app.on_callback_query(filters.regex("^confirm_remove_approved_users"))
@chatowner
@error
async def confirm_remove_all(client: Client, callback_query: CallbackQuery):
    try:
        # Extract chat_id from callback_data
        chat_id = callback_query.message.chat.id

        # Remove all filters for the chat
        result = await unapprove_all_users(chat_id)
        
        if result:
            await callback_query.message.edit_text(f"𝖠𝗅𝗅 𝖠𝗉𝗉𝗋𝗈𝗏𝖾𝖽 𝖴𝗌𝖾𝗋𝗌 𝖧𝖺𝗌 𝖡𝖾𝖾𝗇 𝖴𝗇𝖺𝗉𝗉𝗋𝗈𝗏𝖾𝖽 𝖿𝗋𝗈𝗆 {callback_query.message.chat.title}!")
        else:
            await callback_query.message.edit_text(f"𝖭𝗈 𝖠𝗉𝗉𝗋𝗈𝗏𝖾𝖽 𝖴𝗌𝖾𝗋 𝖥𝗈𝗎𝗇𝖽 𝖨𝗇 {callback_query.message.chat.title}.")

        # Acknowledge the callback
        await callback_query.answer("All filters removed!", show_alert=False)
    except Exception as e:
        # Handle any errors gracefully
        print(f"Error during callback processing: {e}")
        await callback_query.message.edit_text("𝖠𝗇 𝖾𝗋𝗋𝗈𝗋 𝗈𝖼𝖼𝗎𝗋𝗋𝖾𝖽 𝗐𝗁𝗂𝗅𝖾 𝗋𝖾𝗆𝗈𝗏𝗂𝗇𝗀 𝖿𝗂𝗅𝗍𝖾𝗋𝗌.")
        await callback_query.answer("Error occurred!", show_alert=True)


__module__ = "𝖠𝗉𝗉𝗋𝗈𝗏𝖺𝗅"

__help__ = """𝖲𝗈𝗆𝖾𝗍𝗂𝗆𝖾𝗌, 𝗒𝗈𝗎 𝗆𝗂𝗀𝗁𝗍 𝗍𝗋𝗎𝗌𝗍 𝖺 𝗎𝗌𝖾𝗋 𝗇𝗈𝗍 𝗍𝗈 𝗌𝖾𝗇𝖽 𝗎𝗇𝗐𝖺𝗇𝗍𝖾𝖽 𝖼𝗈𝗇𝗍𝖾𝗇𝗍.
 𝖬𝖺𝗒𝖻𝖾 𝗇𝗈𝗍 𝖾𝗇𝗈𝗎𝗀𝗁 𝗍𝗈 𝗆𝖺𝗄𝖾 𝗍𝗁𝖾𝗆 𝖺𝖽𝗆𝗂𝗇, 𝖻𝗎𝗍 𝗒𝗈𝗎 𝗆𝗂𝗀𝗁𝗍 𝖻𝖾 𝗈𝗄 𝗐𝗂𝗍𝗁 𝗅𝗈𝖼𝗄𝗌, 𝖻𝗅𝖺𝖼𝗄𝗅𝗂𝗌𝗍𝗌, 𝖺𝗇𝖽 𝖺𝗇𝗍𝗂𝖿𝗅𝗈𝗈𝖽 𝗇𝗈𝗍 𝖺𝗉𝗉𝗅𝗒𝗂𝗇𝗀 𝗍𝗈 𝗍𝗁𝖾𝗆.
 
𝖳𝗁𝖺𝗍'𝗌 𝗐𝗁𝖺𝗍 𝖺𝗉𝗉𝗋𝗈𝗏𝖺𝗅𝗌 𝖺𝗋𝖾 𝖿𝗈𝗋 - 𝖺𝗉𝗉𝗋𝗈𝗏𝖾 𝗈𝖿 𝗍𝗋𝗎𝗌𝗍𝗐𝗈𝗋𝗍𝗁𝗒 𝗎𝗌𝖾𝗋𝗌 𝗍𝗈 𝖺𝗅𝗅𝗈𝗐 𝗍𝗁𝖾𝗆 𝗍𝗈 𝗌𝖾𝗇𝖽 𝗆𝖾𝗌𝗌𝖺𝗀𝖾𝗌 𝖿𝗋𝖾𝖾𝗅𝗒.
 
**𝖮𝗐𝗇𝖾𝗋 𝖮𝗇𝗅𝗒:**
   ✧ `/𝗎𝗇𝖺𝗉𝗉𝗋𝗈𝗏𝖾𝖺𝗅𝗅` **:** 𝖴𝗇𝖺𝗉𝗉𝗋𝗈𝗏𝖾 **𝖠𝖫𝖫** 𝗎𝗌𝖾𝗋𝗌 𝗂𝗇 𝖺 𝖼𝗁𝖺𝗍. 𝖳𝗁𝗂𝗌 𝖺𝖼𝗍𝗂𝗈𝗇 𝖼𝖺𝗇𝗇𝗈𝗍 𝖻𝖾 𝗎𝗇𝖽𝗈𝗇𝖾.
   
**𝖠𝖽𝗆𝗂𝗇 𝖢𝗈𝗆𝗆𝖺𝗇𝖽𝗌:**
   ✧ `/𝖺𝗉𝗉𝗋𝗈𝗏𝖾` (𝗎𝗌𝖾𝗋) **:** 𝖠𝗉𝗉𝗋𝗈𝗏𝖾 𝖺 𝗎𝗌𝖾𝗋. 𝖫𝗈𝖼𝗄𝗌, 𝖻𝗅𝖺𝖼𝗄𝗅𝗂𝗌𝗍𝗌, 𝖺𝗇𝖽 𝖺𝗇𝗍𝗂𝖿𝗅𝗈𝗈𝖽 𝗐𝗈𝗇'𝗍 𝖺𝗉𝗉𝗅𝗒 𝗍𝗈 𝗍𝗁𝖾𝗆 𝖺𝗇𝗒𝗆𝗈𝗋𝖾.
   ✧ `/𝗎𝗇𝖺𝗉𝗉𝗋𝗈𝗏𝖾` (𝗎𝗌𝖾𝗋) **:** 𝖴𝗇𝖺𝗉𝗉𝗋𝗈𝗏𝖾 𝖺 𝗎𝗌𝖾𝗋. 𝖳𝗁𝖾𝗒 𝗐𝗂𝗅𝗅 𝗇𝗈𝗐 𝖻𝖾 𝗌𝗎𝖻𝗃𝖾𝖼𝗍 𝗍𝗈 𝗅𝗈𝖼𝗄𝗌, 𝖻𝗅𝖺𝖼𝗄𝗅𝗂𝗌𝗍𝗌, 𝖺𝗇𝖽 𝖺𝗇𝗍𝗂𝖿𝗅𝗈𝗈𝖽 𝖺𝗀𝖺𝗂𝗇.
   ✧ `/𝖺𝗉𝗉𝗋𝗈𝗏𝖾𝖽` **:** 𝖫𝗂𝗌𝗍 𝖺𝗅𝗅 𝖺𝗉𝗉𝗋𝗈𝗏𝖾𝖽 𝗎𝗌𝖾𝗋𝗌.
 """