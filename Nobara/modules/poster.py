import aiohttp
import urllib.parse
import logging
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from pyrogram.enums import ParseMode

from Nobara import app
from config import config
from Nobara.decorator.save import save 
from Nobara.decorator.errors import error

logger = logging.getLogger(__name__)

# TMDB API Key
TMDB_API_KEY = "4b061466449ce519d5884948a9671e63"

# Helper function for async API calls
async def fetch_json(url):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
    except Exception as e:
        logger.error(f"API Fetch Error: {e}")
    return None


@app.on_message(filters.command("poster", prefixes=config.COMMAND_PREFIXES))
@error
@save
async def get_poster_menu(client, message):
    if len(message.command) == 1:
        return await message.reply_text("<b>⚠️ 𝖯𝗅𝖾𝖺𝗌𝖾 𝗉𝗋𝗈𝗏𝗂𝖽𝖾 𝖺 𝗆𝗈𝗏𝗂𝖾 𝗈𝗋 𝖳𝖵 𝗌𝗁𝗈𝗐 𝗇𝖺𝗆𝖾.\n\n📌 𝖤𝗑𝖺𝗆𝗉𝗅𝖾:</b> `/poster naruto`", parse_mode=ParseMode.HTML)

    query = " ".join(message.command[1:])
    # Short query for callback data (max 20 chars to fit 64-byte limit)
    short_query = query[:20].replace(" ", "-").replace("_", "-")
    safe_query = urllib.parse.quote_plus(query)
    
    msg = await message.reply_text(f"<b>🔎 𝖲𝖾𝖺𝗋𝖼𝗁𝗂𝗇𝗀 𝖳𝖬𝖣𝖡 𝖿𝗈𝗋</b> <code>{query}</code> <b>...</b>", parse_mode=ParseMode.HTML)

    try:
        search_url = f"https://api.themoviedb.org/3/search/multi?api_key={TMDB_API_KEY}&query={safe_query}"
        search_results = await fetch_json(search_url)

        if not search_results or not search_results.get("results"):
            return await msg.edit_text("<b>❌ 𝖭𝗈 𝗋𝖾𝗌𝗎𝗅𝗍𝗌 𝖿𝗈𝗎𝗇𝖽 𝖿𝗈𝗋 𝗒𝗈𝗎𝗋 𝗌𝖾𝖺𝗋𝖼𝗁!</b>", parse_mode=ParseMode.HTML)

        valid_results = [item for item in search_results["results"] if item["media_type"] in ["movie", "tv"]]
        
        if not valid_results:
             return await msg.edit_text("<b>❌ 𝖭𝗈 𝗆𝗈𝗏𝗂𝖾 𝗈𝗋 𝖳𝖵 𝗌𝗁𝗈𝗐 𝖿𝗈𝗎𝗇𝖽!</b>", parse_mode=ParseMode.HTML)

        buttons = []
        for item in valid_results[:10]:
            tmdb_id = item["id"]
            media_type = item["media_type"]
            title = item.get("name") or item.get("title", "𝖴𝗇𝗄𝗇𝗈𝗐𝗇")
            
            date_key = "first_air_date" if media_type == "tv" else "release_date"
            year = item.get(date_key, "")[:4] if item.get(date_key) else "𝖭/𝖠"
            
            m_icon = "📺" if media_type == "tv" else "🎬"
            m_type_str = "𝖳𝖵" if media_type == "tv" else "𝖬𝗈𝗏𝗂𝖾"
            btn_text = f"{m_icon} {title} ({year}) [{m_type_str}]"
            
            # Pass short_query to support the Back to Search button
            buttons.append([InlineKeyboardButton(btn_text, callback_data=f"p_menu_{media_type}_{tmdb_id}_{short_query}")])
            
        buttons.append([InlineKeyboardButton("❌ 𝖢𝗅𝗈𝗌𝖾", callback_data="poster_close_data")])

        await msg.edit_text(
            text=f"<b>✅ 𝖬𝗎𝗅𝗍𝗂𝗉𝗅𝖾 𝗋𝖾𝗌𝗎𝗅𝗍𝗌 𝖿𝗈𝗎𝗇𝖽 𝖿𝗈𝗋</b> <code>{query}</code>\n\n<b>👇 𝖲𝖾𝗅𝖾𝖼𝗍 𝗒𝗈𝗎𝗋 𝗆𝗈𝗏𝗂𝖾 𝗈𝗋 𝗌𝖾𝗋𝗂𝖾𝗌 𝖿𝗋𝗈𝗆 𝖻𝖾𝗅𝗈𝗐:</b>",
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode=ParseMode.HTML
        )

    except Exception as e:
        logger.error(e)
        await msg.edit_text(f"<b>⚠️ 𝖠𝗇 𝖾𝗋𝗋𝗈𝗋 𝗈𝖼𝖼𝗎𝗋𝗋𝖾𝖽:</b> `{e}`", parse_mode=ParseMode.HTML)


# Handler for "Back to Search Results" button
@app.on_callback_query(filters.regex(r"^p_search_"))
@error
async def handle_back_to_search(client, callback_query):
    short_query = callback_query.data.replace("p_search_", "").replace("-", " ")
    await callback_query.answer("🔎 𝖫𝗈𝖺𝖽𝗂𝗇𝗀 𝗌𝖾𝖺𝗋𝖼𝗁 𝗋𝖾𝗌𝗎𝗅𝗍𝗌...")

    try:
        safe_query = urllib.parse.quote_plus(short_query)
        search_url = f"https://api.themoviedb.org/3/search/multi?api_key={TMDB_API_KEY}&query={safe_query}"
        search_results = await fetch_json(search_url)

        if not search_results or not search_results.get("results"):
            return await callback_query.answer("❌ 𝖭𝗈 𝗋𝖾𝗌𝗎𝗅𝗍𝗌 𝖿𝗈𝗎𝗇𝖽 𝖿𝗈𝗋 𝗒𝗈𝗎𝗋 𝗌𝖾𝖺𝗋𝖼𝗁!", show_alert=True)

        valid_results = [item for item in search_results["results"] if item["media_type"] in ["movie", "tv"]]
        
        if not valid_results:
             return await callback_query.answer("❌ 𝖭𝗈 𝗆𝗈𝗏𝗂𝖾 𝗈𝗋 𝖳𝖵 𝗌𝗁𝗈𝗐 𝖿𝗈𝗎𝗇𝖽!", show_alert=True)

        buttons = []
        cb_query_str = callback_query.data.replace("p_search_", "")
        for item in valid_results[:10]:
            tmdb_id = item["id"]
            media_type = item["media_type"]
            title = item.get("name") or item.get("title", "𝖴𝗇𝗄𝗇𝗈𝗐𝗇")
            
            date_key = "first_air_date" if media_type == "tv" else "release_date"
            year = item.get(date_key, "")[:4] if item.get(date_key) else "𝖭/𝖠"
            
            m_icon = "📺" if media_type == "tv" else "🎬"
            m_type_str = "𝖳𝖵" if media_type == "tv" else "𝖬𝗈𝗏𝗂𝖾"
            btn_text = f"{m_icon} {title} ({year}) [{m_type_str}]"
            
            buttons.append([InlineKeyboardButton(btn_text, callback_data=f"p_menu_{media_type}_{tmdb_id}_{cb_query_str}")])
            
        buttons.append([InlineKeyboardButton("❌ 𝖢𝗅𝗈𝗌𝖾", callback_data="poster_close_data")])

        text = f"<b>✅ 𝖬𝗎𝗅𝗍𝗂𝗉𝗅𝖾 𝗋𝖾𝗌𝗎𝗅𝗍𝗌 𝖿𝗈𝗎𝗇𝖽 𝖿𝗈𝗋</b> <code>{short_query}</code>\n\n<b>👇 𝖲𝖾𝗅𝖾𝖼𝗍 𝗒𝗈𝗎𝗋 𝗆𝗈𝗏𝗂𝖾 𝗈𝗋 𝗌𝖾𝗋𝗂𝖾𝗌 𝖿𝗋𝗈𝗆 𝖻𝖾𝗅𝗈𝗐:</b>"
        
        if callback_query.message.photo:
            await client.send_message(
                chat_id=callback_query.message.chat.id,
                text=text,
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode=ParseMode.HTML
            )
            try:
                await callback_query.message.delete()
            except Exception:
                pass
        else:
            await callback_query.message.edit_text(
                text=text, 
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode=ParseMode.HTML
            )

    except Exception as e:
        logger.error(e)
        await callback_query.answer(f"⚠️ 𝖠𝗇 𝖾𝗋𝗋𝗈𝗋 𝗈𝖼𝖼𝗎𝗋𝗋𝖾𝖽!", show_alert=True)


# Main Menu for Poster Categories
@app.on_callback_query(filters.regex(r"^p_menu_"))
@error
async def show_poster_categories(client, callback_query):
    data = callback_query.data.split("_")
    media_type = data[2]
    tmdb_id = data[3]
    short_query = data[4] if len(data) > 4 else ""
    
    await callback_query.answer("𝖦𝖾𝗇𝖾𝗋𝖺𝗍𝗂𝗇𝗀 𝗆𝖾𝗇𝗎...")

    try:
        details_url = f"https://api.themoviedb.org/3/{media_type}/{tmdb_id}?api_key={TMDB_API_KEY}"
        img_url = f"https://api.themoviedb.org/3/{media_type}/{tmdb_id}/images?api_key={TMDB_API_KEY}"
        
        details = await fetch_json(details_url)
        images = await fetch_json(img_url)

        if not details or not images:
            return await callback_query.answer("⚠️ 𝖥𝖺𝗂𝗅𝖾𝖽 𝗍𝗈 𝖿𝖾𝗍𝖼𝗁 𝖽𝖾𝗍𝖺𝗂𝗅𝗌!", show_alert=True)

        title = details.get("name") or details.get("title", "𝖴𝗇𝗄𝗇𝗈𝗐𝗇 𝖳𝗂𝗍𝗅𝖾")
        date_key = "first_air_date" if media_type == "tv" else "release_date"
        year = details.get(date_key, "")[:4] if details.get(date_key) else "𝖭/𝖠"

        backdrops = images.get("backdrops", [])
        posters = images.get("posters", [])
        logos = images.get("logos", [])

        # Filter: Landscape (with language/text) vs Clean Landscape (No language/textless)
        landscape = [img for img in backdrops if img.get("iso_639_1") not in (None, "xx")]
        # Sort Landscape: English first, then alphabetical by language code
        landscape.sort(key=lambda x: (0 if x.get("iso_639_1") == 'en' else 1, x.get("iso_639_1", "")))
        
        clean_landscape = [img for img in backdrops if img.get("iso_639_1") in (None, "xx")]

        # Use w1280 for stable telegram loading instead of original
        main_poster_path = details.get('poster_path') or (posters[0]['file_path'] if posters else None)
        main_poster = f"https://image.tmdb.org/t/p/w1280{main_poster_path}" if main_poster_path else "https://via.placeholder.com/800x1200?text=No+Poster"

        buttons = [
            [
                InlineKeyboardButton(f"🌄 𝖫𝖺𝗇𝖽𝗌𝖼𝖺𝗉𝖾 ({len(landscape)})", callback_data=f"p_view_land_{media_type}_{tmdb_id}_0_{short_query}"),
                InlineKeyboardButton(f"📱 𝖯𝗈𝗋𝗍𝗋𝖺𝗂𝗍 ({len(posters)})", callback_data=f"p_view_port_{media_type}_{tmdb_id}_0_{short_query}")
            ],
            [
                InlineKeyboardButton(f"✨ 𝖫𝗈𝗀𝗈𝗌 ({len(logos)})", callback_data=f"p_view_logo_{media_type}_{tmdb_id}_0_{short_query}"),
                InlineKeyboardButton(f"🌌 𝖢𝗅𝖾𝖺𝗇 𝖫𝖺𝗇𝖽𝗌𝖼𝖺𝗉𝖾 ({len(clean_landscape)})", callback_data=f"p_view_clean_{media_type}_{tmdb_id}_0_{short_query}")
            ]
        ]
        
        nav_close_btns = []
        if short_query:
            nav_close_btns.append(InlineKeyboardButton("🔙 𝖡𝖺𝖼𝗄 𝖳𝗈 𝖲𝖾𝖺𝗋𝖼𝗁", callback_data=f"p_search_{short_query}"))
        nav_close_btns.append(InlineKeyboardButton("❌ 𝖢𝗅𝗈𝗌𝖾", callback_data="poster_close_data"))
        buttons.append(nav_close_btns)

        m_type_str = "𝖳𝖵 𝖲𝖾𝗋𝗂𝖾𝗌" if media_type == "tv" else "𝖬𝗈𝗏𝗂𝖾"
        tmdb_link = f"https://www.themoviedb.org/{media_type}/{tmdb_id}"
        
        caption = f"""
<b>🧿 𝖳𝗂𝗍𝗅𝖾:</b> {title}
<b>📅 𝖸𝖾𝖺𝗋:</b> {year}
<b>🏷️ 𝖳𝗒𝗉𝖾:</b> {m_type_str}

<b>🔗 𝖳𝖬𝖣𝖡:</b> <a href="{tmdb_link}">𝖵𝗂𝖾𝗐 𝗈𝗇 𝖳𝖬𝖣𝖡</a>

<b>👇 𝖲𝖾𝗅𝖾𝖼𝗍 𝗉𝗈𝗌𝗍𝖾𝗋 𝖼𝖺𝗍𝖾𝗀𝗈𝗋𝗒 𝖻𝖾𝗅𝗈𝗐:</b>
"""
        
        if callback_query.message.photo:
            await callback_query.message.edit_media(
                media=InputMediaPhoto(media=main_poster, caption=caption),
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        else:
            await client.send_photo(
                chat_id=callback_query.message.chat.id,
                photo=main_poster,
                caption=caption,
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode=ParseMode.HTML
            )
            # Safe delete logic
            try:
                await callback_query.message.delete()
            except Exception:
                pass

    except Exception as e:
        logger.error(f"Menu Error: {e}")
        await callback_query.answer(f"𝖤𝗋𝗋𝗈𝗋: 𝖲𝗈𝗆𝖾𝗍𝗁𝗂𝗇𝗀 𝗐𝖾𝗇𝗍 𝗐𝗋𝗈𝗇𝗀!", show_alert=True)


# Viewer for Posters, Landscapes, Logos
@app.on_callback_query(filters.regex(r"^p_view_"))
@error
async def handle_poster_viewer(client, callback_query):
    data = callback_query.data.split("_")
    p_type = data[2]
    media_type = data[3]
    tmdb_id = data[4]
    current_index = int(data[5])
    short_query = data[6] if len(data) > 6 else ""
    
    await callback_query.answer("𝖥𝖾𝗍𝖼𝗁𝗂𝗇𝗀 𝗂𝗆𝖺𝗀𝖾𝗌...")

    try:
        url = f"https://api.themoviedb.org/3/{media_type}/{tmdb_id}/images?api_key={TMDB_API_KEY}"
        response = await fetch_json(url)
        
        if not response:
            return await callback_query.answer("⚠️ 𝖠𝖯𝖨 𝖤𝗋𝗋𝗈𝗋!", show_alert=True)
            
        backdrops = response.get("backdrops", [])
        if p_type == "land":
            images = [img for img in backdrops if img.get("iso_639_1") not in (None, "xx")]
            # Ensure English is priority in viewing as well
            images.sort(key=lambda x: (0 if x.get("iso_639_1") == 'en' else 1, x.get("iso_639_1", "")))
            type_name = "𝖫𝖺𝗇𝖽𝗌𝖼𝖺𝗉𝖾"
        elif p_type == "port":
            images = response.get("posters", [])
            type_name = "𝖯𝗈𝗋𝗍𝗋𝖺𝗂𝗍"
        elif p_type == "logo":
            images = response.get("logos", [])
            type_name = "𝖫𝗈𝗀𝗈𝗌"
        elif p_type == "clean":
            images = [img for img in backdrops if img.get("iso_639_1") in (None, "xx")]
            type_name = "𝖢𝗅𝖾𝖺𝗇 𝖫𝖺𝗇𝖽𝗌𝖼𝖺𝗉𝖾"
        else:
            images = []

        if not images:
            return await callback_query.answer(f"⚠️ 𝖭𝗈 {p_type.upper()} 𝖿𝗈𝗎𝗇𝖽 𝖿𝗈𝗋 𝗍𝗁𝗂𝗌!", show_alert=True)

        # Loop around if index is out of range
        if current_index >= len(images): current_index = 0
        if current_index < 0: current_index = len(images) - 1

        img = images[current_index]
        # Use w1280 for stable loading on Telegram servers
        img_url = f"https://image.tmdb.org/t/p/w1280{img['file_path']}"
        original_url = f"https://image.tmdb.org/t/p/original{img['file_path']}"
        
        details_url = f"https://api.themoviedb.org/3/{media_type}/{tmdb_id}?api_key={TMDB_API_KEY}"
        details = await fetch_json(details_url)
        title = details.get("name") or details.get("title", "𝖴𝗇𝗄𝗇𝗈𝗐𝗇")

        lang = img.get('iso_639_1')
        lang_display = lang.upper() if lang and lang != "xx" else '𝖭𝗈𝗇𝖾 / 𝖢𝗅𝖾𝖺𝗇'

        caption = f"""
<b>🧿 𝖳𝗂𝗍𝗅𝖾:</b> {title}

<b>🎨 𝖢𝖺𝗍𝖾𝗀𝗈𝗋𝗒:</b> {type_name}
<b>🌐 𝖫𝖺𝗇𝗀𝗎𝖺𝗀𝖾:</b> {lang_display}
<b>📏 𝖱𝖾𝗌𝗈𝗅𝗎𝗍𝗂𝗈𝗇:</b> {img.get('width')}x{img.get('height')}

<b>📥 𝖮𝗋𝗂𝗀𝗂𝗇𝖺𝗅 𝖫𝗂𝗇𝗄:</b> <a href="{original_url}">𝖣𝗈𝗐𝗇𝗅𝗈𝖺𝖽 𝖧𝖾𝗋𝖾</a>
"""

        nav_btns = []
        if len(images) > 1:
            nav_btns.append(InlineKeyboardButton("⏮️", callback_data=f"p_view_{p_type}_{media_type}_{tmdb_id}_0_{short_query}"))
            nav_btns.append(InlineKeyboardButton("◀️", callback_data=f"p_view_{p_type}_{media_type}_{tmdb_id}_{current_index - 1}_{short_query}"))
            
        nav_btns.append(InlineKeyboardButton(f"{current_index + 1} / {len(images)}", callback_data="poster_none_data"))
        
        if len(images) > 1:
            nav_btns.append(InlineKeyboardButton("▶️", callback_data=f"p_view_{p_type}_{media_type}_{tmdb_id}_{current_index + 1}_{short_query}"))
            nav_btns.append(InlineKeyboardButton("⏭️", callback_data=f"p_view_{p_type}_{media_type}_{tmdb_id}_{len(images) - 1}_{short_query}"))
        
        buttons = [nav_btns]
        buttons.append([
            InlineKeyboardButton("🔙 𝖡𝖺𝖼𝗄 𝖳𝗈 𝖬𝖾𝗇𝗎", callback_data=f"p_menu_{media_type}_{tmdb_id}_{short_query}"), 
            InlineKeyboardButton("❌ 𝖢𝗅𝗈𝗌𝖾", callback_data="poster_close_data")
        ])

        try:
            await callback_query.message.edit_media(
                media=InputMediaPhoto(media=img_url, caption=caption),
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        except Exception:
            # Fallback for CURL failure: try a smaller size if 1280 also fails
            small_img_url = f"https://image.tmdb.org/t/p/w780{img['file_path']}"
            await callback_query.message.edit_media(
                media=InputMediaPhoto(media=small_img_url, caption=caption),
                reply_markup=InlineKeyboardMarkup(buttons)
            )

    except Exception as e:
        logger.error(f"Viewer Error: {e}")
        await callback_query.answer(f"𝖤𝗋𝗋𝗈𝗋: 𝖲𝗈𝗆𝖾𝗍𝗁𝗂𝗇𝗀 𝗐𝖾𝗇𝗍 𝗐𝗋𝗈𝗇𝗀!", show_alert=True)


# Ignored button handler (e.g., for "1 / 10" indicator)
@app.on_callback_query(filters.regex(r"^poster_none_data$"))
@error
async def ignore_callback(client, callback_query):
    await callback_query.answer()


# Close button handler specifically for poster module to avoid global conflicts
@app.on_callback_query(filters.regex(r"^poster_close_data$"))
@error
async def close_callback(client, callback_query):
    try:
        await callback_query.message.delete()
    except Exception:
        await callback_query.answer("⚠️ 𝖨 𝖽𝗈𝗇'𝗍 𝗁𝖺𝗏𝖾 𝗉𝖾𝗋𝗆𝗂𝗌𝗌𝗂𝗈𝗇 𝗍𝗈 𝖽𝖾𝗅𝖾𝗍𝖾 𝗍𝗁𝗂𝗌 𝗆𝖾𝗌𝗌𝖺𝗀𝖾!", show_alert=True)


__module__ = "𝖯𝗈𝗌𝗍𝖾𝗋"

__help__ = """**𝖯𝗈𝗌𝗍𝖾𝗋 𝖲𝖾𝖺𝗋𝖼𝗁 𝖢𝗈𝗆𝗆𝖺𝗇𝖽𝗌:**

  ✧ `/poster` **:** 𝖲𝖾𝖺𝗋𝖼𝗁 𝖿𝗈𝗋 𝖬𝗈𝗏𝗂𝖾/𝖳𝖵 𝖲𝗁𝗈𝗐 𝗉𝗈𝗌𝗍𝖾𝗋𝗌, 𝖻𝖺𝖼𝗄𝖽𝗋𝗈𝗉𝗌, 𝖺𝗇𝖽 𝗅𝗈𝗀𝗈𝗌 𝖿𝗋𝗈𝗆 𝖳𝖬𝖣𝖡 𝗂𝗇 𝗁𝗂𝗀𝗁 𝗊𝗎𝖺𝗅𝗂𝗍𝗒.
  
  **𝖤𝗑𝖺𝗆𝗉𝗅𝖾:**
  `/poster naruto`
"""
