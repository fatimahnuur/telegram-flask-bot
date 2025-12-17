from flask import Flask, request
import os

from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, filters

from pdf2docx import Converter
from docx import Document
from PIL import Image
import pytesseract

# =========================
# Telegram token
# =========================
TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable topilmadi")

# =========================
# Fayllar /tmp ichida saqlanadi
# =========================
UPLOAD = "/tmp/files"
os.makedirs(UPLOAD, exist_ok=True)

# Tesseract (agar Render’da bo‘lsa)
pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"

# =========================
# Flask app
# =========================
app = Flask(__name__)

# =========================
# Telegram Bot & Dispatcher (Sync)
# =========================
bot = Bot(token=TOKEN)
dp = Dispatcher(bot, None, workers=0, use_context=True)

# =========================
# /start command
# =========================
def start(update, context):
    update.message.reply_text(
        "📁 Converter Botga xush kelibsiz!\n"
        "PDF / DOCX / JPG / PNG fayl yuboring."
    )

dp.add_handler(CommandHandler("start", start))

# =========================
# Fayl handler
# =========================
MAX_FILE_SIZE_MB = 5

def file_handler(update, context):
    doc = update.message.document
    if not doc:
        update.message.reply_text("❌ Fayl topilmadi")
        return

    if doc.file_size > MAX_FILE_SIZE_MB * 1024 * 1024:
        update.message.reply_text(
            f"❌ Fayl juda katta! Maks {MAX_FILE_SIZE_MB} MB"
        )
        return

    file_path = os.path.join(UPLOAD, doc.file_name)
    new_file = bot.get_file(doc.file_id)
    new_file.download(custom_path=file_path)

    ext = doc.file_name.lower()

    try:
        # PDF → DOCX
        if ext.endswith(".pdf"):
            out = file_path.replace(".pdf", ".docx")
            cv = Converter(file_path)
            cv.convert(out)
            cv.close()

        # DOCX → TXT
        elif ext.endswith(".docx"):
            out = file_path.replace(".docx", ".txt")
            d = Document(file_path)
            text = "\n".join(p.text for p in d.paragraphs)
            with open(out, "w", encoding="utf-8") as f:
                f.write(text)

        # IMAGE → TEXT (OCR)
        elif ext.endswith((".png", ".jpg", ".jpeg")):
            out = file_path + ".txt"
            img = Image.open(file_path)
            text = pytesseract.image_to_string(img, lang="eng")
            with open(out, "w", encoding="utf-8") as f:
                f.write(text)

        else:
            update.message.reply_text("❌ Bu format qo‘llab-quvvatlanmaydi")
            return

        update.message.reply_document(
            document=open(out, "rb"),
            caption="✅ Tayyor!"
        )

    except Exception as e:
        update.message.reply_text(f"⚠ Xatolik: {e}")

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
        if "out" in locals() and os.path.exists(out):
            os.remove(out)

dp.add_handler(MessageHandler(filters.Document.ALL, file_handler))

# =========================
# Webhook route
# =========================
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dp.process_update(update)
    return "OK"

@app.route("/")
def index():
    return "Bot ishlamoqda 🚀"

# =========================
# Flask run
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
