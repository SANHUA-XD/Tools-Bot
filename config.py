class config:

    #Client
    API_ID = 
    API_HASH = ""
    BOT_TOKEN = ""
    BOT_NAME = "Shizuka"
    BOT_USERNAME = "Shizuka_Helper_Robot"
    BOT_ID = 8683179971
    WORKERS = 30
    MAX_MESSAGE_CACHE_SIZE = 100
    MAX_CONCURRENT_TRANSMISSIONS = 10
    
     
    #Git
    GIT_USERNAME = ""
    GIT_URL_WITH_TOKEN = "" 


    #Info
    BOT_VERSION = "x"
    OWNER_ID = 6163647625
    OWNER_USERNAME = "Sourov_Nobita"
    SUPPORT_CHAT = -1002357831293
    SUPPORT_CHAT_USERNAME = "Rare_Bots_Support"
    SUPPORT_CHAT_LINK = "https://t.me/Rare_Bots_Support"
    LOG_CHANNEL = -1004460982649
    ERROR_LOG_CHANNEL = -1004460982649
    DOWNLOAD_LOCATION = "./downloads"
    COMMAND_PREFIXES = ["/" , "!" , "." , "#" , "$" , "%" , "&" , "?"] 
    CMD_STARTERS = "/.!&#%$"
    STATS_IMG_URL = "https://files.catbox.moe/tg9aqb.mp4"
    START_IMG_URL = "https://files.catbox.moe/tg9aqb.mp4"
    HELP_IMG_URL = "https://files.catbox.moe/5vj9jh.mp4"
    ALIVE_IMG_URL = "https://files.catbox.moe/ugd0i7.mp4"

    # Photos shown on the /link deep-link page (random.choice picks one each
    # time). Add as many as you want.
    LINK_PICS = [
        "https://files.catbox.moe/wybrme.jpg",
    ]
    
    
    #Database
    MONGODB_URI = "mongodb+srv://:@cluster0.r4kozye.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0" # Use Local Hosted Or Atlas !!
    DATABASE_NAME = "Shizuka"

    # Separate, dedicated MongoDB just for filters. Filters (especially with
    # media file_ids and buttons) can grow fast and eat into a free-tier
    # cluster's storage/connection limits, so they get their own cluster/db
    # here instead of sharing the main one. Leave FILTER_MONGODB_URI empty
    # ("") to just reuse MONGODB_URI above.
    FILTER_MONGODB_URI = "mongodb+srv://:@cluster0.e4ug2jy.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    FILTER_DATABASE_NAME = "ShizukaFilters"

    #API
    IMGBB_API_KEY = ""  # Get a free key at https://api.imgbb.com/
    TMDB_API_KEY = ""  # https://www.themoviedb.org/settings/api - used for filter genre-tagging

    #Donate (used by /donate in mics.py) - fill in your own wallet addresses
    DONATE_BTC_ADDRESS = ""
    DONATE_USDT_TRC20_ADDRESS = ""
    DONATE_ETH_ADDRESS = ""
    DONATE_BNB_BEP20_ADDRESS = ""
    DONATE_OTHER_METHODS = "Contact the owner directly for other payment methods (PayPal, bKash, Nagad, etc)."
    ARQ_API_KEY = "RLWCED-WZASYO-AWOLTB-ITBWTP-ARQ"
    ARQ_API_URL = "arq.hamker.dev"
    CRICKET_API_URL = "https://sugoi-api.vercel.app/cricket"
    FOOTBALL_API_URL = "https://sugoi-api.vercel.app/football"
    BINGSEARCH_URL = "https://sugoi-api.vercel.app/search"
    NEWS_URL = "https://sugoi-api.vercel.app/news?keyword={}"
    shayri_api_url = "https://hindi-quotes.vercel.app/random"
    BASE_URL = "https://api.waifu.pics"
    Movie_Api = "5d3274c3bb08b4276482436c8444abc0"
    Movie_RAC = "eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiI1ZDMyNzRjM2JiMDhiNDI3NjQ4MjQzNmM4NDQ0YWJjMCIsIm5iZiI6MTczMzIyMjgxMy42OTQwMDAyLCJzdWIiOiI2NzRlZTE5ZDJjZTRjZTdkZDYwOTU2YjAiLCJzY29wZXMiOlsiYXBpX3JlYWQiXSwidmVyc2lvbiI6MX0.aXfQw0_CRrKl2iSJd9tFE1TVbWWVYNgysWkUVlwzyRg"
    Pokedex = "https://sugoi-api.vercel.app/pokemon?name={name_or_id}"
    OPENAI_KEY = "xx" #Get From Open Ai's Website
    LYRICS_GENIUS_TOKEN = ""

    #Multi-AI Provider Failover (used by Nobara/helper/ai_provider.py for
    # /ask and the chatbot module). If a provider fails/rate-limits, the bot
    # automatically tries the next one in this list.
    AI_PROVIDER_PRIORITY = "groq,openrouter,cerebras,gemini,together,huggingface,deepseek"

    GROQ_API_KEY = ""  # https://console.groq.com/keys
    GROQ_MODEL = "llama-3.3-70b-versatile"

    OPENROUTER_API_KEY = ""  # https://openrouter.ai/keys
    # "openrouter/free" auto-picks whatever model is currently free on OpenRouter,
    # avoiding 404s when a specific ":free" model ID gets pulled to paid.
    OPENROUTER_MODEL = "openrouter/free"

    CEREBRAS_API_KEY = ""  # https://cloud.cerebras.ai
    CEREBRAS_MODEL = "llama-3.3-70b"

    GEMINI_API_KEY = ""  # https://aistudio.google.com/apikey
    GEMINI_MODEL = "gemini-2.0-flash"

    TOGETHER_API_KEY = ""  # https://api.together.ai
    TOGETHER_MODEL = "meta-llama/Llama-3.3-70B-Instruct-Turbo"

    HUGGINGFACE_API_KEY = ""  # https://huggingface.co/settings/tokens
    HUGGINGFACE_MODEL = "meta-llama/Llama-3.3-70B-Instruct"

    DEEPSEEK_API_KEY = ""  # https://platform.deepseek.com
    DEEPSEEK_MODEL = "deepseek-chat"

    OPENAI_API_KEY = ""  # optional, paid
    OPENAI_MODEL = "gpt-4o-mini"
