import logging
from datetime import datetime, time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# ---------- الإعدادات ----------
TOKEN = "8169559283:AAGRln4XS6jUyT0J4qjJqUTN4Nvy8m0_Axc"  # 👈 حط التوكن الجديد هنا

CHANNEL_ID = -1003494248444  # معرف القناة (البوت لازم يكون أدمن)

# ساعات العمل (12 ظهراً - 11 ليلاً)
WORKING_HOURS_START = time(12, 0)
WORKING_HOURS_END = time(23, 0)

# كلمات محظورة
BANNED_WORDS = [
    "كلب",
    "حيوان",
    "كس",
]

# ---------- تسجيل الأخطاء ----------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# تخزين بيانات المستخدمين (مؤقت)
user_data = {}

# ---------- دوال مساعدة ----------
def is_working_hours():
    now = datetime.now().time()
    return WORKING_HOURS_START <= now <= WORKING_HOURS_END

def contains_banned_words(text: str):
    if not text:
        return False
    text = text.lower()
    return any(word.lower() in text for word in BANNED_WORDS)

# ---------- أوامر ----------
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if user.id not in user_data:
        user_data[user.id] = {
            "name": user.first_name,
            "username": user.username,
            "messages_count": 0,
            "join_date": datetime.now().strftime("%Y-%m-%d"),
        }

    status = "✅ نحن متاحون الآن" if is_working_hours() else "⏰ خارج أوقات العمل"

    text = f"""
👋 *أهلاً {user.first_name}*

مرحباً بك في بوت التواصل مع إدارة المدرسة 🎓

{status}

🕐 ساعات العمل:
من 12 ظهراً إلى 11 ليلاً

اختر نوع رسالتك 👇
"""

    keyboard = [
        [InlineKeyboardButton("❓ سؤال", callback_data="question")],
        [InlineKeyboardButton("🐛 مشكلة", callback_data="problem")],
        [InlineKeyboardButton("💡 اقتراح", callback_data="suggestion")],
        [InlineKeyboardButton("📊 إحصائياتي", callback_data="stats")],
    ]

    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📚 استخدم الأزرار أو أرسل رسالتك مباشرة.\n"
        "نحن نرد خلال ساعات العمل ⏰",
        parse_mode="Markdown",
    )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    data = user_data.get(user.id)

    if not data:
        await update.message.reply_text("لا توجد إحصائيات بعد.")
        return

    await update.message.reply_text(
        f"""
📊 *إحصائياتك*

👤 الاسم: {data['name']}
📅 منذ: {data['join_date']}
📨 الرسائل: {data['messages_count']}
""",
        parse_mode="Markdown",
    )

# ---------- الأزرار ----------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "question":
        context.user_data["category"] = "❓ سؤال"
        await query.edit_message_text("✏️ اكتب سؤالك الآن", parse_mode="Markdown")

    elif query.data == "problem":
        context.user_data["category"] = "🐛 مشكلة"
        await query.edit_message_text("✏️ صف المشكلة بالتفصيل", parse_mode="Markdown")

    elif query.data == "suggestion":
        context.user_data["category"] = "💡 اقتراح"
        await query.edit_message_text("✏️ شاركنا اقتراحك", parse_mode="Markdown")

    elif query.data == "stats":
        await stats_command(update, context)

# ---------- استقبال الرسائل ----------
async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user = update.effective_user

    if not message or not user:
        return

    if user.id not in user_data:
        user_data[user.id] = {
            "name": user.first_name,
            "username": user.username,
            "messages_count": 0,
            "join_date": datetime.now().strftime("%Y-%m-%d"),
        }

    user_data[user.id]["messages_count"] += 1

    text = message.text or message.caption or ""

    if contains_banned_words(text):
        await message.reply_text("⚠️ رسالتك تحتوي على ألفاظ غير مناسبة.")
        return

    category = context.user_data.get("category", "📨 عام")
    status = "داخل الدوام" if is_working_hours() else "خارج الدوام"

    if message.text:
        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=f"""
📩 رسالة جديدة

🏷️ {category}
👤 {user.first_name}
📌 @{user.username}
🆔 {user.id}
⏰ {status}

{text}
""",
            parse_mode="Markdown",
        )

    await message.reply_text("✅ تم إرسال رسالتك بنجاح", parse_mode="Markdown")
    context.user_data.pop("category", None)

# ---------- الأخطاء ----------
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(context.error)

# ---------- main ----------
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(
        MessageHandler(filters.TEXT | filters.PHOTO | filters.DOCUMENT, forward_message)
    )

    app.add_error_handler(error_handler)

    print("🤖 البوت شغال...")
    app.run_polling()

if __name__ == "__main__":
    main()
