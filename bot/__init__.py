import os.path

import telegram.ext
import telegram.request._httpxrequest
from telegram.ext import Defaults, ApplicationBuilder, PicklePersistence, PersistenceInput

import config
from bot import profiles, start, nintendo, data
from bot.utils import BackoffRetryRequest


def run():
    defaults = Defaults(
        parse_mode=telegram.constants.ParseMode.HTML
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
    request = BackoffRetryRequest()

    application = ApplicationBuilder().token(config.get(config.BOT_TOKEN)).defaults(defaults).persistence(persistence).request(request).get_updates_request(request).build()
    application.add_handlers(start.handlers)
    application.add_handlers(profiles.handlers)

    application.job_queue.run_once(data.init_bot_data, when=0)
    application.job_queue.run_repeating(nintendo.update_nsoapp_version_job, first=10, interval=config.get(config.NINTENDO_APP_VERSION_UPDATE_INTERVAL))
    application.job_queue.run_repeating(nintendo.update_s3s_version_job, first=10, interval=config.get(config.NINTENDO_APP_VERSION_UPDATE_INTERVAL))
    application.job_queue.run_repeating(nintendo.update_webview_version_job, first=10, interval=config.get(config.NINTENDO_WEBVIEW_VERSION_UPDATE_INTERVAL))
    application.run_polling()
