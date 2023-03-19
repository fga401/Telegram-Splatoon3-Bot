import os.path
import sqlite3

import telegram.ext
import telegram.request._httpxrequest
from telegram.ext import Defaults, ApplicationBuilder, PicklePersistence, PersistenceInput

import config
from bot import profiles, start, jobs, data, nintendo
from bot.data import Consts
from bot.utils import BackoffRetryRequest


def run():
    defaults = Defaults(
        parse_mode=telegram.constants.ParseMode.HTML,
    )
    persistence = PicklePersistence(
        filepath=os.path.join('data', 'data'),
        store_data=PersistenceInput(
            user_data=True,
            bot_data=True,
            chat_data=False,
            callback_data=False,
        )
    )
    request = BackoffRetryRequest(connection_pool_size=256)
    application = (
        ApplicationBuilder()
        .token(config.get(config.BOT_TOKEN))
        .defaults(defaults)
        .persistence(persistence)
        .get_updates_request(request)
        .request(request)
        .build()
    )
    application.add_handlers(start.handlers)
    application.add_handlers(nintendo.handlers)

    profiles.init_profile(application)
    data.init_bot_data(application)
    jobs.init_jobs(application)

    application.run_polling()
