import re
from datetime import date, datetime, timedelta
from typing import List

from telegram import Update

from classes.patients import Patient, PatientInfo
from classes.users import User, get_user
from constants import MESSAGE_MAX_SIZE, STATUS_INPATIENT
from notifier import fb_select_data
from utils import (delete_calling_message, get_diary_today, private_access,
                   send_message_list)


def get_summary(start_date: date, user: User) -> List[Patient]:
    start_datetime = datetime(year=start_date.year,
                              month=start_date.month,
                              day=start_date.day,
                              hour=8,
                              minute=0)
    end_datetime = start_datetime + timedelta(days=1)
    query_department_arg = f"= '{user.department}'"
    pattern_surgery = re.compile(r'^.* ХИРУРГИЯ$')
    pattern_therapy = re.compile(r'^.* ТЕРАПИЯ$')
    if pattern_surgery.match(user.department):
        user_department = 'ХИРУРГИЯ'
        query_department_arg = f"LIKE '% {user_department}'"
    if pattern_therapy.match(user.department):
        user_department = 'ТЕРАПИЯ'
        query_department_arg = f"LIKE '% {user_department}'"
    select_query = (
        "SELECT main_card.id_pac, "
        "       main_card.id, "
        "       main_card.d_in, "
        "       main_card.d_out, "
        "       patient.fm, "
        "       patient.im, "
        "       patient.ot, "
        "       patient.dtr, "
        "       patient.pol, "
        "       department.short, "
        "       main_card.remzal, "
        "       main_card.dsnapr, "
        "       main_card.dspriem, "
        "       main_card.id_dvig, "
        "       main_card.id_otkaz, "
        "       inpatient_department.short, "
        "       doctor.last_name "
        "           || ' ' || doctor.first_name "
        "           || ' ' || doctor.middle_name "
        "FROM main_card "
        "   LEFT JOIN pacient patient ON main_card.id_pac = patient.id "
        "   LEFT JOIN priemnic department "
        "       ON main_card.id_priem = department.id "
        "   LEFT JOIN priemnic inpatient_department "
        "       ON main_card.id_gotd = inpatient_department.id "
        "   LEFT JOIN doctor ON main_card.amb_doc_id = doctor.doctor_id "
        "WHERE "
        f"  ((department.short {query_department_arg}) "
        f"      OR (inpatient_department.short {query_department_arg})) "
        "   AND (main_card.d_in >= ?) "
        "   AND (main_card.d_in < ?) "
        "ORDER BY main_card.id"
    )
    patients_data = fb_select_data(
        select_query,
        [
            start_datetime - timedelta(days=1),
            end_datetime
        ]
    )
    unsorted_patients = list()
    for patient_data in patients_data:
        unsorted_patients.append(Patient(*patient_data))
    patients = list()
    for patient in unsorted_patients:
        if (patient.admission_date >= start_datetime
                and (patient.is_outcome()
                     and patient.admission_outcome_date < end_datetime)):
            patients.append(patient)
        elif (patient.admission_date < start_datetime
              and ((not patient.is_outcome())
                   or patient.admission_outcome_date >= start_datetime)):
            patients.append(patient)
    return patients


def gen_summary_messages(start_date: date, user: User) -> List[str]:
    patients = get_summary(start_date, user)
    message_list = list()
    message_header = (f'ЗА {start_date.strftime("%d.%m.%Y")} '
                      f'ОБРАТИЛИСЬ [{user.get_admission_department()}]:\n')
    message_text = message_header
    inpatients_own = 0
    inpatients_other = 0
    inpatients_from_other = 0
    reanimation_holes = 0
    for patient in patients:
        if patient.is_reanimation():
            reanimation_holes += 1
        if patient.status == STATUS_INPATIENT:
            if patient.is_own(user) and patient.is_inpatient_own(user):
                inpatients_own += 1
            elif (not patient.is_own(user)) and patient.is_inpatient_own(user):
                inpatients_from_other += 1
            else:
                inpatients_other += 1
        patient_info = PatientInfo(patient).get_full_info()
        if len(message_text + patient_info) > MESSAGE_MAX_SIZE:
            message_list.append(message_text)
            message_text = patient_info
            continue
        message_text += patient_info
    message_list.append(message_text)
    message_footer = ('===========================\n'
                      'ВСЕГО ОБРАТИЛОСЬ: '
                      f'{len(patients) - inpatients_from_other}\n'
                      f'ГОСПИТАЛИЗАЦИИ СВОИХ: {inpatients_own}\n'
                      f'ГОСПИТАЛИЗАЦИИ ОТ ДРУГИХ: {inpatients_from_other}\n'
                      f'ГОСПИТАЛИЗАЦИИ К ДРУГИМ: {inpatients_other}\n'
                      f'РЕАНИМАЦИОННЫЕ ЗАЛЫ: {reanimation_holes}\n')
    message_list.append(message_footer)
    return message_list


async def show_summary(update: Update, start_date: date) -> None:
    chat_id = update.message.chat_id
    user = get_user(chat_id)
    message_list = gen_summary_messages(start_date, user)
    await send_message_list(
        update,
        message_list,
        'Удалить сводку'
    )


@delete_calling_message
@private_access
async def show_summary_today(update: Update, _) -> None:
    start_date = get_diary_today()
    await show_summary(update, start_date)


@delete_calling_message
@private_access
async def show_summary_yesterday(update: Update, _) -> None:
    start_date = get_diary_today() - timedelta(days=1)
    await show_summary(update, start_date)


async def show_summary_date(update: Update, start_date: date) -> None:
    await show_summary(update, start_date)
