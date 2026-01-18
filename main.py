import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
import os

# ---------------- إعدادات البوت ----------------
# القيم الآن من Environment Variables
TOKEN = os.getenv("BOT_TOKEN")
SUPERVISORS_GROUP_ID = int(os.getenv("SUPERVISORS_GROUP_ID"))
FINAL_CHANNEL_ID = int(os.getenv("FINAL_CHANNEL_ID"))

# ---------------- شتائم ----------------
BANNED_WORDS = [
    "كلبة", "حيوانة", "بقرة", "جموسة", "قحبة",
    "كلب", "منيوك", "معرص", "عرص", "قحبه",
    "كس ام", "كس", "كسم", "شرموطة", "حيوان",
    "مبعوص", "بعص", "باعص", "اخو", "معيرص"
]

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ---------- تخزين بيانات المستخدم ----------
user_data = {}  # يخزن اختيار الطالب: "طالب" أو "طالبة"

# ---------- أوامر البوت ----------
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """اختيار الطالب أو الطالبة"""
    keyboard = [
        [InlineKeyboardButton("طالب", callback_data="role_student")],
        [InlineKeyboardButton("طالبة", callback_data="role_female")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "أهلاً! اختر هل أنت: طالب أم طالبة؟",
        reply_markup=reply_markup
    )

async def role_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_data[query.from_user.id] = query.data  # حفظ اختيار المستخدم

    await query.edit_message_text(
        f"تم اختيارك: {'طالب' if query.data=='role_student' else 'طالبة'}\n"
        "الآن يمكنك إرسال رسالتك في الخاص."
    )

# ---------- دالة التحقق من الشتائم ----------
def contains_banned_words(text):
    text_lower = text.lower()
    for word in BANNED_WORDS:
        if word.lower() in text_lower:
            return True
    return False

# ---------- دالة استقبال الرسائل ----------
async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user_id = update.effective_user.id
    role = user_data.get(user_id, "غير محدد")

    if not message.text:
        await message.reply_text("❌ يرجى إرسال رسالة نصية فقط.")
        return

    # التحقق من الشتائم
    if contains_banned_words(message.text):
        await message.reply_text("❌ رسالتك تحتوي على كلمات غير مناسبة وتم رفضها.")
        return

    # إرسال نسخة للمشرفين مع أزرار الموافقة / الرفض
    keyboard = [
        [
            InlineKeyboardButton("✅ إرسال للقناة", callback_data=f"approve_{user_id}"),
            InlineKeyboardButton("❌ رفض", callback_data=f"reject_{user_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(
        chat_id=SUPERVISORS_GROUP_ID,
        text=f"رسالة جديدة من {role}:\n\n{message.text}",
        reply_markup=reply_markup
    )

    await message.reply_text("✅ تم إرسال رسالتك للمشرفين للمراجعة.")

# ---------- دالة التعامل مع أزرار المشرف ----------
async def supervisor_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    if data.startswith("approve_"):
        user_id = int(data.split("_")[1])
        original_message = query.message.text  # الرسالة كما هي في المجموعة

        # إرسال للقناة
        await context.bot.send_message(
            chat_id=FINAL_CHANNEL_ID,
            text=f"رسالة من {user_data.get(user_id,'غير محدد')}:\n\n{original_message}"
        )

        await query.edit_message_text(
            f"{original_message}\n\n✅ تم الإرسال للقناة."
        )

    elif data.startswith("reject_"):
        original_message = query.message.text
        await query.edit_message_text(
            f"{original_message}\n\n❌ تم رفض الرسالة."
        )

# ---------- الدالة الرئيسية ----------
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CallbackQueryHandler(role_selection, pattern="^role_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, forward_message))
    app.add_handler(CallbackQueryHandler(supervisor_action, pattern="^(approve|reject)_"))

    print("🤖 البوت يعمل الآن...")
    app.run_polling()

if __name__ == "__main__":
    main()
