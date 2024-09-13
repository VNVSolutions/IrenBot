import logging
import telebot
import string
import os
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from telebot.types import InputMediaPhoto
from telebot import types
from django.utils import timezone
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.core.files import File
from django.dispatch import receiver
from django.db.models import Q
from django.db.models.signals import post_save
from datetime import datetime
from itertools import zip_longest
from .tasks import process_telegram_update
from .conf import bot
from .models import UserProfile
from .models import Categories
from .models import Products
from .models import ProductVariations
from .models import ImageForMain
from .models import BackendHall
from .models import OrderBackendHall
from .models import Basket
from .models import AboutUs
from .models import Contacts


logger = logging.getLogger(__name__)

user_context = {}


@csrf_exempt
def telegram_webhook(request):
    if request.method == 'POST':
        try:
            update_data = request.body.decode('utf-8')
            process_telegram_update.delay(update_data)
            logger.info(f"Отримане оновлення з webhook: {update_data}")
            return HttpResponse('')
        except Exception as e:
            logger.error(f"Помилка обробки вебхуку: {str(e)}")


@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    first_name = message.chat.first_name
    username = message.chat.username
    try:
        user, created = UserProfile.objects.get_or_create(telegram_id=chat_id, defaults={'username': first_name, 'name': username})
        clear_user_context(chat_id)
        bot.send_message(chat_id, "Оберіть дію 👇", reply_markup=create_reply_markup())
    except Exception as e:
        bot.send_message(chat_id, f"Помилка: {str(e)}")


def clear_user_context(chat_id):
    if chat_id in user_context:
        del user_context[chat_id]


def create_reply_markup():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(KeyboardButton('Зарезервувати зал'), KeyboardButton('Замовити їжу'))
    markup.add(KeyboardButton('Корзина'), KeyboardButton('Про нас'))
    markup.add(KeyboardButton('Контакти'))
    return markup


@bot.message_handler(func=lambda message: message.text == 'Назад ⬅')
def go_back(message):
    chat_id = message.chat.id
    clear_user_context(chat_id)
    bot.send_message(chat_id, "Оберіть дію 👇", reply_markup=create_reply_markup())


@bot.message_handler(func=lambda message: message.text == 'Зарезервувати зал')
def reserve_hall(message):
    chat_id = message.chat.id
    halls = BackendHall.objects.all()

    if halls.exists():
        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)

        for hall in halls:
            markup.add(KeyboardButton(hall.name))

        markup.add(KeyboardButton('Назад ⬅'))
        bot.send_message(chat_id, "Оберіть зал для резервації 🏯", reply_markup=markup)
    else:
        bot.send_message(chat_id, "Немає доступних залів для резервації.")


@bot.message_handler(func=lambda message: message.text in [hall.name for hall in BackendHall.objects.all()])
def show_hall_details(message):
    chat_id = message.chat.id
    selected_hall_name = message.text

    try:
        hall = BackendHall.objects.get(name=selected_hall_name)

        if chat_id in user_context:
            user_context[chat_id]['hall'] = hall.name
            user_context[chat_id]['step'] = 'reserve_hall'
        else:
            user_context[chat_id] = {'hall': hall.name, 'step': 'reserve_hall'}

        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(KeyboardButton('Зарезервувати'))
        markup.add(KeyboardButton('Назад ⬅'))

        caption = f"Зал: {hall.name}\nРозмір: {hall.size}"

        if hall.img:
            with open(hall.img.path, 'rb') as image:
                bot.send_photo(chat_id, image, caption=caption, reply_markup=markup)
        else:
            bot.send_message(chat_id, f"{caption}\nЗображення залу відсутнє.", reply_markup=markup)

    except BackendHall.DoesNotExist:
        bot.send_message(chat_id, "Зал не знайдений.")


@bot.message_handler(func=lambda message: message.text == 'Зарезервувати')
def ask_for_contact_details(message):
    chat_id = message.chat.id

    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(KeyboardButton('Поділитись контактом', request_contact=True))
    markup.add(KeyboardButton('Ввести самостійно контакт'))

    user_context[chat_id]['step'] = 'reserve_hall'

    bot.send_message(chat_id, "Вкажіть свої контактні дані 📱", reply_markup=markup)


@bot.message_handler(func=lambda message: message.text == 'Ввести самостійно контакт')
def request_manual_contact(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "Будь ласка, введіть свій контактний номер:")

    if chat_id in user_context and user_context[chat_id].get('step') == 'order_food':
        bot.register_next_step_handler(message, save_manual_contact_order_food)
    elif chat_id in user_context and user_context[chat_id].get('step') == 'reserve_hall':
        bot.register_next_step_handler(message, save_manual_contact_reserve_hall)

def save_manual_contact_order_food(message):
    chat_id = message.chat.id
    contact = message.text

    user_context[chat_id]['contact'] = contact

    process_order(chat_id)

def save_manual_contact_reserve_hall(message):
    chat_id = message.chat.id
    contact = message.text

    try:
        user = UserProfile.objects.get(telegram_id=chat_id)

        if "step" in user_context.get(chat_id, {}) and user_context[chat_id]["step"] == "reserve_hall":
            selected_hall_name = user_context[chat_id]['hall']
            hall = BackendHall.objects.get(name=selected_hall_name)

            OrderBackendHall.objects.create(user=user, hall=hall, contact=contact)

            send_order(chat_id, selected_hall_name, contact)

        else:
            bot.send_message(chat_id, "Помилка: ви не вибрали зал для резервації.")

    except UserProfile.DoesNotExist:
        bot.send_message(chat_id, "Помилка: користувач не знайдений.")
    except BackendHall.DoesNotExist:
        bot.send_message(chat_id, "Помилка: зал не знайдений.")
    except Exception as e:
        bot.send_message(chat_id, f"Сталася помилка: {str(e)}")


def send_order(chat_id, hall_name, contact_info):
    try:
        user = UserProfile.objects.get(telegram_id=chat_id)
        hall = BackendHall.objects.get(name=hall_name)

        caption = f"❗ Нове замовлення ❗\n"
        caption += f"👤 Користувач: {user.username}\n🤖 ID: {user.telegram_id}\n"
        caption += f"🏛 Зал: {hall.name}\n"
        caption += f"📱 Контакт: {contact_info}\n"

        channel_id = -1002297718612
        bot.send_message(channel_id, caption)

        bot.send_message(chat_id, 'Дякую, найближчим часом ми зв\'яжемось з Вами!')
        clear_user_context(chat_id)
        bot.send_message(chat_id, "Оберіть дію 👇", reply_markup=create_reply_markup())
    except Exception as e:
        bot.send_message(chat_id, f"При відправці виникла помилка, спробуйте ще раз: {str(e)}")


@bot.message_handler(func=lambda message: message.text == 'Замовити їжу')
def show_categories(message):
    chat_id = message.chat.id
    categories = Categories.objects.filter(is_active=True)

    if categories.exists():
        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)

        markup.add(KeyboardButton('📖 Відкрити меню 📖'))

        category_buttons = [KeyboardButton(f"{category.smile} {category.categories_name}") for category in categories]
        markup.add(*category_buttons)

        bot.send_message(chat_id, "Оберіть категорію 🍽", reply_markup=markup)
    else:
        bot.send_message(chat_id, "Немає доступних категорій.")


@bot.message_handler(func=lambda message: any(message.text.endswith(category.categories_name) for category in Categories.objects.filter(is_active=True)))
def show_products_details(message):
    chat_id = message.chat.id
    selected_category_name = message.text.split(' ', 1)[-1]

    try:
        category = Categories.objects.get(categories_name=selected_category_name)
        products = Products.objects.filter(categories=category)

        if products.exists():
            markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)

            markup.add(KeyboardButton('📖 Відкрити меню 📖'))

            product_buttons = [KeyboardButton(f"{product.smile} {product.name}") for product in products]
            markup.add(*product_buttons)

            bot.send_message(chat_id, "Оберіть продукт 🍮", reply_markup=markup)
        else:
            bot.send_message(chat_id, "Немає доступних продуктів у цій категорії.", reply_markup=create_reply_markup())

    except Categories.DoesNotExist:
        bot.send_message(chat_id, "Категорія не знайдена.")


@bot.message_handler(func=lambda message: any(message.text.endswith(product.name) for product in Products.objects.all()))
def show_product_details(message):
    chat_id = message.chat.id
    selected_product_name = message.text.split(' ', 1)[-1]

    try:
        product = Products.objects.get(name=selected_product_name)

        if chat_id in user_context:
            user_context[chat_id]['product'] = product.name
            user_context[chat_id]['step'] = 'order_product'
            user_context[chat_id]['product_id'] = product.id
        else:
            user_context[chat_id] = {'product': product.name, 'step': 'order_product', 'product_id': product.id}

        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(KeyboardButton('Додати у корзину 🛒'))
        markup.add(KeyboardButton('Назад ⬅'))

        caption = f"🍽 Продукт: {product.name}\n💵 Ціна: {product.price} грн\n📝 Інгредієнти: {product.ingredients or 'Немає інформації'}"

        if product.image_products:
            with open(product.image_products.path, 'rb') as image:
                bot.send_photo(chat_id, image, caption=caption, reply_markup=markup)
        else:
            bot.send_message(chat_id, f"{caption}\nЗображення продукту відсутнє.", reply_markup=markup)

    except Products.DoesNotExist:
        bot.send_message(chat_id, "Продукт не знайдений.")



@bot.message_handler(func=lambda message: message.text == 'Додати у корзину 🛒')
def ask_for_quantity(message):
    chat_id = message.chat.id

    if chat_id in user_context and user_context[chat_id].get('step') == 'order_product':
        bot.send_message(chat_id, "Введіть кількість товару:")
        bot.register_next_step_handler(message, save_to_basket)
    else:
        bot.send_message(chat_id, "Помилка: товар не вибраний.")


def save_to_basket(message):
    chat_id = message.chat.id
    amount = message.text

    try:
        user = UserProfile.objects.get(telegram_id=chat_id)

        if 'product_id' in user_context[chat_id]:
            product = Products.objects.get(id=user_context[chat_id]['product_id'])

            Basket.objects.create(user=user, products=product, amount=int(amount))

            show_basket_summary(chat_id)

            show_categories(message)
        else:
            bot.send_message(chat_id, "Помилка: товар не знайдений.")

    except ValueError:
        bot.send_message(chat_id, "Будь ласка, введіть правильну кількість.")
        bot.register_next_step_handler(message, save_to_basket)
    except Exception as e:
        bot.send_message(chat_id, f"Сталася помилка: {str(e)}")


def show_basket_summary(chat_id):
    try:
        user = UserProfile.objects.get(telegram_id=chat_id)
        basket_items = Basket.objects.filter(user=user)

        if basket_items.exists():
            total_amount = 0
            summary = "✅ Страва додана до кошика\n"

            for item in basket_items:
                product = item.products
                amount = item.amount
                price = product.price * amount
                total_amount += price

            bot.send_message(chat_id, summary)
        else:
            bot.send_message(chat_id, "Ваш кошик порожній.")
    except Exception as e:
        bot.send_message(chat_id, f"Сталася помилка при відображенні кошика: {str(e)}")


@bot.message_handler(func=lambda message: message.text == 'Корзина')
def show_basket(message):
    chat_id = message.chat.id
    try:
        user = UserProfile.objects.get(telegram_id=chat_id)
        basket_items = Basket.objects.filter(user=user)

        if not basket_items.exists():
            bot.send_message(chat_id, "Ваша корзина порожня ❎")
            return

        total_price = 0
        order_details = "Ваше замовлення:\n\n"

        for item in basket_items:
            item_total = item.products.price * item.amount
            total_price += item_total
            order_details += f"📌 {item.products.name} - {item.products.price}грн x {item.amount} = {item_total}грн\n"

        order_details += f"\n💰 До сплати : {total_price}грн"

        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(KeyboardButton('Замовити ✅'), KeyboardButton('Очистити ❌'))
        markup.add(KeyboardButton('📖 Відкрити меню 📖'))

        bot.send_message(chat_id, order_details, reply_markup=markup)

    except UserProfile.DoesNotExist:
        bot.send_message(chat_id, "Ваша корзина порожня ❎")


@bot.message_handler(func=lambda message: message.text == 'Замовити ✅')
def ask_for_contact_info(message):
    chat_id = message.chat.id
    try:
        user = UserProfile.objects.get(telegram_id=chat_id)
        basket_items = Basket.objects.filter(user=user)

        if not basket_items.exists():
            bot.send_message(chat_id, "Ваша корзина порожня ❎")
            return

        if chat_id not in user_context:
            user_context[chat_id] = {}

        user_context[chat_id]['step'] = 'order_food'

        markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(KeyboardButton('Поділитись контактом', request_contact=True))
        markup.add(KeyboardButton('Ввести самостійно контакт'))
        bot.send_message(chat_id, "Вкажіть свої контактні дані:", reply_markup=markup)

    except UserProfile.DoesNotExist:
        bot.send_message(chat_id, "Помилка. Не вдалося знайти користувача.")


@bot.message_handler(content_types=['contact'])
def handle_contact_info(message):
    chat_id = message.chat.id

    if chat_id in user_context and user_context[chat_id].get('step') == 'order_food':
        if message.contact:
            contact = message.contact.phone_number
        else:
            contact = message.text

        user_context[chat_id]['contact'] = contact

        process_order(chat_id)

    elif chat_id in user_context and user_context[chat_id].get('step') == 'reserve_hall':
        if message.contact:
            contact = message.contact.phone_number
        else:
            contact = message.text

        user_context[chat_id]['contact'] = contact

        send_order(chat_id, user_context[chat_id].get('hall'), contact)
    else:
        bot.send_message(chat_id, "Помилка: неочікуваний формат даних.")


def process_order(chat_id):
    try:
        user = UserProfile.objects.get(telegram_id=chat_id)
        basket_items = Basket.objects.filter(user=user)

        if not basket_items.exists():
            bot.send_message(chat_id, "Ваша корзина порожня ❎")
            return

        contact = user_context[chat_id].get('contact', 'Контакт не вказаний')

        order_details = "❗ Нове замовлення ❗\n"
        order_details += f"👤 Користувач: {user.username}\n🤖 ID: {user.telegram_id}\n"
        order_details += f"📞 Контакт: {contact}\n"

        total_price = 0

        for item in basket_items:
            item_total = item.products.price * item.amount
            total_price += item_total
            order_details += f"📌 {item.products.name} - {item.products.price}грн x {item.amount} = {item_total}грн\n"

        order_details += f"\n💰 До сплати : {total_price}грн"

        channel_id = -1002297718612
        bot.send_message(channel_id, order_details)

        basket_items.delete()

        bot.send_message(chat_id, "Дякуємо за замовлення! Ми з вами зв'яжемось найближчим часом.")
        clear_user_context(chat_id)
        bot.send_message(chat_id, "Оберіть дію 👇", reply_markup=create_reply_markup())
    except UserProfile.DoesNotExist:
        bot.send_message(chat_id, "Помилка. Не вдалося знайти користувача.")


@bot.message_handler(func=lambda message: message.text == 'Очистити ❌')
def clear_basket(message):
    chat_id = message.chat.id
    try:
        user = UserProfile.objects.get(telegram_id=chat_id)
        basket_items = Basket.objects.filter(user=user)

        if not basket_items.exists():
            bot.send_message(chat_id, "Ваша корзина порожня ❎")
            return

        markup = InlineKeyboardMarkup(row_width=1)
        for item in basket_items:
            button = InlineKeyboardButton(text=f"{item.products.name} - Видалити", callback_data=f"delete_{item.id}")
            markup.add(button)

        bot.send_message(chat_id, "Оберіть товар для видалення:", reply_markup=markup)

    except UserProfile.DoesNotExist:
        bot.send_message(chat_id, "Помилка. Не вдалося знайти користувача.")


@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_'))
def delete_item_from_basket(call):
    chat_id = call.message.chat.id
    item_id = call.data.split('_')[1]

    try:
        basket_item = Basket.objects.get(id=item_id)
        basket_item.delete()

        bot.answer_callback_query(call.id, text="Товар успішно видалено.")
        bot.delete_message(chat_id, call.message.message_id)

        remaining_items = Basket.objects.filter(user=basket_item.user)
        if remaining_items.exists():
            update_basket_summary(chat_id)
        else:
            bot.send_message(chat_id, "Ваша корзина порожня ❎")

    except Basket.DoesNotExist:
        bot.send_message(chat_id, "Помилка. Товар не знайдено.")


def update_basket_summary(chat_id):
    try:
        user = UserProfile.objects.get(telegram_id=chat_id)
        basket_items = Basket.objects.filter(user=user)

        if basket_items.exists():
            total_amount = 0
            summary = "Ваше замовлення:\n\n"

            for item in basket_items:
                product = item.products
                amount = item.amount
                price = product.price * amount
                total_amount += price

                summary += f"📌 {product.name} - {product.price}грн x {amount} = {price}грн\n"

            summary += f"\n💰 До сплати: {total_amount}грн"
            bot.send_message(chat_id, summary)
        else:
            bot.send_message(chat_id, "Ваш кошик порожній ❎")
    except Exception as e:
        bot.send_message(chat_id, f"Сталася помилка при оновленні кошика: {str(e)}")


@bot.message_handler(func=lambda message: message.text == '📖 Відкрити меню 📖')
def open_main_menu(message):
    chat_id = message.chat.id
    start(message)


@bot.message_handler(func=lambda message: message.text == 'Про нас')
def about_us(message):
    chat_id = message.chat.id

    try:
        about_info = AboutUs.objects.first()

        if about_info:
            caption = f"ℹ️ Про нас:\n\n{about_info.text}"

            markup = ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add(KeyboardButton('Назад ⬅'))

            if about_info.image_products:
                with open(about_info.image_products.path, 'rb') as image:
                    bot.send_photo(chat_id, image, caption=caption, reply_markup=markup)
            else:
                bot.send_message(chat_id, caption, reply_markup=markup)
        else:
            bot.send_message(chat_id, "Інформація про нас відсутня.")
    except Exception as e:
        bot.send_message(chat_id, f"Сталася помилка при отриманні інформації: {str(e)}")


@bot.message_handler(func=lambda message: message.text == 'Контакти')
def show_contacts(message):
    chat_id = message.chat.id

    try:
        contact_info = Contacts.objects.first()

        if contact_info and contact_info.text:
            markup = ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add(KeyboardButton('Назад ⬅'))

            bot.send_message(chat_id, f"📞 Контакти:\n\n{contact_info.text}", reply_markup=markup)
        else:
            bot.send_message(chat_id, "Інформація про контакти відсутня.")
    except Exception as e:
        bot.send_message(chat_id, f"Сталася помилка при отриманні контактної інформації: {str(e)}")
