from pyrogram import Client, filters
from pyrogram.types import Message
from Nobara import app
from config import config
from Nobara.decorator.save import save
from Nobara.decorator.errors import error
from Nobara.helper.ai_provider import get_ai_response

ASK_SYSTEM_PROMPT = "You are a helpful, concise assistant."


@app.on_message(filters.command(["askgpt", "askgemini", "ask"], prefixes=config.COMMAND_PREFIXES))
@error
@save
async def ask_ai(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply("𝖴𝗌𝖺𝗀𝖾: /𝖺𝗌𝗄 <𝗉𝗋𝗈𝗆𝗉𝗍>")
        return

    prompt = message.text.split(maxsplit=1)[1]
    processing_message = await message.reply("💭 𝖳𝗁𝗂𝗇𝗄𝗂𝗇𝗀... 𝖯𝗅𝖾𝖺𝗌𝖾 𝗐𝖺𝗂𝗍")

    # Tries every configured free AI provider (Groq, OpenRouter, Cerebras,
    # Gemini, Together, HuggingFace, DeepSeek, ...) in priority order and
    # automatically falls back to the next one if a provider fails/limits out.
    response_text, provider_used = await get_ai_response(prompt, system_prompt=ASK_SYSTEM_PROMPT)

    if response_text:
        await processing_message.edit(response_text)
    else:
        await processing_message.edit(
            "𝖲𝗈𝗋𝗋𝗒, 𝖺𝗅𝗅 𝖠𝖨 𝗉𝗋𝗈𝗏𝗂𝖽𝖾𝗋𝗌 𝖺𝗋𝖾 𝖼𝗎𝗋𝗋𝖾𝗇𝗍𝗅𝗒 𝗎𝗇𝖺𝗏𝖺𝗂𝗅𝖺𝖻𝗅𝖾. 𝖯𝗅𝖾𝖺𝗌𝖾 𝗍𝗋𝗒 𝖺𝗀𝖺𝗂𝗇 𝗂𝗇 𝖺 𝖿𝖾𝗐 𝗆𝗂𝗇𝗎𝗍𝖾𝗌."
        )


__module__ = "𝖠𝗌𝗄"
__help__ = """✧ `/ask <prompt>` : 𝖠𝗌𝗄 𝗍𝗁𝖾 𝖠𝖨 𝖺𝗇𝗒𝗍𝗁𝗂𝗇𝗀. 𝖠𝗎𝗍𝗈𝗆𝖺𝗍𝗂𝖼𝖺𝗅𝗅𝗒 𝗍𝗋𝗂𝖾𝗌 𝗆𝗎𝗅𝗍𝗂𝗉𝗅𝖾 𝖿𝗋𝖾𝖾 𝖠𝖨 𝗉𝗋𝗈𝗏𝗂𝖽𝖾𝗋𝗌 𝖺𝗇𝖽 𝖿𝖺𝗅𝗅𝗌 𝖻𝖺𝖼𝗄 𝖺𝗎𝗍𝗈𝗆𝖺𝗍𝗂𝖼𝖺𝗅𝗅𝗒 𝗂𝖿 𝗈𝗇𝖾 𝗂𝗌 𝖽𝗈𝗐𝗇.
✧ `/askgpt <prompt>` , `/askgemini <prompt>` : 𝖠𝗅𝗂𝖺𝗌𝖾𝗌 𝖿𝗈𝗋 `/ask`."""
