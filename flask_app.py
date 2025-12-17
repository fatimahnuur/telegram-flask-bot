from flask import Flask, request
import os
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, filters
from pdf2docx import Converter
from docx import Document
from PyPDF2 import PdfReader
from PIL import Image
import pytesseract

# =========================
# Telegram token
# =========================
TOKEN = os.getenv("BOT_TOKEN")  # Render/Environment variables-da qo'shing

# =========================
# Fayllar /tmp ichida saqlanadi
# =========================
UPLOAD = "/tmp/files"
os.makedirs(UPLOAD, exist_ok=True)

# Tesseract manzili (Linux serverlarda)
pytesseract.pytesseract.tesseract_cmd = r"/usr/bin/tesseract"

# =========================
# Flask app va bot
# =========================
app = Flask(__name__)
bot = Bot(token=TOKEN)
dispatcher = Dispatcher(bot, None, workers=0)

# =========================
# /start command
# =========================
def start(update, context):
    update.message.reply_text(
        "📁 Converter Botga xush kelibsiz!\n"
        "Fayl yuboring (PDF/DOCX/JPG/PNG)."
    )

dispatcher.add_handler(CommandHandler("start", start))

# =========================
# Fayl handler
# =========================
MAX_FILE_SIZE_MB = 5  # Fayl hajmi limit

def file_handler(update, context):
    doc = update.message.document
    if not doc:
        update.message.reply_text("❌ Fayl topilmadi")
        return

    if doc.file_size > MAX_FILE_SIZE_MB * 1024 * 1024:
        update.message.reply_text(f"❌ Fayl juda katta! Maks {MAX_FILE_SIZE_MB} MB")
        return

    ext = doc.file_name.lower()
    file_path = os.path.join(UPLOAD, doc.file_name)
    doc.get_file().download(file_path)

    try:
        if ext.endswith(".pdf"):
            out = file_path.replace(".pdf", ".docx")
            cv = Converter(file_path)
            cv.convert(out)
            cv.close()

        elif ext.endswith(".docx"):
            out = file_path.replace(".docx", ".pdf")
            d = Document(file_path)
            text = "\n".join([p.text for p in d.paragraphs])
            with open(out, "w", encoding="utf-8") as f:
                f.write(text)

        elif ext.endswith((".png", ".jpg", ".jpeg")):
            out = file_path + ".txt"
            img = Image.open(file_path)
            text = pytesseract.image_to_string(img, lang="eng+uzb+rus")
            with open(out, "w", encoding="utf-8") as f:
                f.write(text)
        else:
            update.message.reply_text("❌ Bu formatni bilmayman")
            return

        # Faylni jo'natish
        update.message.reply_document(open(out, "rb"), caption="✅ Tayyor!")
        
        # Temporary fayllarni o'chirish
        os.remove(file_path)
        os.remove(out)

    except Exception as e:
        update.message.reply_text(f"⚠ Xatolik: {e}")

dispatcher.add_handler(MessageHandler(filters.Document.ALL, file_handler))

# =========================
# Webhook route
# =========================
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "OK"

@app.route("/")
def index():
    return "Bot ishlamoqda!"

# =========================
# Flask app run (development)
# =========================
if __name__ == "__main__":
    app.run()
