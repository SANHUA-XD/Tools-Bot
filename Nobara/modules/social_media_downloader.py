from pyrogram import Client, filters
from pyrogram.types import Message, InputMediaPhoto
import os
import time
import asyncio
import aiohttp
from Nobara import app
import yt_dlp
from Nobara.helper.on_start import clear_downloads_folder
from config import config 
from Nobara.decorator.save import save
from Nobara.decorator.errors import error 
from youtubesearchpython.__future__ import VideosSearch


# --- Progress Bar Helper Functions ---

def format_bytes(size):
    if not size: return "0 B"
    power = 2**10
    n = 0
    power_labels = {0: '', 1: 'KB', 2: 'MB', 3: 'GB', 4: 'TB'}
    while size > power:
        size /= power
        n += 1
    return f"{size:.2f} {power_labels[n]}"

def make_progress_bar(current, total):
    if total in (0, None):
        return "▱▱▱▱▱▱▱▱▱▱ 0%"
    percent = current / total
    filled = int(10 * percent)
    bar = "▰" * filled + "▱" * (10 - filled)
    return f"{bar} {percent*100:.1f}%"

async def pyrogram_progress(current, total, message, start_time, action):
    now = time.time()
    if not hasattr(message, "last_updated"):
        message.last_updated = 0
    
    # Update message every 2 seconds to avoid Telegram FloodWait
    if now - message.last_updated > 2 or current == total:
        bar = make_progress_bar(current, total)
        text = f"**{action}...**\n\n{bar}\n**{format_bytes(current)} / {format_bytes(total)}**"
        try:
            await message.edit_text(text)
            message.last_updated = now
        except Exception:
            pass

def get_ytdl_progress_hook(message, loop, action="Downloading"):
    last_update_time = [0]
    def hook(d):
        if d['status'] == 'downloading':
            now = time.time()
            if now - last_update_time[0] > 2:
                total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                downloaded = d.get('downloaded_bytes', 0)
                bar = make_progress_bar(downloaded, total)
                text = f"**{action}...**\n\n{bar}\n**{format_bytes(downloaded)} / {format_bytes(total)}**"
                try:
                    asyncio.run_coroutine_threadsafe(message.edit_text(text), loop)
                except Exception:
                    pass
                last_update_time[0] = now
    return hook


# --- Downloader Classes ---

class Downloader:
    def __init__(self, download_path='downloads'):
        self.download_path = download_path
        if not os.path.exists(self.download_path):
            os.makedirs(self.download_path)

    def _get_cookie_opts(self):
        # player_client fallback and cookies solve two DIFFERENT problems -
        # cookies handle "sign in to confirm you're not a bot"/age-gated
        # content, while player_client affects which YouTube signature/"n"
        # challenge gets used. They were previously either/or (cookies
        # entirely skipped the player_client fallback when present), which
        # meant this fallback silently never even ran whenever cookies.txt
        # existed - now both apply together.
        opts = {'extractor_args': {'youtube': {'player_client': ['android', 'ios', 'tv', 'web']}}}
        cookie_path = 'TXT/cookies.txt'
        if os.path.exists(cookie_path):
            opts['cookiefile'] = cookie_path
        return opts

    @staticmethod
    def _is_image_only(entry) -> bool:
        if not entry:
            return False
        formats = entry.get('formats') or []
        if not formats:
            return (entry.get('ext') or '').lower() in ('jpg', 'jpeg', 'png', 'webp')
        return all((f.get('vcodec') or 'none') == 'none' for f in formats)

    def download(self, url, loop=None, message=None):
        # Probe first (no download) so we know whether this is a video post
        # or a photo/carousel post. Instagram, TikTok, etc. photo posts have
        # NO video stream at all - forcing 'bestvideo+bestaudio/best' on them
        # always failed with "Requested format is not available", exactly
        # like the "Only images are available for download" warning.
        probe_opts = {'quiet': True, 'noplaylist': False, **self._get_cookie_opts()}
        with yt_dlp.YoutubeDL(probe_opts) as probe:
            probe_info = probe.extract_info(url, download=False)

        entries = probe_info.get('entries') if probe_info.get('_type') == 'playlist' else [probe_info]
        entries = [e for e in entries if e]

        if entries and all(self._is_image_only(e) for e in entries):
            return self._download_photos(url, probe_info, entries)

        ydl_opts = {
            'format': 'bestvideo+bestaudio/best', # Broadest compatibility for Pinterest, FB, IG, YT
            'outtmpl': os.path.join(self.download_path, '%(title)s.%(ext)s'),
            'writethumbnail': True,
            # For .m3u8/HLS streams: use ffmpeg (already a dependency here)
            # as the downloader instead of yt-dlp's native HLS downloader,
            # which is more reliable for segmented/live-style streams.
            # N_m3u8DL-RE is a separate compiled binary that isn't
            # guaranteed to be installable on Heroku (same class of problem
            # as the earlier git/mongodump binary issues), so this reaches
            # the same goal using what's already available.
            'hls_prefer_native': False,
            'hls_use_mpegts': True,
            'postprocessors': [
                {
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4',
                },
                {
                    'key': 'EmbedThumbnail',
                    'already_have_thumbnail': True,
                },
            ],
            'noprogress': True,
            'quiet': True,
            **self._get_cookie_opts(),
        }

        if loop and message:
            ydl_opts['progress_hooks'] = [get_ytdl_progress_hook(message, loop, "⬇️ Downloading Video")]

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

            video_path = ydl.prepare_filename(info)
            base, _ = os.path.splitext(video_path)
            
            if not os.path.exists(video_path) and os.path.exists(base + '.mp4'):
                video_path = base + '.mp4'

            thumb_path = None
            if os.path.exists(base + '.jpg'):
                thumb_path = base + '.jpg'
            elif os.path.exists(base + '.webp'):
                thumb_path = base + '.webp'

            video_info = {
                'is_photo': False,
                'video_path': video_path,
                'thumb_path': thumb_path,
                'duration': info.get('duration'),
                'quality': info.get('format_note'),
                'height': info.get('height', 0),
                'width': info.get('width', 0),
                'title': info.get('title', 'Downloaded Video'),
                'uploader': info.get('uploader', 'Unknown'),
            }
            return video_info

    def _download_photos(self, url, probe_info, entries):
        """Downloads a photo post or carousel (Instagram/TikTok/etc.) as image files."""
        img_opts = {
            'outtmpl': os.path.join(self.download_path, '%(id)s_%(autonumber)s.%(ext)s'),
            'quiet': True,
            'noprogress': True,
            **self._get_cookie_opts(),
        }
        image_paths = []
        with yt_dlp.YoutubeDL(img_opts) as ydl:
            result = ydl.extract_info(url, download=True)
            sub_entries = result.get('entries') if result.get('_type') == 'playlist' else [result]
            for entry in sub_entries:
                if not entry:
                    continue
                path = ydl.prepare_filename(entry)
                if os.path.exists(path):
                    image_paths.append(path)

        return {
            'is_photo': True,
            'image_paths': image_paths,
            'title': probe_info.get('title', 'Downloaded Post'),
            'uploader': probe_info.get('uploader', 'Unknown'),
        }

class SongDownloader:
    def __init__(self, download_path='downloads'):
        self.download_path = download_path
        if not os.path.exists(self.download_path):
            os.makedirs(self.download_path)

    async def search_arq(self, query):
        """Fetch song info using ARQ API to bypass YouTube bot detection/cookies error."""
        url = f"https://{config.ARQ_API_URL}/deezer"
        headers = {"Authorization": config.ARQ_API_KEY}
        params = {"query": query}
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=headers, params=params, timeout=15) as response:
                    if response.status == 200:
                        res = await response.json()
                        if res.get("ok") and res.get("result"):
                            track = res["result"][0]
                            return {
                                'title': track.get('title'),
                                'url': track.get('preview') or track.get('link'),
                                'duration': track.get('duration'),
                                'artist': track.get('artist', {}).get('name', 'Unknown Artist'),
                                'channel': track.get('artist', {}).get('name', 'Unknown Artist'),
                                'thumbnail': track.get('artist', {}).get('picture_medium')
                            }
            except Exception:
                pass
        
        # Fallback to YouTube Search if ARQ fails
        videos_search = VideosSearch(query, limit=1)
        results = await videos_search.next()
        if results['result']:
            video = results['result'][0]
            return {
                'title': video['title'],
                'url': video['link'],
                'duration': video['duration'],
                'channel': video['channel']['name'],
                'artist': video['channel']['name'],
            }
        return None

    def download_song(self, url, loop=None, message=None):
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(self.download_path, '%(title)s.%(ext)s'),
            'postprocessors': [
                {
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                },
                {
                    'key': 'EmbedThumbnail',
                },
            ],
            'writethumbnail': True,
            'noprogress': True,
            'quiet': True,
        }

        # player_client fallback and cookies solve different problems (see
        # VideoDownloader._get_cookie_opts) - apply both together instead of
        # either/or, since cookies alone don't solve the signature/"n"
        # challenge that was actually causing "Requested format is not
        # available" here.
        ydl_opts['extractor_args'] = {'youtube': {'player_client': ['android', 'ios', 'tv', 'web']}}
        cookie_path = 'TXT/cookies.txt'
        if os.path.exists(cookie_path):
            ydl_opts['cookiefile'] = cookie_path

        if loop and message:
            ydl_opts['progress_hooks'] = [get_ytdl_progress_hook(message, loop, "⬇️ Downloading Audio")]

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            
            # If it's a playlist or multiple entries, grab the first one safely
            if 'entries' in info:
                info = info['entries'][0]

            audio_path = ydl.prepare_filename(info)
            base, _ = os.path.splitext(audio_path)
            
            if os.path.exists(base + '.mp3'):
                audio_path = base + '.mp3'

            thumb_path = None
            if os.path.exists(base + '.jpg'):
                thumb_path = base + '.jpg'
            elif os.path.exists(base + '.webp'):
                thumb_path = base + '.webp'

            song_info = {
                'audio_path': audio_path,
                'thumb_path': thumb_path,
                'duration': info.get('duration', 0),
                'title': info.get('title', 'Downloaded Audio'),
                'artist': info.get('artist', info.get('uploader', 'Unknown Artist')),
            }
            return song_info

downloader = Downloader()
song_downloader = SongDownloader()

# --- Bot Commands ---

@app.on_message(filters.command(["ytdl", "dl"], prefixes=config.COMMAND_PREFIXES))
@error
@save
async def download_video(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply("Please provide a link.")

    a = await message.reply_text("**⬇️ Preparing to download...**\n\n▱▱▱▱▱▱▱▱▱▱ 0%")
    url = message.command[1]
    
    try:
        loop = asyncio.get_event_loop()
        # Run downloader in background to prevent bot freezing
        video_info = await loop.run_in_executor(None, downloader.download, url, loop, a)

        await a.edit_text("**✅ Download complete! Starting Upload...**\n\n▱▱▱▱▱▱▱▱▱▱ 0%")

        # Get Dynamic Bot Username for Caption
        bot_username = getattr(config, "BOT_USERNAME", None)
        if not bot_username:
            bot_username = client.me.username if client.me else "Shizuka_Helper_Robot"

        if video_info.get('is_photo'):
            image_paths = video_info.get('image_paths') or []
            if not image_paths:
                await a.edit_text("❌ **No downloadable photos found in this post.**")
                clear_downloads_folder()
                return

            caption = (
                f"**{video_info['title']}**\n"
                f"**By {video_info['uploader']}**\n\n"
                f"**Uploaded By @{bot_username}**"
            )

            if len(image_paths) == 1:
                await message.reply_photo(photo=image_paths[0], caption=caption)
            else:
                media_group = [InputMediaPhoto(p) for p in image_paths[:10]]
                media_group[0] = InputMediaPhoto(image_paths[0], caption=caption)
                await message.reply_media_group(media=media_group)

            await a.delete()
            clear_downloads_folder()
            return

        custom_caption = (
            f"**{video_info['title']}**\n"
            f"**Video by {video_info['uploader']}**\n\n"
            f"**Uploaded By @{bot_username}**"
        )

        await message.reply_video(
            video=video_info['video_path'],
            thumb=video_info.get('thumb_path'),
            caption=custom_caption,
            width=video_info['width'],
            height=video_info['height'],
            duration=video_info['duration'] or 0,
            supports_streaming=True,
            progress=pyrogram_progress,
            progress_args=(a, time.time(), "⬆️ Uploading Video")
        )
        await a.delete()
        clear_downloads_folder()
    except Exception as e:
        err_text = str(e)
        if "tiktok.com" in url.lower() and "/photo/" in url.lower():
            await a.edit_text(
                "❌ **TikTok photo posts aren't downloadable right now.**\n\n"
                "This is a known, still-open limitation in the yt-dlp library itself - "
                "it doesn't yet recognize TikTok's `/photo/` URL format at all "
                "(regular TikTok videos work fine). Nothing to configure here; "
                "this needs an upstream yt-dlp fix."
            )
        else:
            await a.edit(f"❌ **An error occurred:** `{err_text[:200]}`")
        clear_downloads_folder()


@app.on_message(filters.command("song", prefixes=config.COMMAND_PREFIXES))
@error
@save
async def download_song(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply("Please provide a song name.")

    query = " ".join(message.command[1:])
    a = await message.reply_text("**🔍 Searching for the song...**")

    try:
        search_result = await song_downloader.search_arq(query)
        if not search_result:
            return await a.edit("Could not find the song.")

        await a.edit("**⬇️ Found it! Preparing to download...**\n\n▱▱▱▱▱▱▱▱▱▱ 0%")

        loop = asyncio.get_event_loop()
        # Run downloader in background to prevent bot freezing
        song_info = await loop.run_in_executor(None, song_downloader.download_song, search_result['url'], loop, a)
        
        await a.edit_text("**✅ Download complete! Starting Upload...**\n\n▱▱▱▱▱▱▱▱▱▱ 0%")

        # Get Dynamic Bot Username for Caption
        bot_username = getattr(config, "BOT_USERNAME", None)
        if not bot_username:
            bot_username = client.me.username if client.me else "Shizuka_Helper_Robot"

        custom_caption = (
            f"**{song_info['title']}**\n"
            f"**Artist:** {song_info['artist']}\n"
            f"**Duration:** {search_result['duration']}\n"
            f"**Channel:** {search_result['channel']}\n\n"
            f"**Uploaded By @{bot_username}**"
        )

        await message.reply_audio(
            audio=song_info['audio_path'],
            thumb=song_info.get('thumb_path'),
            caption=custom_caption,
            title=song_info['title'],
            performer=song_info['artist'],
            progress=pyrogram_progress,
            progress_args=(a, time.time(), "⬆️ Uploading Audio")
        )
        await a.delete()
        clear_downloads_folder()
    except Exception as e:
        await a.edit(f"❌ **An error occurred:** `{str(e)[:200]}`")
        clear_downloads_folder()


__module__ = "𝖣𝗈𝗐𝗇𝗅𝗈𝖺𝖽𝖾𝗋"

__help__ = """**𝖵𝗂𝖽𝖾𝗈 𝖣𝗈𝗐𝗇𝗅𝗈𝖺𝖽𝖾𝗋:**

- **𝖢𝗈𝗆𝗆𝖺𝗇𝖽𝗌:**
 ✧ `/𝗒𝗍𝖽𝗅` 𝗈𝗋 `/𝖽𝗅 <𝗅𝗂𝗇𝗄>` : 𝖣𝗈𝗐𝗇𝗅𝗈𝖺𝖽𝗌 𝗍𝗁𝖾 𝖸𝗈𝗎𝖳𝗎𝖻𝖾/𝖨𝗇𝗌𝗍𝖺𝗀𝗋𝖺𝗆/𝖯𝗂𝗇𝗍𝖾𝗋𝖾𝗌𝗍/𝖮𝗍𝗁𝖾𝗋𝗌 𝗏𝗂𝖽𝖾𝗈 𝖿𝗋𝗈𝗆 𝗍𝗁𝖾 𝗉𝗋𝗈𝗏𝗂𝖽𝖾𝖽 𝗅𝗂𝗇𝗄 𝖺𝗇𝖽 𝗎𝗉𝗅𝗈𝖺𝖽𝗌 𝗂𝗍 𝗐𝗂𝗍𝗁 𝗆𝖾𝗍𝖺𝖽𝖺𝗍𝖺.
 ✧ `/𝗌𝗈𝗇𝗀 <𝗇𝖺𝗆𝖾>` : 𝖲𝖾𝖺𝗋𝖼𝗁𝖾𝗌 𝖺𝗇𝖽 𝖽𝗈𝗐𝗇𝗅𝗈𝖺𝖽𝗌 𝗍𝗁𝖾 𝗌𝗈𝗇𝗀 𝖺𝗌 𝖺𝗇 𝖺𝗎𝖽𝗂𝗈 𝖿𝗂𝗅𝖾.
 
- **𝖴𝗌𝖺𝗀𝖾:**
   𝟣. 𝖴𝗌𝖾 𝗍𝗁𝖾 `/𝗒𝗍𝖽𝗅` 𝗈𝗋 `/𝖽𝗅` 𝖼𝗈𝗆𝗆𝖺𝗇𝖽 𝖿𝗈𝗅𝗅𝗈𝗐𝖾𝖽 𝖻𝗒 𝖺 𝗏𝖺𝗅𝗂𝖽 𝖵𝗂𝖽𝖾𝗈 𝗅𝗂𝗇𝗄.
   𝟤. 𝖴𝗌𝖾 𝗍𝗁𝖾 `/𝗌𝗈𝗇𝗀` 𝖼𝗈𝗆𝗆𝖺𝗇𝖽 𝖿𝗈𝗅𝗅𝗈𝗐𝖾𝖽 𝖻𝗒 𝗍𝗁𝖾 𝗌𝗈𝗇𝗀 𝗇𝖺𝗆𝖾.
"""
