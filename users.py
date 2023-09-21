import logging
import os
from dataclasses import dataclass

import psycopg2
from dotenv import load_dotenv
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

load_dotenv()

PG_HOST = os.getenv('PG_HOST')
PG_PORT = int(os.getenv('PG_PORT'))
PG_DATABASE = os.getenv('PG_DATABASE')
PG_USER = os.getenv('PG_USER')
PG_PASSWORD = os.getenv('PG_PASSWORD')
DEVELOP = int(os.getenv('DEVELOP'))


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
        connection = psycopg2.connect(host=PG_HOST,
                                      port=PG_PORT,
                                      database=PG_DATABASE,
                                      user=PG_USER,
                                      password=PG_PASSWORD)
        connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    except psycopg2.Error as error:
        logging.error(f'PG connect ERROR: {error}')
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
        logging.error(f'PG query ERROR: {error}')
        return False
    if connection:
        cursor.close()
        connection.close()
    return True


def get_users():
    connection = connect_psql()
    if not connection:
        return None
    try:
        cursor = connection.cursor()
        develop_where = str()
        if DEVELOP:
            develop_where = 'WHERE users.id = 1'
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
                       '        on users.department_id = departments.id '
                       f'{develop_where} '
                       'ORDER BY users.id')
        users_data = cursor.fetchall()
    except psycopg2.Error as error:
        logging.error(f'PG query ERROR: {error}')
        return None
    if connection:
        cursor.close()
        connection.close()
    if not users_data:
        logging.warning('PG users table is empty!')
        return None
    users = list()
    for user_data in users_data:
        users.append(User(*user_data))
    return users
