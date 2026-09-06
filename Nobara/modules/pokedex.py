from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message
import aiohttp
import os
from config import config 
from Nobara import app
from Nobara.decorator.save import save 
from Nobara.decorator.errors import error

async def get_pokemon_info(name_or_id):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://sugoi-api.vercel.app/pokemon?name={name_or_id}") as response:
                if response.status == 200:
                    return await response.json()

            async with session.get(f"https://sugoi-api.vercel.app/pokemon?name={name_or_id}") as response:
                if response.status == 200:
                    return await response.json()

    except Exception as e:
        print(f"An error occurred: {str(e)}")

    return None

@app.on_message(filters.command("pokedex" , prefixes=config.COMMAND_PREFIXES))
@error
@save
async def pokedex(client: Client, message: Message):
    try:
        if message.command and len(message.command) > 1:
            name_or_id = message.command[1]
            pokemon_info = await get_pokemon_info(name_or_id)

            if pokemon_info:
                reply_message = (
                    f"\U0001F43E **𝖭𝖠𝖬𝖤:** {pokemon_info['name']}\n"
                    f"\u2022 **𝖨𝖣:** {pokemon_info['id']}\n"
                    f"\u2022 **𝖧𝖤𝖨𝖦𝖧𝖳:** {pokemon_info['height']}\n"
                    f"\u2022 **𝖶𝖤𝖨𝖦𝖧𝖳:** {pokemon_info['weight']}\n"
                )

                abilities = ", ".join(
                    ability["ability"]["name"] for ability in pokemon_info["abilities"]
                )
                reply_message += f"\u2022 **𝖠𝖡𝖨𝖫𝖨𝖳𝖨𝖤𝖲:** {abilities}\n"

                types = ", ".join(
                    type_info["type"]["name"] for type_info in pokemon_info["types"]
                )
                reply_message += f"\u2022 **𝖳𝖸𝖯𝖤𝖲:** {types}\n"

                image_url = f"https://img.pokemondb.net/artwork/large/{pokemon_info['name']}.jpg"

                # Create inline buttons
                keyboard = [
                    [
                        InlineKeyboardButton(text="\U0001F516 𝖲𝖳𝖠𝖳𝖲", callback_data="stats"),
                        InlineKeyboardButton(text="\u2694\ufe0f 𝖬𝖮𝖵𝖤𝖲", callback_data="moves"),
                    ]
                ]

                reply_markup = InlineKeyboardMarkup(keyboard)

                await message.reply_photo(
                    photo=image_url,
                    caption=reply_message,
                    reply_markup=reply_markup,
                )
            else:
                await message.reply_text("𝖯𝗈𝗄𝖾𝗆𝗈𝗇 𝗇𝗈𝗍 𝖿𝗈𝗎𝗇𝖽.")
        else:
            await message.reply_text("𝖯𝗅𝖾𝖺𝗌𝖾 𝗉𝗋𝗈𝗏𝗂𝖽𝖾 𝖺 𝖯𝗈𝗄𝖾𝗆𝗈𝗇 𝗇𝖺𝗆𝖾 𝗈𝗋 𝖨𝖣.")
    except Exception as e:
        await message.reply_text(f"𝖠𝗇 𝖾𝗋𝗋𝗈𝗋 𝗈𝖼𝖼𝗎𝗋𝗋𝖾𝖽: {str(e)}")

@app.on_callback_query(filters.regex("^(stats|moves)$"))
@error
async def callback_query_handler(client: Client, query: CallbackQuery):
    await query.answer()

    try:
        name = query.message.caption.split("\n")[0].split(": ")[1]
        pokemon_info = await get_pokemon_info(name)

        if pokemon_info:
            stats = "\n".join(
                f"{stat['stat']['name'].upper()}: {stat['base_stat']}"
                for stat in pokemon_info["stats"]
            )
            stats_message = f"\u2022 **𝖲𝖳𝖠𝖳𝖲:**\n{stats}\n"

            moves = ", ".join(
                move_info["move"]["name"] for move_info in pokemon_info["moves"]
            )
            moves_message = f"\u2022 **𝖬𝖮𝖵𝖤𝖲:** {moves}"

            if query.data == "stats":
                await query.message.reply_text(stats_message)
            elif query.data == "moves":
                if len(moves_message) > 1000:
                    # Save the moves message to a file
                    with open("moves.txt", "w") as file:
                        file.write(moves_message)
                    await query.message.reply_text(
                        "𝖳𝗁𝖾 𝗆𝗈𝗏𝖾𝗌 𝖾𝗑𝖼𝖾𝖾𝖽 𝟣𝟢𝟢𝟢 𝖼𝗁𝖺𝗋𝖺𝖼𝗍𝖾𝗋𝗌. 𝖲𝖾𝗇𝖽𝗂𝗇𝗀 𝖺𝗌 𝖺 𝖿𝗂𝗅𝖾.",
                        disable_web_page_preview=True,
                    )
                    # Send the file to the user
                    await query.message.reply_document(document=open("moves.txt", "rb"))
                    # Delete the file after sending
                    os.remove("moves.txt")
                else:
                    await query.message.reply_text(moves_message)
        else:
            await query.message.reply_text("𝖯𝗈𝗄𝖾𝗆𝗈𝗇 𝗇𝗈𝗍 𝖿𝗈𝗎𝗇𝖽.")
    except Exception as e:
        await query.message.reply_text(f"𝖠𝗇 𝖾𝗋𝗋𝗈𝗋 𝗈𝖼𝖼𝗎𝗋𝗋𝖾𝖽: {str(e)}")

__module__ = "𝖯𝗈𝗄𝖾𝖽𝖾𝗑"

__help__ = """𝖳𝗁𝗂𝗌 𝗆𝗈𝖽𝗎𝗅𝖾 𝖺𝗅𝗅𝗈𝗐𝗌 𝗎𝗌𝖾𝗋𝗌 𝗍𝗈 𝖿𝖾𝗍𝖼𝗁 𝖽𝖾𝗍𝖺𝗂𝗅𝖾𝖽 𝗂𝗇𝖿𝗈𝗋𝗆𝖺𝗍𝗂𝗈𝗇 𝖺𝖻𝗈𝗎𝗍 𝖯𝗈𝗄é𝗆𝗈𝗇, 𝗂𝗇𝖼𝗅𝗎𝖽𝗂𝗇𝗀 𝗌𝗍𝖺𝗍𝗌, 𝗆𝗈𝗏𝖾𝗌, 𝖺𝗇𝖽 𝗍𝗒𝗉𝖾𝗌.
 
**𝖠𝗏𝖺𝗂𝗅𝖺𝖻𝗅𝖾 𝖢𝗈𝗆𝗆𝖺𝗇𝖽𝗌:**
𝟣. `/𝗉𝗈𝗄𝖾𝖽𝖾𝗑 <𝗇𝖺𝗆𝖾_𝗈𝗋_𝗂𝖽>` - 𝖲𝖾𝖺𝗋𝖼𝗁 𝖿𝗈𝗋 𝖺 𝖯𝗈𝗄é𝗆𝗈𝗇 𝖻𝗒 𝗂𝗍𝗌 𝗇𝖺𝗆𝖾 𝗈𝗋 𝖨𝖣.
    𝖤𝗑𝖺𝗆𝗉𝗅𝖾: `/𝗉𝗈𝗄𝖾𝖽𝖾𝗑 𝗉𝗂𝗄𝖺𝖼𝗁𝗎`

**𝖨𝗇𝗅𝗂𝗇𝖾 𝖥𝖾𝖺𝗍𝗎𝗋𝖾𝗌:**
- **\U0001f516 𝖲𝖳𝖠𝖳𝖲**: 𝖵𝗂𝖾𝗐 𝗍𝗁𝖾 𝗌𝗍𝖺𝗍𝗌 𝗈𝖿 𝗍𝗁𝖾 𝖯𝗈𝗄é𝗆𝗈𝗇.
 - **\u2694\ufe0f 𝖬𝖮𝖵𝖤𝖲**: 𝖵𝗂𝖾𝗐 𝗍𝗁𝖾 𝗆𝗈𝗏𝖾𝗌 𝗈𝖿 𝗍𝗁𝖾 𝖯𝗈𝗄é𝗆𝗈𝗇.
 
**𝖭𝗈𝗍𝖾:**
- 𝖸𝗈𝗎 𝖼𝖺𝗇 𝗌𝖾𝖺𝗋𝖼𝗁 𝗎𝗌𝗂𝗇𝗀 𝖾𝗂𝗍𝗁𝖾𝗋 𝗍𝗁𝖾 𝖯𝗈𝗄é𝗆𝗈𝗇'𝗌 𝗇𝖺𝗆𝖾 (𝖾.𝗀., "𝗉𝗂𝗄𝖺𝖼𝗁𝗎") 𝗈𝗋 𝗂𝗍𝗌 𝖨𝖣 (𝖾.𝗀., "𝟤𝟧").
 - 𝖨𝖿 𝗍𝗁𝖾 𝖯𝗈𝗄é𝗆𝗈𝗇 𝗁𝖺𝗌 𝖺 𝗅𝖺𝗋𝗀𝖾 𝗅𝗂𝗌𝗍 𝗈𝖿 𝗆𝗈𝗏𝖾𝗌, 𝗍𝗁𝖾𝗒 𝗐𝗂𝗅𝗅 𝖻𝖾 𝗌𝖾𝗇𝗍 𝖺𝗌 𝖺 𝖿𝗂𝗅𝖾.
 """
