import asyncio
import os
import re
import shutil
import tempfile
import uuid
from PIL import Image
from pyrogram import Client, emoji, enums, filters
from pyrogram.errors import BadRequest, PeerIdInvalid, StickersetInvalid
from pyrogram.file_id import FileId
from pyrogram.raw.functions.messages import GetStickerSet, SendMedia
from pyrogram.raw.functions.stickers import (
    AddStickerToSet,
    CreateStickerSet,
    DeleteStickerSet,
    RemoveStickerFromSet,
)
from pyrogram.raw.types import (
    DocumentAttributeFilename,
    InputDocument,
    InputMediaUploadedDocument,
    InputStickerSetItem,
    InputStickerSetShortName,
)
from pyrogram.types import InlineKeyboardButton
from pyrogram.types import InlineKeyboardButton as IKB
from pyrogram.types import InlineKeyboardMarkup
from pyrogram.types import InlineKeyboardMarkup as IKM
from pyrogram.types import Message
from Nobara import app
from Nobara.helper.state import state
from Nobara.database.stickerpackdb import (
    add_pack,
    delete_pack,
    get_active_pack,
    get_pack,
    get_packs,
    mark_created,
    set_active_pack,
)
from config import config 
from pyrogram.enums import ParseMode
import textwrap
from PIL import ImageDraw, ImageFont
from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.video.VideoClip import TextClip
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip

def get_emoji_regex():
    e_list = [
        getattr(emoji, e).encode("unicode-escape").decode("ASCII")
        for e in dir(emoji)
        if not e.startswith("_")
    ]
    e_sort = sorted([x for x in e_list if not x.startswith("*")], reverse=True)
    pattern_ = f"({'|'.join(e_sort)})"
    return re.compile(pattern_)


EMOJI_PATTERN = get_emoji_regex()
SUPPORTED_TYPES = ["jpeg", "png", "webp"]


class Memify:
    def __init__(self, font_path="Nobara/fonts/default.ttf"):
        self.font_path = font_path

    def draw_text(self, media_path, text, bg_color=None):
        unique_id = str(uuid.uuid4())  # Generate unique file name
        if media_path.endswith(".webm"):
            return self.process_video(media_path, text, bg_color, unique_id)
        else:
            return self.process_image(media_path, text, bg_color, unique_id)

    def process_image(self, media_path, text, bg_color, unique_id):
        img = Image.open(media_path)
        os.remove(media_path)
        processed_img = self.process_frame(img, text, bg_color)
        meme_path = f"{unique_id}.webp"
        processed_img.save(meme_path, "webp")
        return meme_path

    def process_video(self, media_path, text, bg_color, unique_id):
        clip = VideoFileClip(media_path)
        os.remove(media_path)
    
        font_size = max(24, int((70 / 640) * clip.w))
        font_path = self.font_path
    
        if ";" in text:
            upper_text, lower_text = text.split(";")
        else:
            upper_text = text
            lower_text = ""
    
        # Define create_text_clip before using it
        def create_text_clip(txt, position):
            # Calculate dynamic wrapping width based on the frame's width
            max_chars_per_line = int(clip.w / (font_size * 0.6))  # Adjust 0.6 as needed
            lines = textwrap.wrap(txt, width=max_chars_per_line)
    
            text_clips = []
            line_spacing = font_size + 10  # Spacing between lines
            total_height = len(lines) * line_spacing  # Total height of the text block
    
            for i, line in enumerate(lines):
                if position == "top":
                    y_pos = max(0, (clip.h - total_height) // 2 - (len(lines) - i - 1) * line_spacing - 110)
                elif position == "bottom":
                    y_pos = min(clip.h - line_spacing, clip.h - total_height + (i * line_spacing) - 20)
                else:
                    raise ValueError("Invalid position. Use 'top' or 'bottom'.")
    
                text_clip = (
                    TextClip(
                        text=line,
                        font_size=font_size,
                        font=font_path,
                        color="white",
                        bg_color=bg_color,
                        stroke_color="black",
                        stroke_width=2,
                    )
                    .with_position(("center", y_pos))
                    .with_duration(clip.duration)
                )
                text_clips.append(text_clip)
    
            return text_clips
    
        # Use create_text_clip after defining it
        upper_clips = create_text_clip(upper_text, "top") if upper_text else []
        lower_clips = create_text_clip(lower_text, "bottom") if lower_text else []
    
        final_clips = [clip] + upper_clips + lower_clips
        final = CompositeVideoClip(final_clips)
        meme_path = f"{unique_id}.webm"
        final.write_videofile(meme_path, codec="libvpx-vp9")
        return meme_path


    def process_frame(self, img, text, bg_color):
        i_width, i_height = img.size
        font_size = int((70 / 640) * i_width)
        font = ImageFont.truetype(self.font_path, font_size)

        if ";" in text:
            upper_text, lower_text = text.split(";")
        else:
            upper_text = text
            lower_text = ""

        draw = ImageDraw.Draw(img)

        def draw_text_with_outline(draw, text, position, font, fill, outline):
            x, y = position
            offsets = [-2, -1, 0, 1, 2]
            for dx in offsets:
                for dy in offsets:
                    if dx != 0 or dy != 0:
                        draw.text((x + dx, y + dy), text, font=font, fill=outline)
            draw.text((x, y), text, font=font, fill=fill)

        def draw_wrapped_text(lines, start_y, bg_color, align):
            current_h = start_y
            for line in lines:
                bbox = draw.textbbox((0, 0), line, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]

                if bg_color:
                    draw.rectangle(
                        [((i_width - text_width) / 2 - 5, current_h - 5),
                         ((i_width + text_width) / 2 + 5, current_h + text_height + 5)],
                        fill=bg_color,
                    )
                draw_text_with_outline(
                    draw,
                    line,
                    ((i_width - text_width) / 2, current_h),
                    font=font,
                    fill="white",
                    outline="black",
                )
                current_h += text_height + 10

        upper_lines = textwrap.wrap(upper_text, width=20)
        lower_lines = textwrap.wrap(lower_text, width=20)

        draw_wrapped_text(upper_lines, 10, bg_color, align="top")
        draw_wrapped_text(lower_lines, i_height - len(lower_lines) * font_size - 10, bg_color, align="bottom")

        return img


memify = Memify()


@app.on_message(filters.command("getsticker" , prefixes=config.COMMAND_PREFIXES))
async def getsticker_(self: Client, ctx: Message):
    if not ctx.reply_to_message:
        return await ctx.reply("𝖯𝗅𝖾𝖺𝗌𝖾 𝗋𝖾𝗉𝗅𝗒 𝗍𝗈 𝖺 𝗌𝗍𝗂𝖼𝗄𝖾𝗋 𝗍𝗈 𝗎𝗌𝖾 𝗍𝗁𝗂𝗌 𝖼𝗈𝗆𝗆𝖺𝗇𝖽.")
    
    sticker = ctx.reply_to_message.sticker
    if not sticker:
        return await ctx.reply("𝖳𝗁𝗂𝗌 𝖼𝗈𝗆𝗆𝖺𝗇𝖽 𝗈𝗇𝗅𝗒 𝗌𝗎𝗉𝗉𝗈𝗋𝗍𝗌 𝗌𝗍𝗂𝖼𝗄𝖾𝗋𝗌.")
    
    if sticker.is_animated:
        return await ctx.reply("𝖠𝗇𝗂𝗆𝖺𝗍𝖾𝖽 𝗌𝗍𝗂𝖼𝗄𝖾𝗋𝗌 𝖺𝗋𝖾 𝗇𝗈𝗍 𝗌𝗎𝗉𝗉𝗈𝗋𝗍𝖾𝖽.")
    
    with tempfile.TemporaryDirectory() as tempdir:
        path = os.path.join(tempdir, "getsticker")
    
    sticker_file = await self.download_media(
        message=ctx.reply_to_message,
        file_name=f"{path}/{sticker.set_name}.png",
    )
    
    await ctx.reply_to_message.reply_document(
        document=sticker_file,
        caption=f"<b>𝖤𝗆𝗈𝗃𝗂:</b> {sticker.emoji}\n"
                f"<b>𝖲𝗍𝗂𝖼𝗄𝖾𝗋 𝖨𝖣:</b> <code>{sticker.file_id}</code>\n\n",
        parse_mode=ParseMode.HTML,
    )
    shutil.rmtree(tempdir, ignore_errors=True)



@app.on_message(filters.command("getvidsticker" , prefixes=config.COMMAND_PREFIXES))
async def _vidstick(_, message):
    chat_id = message.chat.id
    replied = message.reply_to_message
    if replied and replied.sticker:
        if not replied.sticker.is_video:
            return await message.reply_text("𝖴𝗌𝖾 /𝗀𝖾𝗍𝗌𝗍𝗂𝖼𝗄𝖾𝗋 𝗂𝖿 𝗌𝗍𝗂𝖼𝗄𝖾𝗋 𝗂𝗌 𝗇𝗈𝗍 𝗏𝗂𝖽𝖾𝗈.")
        file_id = replied.sticker.file_id
        new_file = await _.download_media(file_id, file_name="sticker.mp4")
        await _.send_animation(chat_id, new_file)
        os.remove(new_file)
    else:
        await message.reply_text("𝖯𝗅𝖾𝖺𝗌𝖾 𝗋𝖾𝗉𝗅𝗒 𝗍𝗈 𝖺 𝗏𝗂𝖽𝖾𝗈 𝗌𝗍𝗂𝖼𝗄𝖾𝗋 𝗍𝗈 𝗎𝗉𝗅𝗈𝖺𝖽 𝗂𝗍'𝗌 𝖬𝖯𝟦.")


@app.on_message(filters.command("getvideo" , prefixes=config.COMMAND_PREFIXES))
async def _vidstick(_, message):
    chat_id = message.chat.id
    replied = message.reply_to_message
    if replied and replied.animation:
        file_id = replied.animation.file_id
        new_file = await _.download_media(file_id, file_name="video.mp4")
        print(new_file)
        await _.send_video(chat_id, video=open(new_file, "rb"))
        os.remove(new_file)
    else:
        await message.reply_text("𝖯𝗅𝖾𝖺𝗌𝖾 𝗋𝖾𝗉𝗅𝗒 𝗍𝗈 𝖺 𝗀𝗂𝖿 𝖿𝗈𝗋 𝗆𝖾 𝗍𝗈 𝗀𝖾𝗍 𝗂𝗍'𝗌 𝗏𝗂𝖽𝖾𝗈.")


@app.on_message(filters.command("stickerid" , prefixes=config.COMMAND_PREFIXES) & filters.reply)
async def getstickerid(_, ctx: Message):
    if ctx.reply_to_message.sticker:
        await ctx.reply(
            "𝖳𝗁𝖾 𝖨𝖣 𝗈𝖿 𝗍𝗁𝗂𝗌 𝗌𝗍𝗂𝖼𝗄𝖾𝗋 𝗂𝗌: <code>{stickerid}</code>".format(
                stickerid=ctx.reply_to_message.sticker.file_id
            )
        )


@app.on_message(filters.command("unkang" , prefixes=config.COMMAND_PREFIXES) & filters.reply)
async def unkangs(self: Client, ctx: Message):
    if not ctx.from_user:
        return await ctx.reply("𝖨 𝖽𝗈𝗇'𝗍 𝗄𝗇𝗈𝗐 𝗐𝗁𝗈 𝗒𝗈𝗎 𝖺𝗋𝖾. 𝖳𝗋𝗒 𝗎𝗌𝗂𝗇𝗀 𝗍𝗁𝗂𝗌 𝖼𝗈𝗆𝗆𝖺𝗇𝖽 𝗂𝗇 𝖺 𝗉𝗋𝗂𝗏𝖺𝗍𝖾 𝗆𝖾𝗌𝗌𝖺𝗀𝖾.")
    
    if sticker := ctx.reply_to_message.sticker:
        if str(ctx.from_user.id) not in sticker.set_name:
            return await ctx.reply("𝖳𝗁𝗂𝗌 𝗌𝗍𝗂𝖼𝗄𝖾𝗋 𝗂𝗌 𝗇𝗈𝗍 𝗂𝗇 𝗒𝗈𝗎𝗋 𝗉𝖺𝖼𝗄!")
        
        pp = await ctx.reply("𝖱𝖾𝗆𝗈𝗏𝗂𝗇𝗀 𝗌𝗍𝗂𝖼𝗄𝖾𝗋 𝖿𝗋𝗈𝗆 𝗒𝗈𝗎𝗋 𝗉𝖺𝖼𝗄...")
        
        try:
            decoded = FileId.decode(sticker.file_id)
            sticker = InputDocument(
                id=decoded.media_id,
                access_hash=decoded.access_hash,
                file_reference=decoded.file_reference,
            )
            await app.invoke(RemoveStickerFromSet(sticker=sticker))
            await pp.edit("𝖲𝗍𝗂𝖼𝗄𝖾𝗋 𝗋𝖾𝗆𝗈𝗏𝖾𝖽 𝗌𝗎𝖼𝖼𝖾𝗌𝗌𝖿𝗎𝗅𝗅𝗒!")
        except Exception as e:
            await pp.edit(f"𝖠𝗇 𝖾𝗋𝗋𝗈𝗋 𝗈𝖼𝖼𝗎𝗋𝗋𝖾𝖽 𝗐𝗁𝗂𝗅𝖾 𝗋𝖾𝗆𝗈𝗏𝗂𝗇𝗀 𝗍𝗁𝖾 𝗌𝗍𝗂𝖼𝗄𝖾𝗋: {e}")
    else:
        await ctx.reply(f"𝖴𝗌𝖺𝗀𝖾: 𝖱𝖾𝗉𝗅𝗒 𝗍𝗈 𝖺 𝗌𝗍𝗂𝖼𝗄𝖾𝗋 𝗍𝗈 𝗋𝖾𝗆𝗈𝗏𝖾 𝗂𝗍 𝖿𝗋𝗈𝗆 𝗒𝗈𝗎𝗋 𝗉𝖺𝖼𝗄. 𝖤𝗑𝖺𝗆𝗉𝗅𝖾: /𝗎𝗇𝗄𝖺𝗇𝗀 @{self.me.username}")


def _slugify_link(raw: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_]", "", raw.strip())
    if not slug:
        return ""
    if slug[0].isdigit():
        slug = f"p{slug}"
    return slug[:40]


@app.on_message(filters.command("newpack", prefixes=config.COMMAND_PREFIXES) & filters.private)
async def new_pack(client: Client, message: Message):
    if not message.from_user:
        return await message.reply("𝖯𝗅𝖾𝖺𝗌𝖾 𝗎𝗌𝖾 𝗍𝗁𝗂𝗌 𝗂𝗇 𝖺 𝗉𝗋𝗂𝗏𝖺𝗍𝖾 𝗆𝖾𝗌𝗌𝖺𝗀𝖾 𝗐𝗂𝗍𝗁 𝗆𝖾.")
    user_id = message.from_user.id

    try:
        name_msg = await client.ask(
            message.chat.id,
            "📦 𝖲𝖾𝗇𝖽 𝖺 **𝗇𝖺𝗆𝖾** (𝗍𝗂𝗍𝗅𝖾) 𝖿𝗈𝗋 𝗒𝗈𝗎𝗋 𝗇𝖾𝗐 𝗌𝗍𝗂𝖼𝗄𝖾𝗋 𝗉𝖺𝖼𝗄.\n𝖮𝗋 /cancel 𝗍𝗈 𝗌𝗍𝗈𝗉.",
            filters=filters.text,
            timeout=120,
        )
    except asyncio.TimeoutError:
        return await message.reply("⌛ 𝖳𝗂𝗆𝖾𝖽 𝗈𝗎𝗍. 𝖯𝗅𝖾𝖺𝗌𝖾 𝗍𝗋𝗒 /newpack 𝖺𝗀𝖺𝗂𝗇.")
    if name_msg.text.strip().lower() in ("/cancel", "cancel"):
        return await name_msg.reply("❌ 𝖢𝖺𝗇𝖼𝖾𝗅𝗅𝖾𝖽.")
    title = name_msg.text.strip()[:64]

    try:
        link_msg = await client.ask(
            message.chat.id,
            "🔗 𝖭𝗈𝗐 𝗌𝖾𝗇𝖽 𝖺 𝗌𝗁𝗈𝗋𝗍 **𝗅𝗂𝗇𝗄 𝗇𝖺𝗆𝖾** 𝖿𝗈𝗋 𝗍𝗁𝖾 𝗉𝖺𝖼𝗄 (𝗅𝖾𝗍𝗍𝖾𝗋𝗌/𝗇𝗎𝗆𝖻𝖾𝗋𝗌/𝗎𝗇𝖽𝖾𝗋𝗌𝖼𝗈𝗋𝖾 𝗈𝗇𝗅𝗒, "
            "𝖾.𝗀. `myfunnypack`).\n𝖳𝗁𝗂𝗌 𝖻𝖾𝖼𝗈𝗆𝖾𝗌: t.me/addstickers/<𝗅𝗂𝗇𝗄>\n𝖮𝗋 /cancel 𝗍𝗈 𝗌𝗍𝗈𝗉.",
            filters=filters.text,
            timeout=120,
        )
    except asyncio.TimeoutError:
        return await message.reply("⌛ 𝖳𝗂𝗆𝖾𝖽 𝗈𝗎𝗍. 𝖯𝗅𝖾𝖺𝗌𝖾 𝗍𝗋𝗒 /newpack 𝖺𝗀𝖺𝗂𝗇.")
    if link_msg.text.strip().lower() in ("/cancel", "cancel"):
        return await link_msg.reply("❌ 𝖢𝖺𝗇𝖼𝖾𝗅𝗅𝖾𝖽.")

    slug = _slugify_link(link_msg.text)
    if not slug:
        return await link_msg.reply("⚠️ 𝖳𝗁𝖺𝗍 𝗅𝗂𝗇𝗄 𝗇𝖺𝗆𝖾 𝗂𝗌𝗇'𝗍 𝗏𝖺𝗅𝗂𝖽. 𝖯𝗅𝖾𝖺𝗌𝖾 𝗍𝗋𝗒 /newpack 𝖺𝗀𝖺𝗂𝗇 𝗐𝗂𝗍𝗁 𝗅𝖾𝗍𝗍𝖾𝗋𝗌/𝗇𝗎𝗆𝖻𝖾𝗋𝗌 𝗈𝗇𝗅𝗒.")

    short_name = f"{slug}_{user_id}_by_{client.me.username}"
    if await get_pack(user_id, short_name):
        return await link_msg.reply("⚠️ 𝖸𝗈𝗎 𝖺𝗅𝗋𝖾𝖺𝖽𝗒 𝗁𝖺𝗏𝖾 𝖺 𝗉𝖺𝖼𝗄 𝗐𝗂𝗍𝗁 𝗍𝗁𝖺𝗍 𝗅𝗂𝗇𝗄 𝗇𝖺𝗆𝖾. 𝖳𝗋𝗒 /newpack 𝖺𝗀𝖺𝗂𝗇 𝗐𝗂𝗍𝗁 𝖺 𝖽𝗂𝖿𝖿𝖾𝗋𝖾𝗇𝗍 𝗈𝗇𝖾.")

    # kind is decided by whatever the FIRST /kang into this pack turns out
    # to be (photo vs video vs animated) - default to static for now, the
    # kang flow re-tags it correctly once real media arrives.
    await add_pack(user_id, short_name, title, kind="static")
    await set_active_pack(user_id, short_name)

    await link_msg.reply(
        f"✅ 𝖯𝖺𝖼𝗄 **{title}** 𝗋𝖾𝗀𝗂𝗌𝗍𝖾𝗋𝖾𝖽 𝖺𝗇𝖽 𝗌𝖾𝗍 𝖺𝗌 𝗒𝗈𝗎𝗋 𝖺𝖼𝗍𝗂𝗏𝖾 𝗉𝖺𝖼𝗄!\n\n"
        f"🔗 𝖫𝗂𝗇𝗄: `t.me/addstickers/{short_name}`\n\n"
        f"𝖭𝗈𝗐 𝗋𝖾𝗉𝗅𝗒 𝗍𝗈 𝖺𝗇𝗒 𝗌𝗍𝗂𝖼𝗄𝖾𝗋/𝗉𝗁𝗈𝗍𝗈/𝗀𝗂𝖿/𝗏𝗂𝖽𝖾𝗈 𝗐𝗂𝗍𝗁 /kang 𝗍𝗈 𝖺𝖽𝖽 𝗂𝗍 𝗁𝖾𝗋𝖾 - 𝗍𝗁𝖾 𝗉𝖺𝖼𝗄 𝗂𝗌 𝖼𝗋𝖾𝖺𝗍𝖾𝖽 𝗈𝗇 𝖳𝖾𝗅𝖾𝗀𝗋𝖺𝗆 𝖺𝗎𝗍𝗈𝗆𝖺𝗍𝗂𝖼𝖺𝗅𝗅𝗒 𝗐𝗂𝗍𝗁 𝗒𝗈𝗎𝗋 𝖿𝗂𝗋𝗌𝗍 𝗌𝗍𝗂𝖼𝗄𝖾𝗋.\n\n"
        f"𝖴𝗌𝖾 /mypacks 𝖺𝗇𝗒𝗍𝗂𝗆𝖾 𝗍𝗈 𝗌𝖾𝖾 𝗈𝗋 𝗌𝗐𝗂𝗍𝖼𝗁 𝖻𝖾𝗍𝗐𝖾𝖾𝗇 𝗒𝗈𝗎𝗋 𝗉𝖺𝖼𝗄𝗌."
    )


def _pack_kind_emoji(kind: str) -> str:
    return {"animated": "🎞", "video": "📹"}.get(kind, "🖼")


async def _render_packs_keyboard(user_id: int):
    packs = await get_packs(user_id)
    if not packs:
        return None
    rows = []
    for p in packs:
        mark = "✅ " if p.get("active") else ""
        rows.append([
            InlineKeyboardButton(
                f"{mark}{_pack_kind_emoji(p.get('kind', 'static'))} {p['title']}",
                callback_data=f"spk_sel_{p['short_name']}",
            )
        ])
        link_btn = (
            InlineKeyboardButton("🔗 𝖮𝗉𝖾𝗇", url=f"https://t.me/addstickers/{p['short_name']}")
            if p.get("created")
            else InlineKeyboardButton("⏳ 𝖤𝗆𝗉𝗍𝗒 (𝗄𝖺𝗇𝗀 𝗍𝗈 𝖼𝗋𝖾𝖺𝗍𝖾)", callback_data="spk_noop")
        )
        rows.append([link_btn, InlineKeyboardButton("🗑 𝖣𝖾𝗅𝖾𝗍𝖾", callback_data=f"spk_del_{p['short_name']}")])
    return InlineKeyboardMarkup(rows)


@app.on_message(filters.command(["mypacks", "packs"], prefixes=config.COMMAND_PREFIXES) & filters.private)
async def my_packs(client: Client, message: Message):
    if not message.from_user:
        return await message.reply("𝖯𝗅𝖾𝖺𝗌𝖾 𝗎𝗌𝖾 𝗍𝗁𝗂𝗌 𝗂𝗇 𝖺 𝗉𝗋𝗂𝗏𝖺𝗍𝖾 𝗆𝖾𝗌𝗌𝖺𝗀𝖾 𝗐𝗂𝗍𝗁 𝗆𝖾.")
    kb = await _render_packs_keyboard(message.from_user.id)
    if not kb:
        return await message.reply("𝖸𝗈𝗎 𝖽𝗈𝗇'𝗍 𝗁𝖺𝗏𝖾 𝖺𝗇𝗒 𝗇𝖺𝗆𝖾𝖽 𝗉𝖺𝖼𝗄𝗌 𝗒𝖾𝗍. 𝖴𝗌𝖾 /newpack 𝗍𝗈 𝖼𝗋𝖾𝖺𝗍𝖾 𝗈𝗇𝖾!")
    await message.reply(
        "**📦 𝖸𝗈𝗎𝗋 𝖲𝗍𝗂𝖼𝗄𝖾𝗋 𝖯𝖺𝖼𝗄𝗌**\n𝖳𝖺𝗉 𝖺 𝗉𝖺𝖼𝗄 𝗍𝗈 𝗆𝖺𝗄𝖾 𝗂𝗍 𝖺𝖼𝗍𝗂𝗏𝖾 (𝗎𝗌𝖾𝖽 𝖻𝗒 /kang), 𝗈𝗋 /kang #<𝗅𝗂𝗇𝗄> 𝗍𝗈 𝗍𝖺𝗋𝗀𝖾𝗍 𝗈𝗇𝖾 𝗃𝗎𝗌𝗍 𝗈𝗇𝖼𝖾.",
        reply_markup=kb,
    )


@app.on_callback_query(filters.regex(r"^spk_sel_"))
async def spk_select(client: Client, query):
    short_name = query.data[len("spk_sel_"):]
    await set_active_pack(query.from_user.id, short_name)
    await query.answer("✅ 𝖠𝖼𝗍𝗂𝗏𝖾 𝗉𝖺𝖼𝗄 𝗎𝗉𝖽𝖺𝗍𝖾𝖽!")
    kb = await _render_packs_keyboard(query.from_user.id)
    if kb:
        try:
            await query.message.edit_reply_markup(kb)
        except Exception:
            pass


@app.on_callback_query(filters.regex(r"^spk_del_"))
async def spk_delete(client: Client, query):
    short_name = query.data[len("spk_del_"):]
    pack = await get_pack(query.from_user.id, short_name)
    if not pack:
        return await query.answer("𝖠𝗅𝗋𝖾𝖺𝖽𝗒 𝗋𝖾𝗆𝗈𝗏𝖾𝖽.", show_alert=True)
    if pack.get("created"):
        try:
            await client.invoke(DeleteStickerSet(stickerset=InputStickerSetShortName(short_name=short_name)))
        except Exception:
            pass  # still remove it from our records even if Telegram's side fails/is already gone
    await delete_pack(query.from_user.id, short_name)
    await query.answer("🗑 𝖯𝖺𝖼𝗄 𝖽𝖾𝗅𝖾𝗍𝖾𝖽.", show_alert=True)
    kb = await _render_packs_keyboard(query.from_user.id)
    try:
        if kb:
            await query.message.edit_reply_markup(kb)
        else:
            await query.message.edit_text("𝖸𝗈𝗎 𝖽𝗈𝗇'𝗍 𝗁𝖺𝗏𝖾 𝖺𝗇𝗒 𝗇𝖺𝗆𝖾𝖽 𝗉𝖺𝖼𝗄𝗌 𝗅𝖾𝖿𝗍. 𝖴𝗌𝖾 /newpack 𝗍𝗈 𝖼𝗋𝖾𝖺𝗍𝖾 𝗈𝗇𝖾!")
    except Exception:
        pass


@app.on_callback_query(filters.regex(r"^spk_noop$"))
async def spk_noop(client: Client, query):
    await query.answer("𝖭𝗈 𝗌𝗍𝗂𝖼𝗄𝖾𝗋𝗌 𝗂𝗇 𝗍𝗁𝗂𝗌 𝗉𝖺𝖼𝗄 𝗒𝖾𝗍 - 𝗄𝖺𝗇𝗀 𝗌𝗈𝗆𝖾𝗍𝗁𝗂𝗇𝗀 𝗂𝗇𝗍𝗈 𝗂𝗍 𝖿𝗂𝗋𝗌𝗍!", show_alert=True)


@app.on_message(filters.command("kang" , prefixes=config.COMMAND_PREFIXES))
async def kang_sticker(self: Client, ctx: Message):
    if not ctx.from_user:
        return await ctx.reply("𝖸𝗈𝗎 𝖼𝖺𝗇'𝗍 𝗎𝗌𝖾 𝗍𝗁𝗂𝗌 𝖼𝗈𝗆𝗆𝖺𝗇𝖽 𝖺𝗇𝗈𝗇𝗒𝗆𝗈𝗎𝗌𝗅𝗒.")
    
    prog_msg = await ctx.reply("**𝖯𝗅𝖾𝖺𝗌𝖾 𝖶𝖺𝗂𝗍 𝖠𝗇𝖽 𝖫𝖾𝗍 𝖬𝖾 𝖯𝗋𝗈𝖼𝖾𝗌𝗌 𝖸𝗈𝗎𝗋 𝖱𝖾𝗊𝗎𝖾𝗌𝗍...**")
    sticker_emoji = "✔️"
    packnum = 0
    packname_found = False
    resize = False
    animated = False
    videos = False
    convert = False
    reply = ctx.reply_to_message
    user = await self.resolve_peer(ctx.from_user.username or ctx.from_user.id)

    if reply and reply.media:
        if reply.photo:
            resize = True
        elif reply.animation:
            videos = True
            convert = True
        elif reply.video:
            convert = True
            videos = True
        elif reply.document:
            if "image" in reply.document.mime_type:
                # mime_type: image/webp
                resize = True
            elif reply.document.mime_type in (
                enums.MessageMediaType.VIDEO,
                enums.MessageMediaType.ANIMATION,
            ):
                # mime_type: application/video
                videos = True
                convert = True
            elif "tgsticker" in reply.document.mime_type:
                # mime_type: application/x-tgsticker
                animated = True
        elif reply.sticker:
            if not reply.sticker.file_name:
                return await prog_msg.edit("𝖳𝗁𝗂𝗌 𝗌𝗍𝗂𝖼𝗄𝖾𝗋 𝗁𝖺𝗌 𝗇𝗈 𝖿𝗂𝗅𝖾 𝗇𝖺𝗆𝖾!")
            if reply.sticker.emoji:
                sticker_emoji = reply.sticker.emoji
            animated = reply.sticker.is_animated
            videos = reply.sticker.is_video
            if videos:
                convert = False
            elif not reply.sticker.file_name.endswith(".tgs"):
                resize = True
        else:
            return await prog_msg.edit("𝖴𝗇𝖺𝖻𝗅𝖾 𝖳𝗈 𝖪𝖺𝗇𝗀 𝖳𝗁𝗂𝗌 𝖳𝗒𝗉𝖾.")

        pack_prefix = "anim" if animated else "vid" if videos else "a"
        packname = f"{pack_prefix}_{ctx.from_user.id}_by_{self.me.username}"
        pack_title_override = None
        explicit_pack = False

        if (
            len(ctx.command) > 1
            and ctx.command[1].isdigit()
            and int(ctx.command[1]) > 0
        ):
            # provide pack number to kang in desired pack
            packnum = int(ctx.command.pop(1))
            packname = (
                f"{pack_prefix}{packnum}_{ctx.from_user.id}_by_{self.me.username}"
            )
            explicit_pack = True
        elif ctx.command and len(ctx.command) > 1 and ctx.command[1].startswith("#"):
            # /kang #packlink -> target a specific named pack directly by
            # its short link (as shown in /mypacks), instead of the active one
            wanted = ctx.command.pop(1)[1:]
            found_pack = await get_pack(ctx.from_user.id, wanted) or next(
                (p for p in await get_packs(ctx.from_user.id) if p["short_name"].split("_", 1)[0] == wanted),
                None,
            )
            if found_pack:
                packname = found_pack["short_name"]
                pack_title_override = found_pack["title"]
                explicit_pack = True

        if not explicit_pack:
            # No pack explicitly named in the command - fall back to
            # whichever named pack the user has marked active via
            # /mypacks (see /newpack), so kangs land in the pack they
            # actually chose instead of always the legacy default one.
            kind = "animated" if animated else "video" if videos else "static"
            active = await get_active_pack(ctx.from_user.id, kind)
            if active:
                packname = active["short_name"]
                pack_title_override = active["title"]

        if len(ctx.command) > 1:
            # matches all valid emojis in input
            sticker_emoji = (
                "".join(set(EMOJI_PATTERN.findall("".join(ctx.command[1:]))))
                or sticker_emoji
            )
        filename = await self.download_media(ctx.reply_to_message)
        if not filename:
            # Failed to download
            await prog_msg.delete()
            return
    elif ctx.entities and len(ctx.entities) > 1:
        pack_prefix = "a"
        filename = "sticker.png"
        packname = f"c{ctx.from_user.id}_by_{self.me.username}"
        img_url = next(
            (
                ctx.text[y.offset : (y.offset + y.length)]
                for y in ctx.entities
                if y.type == "url"
            ),
            None,
        )

        if not img_url:
            await prog_msg.delete()
            return
        try:
            r = await state.get(img_url)
            if r.status_code == 200:
                with open(filename, mode="wb") as f:
                    f.write(r.read())
        except Exception as r_e:
            return await prog_msg.edit(f"{r_e.__class__.__name__} : {r_e}")
        if len(ctx.command) > 2:
            # m.command[1] is image_url
            if ctx.command[2].isdigit() and int(ctx.command[2]) > 0:
                packnum = ctx.command.pop(2)
                packname = f"a{packnum}_{ctx.from_user.id}_by_{self.me.username}"
            if len(ctx.command) > 2:
                sticker_emoji = (
                    "".join(set(EMOJI_PATTERN.findall("".join(ctx.command[2:]))))
                    or sticker_emoji
                )
            resize = True
    else:
        return await prog_msg.edit(
            "𝖴𝗌𝖺𝗀𝖾: 𝖱𝖾𝗉𝗅𝗒 𝗍𝗈 𝖺 𝗆𝖾𝗌𝗌𝖺𝗀𝖾 𝗐𝗂𝗍𝗁 𝖺 𝗉𝗁𝗈𝗍𝗈, 𝗌𝗍𝗂𝖼𝗄𝖾𝗋, 𝗈𝗋 𝖺𝗇𝗂𝗆𝖺𝗍𝗂𝗈𝗇 𝗍𝗈 𝗄𝖺𝗇𝗀 𝗂𝗍!"
        )
    try:
        if resize:
            filename = resize_image(filename)
        elif convert:
            filename = await convert_video(filename)
            if filename is False:
                return await prog_msg.edit("Error")
        max_stickers = 50 if animated else 120
        while not packname_found:
            try:
                stickerset = await self.invoke(
                    GetStickerSet(
                        stickerset=InputStickerSetShortName(short_name=packname),
                        hash=0,
                    )
                )
                if stickerset.set.count >= max_stickers:
                    packnum += 1
                    packname = f"{pack_prefix}_{packnum}_{ctx.from_user.id}_by_{self.me.username}"
                else:
                    packname_found = True
            except StickersetInvalid:
                break
        file = await self.save_file(filename)
        # `guess_mime_type()` returns None for extensions it doesn't
        # recognise (this is what caused "'NoneType' object has no
        # attribute 'encode'" - pyrogram tries to .encode() the mime type
        # string internally). Always fall back to something sane instead.
        mime_type = self.guess_mime_type(filename) or (
            "video/webm" if filename.endswith(".webm")
            else "application/x-tgsticker" if filename.endswith(".tgs")
            else "image/png"
        )
        media = await self.invoke(
            SendMedia(
                peer=(await self.resolve_peer(config.LOG_CHANNEL)),
                media=InputMediaUploadedDocument(
                    file=file,
                    mime_type=mime_type,
                    attributes=[DocumentAttributeFilename(file_name=filename)],
                ),
                message=f"𝖲𝗍𝗂𝖼𝗄𝖾𝗋 𝗄𝖺𝗇𝗀𝖾𝖽 𝖻𝗒 -> {ctx.from_user.mention}",
                random_id=self.rnd_id(),
            ),
        )
        msg_ = media.updates[-1].message
        stkr_file = msg_.media.document
        if packname_found:
            await prog_msg.edit("𝖠𝖽𝖽𝗂𝗇𝗀 𝗍𝗈 𝗍𝗁𝖾 𝖾𝗑𝗂𝗌𝗍𝗂𝗇𝗀 𝗌𝗍𝗂𝖼𝗄𝖾𝗋 𝗉𝖺𝖼𝗄...")
            await self.invoke(
                AddStickerToSet(
                    stickerset=InputStickerSetShortName(short_name=packname),
                    sticker=InputStickerSetItem(
                        document=InputDocument(
                            id=stkr_file.id,
                            access_hash=stkr_file.access_hash,
                            file_reference=stkr_file.file_reference,
                        ),
                        emoji=sticker_emoji,
                    ),
                )
            )
        else:
            await prog_msg.edit("𝖢𝗋𝖾𝖺𝗍𝗂𝗇𝗀 𝖺 𝗇𝖾𝗐 𝗌𝗍𝗂𝖼𝗄𝖾𝗋 𝗉𝖺𝖼𝗄...")
            if pack_title_override:
                stkr_title = pack_title_override
            else:
                stkr_title = f"{ctx.from_user.first_name}'s"
                if animated:
                    stkr_title += " Animated-Pack"
                elif videos:
                    stkr_title += " Video-Pack"
                if packnum != 0:
                    stkr_title += f" v{packnum}"
            try:
                await self.invoke(
                    CreateStickerSet(
                        user_id=user,
                        title=stkr_title,
                        short_name=packname,
                        stickers=[
                            InputStickerSetItem(
                                document=InputDocument(
                                    id=stkr_file.id,
                                    access_hash=stkr_file.access_hash,
                                    file_reference=stkr_file.file_reference,
                                ),
                                emoji=sticker_emoji,
                            )
                        ]
                    )
                )
            except PeerIdInvalid:
                return await prog_msg.edit(
                    "𝖯𝗅𝖾𝖺𝗌𝖾 𝗌𝗍𝖺𝗋𝗍 𝗍𝗁𝖾 𝖻𝗈𝗍 𝖻𝗒 𝖼𝗅𝗂𝖼𝗄𝗂𝗇𝗀 𝗍𝗁𝖾 𝖻𝗎𝗍𝗍𝗈𝗇 𝖻𝖾𝗅𝗈𝗐:",
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton(
                                    "𝖢𝗅𝗂𝖼𝗄 𝗆𝖾!",
                                    url=f"https://t.me/{self.me.username}?start",
                                )
                            ]
                        ]
                    ),
                )

    except BadRequest:
            return await prog_msg.edit("𝖳𝗁𝖾 𝗌𝗍𝗂𝖼𝗄𝖾𝗋 𝗉𝖺𝖼𝗄 𝗂𝗌 𝖿𝗎𝗅𝗅. 𝖯𝗅𝖾𝖺𝗌𝖾 𝖼𝗋𝖾𝖺𝗍𝖾 𝖺 𝗇𝖾𝗐 𝗉𝖺𝖼𝗄.")
    except Exception as all_e:
        await prog_msg.edit(f"{all_e.__class__.__name__} : {all_e}")
    else:
        markup = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        text="𝖵𝗂𝖾𝗐 𝖲𝗍𝗂𝖼𝗄𝖾𝗋 𝖯𝖺𝖼𝗄",
                        url=f"https://t.me/addstickers/{packname}",
                    )
                ]
            ]
        )
        await prog_msg.edit(
           f"{sticker_emoji} 𝖲𝗍𝗂𝖼𝗄𝖾𝗋 𝖺𝖽𝖽𝖾𝖽 𝗌𝗎𝖼𝖼𝖾𝗌𝗌𝖿𝗎𝗅𝗅𝗒 𝗍𝗈 𝗒𝗈𝗎𝗋 𝗉𝖺𝖼𝗄 !!",
            reply_markup=markup,
        )
        if not packname_found:
            # Pack was just created on Telegram for the first time - if it
            # was one of the user's /newpack-registered named packs,
            # flip it to "created" so /mypacks shows a working link.
            kind = "animated" if animated else "video" if videos else "static"
            existing_named = await get_pack(ctx.from_user.id, packname)
            if existing_named:
                await mark_created(ctx.from_user.id, packname)
            elif pack_title_override:
                await add_pack(ctx.from_user.id, packname, pack_title_override, kind)
                await mark_created(ctx.from_user.id, packname)
                await set_active_pack(ctx.from_user.id, packname)
        # Cleanup
        await self.delete_messages(
            chat_id=config.LOG_CHANNEL, message_ids=msg_.id, revoke=True
        )
        try:
            os.remove(filename)
        except OSError:
            pass


def resize_image(filename: str) -> str:
    im = Image.open(filename)
    maxsize = 512
    scale = maxsize / max(im.width, im.height)
    sizenew = (int(im.width * scale), int(im.height * scale))
    im = im.resize(sizenew, Image.NEAREST)
    downpath, f_name = os.path.split(filename)
    # not hardcoding png_image as "sticker.png"
    png_image = os.path.join(downpath, f"{f_name.split('.', 1)[0]}.png")
    im.save(png_image, "PNG")
    if png_image != filename:
        os.remove(filename)
    return png_image


async def convert_video(filename: str) -> str:
    downpath, f_name = os.path.split(filename)
    webm_video = os.path.join(downpath, f"{f_name.split('.', 1)[0]}.webm")
    cmd = [
        "ffmpeg",
        "-loglevel",
        "quiet",
        "-i",
        filename,
        "-t",
        "00:00:03",
        "-vf",
        "fps=30",
        "-c:v",
        "vp9",
        "-b:v:",
        "500k",
        "-preset",
        "ultrafast",
        "-s",
        "512x512",
        "-y",
        "-an",
        webm_video,
    ]

    proc = await asyncio.create_subprocess_exec(*cmd)
    # Wait for the subprocess to finish
    await proc.communicate()

    if webm_video != filename:
        os.remove(filename)
    return webm_video


@app.on_message(filters.command(["stickerinfo", "stinfo"] , prefixes=config.COMMAND_PREFIXES))
async def give_st_info(c: app, m: Message):  # type: ignore
    if not m.reply_to_message:
        await m.reply_text("𝖯𝗅𝖾𝖺𝗌𝖾 𝗋𝖾𝗉𝗅𝗒 𝗍𝗈 𝖺 𝗌𝗍𝗂𝖼𝗄𝖾𝗋 𝗍𝗈 𝗀𝖾𝗍 𝗂𝗍𝗌 𝗂𝗇𝖿𝗈𝗋𝗆𝖺𝗍𝗂𝗈𝗇.")
        return
    elif not m.reply_to_message.sticker:
        await m.reply_text("𝖳𝗁𝖾 𝗋𝖾𝗉𝗅𝗂𝖾𝖽 𝗆𝖾𝗌𝗌𝖺𝗀𝖾 𝗂𝗌 𝗇𝗈𝗍 𝖺 𝗌𝗍𝗂𝖼𝗄𝖾𝗋. 𝖯𝗅𝖾𝖺𝗌𝖾 𝗋𝖾𝗉𝗅𝗒 𝗍𝗈 𝖺 𝗌𝗍𝗂𝖼𝗄𝖾𝗋.")
        return
    
    st_in = m.reply_to_message.sticker
    st_type = "Normal"
    if st_in.is_animated:
        st_type = "Animated"
    elif st_in.is_video:
        st_type = "Video"
    
    st_info = f"""
𝖲𝗍𝗂𝖼𝗄𝖾𝗋 𝖨𝗇𝖿𝗈𝗋𝗆𝖺𝗍𝗂𝗈𝗇:
- **𝖥𝗂𝗅𝖾 𝖨𝖣:** `{st_in.file_id}`
- **𝖥𝗂𝗅𝖾 𝖭𝖺𝗆𝖾:** {st_in.file_name or "N/A"}
- **𝖴𝗇𝗂𝗊𝗎𝖾 𝖥𝗂𝗅𝖾 𝖨𝖣:** `{st_in.file_unique_id}`
- **𝖣𝖺𝗍𝖾 𝖢𝗋𝖾𝖺𝗍𝖾𝖽:** `{st_in.date}`
- **𝖲𝗍𝗂𝖼𝗄𝖾𝗋 𝖳𝗒𝗉𝖾:** {st_type}
- **𝖤𝗆𝗈𝗃𝗂:** {st_in.emoji or "N/A"}
- **𝖯𝖺𝖼𝗄 𝖭𝖺𝗆𝖾:** {st_in.set_name or "N/A"}
    """
    
    kb = None
    if st_in.set_name:
        kb = IKM(
            [
                [
                    IKB(
                        "➕ 𝖠𝖽𝖽 𝖲𝗍𝗂𝖼𝗄𝖾𝗋 𝖯𝖺𝖼𝗄",
                        url=f"https://t.me/addstickers/{st_in.set_name}"
                    )
                ]
            ]
        )
    await m.reply_text(st_info.strip(), reply_markup=kb)


@app.on_message(filters.command("mmf", prefixes=config.COMMAND_PREFIXES))
async def handler(client: Client, message: Message):
    if not message.reply_to_message:
        await message.reply("Reply to an image, video, or video sticker to memify it!")
        return

    reply_message = message.reply_to_message
    if not reply_message.media:
        await message.reply("Provide some text, please...")
        return

    # Grab everything after the command word itself, robustly - this used
    # to split on the literal string "/mmf " which threw an IndexError
    # (crashing the whole dispatcher) whenever someone sent bare "/mmf"
    # with no trailing text, or used a different command prefix.
    text_parts = message.text.split(None, 1) if message.text else []
    command_text = text_parts[1].strip() if len(text_parts) > 1 else ""
    if not command_text:
        await message.reply("You might want to try `/mmf text`")
        return

    file = await client.download_media(reply_message)
    msg = await message.reply("Memifying this media! Please wait.")

    bg_color = None
    if "-back" in command_text:
        parts = command_text.split("-back")
        text = parts[0].strip()
        bg_color = parts[1].strip().split()[0]
    else:
        text = command_text

    meme = memify.draw_text(file, text, bg_color)

    if meme.endswith(".webm"):
        await client.send_sticker(message.chat.id, sticker=meme , emoji="🌐")
    else:
        await client.send_document(message.chat.id, document=meme)

    await msg.delete()
    os.remove(meme)



__module__ = "𝖲𝗍𝗂𝖼𝗄𝖾𝗋𝗌"


__help__ = """**𝖲𝗍𝗂𝖼𝗄𝖾𝗋 𝖬𝖺𝗇𝖺𝗀𝖾𝗆𝖾𝗇𝗍 𝖢𝗈𝗆𝗆𝖺𝗇𝖽𝗌:**

- **𝖱𝖾𝗍𝗋𝗂𝖾𝗏𝖾 𝖲𝗍𝗂𝖼𝗄𝖾𝗋 𝖨𝗇𝖿𝗈𝗋𝗆𝖺𝗍𝗂𝗈𝗇:**
  ✧ `/𝗌𝗍𝗂𝖼𝗄𝖾𝗋𝗂𝗇𝖿𝗈` 𝗈𝗋 `/𝗌𝗍𝗂𝗇𝖿𝗈`: 𝖱𝖾𝗉𝗅𝗒 𝗍𝗈 𝖺 𝗌𝗍𝗂𝖼𝗄𝖾𝗋 𝗍𝗈 𝗀𝖾𝗍 𝗂𝗍𝗌 𝖽𝖾𝗍𝖺𝗂𝗅𝖾𝖽 𝗂𝗇𝖿𝗈𝗋𝗆𝖺𝗍𝗂𝗈𝗇 𝗌𝗎𝖼𝗁 𝖺𝗌 𝖥𝗂𝗅𝖾 𝖨𝖣, 𝖤𝗆𝗈𝗃𝗂, 𝖳𝗒𝗉𝖾, 𝖺𝗇𝖽 𝖯𝖺𝖼𝗄 𝖭𝖺𝗆𝖾.
 
- **𝖣𝗈𝗐𝗇𝗅𝗈𝖺𝖽 𝖲𝗍𝗂𝖼𝗄𝖾𝗋𝗌:**
  ✧ `/𝗀𝖾𝗍𝗌𝗍𝗂𝖼𝗄𝖾𝗋`: 𝖱𝖾𝗉𝗅𝗒 𝗍𝗈 𝖺 𝗌𝗍𝖺𝗍𝗂𝖼 𝗌𝗍𝗂𝖼𝗄𝖾𝗋 𝗍𝗈 𝖽𝗈𝗐𝗇𝗅𝗈𝖺𝖽 𝗂𝗍 𝖺𝗌 𝖺𝗇 𝗂𝗆𝖺𝗀𝖾.
   ✧ `/𝗀𝖾𝗍𝗏𝗂𝖽𝗌𝗍𝗂𝖼𝗄𝖾𝗋`: 𝖱𝖾𝗉𝗅𝗒 𝗍𝗈 𝖺 𝗏𝗂𝖽𝖾𝗈 𝗌𝗍𝗂𝖼𝗄𝖾𝗋 𝗍𝗈 𝖽𝗈𝗐𝗇𝗅𝗈𝖺𝖽 𝗂𝗍 𝖺𝗌 𝖺𝗇 𝖬𝖯𝟦 𝖿𝗂𝗅𝖾.
   ✧ `/𝗀𝖾𝗍𝗏𝗂𝖽𝖾𝗈`: 𝖱𝖾𝗉𝗅𝗒 𝗍𝗈 𝖺 𝖦𝖨𝖥 𝗍𝗈 𝖽𝗈𝗐𝗇𝗅𝗈𝖺𝖽 𝗂𝗍 𝖺𝗌 𝖺 𝗏𝗂𝖽𝖾𝗈 𝖿𝗂𝗅𝖾.
 
- **𝖬𝖺𝗇𝖺𝗀𝖾 𝖲𝗍𝗂𝖼𝗄𝖾𝗋 𝖯𝖺𝖼𝗄𝗌:**
  ✧ `/𝗇𝖾𝗐𝗉𝖺𝖼𝗄` (𝖯𝖬 𝗈𝗇𝗅𝗒): 𝖢𝗋𝖾𝖺𝗍𝖾 𝖺 𝗇𝖺𝗆𝖾𝖽 𝗉𝖺𝖼𝗄 - 𝖨'𝗅𝗅 𝖺𝗌𝗄 𝖿𝗈𝗋 𝖺 𝗇𝖺𝗆𝖾 𝖺𝗇𝖽 𝖺 𝗌𝗁𝗈𝗋𝗍 𝗅𝗂𝗇𝗄, 𝗍𝗁𝖾𝗇 𝗌𝖾𝗍 𝗂𝗍 𝖺𝗌 𝗒𝗈𝗎𝗋 𝖺𝖼𝗍𝗂𝗏𝖾 𝗉𝖺𝖼𝗄.
   ✧ `/𝗆𝗒𝗉𝖺𝖼𝗄𝗌` 𝗈𝗋 `/𝗉𝖺𝖼𝗄𝗌`: 𝖲𝖾𝖾 𝖺𝗅𝗅 𝗒𝗈𝗎𝗋 𝗉𝖺𝖼𝗄𝗌 𝖺𝗌 𝖻𝗎𝗍𝗍𝗈𝗇𝗌 - 𝗍𝖺𝗉 𝗈𝗇𝖾 𝗍𝗈 𝗆𝖺𝗄𝖾 𝗂𝗍 𝖺𝖼𝗍𝗂𝗏𝖾, 𝗈𝗋 🗑 𝗍𝗈 𝖽𝖾𝗅𝖾𝗍𝖾 𝗂𝗍.
   ✧ `/𝗄𝖺𝗇𝗀`: 𝖠𝖽𝖽 𝖺 𝗌𝗍𝗂𝖼𝗄𝖾𝗋, 𝗉𝗁𝗈𝗍𝗈, 𝗈𝗋 𝖺𝗇𝗂𝗆𝖺𝗍𝗂𝗈𝗇 𝗍𝗈 𝗒𝗈𝗎𝗋 𝗈𝗐𝗇 𝗌𝗍𝗂𝖼𝗄𝖾𝗋 𝗉𝖺𝖼𝗄 - 𝗎𝗌𝖾𝗌 𝗒𝗈𝗎𝗋 𝖺𝖼𝗍𝗂𝗏𝖾 𝗉𝖺𝖼𝗄 (𝗌𝖾𝗍 𝗏𝗂𝖺 /𝗇𝖾𝗐𝗉𝖺𝖼𝗄 𝗈𝗋 /𝗆𝗒𝗉𝖺𝖼𝗄𝗌) 𝖻𝗒 𝖽𝖾𝖿𝖺𝗎𝗅𝗍.
     - `/𝗄𝖺𝗇𝗀 <𝗇𝗎𝗆𝖻𝖾𝗋>` - 𝗍𝖺𝗋𝗀𝖾𝗍 𝖺 𝗅𝖾𝗀𝖺𝖼𝗒 𝗇𝗎𝗆𝖻𝖾𝗋𝖾𝖽 𝗉𝖺𝖼𝗄 𝗂𝗇𝗌𝗍𝖾𝖺𝖽.
     - `/𝗄𝖺𝗇𝗀 #𝗅𝗂𝗇𝗄` - 𝗍𝖺𝗋𝗀𝖾𝗍 𝗈𝗇𝖾 𝗈𝖿 𝗒𝗈𝗎𝗋 𝗇𝖺𝗆𝖾𝖽 𝗉𝖺𝖼𝗄𝗌 𝖽𝗂𝗋𝖾𝖼𝗍𝗅𝗒 𝖻𝗒 𝗂𝗍𝗌 𝗅𝗂𝗇𝗄, 𝗃𝗎𝗌𝗍 𝗈𝗇𝖼𝖾, 𝗐𝗂𝗍𝗁𝗈𝗎𝗍 𝗌𝗐𝗂𝗍𝖼𝗁𝗂𝗇𝗀 𝗒𝗈𝗎𝗋 𝖺𝖼𝗍𝗂𝗏𝖾 𝗉𝖺𝖼𝗄.
     - `/𝗄𝖺𝗇𝗀 😀🔥` - 𝗌𝖾𝗍𝗌 𝗆𝗎𝗅𝗍𝗂𝗉𝗅𝖾 𝖾𝗆𝗈𝗃𝗂𝗌 𝖿𝗈𝗋 𝗍𝗁𝖾 𝗌𝗍𝗂𝖼𝗄𝖾𝗋; 𝗅𝖾𝖺𝗏𝖾 𝗂𝗍 𝗈𝗎𝗍 𝖺𝗇𝖽 𝗍𝗁𝖾 𝗌𝗍𝗂𝖼𝗄𝖾𝗋'𝗌 𝗈𝗐𝗇 𝖾𝗆𝗈𝗃𝗂 (𝗈𝗋 ✔️) 𝗂𝗌 𝗎𝗌𝖾𝖽.
   ✧ `/𝗎𝗇𝗄𝖺𝗇𝗀`: 𝖱𝖾𝗆𝗈𝗏𝖾 𝖺 𝗌𝗍𝗂𝖼𝗄𝖾𝗋 𝖿𝗋𝗈𝗆 𝗒𝗈𝗎𝗋 𝗌𝗍𝗂𝖼𝗄𝖾𝗋 𝗉𝖺𝖼𝗄 (𝗈𝗇𝗅𝗒 𝗐𝗈𝗋𝗄𝗌 𝖿𝗈𝗋 𝗌𝗍𝗂𝖼𝗄𝖾𝗋𝗌 𝗂𝗇 𝗒𝗈𝗎𝗋 𝗈𝗐𝗇 𝗉𝖺𝖼𝗄).
 
- **𝖠𝖽𝖽𝗂𝗍𝗂𝗈𝗇𝖺𝗅 𝖢𝗈𝗆𝗆𝖺𝗇𝖽𝗌:**
  ✧ `/𝗌𝗍𝗂𝖼𝗄𝖾𝗋𝗂𝖽`: 𝖱𝖾𝗉𝗅𝗒 𝗍𝗈 𝖺 𝗌𝗍𝗂𝖼𝗄𝖾𝗋 𝗍𝗈 𝗀𝖾𝗍 𝗂𝗍𝗌 𝖥𝗂𝗅𝖾 𝖨𝖣.
   ✧ `/𝗆𝗆𝖿 <𝗍𝖾𝗑𝗍>` 𝗈𝗋 `/𝗆𝖾𝗆𝗂𝖿𝗒 <𝗍𝖾𝗑𝗍>` *:* 𝖠𝖽𝖽 𝗍𝖾𝗑𝗍 𝗍𝗈 𝗍𝗁𝖾 𝗍𝗈𝗉 𝖺𝗇𝖽/𝗈𝗋 𝖻𝗈𝗍𝗍𝗈𝗆 𝗈𝖿 𝖺 𝗋𝖾𝗉𝗅𝗂𝖾𝖽 𝗌𝗍𝗂𝖼𝗄𝖾𝗋 𝗈𝗋 𝗉𝗁𝗈𝗍𝗈. 𝖴𝗌𝖾 `;` 𝗍𝗈 𝗌𝖾𝗉𝖺𝗋𝖺𝗍𝖾 𝗍𝗈𝗉 𝖺𝗇𝖽 𝖻𝗈𝗍𝗍𝗈𝗆 𝗍𝖾𝗑𝗍.
 
**𝖧𝗈𝗐 𝗍𝗈 𝖴𝗌𝖾:**
  𝟣. 𝖴𝗌𝖾 𝗍𝗁𝖾 𝖼𝗈𝗆𝗆𝖺𝗇𝖽𝗌 𝗐𝗁𝗂𝗅𝖾 𝗋𝖾𝗉𝗅𝗒𝗂𝗇𝗀 𝗍𝗈 𝗍𝗁𝖾 𝗋𝖾𝗅𝖾𝗏𝖺𝗇𝗍 𝗆𝖾𝖽𝗂𝖺 (𝗌𝗍𝗂𝖼𝗄𝖾𝗋, 𝗉𝗁𝗈𝗍𝗈, 𝗈𝗋 𝖺𝗇𝗂𝗆𝖺𝗍𝗂𝗈𝗇).
   𝟤. 𝖥𝗈𝗅𝗅𝗈𝗐 𝗈𝗇-𝗌𝖼𝗋𝖾𝖾𝗇 𝗂𝗇𝗌𝗍𝗋𝗎𝖼𝗍𝗂𝗈𝗇𝗌 𝖿𝗈𝗋 𝖾𝖺𝖼𝗁 𝖼𝗈𝗆𝗆𝖺𝗇𝖽 𝗍𝗈 𝗆𝖺𝗇𝖺𝗀𝖾 𝗒𝗈𝗎𝗋 𝗌𝗍𝗂𝖼𝗄𝖾𝗋𝗌 𝖾𝖿𝖿𝖾𝖼𝗍𝗂𝗏𝖾𝗅𝗒.
   𝟥. 𝖴𝗌𝖾 `/𝗄𝖺𝗇𝗀` 𝗍𝗈 𝗌𝗍𝖺𝗋𝗍 𝖻𝗎𝗂𝗅𝖽𝗂𝗇𝗀 𝗒𝗈𝗎𝗋 𝗉𝖾𝗋𝗌𝗈𝗇𝖺𝗅𝗂𝗓𝖾𝖽 𝗌𝗍𝗂𝖼𝗄𝖾𝗋 𝗉𝖺𝖼𝗄 𝗈𝗋 𝖺𝖽𝖽 𝗍𝗈 𝖺𝗇 𝖾𝗑𝗂𝗌𝗍𝗂𝗇𝗀 𝗈𝗇𝖾.
   𝟦. 𝖱𝖾𝗉𝗅𝗒 𝗍𝗈 𝖺 𝗌𝗍𝗂𝖼𝗄𝖾𝗋 𝗈𝗋 𝗉𝗁𝗈𝗍𝗈 𝗐𝗂𝗍𝗁 `/𝗆𝗆𝖿 <𝗍𝗈𝗉 𝗍𝖾𝗑𝗍>;<𝖻𝗈𝗍𝗍𝗈𝗆 𝗍𝖾𝗑𝗍>` 𝗍𝗈 𝗀𝖾𝗇𝖾𝗋𝖺𝗍𝖾 𝖺 𝗆𝖾𝗆𝖾-𝗌𝗍𝗒𝗅𝖾 𝗂𝗆𝖺𝗀𝖾.
   𝟧. 𝖨𝖿 𝗈𝗇𝗅𝗒 𝗈𝗇𝖾 𝗉𝖺𝗋𝗍 𝗈𝖿 𝗍𝗁𝖾 𝗍𝖾𝗑𝗍 𝗂𝗌 𝗉𝗋𝗈𝗏𝗂𝖽𝖾𝖽, 𝗂𝗍 𝗐𝗂𝗅𝗅 𝖺𝗉𝗉𝖾𝖺𝗋 𝖺𝗍 𝗍𝗁𝖾 𝗍𝗈𝗉.
 
"""