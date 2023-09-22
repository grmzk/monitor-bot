import logging
import os
import re
from datetime import date, datetime, time, timedelta

from dotenv import load_dotenv
from telegram import (InlineKeyboardButton, InlineKeyboardMarkup,
                      ReplyKeyboardMarkup, ReplyKeyboardRemove, Update)
from telegram.ext import (Application, CallbackQueryHandler, CommandHandler,
                          ContextTypes, ConversationHandler, MessageHandler,
                          filters)

from constants import (ALL_NOTIFICATIONS, ALL_REANIMATION_HOLE,
                       NO_NOTIFICATION, NOTIFICATION_LEVELS, OWN_PATIENTS,
                       OWN_REANIMATION_HOLE)
from notifier import Patient, fb_select_data, gen_patient_info, start_notifier
from users import (User, get_admin, get_departments, get_enabled_users,
                   get_user, get_users, insert_user, set_enable,
                   set_notification_level)
from utils import send_message, send_message_all

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(module)s] %(message)s',
)

TOKEN = os.getenv('TOKEN')
DEVELOP = int(os.getenv('DEVELOP'))

if DEVELOP:
    TOKEN = os.getenv('TOKEN_DEVELOP')

FAMILY, NAME, SURNAME, PHONE, DEPARTMENT = range(5)
NEW_USERS = dict()


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


def build_menu(buttons, n_cols,
               header_buttons=None,
               footer_buttons=None):
    menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
    if header_buttons:
        menu.insert(0, [header_buttons])
    if footer_buttons:
        menu.append([footer_buttons])
    return menu


async def start(update: Update, _) -> int:
    chat_id = update.message.chat_id
    users = get_users()
    for user in users:
        if user.chat_id == chat_id:
            await update.message.reply_text(
                f'Здравствуйте, {user.get_full_name()}!'
            )
            return ConversationHandler.END
    await update.message.reply_text(
        'Для доступа передайте следующую информацию:\n'
        '- Ф.И.О.\n'
        '- Телефонный номер\n'
        '- Отделение\n\n'
        'Введите вашу фамилию, если готовы:\n',
    )
    return FAMILY


async def end_start(_, __):
    return ConversationHandler.END


async def set_family(update: Update, _):
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


async def set_name(update: Update, _):
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


async def set_surname(update: Update, _):
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


async def set_phone(update: Update, _):
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
    for department_name, department_id in departments.items():
        button_list.append(
            InlineKeyboardButton(department_name)
        )
    reply_markup = ReplyKeyboardMarkup(build_menu(button_list, n_cols=2))
    await update.message.reply_text('Выберите ваше отделение:\n',
                                    reply_markup=reply_markup)
    return DEPARTMENT


async def set_department(update: Update,
                         context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user = update.message.from_user
    message = update.message.text
    departments = get_departments()
    if message not in departments.keys():
        await update.message.reply_text(
            'Выберите ваше отделение из списка, который ниже:\n'
        )
        return DEPARTMENT
    NEW_USERS[chat_id]['department'] = departments[message]
    logging.info(f'Somebody <{user.full_name}> with CHAT_ID={chat_id} '
                 f'entered department: {message}')
    user_data = NEW_USERS[chat_id]
    user = User(family=user_data['family'],
                name=user_data['name'],
                surname=user_data['surname'],
                department=user_data['department'],
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
            'Добавился новый пользователь\n'
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
        'Когда ваша учетная запись будет активирована, придёт уведомление.',
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
            '[ВАША УЧЕТНАЯ ЗАПИСЬ АКТИВИРОВАНА]'
        )
        return
    await context.bot.send_message(
        chat_id,
        f'Ошибка активации пользователя с CHAT_ID={user_chat_id}'
    )


@private_access
async def choose_notifications(update: Update, _) -> None:
    button_list = [
        InlineKeyboardButton(
            NOTIFICATION_LEVELS[OWN_PATIENTS],
            callback_data=f'notification {OWN_PATIENTS}'),
        InlineKeyboardButton(
            NOTIFICATION_LEVELS[OWN_REANIMATION_HOLE],
            callback_data=f'notification {OWN_REANIMATION_HOLE}'
        ),
        InlineKeyboardButton(
            NOTIFICATION_LEVELS[ALL_REANIMATION_HOLE],
            callback_data=f'notification {ALL_REANIMATION_HOLE}'
        ),
        InlineKeyboardButton(
            NOTIFICATION_LEVELS[ALL_NOTIFICATIONS],
            callback_data=f'notification {ALL_NOTIFICATIONS}'
        ),
        InlineKeyboardButton(
            NOTIFICATION_LEVELS[NO_NOTIFICATION],
            callback_data=f'notification {NO_NOTIFICATION}'
        ),
    ]
    reply_markup = InlineKeyboardMarkup(build_menu(button_list, n_cols=1))
    await update.message.reply_text(text='ВЫБЕРИТЕ УРОВЕНЬ УВЕДОМЛЕНИЙ:\n',
                                    reply_markup=reply_markup)


@private_access
async def send_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message.text.split('/sendall ')[-1]
    await send_message_all(context.bot, message)


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


def get_daily_summary(start_date: date, user: User) -> list:
    start_datetime = datetime(year=start_date.year,
                              month=start_date.month,
                              day=start_date.day,
                              hour=8,
                              minute=30)
    end_datetime = start_datetime + timedelta(days=1)
    select_query = (
        'SELECT c.id,'
        '       c.d_in,'
        '       p.fm,'
        '       p.im,'
        '       p.ot,'
        '       p.dtr,'
        '       p.pol,'
        '       otd.short,'
        '       c.remzal,'
        '       c.dsnapr,'
        '       c.dspriem, '
        '       c.id_dvig, '
        '       c.id_otkaz, '
        '       hosp_otd.short '
        'FROM main_card c '
        '   LEFT JOIN pacient p ON c.id_pac = p.id '
        '   LEFT JOIN priemnic otd ON c.id_priem = otd.id '
        '   LEFT JOIN priemnic hosp_otd ON c.id_gotd = hosp_otd.id '
        f'WHERE ((otd.short = \'{user.department}\') '
        f'      OR (hosp_otd.short = \'{user.department}\'))'
        f'  AND (c.d_in >= \'{start_datetime}\') '
        f'  AND (c.d_in < \'{end_datetime}\') '
        'ORDER BY c.id'
    )
    patients_data = fb_select_data(select_query)
    patients = list()
    for patient_data in patients_data:
        patients.append(Patient(*patient_data))
    message_list = list()
    message = (f'ЗА {start_datetime.strftime("%d.%m.%Y")} '
               f'ОБРАТИЛИСЬ [{user.department}]:\n')
    hospit_own = 0
    hospit_other = 0
    hospit_from_other = 0
    reanimation_holes = 0
    for patient in patients:
        if patient.is_reanimation():
            reanimation_holes += 1
        if patient.status == 7:
            if (patient.department == user.department
                    and patient.department == patient.hospitalization):
                hospit_own += 1
            elif (patient.department == user.department
                    and patient.department != patient.hospitalization):
                hospit_other += 1
            else:
                hospit_from_other += 1
        patient_message = gen_patient_info(patient)
        new_message = message + patient_message
        if len(new_message) > 4096:
            message_list.append(message)
            message = patient_message
            continue
        message += patient_message
    message_list.append(message)
    message_list.append('===========================\n'
                        f'ВСЕГО ОБРАТИЛОСЬ: {len(patients)}\n'
                        f'ГОСПИТАЛИЗАЦИИ СВОИХ: {hospit_own}\n'
                        f'ГОСПИТАЛИЗАЦИИ ОТ ДРУГИХ: {hospit_from_other}\n'
                        f'ГОСПИТАЛИЗАЦИИ К ДРУГИМ: {hospit_other}\n'
                        f'РЕАНИМАЦИОННЫЕ ЗАЛЫ: {reanimation_holes}\n')
    return message_list


@private_access
async def show_summary_today(update: Update, _) -> None:
    user = get_user(update.message.chat_id)
    now = datetime.now()
    start_date = now.date()
    if now.time() < time(hour=8, minute=30):
        start_date -= timedelta(days=1)
    message_list = get_daily_summary(start_date, user)
    for message in message_list:
        await update.message.reply_text(message)


@private_access
async def show_summary_yesterday(update: Update, _) -> None:
    user = get_user(update.message.chat_id)
    now = datetime.now()
    start_date = now.date()
    if now.time() < time(hour=8, minute=30):
        start_date -= timedelta(days=1)
    start_date -= timedelta(days=1)
    message_list = get_daily_summary(start_date, user)
    for message in message_list:
        await update.message.reply_text(message)


def main() -> None:
    application = Application.builder().token(TOKEN).build()

    application.add_handler(ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            FAMILY: [MessageHandler(filters.TEXT, set_family)],
            NAME: [MessageHandler(filters.TEXT, set_name)],
            SURNAME: [MessageHandler(filters.TEXT, set_surname)],
            PHONE: [MessageHandler(filters.TEXT, set_phone)],
            DEPARTMENT: [MessageHandler(filters.TEXT, set_department)]
        },
        fallbacks=[CommandHandler('end_start', end_start)]
    ))

    application.add_handler(CommandHandler("sendall",
                                           send_all))
    application.add_handler(CommandHandler("notifications",
                                           choose_notifications))
    application.add_handler(CommandHandler("summary_today",
                                           show_summary_today))
    application.add_handler(CommandHandler("summary_yesterday",
                                           show_summary_yesterday))

    application.add_handler(CallbackQueryHandler(pattern=r'^notification \d$',
                                                 callback=set_notifications))
    application.add_handler(CallbackQueryHandler(pattern=r'^activate \d+$',
                                                 callback=activate_user))

    application.job_queue.run_once(start_notifier, 0)
    application.run_polling()


if __name__ == "__main__":
    main()
