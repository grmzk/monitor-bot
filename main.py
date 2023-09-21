import logging
import os

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (Application, CallbackQueryHandler, CommandHandler,
                          ContextTypes)

from constants import (ALL_NOTIFICATIONS, ALL_REANIMATION_HOLE,
                       NO_NOTIFICATION, NOTIFICATION_LEVELS, OWN_PATIENTS,
                       OWN_REANIMATION_HOLE)
from notifier import start_notifier
from users import get_users, set_notification_level

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(module)s] %(message)s',
)

TOKEN = os.getenv('TOKEN')
DEVELOP = int(os.getenv('DEVELOP'))

if DEVELOP:
    TOKEN = os.getenv('TOKEN_DEVELOP')


def private_access(coroutine):
    async def coroutine_restrict(update: Update,
                                 context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.message.chat_id
        users = get_users()
        for user in users:
            if user.chat_id == chat_id:
                return await coroutine(update, context)
        return await update.message.reply_text(
            '[ДОСТУП ЗАКРЫТ]\n'
            'Для доступа передайте администратору '
            'следующую информацию:\n'
            '- Ф.И.О.\n'
            '- Телефонный номер\n'
            '- Отделение\n'
            f'- CHAT_ID = {chat_id}'
        )
    return coroutine_restrict


def build_menu(buttons, n_cols,
               header_buttons=None,
               footer_buttons=None):
    menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
    if header_buttons:
        menu.insert(0, [header_buttons])
    if footer_buttons:
        menu.append([footer_buttons])
    return menu


@private_access
async def start(update: Update, _) -> None:
    username = update.message.from_user.username
    await update.message.reply_text(f'{username}, здрасти!')


@private_access
async def choose_notifications(update: Update, _) -> None:
    button_list = [
        InlineKeyboardButton(
            NOTIFICATION_LEVELS[OWN_PATIENTS],
            callback_data=f'notifications {OWN_PATIENTS}'),
        InlineKeyboardButton(
            NOTIFICATION_LEVELS[OWN_REANIMATION_HOLE],
            callback_data=f'notifications {OWN_REANIMATION_HOLE}'
        ),
        InlineKeyboardButton(
            NOTIFICATION_LEVELS[ALL_REANIMATION_HOLE],
            callback_data=f'notifications {ALL_REANIMATION_HOLE}'
        ),
        InlineKeyboardButton(
            NOTIFICATION_LEVELS[ALL_NOTIFICATIONS],
            callback_data=f'notifications {ALL_NOTIFICATIONS}'
        ),
        InlineKeyboardButton(
            NOTIFICATION_LEVELS[NO_NOTIFICATION],
            callback_data=f'notifications {NO_NOTIFICATION}'
        ),
    ]
    reply_markup = InlineKeyboardMarkup(build_menu(button_list, n_cols=1))
    await update.message.reply_text(text='Выберите уровень уведомлений:\n'
                                         '=============================',
                                    reply_markup=reply_markup)


async def set_notifications(update: Update,
                            context: ContextTypes.DEFAULT_TYPE) -> None:
    notification_level = int(update.callback_query.data.split()[-1])
    chat_id = update.callback_query.message.chat_id
    if set_notification_level(chat_id, notification_level):
        await context.bot.send_message(
            chat_id,
            'Установлен уровень уведомлений:\n'
            f'<{NOTIFICATION_LEVELS[notification_level]}>'
        )
        logging.info(f'User with CHAT_ID={chat_id} '
                     f'changed notification to {notification_level}')
        return
    await context.bot.send_message(
        chat_id,
        'Не удалось изменить уровень уведомлений, попробуйте позже'
    )


def main() -> None:

    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("notifications",
                                           choose_notifications))
    application.add_handler(CallbackQueryHandler(pattern=r'^notifications \d$',
                                                 callback=set_notifications))
    application.job_queue.run_once(start_notifier, 0)
    application.run_polling()


if __name__ == "__main__":
    main()
