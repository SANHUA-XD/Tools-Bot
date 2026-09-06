import os
import shutil
import subprocess
import sys
from pyrogram import filters
from Nobara import app
from config import config 
from Nobara.helper.on_start import save_restart_data
from Nobara.decorator.errors import error
from Nobara.decorator.save import save

@app.on_message(filters.command("update", prefixes=config.COMMAND_PREFIXES) & filters.user(config.OWNER_ID))
@app.on_message(filters.regex(r"(?i)^Yumeko Update$") & filters.user(config.OWNER_ID))
@error
@save
async def git_pull_command(client, message):
    # Heroku's Python buildpack dyno doesn't ship the "git" binary at runtime
    # (it's only present during the build step), so a plain `git pull` inside
    # the running bot always failed with FileNotFoundError there. Since this
    # bot is deployed by pushing a new zip to GitHub (which Heroku then
    # auto-deploys on its own), an in-dyno git pull isn't meaningful on that
    # setup anyway - so we detect that case and explain it instead of crashing.
    if shutil.which("git") is None:
        await message.reply(
            "❌ **`git` 𝗂𝗌 𝗇𝗈𝗍 𝖺𝗏𝖺𝗂𝗅𝖺𝖻𝗅𝖾 𝗈𝗇 𝗍𝗁𝗂𝗌 𝗁𝗈𝗌𝗍.**\n\n"
            "𝖮𝗇 𝖧𝖾𝗋𝗈𝗄𝗎, 𝗍𝗁𝖾 𝗋𝗎𝗇𝗇𝗂𝗇𝗀 𝖽𝗒𝗇𝗈 𝖽𝗈𝖾𝗌𝗇'𝗍 𝗁𝖺𝗏𝖾 𝗀𝗂𝗍, 𝗌𝗈 `/update` 𝖼𝖺𝗇'𝗍 𝗉𝗎𝗅𝗅 𝖼𝗁𝖺𝗇𝗀𝖾𝗌 𝗂𝗇-𝗉𝗅𝖺𝖼𝖾 𝗁𝖾𝗋𝖾. "
            "𝖨𝖿 𝗒𝗈𝗎 𝗉𝗎𝗌𝗁𝖾𝖽 𝗇𝖾𝗐 𝖼𝗈𝖽𝖾 𝗍𝗈 𝖦𝗂𝗍𝖧𝗎𝖻, 𝖧𝖾𝗋𝗈𝗄𝗎'𝗌 𝖺𝗎𝗍𝗈-𝖽𝖾𝗉𝗅𝗈𝗒 𝖺𝗅𝗋𝖾𝖺𝖽𝗒 𝗁𝖺𝗇𝖽𝗅𝖾𝗌 𝗍𝗁𝖾 𝗎𝗉𝖽𝖺𝗍𝖾 𝖺𝗇𝖽 𝗋𝖾𝗌𝗍𝖺𝗋𝗍𝗌 𝗍𝗁𝖾 𝖽𝗒𝗇𝗈 𝖿𝗈𝗋 𝗒𝗈𝗎. "
            "𝖴𝗌𝖾 `/restart` 𝗂𝖿 𝗒𝗈𝗎 𝗃𝗎𝗌𝗍 𝗇𝖾𝖾𝖽 𝗍𝗈 𝗆𝖺𝗇𝗎𝖺𝗅𝗅𝗒 𝗋𝖾𝗌𝗍𝖺𝗋𝗍 𝗍𝗁𝖾 𝖻𝗈𝗍."
        )
        return

    try:
        # Stash local changes to prevent merge conflicts
        subprocess.run(["git", "stash"], check=True)

        result = subprocess.run(
            ["git", "pull", config.GIT_URL_WITH_TOKEN , "Frierenz"],
            capture_output=True, text=True, check=True
        )
        if "Already up to date" in result.stdout:
            await message.reply("Rᴇᴘᴏ ɪs ᴀʟʀᴇᴀᴅʏ ᴜᴘ ᴛᴏ ᴅᴀᴛᴇ.")
        elif result.returncode == 0:
            restart_message = await message.reply("Gɪᴛ ᴘᴜʟʟ sᴜᴄᴄᴇssғᴜʟ. Bᴏᴛ ᴜᴘᴅᴀᴛᴇᴅ.\n\nRᴇsᴛᴀʀᴛɪɴɢ...")
            save_restart_data(restart_message.chat.id, restart_message.id)
            await restart_bot()
        else:
            await message.reply("Gɪᴛ ᴘᴜʟʟ ғᴀɪʟᴇᴅ. Pʟᴇᴀsᴇ ᴄʜᴇᴄᴋ ᴛʜᴇ ʟᴏɢs.")
    except subprocess.CalledProcessError as e:
        await message.reply(f"Gɪᴛ ᴘᴜʟʟ ғᴀɪʟᴇᴅ ᴡɪᴛʜ ᴇʀʀᴏʀ: {e.stderr}")

async def restart_bot():
    args = [sys.executable, "-m", "Nobara"]  # Adjust this line as needed
    os.execle(sys.executable, *args, os.environ)
    sys.exit()

@app.on_message(filters.command("restart") & filters.user(config.OWNER_ID))
@error
@save
async def restart_command(client, message):
    try:
        restart_message = await message.reply("**ᴏɴɪɪ-ᴄʜᴀɴ Nobara ɪꜱ ʙᴇɪɴɢ ʀᴇꜱᴛᴀʀᴛᴇᴅ !!**")
        save_restart_data(restart_message.chat.id, restart_message.id)
        os.execvp(sys.executable, [sys.executable, "-m", "Nobara"])
    except Exception as e:
        await message.reply(f"Rᴇsᴛᴀʀᴛ ғᴀɪʟᴇᴅ ᴡɪᴛʜ ᴇʀʀᴏʀ: {str(e)}")
        
