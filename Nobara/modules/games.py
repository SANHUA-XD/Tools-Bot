import datetime,pymongo
import random
from Nobara import app
from pyrogram import filters
from Nobara.database.game_db import *
import asyncio
import json
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import config
from Nobara.decorator.save import save
from Nobara.decorator.errors import error

# Load Sudoers JSON
with open("sudoers.json", "r") as f:
    SUDOERS = json.load(f)

# Combine all roles into SUPREME_USERS
SUPREME_USERS = (
    SUDOERS.get("Hokages", [])
    + SUDOERS.get("Jonins", [])
    + SUDOERS.get("Chunins", [])
    + SUDOERS.get("Genins", [])
)

def get_readable_time(seconds: int) -> str:
    time_string = ""
    if seconds < 0:
        raise ValueError("Input value must be non-negative")

    if seconds < 60:
        time_string = f"{round(seconds)}s"
    else:
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)
        if days > 0:
            time_string += f"{round(days)}days, "
        if hours > 0:
            time_string += f"{round(hours)}h:"
        time_string += f"{round(minutes)}m:{round(seconds):02d}s"

    return time_string


with open('trivia.json', 'r') as file:
    data = json.load(file)


async def get_user_won(emoji,value):
    if emoji in ['🎯','🎳']:
        if value >= 4:
            u_won = True
        else:
            u_won = False
    elif emoji in ['🏀','⚽'] :
        if value >= 3:
            u_won = True
        else:
            u_won = False
    return u_won


@app.on_message(filters.command("daily", prefixes=config.COMMAND_PREFIXES))
@error
@save
async def _daily(client,message):
    user_id = message.from_user.id
    if not await is_player(user_id):
        await create_account(user_id,message.from_user.username)
    coins = await user_wallet(user_id)
    x,y = await can_collect_coins(user_id)
    if x is True:
        await gamesdb.update_one({'user_id' : user_id},{'$set' : {'coins' : coins + 10000}},upsert=True)
        await write_last_collection_time_today(user_id,datetime.datetime.now().timestamp())
        return await message.reply_text("🎁 Yᴏᴜ ʜᴀᴠᴇ ᴄʟᴀɪᴍᴇᴅ ʏᴏᴜʀ ᴅᴀɪʟʏ ʙᴏɴᴜs ᴏғ 10,𝟶𝟶𝟶 XP!\n• Cᴜʀʀᴇɴᴛ ʙᴀʟᴀɴᴄᴇ ✑ `{0:,}`XP".format(coins+10000))    
    await message.reply_text("ʏᴏᴜ ᴄᴀɴ ᴄʟᴀɪᴍ ʏᴏᴜʀ ᴅᴀɪʟʏ ʙᴏɴᴜs ɪɴ ᴀʀᴏᴜɴᴅ `{0}`".format(get_readable_time(y)))  
    
    
    
@app.on_message(filters.command("weekly", prefixes=config.COMMAND_PREFIXES))
@error
@save
async def _weekly(client,message):
    user_id = message.from_user.id
    if not await is_player(user_id):
        await create_account(user_id,message.from_user.username)
    coins = await user_wallet(user_id)
    x,y = await can_collect(user_id)
    if x is True:
        await gamesdb.update_one({'user_id' : user_id},{'$set' : {'coins' : coins + 50000}},upsert=True)
        await write_last_collection_time_weekly(user_id,datetime.datetime.now().timestamp())
        return await message.reply_text("🎁 Yᴏᴜ ʜᴀᴠᴇ ᴄʟᴀɪᴍᴇᴅ ʏᴏᴜʀ ᴡᴇᴇᴋʟʏ ʙᴏɴᴜs ᴏғ 50,000 XP!\n• ᴛᴏᴛᴀʟ XP ✑ `{0:,}` XP".format(coins+50000))    
    await message.reply_text("ʏᴏᴜ ᴄᴀɴ ᴄʟᴀɪᴍ ʏᴏᴜʀ ᴡᴇᴇᴋʟʏ ʙᴏɴᴜs ɪɴ ᴀʀᴏᴜɴᴅ `{0}`".format(get_readable_time(y)))
                         
                             
                             
async def can_play(tame,tru):
  current_time = datetime.datetime.now()
  time_since_last_collection = current_time - datetime.datetime.fromtimestamp(tame)
  x = tru - time_since_last_collection.total_seconds()
  if str(x).startswith('-'):
      return 0
  return x
  

BET_DICT = {}
DART_DICT = {}
BOWL_DICT = {}
BASKET_DICT = {}
TRIVIA_DICT = {}


@app.on_message(filters.command("trivia", prefixes=config.COMMAND_PREFIXES))
@error
@save
async def _trivia(client, message):
    chat_id = message.chat.id
    user = message.from_user
    if not await is_player(user.id):
        await create_account(user.id, message.from_user.username)
    if user.id not in TRIVIA_DICT.keys():
        TRIVIA_DICT[user.id] = None
    if TRIVIA_DICT[user.id]:
        x = await can_play(TRIVIA_DICT[user.id], 10 * 60)
        if int(x) != 0:
            return await message.reply(f'You can play trivia again in like {get_readable_time(x)}.')

    question = random.choice(data["questions"])
    id = data["questions"].index(question)
    options = question["options"]
    answer = question["answer"]
    buttons = [[InlineKeyboardButton(option, callback_data=f"tri:{option.lower()}:{id}:{user.id}")] for option in options]
    yos = await message.reply(f"**{question['question']}**\n\n__You Have 20 Seconds to answer.__", reply_markup=InlineKeyboardMarkup(buttons))
    TRIVIA_DICT[user.id] = datetime.datetime.now().timestamp()

    await asyncio.sleep(20)
    try:
        await yos.edit("⌛ Time Up")
    except:
        pass


@app.on_callback_query(filters.regex("^tri:"))
@error
async def trivia_callback(client, query):
    chosen_option, id, user_id = query.data.split(":")[1:]
    user_id = int(user_id)
    answer = data["questions"][int(id)]["answer"].lower()
    await query.message.delete()
    if query.from_user.id != user_id:
        return await query.answer("This is not for you", show_alert=True)

    if chosen_option != answer:
        return await client.send_message(query.message.chat.id,f"🔴 Wrong answer! The correct answer was **{answer.title()}**")

    coins = await user_wallet(user_id)
    new_wallet = coins + 10000
    await gamesdb.update_one({'user_id': user_id}, {'$set': {'coins': new_wallet}})

    message_text = f"🟢 Wow! The answer **{chosen_option.title()}** was right. You got 10,000 XP.\nTotal balance: `{new_wallet:,}` XP"
    return await client.send_message(query.message.chat.id,message_text)


    
@app.on_message(filters.command("bet", prefixes=config.COMMAND_PREFIXES))
@error
@save
async def _bet(client,message):
  chat_id = message.chat.id
  user = message.from_user
  if not await is_player(user.id):
     await create_account(user.id,message.from_user.username)
  if user.id not in BET_DICT.keys():
      BET_DICT[user.id] = None     
  if BET_DICT[user.id]:
      x= await can_play(BET_DICT[user.id],12)
      if int(x) != 0:
        return await message.reply(f'ʏᴏᴜ ᴄᴀɴ ʙᴇᴛ ᴀɢᴀɪɴ ɪɴ ʟɪᴋᴇ {get_readable_time(x)}.')     
  possible = ['h','heads','tails','t','head','tail']
  if len(message.command) < 3:
      return await message.reply_text("✑ ᴜsᴀɢᴇ : /bet [ᴀᴍᴏᴜɴᴛ] [ʜᴇᴀᴅs/ᴛᴀɪʟs]")
  to_bet = message.command[1]
  cmd = message.command[2].lower()
  coins = await user_wallet(user.id)
  if to_bet == '*':
      to_bet = coins
  elif not to_bet.isdigit():
       return await message.reply_text("ʏᴏᴜ ᴛʜɪɴᴋs ᴛʜᴀᴛ ɪᴛ's ᴀ ᴠᴀʟɪᴅ ᴀᴍᴏᴜɴᴛ?")
  to_bet = int(to_bet)
  if to_bet == 0:
      return await message.reply_text("ʏᴏᴜ ᴡᴀɴɴᴀ ʙᴇᴛ 𝟶 ? ʟᴏʟ!") 
  elif to_bet > coins:
      return await message.reply_text("ʏᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ ᴛʜᴀᴛ ᴍᴜᴄʜ XP ʜᴇʀᴇ ɪs ʏᴏᴜʀ ʙᴀʟᴀɴᴄᴇ ✑ `{0:,}` XP".format(coins)) 
  rnd = random.choice(['heads','tails'])
  if cmd not in possible:
      return await message.reply_text("ʏᴏᴜ sʜᴏᴜʟᴅ ᴛʀʏ ʜᴇᴀᴅs ᴏʀ ᴇɪᴛʜᴇʀ ᴛᴀɪʟs.")
  if cmd in ['h','head','heads']:
      if rnd == 'heads':
          user_won = True         
      else:
          user_won = False
  if cmd in ['t','tail','tails']:
      if rnd == 'tails':
          user_won = True
      else:
          user_won = False
  BET_DICT[user.id] = datetime.datetime.now().timestamp()
  if not user_won:
      new_wallet = coins - to_bet
      await gamesdb.update_one({'user_id' : user.id}, {'$set' : {'coins' : new_wallet}})
      return await message.reply_text("🛑 ᴛʜᴇ ᴄᴏɪɴ ʟᴀɴᴅᴇᴅ ᴏɴ {0}!\n• ʏᴏᴜ ʟᴏsᴛ `{1:,}` XP\n• ᴛᴏᴛᴀʟ ʙᴀʟᴀɴᴄᴇ : `{2:,}` XP".format(rnd,to_bet,new_wallet))
  else:
      new_wallet = coins + to_bet
      await gamesdb.update_one({'user_id' : user.id}, {'$set' : {'coins' : new_wallet}})
      return await message.reply_text("✅ ᴛʜᴇ ᴄᴏɪɴ ʟᴀɴᴅᴇᴅ ᴏɴ {0}!\nʏᴏᴜ ᴡᴏɴ `{1:,}` XP\nᴛᴏᴛᴀʟ ʙᴀʟᴀɴᴄᴇ : `{2:,}` XP".format(rnd,to_bet,new_wallet)) 
     

@app.on_message(filters.command("dart", prefixes=config.COMMAND_PREFIXES))
@error
@save
async def _dart(client,message):
  chat_id = message.chat.id
  user = message.from_user
  if not await is_player(user.id):
     await create_account(user.id,message.from_user.username)
  if user.id not in DART_DICT.keys():
      DART_DICT[user.id] = None     
  if DART_DICT[user.id]:
      x= await can_play(DART_DICT[user.id],20)
      if int(x) != 0:
        return await message.reply(f'ʏᴏᴜ ᴄᴀɴ ᴘʟᴀʏ ᴅᴀʀᴛ ᴀɢᴀɪɴ ɪɴ ʟɪᴋᴇ `{get_readable_time(x)}`.')
  if len(message.command) < 2:
      return await message.reply_text("ᴏᴋ! ʙᴜᴛ ʜᴏᴡ ᴍᴜᴄʜ ʏᴏᴜ ᴀʀᴇ ɢᴏɴɴᴀ ʙᴇᴛ.")
  to_bet = message.command[1]
  coins = await user_wallet(user.id)
  if to_bet == '*':
      to_bet = coins
  elif not to_bet.isdigit():
       return await message.reply_text("ʏᴏᴜ ᴛʜɪɴᴋs ᴛʜᴀᴛ ɪᴛ's ᴀ ᴠᴀʟɪᴅ ᴀᴍᴏᴜɴᴛ?")
  to_bet = int(to_bet)
  if to_bet == 0:
      return await message.reply_text("ʏᴏᴜ ᴡᴀɴɴᴀ ʙᴇᴛ 𝟶 ? ʟᴏʟ!") 
  elif to_bet > coins:
      return await message.reply_text("ʏᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ ᴛʜᴀᴛ ᴍᴜᴄʜ XP ʜᴇʀᴇ ɪs ʏᴏᴜʀ ʙᴀʟᴀɴᴄᴇ ✑ `{0:,}` XP".format(coins))
  m = await client.send_dice(chat_id,'🎯')
  msg = await message.reply('....')
  u_won = await get_user_won(m.dice.emoji,m.dice.value)
  DART_DICT[user.id] = datetime.datetime.now().timestamp()
  if not u_won:
      new_wallet = coins - to_bet
      await gamesdb.update_one({'user_id' : user.id}, {'$set' : {'coins' : new_wallet}})
      await asyncio.sleep(5)
      return await msg.edit("🛑 sᴀᴅ ᴛᴏ sᴀʏ! ʙᴜᴛ ʏᴏᴜ ʟᴏsᴛ `{0:,}` XP\n• ᴄᴜʀᴇᴇɴᴛ ʙᴀʟᴀɴᴄᴇ ✑ `{1:,}` XP".format(to_bet,new_wallet))
  else:
      new_wallet = coins + to_bet
      await gamesdb.update_one({'user_id' : user.id}, {'$set' : {'coins' : new_wallet}})
      await asyncio.sleep(5)
      return await msg.edit("✅ ᴡᴏᴡ! ʏᴏᴜ ᴡᴏɴ `{0:,}` XP\n• ᴄᴜʀᴇᴇɴᴛ ʙᴀʟᴀɴᴄᴇ ✑ `{1:,}`XP.".format(to_bet,new_wallet))
     
      
@app.on_message(filters.command("bowl", prefixes=config.COMMAND_PREFIXES))
@error
@save
async def _bowl(client,message):
  chat_id = message.chat.id
  user = message.from_user
  if not await is_player(user.id):
     await create_account(user.id,message.from_user.username) 
  if user.id not in BOWL_DICT.keys():
      BOWL_DICT[user.id] = None     
  if BOWL_DICT[user.id]:
      x= await can_play(BOWL_DICT[user.id],20)
      if int(x) != 0:
        return await message.reply(f'ʏᴏᴜ ᴄᴀɴ ᴘʟᴀʏ ʙᴏᴡʟ ᴀɢᴀɪɴ ɪɴ ʟɪᴋᴇ `{get_readable_time(x)}`.')
  if len(message.command) < 2:
      return await message.reply_text("ᴏᴋ! ʙᴜᴛ ʜᴏᴡ ᴍᴜᴄʜ ʏᴏᴜ ᴀʀᴇ ɢᴏɴɴᴀ ʙᴇᴛ.")
  to_bet = message.command[1]
  coins = await user_wallet(user.id)
  if to_bet == '*':
      to_bet = coins
  elif not to_bet.isdigit():
       return await message.reply_text("ʏᴏᴜ ᴛʜɪɴᴋs ᴛʜᴀᴛ ɪᴛ's ᴀ ᴠᴀʟɪᴅ ᴀᴍᴏᴜɴᴛ?")
  to_bet = int(to_bet)
  if to_bet == 0:
      return await message.reply_text("ʏᴏᴜ ᴡᴀɴɴᴀ ʙᴇᴛ 𝟶 ? ʟᴏʟ!") 
  elif to_bet > coins:
      return await message.reply_text("ʏᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ ᴛʜᴀᴛ ᴍᴜᴄʜ XP ʜᴇʀᴇ ɪs ʏᴏᴜʀ ʙᴀʟᴀɴᴄᴇ ✑ `{0:,}` XP".format(coins))
  m = await client.send_dice(chat_id,'🎳')
  msg = await message.reply('....')
  u_won = await get_user_won(m.dice.emoji,m.dice.value)
  BOWL_DICT[user.id] = datetime.datetime.now().timestamp()
  if not u_won:
      new_wallet = coins - to_bet
      await gamesdb.update_one({'user_id' : user.id}, {'$set' : {'coins' : new_wallet}})
      await asyncio.sleep(5)
      return await msg.edit("🛑 sᴀᴅ ᴛᴏ sᴀʏ! ʙᴜᴛ ʏᴏᴜ ʟᴏsᴛ `{0:,}` XP\n• ᴄᴜʀᴇᴇɴᴛ ʙᴀʟᴀɴᴄᴇ ✑ `{1:,}` XP".format(to_bet,new_wallet))
  else:
      new_wallet = coins + to_bet
      await gamesdb.update_one({'user_id' : user.id}, {'$set' : {'coins' : new_wallet}})
      await asyncio.sleep(5)
      return await msg.edit("✅ ᴡᴏᴡ! ʏᴏᴜ ᴡᴏɴ `{0:,}` XP\n• ᴄᴜʀᴇᴇɴᴛ ʙᴀʟᴀɴᴄᴇ ✑ `{1:,}` XP.".format(to_bet,new_wallet))
  

@app.on_message(filters.command("basket", prefixes=config.COMMAND_PREFIXES))
@error
@save
async def _basket(client,message):
  chat_id = message.chat.id
  user = message.from_user
  if not await is_player(user.id):
     await create_account(user.id,message.from_user.username) 
  if user.id not in BASKET_DICT.keys():
      BASKET_DICT[user.id] = None     
  if BASKET_DICT[user.id]:
      x= await can_play(BASKET_DICT[user.id],20)
      if int(x) != 0:
        return await message.reply(f'ʏᴏᴜ ᴄᴀɴ ᴘʟᴀʏ ʙᴀsᴋᴇᴛ ᴀɢᴀɪɴ ɪɴ ʟɪᴋᴇ `{get_readable_time(x)}`.')
  if len(message.command) < 2:
      return await message.reply_text("ᴏᴋ! ʙᴜᴛ ʜᴏᴡ ᴍᴜᴄʜ ʏᴏᴜ ᴀʀᴇ ɢᴏɴɴᴀ ʙᴇᴛ.")
  to_bet = message.command[1]
  coins = await user_wallet(user.id)
  if to_bet == '*':
      to_bet = coins
  elif not to_bet.isdigit():
       return await message.reply_text("ʏᴏᴜ ᴛʜɪɴᴋs ᴛʜᴀᴛ ɪᴛ's ᴀ ᴠᴀʟɪᴅ ᴀᴍᴏᴜɴᴛ?")
  to_bet = int(to_bet)
  if to_bet == 0:
      return await message.reply_text("ʏᴏᴜ ᴡᴀɴɴᴀ ʙᴇᴛ 𝟶 ? ʟᴏʟ!") 
  elif to_bet > coins:
      return await message.reply_text("ʏᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ ᴛʜᴀᴛ ᴍᴜᴄʜ XP ʜᴇʀᴇ ɪs ʏᴏᴜʀ ʙᴀʟᴀɴᴄᴇ ✑ `{0:,}` XP".format(coins))
  m = await client.send_dice(chat_id,'🏀')
  msg = await message.reply('....')
  u_won = await get_user_won(m.dice.emoji,m.dice.value)
  BASKET_DICT[user.id] = datetime.datetime.now().timestamp()
  if not u_won:
      new_wallet = coins - to_bet
      await gamesdb.update_one({'user_id' : user.id}, {'$set' : {'coins' : new_wallet}})
      await asyncio.sleep(5)
      return await msg.edit("🛑 sᴀᴅ ᴛᴏ sᴀʏ! ʙᴜᴛ ʏᴏᴜ ʟᴏsᴛ `{0:,}` XP\n• ᴄᴜʀᴇᴇɴᴛ ʙᴀʟᴀɴᴄᴇ ✑ `{1:,}` XP".format(to_bet,new_wallet))
  else:
      new_wallet = coins + to_bet
      await gamesdb.update_one({'user_id' : user.id}, {'$set' : {'coins' : new_wallet}})
      await asyncio.sleep(5)
      return await msg.edit("✅ ᴡᴏᴡ! ʏᴏᴜ ᴡᴏɴ `{0:,}` XP\n• ᴄᴜʀᴇᴇɴᴛ ʙᴀʟᴀɴᴄᴇ ✑ `{1:,}` XP.".format(to_bet,new_wallet))
  
@app.on_message(filters.command("pay", prefixes=config.COMMAND_PREFIXES) & filters.group)
@error
@save
async def _pay(client,message):
    if not message.reply_to_message:
        return await message.reply_text("ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴜsᴇʀ")
    to_user =  message.reply_to_message.from_user
    from_user = message.from_user
    if to_user.id == from_user.id:
        if message.from_user.id not in SUPREME_USERS:
            return
    if not await is_player(to_user.id):
        await create_account(to_user.id,to_user.username)
    if not await is_player(from_user.id):
        await create_account(from_user.id,from_user.username)
    if len(message.command) < 2:
        return await message.reply_text("ᴜsᴀɢᴇ : /pay `100`")
    amount = message.command[1]
    to_pay =  message.command[1].lower()
    tcoins = await user_wallet(to_user.id)
    fcoins = await user_wallet(from_user.id)
    if amount == '*':
        if message.from_user.id not in SUPREME_USERS:
            amount = fcoins
    elif not amount.isdigit():
       return await message.reply_text("ʏᴏᴜ ᴛʜɪɴᴋs ᴛʜᴀᴛ ɪᴛ's ᴀ ᴠᴀʟɪᴅ ᴀᴍᴏᴜɴᴛ?")
    amount = int(amount)
    if amount == 0:
        return await message.reply_text("ʏᴏᴜ ᴡᴀɴɴᴀ 𝟶 ʟᴏʟ!") 
    elif amount > fcoins:
        if message.from_user.id not in SUPREME_USERS:
            return await message.reply_text("ʏᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ ᴛʜᴀᴛ ᴍᴜᴄʜ XP ʜᴇʀᴇ ɪs ʏᴏᴜʀ ʙᴀʟᴀɴᴄᴇ ✑ `{0:,}` XP".format(fcoins))
    if message.from_user.id not in SUPREME_USERS:
        await gamesdb.update_one({'user_id' : to_user.id},{'$set' : {'coins' : tcoins + amount }})
        await gamesdb.update_one({'user_id' : from_user.id},{'$set' : {'coins' : fcoins - amount }})
    else:
        await gamesdb.update_one({'user_id' : to_user.id},{'$set' : {'coins' : tcoins + amount }})
    await message.reply_text("sᴜᴄᴄᴇss! {0} ᴘᴀɪᴅ {1:,} XP ᴛᴏ {2}.".format(from_user.mention,amount,to_user.mention))


@app.on_message(filters.command(["gametop", "XPtop"], prefixes=config.COMMAND_PREFIXES))
@error
@save
async def _top(client,message): 
    x = gamesdb.find().sort("coins", pymongo.DESCENDING)
    msg = "**📈 GLOBAL XP LEADERBOARD | 🌍**\n\n"
    counter = 1
    for i in await x.to_list(length=None):
        if counter == 11:
            break
            
        # KeyError fix
        coins = i.get("coins", 0)
        if coins == 0:
            continue
            
        user_name = i.get("username", "")
        link = f"[{user_name}](https://t.me/{user_name})" if user_name else str(i["user_id"])
        
        if counter == 1:
            msg += f"{counter:02d}.**👑 {link}** ⪧ {coins:,}\n"
        else:
            msg += f"{counter:02d}.**👤 {link}** ⪧ {coins:,}\n"
        counter += 1
    await message.reply(msg,disable_web_page_preview=True)
    
@app.on_message(filters.command(["bal","balance","XP"], prefixes=config.COMMAND_PREFIXES))
@error
@save
async def _bal(client,message):
    user = message.from_user
    if not await is_player(user.id):
        await create_account(user.id,message.from_user.username)
    coins = await user_wallet(user.id)
    await message.reply("⁕ {0}'s ᴡᴀʟʟᴇᴛ.\n≪━─━─━─━─◈─━─━─━─━≫\n**XP ⪧** `{1:,}` \n**≪━─━─━─━─◈─━─━─━─━≫".format(user.mention,coins))

    
    
@app.on_message(filters.command("set_XP", prefixes=config.COMMAND_PREFIXES))
@error
@save
async def _set_xp(client,message):
    user = message.from_user
    if user.id not in SUPREME_USERS:
        return 
    if not message.reply_to_message:
        return await message.reply_text("Reply to a User")
    if not message.reply_to_message.from_user:
        return await message.reply_text("Reply to a User")
    from_user = message.reply_to_message.from_user
    if not await is_player(from_user.id):
        await create_account(from_user.id,from_user.username) 
    if len(message.command) < 2:
        return await message.reply("Give Me a Value to set users XP")
    XP = message.command[1]
    if not XP.isdigit():
        return await message.reply("The Provided Value is not a Integer.")
    XP = abs(int(XP))
    await gamesdb.update_one({'user_id' : from_user.id},{'$set' : {'coins' : XP }})
    return await message.reply_text(f"Success! Set the XP of user {from_user.mention} to {XP}")


__module__ = "𝖦𝖺𝗆𝖾𝗌"

__help__ = """**𝖬𝗂𝗇𝗂 𝖦𝖺𝗆𝖾𝗌 & 𝖤𝖼𝗈𝗇𝗈𝗆𝗒:**

✧ `/𝗀𝖺𝗆𝖾` : Opens the configuration panel for the Fast Typing game. (Admins only)
✧ `/𝗅𝖾𝖺𝖽𝖾𝗋𝖻𝗈𝖺𝗋𝖽` : Shows Fast Typing points for this group.
✧ `/𝗀𝗅𝗈𝖻𝖺𝗅𝗅𝖾𝖺𝖽𝖾𝗋𝖻𝗈𝖺𝗋𝖽` : Shows Global Users Fast Typing points.
✧ `/𝗀𝗋𝗈𝗎𝗉𝗅𝖾𝖺𝖽𝖾𝗋𝖻𝗈𝖺𝗋𝖽` : Shows Top Groups by Fast Typing points.
✧ `/𝖽𝖺𝗂𝗅𝗒` : Claim your daily 10k XP bonus.
✧ `/𝗐𝖾𝖾𝗄𝗅𝗒` : Claim your weekly 50k XP bonus.
✧ `/𝖻𝖺𝗅` 𝗈𝗋 `/𝖻𝖺𝗅𝖺𝗇𝖼𝖾` : Check your XP balance.
✧ `/𝗉𝖺𝗒 <𝖺𝗆𝗈𝗎𝗇𝗍>` : Pay XP to another user (Reply).
✧ `/𝗀𝖺𝗆𝖾𝗍𝗈𝗉` : View Global XP Economy Leaderboard.
✧ `/𝖻𝖾𝗍 <𝖺𝗆𝗈𝗎𝗇𝗍> <𝗁𝖾𝖺𝖽𝗌/𝗍𝖺𝗂𝗅𝗌>` : Bet your XP on a coin flip.
✧ `/𝖽𝖺𝗋𝗍 <𝖺𝗆𝗈𝗎𝗇𝗍>` : Play dart to win/lose XP.
✧ `/𝖻𝗈𝗐𝗅 <𝖺𝗆𝗈𝗎𝗇𝗍>` : Play bowling to win/lose XP.
✧ `/𝖻𝖺𝗌𝗄𝖾𝗍 <𝖺𝗆𝗈𝗎𝗇𝗍>` : Play basketball to win/lose XP.
✧ `/𝗍𝗋𝗂𝗏𝗂𝖺` : Play a simple trivia question to earn XP.

𝖭𝗈𝗍𝖾: 𝖶𝗂𝗇𝗇𝗂𝗇𝗀 𝖺 𝖥𝖺𝗌𝗍 𝖳𝗒𝗉𝗂𝗇𝗀 𝗋𝗈𝗎𝗇𝖽 (𝗌𝖾𝖾 `/𝗀𝖺𝗆𝖾`) 𝖺𝗅𝗌𝗈 𝖺𝖽𝖽𝗌 𝖷𝖯 𝗍𝗈 𝗍𝗁𝗂𝗌 𝗌𝖺𝗆𝖾 𝗐𝖺𝗅𝗅𝖾𝗍 - 𝗂𝗍'𝗌 𝖺𝗅𝗅 𝗈𝗇𝖾 𝗎𝗇𝗂𝖿𝗂𝖾𝖽 𝖾𝖼𝗈𝗇𝗈𝗆𝗒.
"""
