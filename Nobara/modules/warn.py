from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from Nobara.database import warn_db
from Nobara import app
from Nobara.helper.user import resolve_user , RESTRICT
from Nobara.decorator.chatadmin import can_restrict_members
from pyrogram.enums import ParseMode
from pyrogram.errors import ChatAdminRequired
from config import config
from pyrogram.enums import ChatMemberStatus
from Nobara.decorator.save import save 
from Nobara.decorator.errors import error


MAX_WARNS = warn_db.MAX_WARNS

@app.on_message(filters.command("warn" , prefixes=config.COMMAND_PREFIXES) & filters.group)
@can_restrict_members
@error
@save
async def warn_user(client: Client, message: Message):

    try :

        if len(message.command) < 2 and not message.reply_to_message:
            await message.reply(
                "<b>𝖴𝗌𝖺𝗀𝖾:</b> 𝖱𝖾𝗉𝗅𝗒 𝗍𝗈 𝖺 𝗎𝗌𝖾𝗋 𝗈𝗋 𝗆𝖾𝗇𝗍𝗂𝗈𝗇 𝗍𝗁𝖾𝗆 𝗍𝗈 𝗂𝗌𝗌𝗎𝖾 𝖺 𝗐𝖺𝗋𝗇𝗂𝗇𝗀. 𝖮𝗉𝗍𝗂𝗈𝗇𝖺𝗅𝗅𝗒, 𝗂𝗇𝖼𝗅𝗎𝖽𝖾 𝖺 𝗋𝖾𝖺𝗌𝗈𝗇.\n"
                "<b>𝖤𝗑𝖺𝗆𝗉𝗅𝖾:</b> <code>/𝗐𝖺𝗋𝗇 @𝗎𝗌𝖾𝗋𝗇𝖺𝗆𝖾 𝖲𝗉𝖺𝗆𝗆𝗂𝗇𝗀 𝗂𝗇 𝗍𝗁𝖾 𝖼𝗁𝖺𝗍</code>",
                parse_mode=ParseMode.HTML
            )
            return
    
        reason = " ".join(message.command[2:]) if len(message.command) > 2 else "𝖭𝗈 𝗋𝖾𝖺𝗌𝗈𝗇 𝗉𝗋𝗈𝗏𝗂𝖽𝖾𝖽."
        target_user = await resolve_user(client, message)
    
        if not target_user:
            await message.reply("<b>𝖤𝗋𝗋𝗈𝗋:</b> 𝖴𝗇𝖺𝖻𝗅𝖾 𝗍𝗈 𝗂𝖽𝖾𝗇𝗍𝗂𝖿𝗒 𝗍𝗁𝖾 𝗎𝗌𝖾𝗋 𝗍𝗈 𝗐𝖺𝗋𝗇.", parse_mode=ParseMode.HTML)
            return

        # Check the user's current status in the chat
        x = await app.get_chat_member(message.chat.id, target_user.id)
    
        if x.status == ChatMemberStatus.OWNER:
            await message.reply("𝖧𝗈𝗐 𝖢𝖺𝗇 𝖨 Warn 𝖳𝗁𝖾 𝖮𝗐𝗇𝖾𝗋 𝖮𝖥 𝖳𝗁𝗂𝗌 𝖢𝗁𝖺𝗍?")
            return
    
        if x.status == ChatMemberStatus.ADMINISTRATOR:
            await message.reply("𝖴𝗌𝖾𝗋 𝖨𝗌 𝖠𝗅𝗋𝖾𝖺𝖽𝗒 𝖠𝗇 𝖠𝖽𝗆𝗂𝗇!")
            return
    
        warn_count = await warn_db.add_warn(message.chat.id, target_user.id, reason, client)
        user_mention = target_user.mention
    
        if warn_count >= MAX_WARNS:
            await message.reply(
                f"**𝖴𝗌𝖾𝗋 𝖡𝖺𝗇𝗇𝖾𝖽:** {user_mention}\n"
                f"**𝖱𝖾𝖺𝗌𝗈𝗇:** {reason}\n"
                f"**𝖶𝖺𝗋𝗇𝗂𝗇𝗀𝗌 𝖤𝗑𝖼𝖾𝖾𝖽𝖾𝖽:** {MAX_WARNS}\n\n"
            )
            return
    
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("- 1", callback_data=f"warn_decrease_{target_user.id}"),
                InlineKeyboardButton("+ 1", callback_data=f"warn_increase_{target_user.id}")
            ],
            [InlineKeyboardButton("𝖢𝗅𝖾𝖺𝗋 𝖠𝗅𝗅 𝖶𝖺𝗋𝗇𝗂𝗇𝗀𝗌", callback_data=f"warn_delete_{target_user.id}")],
            [InlineKeyboardButton("🗑️", callback_data="delete")]
        ])
    
        await message.reply(
            f"**𝖶𝖺𝗋𝗇𝗂𝗇𝗀 𝖨𝗌𝗌𝗎𝖾𝖽:** {user_mention}\n"
            f"**𝖱𝖾𝖺𝗌𝗈𝗇:** {reason}\n"
            f"**𝖢𝗎𝗋𝗋𝖾𝗇𝗍 𝖶𝖺𝗋𝗇𝗂𝗇𝗀𝗌:** {warn_count} / {MAX_WARNS}",
            reply_markup=keyboard
        )
        await app.restrict_chat_member(message.chat.id , target_user.id , permissions=RESTRICT)

    except ChatAdminRequired:
        await message.reply_text("Chat ADMIN REQUIRED")
    except Exception :
        return   


@app.on_callback_query(filters.regex(r"warn_(increase|decrease|delete)_(\d+)"))
@can_restrict_members
@error
async def handle_warn_callbacks(client: Client, callback: CallbackQuery):

    try :

        action, user_id = callback.data.split("_")[1:]
        user_id = int(user_id)
    
        warn_count = 0
        if action == "increase":
            warn_count = await warn_db.add_warn(callback.message.chat.id, user_id, "𝖭𝗈 𝗋𝖾𝖺𝗌𝗈𝗇 𝗉𝗋𝗈𝗏𝗂𝖽𝖾𝖽.", client)
        elif action == "decrease":
            warn_count = await warn_db.remove_warn(callback.message.chat.id, user_id)
        elif action == "delete":
            await warn_db.clear_warns(callback.message.chat.id, user_id)
    
        if warn_count >= MAX_WARNS:
            await callback.message.edit_text(
                f"<b>𝖴𝗌𝖾𝗋 𝖡𝖺𝗇𝗇𝖾𝖽</b>\n"
                f"<b>𝖶𝖺𝗋𝗇𝗂𝗇𝗀𝗌 𝖤𝗑𝖼𝖾𝖾𝖽𝖾𝖽:</b> {MAX_WARNS}\n\n"
                f"<i>𝖳𝗁𝗂𝗌 𝗎𝗌𝖾𝗋 𝗁𝖺𝗌 𝖻𝖾𝖾𝗇 𝖻𝖺𝗇𝗇𝖾𝖽 𝖿𝗋𝗈𝗆 𝗍𝗁𝖾 𝖼𝗁𝖺𝗍.</i>",
                parse_mode=ParseMode.HTML
            )
        else:
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("- 1", callback_data=f"warn_decrease_{user_id}"),
                    InlineKeyboardButton("+ 1", callback_data=f"warn_increase_{user_id}")
                ],
                [InlineKeyboardButton("𝖢𝗅𝖾𝖺𝗋 𝖠𝗅𝗅 𝖶𝖺𝗋𝗇𝗂𝗇𝗀𝗌", callback_data=f"warn_delete_{user_id}")],
                [InlineKeyboardButton("🗑️", callback_data="delete")]
            ])
            action_text = "𝖨𝗇𝖼𝗋𝖾𝖺𝗌𝖾𝖽" if action == "increase" else "𝖣𝖾𝖼𝗋𝖾𝖺𝗌𝖾𝖽" if action == "decrease" else "𝖢𝗅𝖾𝖺𝗋𝖾𝖽"
            await callback.message.edit_text(
                f"<b>𝖶𝖺𝗋𝗇𝗂𝗇𝗀 𝖴𝗉𝖽𝖺𝗍𝖾𝖽</b>\n"
                f"<b>𝖠𝖼𝗍𝗂𝗈𝗇:</b> {action_text}\n"
                f"<b>𝖢𝗎𝗋𝗋𝖾𝗇𝗍 𝖶𝖺𝗋𝗇𝗂𝗇𝗀𝗌:</b> {warn_count} / {MAX_WARNS}",
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
    
        await callback.answer()
    except ChatAdminRequired :
        await callback.message.reply_text("Chat ADMIN REQUIRED !!")
    except Exception :
        return


@app.on_message(filters.command("unwarn" , prefixes=config.COMMAND_PREFIXES) & filters.group)
@can_restrict_members
@error
@save
async def unwarn_user(client: Client, message: Message):

    try :

        if len(message.command) < 2 and not message.reply_to_message:
            await message.reply(
                "<b>𝖴𝗌𝖺𝗀𝖾:</b> 𝖱𝖾𝗉𝗅𝗒 𝗍𝗈 𝖺 𝗎𝗌𝖾𝗋 𝗈𝗋 𝗆𝖾𝗇𝗍𝗂𝗈𝗇 𝗍𝗁𝖾𝗆 𝗍𝗈 𝗋𝖾𝗆𝗈𝗏𝖾 𝖺 𝗐𝖺𝗋𝗇𝗂𝗇𝗀.\n"
                "<b>𝖤𝗑𝖺𝗆𝗉𝗅𝖾:</b> <code>/𝗎𝗇𝗐𝖺𝗋𝗇 @𝗎𝗌𝖾𝗋𝗇𝖺𝗆𝖾 𝖬𝗂𝗌𝗍𝖺𝗄𝖾𝗇 𝗐𝖺𝗋𝗇𝗂𝗇𝗀</code>",
                parse_mode=ParseMode.HTML
            )
            return
    
        target_user = await resolve_user(client, message)
    
        if not target_user:
            await message.reply("<b>𝖤𝗋𝗋𝗈𝗋:</b> 𝖴𝗇𝖺𝖻𝗅𝖾 𝗍𝗈 𝗂𝖽𝖾𝗇𝗍𝗂𝖿𝗒 𝗍𝗁𝖾 𝗎𝗌𝖾𝗋 𝗍𝗈 𝗎𝗇𝗐𝖺𝗋𝗇.", parse_mode=ParseMode.HTML)
            return

        # Check the user's current status in the chat
        x = await app.get_chat_member(message.chat.id, target_user.id)
    
        if x.status == ChatMemberStatus.OWNER:
            await message.reply("𝖧𝗈𝗐 𝖢𝖺𝗇 𝖨 Unwarn 𝖳𝗁𝖾 𝖮𝗐𝗇𝖾𝗋 𝖮𝖥 𝖳𝗁𝗂𝗌 𝖢𝗁𝖺𝗍?")
            return
    
        if x.status == ChatMemberStatus.ADMINISTRATOR:
            await message.reply("𝖴𝗌𝖾𝗋 𝖨𝗌 𝖠𝗅𝗋𝖾𝖺𝖽𝗒 𝖠𝗇 𝖠𝖽𝗆𝗂𝗇!")
            return    

        warn_count = await warn_db.remove_warn(message.chat.id, target_user.id)
        user_mention = target_user.mention
    
        if warn_count == 0:
            await message.reply(
                f"**𝖭𝗈 𝗐𝖺𝗋𝗇𝗂𝗇𝗀𝗌 𝗍𝗈 𝗋𝖾𝗆𝗈𝗏𝖾 𝖿𝗈𝗋:** {user_mention}"
            )
            return
    
        await message.reply(
            f"**𝖶𝖺𝗋𝗇𝗂𝗇𝗀 𝗋𝖾𝗆𝗈𝗏𝖾𝖽 𝖿𝗈𝗋:** {user_mention}\n"
            f"**𝖱𝖾𝗆𝖺𝗂𝗇𝗂𝗇𝗀 𝖶𝖺𝗋𝗇𝗂𝗇𝗀𝗌:** {warn_count}"
        )
    except ChatAdminRequired :
        await message.reply_text("Chat ADMIN REQUIRED")
    except Exception :
        return

__module__ = "𝖶𝖺𝗋𝗇"


__help__ = """**𝖶𝖺𝗋𝗇𝗂𝗇𝗀 𝖲𝗒𝗌𝗍𝖾𝗆**

- **𝖢𝗈𝗆𝗆𝖺𝗇𝖽𝗌:**

  ✧ `/warn <user> [reason]` **:** 𝖨𝗌𝗌𝗎𝖾 𝖺 𝗐𝖺𝗋𝗇𝗂𝗇𝗀 𝗍𝗈 𝖺 𝗎𝗌𝖾𝗋 𝗂𝗇 𝗍𝗁𝖾 𝗀𝗋𝗈𝗎𝗉. 𝖳𝗁𝗂𝗌 𝗐𝗂𝗅𝗅 𝖺𝗅𝗌𝗈 𝖽𝗂𝗌𝗉𝗅𝖺𝗒 𝗍𝗁𝖾 𝗇𝗎𝗆𝖻𝖾𝗋 𝗈𝖿 𝗐𝖺𝗋𝗇𝗂𝗇𝗀𝗌.

  ✧ `/unwarn <user>` **:** 𝖱𝖾𝗆𝗈𝗏𝖾 𝗈𝗇𝖾 𝗐𝖺𝗋𝗇𝗂𝗇𝗀 𝖿𝗋𝗈𝗆 𝖺 𝗎𝗌𝖾𝗋.

- **𝖣𝖾𝗍𝖺𝗂𝗅𝗌:**
  
  ✧ 𝖶𝗁𝖾𝗇 𝖺 𝗎𝗌𝖾𝗋 𝗋𝖾𝖺𝖼𝗁𝖾𝗌 𝗍𝗁𝖾 𝗆𝖺𝗑𝗂𝗆𝗎𝗆 𝗐𝖺𝗋𝗇𝗂𝗇𝗀𝗌, 𝗍𝗁𝖾𝗒 𝗐𝗂𝗅𝗅 𝖻𝖾 𝖺𝗎𝗍𝗈𝗆𝖺𝗍𝗂𝖼𝖺𝗅𝗅𝗒 𝖻𝖺𝗇𝗇𝖾𝖽 𝖿𝗋𝗈𝗆 𝗍𝗁𝖾 𝗀𝗋𝗈𝗎𝗉.

  ✧ 𝖠𝖽𝗆𝗂𝗇𝗌 𝖼𝖺𝗇 𝗂𝗇𝖼𝗋𝖾𝖺𝗌𝖾, 𝖽𝖾𝖼𝗋𝖾𝖺𝗌𝖾, 𝗈𝗋 𝖼𝗅𝖾𝖺𝗋 𝗐𝖺𝗋𝗇𝗂𝗇𝗀𝗌 𝗏𝗂𝖺 𝗂𝗇𝗅𝗂𝗇𝖾 𝖻𝗎𝗍𝗍𝗈𝗇𝗌.

- **𝖤𝗑𝖺𝗆𝗉𝗅𝖾𝗌:**
  
  ✧ `/warn user Spamming in the group`
  ✧ `/unwarn user`
"""
