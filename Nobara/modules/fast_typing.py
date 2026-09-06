import os
import time
import io
import random
import asyncio
import requests
import textwrap
from PIL import Image, ImageDraw, ImageFont
from pyrogram import Client, filters, ContinuePropagation
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.enums import ChatMemberStatus
from Nobara import app, FAST_TYPING_GROUP
from config import config
from Nobara.decorator.save import save
from Nobara.decorator.errors import error
from Nobara.database.game_db import get_ft_settings, update_ft_settings, add_local_ft_point, get_all_active_ft_chats, get_local_leaderboard, get_global_user_leaderboard, get_global_chat_leaderboard, FT_WIN_XP_REWARD

# ==========================================
# GAME ASSETS & CONSTANTS (Massively Expanded)
# ==========================================
FREQ_MAP = {
    3600: "1h", 7200: "2h", 10800: "3h", 14400: "4h",
    21600: "6h", 28800: "8h", 43200: "12h", 86400: "1D"
}
FREQ_LIST = list(FREQ_MAP.keys())

WORDS = [
    "RECORDS", "TELEGRAM", "BOT", "HOKAGE", "NINJA", "TYPING", "MINIGAME", "CHALLENGE", "WINNER", "GENIN",
    "NARUTO", "SASUKE", "SAKURA", "KAKASHI", "JAPAN", "ANIME", "MANGA", "OTAKU", "JUTSU", "CHAKRA",
    "SHINOBI", "KUNAI", "SHURIKEN", "SAMURAI", "KATANA", "DRAGON", "PHOENIX", "SWORD", "MAGIC", "POWER",
    "NATURE", "OCEAN", "GALAXY", "UNIVERSE", "PLANET", "STAR", "SUN", "MOON", "EARTH", "WORLD",
    "PROGRAMMING", "PYTHON", "JAVA", "JAVASCRIPT", "HTML", "CSS", "REACT", "NODEJS", "DATABASE", "SERVER",
    "INTERNET", "WEBSITE", "HACKER", "CYBER", "SECURITY", "SYSTEM", "CLOUD", "SOFTWARE", "HARDWARE", "NETWORK"
]

EMOJIS = [
    ("🚀", "rocket"), ("❤️", "heart"), ("🔥", "fire"), ("🎉", "party"), ("🌟", "star"),
    ("🍎", "apple"), ("🚗", "car"), ("🐶", "dog"), ("🐱", "cat"), ("🍕", "pizza"),
    ("⚽", "football"), ("🎸", "guitar"), ("✈️", "airplane"), ("📱", "phone"), ("⌚", "watch"),
    ("💎", "diamond"), ("🍔", "burger"), ("🍦", "ice cream"), ("🍩", "donut"), ("🍓", "strawberry"),
    ("🍉", "watermelon"), ("🍌", "banana"), ("🍒", "cherry"), ("🍍", "pineapple"), ("🥭", "mango"),
    ("🏀", "basketball"), ("🎾", "tennis"), ("🏐", "volleyball"), ("🏓", "table tennis"), ("🎱", "ping pong"),
    ("🎮", "video game"), ("🎧", "headphones"), ("🎤", "microphone"), ("🎬", "clapper board"), ("🎨", "art"),
    ("🏖️", "beach"), ("🏕️", "camping"), ("⛰️", "mountain"), ("🌋", "volcano"), ("🏝️", "island")
]

MATHS = [
    ("5 + 7", "12"), ("10 - 3", "7"), ("4 * 5", "20"), ("15 / 3", "5"), ("8 + 9", "17"),
    ("12 + 15", "27"), ("20 - 8", "12"), ("6 * 6", "36"), ("25 / 5", "5"), ("14 + 16", "30"),
    ("50 - 25", "25"), ("7 * 8", "56"), ("100 / 10", "10"), ("9 + 12", "21"), ("30 - 14", "16"),
    ("3 * 15", "45"), ("40 / 8", "5"), ("18 + 22", "40"), ("60 - 35", "25"), ("9 * 9", "81"),
    ("11 * 11", "121"), ("12 * 12", "144"), ("100 - 45", "55"), ("75 + 25", "100"), ("200 / 2", "100"),
    ("30 * 3", "90"), ("45 / 9", "5"), ("8 * 7", "56"), ("50 + 60", "110"), ("150 - 75", "75"),
    ("80 / 4", "20"), ("15 * 2", "30"), ("99 + 1", "100"), ("1000 / 10", "100"), ("5 * 25", "125")
]

FLAGS = [
    ("🇺🇸", "usa"), ("🇧🇩", "bangladesh"), ("🇮🇳", "india"), ("🇯🇵", "japan"), ("🇬🇧", "uk"),
    ("🇨🇦", "canada"), ("🇦🇺", "australia"), ("🇧🇷", "brazil"), ("🇫🇷", "france"), ("🇩🇪", "germany"),
    ("🇮🇹", "italy"), ("🇪🇸", "spain"), ("🇷🇺", "russia"), ("🇨🇳", "china"), ("🇰🇷", "south korea"),
    ("🇿🇦", "south africa"), ("🇦🇷", "argentina"), ("🇲🇽", "mexico"), ("🇸🇦", "saudi arabia"), ("🇪🇬", "egypt"),
    ("🇹🇷", "turkey"), ("🇮🇩", "indonesia"), ("🇵🇰", "pakistan"), ("🇳🇬", "nigeria"), ("🇻🇳", "vietnam"),
    ("🇹🇭", "thailand"), ("🇵🇭", "philippines"), ("🇲🇾", "malaysia"), ("🇸🇬", "singapore"), ("🇳🇿", "new zealand"),
    ("🇨🇭", "switzerland"), ("🇳🇱", "switzerland"), ("🇸🇪", "sweden"), ("🇳🇴", "norway"), ("🇩🇰", "denmark")
]

SONGS = [
    ("Never gonna give you...", "up"), ("Twinkle twinkle little...", "star"), ("Happy birthday to...", "you"),
    ("We will we will rock...", "you"), ("Let it go, let it...", "go"), ("I want it that...", "way"),
    ("Shape of...", "you"), ("Bohemian...", "rhapsody"), ("Hotel...", "california"), ("Billie...", "jean"),
    ("Smells like teen...", "spirit"), ("Sweet child o'...", "mine"), ("Rolling in the...", "deep"), 
    ("Someone like...", "you"), ("Hey...", "jude"), ("Don't stop...", "believin'"), ("Livin' on a...", "prayer"),
    ("I will always love...", "you"), ("My heart will go...", "on"), ("Shake it...", "off"),
    ("Thinking out...", "loud"), ("Love me like you...", "do"), ("Uptown...", "funk"), ("Counting...", "stars"),
    ("Call me...", "maybe"), ("Just the way you...", "are"), ("Can't stop the...", "feeling"), ("All of...", "me"),
    ("A thousand...", "years"), ("Stay with...", "me"), ("Wake me up before you...", "go-go"),
    ("Take me to...", "church"), ("I'm yours...", "forever"), ("Baby, you're a...", "firework")
]

QUES = [
    ("What is the capital of Japan?", "tokyo"), ("Which planet is the Red Planet?", "mars"), 
    ("What is 15 + 25?", "40"), ("Who wrote 'Hamlet'?", "shakespeare"), ("What is the largest ocean?", "pacific"),
    ("What is the capital of France?", "paris"), ("Which animal is known as the King of the Jungle?", "lion"),
    ("How many continents are there?", "7"), ("What is the boiling point of water in Celsius?", "100"), 
    ("Who painted the Mona Lisa?", "da vinci"), ("What is the hardest natural substance?", "diamond"),
    ("Which gas do plants absorb?", "carbon dioxide"), ("How many legs does a spider have?", "8"),
    ("What is the chemical symbol for Gold?", "au"), ("Who is the founder of Microsoft?", "bill gates"),
    ("What is the longest river?", "nile"), ("What is the square root of 64?", "8"),
    ("Which country is known as the Land of the Rising Sun?", "japan"), ("What is the largest mammal?", "blue whale"),
    ("How many days are in a leap year?", "366"), ("What is the capital of Italy?", "rome"),
    ("Which is the smallest planet in our solar system?", "mercury"), ("What is 50 + 50?", "100"),
    ("Who discovered gravity?", "newton"), ("What is the largest desert in the world?", "sahara"),
    ("What is the primary language spoken in Brazil?", "portuguese"), ("How many states are in the USA?", "50"),
    ("What is the national flower of Japan?", "cherry blossom"), ("Which gas is most abundant in Earth's atmosphere?", "nitrogen"),
    ("Who is the author of Harry Potter?", "jk rowling"), ("What is the capital of Australia?", "canberra")
]

# 👇 আপনার আপলোড করা ব্যাকগ্রাউন্ড ছবির ডিরেক্ট লিংকগুলো এখানে দিন (Telegraph বা ImgBB লিংক)
BACKGROUND_TEMPLATES = [
    "https://i.ibb.co/KxGQbyRj/image.jpg",
    "https://i.ibb.co/dwGsXv3m/image.jpg",
]

# Active games in memory: chat_id -> {word, start_time, msg_id, prev_msg_id, task_ref, options, needs_button}
active_ft_games = {}

# ==========================================
# IMAGE GENERATOR (With Big Font, Emoji & Auto-wrap)
# ==========================================
def generate_word_image(text, cat):
    img = None
    if BACKGROUND_TEMPLATES:
        try:
            bg_url = random.choice(BACKGROUND_TEMPLATES)
            response = requests.get(bg_url, stream=True, timeout=5)
            if response.status_code == 200:
                img = Image.open(io.BytesIO(response.content)).convert("RGBA")
                img = img.resize((800, 400))
        except Exception as e:
            print(f"Failed to load template image: {e}")
            img = None

    if img is None:
        img = Image.new('RGBA', (800, 400), color=(30, 5, 5, 255))
    else:
        img = img.convert("RGBA")
        
    font_path = "ft_font.ttf"
    if not os.path.exists(font_path):
        try:
            r = requests.get("https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Black.ttf", timeout=10)
            with open(font_path, "wb") as f:
                f.write(r.content)
        except:
            pass

    W, H = img.size
    cx, cy = W // 2, H // 2

    # --- 1. EMOJI & FLAGS FIX (Using Twemoji API without Box) ---
    if cat in ["emoji", "flags"]:
        codepoints = [hex(ord(c))[2:] for c in text if hex(ord(c))[2:] != 'fe0f']
        code_str = "-".join(codepoints)
        url = f"https://cdnjs.cloudflare.com/ajax/libs/twemoji/14.0.2/72x72/{code_str}.png"
        
        success = False
        try:
            r = requests.get(url, timeout=5)
            if r.status_code == 200:
                e_img = Image.open(io.BytesIO(r.content)).convert("RGBA")
                try: resample = Image.Resampling.LANCZOS
                except: resample = Image.ANTIALIAS
                
                e_img = e_img.resize((150, 150), resample)
                
                txt_overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
                txt_overlay.paste(e_img, (cx - 75, cy - 75), e_img)
                img = Image.alpha_composite(img, txt_overlay)
                success = True
        except: pass
        
        if success:
            final_img = img.convert("RGB")
            bio = io.BytesIO()
            bio.name = 'fast_typing.jpg'
            final_img.save(bio, 'JPEG')
            bio.seek(0)
            return bio

    # --- 2. SONG & QUES LONG TEXT WRAP FIX ---
    font_size = 100
    if cat in ["song", "ques"]:
        lines = textwrap.wrap(text, width=22)
        text = "\n".join(lines)
        font_size = 75

    try:
        font = ImageFont.truetype(font_path, font_size) 
    except:
        font = ImageFont.load_default()

    txt_overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(txt_overlay)

    outline_color = (0, 0, 0, 255)
    text_color = (255, 255, 255, 255)
    
    try:
        d.text((cx, cy), text, fill=text_color, anchor="mm", align="center", font=font, stroke_width=5, stroke_fill=outline_color)
    except:
        offset = 4
        for ox in [-offset, 0, offset]:
            for oy in [-offset, 0, offset]:
                d.text((cx + ox, cy + oy), text, fill=outline_color, anchor="mm", align="center", font=font)
        d.text((cx, cy), text, fill=text_color, anchor="mm", align="center", font=font)
    
    final_img = Image.alpha_composite(img, txt_overlay).convert("RGB")
    
    bio = io.BytesIO()
    bio.name = 'fast_typing.jpg'
    final_img.save(bio, 'JPEG')
    bio.seek(0)
    return bio

# ==========================================
# UI BUILDER
# ==========================================
def build_ft_keyboard(settings):
    is_on = "🟢 ON" if settings["is_on"] else "🔴 OFF"
    freq_str = FREQ_MAP.get(settings["freq"], "1h")
    
    def check(val, lst): return "✅" if val in lst else "❌"

    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"Status: {is_on}", callback_data="ft_toggle_status")],
        [InlineKeyboardButton(f"Frequency: {freq_str}", callback_data="ft_toggle_freq")],
        [InlineKeyboardButton("📚 Content Category", callback_data="none")],
        [
            InlineKeyboardButton(f"Words {check('words', settings['cats'])}", callback_data="ft_cat_words"),
            InlineKeyboardButton(f"Emoji {check('emoji', settings['cats'])}", callback_data="ft_cat_emoji"),
            InlineKeyboardButton(f"Math {check('math', settings['cats'])}", callback_data="ft_cat_math")
        ],
        [
            InlineKeyboardButton(f"Flags {check('flags', settings['cats'])}", callback_data="ft_cat_flags"),
            InlineKeyboardButton(f"Song {check('song', settings['cats'])}", callback_data="ft_cat_song"),
            InlineKeyboardButton(f"Ques {check('ques', settings['cats'])}", callback_data="ft_cat_ques")
        ],
        [InlineKeyboardButton("⚙️ Additional Options", callback_data="none")],
        [
            InlineKeyboardButton(f"Pin Msg {check('pin', settings['opts'])}", callback_data="ft_opt_pin"),
            InlineKeyboardButton(f"Del Prev {check('delete_prev', settings['opts'])}", callback_data="ft_opt_delete_prev"),
            InlineKeyboardButton(f"Warn Exp {check('warn', settings['opts'])}", callback_data="ft_opt_warn")
        ]
    ])

# ==========================================
# /game COMMAND
# ==========================================
@app.on_message(filters.command("game", prefixes=config.COMMAND_PREFIXES) & filters.group)
@error
@save
async def ft_menu(client: Client, message: Message):
    user_id = message.from_user.id if message.from_user else (message.sender_chat.id if message.sender_chat else 0)
    chat_id = message.chat.id
    
    member = await client.get_chat_member(chat_id, user_id)
    if member.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
        return await message.reply("𝖸𝗈𝗎 𝗇𝖾𝖾𝖽 𝗍𝗈 𝖻𝖾 𝖺𝗇 𝖺𝖽𝗆𝗂𝗇 𝗍𝗈 𝖼𝗈𝗇𝖿𝗂𝗀𝗎𝗋𝖾 𝗍𝗁𝖾 𝗀𝖺𝗆𝖾.")
        
    settings = await get_ft_settings(chat_id)
    if "ques" not in settings.get("cats", []) and "ques" not in settings.get("disabled_cats", []):
        pass 
    
    text = (
        "⚡️ **FAST TYPING**\n"
        "The bot will send an image containing a word or puzzle. Users must answer correctly as quickly as possible. The first one wins.\n\n"
        f"⏱ **Frequency:** {FREQ_MAP.get(settings['freq'], '1h')}"
    )
    
    await message.reply(text, reply_markup=build_ft_keyboard(settings))

@app.on_callback_query(filters.regex(r"^ft_toggle|^ft_cat|^ft_opt"))
@error
async def ft_callback(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    chat_id = query.message.chat.id
    
    member = await client.get_chat_member(chat_id, user_id)
    if member.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
        return await query.answer("Only admins can change these settings.", show_alert=True)
        
    settings = await get_ft_settings(chat_id)
    data = query.data
    
    if data == "ft_toggle_status":
        settings["is_on"] = not settings["is_on"]
        if settings["is_on"]:
            settings["last_run"] = 0 
            
    elif data == "ft_toggle_freq":
        idx = FREQ_LIST.index(settings["freq"]) if settings["freq"] in FREQ_LIST else 0
        settings["freq"] = FREQ_LIST[(idx + 1) % len(FREQ_LIST)]
        
    elif data.startswith("ft_cat_"):
        cat = data.split("_")[2]
        if cat in settings["cats"]:
            if len(settings["cats"]) > 1:
                settings["cats"].remove(cat)
            else:
                return await query.answer("You must have at least one category enabled!", show_alert=True)
        else:
            settings["cats"].append(cat)
            
    elif data.startswith("ft_opt_"):
        opt = data.split("_")[2]
        if opt in settings["opts"]:
            settings["opts"].remove(opt)
        else:
            settings["opts"].append(opt)

    await update_ft_settings(chat_id, settings)
    
    if data == "ft_toggle_status" and settings["is_on"]:
        asyncio.create_task(start_game_instance(client, chat_id, settings))
        settings["last_run"] = time.time()
        await update_ft_settings(chat_id, settings)
    
    text = (
        "⚡️ **FAST TYPING**\n"
        "The bot will send an image containing a word or puzzle. Users must answer correctly as quickly as possible. The first one wins.\n\n"
        f"⏱ **Frequency:** {FREQ_MAP.get(settings['freq'], '1h')}"
    )
    await query.message.edit_text(text, reply_markup=build_ft_keyboard(settings))

# ==========================================
# GAME LOGIC & SCHEDULER
# ==========================================
async def start_game_instance(client: Client, chat_id: int, settings: dict):
    cat = random.choice(settings["cats"])
    options_list = None
    reply_markup = None
    needs_button = cat in ["emoji", "flags", "song", "ques"]
    
    if cat == "words":
        answer = random.choice(WORDS)
        photo = await asyncio.to_thread(generate_word_image, answer, cat)
    elif cat == "math":
        q, answer = random.choice(MATHS)
        photo = await asyncio.to_thread(generate_word_image, q, cat)
    else:
        # Button based categories
        source_list = EMOJIS if cat == "emoji" else FLAGS if cat == "flags" else SONGS if cat == "song" else QUES
        q, answer = random.choice(source_list)
        photo = await asyncio.to_thread(generate_word_image, q, cat)
        
        # Generate Options
        other_options = [item[1] for item in source_list if item[1] != answer]
        wrong_choices = random.sample(other_options, min(3, len(other_options)))
        options_list = [answer] + wrong_choices
        random.shuffle(options_list)
        
        buttons = []
        row = []
        for i, opt in enumerate(options_list):
            row.append(InlineKeyboardButton(str(opt).title(), callback_data=f"ftans_{i}"))
            if len(row) == 2:
                buttons.append(row)
                row = []
        if row: buttons.append(row)
        reply_markup = InlineKeyboardMarkup(buttons)
        
    caption = "⚡️ Be the first to write the word/answer shown in the photo to climb the mini-game leaderboard.\n\n⏱ Time remaining: 10 minutes"
    
    try:
        msg = await client.send_photo(
            chat_id, 
            photo=photo, 
            caption=caption, 
            reply_markup=reply_markup,
            has_spoiler=True, 
            protect_content=True
        )
        
        if "pin" in settings["opts"]:
            try: await msg.pin(disable_notification=True)
            except: pass
            
        if "delete_prev" in settings["opts"] and chat_id in active_ft_games:
            prev_msg = active_ft_games[chat_id].get("msg_id")
            if prev_msg:
                try: await client.delete_messages(chat_id, prev_msg)
                except: pass

        active_ft_games[chat_id] = {
            "word": str(answer),
            "start_time": time.time(),
            "msg_id": msg.id,
            "warn_msg_id": None,
            "settings": settings,
            "options": options_list,
            "needs_button": needs_button
        }

        async def game_lifecycle():
            await asyncio.sleep(8 * 60)
            if chat_id in active_ft_games and active_ft_games[chat_id]["msg_id"] == msg.id:
                if "warn" in settings["opts"]:
                    try:
                        w_msg = await msg.reply("⚠️ Alarm: time is running out!!")
                        active_ft_games[chat_id]["warn_msg_id"] = w_msg.id
                    except: pass
                    
            await asyncio.sleep(2 * 60)
            if chat_id in active_ft_games and active_ft_games[chat_id]["msg_id"] == msg.id:
                try:
                    msgs_to_del = [msg.id]
                    if active_ft_games[chat_id]["warn_msg_id"]:
                        msgs_to_del.append(active_ft_games[chat_id]["warn_msg_id"])
                    await client.delete_messages(chat_id, msgs_to_del)
                except: pass
                del active_ft_games[chat_id]
                
        active_ft_games[chat_id]["task_ref"] = asyncio.create_task(game_lifecycle())
        
    except Exception as e:
        print(f"Failed to start game in {chat_id}: {e}")

# Background Scheduler Loop
async def ft_scheduler():
    await asyncio.sleep(10)
    while True:
        try:
            chats = await get_all_active_ft_chats()
            now = time.time()
            for chat in chats:
                chat_id = chat["chat_id"]
                freq = chat.get("freq", 3600)
                last_run = chat.get("last_run", 0)
                
                if last_run == 0 or (now - last_run >= freq):
                    chat["last_run"] = now
                    await update_ft_settings(chat_id, chat)
                    await start_game_instance(app, chat_id, chat)
                    
        except Exception as e:
            print(f"FT Scheduler Error: {e}")
            
        await asyncio.sleep(60)

asyncio.get_event_loop().create_task(ft_scheduler())

# ==========================================
# ANSWER HANDLER (For Words & Math Only)
# ==========================================
# Group=-10 ব্যবহার করা হয়েছে যেন অন্য যেকোনো ফিচারের আগে এটি রান করে এবং ব্লক না হয়
@app.on_message(filters.group & filters.text, group=-10)
async def check_ft_answer(client: Client, message: Message):
    chat_id = message.chat.id
    if chat_id not in active_ft_games:
        raise ContinuePropagation
        
    game = active_ft_games[chat_id]
    
    # Ignore text answers if the game requires a button click
    if game.get("needs_button"):
        raise ContinuePropagation
    
    if message.text.strip().lower() == str(game["word"]).lower():
        elapsed = int(time.time() - game["start_time"])
        mins, secs = divmod(elapsed, 60)
        
        # Robust user_id catch (Fix for Anonymous Admins/Owners)
        if message.from_user:
            user_id = message.from_user.id
            username = message.from_user.username
        elif message.sender_chat:
            user_id = message.sender_chat.id
            username = None
        else:
            raise ContinuePropagation
        
        try:
            await add_local_ft_point(chat_id, user_id, username)
        except Exception as e:
            print(f"Point Error: {e}")
        
        try:
            new_caption = "⚡️ Be the first to write the word shown in the photo to climb the mini-game leaderboard.\n\n⏱ Time remaining: **Ended**"
            await client.edit_message_caption(chat_id, game["msg_id"], caption=new_caption)
        except: pass
        
        win_text = f"💪 Come on! ({mins} minutes {secs} seconds)\nYou guessed the word!\n+{FT_WIN_XP_REWARD} XP (+1 in the local game leaderboard)"
        await message.reply(win_text)
        
        settings = game["settings"]
        try:
            if "pin" in settings["opts"]:
                await client.unpin_chat_message(chat_id, game["msg_id"])
        except: pass
        
        if "task_ref" in game:
            game["task_ref"].cancel()
            
        del active_ft_games[chat_id]
        raise ContinuePropagation
    else:
        # ভুল উত্তর দিলে অন্য মডিউলের জন্য কন্টিনিউ করবে
        raise ContinuePropagation

# ==========================================
# BUTTON ANSWER HANDLER (For Emoji, Flags, Song, Ques)
# ==========================================
@app.on_callback_query(filters.regex(r"^ftans_"))
@error
async def ft_button_answer(client: Client, query: CallbackQuery):
    chat_id = query.message.chat.id
    if chat_id not in active_ft_games:
        return await query.answer("This game has already ended!", show_alert=True)
        
    game = active_ft_games[chat_id]
    if game["msg_id"] != query.message.id:
        return await query.answer("This game session has expired.", show_alert=True)
        
    idx = int(query.data.split("_")[1])
    selected_answer = game["options"][idx]
    
    if selected_answer.lower() == str(game["word"]).lower():
        # Winner Found!
        user_id = query.from_user.id
        username = query.from_user.username
        elapsed = int(time.time() - game["start_time"])
        mins, secs = divmod(elapsed, 60)
        
        try:
            await add_local_ft_point(chat_id, user_id, username)
        except Exception as e:
            print(f"Point Error: {e}")
        
        # Remove buttons and update caption
        try:
            new_caption = "⚡️ Be the first to answer correctly to climb the mini-game leaderboard.\n\n⏱ Time remaining: **Ended**"
            await query.message.edit_caption(caption=new_caption, reply_markup=None)
        except: pass
        
        win_text = f"💪 Come on! ({mins} minutes {secs} seconds)\nYou guessed the right answer!\n+{FT_WIN_XP_REWARD} XP (+1 in the local game leaderboard)"
        await query.message.reply(win_text)
        
        settings = game["settings"]
        try:
            if "pin" in settings["opts"]:
                await client.unpin_chat_message(chat_id, game["msg_id"])
        except: pass
        
        if "task_ref" in game:
            game["task_ref"].cancel()
            
        del active_ft_games[chat_id]
        await query.answer("Correct Answer!", show_alert=False)
    else:
        await query.answer("Wrong answer! Try again.", show_alert=True)

# ==========================================
# LEADERBOARDS (Local & Global)
# ==========================================
@app.on_message(filters.command("leaderboard", prefixes=config.COMMAND_PREFIXES) & filters.group)
@error
@save
async def ft_local_lb(client: Client, message: Message):
    lb = await get_local_leaderboard(message.chat.id)
    if not lb:
        return await message.reply("𝖭𝗈 𝗈𝗇𝖾 𝗁𝖺𝗌 𝗌𝖼𝗈𝗋𝖾𝖽 𝖺𝗇𝗒 𝗉𝗈𝗂𝗇𝗍𝗌 𝗂𝗇 𝗍𝗁𝗂𝗌 𝗀𝗋𝗈𝗎𝗉 𝗒𝖾𝗍!")
    
    text = "**🏆 𝖫𝗈𝖼𝖺𝗅 𝖥𝖺𝗌𝗍 𝖳𝗒𝗉𝗂𝗇𝗀 𝖫𝖾𝖺𝖽𝖾𝗋𝖻𝗈𝖺𝗋𝖽**\n\n"
    for i, user in enumerate(lb, 1):
        user_id = user["user_id"]
        points = user["points"]
        try:
            u = await client.get_users(user_id)
            name = u.mention
        except:
            name = f"𝖴𝗌𝖾𝗋 {user_id}"
        text += f"**{i}.** {name} - `{points}` 𝗐𝗂𝗇𝗌\n"
    await message.reply(text, disable_web_page_preview=True)

@app.on_message(filters.command("globalleaderboard", prefixes=config.COMMAND_PREFIXES))
@error
@save
async def ft_global_user_lb(client: Client, message: Message):
    lb = await get_global_user_leaderboard()
    if not lb:
        return await message.reply("𝖭𝗈 𝖽𝖺𝗍𝖺 𝖺𝗏𝖺𝗂𝗅𝖺𝖻𝗅𝖾 𝗒𝖾𝗍.")
    
    text = "**🌍 𝖦𝗅𝗈𝖻𝖺𝗅 𝖥𝖺𝗌𝗍 𝖳𝗒𝗉𝗂𝗇𝗀 𝖫𝖾𝖺𝖽𝖾𝗋𝖻𝗈𝖺𝗋𝖽**\n\n"
    for i, user in enumerate(lb, 1):
        user_id = user["_id"]
        points = user["total_points"]
        try:
            u = await client.get_users(user_id)
            name = u.mention
        except:
            name = f"𝖴𝗌𝖾𝗋 {user_id}"
        text += f"**{i}.** {name} - `{points}` 𝗐𝗂𝗇𝗌\n"
    await message.reply(text, disable_web_page_preview=True)

@app.on_message(filters.command("groupleaderboard", prefixes=config.COMMAND_PREFIXES))
@error
@save
async def ft_global_chat_lb(client: Client, message: Message):
    lb = await get_global_chat_leaderboard()
    if not lb:
        return await message.reply("𝖭𝗈 𝖽𝖺𝗍𝖺 𝖺𝗏𝖺𝗂𝗅𝖺𝖻𝗅𝖾 𝗒𝖾𝗍.")
    
    text = "**🏙 𝖳𝗈𝗉 𝖦𝗋𝗈𝗎𝗉𝗌 𝖻𝗒 𝖥𝖺𝗌𝗍 𝖳𝗒𝗉𝗂𝗇𝗀**\n\n"
    for i, chat in enumerate(lb, 1):
        chat_id = chat["_id"]
        points = chat["total_points"]
        try:
            c = await client.get_chat(chat_id)
            name = c.title
        except:
            name = f"𝖦𝗋𝗈𝗎𝗉 {chat_id}"
        text += f"**{i}.** {name} - `{points}` 𝗐𝗂𝗇𝗌\n"
    await message.reply(text, disable_web_page_preview=True)
