import aiohttp
from pyrogram import Client, filters
from pyrogram.types import Message
from Nobara import app
from config import config
from Nobara.decorator.errors import error
from Nobara.decorator.save import save

# Free and open exchange rate API (No key required)
API_URL = "https://open.er-api.com/v6/latest/{}"

async def fetch_exchange_rates(base_currency: str):
    """Fetch exchange rates from the API."""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(API_URL.format(base_currency), timeout=10) as response:
                if response.status == 200:
                    return await response.json()
                return None
        except Exception:
            return None

@app.on_message(filters.command("currency", prefixes=config.COMMAND_PREFIXES))
@error
@save
async def currency_converter(client: Client, message: Message):
    args = message.command[1:]
    
    # If no arguments provided
    if not args:
        return await message.reply_text(
            "⚠️ **𝖲𝗒𝗇𝗍𝖺𝗑 𝖤𝗋𝗋𝗈𝗋:**\n"
            "𝖯𝗅𝖾𝖺𝗌𝖾 𝗉𝗋𝗈𝗏𝗂𝖽𝖾 𝗍𝗁𝖾 𝖺𝗆𝗈𝗎𝗇𝗍 𝖺𝗇𝖽 𝖼𝗎𝗋𝗋𝖾𝗇𝖼𝗂𝖾𝗌.\n\n"
            "📌 `𝖴𝗌𝖺𝗀𝖾: /currency [amount] [from] [to]`\n"
            "📌 `𝖴𝗌𝖺𝗀𝖾: /currency list` (𝖳𝗈 𝗌𝖾𝖾 𝖺𝗏𝖺𝗂𝗅𝖺𝖻𝗅𝖾 𝖼𝗎𝗋𝗋𝖾𝗇𝖼𝗂𝖾𝗌)"
        )
        
    # Handling '/currency list'
    if args[0].lower() == "list":
        status_msg = await message.reply_text("🔎 **𝖥𝖾𝗍𝖼𝗁𝗂𝗇𝗀 𝖺𝗏𝖺𝗂𝗅𝖺𝖻𝗅𝖾 𝖼𝗎𝗋𝗋𝖾𝗇𝖼𝗂𝖾𝗌...**")
        data = await fetch_exchange_rates("USD")
        
        if not data or data.get("result") != "success":
            return await status_msg.edit_text("❌ **𝖤𝗋𝗋𝗈𝗋:** 𝖢𝗈𝗎𝗅𝖽 𝗇𝗈𝗍 𝖿𝖾𝗍𝖼𝗁 𝖼𝗎𝗋𝗋𝖾𝗇𝖼𝗒 𝗅𝗂𝗌𝗍 𝖺𝗍 𝗍𝗁𝗂𝗌 𝗆𝗈𝗆𝖾𝗇𝗍.")
            
        currencies = list(data["rates"].keys())
        # Format the list nicely
        formatted_list = ", ".join(f"`{c}`" for c in currencies)
        
        text = f"**🌍 𝖠𝗏𝖺𝗂𝗅𝖺𝖻𝗅𝖾 𝖢𝗎𝗋𝗋𝖾𝗇𝖼𝗂𝖾𝗌 ({len(currencies)}):**\n\n{formatted_list}"
        
        if len(text) > 4096:
            text = text[:4090] + "..."
            
        return await status_msg.edit_text(text)
        
    # Ensure correct format for conversion
    if len(args) != 3:
        return await message.reply_text(
            "⚠️ **𝖨𝗇𝗏𝖺𝗅𝗂𝖽 𝖥𝗈𝗋𝗆𝖺𝗍!**\n"
            "**𝖤𝗑𝖺𝗆𝗉𝗅𝖾:** `/currency 100 USD EUR`"
        )
        
    try:
        # Support commas in numbers (e.g., 1,000)
        amount_str = args[0].replace(",", "")
        amount = float(amount_str)
    except ValueError:
        return await message.reply_text("❌ **𝖨𝗇𝗏𝖺𝗅𝗂𝖽 𝖠𝗆𝗈𝗎𝗇𝗍!** 𝖯𝗅𝖾𝖺𝗌𝖾 𝖾𝗇𝗍𝖾𝗋 𝖺 𝗏𝖺𝗅𝗂𝖽 𝗇𝗎𝗆𝖻𝖾𝗋.")
        
    from_curr = args[1].upper()
    to_curr = args[2].upper()
    
    status_msg = await message.reply_text("🔄 **𝖢𝗈𝗇𝗏𝖾𝗋𝗍𝗂𝗇𝗀 𝖢𝗎𝗋𝗋𝖾𝗇𝖼𝗒...**")
    
    # Fetch real-time rates
    data = await fetch_exchange_rates(from_curr)
    
    if not data or data.get("result") != "success":
        return await status_msg.edit_text(f"❌ **𝖨𝗇𝗏𝖺𝗅𝗂𝖽 𝖻𝖺𝗌𝖾 𝖼𝗎𝗋𝗋𝖾𝗇𝖼𝗒 𝗈𝗋 𝖠𝖯𝖨 𝖽𝗈𝗐𝗇:** `{from_curr}`")
        
    rates = data.get("rates", {})
    
    if to_curr not in rates:
        return await status_msg.edit_text(f"❌ **𝖨𝗇𝗏𝖺𝗅𝗂𝖽 𝗍𝖺𝗋𝗀𝖾𝗍 𝖼𝗎𝗋𝗋𝖾𝗇𝖼𝗒:** `{to_curr}`")
        
    rate = rates[to_curr]
    result = amount * rate
    
    text = (
        f"💱 **𝖢𝗎𝗋𝗋𝖾𝗇𝖼𝗒 𝖢𝗈𝗇𝗏𝖾𝗋𝗌𝗂𝗈𝗇**\n\n"
        f"💸 **𝖠𝗆𝗈𝗎𝗇𝗍:** `{amount:,.2f}` **{from_curr}**\n"
        f"🔄 **𝖢𝗈𝗇𝗏𝖾𝗋𝗍𝖾𝖽:** `{result:,.2f}` **{to_curr}**\n\n"
        f"📊 **𝖱𝖺𝗍𝖾:** `1 {from_curr} = {rate} {to_curr}`"
    )
    
    await status_msg.edit_text(text)


__module__ = "𝖢𝗎𝗋𝗋𝖾𝗇𝖼𝗒"

__help__ = """**𝖢𝗎𝗋𝗋𝖾𝗇𝖼𝗒 𝖢𝗈𝗇𝗏𝖾𝗋𝗍𝖾𝗋:**

𝖢𝗈𝗇𝗏𝖾𝗋𝗍 𝖻𝖾𝗍𝗐𝖾𝖾𝗇 𝖽𝗂𝖿𝖿𝖾𝗋𝖾𝗇𝗍 𝖼𝗎𝗋𝗋𝖾𝗇𝖼𝗂𝖾𝗌 𝗐𝗂𝗍𝗁 𝗋𝖾𝖺𝗅-𝗍𝗂𝗆𝖾 𝖾𝗑𝖼𝗁𝖺𝗇𝗀𝖾 𝗋𝖺𝗍𝖾𝗌.
 
- **𝖢𝗈𝗆𝗆𝖺𝗇𝖽𝗌:**
 ✧ `/𝖼𝗎𝗋𝗋𝖾𝗇𝖼𝗒 [𝖺𝗆𝗈𝗎𝗇𝗍] [𝖿𝗋𝗈𝗆] [𝗍𝗈]` : 𝖢𝗈𝗇𝗏𝖾𝗋𝗍 𝖼𝗎𝗋𝗋𝖾𝗇𝖼𝗒
 ✧ `/𝖼𝗎𝗋𝗋𝖾𝗇𝖼𝗒 𝗅𝗂𝗌𝗍` : 𝖲𝗁𝗈𝗐 𝖺𝗏𝖺𝗂𝗅𝖺𝖻𝗅𝖾 𝖼𝗎𝗋𝗋𝖾𝗇𝖼𝗂𝖾𝗌

- **𝖤𝗑𝖺𝗆𝗉𝗅𝖾𝗌:**
 ✧ `/𝖼𝗎𝗋𝗋𝖾𝗇𝖼𝗒 𝟣𝟢𝟢 𝖴𝖲𝖣 𝖤𝖴𝖱` - 𝖢𝗈𝗇𝗏𝖾𝗋𝗍 𝟣𝟢𝟢 𝖴𝖲 𝖣𝗈𝗅𝗅𝖺𝗋𝗌 𝗍𝗈 𝖤𝗎𝗋𝗈𝗌
 ✧ `/𝖼𝗎𝗋𝗋𝖾𝗇𝖼𝗒 𝟧𝟢 𝖩𝖯𝖸 𝖨𝖭𝖱` - 𝖢𝗈𝗇𝗏𝖾𝗋𝗍 𝟧𝟢 𝖩𝖺𝗉𝖺𝗇𝖾𝗌𝖾 𝖸𝖾𝗇 𝗍𝗈 𝖨𝗇𝖽𝗂𝖺𝗇 𝖱𝗎𝗉𝖾𝖾𝗌
"""
