import traceback
from telegram import Update
from telegram.ext import CallbackContext
from telegram.error import (
    BadRequest, Forbidden, NetworkError, TelegramError, 
    TimedOut, ChatMigrated, InvalidToken
)
from Nobara import log , ptb

from config import config

async def error_handler(update: Update, context: CallbackContext) -> None:
    """Asynchronous error handler for PTB."""
    error = context.error  # Capture the raised error
    try:
        # Attempt to log details of the error
        raise error
    except TimedOut:
        log.warning("Request timed out. Retrying...")
    except BadRequest as e:
        await handle_specific_error(context, update, "BadRequest", e)
    except Forbidden as e:
        await handle_specific_error(context, update, "Forbidden", e)
    except NetworkError as e:
        await handle_specific_error(context, update, "NetworkError", e)
    except ChatMigrated as e:
        await handle_specific_error(context, update, "ChatMigrated", e)
    except InvalidToken as e:
        await handle_specific_error(context, update, "InvalidToken", e)
    except TelegramError as e:
        await handle_specific_error(context, update, "TelegramError", e)
    except Exception as e:
        log.exception(f"An unexpected error occurred: {e}")
        await log_error(context, update, f"Unexpected Error: `{type(e).__name__}`\nDetails: `{str(e)}`")

async def handle_specific_error(context: CallbackContext, update: Update, error_type: str, error: Exception) -> None:
    """Handle specific Telegram errors and log them."""
    log.error(f"{error_type} error: {error}")
    await log_error(context, update, f"`{error_type}`: {str(error)}")

import html

async def log_error(context: CallbackContext, update: Update, error_message: str) -> None:
    """Log error details to a predefined error log channel."""
    log_text = (
        "<b>←←←𝖤𝗋𝗋𝗈𝗋 𝖫𝗈𝗀→→→</b>\n\n"
        f"<b>𝖤𝗋𝗋𝗈𝗋:</b>\n<pre>{html.escape(error_message)}</pre>\n"
        f"<b>𝖤𝗋𝗋𝗈𝗋 𝖳𝗒𝗉𝖾:</b> <code>{html.escape(type(context.error).__name__)}</code>\n\n"
    )

    # Add details about the update if available
    if update:
        chat = update.effective_chat
        user = update.effective_user
        message = update.effective_message
        if chat:
            log_text += (
                "<b>𝖢𝗁𝖺𝗍 𝖨𝗇𝖿𝗈𝗋𝗆𝖺𝗍𝗂𝗈𝗇 :</b>\n"
                f"- <b>𝖢𝗁𝖺𝗍 𝖭𝖺𝗆𝖾 :</b> <code>{html.escape(chat.title or '𝖯𝗋𝗂𝗏𝖺𝗍𝖾 𝖢𝗁𝖺𝗍')}</code>\n"
                f"- <b>𝖢𝗁𝖺𝗍 𝖨𝖣 :</b> <code>{chat.id}</code>\n\n"
            )
        if user:
            log_text += (
                "<b>𝖴𝗌𝖾𝗋 𝖨𝗇𝖿𝗈𝗋𝗆𝖺𝗍𝗂𝗈𝗇 :</b>\n"
                f"- <b>𝖴𝗌𝖾𝗋 𝖭𝖺𝗆𝖾 :</b> <code>{html.escape(user.first_name)}</code>\n"
                f"- <b>𝖴𝗌𝖾𝗋 𝖨𝖣 :</b> <code>{user.id}</code>\n\n"
            )
        if message:
            log_text += (
                "<b>𝖬𝖾𝗌𝗌𝖺𝗀𝖾 :</b>\n"
                f"<pre>{html.escape(message.text or '𝖭𝗈 𝗍𝖾𝗑𝗍 𝖼𝗈𝗇𝗍𝖾𝗇𝗍')}</pre>\n\n"
            )
    else:
        log_text += "<b>𝖴𝗉𝖽𝖺𝗍𝖾 𝖳𝗒𝗉𝖾 :</b> <code>𝖴𝗇𝗄𝗇𝗈𝗐𝗇</code>\n\n"

    # Include traceback details if available
    traceback_text = ''.join(traceback.format_exception(None, context.error, context.error.__traceback__))
    log_text += "<b>𝖳𝗋𝖺𝖼𝖾𝖻𝖺𝖼𝗄:</b>\n<pre>" + html.escape(traceback_text) + "</pre>\n"

    # Attempt to send the error log to the configured error log channel
    try:
        await context.bot.send_message(
            chat_id=config.ERROR_LOG_CHANNEL, 
            text=log_text, 
            parse_mode="HTML"
        )
    except Exception as log_exception:
        log.error(f"Failed to send error log to the channel: {log_exception}")


ptb.add_error_handler(error_handler)