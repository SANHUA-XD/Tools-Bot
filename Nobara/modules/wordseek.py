import random
import asyncio
import datetime
import time
import hashlib
import httpx
from pyrogram import Client, filters, ContinuePropagation
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.enums import ChatMemberStatus
from pyrogram.errors import MessageNotModified
from Nobara import app, WORDSEEK_GROUP
from config import config
from Nobara.decorator.save import save
from Nobara.decorator.errors import error
from Nobara.database.wordseekdb import (
    get_game, save_game, clear_game,
    get_daily, save_daily, is_daily_paused, set_daily_paused,
    get_word_history, add_word_history,
    get_auth_users, add_auth_user, remove_auth_user,
    get_topic_settings, get_all_topics, set_topic_settings, delete_topic_settings,
    get_streak, bump_streak, reset_streak,
    record_score_event, get_leaderboard, get_user_totals,
)

# AI Provider for Smart Hints (Fallback included if AI is down)
try:
    from Nobara.helper.ai_provider import get_ai_response
except ImportError:
    async def get_ai_response(prompt, system_prompt):
        return "Think outside the box! I couldn't connect to the AI brain.", "fallback"

# ==========================================
# EXPANDED WORD LISTS & DICTIONARIES
# ==========================================
WORDS_4 = [
    "TIME", "PLAY", "GAME", "WORD", "SEEK", "LOVE", "LIFE", "MIND", "SOUL", "HERO", 
    "BIRD", "FIRE", "COLD", "DARK", "LIGHT", "MOON", "STAR", "WIND", "RAIN", "SNOW", 
    "KING", "RING", "SONG", "HOPE", "FEAR", "BOLD", "CALM", "DEAR", "EPIC", "WAVE",
    "FAST", "SLOW", "HARD", "SOFT", "GOOD", "EVIL", "RICH", "POOR", "TALL", "DEEP",
    "WIDE", "LOUD", "WILD", "FREE", "SAFE", "TRUE", "FAIR", "WISE", "HOLY", "PURE",
    "IRON", "WOOD", "SAND", "DUST", "ROCK", "FISH", "BEAR", "WOLF", "LION", "MILK",
    "MEAT", "RICE", "SOUP", "CAKE", "SHIP", "BOAT", "CARS", "ROAD", "PATH", "CITY",
    "TOWN", "HOME", "DOOR", "ROOF", "WALL", "ROOM", "BEDS", "DESK", "BOOK", "PAGE",
    "READ", "TALE", "POEM", "MYTH", "FACT", "DATA", "MATH", "ART", "DRAW", "BLUE",
    "BEST", "HOLD", "BOTH", "EACH", "MANY", "SOME", "SUCH", "VERY", "JUST", "ONCE"
]

WORDS_5 = [
    "APPLE", "BRAIN", "CLOUD", "DREAM", "EARTH", "FLAME", "GHOST", "HEART", "IMAGE", "JUICE", 
    "KNIFE", "LEMON", "MAGIC", "NIGHT", "OCEAN", "ADIEU", "CLASS", "STARE", "STAFF", "STAKE", 
    "PLANT", "SPACE", "WATER", "STONE", "RIVER", "SMILE", "TRACK", "TRAIN", "BEACH", "CHAIR", 
    "TABLE", "HOUSE", "MOUSE", "TIGER", "PANDA", "EAGLE", "SHARK", "WHALE", "SNAKE", "ROBOT", 
    "PIZZA", "BREAD", "GRAPE", "SWORD", "BLOOD", "TRAIL", "SOUND", "NOISE", "PEACE", "TRUTH",
    "WORLD", "LIGHT", "BROWN", "BLACK", "WHITE", "GREEN", "SWEET", "FRESH", "SMART", "QUICK",
    "BRAVE", "PROUD", "CRAZY", "HAPPY", "ANGRY", "FUNNY", "HEAVY", "THICK", "EMPTY", "CLEAN",
    "DIRTY", "SHARP", "ROUND", "STEAK", "FRUIT", "SUGAR", "HONEY", "CHEST", "PANTS", "SHOES",
    "SHIRT", "DRESS", "SKIRT", "CLOCK", "WATCH", "RADIO", "PHONE", "CABLE", "STEEL", "BRASS",
    "ALIVE", "ADULT", "AGENT", "AGREE", "AHEAD", "ALARM", "ALBUM", "ALERT", "ALIEN", "ALTER"
]

WORDS_6 = [
    "ANIMAL", "BOTTLE", "CASTLE", "DRAGON", "ENERGY", "FOREST", "GALAXY", "HUNTER", "ISLAND", "JUNGLE", 
    "KNIGHT", "LIZARD", "MONKEY", "NATURE", "PLANET", "SYSTEM", "ROCKET", "METEOR", "GARDEN", "FLOWER", 
    "SPRING", "SUMMER", "WINTER", "AUTUMN", "PERSON", "PEOPLE", "FRIEND", "FAMILY", "SCHOOL", "CHURCH", 
    "TEMPLE", "MARKET", "STREET", "BRIDGE", "SILVER", "GOLDEN", "BRONZE", "SHIELD", "CANNON", "WEAPON",
    "ACTION", "BEAUTY", "CAMERA", "DANGER", "EFFECT", "FATHER", "MOTHER", "DOCTOR", "POLICE", "SINGER",
    "WRITER", "AUTHOR", "PLAYER", "WINNER", "LOSER", "MASTER", "EXPERT", "GENIUS", "LEADER", "MEMBER",
    "PUBLIC", "SECRET", "HIDDEN", "SACRED", "DIVINE", "WONDER", "BATTLE", "COMBAT", "ATTACK", "DEFEND",
    "ESCAPE", "RESCUE", "SEARCH", "TRAVEL", "VOYAGE", "FLIGHT", "DRIVING", "RIDING", "FLYING", "SPORTS"
]

# Fast lookup for some common words before hitting API
EXTRA_VALID_4 = ["GIRL", "BOY", "BABY", "MILK", "BLUE", "PINK", "GOLD", "JUMP", "RUNS", "WALK", "TALK", "SING", "FAST", "SLOW"]
EXTRA_VALID_5 = ["ADULT", "AGENT", "AGREE", "AHEAD", "ALARM", "ALBUM", "ALERT", "ALIEN", "ALTER", "ANGLE", "ANGRY", "APPLY", "ARGUE", "ARISE", "ARMED", "ASSET", "AUDIO", "AUDIT", "AVOID", "AWARD", "AWARE"]
EXTRA_VALID_6 = ["ABROAD", "ACCEPT", "ACCESS", "ACROSS", "ACTING", "ACTIVE", "ACTUAL", "ADVICE", "ADVISE", "AFFECT", "AFFORD", "AFRAID", "AGENCY", "ENJOY", "OBJECT", "OFFICE"]

def get_word_list(length):
    if length == 4: return WORDS_4
    if length == 6: return WORDS_6
    return WORDS_5

async def is_valid_word(word: str, length: int) -> bool:
    """Check if the word is valid locally first, then via Free Dictionary API"""
    word = word.upper()
    
    # 1. Local fast check
    if length == 4 and (word in WORDS_4 or word in EXTRA_VALID_4): return True
    if length == 5 and (word in WORDS_5 or word in EXTRA_VALID_5): return True
    if length == 6 and (word in WORDS_6 or word in EXTRA_VALID_6): return True
    
    # 2. Free API check (api.dictionaryapi.dev)
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{word.lower()}")
            if resp.status_code == 200:
                return True
    except Exception:
        pass # API failed, we reject to be safe from random letters
    return False

# ==========================================
# HELPER FUNCTIONS
# ==========================================
def to_bold_sans(text: str) -> str:
    res = ""
    for char in text.upper():
        if 'A' <= char <= 'Z':
            res += chr(ord(char) - ord('A') + 120276)
        else:
            res += char
    return res

def generate_feedback(guess: str, target: str) -> str:
    result = ["🟥"] * len(target)
    target_chars = list(target)
    guess_chars = list(guess)

    for i in range(len(target)):
        if guess_chars[i] == target_chars[i]:
            result[i] = "🟩"
            target_chars[i] = None
            guess_chars[i] = None

    for i in range(len(target)):
        if guess_chars[i] is not None and guess_chars[i] in target_chars:
            result[i] = "🟨"
            target_chars[target_chars.index(guess_chars[i])] = None

    return " ".join(result)

async def get_new_word(chat_id, length):
    history = await get_word_history(chat_id)
    available = [w for w in get_word_list(length) if w not in history]
    if not available:
        available = get_word_list(length)

    word = random.choice(available)
    await add_word_history(chat_id, word)
    return word

def get_dhaka_date():
    dhaka_tz = datetime.timezone(datetime.timedelta(hours=6))
    now = datetime.datetime.now(dhaka_tz)
    if now.hour < 6:
        now -= datetime.timedelta(days=1)
    return now.strftime("%Y-%m-%d")

def get_daily_word():
    date_str = get_dhaka_date()
    seed = int(hashlib.md5(date_str.encode()).hexdigest(), 16)
    r = random.Random(seed)
    return r.choice(WORDS_5)

async def is_admin_or_auth(client: Client, message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id if message.from_user else (message.sender_chat.id if message.sender_chat else 0)

    auth_users = await get_auth_users(chat_id)
    if user_id in auth_users:
        return True

    try:
        member = await client.get_chat_member(chat_id, user_id)
        if member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            return True
    except: pass
    return False

# ==========================================
# GAME COMMANDS
# ==========================================
@app.on_message(filters.command(["new", "new4", "new5", "new6"], prefixes=config.COMMAND_PREFIXES) & filters.group)
@error
@save
async def start_wordseek(client: Client, message: Message):
    chat_id = message.chat.id
    topic_id = message.message_thread_id
    cmd = message.command[0].lower()

    topics = await get_all_topics(chat_id)
    if topics:
        if topic_id not in topics and topic_id is not None:
            return await message.reply("⚠️ 𝖶𝗈𝗋𝖽𝖲𝖾𝖾𝗄 𝗂𝗌 𝗇𝗈𝗍 𝖺𝗅𝗅𝗈𝗐𝖾𝖽 𝗂𝗇 𝗍𝗁𝗂𝗌 𝗍𝗈𝗉𝗂𝖼.")

    length = 5
    if cmd == "new4": length = 4
    elif cmd == "new6": length = 6
    elif len(message.command) > 1 and message.command[1].isdigit():
        length = int(message.command[1])
        if length not in [4, 5, 6]: length = 5

    if topic_id in topics:
        allowed = topics[topic_id].get("lens", [4, 5, 6])
        if length not in allowed:
            length = topics[topic_id].get("def", allowed[0])
            await message.reply(f"⚠️ 𝖳𝗁𝖺𝗍 𝗅𝖾𝗇𝗀𝗍𝗁 𝗂𝗌 𝗇𝗈𝗍 𝖺𝗅𝗅𝗈𝗐𝖾𝖽 𝗁𝖾𝗋𝖾. 𝖲𝗍𝖺𝗋𝗍𝗂𝗇𝗀 {length}-𝗅𝖾𝗍𝗍𝖾𝗋 𝗀𝖺𝗆𝖾.")

    existing = await get_game(chat_id)
    if existing and existing.get("status"):
        return await message.reply(f"⚠️ 𝖠 𝗀𝖺𝗆𝖾 𝗂𝗌 𝖺𝗅𝗋𝖾𝖺𝖽𝗒 𝗋𝗎𝗇𝗇𝗂𝗇𝗀! 𝖦𝗎𝖾𝗌𝗌 𝗍𝗁𝖾 {existing['len']}-𝗅𝖾𝗍𝗍𝖾𝗋 𝗐𝗈𝗋𝖽.")

    word = await get_new_word(chat_id, length)
    game = {
        "word": word,
        "len": length,
        "guesses": 0,
        "max": 30,
        "status": True,
        "topic": topic_id,
        "history": [],
        "guessed_words": set(),
        "hint_sent": False
    }
    await save_game(chat_id, game)

    await message.reply(f"🎮 **𝖶𝗈𝗋𝖽𝖲𝖾𝖾𝗄 𝖲𝗍𝖺𝗋𝗍𝖾𝖽!**\n\n𝖨 𝗁𝖺𝗏𝖾 𝗁𝗂𝖽𝖽𝖾𝗇 𝖺 **{length}-𝗅𝖾𝗍𝗍𝖾𝗋** 𝗐𝗈𝗋𝖽.\n𝖲𝗍𝖺𝗋𝗍 𝗀𝗎𝖾𝗌𝗌𝗂𝗇𝗀 𝖻𝗒 𝗌𝖾𝗇𝖽𝗂𝗇𝗀 𝖺 {length}-𝗅𝖾𝗍𝗍𝖾𝗋 𝗐𝗈𝗋𝖽!\n\n*(Max 30 guesses)*")

@app.on_message(filters.command("end", prefixes=config.COMMAND_PREFIXES) & filters.group)
@error
@save
async def end_wordseek(client: Client, message: Message):
    chat_id = message.chat.id
    game = await get_game(chat_id)
    if not game or not game.get("status"):
        return await message.reply("⚠️ 𝖭𝗈 𝖺𝖼𝗍𝗂𝗏𝖾 𝗀𝖺𝗆𝖾 𝗍𝗈 𝖾𝗇𝖽.")

    if not await is_admin_or_auth(client, message):
        return await message.reply("⚠️ 𝖮𝗇𝗅𝗒 𝖺𝖽𝗆𝗂𝗇𝗌 𝗈𝗋 𝖺𝗎𝗍𝗁𝗈𝗋𝗂𝗓𝖾𝖽 𝗎𝗌𝖾𝗋𝗌 𝖼𝖺𝗇 𝖾𝗇𝖽 𝗍𝗁𝖾 𝗀𝖺𝗆𝖾.")

    word = game["word"]
    game["status"] = False
    await save_game(chat_id, game)
    await message.reply(f"🛑 **𝖦𝖺𝗆𝖾 𝖤𝗇𝖽𝖾𝖽!**\n\n𝖳𝗁𝖾 𝗐𝗈𝗋𝖽 𝗐𝖺𝗌: **{word}**")

@app.on_message(filters.command("daily", prefixes=config.COMMAND_PREFIXES) & filters.private)
@error
@save
async def daily_wordseek(client: Client, message: Message):
    user_id = message.from_user.id
    date_str = get_dhaka_date()

    if await is_daily_paused(user_id):
        await set_daily_paused(user_id, False)
        await message.reply("▶️ **𝖣𝖺𝗂𝗅𝗒 𝖬𝗈𝖽𝖾 𝖱𝖾𝗌𝗎𝗆𝖾𝖽.**")

    existing = await get_daily(user_id)
    if existing and existing["date"] == date_str:
        if not existing["status"]:
            return await message.reply(f"⚠️ 𝖸𝗈𝗎 𝗁𝖺𝗏𝖾 𝖺𝗅𝗋𝖾𝖺𝖽𝗒 𝖼𝗈𝗆𝗉𝗅𝖾𝗍𝖾𝖽 𝗍𝗈𝖽𝖺𝗒's 𝖣𝖺𝗂𝗅𝗒 𝖶𝗈𝗋𝖽𝖲𝖾𝖾𝗄!\n𝖢𝗈𝗆𝖾 𝖻𝖺𝖼𝗄 𝗍𝗈𝗆𝗈𝗋𝗋𝗈𝗐 𝖺𝗍 𝟢𝟨:𝟢𝟢 (𝖦𝖬𝖳+𝟨).")
        return await message.reply(f"⚠️ 𝖸𝗈𝗎𝗋 𝖽𝖺𝗂𝗅𝗒 𝗀𝖺𝗆𝖾 𝗂𝗌 𝖺𝗅𝗋𝖾𝖺𝖽𝗒 𝗋𝗎𝗇𝗇𝗂𝗇𝗀. 𝖦𝗎𝖾𝗌𝗌 𝗍𝗁𝖾 𝟧-𝗅𝖾𝗍𝗍𝖾𝗋 𝗐𝗈𝗋𝖽!")

    game = {
        "date": date_str,
        "word": get_daily_word(),
        "len": 5,
        "guesses": 0,
        "max": 6,
        "status": True,
        "history": [],
        "guessed_words": set()
    }
    await save_daily(user_id, game)
    await message.reply("📅 **𝖣𝖺𝗂𝗅𝗒 𝖶𝗈𝗋𝖽𝖲𝖾𝖾𝗄 𝖲𝗍𝖺𝗋𝗍𝖾𝖽!**\n\n𝖦𝗎𝖾𝗌𝗌 𝗍𝗈𝖽𝖺𝗒'𝗌 **𝟧-𝗅𝖾𝗍𝗍𝖾𝗋** 𝗐𝗈𝗋𝖽 𝗂𝗇 𝟨 𝗍𝗋𝗂𝖾𝗌.")

@app.on_message(filters.command("pausedaily", prefixes=config.COMMAND_PREFIXES) & filters.private)
@error
@save
async def pause_daily(client: Client, message: Message):
    await set_daily_paused(message.from_user.id, True)
    await message.reply("⏸ **𝖣𝖺𝗂𝗅𝗒 𝖬𝗈𝖽𝖾 𝖯𝖺𝗎𝗌𝖾𝖽.**\n𝖸𝗈𝗎 𝖼𝖺𝗇 𝗇𝗈𝗐 𝗉𝗅𝖺𝗒 𝗇𝗈𝗋𝗆𝖺𝗅 𝗀𝖺𝗆𝖾𝗌. 𝖴𝗌𝖾 /𝖽𝖺𝗂𝗅𝗒 𝗍𝗈 𝗋𝖾𝗌𝗎𝗆𝖾.")

# ==========================================
# GAMEPLAY (TEXT LISTENER)
# ==========================================
# NOTE: pyrogram runs every handler GROUP independently regardless of order
# (an exception or missing ContinuePropagation in one group does NOT block
# other groups - only an explicit StopPropagation would, which this handler
# never raises). So this doesn't need to "win the race" with a negative/
# priority group number - it just gets its own ordinary, dedicated group
# like every other feature in Nobara.
@app.on_message(filters.text & ~filters.command(["new", "new4", "new5", "new6", "end", "daily", "pausedaily", "score", "seekauth", "setgametopic", "unsetgametopic", "allowonlylen", "recreatetopic"]), group=WORDSEEK_GROUP)
@error
async def process_guess(client: Client, message: Message):
    original_text = message.text.strip()
    text = original_text.upper()
    chat_id = message.chat.id
    user_id = message.from_user.id if message.from_user else (message.sender_chat.id if message.sender_chat else 0)
    username = message.from_user.username if message.from_user else None
    name = message.from_user.first_name if message.from_user else "Admin"

    if " " in text or not text.isalpha():
        raise ContinuePropagation

    is_private = message.chat.type.name == "PRIVATE"

    # --- Daily Mode Processing ---
    if is_private:
        game = await get_daily(user_id)
        paused = await is_daily_paused(user_id)
        if game and game["status"] and not paused:
            if len(text) != 5:
                raise ContinuePropagation

            if not await is_valid_word(text, 5):
                await message.reply(f"**{name}:**\n{original_text}\n\n**WordSeek:**\n{original_text.lower()} is not a valid 5-letter word.")
                return

            if text in game["guessed_words"]:
                await message.reply(f"**{name}:**\n{original_text}\n\n**WordSeek:**\nSomeone has already guessed your word. Please try another one!")
                return

            game["guessed_words"].add(text)
            game["guesses"] += 1
            feedback = generate_feedback(text, game["word"])
            bold_guess = to_bold_sans(text)
            game["history"].append(f"{feedback} {bold_guess}")

            board_text = f"WordSeek Daily:\n5-letter mode · {game['guesses']}/6\n\n" + "\n".join(game["history"])

            if text == game["word"]:
                game["status"] = False
                streak = await bump_streak(user_id)
                await record_score_event("daily", user_id, 5, 5, username)
                await save_daily(user_id, game)
                await message.reply(f"{board_text}\n\n🎉 **Great job!** You solved the Daily WordSeek in {game['guesses']}/6 tries!\n🔥 Current Streak: **{streak}**\n🌟 You earned **5 XP**!")
            elif game["guesses"] >= game["max"]:
                game["status"] = False
                await reset_streak(user_id)
                await save_daily(user_id, game)
                await message.reply(f"{board_text}\n\n💔 **Game Over!** Maximum guesses reached.\nThe word was: **{game['word']}**\nYour streak has been reset.")
            else:
                await save_daily(user_id, game)
                await message.reply(board_text)
            return

    # --- Group Mode Processing ---
    game = await get_game(chat_id)
    if game and game.get("status"):
        topic_id = message.message_thread_id

        if game.get("topic") is not None and game["topic"] != topic_id:
            raise ContinuePropagation

        if len(text) == game["len"]:
            if not await is_valid_word(text, game["len"]):
                await message.reply(f"**{name}:**\n{original_text}\n\n**WordSeek:**\n{original_text.lower()} is not a valid {game['len']}-letter word.")
                return

            if text in game["guessed_words"]:
                await message.reply(f"**{name}:**\n{original_text}\n\n**WordSeek:**\nSomeone has already guessed your word. Please try another one!")
                return

            game["guessed_words"].add(text)
            game["guesses"] += 1
            feedback = generate_feedback(text, game["word"])
            bold_guess = to_bold_sans(text)
            game["history"].append(f"{feedback} {bold_guess}")

            board_text = f"WordSeek:\n{game['len']}-letter mode · {game['guesses']}/{game['max']}\n\n" + "\n".join(game["history"])

            if text == game["word"]:
                game["status"] = False

                if game["guesses"] <= 10: xp = 5
                elif game["guesses"] <= 20: xp = 3
                else: xp = 1

                await record_score_event(chat_id, user_id, game["len"], xp, username)
                await save_game(chat_id, game)

                await message.reply(f"{board_text}\n\n🎉 **{name} won!**\n🌟 You earned **{xp} XP**!\nThe word was **{game['word']}**.\n*(Total guesses: {game['guesses']})*")
                return

            elif game["guesses"] >= game["max"]:
                game["status"] = False
                await save_game(chat_id, game)
                await message.reply(f"{board_text}\n\n💔 **Game Over!** Maximum guesses reached.\nThe word was: **{game['word']}**")
                return

            else:
                if game["guesses"] >= 15 and not game["hint_sent"]:
                    game["hint_sent"] = True

                await save_game(chat_id, game)
                await message.reply(board_text)

                if game["guesses"] >= 15 and game["history"][-1] == f"{feedback} {bold_guess}":
                    async def fetch_and_send_hint():
                        target_word = game["word"]
                        sys_prompt = "You are a fun game master providing cryptic hints."
                        prompt = f"Give a very short, clever 1-sentence riddle or hint for the word '{target_word}'. DO NOT use the word '{target_word}' itself in the hint."
                        hint_text, _ = await get_ai_response(prompt, system_prompt=sys_prompt)
                        current_game = await get_game(chat_id)
                        if hint_text and current_game and current_game.get("status"):
                            await client.send_message(chat_id, f"💡 **Smart Hint:**\n{hint_text}", reply_to_message_id=message.id)
                    asyncio.create_task(fetch_and_send_hint())
                return

    raise ContinuePropagation

# ==========================================
# ADVANCED LEADERBOARD & SCORES DASHBOARD
# ==========================================
async def get_lb_text(client: Client, chat_id: int, scope: str, length: str, period: str):
    scores_list = await get_leaderboard(scope, chat_id, length, period)
    scope_name = "Group" if scope == "grp" else "Global"

    period_map = {"tdy": "Today", "wk": "This Week", "mo": "This Month", "yr": "This Year", "all": "All Time"}
    p_name = period_map.get(period, "All Time")

    text = f"🏆 **{scope_name} Leaderboard ({length}-Letters)**\n"
    text += f"📅 **Period:** `{p_name}`\n\n"

    if not scores_list:
        text += "𝖭𝗈 𝗌𝖼𝗈𝗋𝖾𝗌 𝗒𝖾𝗍 𝗂𝗇 𝗍𝗁𝗂𝗌 𝖼𝖺𝗍𝖾𝗀𝗈𝗋𝗒!"
    else:
        for i, (uid, sc) in enumerate(scores_list, 1):
            try:
                u = await client.get_users(uid)
                name = u.first_name if u.first_name else "User"
            except:
                name = f"User {uid}"
            text += f"**{i}.** [{name}](tg://user?id={uid}) ⪧ `{sc}` 𝗐𝗂𝗇𝗌\n"

    return text

async def get_profile_text(client: Client, target_id: int):
    try:
        u = await client.get_users(target_id)
        name = u.first_name if u.first_name else "User"
    except:
        name = f"User {target_id}"

    w4, w5, w6, xp = await get_user_totals(target_id)
    streak = await get_streak(target_id)

    text = f"📊 **𝖲𝖼𝗈𝗋𝖾 𝖯𝗋𝗈𝖿𝗂𝗅𝖾**\n👤 **[{name}](tg://user?id={target_id})**\n\n"
    text += f"🎮 **𝖶𝗈𝗋𝖽𝖲𝖾𝖾𝗄 𝖲𝗍𝖺𝗍𝗌:**\n"
    text += f" ├ 🕹 4-𝖫𝖾𝗍𝗍𝖾𝗋 𝖶𝗂𝗇𝗌: `{w4}`\n"
    text += f" ├ 🕹 5-𝖫𝖾𝗍𝗍𝖾𝗋 𝖶𝗂𝗇𝗌: `{w5}`\n"
    text += f" └ 🕹 6-𝖫𝖾𝗍𝗍𝖾𝗋 𝖶𝗂𝗇𝗌: `{w6}`\n\n"
    text += f"🔥 **𝖣𝖺𝗂𝗅𝗒 𝖲𝗍𝗋𝖾𝖺𝗄:** `{streak}`\n"
    text += f"🌟 **𝖳𝗈𝗍𝖺𝗅 𝖶𝗈𝗋𝖽𝖲𝖾𝖾𝗄 𝖷𝖯:** `{xp}` *(𝖺𝖽𝖽𝖾𝖽 𝗍𝗈 𝗒𝗈𝗎𝗋 𝗆𝖺𝗂𝗇 𝗐𝖺𝗅𝗅𝖾𝗍, 𝗎𝗌𝖾 /bal 𝗍𝗈 𝖼𝗁𝖾𝖼𝗄)*"
    return text

def get_lb_kb(scope, length, period, target_id):
    cb = lambda s, l, p: f"wslb|{s}|{l}|{p}|{target_id}"
    
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👥 Group ✅" if scope=="grp" else "👥 Group", callback_data=cb("grp", length, period)),
            InlineKeyboardButton("🌍 Global ✅" if scope=="glb" else "🌍 Global", callback_data=cb("glb", length, period))
        ],
        [
            InlineKeyboardButton("4-Letter ✅" if length=="4" else "4-Letter", callback_data=cb(scope, "4", period)),
            InlineKeyboardButton("5-Letter ✅" if length=="5" else "5-Letter", callback_data=cb(scope, "5", period)),
            InlineKeyboardButton("6-Letter ✅" if length=="6" else "6-Letter", callback_data=cb(scope, "6", period))
        ],
        [
            InlineKeyboardButton("Today ✅" if period=="tdy" else "Today", callback_data=cb(scope, length, "tdy")),
            InlineKeyboardButton("This Week ✅" if period=="wk" else "This Week", callback_data=cb(scope, length, "wk")),
            InlineKeyboardButton("This Month ✅" if period=="mo" else "This Month", callback_data=cb(scope, length, "mo"))
        ],
        [
            InlineKeyboardButton("This Year ✅" if period=="yr" else "This Year", callback_data=cb(scope, length, "yr")),
            InlineKeyboardButton("All Time ✅" if period=="all" else "All Time", callback_data=cb(scope, length, "all"))
        ],
        [
            InlineKeyboardButton("🔄 Refresh", callback_data=cb(scope, length, period)),
            InlineKeyboardButton("👤 My Profile", callback_data=f"wsprof|{target_id}")
        ],
        [InlineKeyboardButton("❌ Close", callback_data="ws_close")]
    ])

def get_profile_kb(target_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏆 Back to Leaderboard", callback_data=f"wslb|grp|5|all|{target_id}")],
        [InlineKeyboardButton("🔄 Refresh", callback_data=f"wsprof|{target_id}")],
        [InlineKeyboardButton("❌ Close", callback_data="ws_close")]
    ])

@app.on_message(filters.command("score", prefixes=config.COMMAND_PREFIXES) & filters.group)
@error
@save
async def score_cmd(client: Client, message: Message):
    target_id = message.from_user.id
    show_profile = False
    
    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
        show_profile = True
    elif len(message.command) > 1:
        try:
            u = await client.get_users(message.command[1])
            target_id = u.id
            show_profile = True
        except: pass
        
    if show_profile:
        text = await get_profile_text(client, target_id)
        kb = get_profile_kb(target_id)
    else:
        text = await get_lb_text(client, message.chat.id, "grp", "5", "all")
        kb = get_lb_kb("grp", "5", "all", target_id)
        
    await message.reply(text, reply_markup=kb)

@app.on_callback_query(filters.regex(r"^wslb\|"))
@error
async def wslb_callback(client: Client, query: CallbackQuery):
    _, scope, length, period, target_id = query.data.split("|")
    text = await get_lb_text(client, query.message.chat.id, scope, length, period)
    kb = get_lb_kb(scope, length, period, target_id)
    
    try:
        await query.message.edit_text(text, reply_markup=kb)
        await query.answer("Refreshed!", show_alert=False)
    except MessageNotModified:
        await query.answer("Already up to date!", show_alert=False)

@app.on_callback_query(filters.regex(r"^wsprof\|"))
@error
async def wsprof_callback(client: Client, query: CallbackQuery):
    target_id = int(query.data.split("|")[1])
    text = await get_profile_text(client, target_id)
    
    try:
        await query.message.edit_text(text, reply_markup=get_profile_kb(target_id))
        await query.answer("Profile Refreshed!", show_alert=False)
    except MessageNotModified:
        await query.answer("Already up to date!", show_alert=False)

@app.on_callback_query(filters.regex(r"^ws_close$"))
@error
async def close_callback(client: Client, query: CallbackQuery):
    await query.message.delete()

# ==========================================
# GROUP SETTINGS (Admin Only)
# ==========================================
@app.on_message(filters.command("seekauth", prefixes=config.COMMAND_PREFIXES) & filters.group)
@error
@save
async def seekauth_cmd(client: Client, message: Message):
    chat_id = message.chat.id
    if not await is_admin_or_auth(client, message):
        return await message.reply("⚠️ 𝖠𝖽𝗆𝗂𝗇 𝗈𝗇𝗅𝗒.")

    if len(message.command) == 1:
        return await message.reply("𝖴𝗌𝖺𝗀𝖾: `/𝗌𝖾𝖾𝗄𝖺𝗎𝗍𝗁 @𝗎𝗌𝖾𝗋𝗇𝖺𝗆𝖾` 𝗈𝗋 `/𝗌𝖾𝖾𝗄𝖺𝗎𝗍𝗁 𝗋𝖾𝗆𝗈𝗏𝖾 @𝗎𝗌𝖾𝗋𝗇𝖺𝗆𝖾` 𝗈𝗋 `/𝗌𝖾𝖾𝗄𝖺𝗎𝗍𝗁 𝗅𝗂𝗌𝗍`")

    action = message.command[1].lower()

    if action == "list":
        auth_users = await get_auth_users(chat_id)
        if not auth_users: return await message.reply("𝖭𝗈 𝖺𝗎𝗍𝗁𝗈𝗋𝗂𝗓𝖾𝖽 𝗎𝗌𝖾𝗋𝗌.")
        txt = "🛡 **𝖠𝗎𝗍𝗁𝗈𝗋𝗂𝗓𝖾𝖽 𝖴𝗌𝖾𝗋𝗌:**\n"
        for uid in auth_users: txt += f"• `{uid}`\n"
        return await message.reply(txt)

    target_user = None
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user.id
    else:
        try:
            u = await client.get_users(message.command[2] if action == "remove" else message.command[1])
            target_user = u.id
        except: return await message.reply("⚠️ 𝖴𝗌𝖾𝗋 𝗇𝗈𝗍 𝖿𝗈𝗎𝗇𝖽.")

    if action == "remove":
        await remove_auth_user(chat_id, target_user)
        await message.reply("✅ 𝖴𝗌𝖾𝗋 𝗋𝖾𝗆𝗈𝗏𝖾𝖽 𝖿𝗋𝗈𝗆 𝖺𝗎𝗍𝗁.")
    else:
        await add_auth_user(chat_id, target_user)
        await message.reply("✅ 𝖴𝗌𝖾𝗋 𝖺𝗎𝗍𝗁𝗈𝗋𝗂𝗓𝖾𝖽 𝗍𝗈 𝗆𝖺𝗇𝖺𝗀𝖾 𝗀𝖺𝗆𝖾𝗌.")

@app.on_message(filters.command("setgametopic", prefixes=config.COMMAND_PREFIXES) & filters.group)
@error
@save
async def set_topic(client: Client, message: Message):
    if not await is_admin_or_auth(client, message): return
    chat_id = message.chat.id
    topic_id = message.message_thread_id
    if topic_id is None: return await message.reply("⚠️ 𝖯𝗅𝖾𝖺𝗌𝖾 𝗋𝗎𝗇 𝗍𝗁𝗂𝗌 𝗂𝗇𝗌𝗂𝖽𝖾 𝖺 𝗍𝗈𝗉𝗂𝖼.")

    await set_topic_settings(chat_id, topic_id)
    await message.reply("✅ **𝖦𝖺𝗆𝖾𝗌 𝖺𝗋𝖾 𝗇𝗈𝗐 𝗋𝖾𝗌𝗍𝗋𝗂𝖼𝗍𝖾𝖽 𝗍𝗈 𝗍𝗁𝗂𝗌 𝗍𝗈𝗉𝗂𝖼!**")

@app.on_message(filters.command("unsetgametopic", prefixes=config.COMMAND_PREFIXES) & filters.group)
@error
@save
async def unset_topic(client: Client, message: Message):
    if not await is_admin_or_auth(client, message): return
    chat_id = message.chat.id
    topic_id = message.message_thread_id
    await delete_topic_settings(chat_id, topic_id)
    await message.reply("✅ **𝖳𝗈𝗉𝗂𝖼 𝗋𝖾𝗌𝗍𝗋𝗂𝖼𝗍𝗂𝗈𝗇 𝗋𝖾𝗆𝗈𝗏𝖾𝖽.**")

@app.on_message(filters.command("allowonlylen", prefixes=config.COMMAND_PREFIXES) & filters.group)
@error
@save
async def set_lengths(client: Client, message: Message):
    if not await is_admin_or_auth(client, message): return
    chat_id = message.chat.id
    topic_id = message.message_thread_id
    settings = await get_topic_settings(chat_id, topic_id)
    if not settings:
        return await message.reply("⚠️ 𝖯𝗅𝖾𝖺𝗌𝖾 𝗌𝖾𝗍 𝗍𝗁𝗂𝗌 𝗍𝗈𝗉𝗂𝖼 𝖺𝗌 𝖺 𝗀𝖺𝗆𝖾 𝗍𝗈𝗉𝗂𝖼 𝖿𝗂𝗋𝗌𝗍 𝗎𝗌𝗂𝗇𝗀 /𝗌𝖾𝗍𝗀𝖺𝗆𝖾𝗍𝗈𝗉𝗂𝖼.")

    if len(message.command) < 2: return await message.reply("𝖴𝗌𝖺𝗀𝖾: `/𝖺𝗅𝗅𝗈𝗐𝗈𝗇𝗅𝗒𝗅𝖾𝗇 𝟦 𝟧`")

    lens = [int(x) for x in message.command[1:] if x in ["4", "5", "6"]]
    if not lens: return await message.reply("⚠️ 𝖨𝗇𝗏𝖺𝗅𝗂𝖽 𝗅𝖾𝗇𝗀𝗍𝗁𝗌. 𝖴𝗌𝖾 𝟦, 𝟧, 𝗈𝗋 𝟨.")

    await set_topic_settings(chat_id, topic_id, lens=lens, **{"def": lens[0]})
    await message.reply(f"✅ **𝖠𝗅𝗅𝗈𝗐𝖾𝖽 𝗐𝗈𝗋𝖽 𝗅𝖾𝗇𝗀𝗍𝗁𝗌 𝗂𝗇 𝗍𝗁𝗂𝗌 𝗍𝗈𝗉𝗂𝖼:** {', '.join(map(str, lens))}")

@app.on_message(filters.command("recreatetopic", prefixes=config.COMMAND_PREFIXES) & filters.group)
@error
@save
async def recreate_topic(client: Client, message: Message):
    if not await is_admin_or_auth(client, message): return
    chat_id = message.chat.id
    topic_id = message.message_thread_id
    settings = await get_topic_settings(chat_id, topic_id)
    if not settings:
        return await message.reply("⚠️ 𝖯𝗅𝖾𝖺𝗌𝖾 𝗌𝖾𝗍 𝗍𝗁𝗂𝗌 𝗍𝗈𝗉𝗂𝖼 𝖺𝗌 𝖺 𝗀𝖺𝗆𝖾 𝗍𝗈𝗉𝗂𝖼 𝖿𝗂𝗋𝗌𝗍 𝗎𝗌𝗂𝗇𝗀 /𝗌𝖾𝗍𝗀𝖺𝗆𝖾𝗍𝗈𝗉𝗂𝖼.")

    state = message.command[1].lower() if len(message.command) > 1 else "on"
    await set_topic_settings(chat_id, topic_id, recreate=(state == "on"))
    await message.reply(f"✅ **𝖠𝗎𝗍𝗈-𝗋𝖾𝖼𝗋𝖾𝖺𝗍𝖾 𝗍𝗈𝗉𝗂𝖼:** {'𝖤𝗇𝖺𝖻𝗅𝖾𝖽' if state == 'on' else '𝖣𝗂𝗌𝖺𝖻𝗅𝖾𝖽'}")

# ==========================================
# HELP MENU
# ==========================================
__module__ = "𝖶𝗈𝗋𝖽𝖲𝖾𝖾𝗄"

__help__ = """▸ **𝖧𝗈𝗐 𝗍𝗈 𝖯𝗅𝖺𝗒 𝖶𝗈𝗋𝖽𝖲𝖾𝖾𝗄**

𝟣. 𝖲𝗍𝖺𝗋𝗍 𝖺 𝗀𝖺𝗆𝖾 𝗎𝗌𝗂𝗇𝗀 `/𝗇𝖾𝗐`, `/𝗇𝖾𝗐𝟦`, `/𝗇𝖾𝗐𝟧`, 𝗈𝗋 `/𝗇𝖾𝗐𝟨`
𝟤. 𝖦𝗎𝖾𝗌𝗌 𝗍𝗁𝖾 𝗁𝗂𝖽𝖽𝖾𝗇 𝗐𝗈𝗋𝖽.
𝟥. 𝖠𝖿𝗍𝖾𝗋 𝖾𝖺𝖼𝗁 𝗀𝗎𝖾𝗌𝗌, 𝗒𝗈𝗎'𝗅𝗅 𝗀𝖾𝗍 𝖼𝗈𝗅𝗈𝗋 𝗁𝗂𝗇𝗍𝗌:
   🟩 𝖢𝗈𝗋𝗋𝖾𝖼𝗍 𝗅𝖾𝗍𝗍𝖾𝗋 𝗂𝗇 𝗍𝗁𝖾 𝗋𝗂𝗀𝗁𝗍 𝗌𝗉𝗈𝗍
   🟨 𝖢𝗈𝗋𝗋𝖾𝖼𝗍 𝗅𝖾𝗍𝗍𝖾𝗋 𝗂𝗇 𝗍𝗁𝖾 𝗐𝗋𝗈𝗇𝗀 𝗌𝗉𝗈𝗍
   🟥 𝖫𝖾𝗍𝗍𝖾𝗋 𝗇𝗈𝗍 𝗂𝗇 𝗍𝗁𝖾 𝗐𝗈𝗋𝖽
𝟦. 𝖥𝗂𝗋𝗌𝗍 𝗉𝖾𝗋𝗌𝗈𝗇 𝗍𝗈 𝗀𝗎𝖾𝗌𝗌 𝖼𝗈𝗋𝗋𝖾𝖼𝗍𝗅𝗒 𝗐𝗂𝗇𝗌! (𝖬𝖺𝗑 𝟥𝟢 𝗀𝗎𝖾𝗌𝗌𝖾𝗌)
𝟧. 𝖥𝖺𝗌𝗍𝖾𝗌𝗍 𝗐𝗂𝗇𝗇𝖾𝗋𝗌 𝗀𝖾𝗍 𝗆𝗈𝗋𝖾 𝖷𝖯 (𝟧, 𝟥, 𝗈𝗋 𝟣 𝖷𝖯 𝖻𝖺𝗌𝖾𝖽 𝗈𝗇 𝗀𝗎𝖾𝗌𝗌𝖾𝗌) - 𝗍𝗁𝗂𝗌 𝖷𝖯 𝗀𝗈𝖾𝗌 𝗌𝗍𝗋𝖺𝗂𝗀𝗁𝗍 𝗍𝗈 𝗒𝗈𝗎𝗋 𝗆𝖺𝗂𝗇 𝗐𝖺𝗅𝗅𝖾𝗍!

▸ **𝖡𝖺𝗌𝗂𝖼 𝖢𝗈𝗆𝗆𝖺𝗇𝖽𝗌:**
• `/𝗇𝖾𝗐` - 𝖲𝗍𝖺𝗋𝗍 𝖺 𝗇𝖾𝗐 𝗀𝖺𝗆𝖾 (𝖽𝖾𝖿𝖺𝗎𝗅𝗍 𝟧 𝗅𝖾𝗍𝗍𝖾𝗋𝗌)
• `/𝖾𝗇𝖽` - 𝖤𝗇𝖽 𝖼𝗎𝗋𝗋𝖾𝗇𝗍 𝗀𝖺𝗆𝖾 (𝖺𝖽𝗆𝗂𝗇/𝖺𝗎𝗍𝗁 𝗈𝗇𝗅𝗒)
• `/𝗌𝖼𝗈𝗋𝖾` - 𝖵𝗂𝖾𝗐 𝖫𝖾𝖺𝖽𝖾𝗋𝖻𝗈𝖺𝗋𝖽 & 𝖸𝗈𝗎𝗋 𝖯𝗋𝗈𝖿𝗂𝗅𝖾.
• `/𝖽𝖺𝗂𝗅𝗒` (𝖯𝖬 𝗈𝗇𝗅𝗒) - 𝖯𝗅𝖺𝗒 𝗍𝗈𝖽𝖺𝗒'𝗌 𝟧-𝗅𝖾𝗍𝗍𝖾𝗋 𝖽𝖺𝗂𝗅𝗒 𝗐𝗈𝗋𝖽.
• `/𝗉𝖺𝗎𝗌𝖾𝖽𝖺𝗂𝗅𝗒` (𝖯𝖬 𝗈𝗇𝗅𝗒) - 𝖯𝖺𝗎𝗌𝖾 𝖽𝖺𝗂𝗅𝗒 𝗆𝗈𝖽𝖾.

▸ **𝖠𝖽𝗆𝗂𝗇 𝖢𝗈𝗆𝗆𝖺𝗇𝖽𝗌:**
• `/𝗌𝖾𝖾𝗄𝖺𝗎𝗍𝗁` - 𝖬𝖺𝗇𝖺𝗀𝖾 𝗎𝗌𝖾𝗋𝗌 𝗐𝗁𝗈 𝖼𝖺𝗇 𝖾𝗇𝖽 𝗀𝖺𝗆𝖾𝗌.
• `/𝗌𝖾𝗍𝗀𝖺𝗆𝖾𝗍𝗈𝗉𝗂𝖼` - 𝖱𝖾𝗌𝗍𝗋𝗂𝖼𝗍 𝗀𝖺𝗆𝖾𝗌 𝗍𝗈 𝖺 𝗌𝗉𝖾𝖼𝗂𝖿𝗂𝖼 𝗍𝗈𝗉𝗂𝖼.
• `/𝗎𝗇𝗌𝖾𝗍𝗀𝖺𝗆𝖾𝗍𝗈𝗉𝗂𝖼` - 𝖱𝖾𝗆𝗈𝗏𝖾 𝗍𝗈𝗉𝗂𝖼 𝗋𝖾𝗌𝗍𝗋𝗂𝖼𝗍𝗂𝗈𝗇.
• `/𝖺𝗅𝗅𝗈𝗐𝗈𝗇𝗅𝗒𝗅𝖾𝗇` - 𝖱𝖾𝗌𝗍𝗋𝗂𝖼𝗍 𝗐𝗈𝗋𝖽 𝗅𝖾𝗇𝗀𝗍𝗁𝗌 𝗂𝗇 𝖺 𝗍𝗈𝗉𝗂𝖼.

𝖠𝗅𝗅 𝗀𝖺𝗆𝖾 𝗌𝗍𝖺𝗍𝖾, 𝗌𝖼𝗈𝗋𝖾𝗌, 𝖺𝗇𝖽 𝗌𝖾𝗍𝗍𝗂𝗇𝗀𝗌 𝖺𝗋𝖾 𝗌𝖺𝗏𝖾𝖽 𝗍𝗈 𝗍𝗁𝖾 𝖽𝖺𝗍𝖺𝖻𝖺𝗌𝖾, 𝗌𝗈 𝗇𝗈𝗍𝗁𝗂𝗇𝗀 𝗂𝗌 𝗅𝗈𝗌𝗍 𝗂𝖿 𝗍𝗁𝖾 𝖻𝗈𝗍 𝗋𝖾𝗌𝗍𝖺𝗋𝗍𝗌.
"""
