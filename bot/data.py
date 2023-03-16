from dataclasses import dataclass

from telegram.ext import ContextTypes

import config


class BotData:
    NintendoAppVersion = 'NINTENDO_APP_VERSION'
    S3SVersion = 'S3S_VERSION'
    WebviewVersion = 'WEBVIEW_VERSION'


class UserData:
    Profiles = 'PROFILES'
    Current = 'CURRENT'
    Pending = 'PENDING'
    Verifier = 'VERIFIER'
    MessageID_Name = 'MSG_ID_NAME'
    MessageID_Link = 'MSG_ID_LINK'
    MessageID_Timezone = 'MSG_ID_TZ'


@dataclass
class Profile:
    id: int = 0
    name: str = ''
    account_name: str = ''
    session_token: str = ''
    gtoken: str = ''
    bullet_token: str = ''
    language: str = ''
    timezone: str = ''


def init_bot_data(context: ContextTypes.DEFAULT_TYPE):
    context.bot_data.setdefault(BotData.NintendoAppVersion, config.get(config.NINTENDO_APP_VERSION_FALLBACK))
    context.bot_data.setdefault(BotData.S3SVersion, config.get(config.NINTENDO_S3S_FALLBACK))
    context.bot_data.setdefault(BotData.WebviewVersion, config.get(config.NINTENDO_WEBVIEW_VERSION_FALLBACK))
