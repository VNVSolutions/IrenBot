# conf.py
import telebot
from django.conf import settings

bot = telebot.TeleBot(settings.BOT_TOKEN, threaded=False)


def set_webhook():
    bot.remove_webhook()
    success = bot.set_webhook(url=settings.WEBHOOK_URL)
    if success:
        print("Вебхук успішно встановлено")
    else:
        print("Не вдалося встановити вебхук")
