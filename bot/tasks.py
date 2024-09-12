from celery import shared_task
from telebot import types

import logging

from IrenBot.celery import app
from .conf import bot

logger = logging.getLogger(__name__)


@app.task(ignore_result=True)
def process_telegram_update(update_data):
    logger.info("Обробка оновлення Telegram")
    update = types.Update.de_json(update_data)
    logger.info(f"Отримане оновлення: {update}")
    bot.process_new_updates([update])
