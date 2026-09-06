import os
import json
import shutil
from Nobara import app
from config import config

RESTART_DATA_FILE = "restart_data.json"
SUDOERS_FILE = "sudoers.json"

def save_restart_data(chat_id, message_id):
    """Save the chat and message ID to a file."""
    with open(RESTART_DATA_FILE, "w") as f:
        json.dump({"chat_id": chat_id, "message_id": message_id}, f)

def load_restart_data():
    """Load the chat and message ID from the file."""
    if os.path.exists(RESTART_DATA_FILE):
        with open(RESTART_DATA_FILE, "r") as f:
            return json.load(f)
    return None

def clear_restart_data():
    """Delete the restart data file."""
    if os.path.exists(RESTART_DATA_FILE):
        os.remove(RESTART_DATA_FILE)

def edit_restart_message():
    """Edit the restart message after a successful restart."""
    restart_data = load_restart_data()
    if restart_data:
        try:
            chat_id = restart_data["chat_id"]
            message_id = restart_data["message_id"]
            app.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text="**𝖱𝖾𝗌𝗍𝖺𝗋𝗍𝖾𝖽 𝖲𝗎𝖼𝖼𝖾𝗌𝖿𝗎𝗅𝗅𝗒!** ✅"
            )
        except Exception as e:
            print(f"𝖥𝖺𝗂𝗅𝖾𝖽 𝗍𝗈 𝖾𝖽𝗂𝗍 𝗋𝖾𝗌𝗍𝖺𝗋𝗍 𝗆𝖾𝗌𝗌𝖺𝗀𝖾 : {e}")
        finally:
            clear_restart_data()

def clear_downloads_folder():
    """Remove all files and subdirectories in the downloads folder."""
    downloads_path = "downloads"  # Change this to your actual downloads folder path if needed
    if os.path.exists(downloads_path):
        try:
            shutil.rmtree(downloads_path)
            os.makedirs(downloads_path)  # Recreate the folder
            print("Downloads folder cleared successfully.")
        except Exception as e:
            print(f"Failed to clear downloads folder: {e}")

def notify_startup():
    """Notify the log channel and sudoers that the bot has started."""
    app.send_message(
    # Notify the log channel
        chat_id=config.LOG_CHANNEL,
        text="**𝖡𝗈𝗍 𝗁𝖺𝗌 𝖻𝖾𝖾𝗇 𝗌𝗍𝖺𝗋𝗍𝖾𝖽 𝗌𝗎𝖼𝖼𝖾𝗌𝗌𝖿𝗎𝗅𝗅𝗒!** ✅"
    )