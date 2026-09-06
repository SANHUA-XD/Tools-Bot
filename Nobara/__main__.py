import os
import importlib
import asyncio
import json
from datetime import datetime, timedelta
from pyrogram import idle, filters , Client
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery , Message
from Nobara import app, log, telebot, BACKUP_FILE_JSON, ptb, scheduler
from config import config
from Nobara.helper.on_start import edit_restart_message, clear_downloads_folder, notify_startup
from Nobara.admin.roleassign import ensure_owner_is_hokage
from Nobara.helper.state import initialize_services
from Nobara.database import setup_indexes, db
from Nobara.database.wordseekdb import setup_wordseek_indexes
from Nobara.admin.backup import restore_db
from asyncio import sleep
from Nobara.decorator.save import save 
from Nobara.decorator.errors import error 

MODULES = ["modules", "watchers", "admin", "decorator"]
LOADED_MODULES = {}

import hashlib
import random
from Nobara.helper.link_share import decode_chat_id

def _module_id(name: str) -> str:
    """Short, stable id for a module name - does NOT depend on how many other
    modules exist or their sort order, so old /help messages keep working
    correctly even after modules are added/removed in a later deploy."""
    return hashlib.md5(name.encode("utf-8")).hexdigest()[:8]

# Load modules and extract __module__ and __help__
def load_modules_from_folder(folder_name):
    folder_path = os.path.join(os.path.dirname(__file__), folder_name)
    for filename in os.listdir(folder_path):
        if filename.endswith(".py") and filename != "__init__.py":
            module_name = filename[:-3]
            module = importlib.import_module(f"Nobara.{folder_name}.{module_name}")
            __module__ = getattr(module, "__module__", None)
            __help__ = getattr(module, "__help__", None)
            if __module__ and __help__:
                LOADED_MODULES[__module__] = __help__

def load_all_modules():
    for folder in MODULES:
        load_modules_from_folder(folder)
    log.info(f"Loaded {len(LOADED_MODULES)} modules: {', '.join(sorted(LOADED_MODULES.keys()))}")

# Pagination Logic
def get_paginated_buttons(page=1, items_per_page=15):
    modules = sorted(LOADED_MODULES.keys())
    total_pages = (len(modules) + items_per_page - 1) // items_per_page
    if total_pages == 0:
        total_pages = 1

    start_idx = (page - 1) * items_per_page
    end_idx = start_idx + items_per_page
    current_modules = modules[start_idx:end_idx]

    buttons = [
        InlineKeyboardButton(mod, callback_data=f"help_{_module_id(mod)}_{page}")
        for mod in current_modules
    ]
    button_rows = [buttons[i:i + 3] for i in range(0, len(buttons), 3)]

    # Navigation buttons logic: ⬅️ Prev | ❌ Close | Next ➡️ on one row, always
    # with Close in the middle regardless of whether Prev/Next exist.
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton("⬅️ 𝖯𝗋𝖾𝗏", callback_data=f"area_{page - 1}"))
    nav_buttons.append(InlineKeyboardButton("❌ 𝖢𝗅𝗈𝗌𝖾", callback_data="delete"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton("𝖭𝖾𝗑𝗍 ➡️", callback_data=f"area_{page + 1}"))

    button_rows.append(nav_buttons)

    # Back button gets its own row underneath
    button_rows.append([
        InlineKeyboardButton("🔙 𝖡𝖺𝖼𝗄", callback_data="st_back")
    ])

    return InlineKeyboardMarkup(button_rows)

# Helper to generate the main menu buttons
def get_main_menu_buttons():
    buttons = [
        [
            InlineKeyboardButton(
                "➕ ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ɢʀᴏᴜᴘ", url=f"https://t.me/{app.me.username}?startgroup=true"
            )
        ],
        [
            InlineKeyboardButton("🤝 Sᴜᴘᴘᴏʀᴛ", url=config.SUPPORT_CHAT_LINK),
            InlineKeyboardButton("👤 ᴏᴡɴᴇʀ", user_id=config.OWNER_ID)
        ],
        [
            InlineKeyboardButton("🆘 ʜᴇʟᴘ 🆘", callback_data="yumeko_help"),
            InlineKeyboardButton("ᴏᴛʜᴇʀꜱ", callback_data="source_code")
        ]
    ]
    return InlineKeyboardMarkup(buttons)

@app.on_message(filters.command("start" , config.COMMAND_PREFIXES) & filters.private)
@error
@save
async def start_cmd(_, message : Message):
    
    # Check for parameters passed with the start command
    if len(message.command) > 1 and message.command[1] == "help":
        await help_command(Client, message)
        return

    # /link deep link: https://t.me/Bot?start=req_<base64(chat_id)>
    if len(message.command) > 1 and message.command[1].startswith("req_"):
        encoded = message.command[1][4:]
        chat_id = decode_chat_id(encoded)

        if chat_id is None:
            await message.reply_text("⚠️ 𝖳𝗁𝗂𝗌 𝗅𝗂𝗇𝗄 𝗂𝗌 𝗂𝗇𝗏𝖺𝗅𝗂𝖽 𝗈𝗋 𝖾𝗑𝗉𝗂𝗋𝖾𝖽.")
            return

        try:
            chat = await app.get_chat(chat_id)
            expire_at = datetime.now() + timedelta(minutes=10)
            invite = await app.create_chat_invite_link(
                chat_id, creates_join_request=True, expire_date=expire_at
            )

            async def _revoke_after_expiry(chat_id=chat_id, link=invite.invite_link):
                # Telegram's `expire_date` alone just stops NEW joins after
                # that time - the link can still linger around as "expired"
                # instead of being fully revoked. Explicitly revoke it too,
                # at the same 10-minute mark, so it's both expired AND
                # revoked together as requested.
                await asyncio.sleep(600)
                try:
                    await app.revoke_chat_invite_link(chat_id, link)
                except Exception as revoke_err:
                    log.warning(f"Could not revoke expired /link invite for {chat_id}: {revoke_err}")

            asyncio.create_task(_revoke_after_expiry())

            random_pic = random.choice(config.LINK_PICS) if getattr(config, "LINK_PICS", None) else config.START_IMG_URL

            button = InlineKeyboardMarkup(
                [[InlineKeyboardButton("• 𝖱𝖾𝗊𝗎𝖾𝗌𝗍 𝖳𝗈 𝖩𝗈𝗂𝗇 •", url=invite.invite_link)]]
            )

            await message.reply_photo(
                photo=random_pic,
                caption=f"**𝖧𝖾𝗋𝖾 𝗂𝗌 𝗒𝗈𝗎𝗋 𝗅𝗂𝗇𝗄 𝖿𝗈𝗋 {chat.title}**\n\n𝖳𝖺𝗉 𝗍𝗁𝖾 𝖻𝗎𝗍𝗍𝗈𝗇 𝖻𝖾𝗅𝗈𝗐 𝗍𝗈 𝗋𝖾𝗊𝗎𝖾𝗌𝗍 𝗍𝗈 𝗃𝗈𝗂𝗇.\n⏳ 𝖳𝗁𝗂𝗌 𝗅𝗂𝗇𝗄 𝖾𝗑𝗉𝗂𝗋𝖾𝗌 & 𝗋𝖾𝗏𝗈𝗄𝖾𝗌 𝗂𝗇 𝟣𝟢 𝗆𝗂𝗇𝗎𝗍𝖾𝗌.",
                reply_markup=button
            )
        except Exception as e:
            await message.reply_text(f"⚠️ 𝖢𝗈𝗎𝗅𝖽𝗇'𝗍 𝗀𝖾𝗇𝖾𝗋𝖺𝗍𝖾 𝖺 𝗃𝗈𝗂𝗇 𝗅𝗂𝗇𝗄 𝖿𝗈𝗋 𝗍𝗁𝗂𝗌 𝖼𝗁𝖺𝗍. (`{e}`)")
        return
    
    x = await message.reply_text(f"`Hie {message.from_user.first_name} <3`")
    await sleep(0.3)
    await x.edit_text("🐾")
    await sleep(0.8)
    await x.edit_text("❄️")
    await sleep(0.8)
    await x.edit_text("🕊️")
    await sleep(0.8)
    await x.delete()
    
    await sleep(0.2)
    
    user_mention = message.from_user.mention(style="md")
    bot_mention = app.me.mention(style="md")
    await message.reply(
        f"**𝖧𝖾𝗒, {user_mention} 🧸**\n"
        f"**𝖨 𝖺𝗆 {bot_mention} ♡ , 𝗒𝗈𝗎𝗋 𝗏𝖾𝗋𝗌𝖺𝗍𝗂𝗅𝖾 𝗆𝖺𝗇𝖺𝗀𝖾𝗆𝖾𝗇𝗍 𝖻𝗈𝗍, 𝖽𝖾𝗌𝗂𝗀𝗇𝖾𝖽 𝗍𝗈 𝗁𝖾𝗅𝗉 𝗒𝗈𝗎 𝗍𝖺𝗄𝖾 𝖼𝗈𝗇𝗍𝗋𝗈𝗅 𝗈𝖿 𝗒𝗈𝗎𝗋 𝗀𝗋𝗈𝗎𝗉𝗌 𝗐𝗂𝗍𝗁 𝖾𝖺𝗌𝖾 𝗎𝗌𝗂𝗇𝗀 𝗆𝗒 𝗉𝗈𝗐𝖾𝗋𝖿𝗎𝗅 𝗆𝗈𝖽𝗎𝗅𝖾𝗌 𝖺𝗇𝖽 𝖼𝗈𝗆𝗆𝖺𝗇𝖽𝗌!**\n\n"
        f"[✨]({config.START_IMG_URL}) **𝖶𝗁𝖺𝗍 𝖨 𝖢𝖺𝗇 𝖣𝗈:**\n"
        f" • 𝖲𝖾𝖺𝗆𝗅𝖾𝗌𝗌 𝗆𝖺𝗇𝖺𝗀𝖾𝗆𝖾𝗇𝗍 𝗈𝖿 𝗒𝗈𝗎𝗋 𝗀𝗋𝗈𝗎𝗉𝗌\n"
        f" • 𝖯𝗈𝗐𝖾𝗋𝖿𝗎𝗅 𝗆𝗈𝖽𝖾𝗋𝖺𝗍𝗂𝗈𝗇 𝗍𝗈𝗈𝗅𝗌\n"
        f" • 𝖥𝗎𝗇 𝖺𝗇𝖽 𝖾𝗇𝗀𝖺𝗀𝗂𝗇𝗀 𝖿𝖾𝖺𝗍𝗎𝗋𝖾𝗌\n\n"
        f"📚 **𝖭𝖾𝖾𝖽 𝖧𝖾𝗅𝗉?**\n"
        f"𝖢𝗅𝗂𝖼𝗄 𝗍𝗁𝖾 𝖧𝖾𝗅𝗉 𝖻𝗎𝗍𝗍𝗈𝗇 𝖻𝖾𝗅𝗈𝗐 𝗍𝗈 𝗀𝖾𝗍 𝖺𝗅𝗅 𝗍𝗁𝖾 𝖽𝖾𝗍𝖺𝗂𝗅𝗌 𝖺𝖻𝗈𝗎𝗍 𝗆𝗒 𝗆𝗈𝖽𝗎𝗅𝖾𝗌 𝖺𝗇𝖽 𝖼𝗈𝗆𝗆𝖺𝗇𝖽𝗌.",
        reply_markup=get_main_menu_buttons(),
        invert_media = True
    )

# Handler for the "Back" button across the bot
@app.on_callback_query(filters.regex(r"^st_back$"))
@error
async def st_back_callback(client, query: CallbackQuery):
    user_mention = query.from_user.mention(style="md")
    bot_mention = app.me.mention(style="md")
    text = (
        f"**𝖧𝖾𝗒, {user_mention} 🧸**\n"
        f"**𝖨 𝖺𝗆 {bot_mention} ♡ , 𝗒𝗈𝗎𝗋 𝗏𝖾𝗋𝗌𝖺𝗍𝗂𝗅𝖾 𝗆𝖺𝗇𝖺𝗀𝖾𝗆𝖾𝗇𝗍 𝖻𝗈𝗍, 𝖽𝖾𝗌𝗂𝗀𝗇𝖾𝖽 𝗍𝗈 𝗁𝖾𝗅𝗉 𝗒𝗈𝗎 𝗍𝖺𝗄𝖾 𝖼𝗈𝗇𝗍𝗋𝗈𝗅 𝗈𝖿 𝗒𝗈𝗎𝗋 𝗀𝗋𝗈𝗎𝗉𝗌 𝗐𝗂𝗍𝗁 𝖾𝖺𝗌𝖾 𝗎𝗌𝗂𝗇𝗀 𝗆𝗒 𝗉𝗈𝗐𝖾𝗋𝖿𝗎𝗅 𝗆𝗈𝖽𝗎𝗅𝖾𝗌 𝖺𝗇𝖽 𝖼𝗈𝗆𝗆𝖺𝗇𝖽𝗌!**\n\n"
        f"[✨]({config.START_IMG_URL}) **𝖶𝗁𝖺𝗍 𝖨 𝖢𝖺𝗇 𝖣𝗈:**\n"
        f" • 𝖲𝖾𝖺𝗆𝗅𝖾𝗌𝗌 𝗆𝖺𝗇𝖺𝗀𝖾𝗆𝖾𝗇𝗍 𝗈𝖿 𝗒𝗈𝗎𝗋 𝗀𝗋𝗈𝗎𝗉𝗌\n"
        f" • 𝖯𝗈𝗐𝖾𝗋𝖿𝗎𝗅 𝗆𝗈𝖽𝖾𝗋𝖺𝗍𝗂𝗈𝗇 𝗍𝗈𝗈𝗅𝗌\n"
        f" • 𝖥𝗎𝗇 𝖺𝗇𝖽 𝖾𝗇𝗀𝖺𝗀𝗂𝗇𝗀 𝖿𝖾𝖺𝗍𝗎𝗋𝖾𝗌\n\n"
        f"📚 **𝖭𝖾𝖾𝖽 𝖧𝖾𝗅𝗉?**\n"
        f"𝖢𝗅𝗂𝖼𝗄 𝗍𝗁𝖾 𝖧𝖾𝗅𝗉 𝖻𝗎𝗍𝗍𝗈𝗇 𝖻𝖾𝗅𝗈𝗐 𝗍𝗈 𝗀𝖾𝗍 𝖺𝗅𝗅 𝗍𝗁𝖾 𝖽𝖾𝗍𝖺𝗂𝗅𝗌 𝖺𝖻𝗈𝗎𝗍 𝗆𝗒 𝗆𝗈𝖽𝗎𝗅𝖾𝗌 𝖺𝗇𝖽 𝖼𝗈𝗆𝗆𝖺𝗇𝖽𝗌."
    )
    await query.message.edit_text(
        text=text,
        reply_markup=get_main_menu_buttons(),
        invert_media=True
    )

@app.on_message(filters.command("help", prefixes=config.COMMAND_PREFIXES) & filters.private)
@error
@save
async def help_command(client, message: Message):
    prefixes = " ".join(config.COMMAND_PREFIXES)
    await message.reply(
        text=f"**𝖧𝖾𝗋𝖾 𝗂𝗌 𝗍𝗁𝖾 𝗅𝗂𝗌𝗍 𝗈𝖿 𝖺𝗅𝗅 𝗆𝗒 𝗆𝗈𝖽𝗎𝗅𝖾𝗌!**\n"
             f"**𝖢𝗅𝗂𝖼𝗄 𝗈𝗇 𝖺 𝗆𝗈𝖽𝗎𝗅𝖾 𝖻𝖾𝗅𝗈𝗐 𝗍𝗈 𝗀𝖾𝗍 𝖽𝖾𝗍𝖺𝗂𝗅𝖾𝖽 𝗂𝗇𝖿𝗈𝗋𝗆𝖺𝗍𝗂𝗈𝗇 𝖺𝖻𝗈𝗎𝗍 𝗂𝗍.**\n\n"
             f"🔹 **𝖠𝗏𝖺𝗂𝗅𝖺𝖻𝗅𝖾 𝖯𝗋𝖾𝖿𝗂𝗑𝖾𝗌:** {prefixes} \n\n"
             f"[📩]({config.HELP_IMG_URL}) **𝖥𝗈𝗎𝗇𝖽 𝖺 𝖻𝗎𝗀?**\n"
             f"𝖱𝖾𝗉𝗈𝗋𝗍 𝗂𝗍 𝗎𝗌𝗂𝗇𝗀 𝗍𝗁𝖾 /𝖻𝗎𝗀 𝖼𝗈𝗆𝗆𝖺𝗇𝖽, 𝖺𝗇𝖽 𝖨’𝗅𝗅 𝗀𝖾𝗍 𝗂𝗍 𝖿𝗂𝗑𝖾𝖽 𝖺𝗌 𝗌𝗈𝗈𝗇 𝖺𝗌 𝗉𝗈𝗌𝗌𝗂𝖻𝗅𝖾!",
        reply_markup=get_paginated_buttons()
    )

@app.on_callback_query(filters.regex("source_code"))
@error
async def source_code(_, clb: CallbackQuery):
    await clb.answer()
    await clb.message.edit(
        text=(
            "✨ **Name:** Mikasa\n"
            "👨‍💻 **Developer:** [Nobita](https://t.me/Sourov_Nobita)\n\n"
            "🤖 **Bots Under This Community:**\n"
            "   • [Auto Caption Bot](https://t.me/Rare_Auto_Caption_Bot)\n"
            "   • [Group Filter Bot](https://t.me/Rare_Filter_Bot)\n\n"           
            "📂 **Source:** [Main Channel](https://t.me/Rare_Bots_Hub)"
        ),
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔙 Bᴀᴄᴋ", callback_data="st_back")
            ]
        ]),
        disable_web_page_preview=True
    )


@app.on_callback_query(filters.regex(r"^yumeko_help$"))
async def show_help_menu(client, query: CallbackQuery):
    prefixes = " ".join(config.COMMAND_PREFIXES)
    await query.message.edit(
        text=f"**𝖧𝖾𝗋𝖾 𝗂𝗌 𝗍𝗁𝖾 𝗅𝗂𝗌𝗍 𝗈𝖿 𝖺𝗅𝗅 𝗆𝗒 𝗆𝗈𝖽𝗎𝗅𝖾𝗌!**\n"
             f"**𝖢𝗅𝗂𝖼𝗄 𝗈𝗇 𝖺 𝗆𝗈𝖽𝗎𝗅𝖾 𝖻𝖾𝗅𝗈𝗐 𝗍𝗈 𝗀𝖾𝗍 𝖽𝖾𝗍𝖺𝗂𝗅𝖾𝖽 𝗂𝗇𝖿𝗈𝗋𝗆𝖺𝗍𝗂𝗈𝗇 𝖺𝖻𝗈𝗎𝗍 𝗂𝗍.**\n\n"
             f"🔹 **𝖠𝗏𝖺𝗂𝗅𝖺𝖻𝗅𝖾 𝖯𝗋𝖾𝖿𝗂𝗑𝖾𝗌:** {prefixes} \n\n"
             f"[📩]({config.HELP_IMG_URL}) **𝖥𝗈𝗎𝗇𝖽 𝖺 𝖻𝗎𝗀?**\n"
             f"𝖱𝖾𝗉𝗈𝗋𝗍 𝗂𝗍 𝗎𝗌𝗂𝗇𝗀 𝗍𝗁𝖾 /𝖻𝗎𝗀 𝖼𝗈𝗆𝗆𝖺𝗇𝖽, 𝖺𝗇𝖽 𝖨’𝗅𝗅 𝗀𝖾𝗍 𝗂𝗍 𝖿𝗂𝗑𝖾𝖽 𝖺𝗌 𝗌𝗈𝗈𝗇 𝖺𝗌 𝗉𝗈𝗌𝗌𝗂𝖻𝗅𝖾!",
        reply_markup=get_paginated_buttons(),
        invert_media=True
    )

# Callback query handler for module help
@app.on_callback_query(filters.regex(r"^help_[0-9a-f]+_\d+$"))
async def handle_help_callback(client, query: CallbackQuery):
    data = query.data
    try:
        # Extract the module id and page from the callback data
        parts = data.split("_")
        module_id = parts[1]
        current_page = int(parts[2])

        # Look the module up by its stable hash id, not by position - so this
        # keeps working even if modules were added/removed since this
        # /help message was originally sent (e.g. after a redeploy).
        module_name = next((name for name in LOADED_MODULES if _module_id(name) == module_id), None)
        if module_name is None:
            await query.answer("This module no longer exists (the bot may have been updated). Please run /help again.", show_alert=True)
            return

        help_text = LOADED_MODULES.get(module_name, "No help available for this module.")

        # Edit the message to display the help text
        await query.message.edit(
            text=f"{help_text}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 𝖡𝖺𝖼𝗄", callback_data=f"area_{current_page}")]
            ])
        )
        await query.answer()
    except (ValueError, IndexError):
        # This almost always means the /help menu being tapped is "stale" -
        # it was generated before the bot's module list changed (a new
        # deploy added/removed a module), so the numeric index baked into
        # this old message's buttons no longer points to the same module.
        await query.answer(
            "This menu is outdated (the bot was updated since it was sent). Please run /help again.",
            show_alert=True
        )
    except Exception as e:
        # Previously any other error here (e.g. a bad/unescaped character in a
        # module's help text causing Telegram to reject the message edit) was
        # never caught, so the tapped button just sat there "loading" forever
        # with no feedback and no fix. Now we surface it instead of hanging.
        log.warning(f"handle_help_callback failed for {data}: {e}")
        await query.answer("Couldn't open this module's help right now. Please try again.", show_alert=True)

# Callback query handler for pagination
@app.on_callback_query(filters.regex(r"^area_\d+$"))
async def handle_pagination_callback(client, query: CallbackQuery):
    data = query.data
    try:
        page = int(data[5:])
        prefixes = " ".join(config.COMMAND_PREFIXES)

        # Edit both the message text and reply markup
        await query.message.edit(
        text=f"**𝖧𝖾𝗋𝖾 𝗂𝗌 𝗍𝗁𝖾 𝗅𝗂𝗌𝗍 𝗈𝖿 𝖺𝗅𝗅 𝗆𝗒 𝗆𝗈𝖽𝗎𝗅𝖾𝗌!**\n"
             f"**𝖢𝗅𝗂𝖼𝗄 𝗈𝗇 𝖺 𝗆𝗈𝖽𝗎𝗅𝖾 𝖻𝖾𝗅𝗈𝗐 𝗍𝗈 𝗀𝖾𝗍 𝖽𝖾𝗍𝖺𝗂𝗅𝖾𝖽 𝗂𝗇𝖿𝗈𝗋𝗆𝖺𝗍𝗂𝗈𝗇 𝖺𝖻𝗈𝗎𝗍 𝗂𝗍.**\n\n"
             f"🔹 **𝖠𝗏𝖺𝗂𝗅𝖺𝖻𝗅𝖾 𝖯𝗋𝖾𝖿𝗂𝗑𝖾𝗌:** {prefixes} \n\n"
             f"[📩]({config.HELP_IMG_URL}) **𝖥𝗈𝗎𝗇𝖽 𝖺 𝖻𝗎𝗀?**\n"
             f"𝖱𝖾𝗉𝗈𝗋𝗍 𝗂𝗍 𝗎𝗌𝗂𝗇𝗀 𝗍𝗁𝖾 /𝖻𝗎𝗀 𝖼𝗈𝗆𝗆𝖺𝗇𝖽, 𝖺𝗇𝖽 𝖨’𝗅𝗅 𝗀𝖾𝗍 𝗂𝗍 𝖿𝗂𝗑𝖾𝖽 𝖺𝗌 𝗌𝗈𝗈𝗇 𝖺𝗌 𝗉𝗈𝗌𝗌𝗂𝖻𝗅𝖾!",
            reply_markup=get_paginated_buttons(page),
            invert_media=True
        )
        await query.answer()
    except Exception as e:
        log.warning(f"handle_pagination_callback failed: {e}")
        await query.answer("Error occurred while navigating pages. Please try again.", show_alert=True)

# Callback query handler for main menu
@app.on_callback_query(filters.regex(r"^main_menu$"))
async def handle_main_menu_callback(client, query: CallbackQuery):
    prefixes = " ".join(config.COMMAND_PREFIXES)

    try:
        await query.message.edit(
            text=f"**𝖧𝖾𝗋𝖾 𝗂𝗌 𝗍𝗁𝖾 𝗅𝗂𝗌𝗍 𝗈𝖿 𝖺𝗅𝗅 𝗆𝗒 𝗆𝗈𝖽𝗎𝗅𝖾𝗌!**\n"
                 f"**𝖢𝗅𝗂𝖼𝗄 𝗈𝗇 𝖺 𝗆𝗈𝖽𝗎𝗅𝖾 𝖻𝖾𝗅𝗈𝗐 𝗍𝗈 𝗀𝖾𝗍 𝖽𝖾𝗍𝖺𝗂𝗅𝖾𝖽 𝗂𝗇𝖿𝗈𝗋𝗆𝖺𝗍𝗂𝗈𝗇 𝖺𝖻𝗈𝗎𝗍 𝗂𝗍.**\n\n"
                 f"🔹 **𝖠𝗏𝖺𝗂𝗅𝖺𝖻𝗅𝖾 𝖯𝗋𝖾𝖿𝗂𝗑𝖾𝗌:** {prefixes} \n\n"
                 f"[📩]({config.HELP_IMG_URL}) **𝖥𝗈𝗎𝗇𝖽 𝖺 𝖻𝗎𝗀?**\n"
                 f"𝖱𝖾𝗉𝗈𝗋𝗍 𝗂𝗍 𝗎𝗌𝗂𝗇𝗀 𝗍𝗁𝖾 /𝖻𝗎𝗀 𝖼𝗈𝗆𝗆𝖺𝗇𝖽, 𝖺𝗇𝖽 𝖨’𝗅𝗅 𝗀𝖾𝗍 𝗂𝗍 𝖿𝗂𝗑𝖾𝖽 𝖺𝗌 𝗌𝗈𝗈𝗇 𝖺𝗌 𝗉𝗈𝗌𝗌𝗂𝖻𝗅𝖾!",
            reply_markup=get_paginated_buttons(),
            invert_media=True
        )
        await query.answer()
    except Exception as e:
        log.warning(f"handle_main_menu_callback failed: {e}")
        await query.answer("Couldn't open the module list right now. Please try again.", show_alert=True)
    
@app.on_message(filters.command(["start" , "help"], prefixes=config.COMMAND_PREFIXES) & filters.group)
async def start_command(client, message: Message):
    button = InlineKeyboardMarkup([
        [InlineKeyboardButton("Sᴛᴀʀᴛ ɪɴ ᴘᴍ", url=f"https://t.me/{app.me.username}?start=help")]
    ])
    await message.reply(
        text=f"**𝖧𝖾𝗅𝗅𝗈, {message.from_user.first_name} <3**\n"
             f"𝖢𝗅𝗂𝖼𝗄 𝗍𝗁𝖾 𝖻𝗎𝗍𝗍𝗈𝗇 𝖻𝖾𝗅𝗈𝗐 𝗍𝗈 𝖾𝗑𝗉𝗅𝗈𝗋𝖾 𝗆𝗒 𝖿𝖾𝖺𝗍𝗎𝗋𝖾𝗌 𝖺𝗇𝖽 𝖼𝗈𝗆𝗆𝖺𝗇𝖽𝗌!",
        reply_markup=button
    )


async def is_database_empty():
    collections = [db.users, db.afk_collection, db.rules_collection, db.announcement_collection]
    for collection in collections:
        if await collection.count_documents({}) > 0:
            return False
    return True

def get_last_backup_file_id():
    if os.path.exists(BACKUP_FILE_JSON):
        with open(BACKUP_FILE_JSON, "r") as f:
            data = json.load(f)
            return data.get("file_id")
    return None

async def restore_from_last_backup():
    file_id = get_last_backup_file_id()
    if not file_id:
        return "No backup file ID found. Please perform a backup first."

    log.info(f"Restoring from backup file with ID: {file_id}")
    file_path = await app.download_media(file_id)
    response = restore_db(file_path)
    os.remove(file_path)
    return response

if __name__ == "__main__":
    load_all_modules()

    try:
        app.start()
        telebot.start(bot_token=config.BOT_TOKEN)
        initialize_services()
        ensure_owner_is_hokage()
        edit_restart_message()
        clear_downloads_folder()
        notify_startup()

        loop = asyncio.get_event_loop()

        async def initialize_async_components():
            await setup_indexes()
            await setup_wordseek_indexes()
            if await is_database_empty():
                log.warning("Database is empty. Attempting to restore from the last backup...")
                # try :
                #     restore_status = await restore_from_last_backup()
                #     log.info(restore_status)
                # except:
                #     pass
            else:
                log.info("Database is not empty. Proceeding with startup.")
            scheduler.start()
            log.info("Async components initialized.")

            bot_details = await app.get_me()
            log.info(f"Bot Configured: Name: {bot_details.first_name}, ID: {bot_details.id}, Username: @{bot_details.username}")

        loop.run_until_complete(initialize_async_components())
        ptb.run_polling(timeout=15, drop_pending_updates=True)
        log.info("Bot started. Press Ctrl+C to stop.")
        idle()

    except Exception as e:
        log.exception(e)
