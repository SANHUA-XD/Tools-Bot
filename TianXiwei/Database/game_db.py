import datetime
from TianXiwei.Database import gamesdb






ftdb = gamesdb.database['FastTyping']


FT_WIN_XP_REWARD = 500


async def create_account(user_id,user_name):
  dic = {
  'user_id' : user_id,
    "username" : user_name,
    'coins' : 50000,
  }
  return gamesdb.insert_one(dic)

async def is_player(user_id):
  return bool(await gamesdb.find_one({"user_id" : user_id}))
  
async def user_wallet(user_id):
    player = await gamesdb.find_one({"user_id" : user_id})
    if not player:
        return 0
    return player.get('coins', 0)


async def add_xp(user_id: int, amount: int, username: str = None):
    """Adds (or subtracts, if amount is negative) XP to a user's main wallet,
    creating their account first if they don't have one yet."""
    if not await is_player(user_id):
        await create_account(user_id, username or "")
    await gamesdb.update_one(
        {"user_id": user_id},
        {"$inc": {"coins": amount}},
        upsert=True
    )
  
async def write_last_collection_time_today(user_id, time):
    await gamesdb.update_one({'user_id' : user_id},{'$set' : {'last_date' : time}},upsert=True)

async def read_last_collection_time_today(user_id):
    user = await gamesdb.find_one({'user_id' : user_id})
    try:
        collection_time = user['last_date']  
    except : 
        collection_time = None
    if collection_time:  
        return datetime.datetime.fromtimestamp(collection_time)
    else:
        return None
        
async def can_collect_coins(user_id):
    last_collection_time = await read_last_collection_time_today(user_id)
    if last_collection_time is None:
        return (True,True)
    current_time = datetime.datetime.now()
    time_since_last_collection = current_time - last_collection_time
    return (time_since_last_collection.total_seconds() >= 24 * 60 * 60,24 * 60 * 60 - time_since_last_collection.total_seconds())
  
  
  
async def write_last_collection_time_weekly(user_id, time):
    await gamesdb.update_one({'user_id' : user_id},{'$set' : {'last_collection_weekly' : time}},upsert=True)

async def read_last_collection_time_weekly(user_id):
    user = await gamesdb.find_one({'user_id' : user_id})
    try:
        collection_time = user['last_collection_weekly']  
    except : 
        collection_time = None
    if collection_time:  
        return datetime.datetime.fromtimestamp(collection_time)
    else:
        return None
        
           
async def find_and_update(user_id,username):
    user= await gamesdb.find_one({"user_id" : user_id})
    if not user:
        return
    old_username = user["username"].lower()
    if old_username != username.lower():
        return await gamesdb.update_one({'user_id' : user_id},{'$set' : {'username' : username}})
                                 
async def can_collect(user_id):
    last_collection_time = await read_last_collection_time_weekly(user_id)
    if last_collection_time is None:
        return (True,True)
    current_time = datetime.datetime.now()
    time_since_last_collection = current_time - last_collection_time
    return (time_since_last_collection.total_seconds() >= 7 * 24 * 60 * 60,7 * 24 * 60 * 60 - time_since_last_collection.total_seconds())




async def get_ft_settings(chat_id):
    data = await ftdb.find_one({"chat_id": chat_id, "type": "ft_settings"})
    if not data:
        return {
            "chat_id": chat_id,
            "type": "ft_settings",
            "is_on": False,
            "freq": 3600, 
            "cats": ["words"], 
            "opts": ["warn", "delete_prev", "pin"],
            "last_run": 0
        }
    return data

async def update_ft_settings(chat_id, settings):
    await ftdb.update_one({"chat_id": chat_id, "type": "ft_settings"}, {"$set": settings}, upsert=True)

async def add_local_ft_point(chat_id, user_id, username: str = None):


    await ftdb.update_one(
        {"chat_id": chat_id, "user_id": user_id, "type": "ft_points"}, 
        {"$inc": {"points": 1}}, 
        upsert=True
    )


    await add_xp(user_id, FT_WIN_XP_REWARD, username)
    
async def get_all_active_ft_chats():
    chats = []
    async for chat in ftdb.find({"type": "ft_settings", "is_on": True}):
        chats.append(chat)
    return chats

async def get_local_leaderboard(chat_id, limit=10):
    cursor = ftdb.find({"chat_id": chat_id, "type": "ft_points"}).sort("points", -1).limit(limit)
    return await cursor.to_list(length=limit)

async def get_global_user_leaderboard(limit=10):
    pipeline = [
        {"$match": {"type": "ft_points"}},
        {"$group": {"_id": "$user_id", "total_points": {"$sum": "$points"}}},
        {"$sort": {"total_points": -1}},
        {"$limit": limit}
    ]
    cursor = ftdb.aggregate(pipeline)
    return await cursor.to_list(length=limit)

async def get_global_chat_leaderboard(limit=10):
    pipeline = [
        {"$match": {"type": "ft_points"}},
        {"$group": {"_id": "$chat_id", "total_points": {"$sum": "$points"}}},
        {"$sort": {"total_points": -1}},
        {"$limit": limit}
    ]
    cursor = ftdb.aggregate(pipeline)
    return await cursor.to_list(length=limit)
