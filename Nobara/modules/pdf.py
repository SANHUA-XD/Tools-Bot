import os
import time
import asyncio
import html
import aiohttp
import aiofiles
from PIL import Image
from fpdf import FPDF
from PyPDF2 import PdfReader, PdfWriter

from pyrogram import filters, Client
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from pyrogram.enums import ParseMode
from pyrogram import ContinuePropagation

from Nobara import app, log, PDF_INPUT_GROUP
from config import config
from Nobara.decorator.errors import error
from Nobara.decorator.save import save

# ==========================================
# CONSTANTS & CONFIGURATION
# ==========================================
PDF_TEMP_DIR = "downloads/pdf_temp"
FONTS_DIR = "downloads/pdf_fonts"  # separate from Nobara/fonts/ (used by fonts.py/tiny.py) to avoid any interference
os.makedirs(PDF_TEMP_DIR, exist_ok=True)
os.makedirs(FONTS_DIR, exist_ok=True)

# We use Noto Sans as a base Unicode font if available.
DEFAULT_FONT_PATH = os.path.join(FONTS_DIR, "NotoSans-Regular.ttf")

# Dictionary to store active PDF sessions per user
# Structure: { user_id: {"type": "text"|"image", "items": [], "state": "collecting", "main_msg": Message, "pdf_name": "", "password": ""} }
user_sessions = {}

# ==========================================
# CUSTOM PDF CLASS (Clean Layout)
# ==========================================
class CustomPDF(FPDF):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add Unicode Font if exists, otherwise fallback to Arial/Helvetica
        if os.path.exists(DEFAULT_FONT_PATH):
            self.add_font("CustomFont", "", DEFAULT_FONT_PATH, uni=True)
            self.font_family_name = "CustomFont"
        else:
            self.font_family_name = "Helvetica"

    # Header and Footer are intentionally left empty to ensure a clean PDF layout
    def header(self):
        pass

    def footer(self):
        pass


# ==========================================
# ASYNC HELPER FUNCTIONS
# ==========================================
async def encrypt_pdf(input_path: str, output_path: str, password: str):
    """Encrypts a PDF file with a password."""
    try:
        reader = PdfReader(input_path)
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)
        writer.encrypt(password)
        with open(output_path, "wb") as f:
            writer.write(f)
        return True
    except Exception as e:
        log.error(f"PDF Encryption Error: {e}")
        return False

async def text_to_pdf_async(texts: list, output_path: str):
    """Converts a list of text items to a PDF document in a non-blocking thread."""
    def _generate():
        pdf = CustomPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        
        for text in texts:
            pdf.add_page()
            pdf.set_font(pdf.font_family_name, size=12)
            try:
                pdf.multi_cell(0, 8, txt=text)
            except Exception as e:
                log.error(f"PDF MultiCell Error: {e}")
                clean_txt = text.encode('ascii', 'replace').decode('ascii')
                pdf.multi_cell(0, 8, txt=clean_txt)
                
        pdf.output(output_path)

    await asyncio.to_thread(_generate)

async def images_to_pdf_async(image_paths: list, output_path: str):
    """Converts a list of image paths into a single clean PDF document."""
    def _generate():
        pdf = CustomPDF()
        for img_path in image_paths:
            try:
                img = Image.open(img_path)
                # Convert RGBA/Palette to RGB for PDF compatibility
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                    img.save(img_path)
                
                pdf.add_page()
                # Calculate dimensions to fit A4 (210 x 297 mm) keeping aspect ratio
                page_w, page_h = 190, 277
                img_w, img_h = img.size
                ratio = min(page_w / img_w, page_h / img_h)
                new_w, new_h = img_w * ratio, img_h * ratio
                
                # Center the image
                x = 10 + (page_w - new_w) / 2
                y = 10 + (page_h - new_h) / 2
                
                pdf.image(img_path, x=x, y=y, w=new_w, h=new_h)
            except Exception as e:
                log.error(f"Error processing image {img_path}: {e}")
                continue
        pdf.output(output_path)

    await asyncio.to_thread(_generate)


async def merge_pdfs_async(pdf_paths: list, output_path: str):
    """Merges multiple existing PDF files into one, in a non-blocking thread."""
    def _merge():
        writer = PdfWriter()
        for path in pdf_paths:
            reader = PdfReader(path)
            for page in reader.pages:
                writer.add_page(page)
        with open(output_path, "wb") as f:
            writer.write(f)

    await asyncio.to_thread(_merge)


def cleanup_session(user_id):
    """Removes temporary session files and clears queue."""
    if user_id in user_sessions:
        session = user_sessions[user_id]
        if session["type"] in ("image", "merge"):
            for p in session["items"]:
                if os.path.exists(p):
                    try: os.remove(p)
                    except: pass
        del user_sessions[user_id]


async def generate_final_pdf(client: Client, user_id: int):
    """Compiles the final PDF, encrypts if necessary, and uploads."""
    session = user_sessions[user_id]
    main_msg = session["main_msg"]
    pdf_name = session.get("pdf_name", f"Nobara_{int(time.time())}.pdf")
    password = session.get("password", None)
    
    output_path = os.path.join(PDF_TEMP_DIR, pdf_name)
    enc_path = os.path.join(PDF_TEMP_DIR, f"Enc_{pdf_name}")
    final_path = output_path

    try:
        # Generate raw PDF
        if session["type"] == "text":
            await text_to_pdf_async(session["items"], output_path)
        elif session["type"] == "merge":
            await merge_pdfs_async(session["items"], output_path)
        else:
            await images_to_pdf_async(session["items"], output_path)

        if not os.path.exists(output_path):
            raise Exception("PDF generation failed inside rendering thread.")

        # Apply Password if requested
        if password:
            await main_msg.edit_text("🔐 `Applying Password Encryption...`")
            success = await encrypt_pdf(output_path, enc_path, password)
            if success:
                final_path = enc_path

        await main_msg.edit_text("📤 `Uploading Final PDF...`")
        
        # Get Bot Details for Caption
        me = await client.get_me()
        bot_username = me.username if me.username else "Bot"
        
        caption = (
            f"**✅ PDF Generated Successfully!**\n\n"
            f"📄 **Name:** `{pdf_name}`\n"
            f"📚 **{'Merged PDFs' if session['type'] == 'merge' else 'Total Pages'}:** `{len(session['items'])}`\n"
            f"🔒 **Password Protected:** `{'Yes' if password else 'No'}`\n\n"
            f"🤖 **Created by:** @{bot_username}"
        )
        
        await main_msg.reply_document(document=final_path, caption=caption, quote=True)
        await main_msg.delete()
        
    except Exception as e:
        log.error(f"Final PDF Generation Error: {e}")
        await main_msg.edit_text(f"❌ **Error generating PDF:** `{e}`")
    finally:
        cleanup_session(user_id)
        for p in [output_path, enc_path]:
            if os.path.exists(p):
                try: os.remove(p)
                except: pass


# ==========================================
# INTERACTIVE QUEUE HANDLERS
# ==========================================

@app.on_message(filters.command("topdf", prefixes=config.COMMAND_PREFIXES))
@error
@save
async def topdf_cmd(client: Client, message: Message):
    user_id = message.from_user.id
    
    if not message.reply_to_message or not message.reply_to_message.text and not message.reply_to_message.caption:
        return await message.reply_text("❌ Please **reply to a text message** to add it to the PDF queue.")
        
    text = message.reply_to_message.text if message.reply_to_message.text else message.reply_to_message.caption

    # Init or validate session
    if user_id in user_sessions:
        if user_sessions[user_id]["type"] != "text":
            return await message.reply_text("❌ You have an active Image-to-PDF session. Please complete or cancel it first.")
        if user_sessions[user_id]["state"] != "collecting":
            return await message.reply_text("❌ You are in the middle of naming/password process. Complete it first.")
    else:
        user_sessions[user_id] = {"type": "text", "items": [], "state": "collecting"}

    # Add text
    user_sessions[user_id]["items"].append(text)
    count = len(user_sessions[user_id]["items"])

    btns = InlineKeyboardMarkup([
        [InlineKeyboardButton("➖ Remove", callback_data=f"pdf_remove:{user_id}"),
         InlineKeyboardButton("✅ Done", callback_data=f"pdf_done:{user_id}")],
        [InlineKeyboardButton("🚫 Cancel", callback_data=f"pdf_cancel:{user_id}")]
    ])
    
    msg = await message.reply_text(f"📄 **{count}{'st' if count==1 else 'nd' if count==2 else 'rd' if count==3 else 'th'} Message Added!**\nReply to another text message with `/topdf` to add more.", reply_markup=btns)
    user_sessions[user_id]["main_msg"] = msg


@app.on_message(filters.command("img2pdf", prefixes=config.COMMAND_PREFIXES))
@error
@save
async def img2pdf_cmd(client: Client, message: Message):
    user_id = message.from_user.id
    
    if not message.reply_to_message or not message.reply_to_message.photo:
        return await message.reply_text("❌ Please **reply to a photo** (or media group) to add to the PDF queue.")

    # Init or validate session
    if user_id in user_sessions:
        if user_sessions[user_id]["type"] != "image":
            return await message.reply_text("❌ You have an active Text-to-PDF session. Please complete or cancel it first.")
        if user_sessions[user_id]["state"] != "collecting":
            return await message.reply_text("❌ You are in the middle of naming/password process. Complete it first.")
    else:
        user_sessions[user_id] = {"type": "image", "items": [], "state": "collecting"}

    status = await message.reply_text("📥 `Downloading image(s)...`")
    
    photos = []
    if message.reply_to_message.media_group_id:
        media_group = await client.get_media_group(message.chat.id, message.reply_to_message.id)
        photos = [msg for msg in media_group if msg.photo]
    else:
        photos = [message.reply_to_message]

    for msg in photos:
        path = await msg.download(file_name=os.path.join(PDF_TEMP_DIR, f"{user_id}_{int(time.time()*1000)}.jpg"))
        if path:
            user_sessions[user_id]["items"].append(path)

    await status.delete()
    count = len(user_sessions[user_id]["items"])

    btns = InlineKeyboardMarkup([
        [InlineKeyboardButton("➖ Remove", callback_data=f"pdf_remove:{user_id}"),
         InlineKeyboardButton("✅ Done", callback_data=f"pdf_done:{user_id}")],
        [InlineKeyboardButton("🚫 Cancel", callback_data=f"pdf_cancel:{user_id}")]
    ])
    
    msg = await message.reply_text(f"🖼 **{count} Image(s) Added!**\nReply to another photo with `/img2pdf` to add more.", reply_markup=btns)
    user_sessions[user_id]["main_msg"] = msg


@app.on_message(filters.command("pdfmerge", prefixes=config.COMMAND_PREFIXES))
@error
@save
async def pdfmerge_cmd(client: Client, message: Message):
    user_id = message.from_user.id

    if not message.reply_to_message or not message.reply_to_message.document:
        return await message.reply_text("❌ Please **reply to a PDF document** to add it to the merge queue.")

    if not (message.reply_to_message.document.file_name or "").lower().endswith(".pdf"):
        return await message.reply_text("❌ The replied file must be a PDF document.")

    if user_id in user_sessions:
        if user_sessions[user_id]["type"] != "merge":
            return await message.reply_text("❌ You have a different active PDF session. Please complete or cancel it first.")
        if user_sessions[user_id]["state"] != "collecting":
            return await message.reply_text("❌ You are in the middle of naming/password process. Complete it first.")
    else:
        user_sessions[user_id] = {"type": "merge", "items": [], "state": "collecting"}

    status = await message.reply_text("📥 `Downloading PDF...`")
    path = os.path.join(PDF_TEMP_DIR, f"merge_{user_id}_{int(time.time()*1000)}.pdf")
    downloaded = await message.reply_to_message.download(file_name=path)
    await status.delete()

    if not downloaded:
        return await message.reply_text("❌ Couldn't download that PDF. Please try again.")

    user_sessions[user_id]["items"].append(downloaded)
    count = len(user_sessions[user_id]["items"])

    btns = InlineKeyboardMarkup([
        [InlineKeyboardButton("➖ Remove", callback_data=f"pdf_remove:{user_id}"),
         InlineKeyboardButton("✅ Done", callback_data=f"pdf_done:{user_id}")],
        [InlineKeyboardButton("🚫 Cancel", callback_data=f"pdf_cancel:{user_id}")]
    ])

    msg = await message.reply_text(
        f"📎 **{count} PDF{'s' if count != 1 else ''} Queued For Merging!**\n"
        f"(𝖳𝗁𝖾𝗒'𝗅𝗅 𝖻𝖾 𝗆𝖾𝗋𝗀𝖾𝖽 𝗂𝗇 𝗍𝗁𝖾 𝗈𝗋𝖽𝖾𝗋 𝗒𝗈𝗎 𝖺𝖽𝖽𝖾𝖽 𝗍𝗁𝖾𝗆.)\n"
        f"Reply to another PDF with `/pdfmerge` to add more, or hit Done once you have at least 2.",
        reply_markup=btns
    )
    user_sessions[user_id]["main_msg"] = msg


# ==========================================
# CALLBACK HANDLERS
# ==========================================
@app.on_callback_query(filters.regex(r"^pdf_"))
@error
async def pdf_callbacks(client: Client, query: CallbackQuery):
    data = query.data.split(":")
    action = data[0]
    owner_id = int(data[1])
    
    if query.from_user.id != owner_id:
        return await query.answer("❌ This is not your PDF session!", show_alert=True)
        
    if owner_id not in user_sessions:
        return await query.answer("❌ Session expired or already processed.", show_alert=True)
        
    session = user_sessions[owner_id]

    if action == "pdf_remove":
        if not session["items"]:
            return await query.answer("Nothing to remove!", show_alert=True)
            
        removed = session["items"].pop()
        if session["type"] in ("image", "merge") and os.path.exists(removed):
            try: os.remove(removed)
            except: pass
            
        count = len(session["items"])
        if count == 0:
            cleanup_session(owner_id)
            await query.message.edit_text("⚠️ **Session Cancelled:** No items left in the queue.")
        else:
            await query.message.edit_text(
                f"ℹ️ **Item Removed!**\nCurrent total items: {count}",
                reply_markup=query.message.reply_markup
            )
            
    elif action == "pdf_done":
        if not session["items"]:
            return await query.answer("Add at least 1 item first!", show_alert=True)
        if session["type"] == "merge" and len(session["items"]) < 2:
            return await query.answer("Add at least 2 PDFs to merge!", show_alert=True)
            
        session["state"] = "waiting_name"
        session["main_msg"] = query.message
        
        btns = InlineKeyboardMarkup([[InlineKeyboardButton("🚫 Cancel", callback_data=f"pdf_cancel:{owner_id}")]])
        await query.message.edit_text("📝 **Send PDF Name:**\n\nType the desired name for your PDF. (.pdf will be added automatically)", reply_markup=btns)
        
    elif action == "pdf_cancel":
        cleanup_session(owner_id)
        await query.message.edit_text("🚫 **PDF Generation Cancelled.**")
        
    elif action == "pdf_add_pass":
        session["state"] = "waiting_password"
        btns = InlineKeyboardMarkup([[InlineKeyboardButton("🚫 Cancel", callback_data=f"pdf_cancel:{owner_id}")]])
        await query.message.edit_text("🔐 **Send Password:**\n\nType the password you want to lock this PDF with.", reply_markup=btns)
        
    elif action == "pdf_skip_pass":
        session["state"] = "processing"
        await query.message.edit_text("⚙️ `Generating PDF... Please wait.`")
        await generate_final_pdf(client, owner_id)


# ==========================================
# TEXT INPUT LISTENER (For Name & Password)
# ==========================================
@app.on_message(filters.text & ~filters.command(config.COMMAND_PREFIXES), group=PDF_INPUT_GROUP)
@error
async def pdf_input_listener(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id not in user_sessions:
        raise ContinuePropagation
        
    session = user_sessions[user_id]
    state = session.get("state")
    
    if state == "waiting_name":
        # Delete the user's name message for privacy & clean chat
        try: await message.delete()
        except: pass
        
        pdf_name = message.text.strip()
        if not pdf_name.lower().endswith(".pdf"):
            pdf_name += ".pdf"
            
        session["pdf_name"] = pdf_name
        session["state"] = "ask_password"
        
        btns = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔐 Add Password", callback_data=f"pdf_add_pass:{user_id}")],
            [InlineKeyboardButton("⏭ Skip Password", callback_data=f"pdf_skip_pass:{user_id}")],
            [InlineKeyboardButton("🚫 Cancel", callback_data=f"pdf_cancel:{user_id}")]
        ])
        
        await session["main_msg"].edit_text(f"📝 **PDF Name Saved:** `{pdf_name}`\n\nDo you want to protect this PDF with a password?", reply_markup=btns)
        return # Prevent passing to other modules
        
    elif state == "waiting_password":
        # Delete the user's password message immediately for privacy
        try: await message.delete()
        except: pass
        
        session["password"] = message.text.strip()
        session["state"] = "processing"
        
        await session["main_msg"].edit_text("⚙️ `Generating Encrypted PDF... Please wait.`")
        await generate_final_pdf(client, user_id)
        return
        
    raise ContinuePropagation


# ==========================================
# LEGACY PDF PASS HANDLER (Single File)
# ==========================================
@app.on_message(filters.command("pdfpass", prefixes=config.COMMAND_PREFIXES))
@error
@save
async def pdfpass_cmd(client: Client, message: Message):
    """Encrypts a replied PDF document with a password."""
    if not message.reply_to_message or not message.reply_to_message.document:
        return await message.reply_text("❌ Please **reply to a PDF document** with `/pdfpass <password>`.")
    
    if not message.reply_to_message.document.file_name.endswith('.pdf'):
        return await message.reply_text("❌ The replied file must be a PDF document.")
        
    if len(message.command) < 2:
        return await message.reply_text("❌ You must provide a password!\n\n**Usage:** `/pdfpass secret123`")

    password = message.text.split(None, 1)[1]

    # The user's own command message contains the plaintext password - if
    # we're in a group and the bot can delete messages, remove it so it
    # doesn't linger visible in the chat history.
    if message.chat.type.name != "PRIVATE":
        try:
            await message.delete()
        except Exception:
            pass

    status = await message.reply_text("📥 `Downloading PDF for Encryption...`") if message.chat.type.name == "PRIVATE" else await client.send_message(message.chat.id, "📥 `Downloading PDF for Encryption...`")
    
    input_path = os.path.join(PDF_TEMP_DIR, f"in_{int(time.time())}.pdf")
    output_path = os.path.join(PDF_TEMP_DIR, f"Protected_{int(time.time())}.pdf")

    try:
        await message.reply_to_message.download(file_name=input_path)
        
        await status.edit_text("🔐 `Applying AES Encryption...`")
        success = await encrypt_pdf(input_path, output_path, password)
        
        if success:
            me = await client.get_me()
            bot_username = me.username if me.username else "Bot"
            
            await status.edit_text("📤 `Uploading Protected PDF...`")

            caption = (
                f"**🔒 PDF Password Protected!**\n\n"
                f"Password: ||{html.escape(password)}||\n\n"
                f"🤖 **Created by:** @{bot_username}"
            )

            # Privacy: never show the password in a group chat where anyone
            # can see it - the encrypted PDF + password always goes to the
            # requester's DM instead. The group only gets a short notice.
            if message.chat.type.name == "PRIVATE":
                await message.reply_document(document=output_path, caption=caption, quote=True)
            else:
                try:
                    await client.send_document(message.from_user.id, document=output_path, caption=caption)
                    await message.reply_text("✅ **Password-protected PDF sent to your DM** (to keep the password private).")
                except Exception:
                    await message.reply_text(
                        "⚠️ **I couldn't DM you the protected PDF.** Please start a private chat with me first, then try `/pdfpass` again."
                    )
            await status.delete()
        else:
            await status.edit_text("❌ Failed to encrypt the PDF. It might be corrupted or already encrypted.")

    except Exception as e:
        log.error(f"PDF Pass Error: {e}")
        await status.edit_text(f"❌ **Error:** `{e}`")
    finally:
        for p in [input_path, output_path]:
            if os.path.exists(p):
                try: os.remove(p)
                except: pass

__module__ = "𝖯𝖣𝖥"
__help__ = """**PDF Creator Studio**

Generate and manipulate PDF files directly from text or images.

**Interactive Queue Commands:**
✧ `/topdf`: Reply to a text/caption. You can keep replying to multiple messages to queue them up.
✧ `/img2pdf`: Reply to a photo or media group. Queue multiple images before creating the PDF.
✧ `/pdfmerge`: Reply to a PDF document. Queue multiple PDFs (in order) to merge into one file.
*(Follow the interactive buttons after running the command to Set Name, Password, and Render the PDF)*

**Direct Commands:**
✧ `/pdfpass [password]`: Reply to a PDF document to encrypt it with a password.

*Note for Admins:* For proper Unicode (Bangla/Hindi/Arabic) support, place `NotoSans-Regular.ttf` inside the bot's `/fonts` folder.
"""
