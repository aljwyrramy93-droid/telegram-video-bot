
import os
import re
import glob
import asyncio
import tempfile
from urllib.parse import urlparse

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
import yt_dlp

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

PRAYER = """🤲 اللهم إن لنا أحباباً قد مسّهم المرض،
فألبسهم ثوب الصحة والعافية،
واشفهم شفاءً لا يغادر سقماً،
وخفّف عنهم كل ألم، وأرح قلوبهم،
وارزقهم الصحة والعافية يا أرحم الراحمين.

❤️ لا تنسون أحبابكم من الدعاء بالشفاء."""

WELCOME = """أهلاً وسهلاً بك ❤️

📥 بوت تحميل الفيديوهات

أرسل رابط الفيديو وسأقوم بتحميله لك مباشرة.

يدعم:
🎵 TikTok
📸 Instagram
▶️ YouTube

✅ مجاني
✅ بدون اشتراك إجباري بقناة
✅ إرسال الفيديو مباشرة

ارسل الرابط الآن 👇"""

ALLOWED_DOMAINS = (
    "tiktok.com",
    "instagram.com",
    "youtube.com",
    "youtu.be",
)

def valid_url(url):
    try:
        host = (urlparse(url).hostname or "").lower()
        return any(
            host == domain or host.endswith("." + domain)
            for domain in ALLOWED_DOMAINS
        )
    except Exception:
        return False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(WELCOME)


async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    text = message.text or ""

    match = re.search(r"https?://\S+", text)

    if not match:
        await message.reply_text("⚠️ أرسل رابط فيديو صحيح.")
        return

    url = match.group(0).rstrip(".,!?،")

    if not valid_url(url):
        await message.reply_text(
            "❌ الموقع غير مدعوم حالياً.\n"
            "أرسل رابط TikTok أو Instagram أو YouTube."
        )
        return

    status = await message.reply_text(
        "⏳ جاري تحميل الفيديو، انتظر قليلاً..."
    )

    try:
        with tempfile.TemporaryDirectory() as folder:
            options = {
                "outtmpl": os.path.join(folder, "%(id)s.%(ext)s"),
                "format": "best[ext=mp4]/best",
                "merge_output_format": "mp4",
                "max_filesize": 49 * 1024 * 1024,
                "noplaylist": True,
                "quiet": True,
                "no_warnings": True,
                "socket_timeout": 30,
                "retries": 2,
            }

            def download():
                with yt_dlp.YoutubeDL(options) as ydl:
                    ydl.download([url])

            await asyncio.to_thread(download)

            files = [
                f for f in glob.glob(os.path.join(folder, "*"))
                if os.path.isfile(f)
            ]

            if not files:
                raise Exception("لم يتم العثور على ملف الفيديو")

            video = max(files, key=os.path.getsize)

            if os.path.getsize(video) > 49 * 1024 * 1024:
                raise Exception("حجم الفيديو أكبر من الحد المسموح")

            await status.delete()

            with open(video, "rb") as file:
                await message.reply_video(
                    video=file,
                    supports_streaming=True,
                    caption="❤️ تم تحميل الفيديو بنجاح"
                )

            # إرسال الدعاء برسالة منفصلة بعد الفيديو
            await message.reply_text(PRAYER)

    except Exception:
        await status.edit_text(
            "❌ تعذر تحميل الفيديو.\n"
            "تأكد أن الرابط عام ويعمل، وحاول مرة ثانية."
        )


def main():
    if not TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is missing")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, download_video)
    )

    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
