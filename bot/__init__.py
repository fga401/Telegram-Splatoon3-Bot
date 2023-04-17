import logging
import os.path
import sys

import telegram.ext
import telegram.request._httpxrequest
from telegram.ext import Defaults, ApplicationBuilder, PicklePersistence, PersistenceInput, AIORateLimiter

import config
from bot import profiles, start, jobs, data, nintendo, schedules, admin
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
        .rate_limiter(AIORateLimiter(max_retries=sys.maxsize))
        .build()
    )
    application.add_handlers(start.handlers)
    application.add_handlers(nintendo.handlers)

    data.init_bot_data(application)

    profiles.init_profile(application)
    admin.init_admin(application)

    jobs.init_jobs(application)
    schedules.init_schedules(application)

    # disable job queue logging
    logging.getLogger("apscheduler.scheduler").disabled = True
    application.run_polling()
