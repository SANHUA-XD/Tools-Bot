from pyrogram import filters , Client
from pyrogram.enums import ChatMemberStatus
from pyrogram.errors import ChatAdminRequired, RPCError
from Nobara import app as pgram
from pyrogram import enums
from pyrogram.types import ChatPermissions
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup , Message
from config import config 
from Nobara.decorator.save import save 
from Nobara.decorator.errors import error
from Nobara.decorator.chatadmin import chatowner

@pgram.on_message(filters.command("unmuteall" , prefixes=config.COMMAND_PREFIXES) & filters.group)
@chatowner
@error
@save
async def unmute_all_users(client, message):
    chat_id = message.chat.id
    chat_title = message.chat.title


    # Check if the bot has the necessary rights
    bot = await pgram.get_chat_member(chat_id,"me")
    if not bot.privileges or not bot.privileges.can_restrict_members:
        await message.reply_text(
            "**𝖨 𝖽𝗈𝗇'𝗍 𝗁𝖺𝗏𝖾 𝗍𝗁𝖾 𝗇𝖾𝖼𝖾𝗌𝗌𝖺𝗋𝗒 𝗉𝖾𝗋𝗆𝗂𝗌𝗌𝗂𝗈𝗇𝗌 𝗍𝗈 𝗎𝗇𝗆𝗎𝗍𝖾 𝗎𝗌𝖾𝗋𝗌.**\n"
            "𝖯𝗅𝖾𝖺𝗌𝖾 𝗀𝗋𝖺𝗇𝗍 𝗆𝖾 **𝖡𝖺𝗇 𝖱𝗂𝗀𝗁𝗍𝗌** 𝖺𝗇𝖽 𝗍𝗋𝗒 𝖺𝗀𝖺𝗂𝗇."
        )
        return

    # Notify the process start
    progress_message = await message.reply_text(
        f"🔍 **𝖥𝗂𝗇𝖽𝗂𝗇𝗀 𝗆𝗎𝗍𝖾𝖽 𝗎𝗌𝖾𝗋𝗌 𝗂𝗇** `{chat_title}`..."
    )

    try:
        # Find all muted users
        muted_users = []
        async for member in client.get_chat_members(chat_id, filter=enums.ChatMembersFilter.RESTRICTED):
            if member.status == ChatMemberStatus.RESTRICTED:
                muted_users.append(member.user.id)

        # Update the progress message
        if not muted_users:
            await progress_message.edit_text("**𝖭𝗈 𝗆𝗎𝗍𝖾𝖽 𝗆𝖾𝗆𝖻𝖾𝗋𝗌 𝖿𝗈𝗎𝗇𝖽 𝗂𝗇 𝗍𝗁𝗂𝗌 𝖼𝗁𝖺𝗍.**")
            return

        await progress_message.edit_text(
            f"🔍 **𝖥𝗈𝗎𝗇𝖽`{len(muted_users)}` 𝗆𝗎𝗍𝖾𝖽 𝗆𝖾𝗆𝖻𝖾𝗋𝗌 𝗂𝗇** `{chat_title}`.\n"
            "**𝖭𝗈𝗐 𝗎𝗇𝗆𝗎𝗍𝗂𝗇𝗀 𝗍𝗁𝖾𝗆 𝖺𝗅𝗅...**"
        )

        # Unmute all found members by resetting their permissions
        for user_id in muted_users:
            await pgram.restrict_chat_member(
                chat_id,
                user_id,
                permissions=ChatPermissions(can_send_messages=True, 
                                                     can_send_media_messages=True,
                                                     can_send_polls=True,
                                                     can_add_web_page_previews=True,
                                                     can_change_info=True,
                                                     can_invite_users=True,
                                                     can_pin_messages=True) 
                )

        # Notify success
        await progress_message.edit_text(
            f"**𝖲𝗎𝖼𝖼𝖾𝗌𝗌𝖿𝗎𝗅𝗅𝗒 𝗎𝗇𝗆𝗎𝗍𝖾𝖽`{len(muted_users)}` 𝗆𝖾𝗆𝖻𝖾𝗋𝗌 𝗂𝗇** `{chat_title}`!"
        )
    except ChatAdminRequired:
        await progress_message.edit_text(
            "**𝖥𝖺𝗂𝗅𝖾𝖽 𝗍𝗈 𝗎𝗇𝗆𝗎𝗍𝖾 𝗎𝗌𝖾𝗋𝗌 𝖽𝗎𝖾 𝗍𝗈 𝗂𝗇𝗌𝗎𝖿𝖿𝗂𝖼𝗂𝖾𝗇𝗍 𝗉𝖾𝗋𝗆𝗂𝗌𝗌𝗂𝗈𝗇𝗌.**"
        )
    except RPCError as e:
        await progress_message.edit_text(
            f"**𝖠𝗇 𝖾𝗋𝗋𝗈𝗋 𝗈𝖼𝖼𝗎𝗋𝗋𝖾𝖽 𝗐𝗁𝗂𝗅𝖾 𝗎𝗇𝗆𝗎𝗍𝗂𝗇𝗀 𝗎𝗌𝖾𝗋𝗌:**\n`{e}`"
        )

@pgram.on_message(filters.command("unbanall" , prefixes=config.COMMAND_PREFIXES) & filters.group)
@chatowner
@error
@save
async def unban_all_users(client: Client, message: Message):
    chat_id = message.chat.id
    chat_title = message.chat.title

    # Check if the bot has the necessary rights
    bot = await pgram.get_chat_member(chat_id, "me")
    if not bot.privileges or not bot.privileges.can_restrict_members:
        await message.reply_text(
            "**𝖨 𝖽𝗈𝗇'𝗍 𝗁𝖺𝗏𝖾 𝗍𝗁𝖾 𝗇𝖾𝖼𝖾𝗌𝗌𝖺𝗋𝗒 𝗉𝖾𝗋𝗆𝗂𝗌𝗌𝗂𝗈𝗇𝗌 𝗍𝗈 𝗎𝗇𝖻𝖺𝗇 𝗎𝗌𝖾𝗋𝗌.**\n"
            "𝖯𝗅𝖾𝖺𝗌𝖾 𝗀𝗋𝖺𝗇𝗍 𝗆𝖾 **𝖡𝖺𝗇 𝖱𝗂𝗀𝗁𝗍𝗌** 𝖺𝗇𝖽 𝗍𝗋𝗒 𝖺𝗀𝖺𝗂𝗇."
        )
        return

    # Notify the process start
    progress_message = await message.reply_text(
        f"🔍 **𝖥𝗂𝗇𝖽𝗂𝗇𝗀 𝖻𝖺𝗇𝗇𝖾𝖽 𝗎𝗌𝖾𝗋𝗌 𝗂𝗇** `{chat_title}`..."
    )

    try:
        # Find all banned users
        banned_users = []
        async for member in pgram.get_chat_members(chat_id, filter=enums.ChatMembersFilter.BANNED):
            if member.status == ChatMemberStatus.BANNED:
               if member.user: 
                   banned_users.append(member.user.id)

        # Update the progress message
        if not banned_users:
            await progress_message.edit_text("**𝖭𝗈 𝖻𝖺𝗇𝗇𝖾𝖽 𝗆𝖾𝗆𝖻𝖾𝗋𝗌 𝖿𝗈𝗎𝗇𝖽 𝗂𝗇 𝗍𝗁𝗂𝗌 𝖼𝗁𝖺𝗍.**")
            return

        await progress_message.edit_text(
            f"🔍 **𝖥𝗈𝗎𝗇𝖽 `{len(banned_users)}` 𝖻𝖺𝗇𝗇𝖾𝖽 𝗆𝖾𝗆𝖻𝖾𝗋𝗌 𝗂𝗇** `{chat_title}`.\n"
            "**𝖭𝗈𝗐 𝗎𝗇𝖻𝖺𝗇𝗇𝗂𝗇𝗀 𝗍𝗁𝖾𝗆 𝖺𝗅𝗅...**"
        )

        # Unban all found members
        for user_id in banned_users:
            await pgram.unban_chat_member(chat_id, user_id)

        # Notify success
        await progress_message.edit_text(
            f"**𝖲𝗎𝖼𝖼𝖾𝗌𝗌𝖿𝗎𝗅𝗅𝗒 𝗎𝗇𝖻𝖺𝗇𝗇𝖾𝖽 `{len(banned_users)}` 𝗆𝖾𝗆𝖻𝖾𝗋𝗌 𝗂𝗇** `{chat_title}`!"
        )
    except ChatAdminRequired:
        await progress_message.edit_text(
            "**𝖥𝖺𝗂𝗅𝖾𝖽 𝗍𝗈 𝗎𝗇𝖻𝖺𝗇 𝗎𝗌𝖾𝗋𝗌 𝖽𝗎𝖾 𝗍𝗈 𝗂𝗇𝗌𝗎𝖿𝖿𝗂𝖼𝗂𝖾𝗇𝗍 𝗉𝖾𝗋𝗆𝗂𝗌𝗌𝗂𝗈𝗇𝗌.**"
        )
    except RPCError as e:
        await progress_message.edit_text(
            f"**𝖠𝗇 𝖾𝗋𝗋𝗈𝗋 𝗈𝖼𝖼𝗎𝗋𝗋𝖾𝖽 𝗐𝗁𝗂𝗅𝖾 𝗎𝗇𝖻𝖺𝗇𝗇𝗂𝗇𝗀 𝗎𝗌𝖾𝗋𝗌:**\n`{e}`"
        )

@pgram.on_message(filters.command("clearzombies" , prefixes=config.COMMAND_PREFIXES) & filters.group)
@chatowner
@error
@save
async def clear_zombies(client, message):
    chat_id = message.chat.id
    chat_title = message.chat.title

    # Check if the bot has the necessary rights
    bot = await pgram.get_chat_member(chat_id, "me")
    if not bot.privileges or not bot.privileges.can_restrict_members:
        await message.reply_text(
        "**𝖨 𝖽𝗈𝗇'𝗍 𝗁𝖺𝗏𝖾 𝗍𝗁𝖾 𝗇𝖾𝖼𝖾𝗌𝗌𝖺𝗋𝗒 𝗉𝖾𝗋𝗆𝗂𝗌𝗌𝗂𝗈𝗇𝗌 𝗍𝗈 𝖻𝖺𝗇 𝗎𝗌𝖾𝗋𝗌.**\n"
            "𝖯𝗅𝖾𝖺𝗌𝖾 𝗀𝗋𝖺𝗇𝗍 𝗆𝖾 **𝖡𝖺𝗇 𝖱𝗂𝗀𝗁𝗍𝗌** 𝖺𝗇𝖽 𝗍𝗋𝗒 𝖺𝗀𝖺𝗂𝗇."
        )
        return

    # Notify the process start
    progress_message = await message.reply_text(
        f"🔍 **𝖲𝖼𝖺𝗇𝗇𝗂𝗇𝗀 𝖿𝗈𝗋 𝖽𝖾𝗅𝖾𝗍𝖾𝖽 𝖺𝖼𝖼𝗈𝗎𝗇𝗍𝗌 𝗂𝗇** `{chat_title}`..."
    )

    try:
        # Find all deleted accounts
        deleted_accounts = []
        async for member in client.get_chat_members(chat_id):
            if member.user.is_deleted:
                deleted_accounts.append(member.user.id)

        # Update the progress message
        if not deleted_accounts:
            await progress_message.edit_text("**𝖭𝗈 𝖽𝖾𝗅𝖾𝗍𝖾𝖽 𝖺𝖼𝖼𝗈𝗎𝗇𝗍𝗌 𝖿𝗈𝗎𝗇𝖽 𝗂𝗇 𝗍𝗁𝗂𝗌 𝖼𝗁𝖺𝗍.**")
            return

        await progress_message.edit_text(
            f"🔍 **𝖥𝗈𝗎𝗇𝖽 `{len(deleted_accounts)}` 𝖽𝖾𝗅𝖾𝗍𝖾𝖽 𝖺𝖼𝖼𝗈𝗎𝗇𝗍𝗌 𝗂𝗇** `{chat_title}`.\n"
            "**𝖭𝗈𝗐 𝖻𝖺𝗇𝗇𝗂𝗇𝗀 𝗍𝗁𝖾𝗆...**"
        )

        # Ban all deleted accounts
        for user_id in deleted_accounts:
            try:
                await pgram.ban_chat_member(chat_id, user_id)
            except RPCError:
                pass  # Ignore errors for individual accounts

        # Notify success
        await progress_message.edit_text(
            f"**𝖲𝗎𝖼𝖼𝖾𝗌𝗌𝖿𝗎𝗅𝗅𝗒 𝖻𝖺𝗇𝗇𝖾𝖽 `{len(deleted_accounts)}` 𝖽𝖾𝗅𝖾𝗍𝖾𝖽 𝖺𝖼𝖼𝗈𝗎𝗇𝗍𝗌 𝖿𝗋𝗈𝗆** `{chat_title}`!"
        )
    except RPCError as e:
        await progress_message.edit_text(
            f"**𝖠𝗇 𝖾𝗋𝗋𝗈𝗋 𝗈𝖼𝖼𝗎𝗋𝗋𝖾𝖽 𝗐𝗁𝗂𝗅𝖾 𝖻𝖺𝗇𝗇𝗂𝗇𝗀 𝖽𝖾𝗅𝖾𝗍𝖾𝖽 𝖺𝖼𝖼𝗈𝗎𝗇𝗍𝗌:**\n`{e}`"
        )


@pgram.on_message(filters.command("kickdumbs" , prefixes=config.COMMAND_PREFIXES) & filters.group)
@chatowner
@error
@save
async def kick_the_fools(client, message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    chat_title = message.chat.title

    try:
        # Check bot privileges
        bot_member = await client.get_chat_member(chat_id, (await client.get_me()).id)
        if not bot_member.privileges or not bot_member.privileges.can_restrict_members:
            await message.reply("𝖯𝗅𝖾𝖺𝗌𝖾 𝗀𝗋𝖺𝗇𝗍 𝗆𝖾 **𝖡𝖺𝗇 𝖱𝗂𝗀𝗁𝗍𝗌** 𝖺𝗇𝖽 𝗍𝗋𝗒 𝖺𝗀𝖺𝗂𝗇.")
            return

        # Notify about the scanning process
        status_message = await message.reply(f"`🔍 𝖲𝖼𝖺𝗇𝗇𝗂𝗇𝗀 𝖿𝗈𝗋 𝗂𝗇𝖺𝖼𝗍𝗂𝗏𝖾 𝗆𝖾𝗆𝖻𝖾𝗋𝗌 𝗂𝗇{chat_title}...`")

        # Collect inactive members
        inactive_members = []
        async for member in client.get_chat_members(chat_id):
            if member.user.status == enums.UserStatus.LONG_AGO:
                inactive_members.append(member.user.id)

        if not inactive_members:
            await status_message.edit("`𝖭𝗈 𝗂𝗇𝖺𝖼𝗍𝗂𝗏𝖾 𝗆𝖾𝗆𝖻𝖾𝗋𝗌 𝖿𝗈𝗎𝗇𝖽 𝗂𝗇 𝗍𝗁𝗂𝗌 𝖼𝗁𝖺𝗍.`")
            return

        # Show confirmation keyboard
        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("✅ 𝖪𝗂𝖼𝗄 𝖳𝗁𝖾𝗆 𝖠𝗅𝗅", callback_data="kick_all")],
                [InlineKeyboardButton("❌ 𝖢𝖺𝗇𝖼𝖾𝗅", callback_data="cancel_kick")]
            ]
        )

        await status_message.edit(
            f"𝖥𝗈𝗎𝗇𝖽 **{len(inactive_members)}** 𝗂𝗇𝖺𝖼𝗍𝗂𝗏𝖾 𝗆𝖾𝗆𝖻𝖾𝗋𝗌.",
            reply_markup=keyboard
        )

        @pgram.on_callback_query(filters.regex(r"kick_(all|cancel)"))
        @chatowner
        async def callback_kick(client, query):
            # Verify if the callback query is from the chat OWNER
            initiator = await client.get_chat_member(chat_id, query.from_user.id)
            if initiator.status != enums.ChatMemberStatus.OWNER:
                await query.answer("𝖮𝗇𝗅𝗒 𝗍𝗁𝖾 𝖼𝗁𝖺𝗍 𝗈𝗐𝗇𝖾𝗋 𝖼𝖺𝗇 𝖼𝗈𝗇𝖿𝗂𝗋𝗆 𝗍𝗁𝗂𝗌 𝖺𝖼𝗍𝗂𝗈𝗇.", show_alert=True)
                return

            if query.data == "kick_all":
                # Kick all inactive members
                for user_id in inactive_members:
                    try:
                        await client.ban_chat_member(chat_id, user_id)
                        await client.unban_chat_member(chat_id, user_id)  # Unban to allow rejoining
                    except ChatAdminRequired:
                        await query.message.edit("`𝖨 𝗇𝖾𝖾𝖽 𝖡𝖺𝗇 𝖱𝗂𝗀𝗁𝗍𝗌 𝗍𝗈 𝗉𝖾𝗋𝖿𝗈𝗋𝗆 𝗍𝗁𝗂𝗌 𝖺𝖼𝗍𝗂𝗈𝗇.`")
                        return
                    except Exception as e:
                        print(f"𝖤𝗋𝗋𝗈𝗋 𝗄𝗂𝖼𝗄𝗂𝗇𝗀 𝗎𝗌𝖾𝗋 {user_id}: {e}")

                await query.message.edit("`𝖠𝗅𝗅 𝗂𝗇𝖺𝖼𝗍𝗂𝗏𝖾 𝗆𝖾𝗆𝖻𝖾𝗋𝗌 𝗁𝖺𝗏𝖾 𝖻𝖾𝖾𝗇 𝗄𝗂𝖼𝗄𝖾𝖽.`")
            elif query.data == "cancel_kick":
                await query.message.edit("`𝖪𝗂𝖼𝗄𝗂𝗇𝗀 𝗂𝗇𝖺𝖼𝗍𝗂𝗏𝖾 𝗆𝖾𝗆𝖻𝖾𝗋𝗌 𝗁𝖺𝗌 𝖻𝖾𝖾𝗇 𝖺𝖻𝗈𝗋𝗍𝖾𝖽.`")

    except ChatAdminRequired:
        await message.reply("`𝖨 𝗇𝖾𝖾𝖽 𝖡𝖺𝗇 𝖱𝗂𝗀𝗁𝗍𝗌 𝗍𝗈 𝗉𝖾𝗋𝖿𝗈𝗋𝗆 𝗍𝗁𝗂𝗌 𝖺𝖼𝗍𝗂𝗈𝗇.`")
    except Exception as e:
        await message.reply("`𝖠𝗇 𝗎𝗇𝖾𝗑𝗉𝖾𝖼𝗍𝖾𝖽 𝖾𝗋𝗋𝗈𝗋 𝗈𝖼𝖼𝗎𝗋𝗋𝖾𝖽. 𝖢𝗁𝖾𝖼𝗄 𝗅𝗈𝗀𝗌 𝖿𝗈𝗋 𝖽𝖾𝗍𝖺𝗂𝗅𝗌.`")
        print(f"𝖤𝗋𝗋𝗈𝗋: {e}")


__module__ = "𝖬𝖺𝗌𝗌𝖠𝖼𝗍𝗂𝗈𝗇𝗌"


__help__ = """**𝖮𝗐𝗇𝖾𝗋 𝗈𝗇𝗅𝗒:**
  ✧ `/𝗎𝗇𝖻𝖺𝗇𝖺𝗅𝗅` **:** 𝖴𝗇𝖻𝖺𝗇𝗌 𝖠𝗅𝗅 𝖡𝖺𝗇𝗇𝖾𝖽 𝖴𝗌𝖾𝗋 𝖨𝗇 𝖢𝗎𝗋𝗋𝖾𝗇𝗍 𝖢𝗁𝖺𝗍.
   ✧ `/𝗎𝗇𝗆𝗎𝗍𝖾𝖺𝗅𝗅` **:** 𝖴𝗇𝗆𝗎𝗍𝖾𝗌 𝖠𝗅𝗅 𝖬𝗎𝗍𝖾𝖽 𝖴𝗌𝖾𝗋 𝖨𝗇 𝖢𝗎𝗋𝗋𝖾𝗇𝗍 𝖢𝗁𝖺𝗍.
   ✧ `/𝗄𝗂𝖼𝗄𝖽𝗎𝗆𝖻𝗌` **:** 𝖪𝗂𝖼𝗄𝗌 𝖠𝗅𝗅 𝖳𝗁𝖾 𝖨𝗇𝖺𝖼𝗍𝗂𝗏𝖾 𝖬𝖾𝗆𝖻𝖾𝗋𝗌 𝖨𝗇 𝖢𝗎𝗋𝗋𝖾𝗇𝗍 𝖢𝗁𝖺𝗍.
   ✧ `/𝖼𝗅𝖾𝖺𝗋𝗓𝗈𝗆𝖻𝗂𝖾𝗌` **:** 𝖡𝖺𝗇𝗌 𝖠𝗅𝗅 𝖳𝗁𝖾 𝖣𝖾𝗅𝖾𝗍𝖾𝖽 𝖠𝖼𝖼𝗈𝗎𝗇𝗍 𝖨𝗇 𝖢𝗎𝗋𝗋𝖾𝗇𝗍 𝖢𝗁𝖺𝗍.
 """