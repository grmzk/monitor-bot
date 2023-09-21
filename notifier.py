import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime

import fdb
from fdb.fbcore import (ISOLATION_LEVEL_READ_COMMITED_RO, Connection,
                        InternalError, isc_info_page_size, isc_info_version)
from telegram.error import TelegramError
from telegram.ext import CallbackContext

from constants import (ALL_NOTIFICATIONS, ALL_REANIMATION_HOLE, OWN_PATIENTS,
                       OWN_REANIMATION_HOLE)
from users import get_users

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
    card_id: int
    admission_date: datetime
    family: str
    name: str
    surname: str
    birthday: datetime
    gender: str
    department: str
    reanimation: str
    admission_diagnosis: str
    primary_diagnosis: str

    def get_admission_date(self) -> str:
        return self.admission_date.strftime('%d.%m.%Y %H:%M')

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


async def send_message(bot, user, message):
    try:
        await bot.send_message(user.chat_id, message)
    except TelegramError as error:
        logging.error('Sending message to '
                      f'{user.get_full_name()} ERROR: {error}')
    else:
        logging.info(f'Sending message to {user.get_full_name()} SUCCESS')


async def send_messages(bot, patients):
    users = get_users()
    message_all = str()
    message_reanimation_hole_all = str()
    for patient in patients:
        reanimation_hole = ''
        if patient.is_reanimation():
            reanimation_hole = '[РЕАНИМАЦИОННЫЙ ЗАЛ]\n'
        message = (
            '===========================\n'
            f'{reanimation_hole}'
            f'Дата поступления: {patient.get_admission_date()}\n'
            f'Отделение: {patient.department}\n'
            f'Ф.И.О.: {patient.get_full_name()}\n'
            f'Дата рождения: {patient.get_birthday()} '
            f'[{patient.get_age()}]\n'
            'Диагноз при поступлении:\n'
            f'{patient.admission_diagnosis}\n'
        )
        message_all += message
        if patient.is_reanimation():
            message_reanimation_hole_all += message
        for user in users:
            if user.department == patient.department:
                if user.notification_level == OWN_PATIENTS:
                    await send_message(bot, user,
                                       'Новый поступивший пациент:\n'
                                       f'{message}')
                elif (user.notification_level == OWN_REANIMATION_HOLE
                        and patient.is_reanimation()):
                    await send_message(bot, user,
                                       'Новый поступивший пациент:\n'
                                       f'{message}')
    for user in users:
        if user.notification_level == ALL_NOTIFICATIONS:
            await send_message(bot, user,
                               'Новые поступившие пациенты:\n'
                               f'{message_all}')
        elif (user.notification_level == ALL_REANIMATION_HOLE
              and message_reanimation_hole_all):
            await send_message(bot, user,
                               'Новые поступившие пациенты:\n'
                               f'{message_reanimation_hole_all}')


def connect_fdb():
    try:
        connection = fdb.connect(
            dsn='bsmp-big-2:f:/statist/NEW_MED.GDB',
            sql_dialect=1,
            charset='WIN1251',
            user='USR',
            password='12',
            connection_class=MyConnection,
            fb_library_name='/usr/lib64/libfbclient.so.2'
        )
    except Exception as error:
        logging.error(f'FDB connect ERROR: {error}')
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
        logging.error(f'FDB SQL query ERROR: {error}')
        return None
    if connection:
        if cursor:
            cursor.close()
        connection.close()
    return int(card_id)


async def start_notifier(context: CallbackContext):
    max_card_id = get_max_card_id()
    if not max_card_id:
        logging.error('notifier not started!')
        return
    logging.info('notifier started...')
    while True:
        await asyncio.sleep(RETRY_TIME)
        # await asyncio.sleep(15)
        connection = connect_fdb()
        if not connection:
            continue
        patients_data: list
        try:
            cursor = connection.cursor()
            cursor.execute(
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
                '       c.dspriem '
                'FROM main_card c '
                '   LEFT JOIN pacient p ON c.id_pac = p.id '
                '   LEFT JOIN priemnic otd ON c.id_priem = otd.id '
                f'WHERE c.id > {max_card_id} '
                # f'WHERE c.id > {max_card_id - 20} '
                'ORDER BY c.id'
            )
            patients_data = cursor.fetchall()
        except Exception as error:
            logging.error(f'FDB SQL query ERROR: {error}')
            continue
        if connection:
            if cursor:
                cursor.close()
            connection.close()
        if not patients_data:
            continue
        patients = list()
        for patient_data in patients_data:
            patients.append(Patient(*patient_data))
        max_card_id = patients[-1].card_id
        await send_messages(context.bot, patients)

# cursor = db.cursor()
#             cursor.execute('SELECT c.id,'
#                            '       c.d_in,'
#                            '       p.fm,'
#                            '       p.im,'
#                            '       p.ot,'
#                            '       p.dtr,'
#                            '       p.pol,'
#                            '       otd.short,'
#                            '       c.remzal,'
#                            '       c.dsnapr,'
#                            '       c.dspriem '
#                            'FROM main_card c '
#                            'LEFT JOIN pacient p on c.id_pac = p.id '
#                            'LEFT JOIN priemnic otd on c.id_priem = otd.id '
#                            'WHERE c.id_dvig = 10 '
#                            'ORDER BY c.d_in')
#                 patients_data = cursor.fetchall()
#                         except Exception as error:
#                             logging.error(f'FDB SQL query ERROR: {error}')
#                             continue
#                         if not patients_data:
#                             continue
#                         patients = list()
#                         for patient_data in patients_data:
#                             patients.append(Patient(*patient_data))
#                         message = 'Пациенты в приемном отделении:\n'
#                         for patient in patients:
#                             message += (
#                                 '```\n'
#                                 f'Дата поступления: {patient.get_admission_date()}\n'
#                                 f'Ф.И.О.: {patient.get_full_name()}\n'
#                                 f'Дата рождения: {patient.get_birthday()}\n'
#                                 f'Диагноз при поступлении: {patient.admission_diagnosis}\n'
#                                 '```\n'
#                             )
#                         await send_message(message)
