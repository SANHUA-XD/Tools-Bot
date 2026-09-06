import asyncio
from Nobara.database.log_channel_db import get_log_channel
from Nobara import app, scheduler

# ——————————————————————————————————————————————————————————————
# Per-group logs are QUEUED here instead of sent immediately. A background
# job (see start_log_flusher, below) periodically batches and flushes them
# during "free time" - this is what actually lets every module that calls
# send_log() (admin, bans, blacklist, cleaner, nightmode, approve,
# announcement, antichannel, log_channel itself, ...) log every event
# reliably without risking Telegram flood limits in a busy group, since
# many individual instant sends previously could pile up fast.
# ——————————————————————————————————————————————————————————————
_log_queue: dict[int, list[str]] = {}
_FLUSH_INTERVAL_SECONDS = 20
_MAX_MESSAGE_LEN = 4000


async def send_log(chat_id: int, log_message: str):
    log_channel_id = await get_log_channel(chat_id)
    if not log_channel_id:
        return
    _log_queue.setdefault(log_channel_id, []).append(log_message)


async def _flush_log_queues():
    if not _log_queue:
        return

    # Snapshot and clear so new logs queued during the flush aren't lost/duplicated
    pending = dict(_log_queue)
    _log_queue.clear()

    for log_channel_id, messages in pending.items():
        if not messages:
            continue
        batch = "\n\n━━━━━━━━━━━━━━━━━━━━\n\n".join(messages)

        chunks = [batch[i:i + _MAX_MESSAGE_LEN] for i in range(0, len(batch), _MAX_MESSAGE_LEN)] or [batch]

        for chunk in chunks:
            try:
                await app.send_message(log_channel_id, chunk, disable_web_page_preview=True)
            except Exception as e:
                print(f"Error sending log batch to {log_channel_id}: {e}")
            await asyncio.sleep(1)  # stay well under Telegram's per-chat rate limit


def start_log_flusher():
    """Schedules the periodic queue flush. Safe to call multiple times
    (replace_existing=True) since several modules import this file."""
    scheduler.add_job(_flush_log_queues, "interval", seconds=_FLUSH_INTERVAL_SECONDS, id="log_channel_flusher", replace_existing=True)


# Registered at import time (same pattern as Nobara/admin/backup.py's own
# module-level scheduler.add_job call) so no extra startup wiring is needed -
# this file gets imported early anyway since 9+ modules use send_log().
start_log_flusher()


def _mention(name: str, user_id) -> str:
    """Clickable full-name mention, e.g. [𝗡𝗼𝗯𝗶𝘁𝗮](tg://user?id=123)."""
    if not user_id:
        return name or "Unknown"
    safe_name = (name or "User").replace("[", "").replace("]", "")
    return f"[{safe_name}](tg://user?id={user_id})"


# Log format helper - builds a tag-based log entry like:
#
#   #BAN:
#   Chat: Group Name
#   Admin: [Full Name](tg://user?id=...) (ID: 123)
#   User: [Full Name](tg://user?id=...) (ID: 456)
#   Message link: https://t.me/c/.../1
#   Reason: ...
#
# `admin` / `user` are (name, id) tuples (or None). `extra` is an ordered
# dict of tag-specific extra fields (Time, Triggered, Invitelink from,
# Approved by, etc.). `note` is a bare trailing sentence with no field
# label (e.g. "User has been approved.", "User has requested to join the
# chat."). Only fields that are actually passed in show up - nothing is
# auto-added, so each tag can match its own exact shape.
async def format_log(tag: str = None, chat: str = None, admin=None, user=None, message_link: str = None,
                      extra: dict = None, note: str = None, reason: str = None,
                      action: str = None, pinned_link: str = None):
    # Backward-compat aliases for the old signature
    # (format_log(action=..., chat=..., admin=..., user=..., pinned_link=...))
    # so the many existing call sites across the project keep working as-is.
    if tag is None and action is not None:
        tag = action
    if message_link is None and pinned_link is not None:
        message_link = pinned_link

    lines = [f"#{tag.upper()}:", f"Chat: {chat}"]

    if admin:
        name, uid = admin if isinstance(admin, (tuple, list)) else (admin, None)
        lines.append(f"Admin: {_mention(name, uid)}" + (f" (ID: {uid})" if uid else ""))

    if user:
        name, uid = user if isinstance(user, (tuple, list)) else (user, None)
        lines.append(f"User: {_mention(name, uid)}" + (f" (ID: {uid})" if uid else ""))

    if message_link is not None:
        lines.append(f"Message link: {message_link or 'No message link for manual actions'}")

    if extra:
        for key, value in extra.items():
            if value is not None:
                lines.append(f"{key}: {value}")

    if note:
        lines.append(note)

    if reason is not None:
        lines.append(f"Reason: {reason}")

    return "\n".join(lines)
