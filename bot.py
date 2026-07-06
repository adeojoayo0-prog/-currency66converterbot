import os
import re
import logging
import aiohttp
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# --- Logging ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Configuration ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
EXCHANGE_API_KEY = os.environ.get("EXCHANGE_API_KEY", "free")  # Get from exchangerate-api.com
EXCHANGE_API_URL = f"https://api.exchangerate-api.com/v4/latest/"

# Supported currencies (for the inline keyboard)
SUPPORTED_CURRENCIES = [
    "USD", "EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "CNY", "INR", "BRL",
    "ZAR", "NZD", "KRW", "SGD", "MXN", "HKD", "RUB", "TRY", "AED", "SAR",
    "NGN", "KES", "GHS", "EGP", "MAD", "DZD", "TND", "LKR", "BDT", "PKR"
]

# --- Helper Functions ---

async def get_exchange_rates(base_currency="USD"):
    """Fetch live exchange rates from the API."""
    url = f"{EXCHANGE_API_URL}{base_currency}"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("rates", {})
                else:
                    logger.error(f"API Error: {response.status}")
                    return None
    except Exception as e:
        logger.error(f"API Request Failed: {e}")
        return None

def format_currency(amount, currency):
    """Format amount with currency symbol."""
    symbols = {
        "USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥", "CHF": "Fr",
        "CNY": "¥", "INR": "₹", "BRL": "R$", "RUB": "₽", "KRW": "₩",
        "TRY": "₺", "NGN": "₦", "AED": "د.إ", "SAR": "﷼", "EGP": "E£"
    }
    symbol = symbols.get(currency, "")
    return f"{symbol}{amount:,.2f}"

def parse_convert_input(text):
    """Parse user input like '100 USD to EUR' or '100 usd in eur'."""
    patterns = [
        r'(\d+\.?\d*)\s*([A-Za-z]{3})\s+(?:to|in|into|->)\s+([A-Za-z]{3})',
        r'(\d+\.?\d*)\s*([A-Za-z]{3})\s*[/=]\s*([A-Za-z]{3})',
        r'convert\s+(\d+\.?\d*)\s*([A-Za-z]{3})\s+(?:to|in|into)\s+([A-Za-z]{3})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            amount = float(match.group(1))
            from_cur = match.group(2).upper()
            to_cur = match.group(3).upper()
            return amount, from_cur, to_cur
    
    return None

async def convert_currency(amount, from_currency, to_currency):
    """Convert currency using the API."""
    rates = await get_exchange_rates(from_currency)
    if not rates:
        return None
    
    if to_currency not in rates:
        return None
    
    rate = rates[to_currency]
    result = amount * rate
    return result, rate

# --- Bot Commands ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a welcome message when the /start command is issued."""
    welcome_text = (
        f"💰 *Welcome to Currency66 Converter Bot!*\n\n"
        f"I can help you convert currencies instantly using live exchange rates.\n\n"
        f"*How to use me:*\n"
        f"• `/convert 100 USD to EUR` - Convert currency\n"
        f"• `/rates USD` - Show exchange rates for a currency\n"
        f"• `/list` - Show supported currencies\n"
        f"• `/help` - Show this help message\n\n"
        f"*Quick Convert:* Just type `100 usd to eur` directly in the chat!\n\n"
        f"*Supported Currencies:* 30+ major currencies including NGN, GHS, KES, and more."
    )
    
    keyboard = [
        [
            InlineKeyboardButton("💱 Convert Now", callback_data="convert"),
            InlineKeyboardButton("📊 View Rates", callback_data="rates")
        ],
        [
            InlineKeyboardButton("📋 Supported Currencies", callback_data="list"),
            InlineKeyboardButton("❓ Help", callback_data="help")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_text,
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a help message."""
    help_text = (
        "❓ *How to use Currency66 Converter Bot*\n\n"
        "*Commands:*\n"
        "• `/start` - Show welcome message\n"
        "• `/convert 100 USD to EUR` - Convert currency\n"
        "• `/rates USD` - Show exchange rates for a base currency\n"
        "• `/list` - Show all supported currencies\n"
        "• `/help` - Show this help\n\n"
        "*Quick Convert:*\n"
        "Just type `100 usd to eur` directly in chat\n"
        "Or `50 eur in gbp`, `25 usd -> ngn`\n\n"
        "*Examples:*\n"
        "• 100 USD to EUR\n"
        "• 5000 NGN in USD\n"
        "• Convert 200 GBP to JPY"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def convert_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /convert command."""
    if not context.args:
        await update.message.reply_text(
            "❌ Please provide the amount and currencies.\n"
            "*Example:* `/convert 100 USD to EUR`",
            parse_mode="Markdown"
        )
        return
    
    try:
        # Handle args like ["100", "USD", "to", "EUR"]
        if len(context.args) >= 4:
            amount = float(context.args[0])
            from_currency = context.args[1].upper()
            to_currency = context.args[3].upper()
        else:
            await update.message.reply_text(
                "❌ Invalid format.\n"
                "*Example:* `/convert 100 USD to EUR`",
                parse_mode="Markdown"
            )
            return
        
        result = await perform_conversion(update, amount, from_currency, to_currency)
        if result:
            await update.message.reply_text(result, parse_mode="Markdown")
            
    except ValueError:
        await update.message.reply_text("❌ Please enter a valid number for the amount.")

async def rates_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show exchange rates for a specific currency."""
    if not context.args:
        await update.message.reply_text(
            "❌ Please specify a currency.\n"
            "*Example:* `/rates USD`",
            parse_mode="Markdown"
        )
        return
    
    base_currency = context.args[0].upper()
    rates = await get_exchange_rates(base_currency)
    
    if not rates:
        await update.message.reply_text(
            f"❌ Could not fetch rates for {base_currency}. Please try again later."
        )
        return
    
    # Show top 10 currencies
    top_currencies = ["USD", "EUR", "GBP", "JPY", "NGN", "INR", "CNY", "CAD", "AUD", "CHF"]
    response = f"📊 *Exchange Rates (Base: {base_currency})*\n\n"
    
    for currency in top_currencies:
        if currency in rates:
            rate = rates[currency]
            response += f"• {currency}: `{rate:.4f}`\n"
    
    response += "\n_Showing top 10 currencies. Use /list to see all._"
    await update.message.reply_text(response, parse_mode="Markdown")

async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all supported currencies."""
    currencies_list = "\n".join([f"• `{c}`" for c in SUPPORTED_CURRENCIES])
    response = f"📋 *Supported Currencies ({len(SUPPORTED_CURRENCIES)} total)*\n\n{currencies_list}"
    await update.message.reply_text(response, parse_mode="Markdown")

async def perform_conversion(update, amount, from_currency, to_currency):
    """Perform currency conversion and return formatted result."""
    # Validate currencies
    if from_currency not in SUPPORTED_CURRENCIES:
        return f"❌ Currency `{from_currency}` is not supported. Use /list to see all."
    if to_currency not in SUPPORTED_CURRENCIES:
        return f"❌ Currency `{to_currency}` is not supported. Use /list to see all."
    
    if from_currency == to_currency:
        return f"💱 {format_currency(amount, from_currency)} = {format_currency(amount, to_currency)} (same currency)"
    
    # Get conversion
    result = await convert_currency(amount, from_currency, to_currency)
    if result is None:
        return "❌ Failed to fetch exchange rates. Please try again later."
    
    converted_amount, rate = result
    response = (
        f"💱 *Currency Conversion*\n\n"
        f"`{format_currency(amount, from_currency)}` = `{format_currency(converted_amount, to_currency)}`\n\n"
        f"📈 *Rate:* 1 {from_currency} = {rate:.4f} {to_currency}\n"
        f"🔄 *Inverse:* 1 {to_currency} = {1/rate:.4f} {from_currency}\n\n"
        f"🕐 *Live Rates* | Powered by ExchangeRate-API"
    )
    return response

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle regular messages for quick conversion."""
    text = update.message.text
    parsed = parse_convert_input(text)
    
    if parsed:
        amount, from_currency, to_currency = parsed
        result = await perform_conversion(update, amount, from_currency, to_currency)
        if result:
            await update.message.reply_text(result, parse_mode="Markdown")
    else:
        # Check if it's just a currency code
        if text.upper().strip() in SUPPORTED_CURRENCIES:
            await rates_command(update, context)
        else:
            await update.message.reply_text(
                "❌ I didn't understand that.\n\n"
                "Try:\n"
                "• `100 USD to EUR`\n"
                "• `/convert 100 USD to EUR`\n"
                "• `/rates USD`\n"
                "• `/list` for supported currencies\n\n"
                "Send /help for more info."
            )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button callbacks."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "convert":
        await query.edit_message_text(
            "💱 *Convert Currency*\n\n"
            "Type your conversion directly in the chat, like:\n"
            "• `100 USD to EUR`\n"
            "• `5000 NGN in USD`\n"
            "• `/convert 200 GBP to JPY`",
            parse_mode="Markdown"
        )
    elif data == "rates":
        await query.edit_message_text(
            "📊 *View Exchange Rates*\n\n"
            "Type `/rates USD` (replace USD with any currency code).\n\n"
            "Or just type a currency code like `USD` in the chat!"
        )
    elif data == "list":
        currencies_list = "\n".join([f"• `{c}`" for c in SUPPORTED_CURRENCIES])
        response = f"📋 *Supported Currencies ({len(SUPPORTED_CURRENCIES)} total)*\n\n{currencies_list}"
        await query.edit_message_text(response, parse_mode="Markdown")
    elif data == "help":
        help_text = (
            "❓ *How to use Currency66 Converter Bot*\n\n"
            "*Commands:*\n"
            "• `/start` - Show welcome message\n"
            "• `/convert 100 USD to EUR` - Convert currency\n"
            "• `/rates USD` - Show exchange rates\n"
            "• `/list` - Show supported currencies\n\n"
            "*Quick Convert:*\n"
            "Just type `100 usd to eur` directly in chat\n"
            "Or `50 eur in gbp`\n\n"
            "*Example:* `100 USD to NGN`"
        )
        await query.edit_message_text(help_text, parse_mode="Markdown")

# --- Main Application ---

async def main():
    """Start the bot."""
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_TOKEN environment variable not set!")
        return
    
    logger.info("Starting Currency66 Converter Bot...")
    
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # Add command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("convert", convert_command))
    app.add_handler(CommandHandler("rates", rates_command))
    app.add_handler(CommandHandler("list", list_command))
    
    # Add callback handler for inline buttons
    app.add_handler(CallbackQueryHandler(button_callback))
    
    # Add message handler for quick conversions
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Start the bot
    logger.info("Bot is polling for updates...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
