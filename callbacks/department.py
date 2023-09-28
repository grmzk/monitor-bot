import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from classes.users import get_departments, set_department
from utils import build_menu, delete_calling_message, private_access


@delete_calling_message
@private_access
async def choose_department(update: Update, _) -> None:
    departments = get_departments()
    button_list = list()
    for department_id, department_name in departments.items():
        button_list.append(
            InlineKeyboardButton(department_name,
                                 callback_data=f'department {department_id}')
        )
    reply_markup = InlineKeyboardMarkup(build_menu(button_list, n_cols=2))
    await update.message.reply_text(text='ВЫБЕРИТЕ ВАШЕ НОВОЕ ОТДЕЛЕНИЕ:\n',
                                    reply_markup=reply_markup)


@delete_calling_message
async def change_department(update: Update,
                            context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.callback_query.message.chat_id
    department_id = int(update.callback_query.data.split()[-1])
    if set_department(chat_id, department_id):
        departments = get_departments()
        await context.bot.send_message(
            chat_id,
            f'Отделение изменено на [{departments[department_id]}]'
        )
        logging.info(f'User with CHAT_ID={chat_id} '
                     f'changed department to {departments[department_id]}')
        return
    await context.bot.send_message(
        chat_id,
        'Не удалось изменить отделение, попробуйте позже'
    )
