import re
from datetime import datetime, timedelta

from telegram import InlineKeyboardButton, ReplyKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler

from callbacks.inpatients import show_inpatients_date  # noqa: F401
from callbacks.summary import show_summary_date  # noqa: F401
from classes.to_delete import ToDelete
from constants import SHOW
from utils import build_menu, get_diary_today, private_access


@private_access
async def get_date_from_message(update: Update,
                                context: ContextTypes.DEFAULT_TYPE) -> int:
    chat_id = update.message.chat_id
    to_delete = ToDelete(chat_id=chat_id)
    to_delete.add(update.message)
    dates = list()
    for n in reversed(range(15)):
        dates.append(get_diary_today() - timedelta(days=n))
    button_list = list()
    for some_date in dates:
        button_list.append(
            InlineKeyboardButton(some_date.strftime('%d.%m.%Y'))
        )
    reply_markup = ReplyKeyboardMarkup(build_menu(button_list, n_cols=3),
                                       resize_keyboard=True)
    to_delete.add(
        await update.message.reply_text(
            'Введите дату в формате: dd.mm.YYYY\n'
            'Например: 01.01.2010\n\n'
            'Или выберите день из списка:',
            reply_markup=reply_markup
        )
    )
    show_function_name = update.message.text.replace('/', 'show_')
    context.user_data['show_function'] = eval(show_function_name)
    context.user_data['to_delete'] = to_delete
    return SHOW


async def check_date_from_message(update: Update,
                                  context: ContextTypes.DEFAULT_TYPE):
    message_text = update.message.text
    to_delete = context.user_data['to_delete']
    to_delete.add(update.message)
    pattern = re.compile(r'^\d\d\.\d\d\.\d\d\d\d$')
    if not pattern.match(message_text):
        to_delete.add(
            await update.message.reply_text(
                'Дата введена неверно.\n'
                'Попробуйте ещё раз:'
            )
        )
        return SHOW
    await to_delete.final_delete(context.bot)
    start_date = datetime.strptime(message_text, '%d.%m.%Y').date()
    await context.user_data['show_function'](update, start_date)
    return ConversationHandler.END
