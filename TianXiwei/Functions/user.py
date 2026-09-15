import pyrogram
from pyrogram.types import Message, ChatPermissions, ChatPrivileges
from pyrogram.errors import PeerIdInvalid, RPCError
from pyrogram.enums import MessageEntityType, ChatMemberStatus

from TianXiwei import app
from threading import RLock
from time import perf_counter
from cachetools import TTLCache


ADMIN_CACHE = TTLCache(maxsize=512, ttl=60 * 10, timer=perf_counter)
THREAD_LOCK = RLock()

async def resolve_user(client: app, message: Message):
    try:
        if message.reply_to_message and message.reply_to_message.from_user:
            return message.reply_to_message.from_user

        if message.command:
            args = message.command[1:]
            if args:
                query = args[0]

                if query.isdigit():
                    try:
                        return await app.get_users(int(query))
                    except RPCError:
                        return None

                if query.startswith("@"):
                    try:
                        return await app.get_users(query)
                    except RPCError:
                        return None

        if message.entities:
            for entity in message.entities:
                if entity.type == MessageEntityType.TEXT_MENTION and entity.user:
                    return entity.user

        return None

    except PeerIdInvalid:
        return None


DEMOTE = ChatPrivileges(
                            can_delete_messages = False,
                            can_manage_video_chats = False,
                            can_restrict_members = False,
                            can_promote_members = False,
                            can_change_info = False,
                            can_edit_messages = False,
                            can_invite_users = False,
                            can_pin_messages = False,
                            can_post_stories = False,
                            can_edit_stories = False,
                            can_delete_stories = False,
                            is_anonymous = False
            )

PROMOTE = ChatPrivileges(
                            can_delete_messages = True,
                            can_manage_video_chats = True,
                            can_restrict_members = False,
                            can_promote_members = False,
                            can_change_info = False,
                            can_invite_users = True,
                            can_pin_messages = True,
                            can_post_stories = True,
                            can_edit_stories = False,
                            can_delete_stories = False,
                            is_anonymous = False
            )

FULLPROMOTE = ChatPrivileges(
                            can_delete_messages = True,
                            can_manage_video_chats = True,
                            can_restrict_members = True,
                            can_promote_members = True,
                            can_change_info = True,
                            can_invite_users = True,
                            can_pin_messages = True,
                            can_post_stories = True,
                            can_edit_stories = True,
                            can_delete_stories = True,
                            is_anonymous = False
            )

LOWPROMOTE = ChatPrivileges(
                            can_delete_messages = False,
                            can_manage_video_chats = False,
                            can_restrict_members = False,
                            can_promote_members = False,
                            can_change_info = False,
                            can_invite_users = True,
                            can_pin_messages = True,
                            can_post_stories = False,
                            can_edit_stories = False,
                            can_delete_stories = False,
                            is_anonymous = False
            )

async def resolve_user_for_afk(client: app, message: Message):
    try:
        if message.reply_to_message and message.reply_to_message.from_user:
            return message.reply_to_message.from_user

        if message.command:
            args = message.command[1:]
            if args:
                query = args[0]

                if query.isdigit():
                    try:
                        return await app.get_users(int(query))
                    except RPCError:
                        return None

                if query.startswith("@"):
                    try:
                        return await app.get_users(query)
                    except RPCError:
                        return None

        if message.entities:
            for entity in message.entities:
                if entity.type == MessageEntityType.TEXT_MENTION and entity.user:
                    return entity.user
                elif entity.type == MessageEntityType.MENTION and entity.user:
                    return entity.user

        return None

    except PeerIdInvalid:
        return None

MUTE = ChatPermissions(all_perms=False)
UNMUTE = ChatPermissions(
    can_send_messages = True ,
    can_send_media_messages = True ,
    can_add_web_page_previews = True ,
    can_send_audios = True ,
    can_send_docs = True ,
    can_send_games = True ,
    can_send_gifs = True ,
    can_send_inline = True ,
    can_send_photos = True ,
    can_send_stickers = True ,
    can_send_videos = True ,
    can_send_voices = True
)
RESTRICT = ChatPermissions(
    can_send_messages = True ,
    can_send_media_messages = False ,
    can_add_web_page_previews = False ,
    can_send_audios = False ,
    can_send_docs = False ,
    can_send_games = False ,
    can_send_gifs = False ,
    can_send_inline = True ,
    can_send_photos = True ,
    can_send_stickers = True ,
    can_send_videos = False ,
    can_send_voices = False
)

async def is_user_admin(client, chat_id: int, user_id: int) -> bool:
    with THREAD_LOCK:
        try:
            return user_id in ADMIN_CACHE[chat_id]
        except (KeyError, IndexError):
            admin_list = []
            async for admin in client.get_chat_members(chat_id, filter=pyrogram.enums.ChatMembersFilter.ADMINISTRATORS):
                admin_list.append(admin.user.id)
            ADMIN_CACHE[chat_id] = admin_list
            return user_id in admin_list


NIGHT_MODE_PERMISSIONS = ChatPermissions(
    can_send_messages = True ,
    can_send_media_messages = False,
    can_send_polls = False,
    can_add_web_page_previews = False ,
    can_change_info = False,
    can_invite_users = False,
    can_pin_messages = False,
    can_manage_topics = False,
    can_send_audios = False,
    can_send_docs = False,
    can_send_games = False,
    can_send_gifs = False,
    can_send_inline = False,
    can_send_photos = False,
    can_send_plain = False,
    can_send_roundvideos =False ,
    can_send_stickers = False,
    can_send_videos = False,
    can_send_voices = False
)

DEFAULT_PERMISSIONS = ChatPermissions(
    can_send_messages = True ,
    can_send_media_messages = True,
    can_send_polls = True,
    can_add_web_page_previews = True ,
    can_change_info = False,
    can_invite_users = True,
    can_pin_messages = False,
    can_manage_topics = False,
    can_send_audios = True,
    can_send_docs = True,
    can_send_games = True,
    can_send_gifs = True,
    can_send_inline = True,
    can_send_photos = True,
    can_send_plain = True,
    can_send_roundvideos =True ,
    can_send_stickers = True,
    can_send_videos = True,
    can_send_voices = True
)
