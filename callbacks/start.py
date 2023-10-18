import logging
import re

from telegram import (InlineKeyboardButton, InlineKeyboardMarkup,
                      ReplyKeyboardMarkup, ReplyKeyboardRemove, Update)
from telegram.ext import ContextTypes, ConversationHandler

from classes.users import (User, get_admin, get_departments, get_users,
                           insert_user, set_enable)
from constants import DEPARTMENT, FAMILY, NAME, PHONE, SURNAME
from utils import build_menu, send_message

NEW_USERS = dict()


async def start(update: Update, _) -> int:
    chat_id = update.message.chat_id
    users = get_users()
    for user in users:
        if user.chat_id == chat_id:
            await update.message.reply_text(
                f'Здравствуйте, {user.get_full_name()}!'
            )
            return ConversationHandler.END
    await update.message.reply_text('Введите ВАШУ фамилию:')
    return FAMILY


async def start_family(update: Update, _):
    chat_id = update.message.chat_id
    user = update.message.from_user
    message = update.message.text
    pattern = re.compile(r'^[А-Я][А-Яа-я \-]*$')
    if not pattern.match(message):
        await update.message.reply_text(
            'Допускается использование только '
            'букв русского алфавита, дефиса и пробела. '
            'Начинаться фамилия должна с заглавной буквы.\n'
            'Попробуйте ещё раз:'
        )
        return FAMILY
    NEW_USERS[chat_id] = dict()
    NEW_USERS[chat_id]['family'] = message
    NEW_USERS[chat_id]['telegram_full_name'] = user.full_name
    logging.info(f'Somebody <{user.full_name}> with CHAT_ID={chat_id} '
                 f'entered family: {message}')
    await update.message.reply_text('Отлично. Введите своё имя:')
    return NAME


async def start_name(update: Update, _):
    chat_id = update.message.chat_id
    user = update.message.from_user
    message = update.message.text
    pattern = re.compile(r'^[А-Я][А-Яа-я \-]*$')
    if not pattern.match(message):
        await update.message.reply_text(
            'Допускается использование только '
            'букв русского алфавита, дефиса и пробела. '
            'Начинаться имя должно с заглавной буквы.\n'
            'Попробуйте ещё раз:'
        )
        return NAME
    NEW_USERS[chat_id]['name'] = message
    logging.info(f'Somebody <{user.full_name}> with CHAT_ID={chat_id} '
                 f'entered name: {message}')
    await update.message.reply_text('Введите своё отчество:')
    return SURNAME


async def start_surname(update: Update, _):
    chat_id = update.message.chat_id
    user = update.message.from_user
    message = update.message.text
    pattern = re.compile(r'^[А-Я][А-Яа-я \-]*$')
    if not pattern.match(message):
        await update.message.reply_text(
            'Допускается использование только '
            'букв русского алфавита, дефиса и пробела. '
            'Начинаться отчество должно с заглавной буквы.\n'
            'Попробуйте ещё раз:'
        )
        return SURNAME
    NEW_USERS[chat_id]['surname'] = message
    logging.info(f'Somebody <{user.full_name}> with CHAT_ID={chat_id} '
                 f'entered surname: {message}')
    await update.message.reply_text('Введите ваш телефонный номер '
                                    'в формате: +7XXXXXXXXXX')
    return PHONE


async def start_phone(update: Update, _):
    chat_id = update.message.chat_id
    user = update.message.from_user
    message = update.message.text
    pattern = re.compile(r'^\+7\d{10}$')
    if not pattern.match(message):
        await update.message.reply_text(
            'Введите номер телефона в формате: +7XXXXXXXXXX\n'
            'Например: +71234567890\n'
            'Попробуйте ещё раз:'
        )
        return PHONE
    NEW_USERS[chat_id]['phone'] = message
    logging.info(f'Somebody <{user.full_name}> with CHAT_ID={chat_id} '
                 f'entered phone: {message}')
    departments = get_departments()
    button_list = list()
    for department_name in departments.values():
        button_list.append(
            InlineKeyboardButton(department_name)
        )
    reply_markup = ReplyKeyboardMarkup(build_menu(button_list, n_cols=2),
                                       resize_keyboard=True)
    await update.message.reply_text('Выберите ваше отделение:\n',
                                    reply_markup=reply_markup)
    return DEPARTMENT


async def start_department(update: Update,
                           context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user = update.message.from_user
    message = update.message.text
    departments = get_departments()
    if message not in departments.values():
        await update.message.reply_text(
            'Выберите ваше отделение из списка, который ниже:\n'
        )
        return DEPARTMENT
    department_id = list(departments.keys())[list(departments
                                                  .values()).index(message)]
    NEW_USERS[chat_id]['department_id'] = department_id
    logging.info(f'Somebody <{user.full_name}> with CHAT_ID={chat_id} '
                 f'entered department: {message}')
    user_data = NEW_USERS[chat_id]
    user = User(family=user_data['family'],
                name=user_data['name'],
                surname=user_data['surname'],
                department=user_data['department_id'],
                phone=user_data['phone'],
                chat_id=chat_id,
                telegram_full_name=user_data['telegram_full_name'])
    if insert_user(user):
        admin = get_admin()
        button_list = [
            InlineKeyboardButton(
                'Активировать',
                callback_data=f'activate {chat_id}')
        ]
        reply_markup = InlineKeyboardMarkup(build_menu(button_list, n_cols=1))
        await send_message(
            context.bot, admin,
            'ДОБАВИЛСЯ НОВЫЙ ПОЛЬЗОВАТЕЛЬ\n'
            '============================\n'
            f'Ф.И.О.: {user.get_full_name()}\n'
            f'Отделение: {message}\n'
            f'Телефон: {user.phone}\n'
            f'CHAT_ID: {chat_id}\n'
            f'TG Ф.И.О.: {user.telegram_full_name}\n',
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            'Не удалось добавить вашу учетную запись, попробуйте позже '
            'или свяжитесь с администратором.',
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END
    await update.message.reply_text(
        'Отлично, ваши данные направлены администратору.\n'
        'Когда ваша учетная запись будет активирована, придёт уведомление.\n\n'
        'Если вы заранее не договаривались, то попросите того, '
        'кто знаком с администратором, отправить сообщение с вашей фамилией '
        '(это во избежание добавления совсем посторонних людей)',
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


async def activate_user(update: Update,
                        context: ContextTypes.DEFAULT_TYPE) -> None:
    user_chat_id = int(update.callback_query.data.split()[-1])
    chat_id = update.callback_query.message.chat_id
    if set_enable(user_chat_id):
        await context.bot.send_message(
            chat_id,
            f'Пользователь с CHAT_ID={user_chat_id} АКТИВИРОВАН'
        )
        await context.bot.send_message(
            user_chat_id,
            '[ВАША УЧЕТНАЯ ЗАПИСЬ АКТИВИРОВАНА]\n\n'
            'Настроить специальный звук для уведомлений '
            'или включить/выключить звуковые оповещения можно в настройках, '
            'которые обычно расположены '
            'в верхней части экрана справа (три вертикальные точки).\n\n'
            'Также обратите внимание на [МЕНЮ], '
            'которое расположено в нижней части экрана слева.'
        )
        return
    await context.bot.send_message(
        chat_id,
        f'Ошибка активации пользователя с CHAT_ID={user_chat_id}'
    )
