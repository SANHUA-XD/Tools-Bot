import os
import shutil
import zipfile
import tempfile
import asyncio
import aiohttp
import urllib.parse
from datetime import datetime
from pyrogram import filters, enums
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from github import Github, GithubException

from Nobara import app
from config import config
from Nobara.decorator.save import save 
from Nobara.decorator.errors import error

# IN-MEMORY STORAGE FOR TOKENS (NOT SAVED IN DATABASE)
USER_TOKENS = {}

# ==========================================
# 1. GITHUB TOKEN & UPLOAD MODULE
# ==========================================

@app.on_message(filters.command("gittoken", prefixes=config.COMMAND_PREFIXES))
@error
@save
async def set_gittoken(client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("<b>⚠️ 𝖯𝗅𝖾𝖺𝗌𝖾 𝗉𝗋𝗈𝗏𝗂𝖽𝖾 𝖺 𝗏𝖺𝗅𝗂𝖽 𝖦𝗂𝗍𝖧𝗎𝖻 𝗍𝗈𝗄𝖾𝗇.</b>\n<b>📌 𝖤𝗑𝖺𝗆𝗉𝗅𝖾:</b> `/gittoken ghp_xxxxxx`")
        return
    
    token = message.text.split(None, 1)[1].strip()
    USER_TOKENS[message.from_user.id] = token
    
    reply = await message.reply_text("<b>✅ 𝖸𝗈𝗎𝗋 𝖦𝗂𝗍𝖧𝗎𝖻 𝗍𝗈𝗄𝖾𝗇 𝗁𝖺𝗌 𝖻𝖾𝖾𝗇 𝗌𝖺𝗏𝖾𝖽 𝗍𝖾𝗆𝗉𝗈𝗋𝖺𝗋𝗂𝗅𝗒 𝗂𝗇 𝗆𝖾𝗆𝗈𝗋𝗒!</b>")
    
    # Auto-delete token message in groups for security
    if message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        try:
            await message.delete()
            await reply.edit_text("<b>✅ 𝖸𝗈𝗎𝗋 𝖦𝗂𝗍𝖧𝗎𝖻 𝗍𝗈𝗄𝖾𝗇 𝗁𝖺𝗌 𝖻𝖾𝖾𝗇 𝗌𝖺𝗏𝖾𝖽!</b>\n<i>(𝖸𝗈𝗎𝗋 𝗆𝖾𝗌𝗌𝖺𝗀𝖾 𝗐𝖺𝗌 𝖽𝖾𝗅𝖾𝗍𝖾𝖽 𝖿𝗈𝗋 𝗌𝖾𝖼𝗎𝗋𝗂𝗍𝗒 𝗋𝖾𝖺𝗌𝗈𝗇𝗌)</i>")
        except Exception:
            pass


@app.on_message(filters.command("upload", prefixes=config.COMMAND_PREFIXES))
@error
@save
async def upload_to_repo(client, message: Message):
    user_id = message.from_user.id
    
    if user_id not in USER_TOKENS:
        await message.reply_text("<b>⚠️ 𝖯𝗅𝖾𝖺𝗌𝖾 𝗌𝖾𝗍 𝗒𝗈𝗎𝗋 𝖦𝗂𝗍𝖧𝗎𝖻 𝗍𝗈𝗄𝖾𝗇 𝖿𝗂𝗋𝗌𝗍 𝗎𝗌𝗂𝗇𝗀</b> `/gittoken <token>`")
        return

    if not message.reply_to_message or not message.reply_to_message.document:
        await message.reply_text("<b>⚠️ 𝖯𝗅𝖾𝖺𝗌𝖾 𝗋𝖾𝗉𝗅𝗒 𝗍𝗈 𝖺 𝗓𝗂𝗉 𝖿𝗂𝗅𝖾 𝗐𝗂𝗍𝗁 𝗍𝗁𝗂𝗌 𝖼𝗈𝗆𝗆𝖺𝗇𝖽.</b>")
        return

    if not message.reply_to_message.document.file_name.endswith(".zip"):
        await message.reply_text("<b>⚠️ 𝖳𝗁𝖾 𝗋𝖾𝗉𝗅𝗂𝖾𝖽 𝖿𝗂𝗅𝖾 𝗆𝗎𝗌𝗍 𝖻𝖾 𝖺 𝗏𝖺𝗅𝗂𝖽 𝗓𝗂𝗉 𝖿𝗂𝗅𝖾.</b>")
        return

    if len(message.command) < 2:
        await message.reply_text("<b>⚠️ 𝖴𝗌𝖺𝗀𝖾:</b> `/upload owner/repo/branch|title|comment`")
        return

    args_str = message.text.split(None, 1)[1]
    parts = [p.strip() for p in args_str.split("|")]
    
    repo_info = parts[0]
    title = parts[1] if len(parts) > 1 else "Uploaded via Telegram Bot"
    comment = parts[2] if len(parts) > 2 else "Automatic commit"

    repo_parts = repo_info.split("/")
    if len(repo_parts) < 2:
        await message.reply_text("<b>❌ 𝖨𝗇𝗏𝖺𝗅𝗂𝖽 𝗋𝖾𝗉𝗈 𝗌𝗒𝗇𝗍𝖺𝗑. 𝖴𝗌𝖾:</b> <code>owner/repo</code> <b>𝗈𝗋</b> <code>owner/repo/branch</code>")
        return

    owner = repo_parts[0]
    repo_name = repo_parts[1]
    branch = repo_parts[2] if len(repo_parts) > 2 else None

    status = await message.reply_text("<b>📥 𝖣𝗈𝗐𝗇𝗅𝗈𝖺𝖽𝗂𝗇𝗀 𝗒𝗈𝗎𝗋 𝗓𝗂𝗉 𝖿𝗂𝗅𝖾...</b>")

    with tempfile.TemporaryDirectory() as temp_dir:
        zip_path = os.path.join(temp_dir, "archive.zip")
        await client.download_media(message.reply_to_message, file_name=zip_path)
        
        await status.edit_text("<b>📂 𝖤𝗑𝗍𝗋𝖺𝖼𝗍𝗂𝗇𝗀 𝗓𝗂𝗉 𝖿𝗂𝗅𝖾 𝖼𝗈𝗇𝗍𝖾𝗇𝗍𝗌...</b>")
        extract_dir = os.path.join(temp_dir, "extracted_files")
        os.makedirs(extract_dir, exist_ok=True)
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            macosx_path = os.path.join(extract_dir, "__MACOSX")
            if os.path.exists(macosx_path):
                shutil.rmtree(macosx_path)
                
            base_upload_dir = extract_dir
            extracted_items = os.listdir(extract_dir)
            if len(extracted_items) == 1:
                single_item_path = os.path.join(extract_dir, extracted_items[0])
                if os.path.isdir(single_item_path):
                    base_upload_dir = single_item_path
                    
        except Exception as e:
            await status.edit_text(f"<b>❌ 𝖤𝗑𝗍𝗋𝖺𝖼𝗍𝗂𝗈𝗇 𝖿𝖺𝗂𝗅𝖾𝖽:</b> <code>{str(e)}</code>")
            return

        await status.edit_text("<b>⚙️ 𝖯𝗋𝗈𝖼𝖾𝗌𝗌𝗂𝗇𝗀 𝖦𝗂𝗍𝖧𝗎𝖻 𝗎𝗉𝗅𝗈𝖺𝖽...</b>")
        token = USER_TOKENS[user_id]

        def github_worker():
            g = Github(token)
            try:
                repo = g.get_repo(f"{owner}/{repo_name}")
                target_branch = branch if branch else repo.default_branch
                
                for root, _, files in os.walk(base_upload_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        relative_path = os.path.relpath(file_path, base_upload_dir)
                        
                        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                        
                        try:
                            contents = repo.get_contents(relative_path, ref=target_branch)
                            repo.update_file(
                                path=relative_path,
                                message=f"{title}\n\n{comment}",
                                content=content,
                                sha=contents.sha,
                                branch=target_branch
                            )
                        except GithubException as ge:
                            if ge.status == 404:
                                repo.create_file(
                                    path=relative_path,
                                    message=f"{title}\n\n{comment}",
                                    content=content,
                                    branch=target_branch
                                )
                            else:
                                raise ge
                return True, target_branch
            except Exception as ex:
                return False, str(ex)

        await status.edit_text("<b>⬆️ 𝖴𝗉𝗅𝗈𝖺𝖽𝗂𝗇𝗀 𝖿𝗂𝗅𝖾𝗌 𝗍𝗈 𝖦𝗂𝗍𝖧𝗎𝖻 (𝗉𝗅𝖾𝖺𝗌𝖾 𝗐𝖺𝗂𝗍)...</b>")
        success, result = await asyncio.to_thread(github_worker)
        
        if success:
            await status.edit_text(f"<b>✅ 𝖲𝗎𝖼𝖼𝖾𝗌𝗌𝖿𝗎𝗅𝗅𝗒 𝗎𝗉𝗅𝗈𝖺𝖽𝖾𝖽 𝖺𝗅𝗅 𝖿𝗂𝗅𝖾𝗌 𝗍𝗈 𝖻𝗋𝖺𝗇𝖼𝗁:</b> <code>{result}</code>")
        else:
            await status.edit_text(f"<b>❌ 𝖦𝗂𝗍𝖧𝗎𝖻 𝖾𝗋𝗋𝗈𝗋:</b> <code>{result}</code>")


# ==========================================
# 2. GITHUB SEARCH & PROFILE MODULE
# ==========================================

@app.on_message(filters.command(['repo', 'githubrepo'], prefixes=config.COMMAND_PREFIXES))
@error
@save
async def git_repo(client, message: Message):
    if len(message.command) == 1:
        return await message.reply_text("<b>⚠️ 𝖯𝗅𝖾𝖺𝗌𝖾 𝗉𝗋𝗈𝗏𝗂𝖽𝖾 𝖺 𝗋𝖾𝗉𝗈𝗌𝗂𝗍𝗈𝗋𝗒 𝗇𝖺𝗆𝖾.</b>\n\n<b>📌 𝖤𝗑𝖺𝗆𝗉𝗅𝖾:</b> `/repo Telegram-bot`")
        
    pablo = await message.reply_text("<b>🔎 𝖲𝖾𝖺𝗋𝖼𝗁𝗂𝗇𝗀 𝖦𝗂𝗍𝖧𝗎𝖻 𝗋𝖾𝗉𝗈𝗌𝗂𝗍𝗈𝗋𝗂𝖾𝗌...</b>")
    
    try:
        query = message.text.split(None, 1)[1]
        safe_query = urllib.parse.quote(query)
        url = f"https://api.github.com/search/repositories?q={safe_query}&per_page=7"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                if r.status != 200:
                    return await pablo.edit("<b>❌ 𝖤𝗋𝗋𝗈𝗋 𝖿𝖾𝗍𝖼𝗁𝗂𝗇𝗀 𝖽𝖺𝗍𝖺 𝖿𝗋𝗈𝗆 𝖦𝗂𝗍𝖧𝗎𝖻!</b>")
                lool = await r.json()
        
        if lool.get("total_count", 0) == 0:
            return await pablo.edit("<b>❌ 𝖭𝗈 𝗋𝖾𝗉𝗈𝗌𝗂𝗍𝗈𝗋𝗒 𝖿𝗈𝗎𝗇𝖽 𝖿𝗈𝗋 𝗒𝗈𝗎𝗋 𝗊𝗎𝖾𝗋𝗒!</b>")
            
        items = lool.get("items", [])
        txt = f"<b>🔍 𝖳𝗈𝗉 𝗋𝖾𝗌𝗎𝗅𝗍𝗌 𝖿𝗈𝗋:</b> <code>{query}</code>\n"
        txt += "━━━━━━━━━━━━━━━━━━━━━━\n\n"

        for i, qw in enumerate(items, 1):
            name = qw.get("full_name")
            link = qw.get("html_url")
            stars = qw.get("stargazers_count", 0)
            forks = qw.get("forks_count", 0)
            lang = qw.get("language") or "N/A"
            size_kb = qw.get("size", 0)
            size_mb = round(size_kb / 1024, 2)
            
            txt += f"<b>{i}. <a href='{link}'>{name}</a></b>\n"
            txt += f"⭐ 𝖲𝗍𝖺𝗋𝗌: <code>{stars}</code> | 🍴 𝖥𝗈𝗋𝗄𝗌: <code>{forks}</code>\n"
            txt += f"📝 𝖫𝖺𝗇𝗀: <code>{lang}</code> | 📦 𝖲𝗂𝗓𝖾: <code>{size_mb} 𝖬𝖡</code>\n\n"
        
        txt += "<b>━━━━━━━━━━━━━━━━━━━━━━</b>"

        btn = InlineKeyboardMarkup([
            [InlineKeyboardButton("🌐 𝖵𝗂𝖾𝗐 𝖠𝗅𝗅 𝖱𝖾𝗌𝗎𝗅𝗍𝗌", url=f"https://github.com/search?q={safe_query}")],
            [InlineKeyboardButton("❌ 𝖢𝗅𝗈𝗌𝖾", callback_data="repo_close_data")]
        ])
            
        await pablo.edit(txt, reply_markup=btn, disable_web_page_preview=True)
        
    except Exception as e:
        await pablo.edit(f"<b>⚠️ 𝖠𝗇 𝖾𝗋𝗋𝗈𝗋 𝗈𝖼𝖼𝗎𝗋𝗋𝖾𝖽:</b> `{e}`")


@app.on_message(filters.command(['github', 'git'], prefixes=config.COMMAND_PREFIXES))
@error
@save
async def github_user(client, message: Message):
    if len(message.command) == 1:
        return await message.reply_text("<b>⚠️ 𝖯𝗅𝖾𝖺𝗌𝖾 𝗉𝗋𝗈𝗏𝗂𝖽𝖾 𝖺 𝖦𝗂𝗍𝖧𝗎𝖻 𝗎𝗌𝖾𝗋𝗇𝖺𝗆𝖾.</b>\n\n<b>📌 𝖤𝗑𝖺𝗆𝗉𝗅𝖾:</b> `/github Sourov-Nobita`")
    
    username = message.text.split(None, 1)[1]
    pablo = await message.reply_text(f"<b>🔎 𝖥𝖾𝗍𝖼𝗁𝗂𝗇𝗀 𝗂𝗇𝖿𝗈 𝖿𝗈𝗋</b> <code>{username}</code><b>...</b>")
    
    try:
        url = f"https://api.github.com/users/{urllib.parse.quote(username)}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                if r.status == 404:
                    return await pablo.edit(f"<b>❌ 𝖦𝗂𝗍𝖧𝗎𝖻 𝗎𝗌𝖾𝗋 <code>{username}</code> 𝗇𝗈𝗍 𝖿𝗈𝗎𝗇𝖽!</b>")
                if r.status != 200:
                    return await pablo.edit("<b>❌ 𝖠𝖯𝖨 𝖾𝗋𝗋𝗈𝗋 𝗈𝖼𝖼𝗎𝗋𝗋𝖾𝖽!</b>")
                user_data = await r.json()

        name = user_data.get('name') or user_data.get('login')
        login = user_data.get('login')
        bio = user_data.get('bio') or "𝖭𝗈 𝖻𝗂𝗈 𝖺𝗏𝖺𝗂𝗅𝖺𝖻𝗅𝖾."
        public_repos = user_data.get('public_repos', 0)
        followers = user_data.get('followers', 0)
        following = user_data.get('following', 0)
        company = user_data.get('company') or "N/A"
        location = user_data.get('location') or "N/A"
        blog = user_data.get('blog')
        avatar_url = user_data.get('avatar_url')
        profile_url = user_data.get('html_url')
        
        blog_url = None
        if blog:
            if blog.startswith("http://") or blog.startswith("https://"):
                blog_url = blog
            else:
                blog_url = "https://" + blog

        created_at = user_data.get('created_at')
        if created_at:
            date_obj = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ")
            formatted_date = date_obj.strftime("%d %b %Y")
        else:
            formatted_date = "N/A"

        caption = f"""
<b>👤 𝖭𝖺𝗆𝖾:</b> {name}
<b>🔖 𝖴𝗌𝖾𝗋𝗇𝖺𝗆𝖾:</b> <a href="{profile_url}">@{login}</a>

<b>📖 𝖡𝗂𝗈:</b> <i>{bio}</i>

<b>📊 𝖲𝗍𝖺𝗍𝗂𝗌𝗍𝗂𝖼𝗌:</b>
├ <b>📁 𝖱𝖾𝗉𝗈𝗌𝗂𝗍𝗈𝗋𝗂𝖾𝗌:</b> <code>{public_repos}</code>
├ <b>👥 𝖥𝗈𝗅𝗅𝗈𝗐𝖾𝗋𝗌:</b> <code>{followers}</code>
└ <b>🫂 𝖥𝗈𝗅𝗅𝗈𝗐𝗂𝗇𝗀:</b> <code>{following}</code>

<b>🏢 𝖢𝗈𝗆𝗉𝖺𝗇𝗒:</b> <i>{company}</i>
<b>📍 𝖫𝗈𝖼𝖺𝗍𝗂𝗈𝗇:</b> <i>{location}</i>
<b>📅 𝖩𝗈𝗂𝗇𝖾𝖽:</b> <i>{formatted_date}</i>
"""
        if user_data.get('type') == "Organization":
            caption += "\n<b>🏢 𝖠𝖼𝖼𝗈𝗎𝗇𝗍 𝖳𝗒𝗉𝖾:</b> 𝖮𝗋𝗀𝖺𝗇𝗂𝗓𝖺𝗍𝗂𝗈𝗇"
        elif user_data.get('site_admin'):
            caption += "\n<b>🛡️ 𝖲𝗂𝗍𝖾 𝖠𝖽𝗆𝗂𝗇:</b> 𝖸𝖾𝗌"

        btn_list = [
            [
                InlineKeyboardButton("🔗 𝖵𝗂𝖾𝗐 𝖯𝗋𝗈𝖿𝗂𝗅𝖾", url=profile_url),
                InlineKeyboardButton("📁 𝖱𝖾𝗉𝗈𝗌𝗂𝗍𝗈𝗋𝗂𝖾𝗌", url=f"{profile_url}?tab=repositories")
            ]
        ]
        
        if blog_url:
            btn_list.append([InlineKeyboardButton("🌐 𝖶𝖾𝖻𝗌𝗂𝗍𝖾", url=blog_url)])
            
        btn_list.append([InlineKeyboardButton("❌ 𝖢𝗅𝗈𝗌𝖾", callback_data="repo_close_data")])
        btn = InlineKeyboardMarkup(btn_list)

        status_card = f"https://github-readme-stats.vercel.app/api?username={login}&show_icons=true&theme=tokyonight&count_private=true"

        try:
            await message.reply_photo(
                photo=status_card,
                caption=caption,
                reply_markup=btn
            )
            await pablo.delete()
        except:
            if avatar_url:
                await message.reply_photo(photo=avatar_url, caption=caption, reply_markup=btn)
                await pablo.delete()
            else:
                await pablo.edit(caption, reply_markup=btn, disable_web_page_preview=True)

    except Exception as e:
        await pablo.edit(f"<b>⚠️ 𝖠𝗇 𝖾𝗋𝗋𝗈𝗋 𝗈𝖼𝖼𝗎𝗋𝗋𝖾𝖽:</b> `{e}`")


# ==========================================
# 3. CALLBACK QUERY HANDLER (FOR CLOSE BUTTONS)
# ==========================================

@app.on_callback_query(filters.regex("^repo_close_data$"))
@error
async def close_callback_handler(client, query: CallbackQuery):
    try:
        await query.message.delete()
    except Exception:
        await query.answer("❌ 𝖢𝗈𝗎𝗅𝖽 𝗇𝗈𝗍 𝖽𝖾𝗅𝖾𝗍𝖾 𝗍𝗁𝖾 𝗆𝖾𝗌𝗌𝖺𝗀𝖾.", show_alert=True)


__module__ = "𝖦𝗂𝗍𝖧𝗎𝖻"

__help__ = """**𝖦𝗂𝗍𝖧𝗎𝖻 & 𝖱𝖾𝗉𝗈 𝖢𝗈𝗆𝗆𝖺𝗇𝖽𝗌:**

  ✧ `/github <username>` **:** 𝖦𝖾𝗍 𝗂𝗇𝖿𝗈𝗋𝗆𝖺𝗍𝗂𝗈𝗇 𝖺𝖻𝗈𝗎𝗍 𝖺 𝖦𝗂𝗍𝖧𝗎𝖻 𝗎𝗌𝖾𝗋.
  ✧ `/repo <query>` **:** 𝖲𝖾𝖺𝗋𝖼𝗁 𝖿𝗈𝗋 𝖦𝗂𝗍𝖧𝗎𝖻 𝗋𝖾𝗉𝗈𝗌𝗂𝗍𝗈𝗋𝗂𝖾𝗌.
  ✧ `/gittoken <token>` **:** 𝖲𝖺𝗏𝖾 𝗒𝗈𝗎𝗋 𝖦𝗂𝗍𝖧𝗎𝖻 𝖯𝖾𝗋𝗌𝗈𝗇𝖺𝗅 𝖠𝖼𝖼𝖾𝗌𝗌 𝖳𝗈𝗄𝖾𝗇 𝗂𝗇 𝗆𝖾𝗆𝗈𝗋𝗒.
  ✧ `/upload <owner/repo/branch|title|comment>` **:** 𝖱𝖾𝗉𝗅𝗒 𝗍𝗈 𝖺 .𝗓𝗂𝗉 𝖿𝗂𝗅𝖾 𝗍𝗈 𝗎𝗉𝗅𝗈𝖺𝖽 𝗂𝗍𝗌 𝖼𝗈𝗇𝗍𝖾𝗇𝗍𝗌 𝗍𝗈 𝗒𝗈𝗎𝗋 𝖦𝗂𝗍𝖧𝗎𝖻 𝗋𝖾𝗉𝗈𝗌𝗂𝗍𝗈𝗋𝗒.
"""
