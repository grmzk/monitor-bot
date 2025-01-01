import logging
import os
import re
from dataclasses import dataclass
from typing import Dict, List, Union

from dotenv import load_dotenv

from databases.postgresql_db import pg_select_data, pg_write_data

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
    admin: bool = False
    id: int = 0

    def get_full_name(self) -> str:
        return f'{self.family} {self.name} {self.surname}'

    def get_admission_department(self) -> str:
        pattern_surgery = re.compile(r'^.* ХИРУРГИЯ$')
        pattern_therapy = re.compile(r'^.* ТЕРАПИЯ$')
        if pattern_surgery.match(self.department):
            return 'ХИРУРГИЯ'
        if pattern_therapy.match(self.department):
            return 'ТЕРАПИЯ'
        return self.department


def set_notification_level(chat_id: int, notification_level: int) -> bool:
    write_query = (
        f"UPDATE {USERS_TABLE} "
        "SET notification_level = %s "
        "WHERE chat_id = %s"
    )
    return pg_write_data(write_query, [notification_level, chat_id])


def set_department(chat_id: int, department_id: int) -> bool:
    write_query = (
        f"UPDATE {USERS_TABLE} "
        "SET department_id = %s "
        "WHERE chat_id = %s"
    )
    return pg_write_data(write_query, [department_id, chat_id])


def set_enable(chat_id: int) -> bool:
    write_query = (
        f"UPDATE {USERS_TABLE} "
        "SET enable = true "
        "WHERE chat_id = %s"
    )
    return pg_write_data(write_query, [chat_id])


def insert_user(user: User) -> bool:
    write_query = (
        f"INSERT INTO {USERS_TABLE} "
        "   (family, name, surname, department_id, phone, chat_id, "
        "   notification_level, telegram_full_name, enable, admin) "
        "VALUES "
        "   (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
    )
    return pg_write_data(
        write_query,
        [
            user.family,
            user.name,
            user.surname,
            user.department,
            user.phone,
            user.chat_id,
            user.notification_level,
            user.telegram_full_name,
            user.enable,
            user.admin
        ]
    )


def get_users(enabled: Union[bool, None] = None,
              admin: Union[bool, None] = None) -> Union[List[User], None]:
    where = ''
    variables = None
    if (enabled is not None
            and admin is not None):
        where = (
            f"WHERE ({USERS_TABLE}.enable = %s) "
            f"  AND ({USERS_TABLE}.admin = %s) "
        )
        variables = [enabled, admin]
    else:
        if enabled is not None:
            where = f"WHERE ({USERS_TABLE}.enable = %s) "
            variables = [enabled]
        elif admin is not None:
            where = f"WHERE ({USERS_TABLE}.admin = %s) "
            variables = [admin]
    select_query = (
        f"SELECT {USERS_TABLE}.family, "
        f"       {USERS_TABLE}.name, "
        f"       {USERS_TABLE}.surname, "
        "        departments.name, "
        f"       {USERS_TABLE}.phone, "
        f"       {USERS_TABLE}.chat_id, "
        f"       {USERS_TABLE}.telegram_full_name, "
        f"       {USERS_TABLE}.notification_level, "
        f"       {USERS_TABLE}.enable, "
        f"       {USERS_TABLE}.admin, "
        f"       {USERS_TABLE}.id "
        f"FROM {USERS_TABLE} "
        f"  JOIN departments ON {USERS_TABLE}.department_id = departments.id "
        f"{where}"
        f"ORDER BY {USERS_TABLE}.id"
    )
    users_data = pg_select_data(select_query, variables)
    if not users_data:
        logging.warning(f'PG {USERS_TABLE} table is empty!')
        return None
    users = list()
    for user_data in users_data:
        users.append(User(*user_data))
    return users


def get_enabled_users() -> List[User]:
    return get_users(enabled=True)


def get_admin_users() -> List[User]:
    return get_users(admin=True)


def get_user(chat_id: int) -> Union[User, None]:
    select_query = (
        f"SELECT {USERS_TABLE}.family, "
        f"       {USERS_TABLE}.name, "
        f"       {USERS_TABLE}.surname, "
        "        departments.name, "
        f"       {USERS_TABLE}.phone, "
        f"       {USERS_TABLE}.chat_id, "
        f"       {USERS_TABLE}.telegram_full_name, "
        f"       {USERS_TABLE}.notification_level, "
        f"       {USERS_TABLE}.enable, "
        f"       {USERS_TABLE}.admin, "
        f"       {USERS_TABLE}.id "
        f"FROM {USERS_TABLE} "
        f"  JOIN departments ON {USERS_TABLE}.department_id = departments.id "
        f"WHERE {USERS_TABLE}.chat_id = %s "
    )
    user_data = pg_select_data(select_query, [chat_id])
    if not user_data:
        return None
    return User(*user_data[0])


def get_departments() -> Union[Dict[int, str], None]:
    select_query = (
        "SELECT id, name "
        "FROM departments "
        "ORDER BY id"
    )
    departments_data = pg_select_data(select_query)
    if not departments_data:
        logging.warning('PG departments table is empty!')
        return None
    departments = dict()
    for department_data in departments_data:
        departments[int(department_data[0])] = department_data[1].upper()
    return departments
