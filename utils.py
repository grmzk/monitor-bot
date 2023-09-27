import logging

from telegram import Bot
from telegram.error import TelegramError

from users import User, get_enabled_users


async def send_message(bot: Bot,
                       user: User,
                       message_text: str,
                       reply_markup=None):
    try:
        await bot.send_message(user.chat_id, message_text,
                               reply_markup=reply_markup)
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
