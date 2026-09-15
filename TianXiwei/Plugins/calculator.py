import re
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from TianXiwei import app
from config import config
from TianXiwei.Extra.save import save
from TianXiwei.Extra.errors import error




def get_calc_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("(", callback_data="calc_("),
            InlineKeyboardButton(")", callback_data="calc_)"),
            InlineKeyboardButton("%", callback_data="calc_%"),
            InlineKeyboardButton("C", callback_data="calc_C"),
        ],
        [
            InlineKeyboardButton("7", callback_data="calc_7"),
            InlineKeyboardButton("8", callback_data="calc_8"),
            InlineKeyboardButton("9", callback_data="calc_9"),
            InlineKeyboardButton("÷", callback_data="calc_/"),
        ],
        [
            InlineKeyboardButton("4", callback_data="calc_4"),
            InlineKeyboardButton("5", callback_data="calc_5"),
            InlineKeyboardButton("6", callback_data="calc_6"),
            InlineKeyboardButton("×", callback_data="calc_*"),
        ],
        [
            InlineKeyboardButton("1", callback_data="calc_1"),
            InlineKeyboardButton("2", callback_data="calc_2"),
            InlineKeyboardButton("3", callback_data="calc_3"),
            InlineKeyboardButton("-", callback_data="calc_-"),
        ],
        [
            InlineKeyboardButton(".", callback_data="calc_."),
            InlineKeyboardButton("0", callback_data="calc_0"),
            InlineKeyboardButton("⌫", callback_data="calc_DEL"),
            InlineKeyboardButton("+", callback_data="calc_+"),
        ],
        [
            InlineKeyboardButton("=", callback_data="calc_=")
        ]
    ])




@app.on_message(filters.command(["calculate", "calc"], prefixes=config.COMMAND_PREFIXES))
@error
@save
async def direct_calc(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply("𝖯𝗅𝖾𝖺𝗌𝖾 𝗉𝗋𝗈𝗏𝗂𝖽𝖾 𝖺𝗇 𝖾𝗑𝗉𝗋𝖾𝗌𝗌𝗂𝗈𝗇.\n𝖤𝗑𝖺𝗆𝗉𝗅𝖾: `/𝖼𝖺𝗅𝖼𝗎𝗅𝖺𝗍𝖾 𝟩𝟥𝟨+𝟪𝟣𝟪`")
        return
    
    expr = "".join(message.command[1:])
    

    clean_expr = re.sub(r'[^0-9\+\-\*\/\.\(\)\%]', '', expr)
    
    try:
        if not clean_expr:
            raise ValueError
        
        result = eval(clean_expr)
        

        if isinstance(result, float) and result.is_integer():
            result = int(result)
            
        await message.reply(f"**📝 𝖤𝗑𝗉𝗋𝖾𝗌𝗌𝗂𝗈𝗇:** `{clean_expr}`\n**✅ 𝖱𝖾𝗌𝗎𝗅𝗍:** `{result}`")
    except ZeroDivisionError:
        await message.reply("**❌ 𝖤𝗋𝗋𝗈𝗋:** `Division by zero is not allowed.`")
    except Exception:
        await message.reply("**❌ 𝖨𝗇𝗏𝖺𝗅𝗂𝖽 𝖤𝗑𝗉𝗋𝖾𝗌𝗌𝗂𝗈𝗇!**")




@app.on_message(filters.command("calculator", prefixes=config.COMMAND_PREFIXES))
@error
@save
async def interactive_calc(client: Client, message: Message):
    text = "🧮 **𝖨𝗇𝗍𝖾𝗋𝖺𝖼𝗍𝗂𝗏𝖾 𝖢𝖺𝗅𝖼𝗎𝗅𝖺𝗍𝗈𝗋**\n\n**𝖣𝗂𝗌𝗉𝗅𝖺𝗒:**\n`0`"
    await message.reply(text, reply_markup=get_calc_keyboard())




@app.on_callback_query(filters.regex(r"^calc_"))
@error
async def calc_callback(client: Client, query: CallbackQuery):
    button_data = query.data.split("_")[1]
    

    message_text = query.message.text
    lines = message_text.split("\n")
    current_expr = lines[-1].strip()
    

    if current_expr in ["0", "Error", "Error (Div by 0)"]:
        current_expr = ""
        

    if "=" in current_expr:
        result_value = current_expr.split("=")[-1].strip()
        if button_data in ["+", "-", "*", "/", "%"]:

            current_expr = result_value
        elif button_data in ["C", "DEL", "="]:
            current_expr = result_value
        else:

            current_expr = ""


    if button_data == "C":
        current_expr = "0"
        
    elif button_data == "DEL":
        current_expr = current_expr[:-1] if len(current_expr) > 1 else "0"
        
    elif button_data == "=":
        if current_expr == "" or current_expr == "0":
            current_expr = "0"
        else:
            try:

                clean_expr = re.sub(r'[^0-9\+\-\*\/\.\(\)\%]', '', current_expr)
                res = eval(clean_expr)
                

                if isinstance(res, float) and res.is_integer():
                    res = int(res)

                current_expr = f"{current_expr} = {res}"
            except ZeroDivisionError:
                current_expr = "Error (Div by 0)"
            except Exception:
                current_expr = "Error"
                
    else:

        current_expr += button_data
        

    if current_expr == "":
        current_expr = "0"
        
    new_text = f"🧮 **𝖨𝗇𝗍𝖾𝗋𝖺𝖼𝗍𝗂𝗏𝖾 𝖢𝖺𝗅𝖼𝗎𝗅𝖺𝗍𝗈𝗋**\n\n**𝖣𝗂𝗌𝗉𝗅𝖺𝗒:**\n`{current_expr}`"
    

    if new_text != message_text:
        await query.message.edit_text(new_text, reply_markup=get_calc_keyboard())
        
    await query.answer()

__module__ = "𝖢𝖺𝗅𝖼𝗎𝗅𝖺𝗍𝗈𝗋"

__help__ = """**𝖢𝖺𝗅𝖼𝗎𝗅𝖺𝗍𝗈𝗋 𝖥𝖾𝖺𝗍𝗎𝗋𝖾𝗌:**

- **𝖢𝗈𝗆𝗆𝖺𝗇𝖽𝗌:**

 ✧ `/𝖼𝖺𝗅𝖼𝗎𝗅𝖺𝗍𝗈𝗋` : 𝖮𝗉𝖾𝗇𝗌 𝖺𝗇 𝗂𝗇𝗍𝖾𝗋𝖺𝖼𝗍𝗂𝗏𝖾 𝖼𝖺𝗅𝖼𝗎𝗅𝖺𝗍𝗈𝗋 𝗐𝗂𝗍𝗁 𝖻𝗎𝗍𝗍𝗈𝗇𝗌.
 ✧ `/𝖼𝖺𝗅𝖼𝗎𝗅𝖺𝗍𝖾 <𝖾𝗑𝗉𝗋𝖾𝗌𝗌𝗂𝗈𝗇>` : 𝖣𝗂𝗋𝖾𝖼𝗍𝗅𝗒 𝖼𝖺𝗅𝖼𝗎𝗅𝖺𝗍𝖾𝗌 𝖺 𝗆𝖺𝗍𝗁 𝗉𝗋𝗈𝖻𝗅𝖾𝗆 (𝖠𝗅𝗂𝖺𝗌: `/𝖼𝖺𝗅𝖼`).
 
- **𝖤𝗑𝖺𝗆𝗉𝗅𝖾𝗌:**
  ✧ `/𝖼𝖺𝗅𝖼𝗎𝗅𝖺𝗍𝖾 𝟩𝟥𝟨+𝟪𝟣𝟪`
  ✧ `/𝖼𝖺𝗅𝖼𝗎𝗅𝖺𝗍𝖾 (𝟧𝟢*𝟤)/𝟧`
 """
