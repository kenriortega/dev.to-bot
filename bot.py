import logging
import os
import requests
import json
import sys
from threading import Thread
from dotenv import load_dotenv
# telegram api
from telegram import BotCommand
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters
from telegram.error import (TelegramError, Unauthorized)
from telegram.ext.callbackcontext import CallbackContext
from telegram.update import Update


# INTERVAL_BY_HOURS = 7200  # 2h
INTERVAL_BY_HOURS = 3600  # 1h
# INTERVAL_BY_HOURS = 1800  # 30m
# INTERVAL_BY_HOURS = 900  # 15m
COUNT_PER_PAGE_DEVTO = 10

logdir_path = os.path.dirname(os.path.abspath(__file__))
logfile_path = os.path.join(logdir_path, "logs", "bot.log")

if not os.path.exists(os.path.join(logdir_path, "logs")):
    os.makedirs(os.path.join(logdir_path, "logs"))

logfile_handler = logging.handlers.WatchedFileHandler(
    logfile_path, 'a', 'utf-8')

logger = logging.getLogger(__name__)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s - func:%(funcName)s',
    level=logging.INFO,
    handlers=[logfile_handler],
)
load_dotenv()

__author__ = os.getenv('ADMIN_USER')


def make_request_by_url() -> dict:
    r = requests.get(
        # f"https://dev.to/api/articles?tag={tag}&per_page={COUNT_PER_PAGE_DEVTO}",
        f"https://dev.to/api/articles?per_page={COUNT_PER_PAGE_DEVTO}",
    )
    value = list(map(
        lambda article: {
            # "title": article.get('title'),
            # "description": article.get('description'),
            "url": article.get('url'),
            "published_at": article.get('published_at'),
        }, r.json(),
    ))

    value = {
        "articles": value
    }
    return value


def callback_job(context: CallbackContext):
    try:
        value = make_request_by_url()
        for a in value.get('articles'):
            try:
                context.bot.send_message(
                    chat_id=os.getenv('TELEGRAM_CHANNEL_ID'),
                    text=f"{a.get('published_at')}: \n{a.get('url')}",
                )
            except Unauthorized as un:
                # remove update.message.chat_id from conversation list
                logging.error(
                    f'bot was blocked by the user {un}')

            except TelegramError as te:
                # handle all other telegram related errors
                logging.error(te)
    except Exception as e:
        logging.error(e)


def main():
    updater = Updater(
        token=os.getenv('TELEGRAM_TOKEN'),
        use_context=True,
        request_kwargs={'read_timeout': 60, 'connect_timeout': 70},
    )
    dp = updater.dispatcher
    j = updater.job_queue

    def stop_and_restart():
        """Gracefully stop the Updater and replace the current process with a new one"""
        j.stop()
        updater.stop()
        logger.info('Bot stopped gracefully')
        os.execl(sys.executable, sys.executable, *sys.argv)

    def restart(update, context):
        update.message.reply_text('Bot is restarting...')
        Thread(target=stop_and_restart).start()

    dp.add_handler(CommandHandler(
        'r', restart, filters=Filters.user(username=os.getenv('ADMIN_USER'))))

    # job queue
    j.run_repeating(callback_job, interval=INTERVAL_BY_HOURS, first=0)

    # Start BOT
    updater.start_polling()
    logger.info('Listening humans as %s..' % updater.bot.username)
    updater.idle()
    logger.info('Bot stopped gracefully')


if __name__ == "__main__":
    main()
