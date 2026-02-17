import os
import threading
from flask import Flask
from google import genai
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# --- CONFIG ---
# These will be set in Render's Environment Variables
TG_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_KEY = os.getenv("GOOGLE_API_KEY")

# --- AI SETUP ---
client = genai.Client(api_key=GEMINI_KEY)

# --- FLASK SERVER (Keep-Alive for Render) ---
web_app = Flask(__name__)

@web_app.route('/')
def health_check():
    return "AI Assistant is Online!", 200

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host='0.0.0.0', port=port)

# --- BOT LOGIC ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    user_text = update.message.text
    
    # Show "typing..." action in Telegram
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        # Generate AI response
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=user_text
        )
        
        # Reply to user
        await update.message.reply_text(response.text)
        
    except Exception as e:
        print(f"Error: {e}")
        await update.message.reply_text("⚠️ My brain is a bit foggy. Can you try asking that again?")

# --- MAIN ---
if __name__ == "__main__":
    # 1. Start Flask health-check server in background
    threading.Thread(target=run_web_server, daemon=True).start()
    
    # 2. Start Telegram Bot
    if not TG_TOKEN:
        print("❌ Error: TELEGRAM_TOKEN not found in environment variables.")
    else:
        app = Application.builder().token(TG_TOKEN).build()
        # Responds to all text messages (Privacy Mode must be disabled for groups)
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        print("🚀 AI Bot is starting...")
        app.run_polling()
