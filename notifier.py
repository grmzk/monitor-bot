import asyncio
import logging
import os
import re
from dataclasses import dataclass
from datetime import MINYEAR, datetime

import fdb
from dotenv import load_dotenv
from fdb.fbcore import (ISOLATION_LEVEL_READ_COMMITED_RO, Connection,
                        InternalError, isc_info_page_size, isc_info_version)
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext

from constants import (ALL_NOTIFICATIONS, ALL_REANIMATION_HOLE, OWN_PATIENTS,
                       OWN_REANIMATION_HOLE, REJECTIONS, STATUS_INPATIENT,
                       STATUS_OUTPATIENT_MAIN, STATUSES)
from users import User, get_enabled_users
from utils import build_menu, send_message

load_dotenv()

RETRY_TIME = 60

FB_DSN = os.getenv('FB_DSN')
FB_USER = os.getenv('FB_USER')
FB_PASSWORD = os.getenv('FB_PASSWORD')
FB_LIBRARY_NAME = os.getenv('FB_LIBRARY_NAME')
DEVELOP = int(os.getenv('DEVELOP'))

if DEVELOP:
    RETRY_TIME = 60


class MyConnection(Connection):
    def __init__(self, db_handle, dpb=None, sql_dialect=3, charset=None,
                 isolation_level=ISOLATION_LEVEL_READ_COMMITED_RO):
        try:
            super(MyConnection, self).__init__(db_handle, dpb, sql_dialect,
                                               charset,
                                               isolation_level)
        except InternalError as error:
            if str(error) == 'Result code does not match request code.':
                verstr = self.db_info(isc_info_version)
                x = verstr.split()
                if x[0].find('V') > 0:
                    (x, self.__version) = x[0].split('V')
                elif x[0].find('T') > 0:
                    (x, self.__version) = x[0].split('T')
                else:
                    # Unknown version
                    self.__version = '0.0.0.0'
                x = self.__version.split('.')
                self.__engine_version = float('%s.%s' % (x[0], x[1]))
                #
                self.__page_size = self.db_info(isc_info_page_size)
            else:
                raise


@dataclass
class Patient:
    patient_id: int
    card_id: int
    admission_date: datetime
    admission_outcome_date: datetime
    family: str
    name: str
    surname: str
    birthday: datetime
    gender: str
    department: str
    reanimation: str
    incoming_diagnosis: str
    admission_diagnosis: str
    status: int
    reject: int
    inpatient_department: str
    doctor: str

    @staticmethod
    def get_date(date: datetime) -> str:
        return date.strftime('%d.%m.%Y %H:%M')

    def get_admission_date(self) -> str:
        return self.get_date(self.admission_date)

    def get_admission_outcome_date(self) -> str:
        return self.get_date(self.admission_outcome_date)

    def get_full_name(self) -> str:
        return f'{self.family} {self.name} {self.surname}'

    def get_birthday(self) -> str:
        return self.birthday.strftime('%d.%m.%Y')

    def get_age(self) -> str:
        birthday = self.birthday
        now = datetime.now()
        age = (now.year - birthday.year
               - ((now.month, now.day) < (birthday.month, birthday.day)))
        ending: str
        if 5 <= age <= 20:
            ending = 'лет'
        elif age % 10 == 1:
            ending = 'год'
        elif 2 <= age % 10 <= 4:
            ending = 'года'
        else:
            ending = 'лет'
        return f'{age} {ending}'

    def is_reanimation(self) -> bool:
        if self.reanimation == 'F':
            return False
        return True

    def is_outcome(self) -> bool:
        return self.admission_outcome_date.year != MINYEAR

    def is_own(self, user: User) -> bool:
        pattern_surgery = re.compile(r'^.* ХИРУРГИЯ$')
        pattern_therapy = re.compile(r'^.* ТЕРАПИЯ$')
        return ((user.department == self.department)
                or (pattern_surgery.match(self.department)
                    and pattern_surgery.match(user.department))
                or (pattern_therapy.match(self.department)
                    and pattern_therapy.match(user.department)))

    def is_inpatient_own(self, user: User) -> bool:
        pattern_surgery = re.compile(r'^.* ХИРУРГИЯ$')
        pattern_therapy = re.compile(r'^.* ТЕРАПИЯ$')
        return ((user.department == self.inpatient_department)
                or (pattern_surgery.match(str(self.inpatient_department))
                    and pattern_surgery.match(user.department))
                or (pattern_therapy.match(str(self.inpatient_department))
                    and pattern_therapy.match(user.department)))

    def is_inpatient(self) -> bool:
        return bool(self.inpatient_department)


def gen_patient_info(patient: Patient, admission=False) -> str:
    reanimation_hole = ''
    full_name = patient.get_full_name()
    admission_outcome_date = ''
    admission_diagnosis = ''
    result = ''
    doctor = ''
    if patient.is_reanimation():
        reanimation_hole = '[РЕАНИМАЦИОННЫЙ ЗАЛ]\n'
    if not patient.get_full_name().strip():
        if patient.gender == 'М':
            full_name = 'НЕИЗВЕСТНЫЙ'
        else:
            full_name = 'НЕИЗВЕСТНАЯ'
    if not admission:
        if patient.is_outcome():
            admission_outcome_date = (
                f'Дата исхода: {patient.get_admission_outcome_date()}\n'
            )
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
            result += f'ГОСПИТАЛИЗАЦИЯ [{patient.inpatient_department}]'
        else:
            result += STATUSES.get(patient.status, f'status={patient.status}')
        result += '\n'
        if patient.doctor:
            doctor = (
                f'Врач: {patient.doctor}\n'
            )
    return (
        '===========================\n'
        f'{reanimation_hole}'
        f'Дата поступления: {patient.get_admission_date()}\n'
        f'{admission_outcome_date}'
        f'Отделение: {patient.department}\n'
        f'Ф.И.О.: {full_name}\n'
        f'Дата рождения: {patient.get_birthday()} '
        f'[{patient.get_age()}]\n'
        'Диагноз при поступлении:\n'
        f'{patient.incoming_diagnosis}\n'
        f'{admission_diagnosis}'
        f'{result}'
        f'{doctor}'
    )


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
        message += gen_patient_info(patient, admission=True)
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


def connect_fdb():
    try:
        connection = fdb.connect(
            dsn=FB_DSN,
            sql_dialect=1,
            charset='WIN1251',
            user=FB_USER,
            password=FB_PASSWORD,
            connection_class=MyConnection,
            fb_library_name=FB_LIBRARY_NAME
        )
    except Exception as error:
        logging.error(f'FB connect ERROR: {error}')
        return None
    return connection


def get_max_card_id() -> int:
    connection = connect_fdb()
    if not connection:
        return 0
    try:
        cursor = connection.cursor()
        cursor.execute('SELECT id FROM main_card ORDER BY id DESC ROWS 1')
        card_id = cursor.fetchall()[0][0]
    except Exception as error:
        logging.error(f'FB query ERROR: {error}')
        return None
    if connection:
        cursor.close()
        connection.close()
    return int(card_id)


def fb_select_data(select_query: str) -> list:
    connection = connect_fdb()
    if not connection:
        return list()
    try:
        cursor = connection.cursor()
        cursor.execute(select_query)
        data = cursor.fetchall()
    except Exception as error:
        logging.error(f'FB query ERROR: {error}')
        return list()
    if connection:
        cursor.close()
        connection.close()
        logging.info('FB query complete SUCCESS')
    return data


async def start_notifier(context: CallbackContext):
    max_card_id = get_max_card_id()
    if not max_card_id:
        logging.error('NOTIFIER not started!')
        return
    logging.info('NOTIFIER started...')
    while True:
        await asyncio.sleep(RETRY_TIME)
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
            f'WHERE c.id > {max_card_id} '
            'ORDER BY c.id'
        )
        patients_data = fb_select_data(select_query)
        if not patients_data:
            continue
        patients = list()
        for patient_data in patients_data:
            patients.append(Patient(*patient_data))
        max_card_id = patients[-1].card_id
        await send_messages(context.bot, patients)
