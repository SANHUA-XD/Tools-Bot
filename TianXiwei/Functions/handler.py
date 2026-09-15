from config import config
from telethon import events
from TianXiwei import telebot

def register(**args):
    """Registers a new message with multiple command prefixes."""
    pattern = args.get("pattern")
    

    r_pattern = f"^[{config.CMD_STARTERS}]"


    if pattern is not None and not pattern.startswith("(?i)"):
        args["pattern"] = f"(?i){pattern}"


    if pattern:
        args["pattern"] = pattern.replace("^/", r_pattern, 1)

    def decorator(func):
        telebot.add_event_handler(func, events.NewMessage(**args))
        return func

    return decorator
