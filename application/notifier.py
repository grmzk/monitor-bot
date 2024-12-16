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
from databases.postgresql_db import pg_select_data, pg_write_data
from utils import build_menu, send_message, send_message_admin

load_dotenv()

DEVELOP = int(os.getenv('DEVELOP'))
GET_LAST_ID = int(os.getenv('GET_LAST_ID'))
SET_LAST_ID = int(os.getenv('SET_LAST_ID'))


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
        message = 'НОВЫЙ ПОСТУПИВШИЙ ПАЦИЕНТ:\n'
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


def get_main_card_last_id() -> Union[int, bool]:
    select_query = ("SELECT value "
                    "FROM variables "
                    "WHERE name = 'main_card_last_id'")
    data = pg_select_data(select_query)
    if not data:
        return False
    return data[0][0]


def set_main_card_last_id(main_card_last_id: int) -> Union[int, bool]:
    write_query = (
        "UPDATE variables "
        "SET value = %s "
        "WHERE name = 'main_card_last_id'"
    )
    return pg_write_data(write_query, [main_card_last_id])


async def start_notifier(context: CallbackContext):
    max_card_id = get_main_card_last_id()
    if not max_card_id:
        logging.error('NOTIFIER get_main_card_last_id ERROR!')
        return
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
        return
    patients = list()
    for patient_data in patients_data:
        patients.append(Patient(*patient_data))
    max_card_id = patients[-1].card_id
    if DEVELOP:
        if GET_LAST_ID:
            await send_message_admin(context.bot,
                                     f"LAST_ID: {get_main_card_last_id()}\n"
                                     f"LAST_ID in BSMP1_DB: {max_card_id}")
            return
        if SET_LAST_ID:
            set_main_card_last_id(max_card_id)
            await send_message_admin(context.bot,
                                     f"LAST_ID was set to {max_card_id}")
            return
    else:
        set_main_card_last_id(max_card_id)
    await send_messages(context.bot, patients)
