import os
import threading
import logging
from flask import Flask
from google import genai
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# --- CONFIG ---
# Ensure these are set in Render's Environment Variables
TG_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_KEY = os.getenv("GOOGLE_API_KEY")

# --- AI SETUP ---
# Standard client initialization
client = genai.Client(api_key=GEMINI_KEY)

# --- FLASK SERVER (Health Check for Render/UptimeRobot) ---
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "AI Bot is Online!", 200

def run_web_server():
    # Render binds to this PORT
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host='0.0.0.0', port=port)

# --- BOT LOGIC ---
async def handle_ai_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Ignore empty messages or non-text
    if not update.message or not update.message.text:
        return

    user_text = update.message.text
    
    # Send "typing..." status so user knows it's thinking
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        # Primary attempt with the latest Gemini 3 model
        response = client.models.generate_content(
            model="gemini-3-flash-preview", 
            contents=user_text
        )
        await update.message.reply_text(response.text)
        
    except Exception as e:
        print(f"Primary Model Error: {e}")
        
        # Fallback to the hyper-stable Gemini 2.0 if 3 is not found (404)
        try:
            fallback_response = client.models.generate_content(
                model="gemini-2.0-flash", 
                contents=user_text
            )
            await update.message.reply_text(fallback_response.text)
        except Exception as e2:
            print(f"Fallback Model Error: {e2}")
            await update.message.reply_text("⚠️ API Error: Unable to reach AI models. Check Render logs.")

# --- EXECUTION ---
if __name__ == "__main__":
    # 1. Start Flask in background
    threading.Thread(target=run_web_server, daemon=True).start()
    
    # 2. Start Telegram Bot
    if not TG_TOKEN:
        print("❌ CRITICAL: TELEGRAM_TOKEN missing!")
    else:
        app = Application.builder().token(TG_TOKEN).build()
        
        # This listens to all text. 
        # Remember: Promote to Admin & Disable Privacy Mode in BotFather for groups!
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ai_query))
        
        print("🚀 AI Bot is polling...")
        app.run_polling()
