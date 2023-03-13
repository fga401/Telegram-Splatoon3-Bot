import os.path

import telegram.ext
from telegram.ext import Defaults, ApplicationBuilder, PicklePersistence, PersistenceInput

import config
from bot import profiles, start
from bot.whitelist import WhitelistFilter


def run():
    defaults = Defaults(
        parse_mode=telegram.constants.ParseMode.HTML
    )
    persistence = PicklePersistence(
        filepath=os.path.join('data', 'data'),
        store_data=PersistenceInput(
            user_data=True,
            bot_data=False,
            chat_data=False,
            callback_data=False,
        )
    )

    application = ApplicationBuilder().token(config.get(config.BOT_TOKEN)).defaults(defaults).persistence(persistence).build()
    application.add_handlers(start.handlers)
    application.add_handlers(profiles.handlers)

    application.run_polling()
