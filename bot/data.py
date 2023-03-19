import datetime
import logging
from dataclasses import dataclass

from telegram.ext import ContextTypes, Application

import config

logger = logging.getLogger('bot.data')


class Consts:
    PersistJobStore = 'persist'


class BotData:
    NintendoAppVersion = 'NINTENDO_APP_VERSION'
    S3SVersion = 'S3S_VERSION'
    WebviewVersion = 'WEBVIEW_VERSION'
    GraphQLRequestMap = 'GRAPHQL_REQUEST_MAP'
    RegisteredUsers = 'REGISTERED_USERS'
    StageNames = 'STAGE_NAMES'
    WeaponNames = 'WEAPON_NAMES'
    RuleNames = 'RULE_NAMES'


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
    country: str = ''
    language: str = ''
    timezone: str = ''


@dataclass
class Rule:
    id: str
    name: str


@dataclass
class Stage:
    id: str
    name: str
    image_url: str


@dataclass
class Weapon:
    name: str
    image_url: str


@dataclass
class BattleSetting:
    rule: Rule
    stage: tuple[Stage, Stage]


@dataclass
class JobSetting:
    stage: Stage
    weapon: tuple[Weapon, Weapon, Weapon, Weapon]


@dataclass
class Schedule:
    start_time: datetime.datetime
    end_time: datetime.datetime


@dataclass
class BattleSchedule(Schedule):
    setting: BattleSetting


@dataclass
class JobSchedule(Schedule):
    setting: JobSetting


@dataclass
class Schedules:
    # TODO: bigRun
    # TODO: teamContest
    # TODO: fest
    regular: list[BattleSchedule]
    challenge: list[BattleSchedule]
    open: list[BattleSchedule]
    x: list[BattleSchedule]
    coop: list[JobSchedule]


async def _init_bot_data(context: ContextTypes.DEFAULT_TYPE):
    logger.info('Initialized bot data')
    context.bot_data.setdefault(BotData.NintendoAppVersion, config.get(config.NINTENDO_APP_VERSION))
    context.bot_data.setdefault(BotData.S3SVersion, config.get(config.NINTENDO_S3S_VERSION))
    context.bot_data.setdefault(BotData.WebviewVersion, config.get(config.NINTENDO_WEBVIEW_VERSION))
    context.bot_data.setdefault(BotData.GraphQLRequestMap, config.get(config.NINTENDO_GRAPHQL_REQUEST_MAP))
    context.bot_data.setdefault(BotData.RegisteredUsers, set())
    context.bot_data.setdefault(BotData.StageNames, dict())
    context.bot_data.setdefault(BotData.RuleNames, dict())
    context.bot_data.setdefault(BotData.WeaponNames, dict())


def init_bot_data(application: Application):
    application.job_queue.run_custom(
        _init_bot_data,
        job_kwargs={
            'run_date': datetime.datetime.utcnow(),
            'misfire_grace_time': None,
        })
