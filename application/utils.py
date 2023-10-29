import logging
from datetime import date, datetime, time, timedelta
from typing import List

from telegram import (Bot, InlineKeyboardButton, InlineKeyboardMarkup,
                      ReplyKeyboardRemove, Update)
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from classes.to_delete import ToDelete
from classes.users import User, get_enabled_users


async def send_message(bot: Bot,
                       user: User,
                       message_text: str,
                       reply_markup=None):
    try:
        await bot.send_message(user.chat_id,
                               message_text,
                               reply_markup=reply_markup,
                               parse_mode=ParseMode.HTML)
    except TelegramError as error:
        logging.error('Sending message to '
                      f'<{user.get_full_name()}> ERROR: {error}')
    else:
        logging.info(f'Sending message to <{user.get_full_name()}> SUCCESS')


async def send_message_all(bot: Bot, message_text: str, reply_markup=None):
    users = get_enabled_users()
    for user in users:
        await send_message(bot, user, message_text, reply_markup)


def build_menu(buttons, n_cols,
               header_buttons=None,
               footer_buttons=None):
    menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
    if header_buttons:
        menu.insert(0, [header_buttons])
    if footer_buttons:
        menu.append([footer_buttons])
    return menu


def private_access(coroutine):
    async def coroutine_restrict(update: Update,
                                 context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.message.chat_id
        users = get_enabled_users()
        for user in users:
            if user.chat_id == chat_id:
                return await coroutine(update, context)
        return await update.message.reply_text('[ДОСТУП ЗАКРЫТ]')
    return coroutine_restrict


def delete_calling_message(coroutine):
    async def wrapper(update: Update,
                      context: ContextTypes.DEFAULT_TYPE):
        message = update.message or update.callback_query.message
        await coroutine(update, context)
        await context.bot.delete_message(message.chat_id, message.message_id)
    return wrapper


def get_diary_today() -> date:
    diary_today = date.today()
    if datetime.now().time() < time(hour=8, minute=0):
        diary_today -= timedelta(days=1)
    return diary_today


async def send_message_list(update: Update,
                            message_list: List[str],
                            remove_button_title: str):
    chat_id = update.message.chat_id
    to_delete = ToDelete(chat_id=chat_id)
    button_list = [
        InlineKeyboardButton(
            remove_button_title,
            callback_data=f'delete {to_delete.to_delete_id}')
    ]
    reply_markup = InlineKeyboardMarkup(build_menu(button_list, n_cols=1))
    try:
        for message_text in message_list[:-1]:
            to_delete.add(
                await update.message.reply_text(
                    message_text,
                    reply_markup=ReplyKeyboardRemove(),
                    parse_mode=ParseMode.HTML
                )
            )
        else:
            to_delete.add(
                await update.message.reply_text(
                    message_list[-1],
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.HTML
                )
            )
    except TelegramError as error:
        logging.error('Sending message_list to '
                      f'CHAT_ID={chat_id} ERROR: {error}')
    else:
        logging.info(f'Sending message_list to CHAT_ID={chat_id} SUCCESS')
    to_delete.save()
