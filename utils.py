import logging

from telegram import Bot
from telegram.error import TelegramError

from users import User, get_enabled_users


async def send_message(bot: Bot, user: User, message: str, reply_markup=None):
    try:
        await bot.send_message(user.chat_id, message,
                               reply_markup=reply_markup)
    except TelegramError as error:
        logging.error('Sending message to '
                      f'<{user.get_full_name()}> ERROR: {error}')
    else:
        logging.info(f'Sending message to <{user.get_full_name()}> SUCCESS')


async def send_message_all(bot: Bot, message: str, reply_markup=None):
    users = get_enabled_users()
    for user in users:
        await send_message(bot, user, message, reply_markup)
