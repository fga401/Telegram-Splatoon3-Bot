import os.path

import telegram.ext
from telegram.ext import Defaults, ApplicationBuilder, CommandHandler, CallbackQueryHandler, PicklePersistence, PersistenceInput

import config
from bot.settings import start, settings, settings_button_add, SettingsButtonCallback
from bot.whitelist import WhitelistFilter


def run():
    defaults = Defaults(
        parse_mode=telegram.constants.ParseMode.MARKDOWN_V2
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
    whitelist_filter = WhitelistFilter(config.get(config.BOT_WHITELIST))

    application = ApplicationBuilder().token(config.get(config.BOT_TOKEN)).defaults(defaults).persistence(persistence).build()
    application.add_handler(CommandHandler('start', start, filters=whitelist_filter))
    application.add_handler(CommandHandler('settings', settings, filters=whitelist_filter))
    application.add_handler(CallbackQueryHandler(settings_button_add, pattern=SettingsButtonCallback.regexp))

    application.run_polling()
