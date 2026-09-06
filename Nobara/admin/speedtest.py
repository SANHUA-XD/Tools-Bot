import speedtest
from pyrogram import filters
from pyrogram.types import Message
from Nobara import app
from config import config 
from Nobara.decorator.errors import error
from Nobara.decorator.save import save


@app.on_message(filters.command(["speedtest" , "spt"] , prefixes=config.COMMAND_PREFIXES) & filters.user(config.OWNER_ID))
@error
@save
async def speedtest_command(client, message: Message):
    a = await message.reply("**🚀 𝖱𝗎𝗇𝗇𝗂𝗇𝗀 𝗌𝗉𝖾𝖾𝖽 𝗍𝖾𝗌𝗍, 𝗉𝗅𝖾𝖺𝗌𝖾 𝗐𝖺𝗂𝗍...**")
    try:
        # Initialize Speedtest
        st = speedtest.Speedtest()

        # Find the best server
        await a.edit_text("🌍 **𝖥𝗂𝗇𝖽𝗂𝗇𝗀 𝗍𝗁𝖾 𝖻𝖾𝗌𝗍 𝗌𝖾𝗋𝗏𝖾𝗋...**")
        st.get_best_server()

        # Run download speed test
        await a.edit_text("📥 **𝖳𝖾𝗌𝗍𝗂𝗇𝗀 𝖽𝗈𝗐𝗇𝗅𝗈𝖺𝖽 𝗌𝗉𝖾𝖾𝖽...**")
        download_speed = st.download() / 1_000_000  # Convert to Mbps

        # Run upload speed test
        await a.edit_text("📤 **𝖳𝖾𝗌𝗍𝗂𝗇𝗀 𝗎𝗉𝗅𝗈𝖺𝖽 𝗌𝗉𝖾𝖾𝖽...**")
        upload_speed = st.upload() / 1_000_000  # Convert to Mbps

        # Calculate ping
        await a.edit_text("📡** 𝖢𝖺𝗅𝖼𝗎𝗅𝖺𝗍𝗂𝗇𝗀 𝗉𝗂𝗇𝗀...**")
        ping = st.results.ping

        # Generate shareable result image
        image_url = st.results.share()
        await a.delete()

        # Prepare results text
        results = (
            f"**📊 𝖲𝗉𝖾𝖾𝖽𝗍𝖾𝗌𝗍 𝖱𝖾𝗌𝗎𝗅𝗍𝗌:**\n\n"
            f"**📥 𝖣𝗈𝗐𝗇𝗅𝗈𝖺𝖽 :** {download_speed:.2f} Mbps\n"
            f"**📤 𝖴𝗉𝗅𝗈𝖺𝖽 :** {upload_speed:.2f} Mbps\n"
            f"**📡 𝖯𝗂𝗇𝗀 :** {ping} ms\n\n"
            f"**🌐 𝖲𝖾𝗋𝗏𝖾𝗋 𝖣𝖾𝗍𝖺𝗂𝗅𝗌 :**\n"
            f"🔹 𝖨𝖲𝖯 : {st.results.client['isp']}\n"
            f"🔹 𝖢𝗈𝗎𝗇𝗍𝗋𝗒 : {st.results.client['country']}\n"
        )

        # Send the results as a photo
        await message.reply_photo(photo=image_url, caption=results)

    except Exception as e:
        await message.reply(f"❌ 𝖥𝖺𝗂𝗅𝖾𝖽 𝗍𝗈 𝗋𝗎𝗇 𝗌𝗉𝖾𝖾𝖽 𝗍𝖾𝗌𝗍")
