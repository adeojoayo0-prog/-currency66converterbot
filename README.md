# Currency66 Converter Bot 💰

A Telegram bot for real-time currency conversion with support for 30+ currencies.

## Features

- ✅ Real-time exchange rates
- ✅ 30+ supported currencies including NGN, GHS, KES
- ✅ Quick conversion: `100 USD to EUR`
- ✅ Inline keyboard interface
- ✅ Exchange rate display
- ✅ Built with python-telegram-bot

## Deployment

This bot is designed to be deployed on Railway via GitHub.

### Environment Variables

- `TELEGRAM_TOKEN`: Your bot token from @BotFather
- `EXCHANGE_API_KEY`: Optional API key (default: "free")

## Local Development

```bash
pip install -r requirements.txt
export TELEGRAM_TOKEN="your_token_here"
python bot.py
