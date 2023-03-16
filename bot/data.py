import logging

from telegram.ext import ContextTypes

import config


class BotData:
    NintendoAppVersion = 'NINTENDO_APP_VERSION'
    S3SVersion = 'S3S_VERSION'
    WebviewVersion = 'WEBVIEW_VERSION'


def init_bot_data(context: ContextTypes.DEFAULT_TYPE):
    context.bot_data.setdefault(BotData.NintendoAppVersion, config.get(config.NINTENDO_APP_VERSION_FALLBACK))
    context.bot_data.setdefault(BotData.S3SVersion, config.get(config.NINTENDO_S3S_FALLBACK))
    context.bot_data.setdefault(BotData.WebviewVersion, config.get(config.NINTENDO_WEBVIEW_VERSION_FALLBACK))
