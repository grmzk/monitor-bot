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

from constants import (NOTIFICATION_DESCRIPTIONS, NOTIFICATION_TITLES,
                       REJECTIONS, STATUS_DIS_DIAGNOSIS, STATUS_INPATIENT,
                       STATUS_OTHER_HOSPITAL, STATUS_OUTPATIENT,
                       STATUS_OUTPATIENT_MAIN, STATUS_OVER_DIAGNOSIS,
                       STATUS_PROCESSING, STATUS_SELF_DENIAL,
                       STATUS_SELF_LEAVE, STATUS_UNREASON_DENY,
                       STATUS_UNREASON_DIRECTED, STATUSES)
from notifier import Patient, fb_select_data, gen_patient_info, start_notifier
from users import (User, get_admin, get_departments, get_enabled_users,
                   get_user, get_users, insert_user, set_department,
                   set_enable, set_notification_level)
from utils import build_menu, send_message, send_message_all

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
TO_DELETE = dict()


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
        'Введите вашу ФАМИЛИЮ (только ФАМИЛИЮ!):\n',
    )
    return FAMILY


async def conversation_handler_end(_, __):
    return ConversationHandler.END


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


@delete_calling_message
@private_access
async def send_all(update: Update,
                   context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message.text.split('/sendall ')[-1]
    await send_message_all(context.bot, message)


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


def get_daily_summary(start_date: date, user: User) -> list:  # noqa: C901
    start_datetime = datetime(year=start_date.year,
                              month=start_date.month,
                              day=start_date.day,
                              hour=8,
                              minute=0)
    end_datetime = start_datetime + timedelta(days=1)
    query_department_arg = f'= \'{user.department}\''
    user_department = user.department
    pattern_surgery = re.compile(r'^.* ХИРУРГИЯ$')
    pattern_therapy = re.compile(r'^.* ТЕРАПИЯ$')
    if pattern_surgery.match(user.department):
        user_department = 'ХИРУРГИЯ'
        query_department_arg = f'LIKE \'% {user_department}\''
    if pattern_therapy.match(user.department):
        user_department = 'ТЕРАПИЯ'
        query_department_arg = f'LIKE \'% {user_department}\''
    select_query = (
        'SELECT c.id_pac, '
        '       c.id, '
        '       c.d_in, '
        '       c.d_out, '
        '       p.fm, '
        '       p.im, '
        '       p.ot, '
        '       p.dtr, '
        '       p.pol, '
        '       otd.short, '
        '       c.remzal, '
        '       c.dsnapr, '
        '       c.dspriem, '
        '       c.id_dvig, '
        '       c.id_otkaz, '
        '       hosp_otd.short, '
        '       doc.last_name '
        '       || \' \' || doc.first_name '
        '       || \' \' || doc.middle_name '
        'FROM main_card c '
        '   LEFT JOIN pacient p ON c.id_pac = p.id '
        '   LEFT JOIN priemnic otd ON c.id_priem = otd.id '
        '   LEFT JOIN priemnic hosp_otd ON c.id_gotd = hosp_otd.id '
        '   LEFT JOIN doctor doc ON c.amb_doc_id = doc.doctor_id '
        f'WHERE '
        f'  ((otd.short {query_department_arg}) '
        f'          OR (hosp_otd.short {query_department_arg})) '
        f'  AND (c.d_in >= \'{start_datetime - timedelta(days=1)}\') '
        f'  AND (c.d_in < \'{end_datetime}\') '
        'ORDER BY c.id'
    )
    patients_data = fb_select_data(select_query)
    unsorted_patients = list()
    for patient_data in patients_data:
        unsorted_patients.append(Patient(*patient_data))
    patients = list()
    for patient in unsorted_patients:
        if (patient.admission_date >= start_datetime
                and patient.admission_outcome_date < end_datetime):
            patients.append(patient)
        elif (patient.admission_date < start_datetime
              and (patient.admission_outcome_date >= start_datetime
                   or patient.status == STATUS_PROCESSING)):
            patients.append(patient)
    message_list = list()
    message = (f'ЗА {start_datetime.strftime("%d.%m.%Y")} '
               f'ОБРАТИЛИСЬ [{user_department}]:\n')
    hospit_own = 0
    hospit_other = 0
    hospit_from_other = 0
    reanimation_holes = 0
    for patient in patients:
        if patient.is_reanimation():
            reanimation_holes += 1
        if patient.status == STATUS_INPATIENT:
            if (patient.department == user.department
                    and patient.department == patient.hospitalization):
                hospit_own += 1
            elif (patient.department == user.department
                    and patient.department != patient.hospitalization):
                hospit_other += 1
            elif (pattern_surgery.match(patient.department)
                    and user_department == 'ХИРУРГИЯ'
                    and pattern_surgery.match(patient.hospitalization)):
                hospit_own += 1
            elif (pattern_surgery.match(patient.department)
                    and user_department == 'ХИРУРГИЯ'
                    and not pattern_surgery.match(patient.hospitalization)):
                hospit_other += 1
            elif (pattern_therapy.match(patient.department)
                    and user_department == 'ТЕРАПИЯ'
                    and pattern_therapy.match(patient.hospitalization)):
                hospit_own += 1
            elif (pattern_therapy.match(patient.department)
                    and user_department == 'ТЕРАПИЯ'
                    and not pattern_therapy.match(patient.hospitalization)):
                hospit_other += 1
            else:
                hospit_from_other += 1
        patient_message = gen_patient_info(patient)
        if len(message + patient_message) > 4096:
            message_list.append(message)
            message = patient_message
            continue
        message += patient_message
    message_list.append(message)
    message_list.append('===========================\n'
                        'ВСЕГО ОБРАТИЛОСЬ: '
                        f'{len(patients) - hospit_from_other}\n'
                        f'ГОСПИТАЛИЗАЦИИ СВОИХ: {hospit_own}\n'
                        f'ГОСПИТАЛИЗАЦИИ ОТ ДРУГИХ: {hospit_from_other}\n'
                        f'ГОСПИТАЛИЗАЦИИ К ДРУГИМ: {hospit_other}\n'
                        f'РЕАНИМАЦИОННЫЕ ЗАЛЫ: {reanimation_holes}\n')
    return message_list


async def show_summary(update: Update, start_date: date) -> None:
    chat_id = update.message.chat_id
    if TO_DELETE.get('summary') and TO_DELETE.get('summary').get(chat_id):
        TO_DELETE['summary'][chat_id].append(update.message)
    else:
        TO_DELETE['summary'] = {chat_id: [update.message]}
    user = get_user(chat_id)
    message_list = get_daily_summary(start_date, user)
    button_list = [
        InlineKeyboardButton(
            'Удалить последнюю сводку',
            callback_data='delete summary')
    ]
    reply_markup = InlineKeyboardMarkup(build_menu(button_list, n_cols=1))
    for message in message_list[:-1]:
        TO_DELETE['summary'][chat_id].append(
            await update.message.reply_text(message,
                                            reply_markup=ReplyKeyboardRemove())
        )
    else:
        TO_DELETE['summary'][chat_id].append(
            await update.message.reply_text(message_list[-1],
                                            reply_markup=reply_markup)
        )


def get_diary_today() -> date:
    diary_today = date.today()
    if datetime.now().time() < time(hour=8, minute=0):
        diary_today -= timedelta(days=1)
    return diary_today


@private_access
async def show_summary_today(update: Update, _) -> None:
    start_date = get_diary_today()
    await show_summary(update, start_date)


@private_access
async def show_summary_yesterday(update: Update, _) -> None:
    start_date = get_diary_today() - timedelta(days=1)
    await show_summary(update, start_date)


@private_access
async def get_date_for_summary(update: Update, _) -> None:
    chat_id = update.message.chat_id
    TO_DELETE['summary'] = {chat_id: [update.message]}
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
    TO_DELETE['summary'][chat_id].append(
        await update.message.reply_text(
            'Введите дату в формате: dd.mm.YYYY\n'
            'Например: 01.01.2010\n\n'
            'Или выберите день из списка:',
            reply_markup=reply_markup
        )
    )
    return 0


async def show_summary_date(update: Update, _) -> None:
    chat_id = update.message.chat_id
    message = update.message.text
    pattern = re.compile(r'^\d\d\.\d\d\.\d\d\d\d$')
    if not pattern.match(message):
        TO_DELETE['summary'][chat_id].append(
            await update.message.reply_text(
                'Дата введена неверно.\n'
                'Попробуйте ещё раз:'
            )
        )
        return 0
    start_date = datetime.strptime(message, '%d.%m.%Y').date()
    await show_summary(update, start_date)
    return ConversationHandler.END


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


def get_processing_patients_all(user: User) -> list:
    start_date = get_diary_today()
    start_datetime = datetime(year=start_date.year,
                              month=start_date.month,
                              day=start_date.day,
                              hour=8,
                              minute=0)
    reanimation_time = ((datetime.now() - timedelta(hours=2, minutes=30))
                        .replace(microsecond=0))
    select_query = (
        'SELECT c.id_pac, '
        '       c.id, '
        '       c.d_in, '
        '       c.d_out, '
        '       p.fm, '
        '       p.im, '
        '       p.ot, '
        '       p.dtr, '
        '       p.pol, '
        '       otd.short, '
        '       c.remzal, '
        '       c.dsnapr, '
        '       c.dspriem, '
        '       c.id_dvig, '
        '       c.id_otkaz, '
        '       hosp_otd.short, '
        '       doc.last_name '
        '       || \' \' || doc.first_name '
        '       || \' \' || doc.middle_name '
        'FROM main_card c '
        '   LEFT JOIN pacient p ON c.id_pac = p.id '
        '   LEFT JOIN priemnic otd ON c.id_priem = otd.id '
        '   LEFT JOIN priemnic hosp_otd ON c.id_gotd = hosp_otd.id '
        '   LEFT JOIN doctor doc ON c.amb_doc_id = doc.doctor_id '
        f'WHERE '
        f'  (c.d_in >= \'{start_datetime - timedelta(days=1)}\') '
        f'  AND ((c.id_dvig = {STATUS_PROCESSING}) '
        f'      OR ((c.remzal <> \'F\') '
        f'          AND (c.d_in >= \'{reanimation_time}\'))) '
        'ORDER BY c.id'
    )
    patients_data = fb_select_data(select_query)
    patients_all = list()
    for patient_data in patients_data:
        patients_all.append(Patient(*patient_data))
    return patients_all


def get_processing_info_all(user: User) -> list:
    patients = get_processing_patients_all(user)
    message_list = list()
    message_header = 'СЕЙЧАС ОБСЛЕДУЮТСЯ [ВСЕ ОТДЕЛЕНИЯ]\n'
    message_footer = ('===========================\n'
                      '[ВСЕ ОТДЕЛЕНИЯ]\n'
                      f'ВСЕГО ОБСЛЕДУЮТСЯ: {len(patients)}\n')
    message = message_header
    reanimation_holes = 0
    for patient in patients:
        if patient.is_reanimation():
            reanimation_holes += 1
        patient_message = gen_patient_info(patient)
        if len(message + patient_message) > 4096:
            message_list.append(message)
            message = patient_message
            continue
        message += patient_message
    message_list.append(message)
    message_footer += f'РЕАНИМАЦИОННЫЕ ЗАЛЫ: {reanimation_holes}'
    message_list.append(message_footer)
    return message_list


def get_processing_info_own(user: User) -> list:
    patients_all = get_processing_patients_all(user)
    patients = list()
    pattern_surgery = re.compile(r'^.* ХИРУРГИЯ$')
    pattern_therapy = re.compile(r'^.* ТЕРАПИЯ$')
    for patient in patients_all:
        if patient.is_own(user):
            patients.append(patient)
    message_list = list()
    department = user.department
    if pattern_surgery.match(user.department):
        department = 'ХИРУРГИЯ'
    elif pattern_therapy.match(user.department):
        department = 'ТЕРАПИЯ'
    message_header = f'СЕЙЧАС ОБСЛЕДУЮТСЯ [{department}]\n'
    message_footer = ('===========================\n'
                      f'[{department}]\n'
                      f'ВСЕГО ОБСЛЕДУЮТСЯ: {len(patients)}\n')
    message = message_header
    reanimation_holes = 0
    for patient in patients:
        if patient.is_reanimation():
            reanimation_holes += 1
        patient_message = gen_patient_info(patient)
        if len(message + patient_message) > 4096:
            message_list.append(message)
            message = patient_message
            continue
        message += patient_message
    message_list.append(message)
    message_footer += f'РЕАНИМАЦИОННЫЕ ЗАЛЫ: {reanimation_holes}'
    message_list.append(message_footer)
    return message_list


def get_processing_info_rean(user: User) -> list:
    patients_all = get_processing_patients_all(user)
    patients = list()
    for patient in patients_all:
        if patient.is_reanimation():
            patients.append(patient)
    message_list = list()
    message_header = 'СЕЙЧАС ОБСЛЕДУЮТСЯ [РЕАНИМАЦИОННЫЙ ЗАЛ]\n'
    message_footer = ('===========================\n'
                      '[РЕАНИМАЦИОННЫЙ ЗАЛ]\n'
                      f'ВСЕГО ОБСЛЕДУЮТСЯ: {len(patients)}\n')
    message = message_header
    for patient in patients:
        patient_message = gen_patient_info(patient)
        if len(message + patient_message) > 4096:
            message_list.append(message)
            message = patient_message
            continue
        message += patient_message
    message_list.append(message)
    message_list.append(message_footer)
    return message_list


async def show_processing(update: Update,
                          message_list: list) -> None:
    chat_id = update.message.chat_id
    TO_DELETE['processing'] = {chat_id: [update.message]}
    button_list = [
        InlineKeyboardButton(
            'Удалить последний список',
            callback_data='delete processing')
    ]
    reply_markup = InlineKeyboardMarkup(build_menu(button_list, n_cols=1))
    for message in message_list[:-1]:
        TO_DELETE['processing'][chat_id].append(
            await update.message.reply_text(message,
                                            reply_markup=ReplyKeyboardRemove())
        )
    else:
        TO_DELETE['processing'][chat_id].append(
            await update.message.reply_text(message_list[-1],
                                            reply_markup=reply_markup)
        )


@private_access
async def show_processing_all(update: Update, _) -> None:
    user = get_user(update.message.chat_id)
    message_list = get_processing_info_all(user)
    await show_processing(update, message_list)


@private_access
async def show_processing_own(update: Update, _) -> None:
    user = get_user(update.message.chat_id)
    message_list = get_processing_info_own(user)
    await show_processing(update, message_list)


@private_access
async def show_processing_rean(update: Update, _) -> None:
    user = get_user(update.message.chat_id)
    message_list = get_processing_info_rean(user)
    await show_processing(update, message_list)


async def delete_messages(update: Update,
                          context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.callback_query.message.chat_id
    delete_key = update.callback_query.data.split()[-1]
    for message in TO_DELETE[delete_key][chat_id]:
        await context.bot.delete_message(message.chat_id, message.message_id)
    TO_DELETE[delete_key][chat_id] = list()


async def show_history(update: Update,  # noqa: C901
                       context: ContextTypes.DEFAULT_TYPE) -> None:
    patient_id = int(update.callback_query.data.split()[-1])
    select_query = (
        'SELECT c.id_pac, '
        '       c.id, '
        '       c.d_in, '
        '       c.d_out, '
        '       p.fm, '
        '       p.im, '
        '       p.ot, '
        '       p.dtr, '
        '       p.pol, '
        '       otd.short, '
        '       c.remzal, '
        '       c.dsnapr, '
        '       c.dspriem, '
        '       c.id_dvig, '
        '       c.id_otkaz, '
        '       hosp_otd.short, '
        '       doc.last_name '
        '       || \' \' || doc.first_name '
        '       || \' \' || doc.middle_name '
        'FROM main_card c '
        '   LEFT JOIN pacient p ON c.id_pac = p.id '
        '   LEFT JOIN priemnic otd ON c.id_priem = otd.id '
        '   LEFT JOIN priemnic hosp_otd ON c.id_gotd = hosp_otd.id '
        '   LEFT JOIN doctor doc ON c.amb_doc_id = doc.doctor_id '
        f'WHERE '
        f'  c.id_pac = {patient_id} '
        'ORDER BY c.id'
    )
    patients_data = fb_select_data(select_query)
    history = list()
    for patient_data in patients_data:
        history.append(Patient(*patient_data))
    message_header = ('ВСЕ ОБРАЩЕНИЯ ПАЦИЕНТА\n'
                      '===========================\n'
                      f'Ф.И.О.: {history[0].get_full_name()}\n'
                      f'Дата рождения: {history[0].get_birthday()} '
                      f'[{history[0].get_age()}]\n')
    message = ''
    message_list = [message_header]
    inpatient = 0
    outpatient = 0
    self_denial = 0
    self_leave = 0
    unreason_directed = 0
    reanimation_holes = 0
    for patient in history:
        if patient.status == STATUS_INPATIENT:
            inpatient += 1
        elif patient.reject == STATUS_OUTPATIENT:
            outpatient += 1
        elif patient.reject == STATUS_SELF_DENIAL:
            self_denial += 1
        elif patient.reject == STATUS_SELF_LEAVE:
            self_leave += 1
        elif (patient.status == STATUS_OTHER_HOSPITAL
              or patient.reject in [STATUS_OVER_DIAGNOSIS,
                                    STATUS_DIS_DIAGNOSIS,
                                    STATUS_UNREASON_DIRECTED,
                                    STATUS_UNREASON_DENY]):
            unreason_directed += 1
        reanimation_hole = ''
        if patient.is_reanimation():
            reanimation_holes += 1
            reanimation_hole = '[РЕАНИМАЦИОННЫЙ ЗАЛ]\n'
        admission_diagnosis = ''
        if patient.admission_diagnosis:
            admission_diagnosis = (
                'Диагноз приёмного отделения:\n'
                f'{patient.admission_diagnosis}\n'
            )
        result = 'Исход: '
        if patient.status == STATUS_OUTPATIENT_MAIN:
            result += REJECTIONS.get(patient.reject,
                                     f'reject={patient.reject}')
        elif patient.status == STATUS_INPATIENT:
            result += f'ГОСПИТАЛИЗАЦИЯ [{patient.hospitalization}]'
        else:
            result += STATUSES.get(patient.status, f'status={patient.status}')
        result += '\n'
        doctor = ''
        if patient.doctor:
            doctor = (
                f'Врач: {patient.doctor}\n'
            )
        patient_message = (
            '===========================\n'
            f'{reanimation_hole}'
            f'Дата поступления: {patient.get_admission_date()}\n'
            f'Отделение: {patient.department}\n'
            f'{admission_diagnosis}'
            f'{result}'
            f'{doctor}'
        )
        if len(message + patient_message) > 4096:
            message_list.append(message)
            message = patient_message
            continue
        message += patient_message
    message_list.append(message)
    message_footer = (
        '===========================\n'
        f'[{history[0].get_full_name()}]\n'
        f'ВСЕГО ОБРАЩЕНИЙ: {len(history)}\n'
        f'ГОСПИТАЛИЗАЦИИ: {inpatient}\n'
        f'РЕАНИМАЦИОННЫЕ ЗАЛЫ: {reanimation_holes}\n'
        f'АМБУЛАТОРНОЕ ЛЕЧЕНИЕ: {outpatient}\n'
        f'САМООТКАЗ: {self_denial}\n'
        f'САМОУХОД: {self_leave}\n'
        f'НЕОБОСНОВАННО НАПРАВЛЕН: {unreason_directed}\n'
    )
    message_list.append(message_footer)
    chat_id = update.callback_query.message.chat_id
    TO_DELETE['history'] = {chat_id: list()}
    button_list = [
        InlineKeyboardButton(
            'Удалить историю обращений',
            callback_data='delete history')
    ]
    reply_markup = InlineKeyboardMarkup(build_menu(button_list, n_cols=1))
    for message in message_list[:-1]:
        TO_DELETE['history'][chat_id].append(
            await context.bot.send_message(chat_id, message,
                                           reply_markup=ReplyKeyboardRemove())
        )
    else:
        TO_DELETE['history'][chat_id].append(
            await context.bot.send_message(chat_id, message_list[-1],
                                           reply_markup=reply_markup)
        )


def main() -> None:
    application = Application.builder().token(TOKEN).build()

    application.add_handler(ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            FAMILY: [MessageHandler(filters.TEXT, start_family)],
            NAME: [MessageHandler(filters.TEXT, start_name)],
            SURNAME: [MessageHandler(filters.TEXT, start_surname)],
            PHONE: [MessageHandler(filters.TEXT, start_phone)],
            DEPARTMENT: [MessageHandler(filters.TEXT, start_department)]
        },
        fallbacks=[CommandHandler('conversation_handler_end',
                                  conversation_handler_end)]
    ))
    application.add_handler(ConversationHandler(
        entry_points=[CommandHandler('summary_date',
                                     get_date_for_summary)],
        states={0: [MessageHandler(filters.TEXT, show_summary_date)]},
        fallbacks=[CommandHandler('conversation_handler_end',
                                  conversation_handler_end)]
    ))

    application.add_handler(CommandHandler('sendall',
                                           send_all))
    application.add_handler(CommandHandler('notifications',
                                           choose_notifications))
    application.add_handler(CommandHandler('summary_today',
                                           show_summary_today))
    application.add_handler(CommandHandler('summary_yesterday',
                                           show_summary_yesterday))
    application.add_handler(CommandHandler('department',
                                           choose_department))
    application.add_handler(CommandHandler('settings',
                                           show_settings))
    application.add_handler(CommandHandler('processing_all',
                                           show_processing_all))
    application.add_handler(CommandHandler('processing_own',
                                           show_processing_own))
    application.add_handler(CommandHandler('processing_rean',
                                           show_processing_rean))

    application.add_handler(CallbackQueryHandler(
        pattern=r'^notification \d$',
        callback=change_notifications)
    )
    application.add_handler(CallbackQueryHandler(pattern=r'^activate \d+$',
                                                 callback=activate_user))
    application.add_handler(CallbackQueryHandler(pattern=r'^delete .+$',
                                                 callback=delete_messages))
    application.add_handler(CallbackQueryHandler(pattern=r'^department \d+$',
                                                 callback=change_department))
    application.add_handler(CallbackQueryHandler(pattern=r'^history \d+$',
                                                 callback=show_history))

    application.job_queue.run_once(start_notifier, 0)
    application.run_polling()


if __name__ == "__main__":
    main()
