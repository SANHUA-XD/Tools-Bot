import requests
from Nobara.helper.handler import register
from telethon import Button

@register(pattern="[/!]ud")
async def ud_(e):
    try:
        text = e.text.split(" ", maxsplit=1)[1]
    except IndexError:
        return await e.reply("𝖯𝗅𝖾𝖺𝗌𝖾 𝖾𝗇𝗍𝖾𝗋 𝗄𝖾𝗒𝗐𝗈𝗋𝖽𝗌 𝗍𝗈 𝗌𝖾𝖺𝗋𝖼𝗁 𝗈𝗇 𝗎𝖽!")

    url = f"https://api.urbandictionary.com/v0/define?term={text}"
    response = requests.get(url)
    results = response.json()

    if results.get("list"):
        definition = results["list"][0].get("definition", "")
        example = results["list"][0].get("example", "")
        definition = definition.replace("[", "").replace("]", "")
        example = example.replace("[", "").replace("]", "")

        reply_txt = f'𝖶𝗈𝗋𝖽: {text}\n\n𝖣𝖾𝖿𝗂𝗇𝗂𝗍𝗂𝗈𝗇:\n{definition}\n\n𝖤𝗑𝖺𝗆𝗉𝗅𝖾:\n{example}'
    else:
        reply_txt = f'𝖶𝗈𝗋𝖽: {text}\n\n𝖱𝖾𝗌𝗎𝗅𝗍𝗌: 𝖲𝗈𝗋𝗋𝗒, 𝖼𝗈𝗎𝗅𝖽 𝗇𝗈𝗍 𝖿𝗂𝗇𝖽 𝖺𝗇𝗒 𝗆𝖺𝗍𝖼𝗁𝗂𝗇𝗀 𝗋𝖾𝗌𝗎𝗅𝗍𝗌!'

    google_search_url = f"https://www.google.com/search?q={text}"
    await e.reply(reply_txt, buttons=Button.url("🔎 𝖦𝗈𝗈𝗀𝗅𝖾 𝗂𝗍!", google_search_url), parse_mode="html")

__module__ = "𝖴𝗋𝖻𝖺𝗇 𝖣𝗂𝖼𝗍𝗂𝗈𝗇𝖺𝗋𝗒"


__help__ = """**𝖴𝗋𝖻𝖺𝗇 𝖣𝗂𝖼𝗍𝗂𝗈𝗇𝖺𝗋𝗒 𝖫𝗈𝗈𝗄𝗎𝗉**

- **𝖢𝗈𝗆𝗆𝖺𝗇𝖽:**
  ✧ `/𝗎𝖽 <𝗐𝗈𝗋𝖽>` **:** 𝖥𝖾𝗍𝖼𝗁 𝗍𝗁𝖾 𝖽𝖾𝖿𝗂𝗇𝗂𝗍𝗂𝗈𝗇 𝖺𝗇𝖽 𝖾𝗑𝖺𝗆𝗉𝗅𝖾 𝗎𝗌𝖺𝗀𝖾 𝗈𝖿 𝖺 𝗐𝗈𝗋𝖽 𝖿𝗋𝗈𝗆 𝖴𝗋𝖻𝖺𝗇 𝖣𝗂𝖼𝗍𝗂𝗈𝗇𝖺𝗋𝗒.
 
- **𝖣𝖾𝗍𝖺𝗂𝗅𝗌:**
  ✧ 𝖲𝖾𝖺𝗋𝖼𝗁𝖾𝗌 𝖿𝗈𝗋 𝗍𝗁𝖾 𝗀𝗂𝗏𝖾𝗇 𝗄𝖾𝗒𝗐𝗈𝗋𝖽 𝗈𝗇 𝖴𝗋𝖻𝖺𝗇 𝖣𝗂𝖼𝗍𝗂𝗈𝗇𝖺𝗋𝗒.
   ✧ 𝖨𝖿 𝗇𝗈 𝗋𝖾𝗌𝗎𝗅𝗍𝗌 𝖺𝗋𝖾 𝖿𝗈𝗎𝗇𝖽, 𝗂𝗍 𝗐𝗂𝗅𝗅 𝗇𝗈𝗍𝗂𝖿𝗒 𝗒𝗈𝗎.
   ✧ 𝖯𝗋𝗈𝗏𝗂𝖽𝖾𝗌 𝖺𝗇 𝗈𝗉𝗍𝗂𝗈𝗇 𝗍𝗈 𝖦𝗈𝗈𝗀𝗅𝖾 𝗍𝗁𝖾 𝗐𝗈𝗋𝖽 𝖿𝗈𝗋 𝗆𝗈𝗋𝖾 𝖼𝗈𝗇𝗍𝖾𝗑𝗍.
 """