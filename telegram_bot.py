import logging
logging.basicConfig(level=logging.DEBUG)

from telegram import Bot
import asyncio

# Replace 'YOUR_BOT_TOKEN' with your actual Telegram bot token
BOT_TOKEN = '7996895067:AAEMwpL74LLiqlIBwImLnjjz9Gl8to_b1dU'
CHAT_ID = '1315760644'  # chat ID or user ID where you want to send messages

bot = Bot(token=BOT_TOKEN)

async def send_cleaning_notification(task, time, priority):
    message = (
        f"🧹 *New Cleaning Task Scheduled!*\n\n"
        f"🧹 Task: {task}\n"
        f"⏰ Time: {time}\n"
        f"🔔 Priority: {priority.capitalize()}"
    )
    await bot.send_message(chat_id=CHAT_ID, text=message, parse_mode='Markdown')

async def main():
    await send_cleaning_notification("Test cleaning task", "2025-05-29 15:00", "high")
    print("Test notification sent! Check your Telegram.")

if __name__ == "__main__":
    asyncio.run(main())


