# CleanSweep AI

An intelligent cleaning task management system that uses AI to predict and schedule cleaning tasks based on traffic patterns.

## Features

- 🤖 Telegram bot for task notifications
- 📊 AI-powered traffic prediction
- 📅 Smart task scheduling
- 🔔 Real-time notifications
- 📱 User-friendly interface

## Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/CleanSweepAI.git
cd CleanSweepAI
```

2. Create and activate virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
Create a `.env` file with:
```
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

5. Run the application:
```bash
# Start Flask backend
cd backend
python app.py

# In another terminal, start Telegram bot
python telegram_bot.py
```

## Usage

1. Start a chat with the Telegram bot
2. Use the following commands:
   - `/start` - Get welcome message
   - `/help` - Show available commands
   - `/notify` - Send test notification
   - `/tasks` - View current tasks
   - `/predict` - Generate new predictions

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. 