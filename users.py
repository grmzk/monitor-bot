import logging
import os
from dataclasses import dataclass

from dotenv import load_dotenv

from postgresql_db import pg_select_data, pg_write_data

load_dotenv()

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


def set_notification_level(chat_id: int, notification_level: int) -> bool:
    write_query = (
        f'UPDATE {USERS_TABLE} '
        f'SET notification_level = {notification_level} '
        f'WHERE chat_id = {chat_id}'
    )
    return pg_write_data(write_query)


def set_department(chat_id: int, department_id: int) -> bool:
    write_query = (
        f'UPDATE {USERS_TABLE} '
        f'SET department_id = {department_id} '
        f'WHERE chat_id = {chat_id}'
    )
    return pg_write_data(write_query)


def set_enable(chat_id: int) -> bool:
    write_query = (
        f'UPDATE {USERS_TABLE} '
        f'SET enable = true '
        f'WHERE chat_id = {chat_id}'
    )
    return pg_write_data(write_query)


def insert_user(user: User) -> bool:
    write_query = (
        f'INSERT INTO {USERS_TABLE} '
        '  (family, name, surname, department_id, phone, '
        '   chat_id, notification_level, telegram_full_name, enable) '
        'VALUES '
        f' (\'{user.family}\', \'{user.name}\', \'{user.surname}\', '
        f'  {user.department}, \'{user.phone}\', {user.chat_id}, '
        f'  {user.notification_level}, \'{user.telegram_full_name}\', '
        f'  {user.enable})'
    )
    return pg_write_data(write_query)


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
    users_data = pg_select_data(select_query)
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


def get_user(chat_id: int) -> User:
    users = get_users()
    for user in users:
        if user.chat_id == chat_id:
            return user
    return None


def get_departments() -> dict:
    select_query = (
        'SELECT id, name '
        'FROM departments '
        'ORDER BY id'
    )
    departments_data = pg_select_data(select_query)
    if not departments_data:
        logging.warning('PG departments table is empty!')
        return list()
    departments = dict()
    for department_data in departments_data:
        departments[int(department_data[0])] = department_data[1]
    return departments
