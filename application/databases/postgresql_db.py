import logging
import os
from typing import Union

import psycopg2
from dotenv import load_dotenv
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

load_dotenv()

PG_HOST = os.getenv('PG_HOST')
PG_PORT = int(os.getenv('PG_PORT'))
PG_DATABASE = os.getenv('POSTGRES_DB')
PG_USER = os.getenv('POSTGRES_USER')
PG_PASSWORD = os.getenv('POSTGRES_PASSWORD')


def connect_psql():
    try:
        connection = psycopg2.connect(host=PG_HOST,
                                      port=PG_PORT,
                                      database=PG_DATABASE,
                                      user=PG_USER,
                                      password=PG_PASSWORD)
        connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    except psycopg2.Error as error:
        logging.error(f'PG CONNECT: {error}')
        return None
    return connection


def pg_select_data(select_query: str,
                   variables: Union[list, None] = None) -> Union[list, None]:
    connection = connect_psql()
    if not connection:
        return None
    try:
        cursor = connection.cursor()
        cursor.execute(select_query, vars=variables)
        data = cursor.fetchall()
    except psycopg2.Error as error:
        logging.error(f'PG QUERY: {error}')
        return None
    if connection:
        cursor.close()
        connection.close()
    return data


def pg_write_data(write_query: str,
                  variables: Union[list, None] = None) -> Union[int, bool]:
    connection = connect_psql()
    if not connection:
        return False
    try:
        cursor = connection.cursor()
        cursor.execute(write_query + ' RETURNING id', vars=variables)
        query_id = cursor.fetchone()[0]
    except psycopg2.Error as error:
        logging.error(f'PG QUERY: {error}')
        return False
    if connection:
        cursor.close()
        connection.close()
    return query_id
