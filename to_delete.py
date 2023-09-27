import logging
import os
from typing import List

from dotenv import load_dotenv
from telegram import Bot, Message
from telegram.error import BadRequest

from postgresql_db import pg_select_data, pg_write_data

load_dotenv()

TO_DELETE_TABLE = 'to_delete'
DEVELOP = int(os.getenv('DEVELOP'))
if DEVELOP:
    TO_DELETE_TABLE = 'to_delete_develop'


class ToDelete:
    to_delete_id: int
    chat_id: int
    messages_id: List[int]

    def __init__(self, to_delete_id: int = None, chat_id: int = None):
        if to_delete_id and chat_id:
            logging.error('ToDelete: Two initial arguments are '
                          'specified together, but one was expected')
            return
        if not (to_delete_id or chat_id):
            logging.error('ToDelete: Initial argument is not specified, '
                          'one was expected')
            return
        self.messages_id = list()
        if to_delete_id:
            select_query = ('SELECT id, chat_id, messages_id '
                            f'FROM {TO_DELETE_TABLE} '
                            'WHERE id = %s')
            data = pg_select_data(select_query, [to_delete_id])[0]
            self.to_delete_id, self.chat_id, self.messages_id = data
        elif chat_id:
            write_query = (f'INSERT INTO {TO_DELETE_TABLE} (chat_id) '
                           'VALUES (%s)')
            self.to_delete_id = pg_write_data(write_query, [chat_id])
            self.chat_id = chat_id

    def add(self, message: Message) -> Message:
        if message.message_id in self.messages_id:
            logging.error('ToDelete: message already added')
            return message
        if message.chat_id != self.chat_id:
            logging.error('ToDelete: incorrect chat_id')
            return message
        self.messages_id.append(message.message_id)
        return message

    def save(self) -> int:
        write_query = (f'UPDATE {TO_DELETE_TABLE} '
                       'SET messages_id = %s '
                       'WHERE id = %s')
        return pg_write_data(write_query,
                             [self.messages_id, self.to_delete_id])

    async def delete(self, bot: Bot):
        for message_id in self.messages_id:
            try:
                await bot.delete_message(self.chat_id, message_id)
            except BadRequest as error:
                if error.message == 'Message to delete not found':
                    logging.warning('ToDelete: Message for delete not found')
                else:
                    raise error
        self.messages_id.clear()

    async def final_delete(self, bot: Bot) -> int:
        await self.delete(bot)
        write_query = ('DELETE '
                       f'FROM {TO_DELETE_TABLE} '
                       'WHERE id = %s')
        return pg_write_data(write_query, [self.to_delete_id])

    def __str__(self) -> str:
        return str([self.to_delete_id, self.chat_id, self.messages_id])
