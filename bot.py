import os
import logging
from threading import Thread
from flask import Flask
from groq import Groq
from gtts import gTTS
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# إعدادات الـ Logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

# جلب التوكنز من ريندر
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

groq_client = Groq(api_key=GROQ_API_KEY)

app = Flask('')
@app.route('/')
def home(): 
    return "English Voice Tutor Bot is Running!"

def run_server():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

# دالة الترحيب
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Welcome to your AI English Voice Tutor! 🇬🇧🎙️\n\n"
        "أنا هنا عشان أطور لغتك ونطقك! تقدر دلوقتي تكلمني بكتابة أو تبعتلي **رسالة صوتية (Voice Note)** "
        "وهسمعك وأصلحلك نطقك وقواعدك، وأرد عليك برقم صوتي تسمعه عشان تدرب على الاستماع والنطق!"
    )

# دالة للحصول على رد الذكاء الاصطناعي
def get_ai_response(user_text):
    chat_completion = groq_client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a friendly English teacher. The user is practicing speaking/listening with you. "
                    "Respond in simple, natural English. "
                    "At the very end of your message, if they made spelling, grammar, or pronounciation mistakes, "
                    "add a short section called '🛠️ Quick Correction:' and explain it briefly."
                )
            },
            {"role": "user", "content": user_text}
        ],
        model="llama-3.3-70b-versatile",
        temperature=0.7,
    )
    return chat_completion.choices[0].message.content

# معالجة الرسائل النصية العادية
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    try:
        reply = get_ai_response(update.message.text)
        await update.message.reply_text(reply)
    except Exception as e:
        logging.error(f"Text error: {e}")
        await update.message.reply_text("Sorry, I had a glitch. Try again!")

# معالجة الرسائل الصوتية (🎙️ السحر هنا)
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # إشارة للبوت إنه بيسجل صوت
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="record_voice")
    
    voice_file_path = "user_voice.ogg"
    converted_mp3_path = "user_voice.mp3"
    reply_audio_path = "ai_reply.mp3"

    try:
        # 1. تحميل ملف الصوت من تليجرام
        new_file = await context.bot.get_file(update.message.voice.file_id)
        await new_file.download_to_drive(voice_file_path)

        # 2. تحويل الصوت لنص باستخدام Groq Whisper API
        with open(voice_file_path, "rb") as audio_file:
            transcription = groq_client.audio.transcriptions.create(
                file=(voice_file_path, audio_file.read()),
                model="whisper-large-v3",
                language="en"
            )
        
        user_text = transcription.text
        logging.info(f"User Said: {user_text}")

        # طمأنة المستخدم باللي قاله وكتابة الرد
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        
        # 3. أخذ الرد من الذكاء الاصطناعي
        ai_reply_text = get_ai_response(user_text)

        # 4. تحويل رد الذكاء الاصطناعي لصوت مسموع (لكنة بريطانية أو أمريكية ناعمة)
        tts = gTTS(text=ai_reply_text, lang='en', tld='co.uk', slow=False)
        tts.save(reply_audio_path)

        # 5. إرسال النص والصوت للمستخدم معاً ليتعلم القراءة والاستماع
        await update.message.reply_text(f"✍️ *You said:* {user_text}\n\n🤖 *Teacher Reply:* {ai_reply_text}", parse_mode="Markdown")
        with open(reply_audio_path, "rb") as audio_to_send:
            await update.message.reply_voice(voice=audio_to_send)

    except Exception as e:
        logging.error(f"Voice processing error: {e}")
        await update.message.reply_text("I couldn't understand the audio clearly, please try speaking again! 🎙️")
    
    # تنظيف الملفات المؤقتة من السيرفر
    for path in [voice_file_path, reply_audio_path]:
        if os.path.exists(path):
            os.remove(path)

def main() -> None:
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(filters.VOICE, handle_voice) # تفعيل استقبال الصوت
    
    Thread(target=run_server, daemon=True).start()
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == '__main__':
    main()
