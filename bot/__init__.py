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
    application.add_handlers(profiles.handlers)
    application.add_handlers(nintendo.handlers)

    application.job_queue.run_once(data.init_bot_data, when=0)
    application.job_queue.run_repeating(nintendo.update_nsoapp_version_job, first=10, interval=config.get(config.NINTENDO_APP_VERSION_UPDATE_INTERVAL))
    application.job_queue.run_repeating(nintendo.update_s3s_version_job, first=20, interval=config.get(config.NINTENDO_APP_VERSION_UPDATE_INTERVAL))
    application.job_queue.run_repeating(nintendo.update_webview_version_job, first=15, interval=config.get(config.NINTENDO_WEBVIEW_VERSION_UPDATE_INTERVAL))
    application.job_queue.run_repeating(nintendo.update_graphql_request_map_job, first=5, interval=config.get(config.NINTENDO_GRAPHQL_REQUEST_MAP_UPDATE_INTERVAL))
    application.run_polling()
