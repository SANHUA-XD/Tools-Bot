from Nobara import app , CHATBOT_GROUP
from Nobara.database.chatbotdb import enable_chatbot , disable_chatbot , is_chatbot_enabled
from pyrogram import Client , filters
from pyrogram.types import Message , CallbackQuery , InlineKeyboardButton , InlineKeyboardMarkup
from config import config 
from Nobara.decorator.chatadmin import chatadmin
from pyrogram.enums import ChatAction
from Nobara.helper.ai_provider import get_ai_response
from Nobara.decorator.save import save 
from Nobara.decorator.errors import error

CHATBOT_SYSTEM_PROMPT = (
    "You are a friendly, witty Telegram group chatbot. Keep replies short, "
    "casual and conversational."
)

# Command to toggle announcement status
@app.on_message(filters.command("chatbot" , prefixes=config.COMMAND_PREFIXES) & filters.group)
@chatadmin
@error
@save
async def chatbot_handler(client: Client, message: Message):
    chat_id = message.chat.id
        
    if await is_chatbot_enabled(chat_id):
        # If already enabled, send a button to disable
        button = InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔴 𝖣𝗂𝗌𝖺𝖻𝗅𝖾 𝖢𝗁𝖺𝗍𝖡𝗈𝗍", callback_data=f"disable_chatbot:{chat_id}")],
            [InlineKeyboardButton("🗑️", callback_data="delete")]]
        )
        await message.reply_text("**📢 𝖢𝗁𝖺𝗍𝖡𝗈𝗍 𝗂𝗌 𝖾𝗇𝖺𝖻𝗅𝖾𝖽 𝗂𝗇 𝗍𝗁𝗂𝗌 𝖼𝗁𝖺𝗍.**", reply_markup=button)
    else:
        # If not enabled, send a button to enable
        button = InlineKeyboardMarkup(
            [[InlineKeyboardButton("🟢 𝖤𝗇𝖺𝖻𝗅𝖾 𝖢𝗁𝖺𝗍𝖡𝗈𝗍", callback_data=f"enable_chatbot:{chat_id}")],
            [InlineKeyboardButton("🗑️", callback_data="delete")]]
             
        )
        await message.reply_text("**📢 𝖢𝗁𝖺𝗍𝖡𝗈𝗍 𝗂𝗌 𝖽𝗂𝗌𝖺𝖻𝗅𝖾𝖽 𝗂𝗇 𝗍𝗁𝗂𝗌 𝖼𝗁𝖺𝗍.**", reply_markup=button)


# Callback query handler to enable/disable announcements
@app.on_callback_query(filters.regex("^(enable_chatbot|disable_chatbot):"))
@chatadmin
@error
async def toggle_announcements(client: Client, callback_query : CallbackQuery):
    action, chat_id = callback_query.data.split(":")
    chat_id = int(chat_id)
    chat = await client.get_chat(chat_id)

    if action == "enable_chatbot":
        await enable_chatbot(chat_id, chat.title, chat.username)
        await callback_query.message.edit_text("**🟢 𝖢𝗁𝖺𝗍𝖡𝗈𝗍 𝗁𝖺𝗌 𝖻𝖾𝖾𝗇 𝖾𝗇𝖺𝖻𝗅𝖾𝖽 𝖿𝗈𝗋 𝗍𝗁𝗂𝗌 𝖼𝗁𝖺𝗍.**")
    elif action == "disable_chatbot":
        await disable_chatbot(chat_id)
        await callback_query.message.edit_text("**🔴 𝖢𝗁𝖺𝗍𝖡𝗈𝗍 𝗁𝖺𝗏𝖾 𝖻𝖾𝖾𝗇 𝖽𝗂𝗌𝖺𝖻𝗅𝖾𝖽 𝖿𝗈𝗋 𝗍𝗁𝗂𝗌 𝖼𝗁𝖺𝗍.**")

@app.on_message(filters.group | filters.private & filters.reply , group=CHATBOT_GROUP)
@error
@save
async def handle_chatbot(client : Client , message : Message):

    if not message.from_user :
        return

    if not await is_chatbot_enabled(message.chat.id):
        return    

    # Only respond when the user is replying to the bot's own message.
    # (Previously this checked message.reply_to_message.from_user.id without
    # first confirming reply_to_message existed, which raised an
    # AttributeError - and therefore did nothing but spam the error log -
    # on every single non-reply message in a chatbot-enabled group.)
    if not message.reply_to_message or not message.reply_to_message.from_user:
        return

    if message.reply_to_message.from_user.id == config.BOT_ID:
        await client.send_chat_action(message.chat.id , action = ChatAction.TYPING)

        m = message.text

        # Fetch chatbot response, trying multiple free AI providers in order
        # (see Nobara/helper/ai_provider.py) so that if one provider is down
        # or rate-limited, we automatically fall back to the next one.
        bot_response, provider_used = await get_ai_response(m, system_prompt=CHATBOT_SYSTEM_PROMPT)

        if bot_response is None:
            # Notify the group about the issue and disable the chatbot
            await message.reply_text(
                "❌ 𝖢𝗁𝖺𝗍𝖻𝗈𝗍 𝗂𝗌 𝖿𝖺𝖼𝗂𝗇𝗀 𝗂𝗌𝗌𝗎𝖾𝗌 𝖺𝗇𝖽 𝗁𝖺𝗌 𝖻𝖾𝖾𝗇 𝖽𝗂𝗌𝖺𝖻𝗅𝖾𝖽 𝖿𝗈𝗋 𝗇𝗈𝗐. 𝖯𝗅𝖾𝖺𝗌𝖾 𝖼𝗈𝗇𝗍𝖺𝖼𝗍 𝗍𝗁𝖾 𝖻𝗈𝗍 𝗌𝗎𝗉𝗉𝗈𝗋𝗍."
            )
            await disable_chatbot(message.chat.id)
            return

        # Reply to the user's message
        await message.reply_text(bot_response)

__module__ = "𝖢𝗁𝖺𝗍𝖻𝗈𝗍"

__help__ = "✧ /𝖼𝗁𝖺𝗍𝖻𝗈𝗍 : 𝖴𝗌𝖾 𝖨𝗍 𝖳𝗈 𝖤𝗇𝖺𝖻𝗅𝖾 𝖮𝗋 𝖣𝗂𝗌𝖺𝖻𝗅𝖾 𝖢𝗁𝖺𝗍𝖻𝗈𝗍 𝖨𝗇 𝖸𝗈𝗎𝗋 𝖦𝗋𝗈𝗎𝗉."