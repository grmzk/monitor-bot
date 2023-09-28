from datetime import date, timedelta

from telegram import (InlineKeyboardButton, InlineKeyboardMarkup,
                      ReplyKeyboardRemove, Update)

from callbacks.summary import get_daily_summary
from classes.patients import PatientInfo
from classes.to_delete import ToDelete
from classes.users import get_user
from utils import (build_menu, delete_calling_message, get_diary_today,
                   private_access)


async def show_inpatients(update: Update, start_date: date) -> None:
    chat_id = update.message.chat_id
    to_delete = ToDelete(chat_id=chat_id)
    user = get_user(chat_id)
    patients = get_daily_summary(start_date, user)
    inpatients = list()
    for patient in patients:
        if patient.is_inpatient_own(user):
            inpatients.append(patient)
    message_header = (
        f'ЗА {start_date.strftime("%d.%m.%Y")} '
        f'ГОСПИТАЛИЗИРОВАНО [{user.get_admission_department()}]:\n'
    )
    to_delete.add(
        await update.message.reply_text(message_header,
                                        reply_markup=ReplyKeyboardRemove())
    )
    inpatients_own = 0
    inpatients_from_other = 0
    reanimation_holes = 0
    for patient in inpatients:
        if patient.is_reanimation():
            reanimation_holes += 1
        if patient.is_own(user):
            inpatients_own += 1
        else:
            inpatients_from_other += 1
        patient_info = PatientInfo(patient).get_full_info()
        button_list = [
            InlineKeyboardButton(
                'Показать прошлые обращения',
                callback_data=f'history {patient.patient_id}')
        ]
        reply_markup = InlineKeyboardMarkup(build_menu(button_list, n_cols=1))
        if not patient.get_full_name().strip():
            reply_markup = None
        to_delete.add(
            await update.message.reply_text(patient_info,
                                            reply_markup=reply_markup)
        )
    message_footer = ('===========================\n'
                      f'ВСЕГО ГОСПИТАЛИЗИРОВАНО: {len(inpatients)}\n'
                      f'ГОСПИТАЛИЗАЦИИ СВОИХ: {inpatients_own}\n'
                      f'ГОСПИТАЛИЗАЦИИ ОТ ДРУГИХ: {inpatients_from_other}\n'
                      f'РЕАНИМАЦИОННЫЕ ЗАЛЫ: {reanimation_holes}\n')
    button_list = [
        InlineKeyboardButton(
            'Удалить список госпитализаций',
            callback_data=f'delete {to_delete.to_delete_id}')
    ]
    reply_markup = InlineKeyboardMarkup(build_menu(button_list, n_cols=1))
    to_delete.add(
        await update.message.reply_text(message_footer,
                                        reply_markup=reply_markup)
    )
    to_delete.save()


@delete_calling_message
@private_access
async def show_inpatients_today(update: Update, _) -> None:
    start_date = get_diary_today()
    await show_inpatients(update, start_date)


@delete_calling_message
@private_access
async def show_inpatients_yesterday(update: Update, _) -> None:
    start_date = get_diary_today() - timedelta(days=1)
    await show_inpatients(update, start_date)


async def show_inpatients_date(update: Update, start_date: date) -> None:
    await show_inpatients(update, start_date)
