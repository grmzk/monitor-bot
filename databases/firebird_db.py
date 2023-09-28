import logging
import os
from typing import Union

import fdb
from dotenv import load_dotenv
from fdb.fbcore import (ISOLATION_LEVEL_READ_COMMITED_RO, Connection,
                        InternalError, isc_info_page_size, isc_info_version)

load_dotenv()

FB_DSN = os.getenv('FB_DSN')
FB_USER = os.getenv('FB_USER')
FB_PASSWORD = os.getenv('FB_PASSWORD')
FB_LIBRARY_NAME = os.getenv('FB_LIBRARY_NAME')


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
    except fdb.Error as error:
        logging.error(f'FB connect ERROR: {error}')
        return None
    return connection


def fb_select_data(select_query: str,
                   parameters: Union[list, None] = None) -> list:
    connection = connect_fdb()
    if not connection:
        return list()
    try:
        cursor = connection.cursor()
        cursor.execute(select_query, parameters=parameters)
        data = cursor.fetchall()
    except fdb.Error as error:
        logging.error(f'FB query ERROR: {error}')
        return list()
    if connection:
        cursor.close()
        connection.close()
        logging.info('FB query complete SUCCESS')
    return data
