from telegram import Update
from telegram.ext import ContextTypes

from classes.to_delete import ToDelete
from classes.users import get_user
from constants import NOTIFICATION_TITLES
from utils import delete_calling_message, private_access, send_message_all


@delete_calling_message
@private_access
async def send_all(update: Update,
                   context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message.text.split('/sendall ')[-1]
    await send_message_all(context.bot, message)


@delete_calling_message
@private_access
async def show_settings(update: Update, _) -> None:
    chat_id = update.message.chat_id
    user = get_user(chat_id)
    await update.message.reply_text(
        'ТЕКУЩИЕ НАСТРОЙКИ\n\n'
        f'Уведомления: [{NOTIFICATION_TITLES[user.notification_level]}]\n'
        f'Отделение: [{user.department}]\n'
    )


async def delete_messages(update: Update,
                          context: ContextTypes.DEFAULT_TYPE) -> None:
    to_delete_id = int(update.callback_query.data.split()[-1])
    to_delete = ToDelete(to_delete_id=to_delete_id)
    await to_delete.final_delete(context.bot)
