"""
Telegram Bot Entry Point
Initializes and runs the Telegram bot with all handlers.
"""
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder

from config import settings
from telegram_bot.handlers import register_handlers

# ── Logging ──────────────────────────────────────────────────────────────────

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main():
    """Initialize and start the Telegram bot."""
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN is not set! Add it to your .env file.")
        return

    if not settings.GROQ_API_KEY:
        logger.warning("GROQ_API_KEY is not set! The bot will fail to process resumes.")

    logger.info("Starting AI Resume Bot...")
    logger.info(f"API Base URL: {settings.API_BASE_URL}")

    # Build the bot application with increased timeouts
    application = (
        ApplicationBuilder()
        .token(settings.TELEGRAM_BOT_TOKEN)
        .connect_timeout(30.0)
        .read_timeout(30.0)
        .write_timeout(30.0)
        .pool_timeout(30.0)
        .build()
    )

    # Register all handlers
    register_handlers(application)

    logger.info("Bot is running! Press Ctrl+C to stop.")

    # Start polling
    application.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES,
        poll_interval=1.0,
    )


if __name__ == "__main__":
    main()
