from datetime import datetime, timedelta
from typing import List

from telegram import Update

from classes.patients import Patient, PatientInfo
from classes.users import User, get_user
from constants import MESSAGE_MAX_SIZE, STATUS_PROCESSING
from databases.firebird_db import fb_select_data
from utils import (delete_calling_message, get_diary_today, private_access,
                   send_message_list)


def get_processing_patients_all() -> List[Patient]:
    start_date = get_diary_today()
    start_datetime = datetime(year=start_date.year,
                              month=start_date.month,
                              day=start_date.day,
                              hour=8,
                              minute=0)
    reanimation_time = ((datetime.now() - timedelta(hours=2, minutes=30))
                        .replace(microsecond=0))
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
        "   (main_card.d_in >= ?) "
        "   AND ((main_card.id_dvig = ?) "
        "       OR ((main_card.remzal <> ?) "
        "           AND (main_card.d_in >= ?))) "
        "ORDER BY main_card.id"
    )
    patients_data = fb_select_data(
        select_query,
        [
            start_datetime - timedelta(days=1),
            STATUS_PROCESSING,
            'F',
            reanimation_time
        ]
    )
    patients_all = list()
    for patient_data in patients_data:
        patients_all.append(Patient(*patient_data))
    return patients_all


def get_processing_info_all() -> List[str]:
    patients = get_processing_patients_all()
    message_list = list()
    message_header = 'СЕЙЧАС ОБСЛЕДУЮТСЯ [ВСЕ ОТДЕЛЕНИЯ]\n'
    message_footer = ('===========================\n'
                      '[ВСЕ ОТДЕЛЕНИЯ]\n'
                      f'ВСЕГО ОБСЛЕДУЮТСЯ: {len(patients)}\n')
    message_text = message_header
    reanimation_holes = 0
    for patient in patients:
        if patient.is_reanimation():
            reanimation_holes += 1
        patient_info = PatientInfo(patient).get_admission_info()
        if len(message_text + patient_info) > MESSAGE_MAX_SIZE:
            message_list.append(message_text)
            message_text = patient_info
            continue
        message_text += patient_info
    message_list.append(message_text)
    message_footer += f'РЕАНИМАЦИОННЫЕ ЗАЛЫ: {reanimation_holes}'
    message_list.append(message_footer)
    return message_list


def get_processing_info_own(user: User) -> List[str]:
    patients_all = get_processing_patients_all()
    patients = list()
    for patient in patients_all:
        if patient.is_own(user):
            patients.append(patient)
    message_list = list()
    message_header = (f'СЕЙЧАС ОБСЛЕДУЮТСЯ '
                      f'[{user.get_admission_department()}]\n')
    message_footer = ('===========================\n'
                      f'[{user.get_admission_department()}]\n'
                      f'ВСЕГО ОБСЛЕДУЮТСЯ: {len(patients)}\n')
    message_text = message_header
    reanimation_holes = 0
    for patient in patients:
        if patient.is_reanimation():
            reanimation_holes += 1
        patient_info = PatientInfo(patient).get_admission_info()
        if len(message_text + patient_info) > MESSAGE_MAX_SIZE:
            message_list.append(message_text)
            message_text = patient_info
            continue
        message_text += patient_info
    message_list.append(message_text)
    message_footer += f'РЕАНИМАЦИОННЫЕ ЗАЛЫ: {reanimation_holes}'
    message_list.append(message_footer)
    return message_list


def get_processing_info_rean() -> List[str]:
    patients_all = get_processing_patients_all()
    patients = list()
    for patient in patients_all:
        if patient.is_reanimation():
            patients.append(patient)
    message_list = list()
    message_header = 'СЕЙЧАС ОБСЛЕДУЮТСЯ [РЕАНИМАЦИОННЫЙ ЗАЛ]\n'
    message_footer = ('===========================\n'
                      '[РЕАНИМАЦИОННЫЙ ЗАЛ]\n'
                      f'ВСЕГО ОБСЛЕДУЮТСЯ: {len(patients)}\n')
    message_text = message_header
    for patient in patients:
        patient_info = PatientInfo(patient).get_admission_info()
        if len(message_text + patient_info) > MESSAGE_MAX_SIZE:
            message_list.append(message_text)
            message_text = patient_info
            continue
        message_text += patient_info
    message_list.append(message_text)
    message_list.append(message_footer)
    return message_list


async def show_processing(update: Update, message_list: List[str]) -> None:
    await send_message_list(
        update,
        message_list,
        'Удалить список обследующихся'
    )


@delete_calling_message
@private_access
async def show_processing_all(update: Update, _) -> None:
    message_list = get_processing_info_all()
    await show_processing(update, message_list)


@delete_calling_message
@private_access
async def show_processing_own(update: Update, _) -> None:
    user = get_user(update.message.chat_id)
    message_list = get_processing_info_own(user)
    await show_processing(update, message_list)


@delete_calling_message
@private_access
async def show_processing_rean(update: Update, _) -> None:
    message_list = get_processing_info_rean()
    await show_processing(update, message_list)
