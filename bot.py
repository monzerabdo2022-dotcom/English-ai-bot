import os
import logging
from threading import Thread
from flask import Flask
from groq import Groq
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# إعدادات الـ Logging لمتابعة الأخطاء
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

# جلب التوكنز من بيئة العمل في Render
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# تشغيل عميل الذكاء الاصطناعي
groq_client = Groq(api_key=GROQ_API_KEY)

# سيرفر الويب لمنع نوم البوت على Render
app = Flask('')
@app.route('/')
def home(): 
    return "English AI Tutor Bot is Running!"

def run_server():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

# دالة الترحيب /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Welcome to your AI English Tutor! 🇬🇧🤖\n\n"
        "أنا هنا عشان أساعدك تطور لغتك الإنجليزية. كلمني بأي جملة أو افتح معايا موضوع، "
        "وهرد عليك بالإنجليزي، ولو عندك أي غلطة في القواعد (Grammar) أو الإملاء (Spelling) هصلحهالك فوراً بأسلوب سهل!"
    )

# دالة معالجة الرسائل والربط بالذكاء الاصطناعي
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_text = update.message.text
    
    # إرسال إشارة للمستخدم إن البوت بيكتب (Typing...)
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        # إرسال الرسالة لـ Groq مع توجيهات صارمة للذكاء الاصطناعي
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a friendly and helpful English teacher for an Arabic speaker. "
                        "The user wants to practice their English with you. "
                        "Your job is to: "
                        "1. Respond to their message in simple, clear English to keep the conversation going. "
                        "2. IMPORTANT: If the user made ANY grammar or spelling mistakes in their message, "
                        "add a short, friendly section at the end of your response under the title '🛠️ Quick Correction:' "
                        "explaining the mistake in English or simple Arabic so they can learn from it. "
                        "If there are no mistakes, just reply normally and encourage them."
                    )
                },
                {
                    "role": "user",
                    "content": user_text
                }
            ],
            model="llama-3.3-70b-versatile", # الموديل الجديد المحدث والمستقر
            temperature=0.7,
        )
        
        ai_response = chat_completion.choices[0].message.content
        await update.message.reply_text(ai_response)

    except Exception as e:
        logging.error(f"Error with Groq API: {e}")
        await update.message.reply_text("Sorry, I encountered a small glitch. Please try again! 🛠️")

def main() -> None:
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # تشغيل السيرفر في الخلفية
    Thread(target=run_server, daemon=True).start()
    print("AI English Bot is running...")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == '__main__':
    main()
