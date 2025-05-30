import logging
import asyncio
import sys
import requests
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from typing import Optional

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot configuration
BOT_TOKEN = '7996895067:AAEMwpL74LLiqlIBwImLnjjz9Gl8to_b1dU'
CHAT_ID = '1315760644'

# Create a single bot instance for reuse
bot = Bot(token=BOT_TOKEN)

# Sample tasks
tasks = [
    {"task": "Clean lobby", "time": "9:00 AM", "priority": "high"},
    {"task": "Sanitize restrooms", "time": "10:30 AM", "priority": "medium"},
    {"task": "Mop floors", "time": "1:00 PM", "priority": "low"},
]

# ---------------------- ASYNC NOTIFICATION ----------------------

async def send_notification(task: str, time: str, priority: str) -> Optional[bool]:
    """Send a notification about a cleaning task."""
    try:
        message = (
            f"🧹 *New Cleaning Task Scheduled!*\n\n"
            f"🧹 Task: {task}\n"
            f"⏰ Time: {time}\n"
            f"🔔 Priority: {priority.capitalize()}"
        )
        
        result = await bot.send_message(
            chat_id=CHAT_ID,
            text=message,
            parse_mode='Markdown'
        )
        
        logger.info(f"Notification sent successfully! Message ID: {result.message_id}")
        return True
    except Exception as e:
        logger.error(f"Error sending notification: {e}")
        return False

# ---------------------- COMMAND HANDLERS ----------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message."""
    try:
        welcome_message = (
            "🌟 *Welcome to CleanSweep AI Bot!* 🌟\n\n"
            "I'm your intelligent cleaning task assistant.\n\n"
            "*Available Commands:*\n"
            "📋 /tasks - View schedule\n"
            "🔔 /notify - Test notification\n"
            "🔄 /predict - New predictions\n"
            "❓ /help - Show help"
        )
        await update.message.reply_text(welcome_message, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error in /start: {e}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send help message."""
    try:
        help_text = (
            "🔍 *Available Commands:*\n\n"
            "📋 /tasks - View cleaning schedule\n"
            "🔔 /notify - Send test notification\n"
            "🔄 /predict - Generate predictions\n"
            "❓ /help - Show this message"
        )
        await update.message.reply_text(help_text, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error in /help: {e}")

async def show_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show current tasks."""
    try:
        message = "📋 *Current Tasks:*\n\n"
        for t in tasks:
            message += f"• {t['task']} at {t['time']} ({t['priority']})\n"
        await update.message.reply_text(message, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error in /tasks: {e}")

async def send_cleaning_notification(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a test notification."""
    try:
        success = await send_notification(
            "Test Cleaning Task",
            "2025-05-30 15:00:00",
            "high"
        )
        if success:
            await update.message.reply_text("✅ Test notification sent successfully!", parse_mode='Markdown')
        else:
            await update.message.reply_text("❌ Failed to send notification.", parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error in /notify: {e}")
        await update.message.reply_text("❌ Failed to send notification.", parse_mode='Markdown')

async def predict(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate new predictions and send notifications."""
    try:
        await update.message.reply_text(
            "🔄 *Generating Cleaning Predictions*\n\nPlease wait...",
            parse_mode='Markdown'
        )
        
        response = requests.get("http://127.0.0.1:5000/predict-cleaning")
        
        if response.status_code == 200:
            data = response.json()
            
            # Send indoor tasks notifications
            for task in data.get('indoor', []):
                await send_notification(task['task'], task['time'], task['priority'])
                await asyncio.sleep(0.5)  # Reduced delay
            
            # Send road tasks notifications
            for task in data.get('roads', []):
                await send_notification(task['task'], task['time'], task['priority'])
                await asyncio.sleep(0.5)  # Reduced delay
            
            await update.message.reply_text(
                "✅ *Predictions Generated Successfully!*\n\nNotifications sent.",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                "❌ *Prediction Failed*\n\nMake sure the Flask app is running.",
                parse_mode='Markdown'
            )
    except Exception as e:
        logger.error(f"Error in /predict: {e}")
        await update.message.reply_text("❌ Error occurred while predicting.", parse_mode='Markdown')

async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a test message."""
    try:
        await update.message.reply_text(
            "🧹 *Test Message*\n\nThis is a test message to verify the bot is working.",
            parse_mode='Markdown'
        )
        
        await update.message.reply_text(
            "🧹 *New Cleaning Task Scheduled!*\n\n"
            "🧹 Task: Test Cleaning Task\n"
            "⏰ Time: 2025-05-30 15:00:00\n"
            "🔔 Priority: High",
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error in /test: {e}")

# ---------------------- BOT RUNNER ----------------------

async def main():
    """Main function to run the bot."""
    try:
        application = ApplicationBuilder().token(BOT_TOKEN).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("notify", send_cleaning_notification))
        application.add_handler(CommandHandler("tasks", show_tasks))
        application.add_handler(CommandHandler("predict", predict))
        application.add_handler(CommandHandler("test", test))
        
        logger.info("Starting CleanSweep Bot...")
        logger.info("Bot is ready! Try these commands in Telegram:")
        logger.info("- /start - Get welcome message")
        logger.info("- /notify - Send test notification")
        logger.info("- /tasks - View current tasks")
        logger.info("- /help - Show all commands")
        
        # Run the bot
        await application.initialize()
        await application.start()
        await application.run_polling(drop_pending_updates=True)
        
    except Exception as e:
        logger.error(f"Bot failed: {e}")
    finally:
        if 'application' in locals():
            await application.stop()
            await application.shutdown()

# ---------------------- ENTRY POINT ----------------------

if __name__ == '__main__':
    try:
        if sys.platform.startswith('win'):
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(main())
    except Exception as e:
        print(f"Startup failed: {e}")
