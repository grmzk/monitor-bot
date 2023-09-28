import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from classes.users import set_notification_level
from constants import NOTIFICATION_DESCRIPTIONS, NOTIFICATION_TITLES
from utils import build_menu, delete_calling_message, private_access


@delete_calling_message
@private_access
async def choose_notifications(update: Update, _) -> None:
    button_list = list()
    for notification_level, notification_title in NOTIFICATION_TITLES.items():
        button_list.append(
            InlineKeyboardButton(
                notification_title,
                callback_data=f'notification {notification_level}')
        )
    reply_markup = InlineKeyboardMarkup(build_menu(button_list, n_cols=1))
    await update.message.reply_text(text='ВЫБЕРИТЕ УРОВЕНЬ УВЕДОМЛЕНИЙ:\n',
                                    reply_markup=reply_markup)


@delete_calling_message
async def change_notifications(update: Update,
                               context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.callback_query.message.chat_id
    level = int(update.callback_query.data.split()[-1])
    if set_notification_level(chat_id, level):
        await context.bot.send_message(
            chat_id,
            'Установлен уровень уведомлений:\n'
            f'[{NOTIFICATION_TITLES[level]}]\n\n'
            f'На этом уровне {NOTIFICATION_DESCRIPTIONS[level]}'
        )
        logging.info(f'User with CHAT_ID={chat_id} '
                     f'changed notification to {level}')
        return
    await context.bot.send_message(
        chat_id,
        'Не удалось изменить уровень уведомлений, попробуйте позже'
    )
