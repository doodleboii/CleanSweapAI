import logging
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)


BOT_TOKEN = '7996895067:AAEMwpL74LLiqlIBwImLnjjz9Gl8to_b1dU'
CHAT_ID = '1315760644'

# Sample tasks list
tasks = [
    {"task": "Clean lobby", "time": "9:00 AM", "priority": "high"},
    {"task": "Sanitize restrooms", "time": "10:30 AM", "priority": "medium"},
    {"task": "Mop floors", "time": "1:00 PM", "priority": "low"},
]


async def show_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not tasks:
        await update.message.reply_text("No cleaning tasks available.")
        return

    message = "🧹 *Cleaning Tasks:*\n\n"
    for t in tasks:
        message += f"• {t['task']} at {t['time']} (Priority: {t['priority'].capitalize()})\n"
    await update.message.reply_text(message, parse_mode='Markdown')

async def send_cleaning_notification(update: Update, context: ContextTypes.DEFAULT_TYPE):
    
    task = "Test cleaning task"
    time = "2025-05-29 15:00"
    priority = "high"

    message = (
        f"🧹 *New Cleaning Task Scheduled!*\n\n"
        f"🧹 Task: {task}\n"
        f"⏰ Time: {time}\n"
        f"🔔 Priority: {priority.capitalize()}"
    )
    await update.message.reply_text(message, parse_mode='Markdown')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome to CleanSweep AI Bot!\n\n"
        "Use /tasks to see all cleaning tasks.\n"
        "Use /notify to send a test cleaning notification."
    )

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("tasks", show_tasks))
    app.add_handler(CommandHandler("notify", send_cleaning_notification))

    print("Bot started. Press Ctrl+C to stop.")
    app.run_polling()

if __name__ == "__main__":
    main()
