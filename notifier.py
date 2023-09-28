import asyncio
import logging
import os
from typing import Union

from dotenv import load_dotenv
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext

from classes.patients import Patient, PatientInfo
from classes.users import User, get_enabled_users
from constants import (ALL_NOTIFICATIONS, ALL_REANIMATION_HOLE, OWN_PATIENTS,
                       OWN_REANIMATION_HOLE)
from databases.firebird_db import fb_select_data
from utils import build_menu, send_message

load_dotenv()

RETRY_TIME = 60
DEVELOP = int(os.getenv('DEVELOP'))
if DEVELOP:
    RETRY_TIME = 60


async def send_message_with_button(bot: Bot, user: User,
                                   patient: Patient, message: str) -> None:
    button_list = [
        InlineKeyboardButton(
            'Показать прошлые обращения',
            callback_data=f'history {patient.patient_id}')
    ]
    reply_markup = InlineKeyboardMarkup(build_menu(button_list, n_cols=1))
    if not patient.get_full_name().strip():
        reply_markup = None
    await send_message(bot, user, message, reply_markup=reply_markup)


async def send_messages(bot: Bot, patients):
    users = get_enabled_users()
    for patient in patients:
        message = 'Новый поступивший пациент:\n'
        message += PatientInfo(patient).get_admission_info()
        for user in users:
            if user.notification_level == OWN_PATIENTS:
                if patient.is_own(user):
                    await send_message_with_button(bot, user, patient, message)
                continue
            if user.notification_level == OWN_REANIMATION_HOLE:
                if patient.is_own(user) and patient.is_reanimation():
                    await send_message_with_button(bot, user, patient, message)
                continue
            if user.notification_level == ALL_REANIMATION_HOLE:
                if patient.is_reanimation():
                    await send_message_with_button(bot, user, patient, message)
                continue
            if user.notification_level == ALL_NOTIFICATIONS:
                await send_message_with_button(bot, user, patient, message)


def get_max_card_id() -> Union[int, bool]:
    select_query = "SELECT id FROM main_card ORDER BY id DESC ROWS 1"
    data = fb_select_data(select_query)
    if not data:
        return False
    return data[0][0]


async def start_notifier(context: CallbackContext):
    max_card_id = get_max_card_id()
    if not max_card_id:
        logging.error('NOTIFIER not started!')
        return
    logging.info('NOTIFIER started...')
    while True:
        await asyncio.sleep(RETRY_TIME)
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
            "   main_card.id > ? "
            "ORDER BY main_card.id"
        )
        patients_data = fb_select_data(select_query, [max_card_id])
        if not patients_data:
            continue
        patients = list()
        for patient_data in patients_data:
            patients.append(Patient(*patient_data))
        max_card_id = patients[-1].card_id
        await send_messages(context.bot, patients)
