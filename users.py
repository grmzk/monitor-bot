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
USERS_TABLE = 'users'
DEVELOP = int(os.getenv('DEVELOP'))

if DEVELOP:
    USERS_TABLE = 'users_develop'


@dataclass
class User:
    family: str
    name: str
    surname: str
    department: str
    phone: str
    chat_id: int
    telegram_full_name: str
    notification_level: int = 1
    enable: bool = False
    id: int = 0

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


def select_data(select_query: str) -> list:
    connection = connect_psql()
    if not connection:
        return list()
    try:
        cursor = connection.cursor()
        cursor.execute(select_query)
        data = cursor.fetchall()
    except psycopg2.Error as error:
        logging.error(f'PG query ERROR: {error}')
        return list()
    if connection:
        cursor.close()
        connection.close()
    return data


def write_data(write_query: str) -> bool:
    connection = connect_psql()
    if not connection:
        return False
    try:
        cursor = connection.cursor()
        cursor.execute(write_query)
        connection.commit()
    except psycopg2.Error as error:
        logging.error(f'PG query ERROR: {error}')
        return False
    if connection:
        cursor.close()
        connection.close()
    return True


def set_notification_level(chat_id: int, notification_level) -> bool:
    write_query = (
        f'UPDATE {USERS_TABLE} '
        f'SET notification_level = {notification_level} '
        f'WHERE chat_id = {chat_id}'
    )
    return write_data(write_query)


def set_enable(chat_id: int) -> bool:
    write_query = (
        f'UPDATE {USERS_TABLE} '
        f'SET enable = true '
        f'WHERE chat_id = {chat_id}'
    )
    return write_data(write_query)


def insert_user(user: User) -> bool:
    write_query = (
        f'INSERT INTO {USERS_TABLE} '
        '  (family, name, surname, department_id, phone, '
        '   chat_id, notification_level, telegram_full_name, enable) '
        'VALUES '
        f' (\'{user.family}\', \'{user.name}\', \'{user.surname}\', '
        f'  {user.department}, {user.phone}, {user.chat_id}, '
        f'  {user.notification_level}, \'{user.telegram_full_name}\', '
        f'  {user.enable})'
    )
    return write_data(write_query)


def get_users() -> list:
    select_query = (
        f'SELECT {USERS_TABLE}.family, '
        f'       {USERS_TABLE}.name, '
        f'       {USERS_TABLE}.surname, '
        '        departments.name, '
        f'       {USERS_TABLE}.phone, '
        f'       {USERS_TABLE}.chat_id, '
        f'       {USERS_TABLE}.telegram_full_name, '
        f'       {USERS_TABLE}.notification_level, '
        f'       {USERS_TABLE}.enable, '
        f'       {USERS_TABLE}.id '
        f'FROM {USERS_TABLE} '
        '    JOIN departments '
        f'        on {USERS_TABLE}.department_id '
        '            = departments.id '
        f'ORDER BY {USERS_TABLE}.id'
    )
    users_data = select_data(select_query)
    if not users_data:
        logging.warning(f'PG {USERS_TABLE} table is empty!')
        return list()
    users = list()
    for user_data in users_data:
        users.append(User(*user_data))
    return users


def get_enabled_users() -> list:
    users = get_users()
    enabled_users = list()
    for user in users:
        if user.enable:
            enabled_users.append(user)
    return enabled_users


def get_admin() -> User:
    users = get_users()
    return users[0]


def get_departments() -> dict:
    select_query = (
        'SELECT id, name '
        'FROM departments '
        'ORDER BY id'
    )
    departments_data = select_data(select_query)
    if not departments_data:
        logging.warning('PG departments table is empty!')
        return list()
    departments = dict()
    for department_data in departments_data:
        departments[department_data[1]] = int(department_data[0])
    return departments
