from typing import List

from telegram import (InlineKeyboardButton, InlineKeyboardMarkup,
                      ReplyKeyboardRemove, Update)
from telegram.ext import ContextTypes

from classes.patients import Patient, PatientInfo
from classes.to_delete import ToDelete
from constants import (STATUS_DIS_DIAGNOSIS, STATUS_INPATIENT,
                       STATUS_OTHER_HOSPITAL, STATUS_OUTPATIENT,
                       STATUS_OVER_DIAGNOSIS, STATUS_SELF_DENIAL,
                       STATUS_SELF_LEAVE, STATUS_UNREASON_DENY,
                       STATUS_UNREASON_DIRECTED)
from databases.firebird_db import fb_select_data
from utils import build_menu


def get_history(patient_id: int) -> List[Patient]:
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
        "   main_card.id_pac = ? "
        "ORDER BY main_card.id"
    )
    patients_data = fb_select_data(select_query, [patient_id])
    history = list()
    for patient_data in patients_data:
        history.append(Patient(*patient_data))
    return history


async def show_history(update: Update,
                       context: ContextTypes.DEFAULT_TYPE) -> None:
    patient_id = int(update.callback_query.data.split()[-1])
    history = get_history(patient_id)
    message_header = ('ВСЕ ОБРАЩЕНИЯ ПАЦИЕНТА\n'
                      '===========================\n'
                      f'Ф.И.О.: {history[0].get_full_name()}\n'
                      f'Дата рождения: {history[0].get_birthday()} '
                      f'[{history[0].get_age()}]\n')
    message_text = message_header
    message_list = list()
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
        if patient.is_reanimation():
            reanimation_holes += 1
        history_info = PatientInfo(patient).get_history_info()
        if len(message_text + history_info) > 4096:
            message_list.append(message_text)
            message_text = history_info
            continue
        message_text += history_info
    message_list.append(message_text)
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
    to_delete = ToDelete(chat_id=chat_id)
    button_list = [
        InlineKeyboardButton(
            'Удалить историю обращений',
            callback_data=f'delete {to_delete.to_delete_id}')
    ]
    reply_markup = InlineKeyboardMarkup(build_menu(button_list, n_cols=1))
    for message_text in message_list[:-1]:
        to_delete.add(
            await context.bot.send_message(chat_id, message_text,
                                           reply_markup=ReplyKeyboardRemove())
        )
    else:
        to_delete.add(
            await context.bot.send_message(chat_id, message_list[-1],
                                           reply_markup=reply_markup)
        )
    to_delete.save()
