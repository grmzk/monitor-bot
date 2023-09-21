import logging
from dataclasses import dataclass

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


@dataclass
class User:
    id: int
    family: str
    name: str
    surname: str
    department: str
    phone: str
    chat_id: int
    notification_level: int

    def get_full_name(self) -> str:
        return f'{self.family} {self.name} {self.surname}'


def connect_psql():
    try:
        connection = psycopg2.connect(host='93.115.19.207',
                                      port=5432,
                                      database='monitor_bot',
                                      user='monitor_bot',
                                      password='pCacZt73r0PLFWoO')
        connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    except psycopg2.Error as error:
        logging.error(f'PSQL connect ERROR: {error}')
        return None
    return connection


def set_notification_level(chat_id, notification_level):
    connection = connect_psql()
    if not connection:
        return False
    try:
        cursor = connection.cursor()
        cursor.execute('UPDATE users '
                       f'SET notification_level = {notification_level} '
                       f'WHERE chat_id = {chat_id}')
        connection.commit()
    except psycopg2.Error as error:
        logging.error(f'PSQL query ERROR: {error}')
        return False
    if connection:
        if cursor:
            cursor.close()
        connection.close()
    return True


def get_users():
    connection = connect_psql()
    if not connection:
        return None
    try:
        cursor = connection.cursor()
        cursor.execute('SELECT users.id, '
                       '       users.family, '
                       '       users.name, '
                       '       users.surname, '
                       '       departments.name, '
                       '       users.phone, '
                       '       users.chat_id, '
                       '       users.notification_level '
                       'FROM users '
                       '    JOIN departments '
                       '        on users.department_id = departments.id')
        users_data = cursor.fetchall()
    except psycopg2.Error as error:
        logging.error(f'PSQL query ERROR: {error}')
        return None
    if connection:
        if cursor:
            cursor.close()
        connection.close()
    if not users_data:
        logging.warning('PSQL users table is empty!')
        return None
    users = list()
    for user_data in users_data:
        users.append(User(*user_data))
    return users
