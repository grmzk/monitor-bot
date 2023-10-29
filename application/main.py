import logging
import os

from dotenv import load_dotenv
from telegram.ext import (Application, CallbackQueryHandler, CommandHandler,
                          ConversationHandler, MessageHandler, filters)

from callbacks.common_callbacks import (check_date_from_message,
                                        get_date_from_message)
from callbacks.department import change_department, choose_department
from callbacks.history import show_history
from callbacks.inpatients import (show_inpatients_today,
                                  show_inpatients_yesterday)
from callbacks.notifications import change_notifications, choose_notifications
from callbacks.processing import (show_processing_all, show_processing_own,
                                  show_processing_rean)
from callbacks.simple_commands import delete_messages, send_all, show_settings
from callbacks.start import (activate_user, start, start_department,
                             start_family, start_name, start_phone,
                             start_surname)
from callbacks.summary import show_summary_today, show_summary_yesterday
from classes.handlers import EndHandler
from constants import DEPARTMENT, FAMILY, NAME, PHONE, SHOW, SURNAME
from notifier import start_notifier

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(module)s] %(message)s',
)

TOKEN = os.getenv('TOKEN')
DEVELOP = int(os.getenv('DEVELOP'))
RETRY_TIME = 30
if DEVELOP:
    TOKEN = os.getenv('TOKEN_DEVELOP')
    RETRY_TIME = 30


def main() -> None:
    application = Application.builder().token(TOKEN).build()

    application.add_handler(ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            FAMILY: [MessageHandler(filters.TEXT, start_family)],
            NAME: [MessageHandler(filters.TEXT, start_name)],
            SURNAME: [MessageHandler(filters.TEXT, start_surname)],
            PHONE: [MessageHandler(filters.TEXT, start_phone)],
            DEPARTMENT: [MessageHandler(filters.TEXT, start_department)]
        },
        fallbacks=[EndHandler()]
    ))
    application.add_handler(ConversationHandler(
        entry_points=[CommandHandler('summary_date',
                                     get_date_from_message)],
        states={SHOW: [MessageHandler(filters.TEXT, check_date_from_message)]},
        fallbacks=[EndHandler()]
    ))
    application.add_handler(ConversationHandler(
        entry_points=[CommandHandler('inpatients_date',
                                     get_date_from_message)],
        states={SHOW: [MessageHandler(filters.TEXT, check_date_from_message)]},
        fallbacks=[EndHandler()]
    ))

    application.add_handler(CommandHandler('sendall',
                                           send_all))
    application.add_handler(CommandHandler('notifications',
                                           choose_notifications))
    application.add_handler(CommandHandler('summary_today',
                                           show_summary_today))
    application.add_handler(CommandHandler('summary_yesterday',
                                           show_summary_yesterday))
    application.add_handler(CommandHandler('department',
                                           choose_department))
    application.add_handler(CommandHandler('settings',
                                           show_settings))
    application.add_handler(CommandHandler('processing_all',
                                           show_processing_all))
    application.add_handler(CommandHandler('processing_own',
                                           show_processing_own))
    application.add_handler(CommandHandler('processing_rean',
                                           show_processing_rean))
    application.add_handler(CommandHandler('inpatients_today',
                                           show_inpatients_today))
    application.add_handler(CommandHandler('inpatients_yesterday',
                                           show_inpatients_yesterday))

    application.add_handler(CallbackQueryHandler(
        pattern=r'^notification \d$',
        callback=change_notifications)
    )
    application.add_handler(CallbackQueryHandler(pattern=r'^activate \d+$',
                                                 callback=activate_user))
    application.add_handler(CallbackQueryHandler(pattern=r'^delete \d+$',
                                                 callback=delete_messages))
    application.add_handler(CallbackQueryHandler(pattern=r'^department \d+$',
                                                 callback=change_department))
    application.add_handler(CallbackQueryHandler(pattern=r'^history \d+$',
                                                 callback=show_history))

    application.job_queue.run_repeating(start_notifier, RETRY_TIME)
    application.run_polling()


if __name__ == "__main__":
    main()
