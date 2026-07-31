import os

# --- Telegram ---
BOT_TOKEN = os.environ["BOT_TOKEN"]                      # токен нового бота от @BotFather
OWNER_CHAT_ID = int(os.environ["OWNER_CHAT_ID"])         # ваш личный chat_id — куда присылать черновики
CHANNEL_ID = os.environ["CHANNEL_ID"]                     # @beautysupplymoscow или -100xxxxxxxxxx

# --- Webhook (Render) ---
WEBHOOK_HOST = os.environ["WEBHOOK_HOST"]                 # напр. https://bsm-content-bot.onrender.com
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"
PORT = int(os.environ.get("PORT", 10000))

# --- Claude API ---
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")

# --- Расписание автогенерации черновика (МСК) ---
# Список часов через запятую, напр. "11,17" — пришлёт черновик дважды в день
POST_HOURS_MSK = [
    int(h.strip()) for h in os.environ.get("POST_HOURS_MSK", "11,17").split(",") if h.strip()
]
