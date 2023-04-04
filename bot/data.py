import datetime
import json
import logging
from dataclasses import dataclass

from telegram import User
from telegram.ext import ContextTypes, Application

import config
from locales import _

logger = logging.getLogger('bot.data')


class BotData:
    NintendoAppVersion = 'NINTENDO_APP_VERSION'
    S3SVersion = 'S3S_VERSION'
    WebviewVersion = 'WEBVIEW_VERSION'
    GraphQLRequestMap = 'GRAPHQL_REQUEST_MAP'
    RegisteredUsers = 'REGISTERED_USERS'

    StageImageIDs = "STAGE_IMAGE_IDS"
    BattleImageIDs = "BATTLE_IMAGE_IDS"
    JobImageIDs = "JOB_IMAGE_IDS"


class UserData:
    Profiles = 'PROFILES'
    Current = 'CURRENT'
    Pending = 'PENDING'
    Verifier = 'VERIFIER'
    MessageID_Name = 'MSG_ID_NAME'
    MessageID_Link = 'MSG_ID_LINK'
    MessageID_Timezone = 'MSG_ID_TZ'
    LastBattle = 'LAST_BATTLE'
    LastJob = 'LAST_JOB'


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
    tg_user: User = None


@dataclass
class Rule:
    id: str
    rule: str
    name: str

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return isinstance(other, Rule) and self.id == other.id


class RuleEnum:
    TurfWar = Rule(id='VnNSdWxlLTA=', rule='TURF_WAR', name='')
    Goal = Rule(id='VnNSdWxlLTM=', rule='GOAL', name='')
    Area = Rule(id='VnNSdWxlLTE=', rule='AREA', name='')
    Loft = Rule(id='VnNSdWxlLTI=', rule='LOFT', name='')
    Clam = Rule(id='VnNSdWxlLTQ=', rule='CLAM', name='')
    TriColor = Rule(id='VnNSdWxlLTU=', rule='TRI_COLOR', name='')


# placeholder
_('TurfWar')
_('Goal')
_('Area')
_('Loft')
_('Clam')


@dataclass
class Mode:
    id: str
    mode: str

    def __hash__(self):
        return hash((self.id, self.mode))

    def __eq__(self, other):
        return isinstance(other, Rule) and self.id == other.id and self.mode == other.mode


class ModeEnum:
    Regular = Mode(id='VnNNb2RlLTE=', mode='REGULAR')  # TODO
    Challenge = Mode(id='VnNNb2RlLTI=', mode='CHALLENGE')  # TODO
    Open = Mode(id='VnNNb2RlLTUx', mode='OPEN')  # TODO
    X = Mode(id='VnNNb2RlLTM=', mode='X_MATCH')
    Fest = Mode(id='', mode='FEST')
    FestOpen = Mode(id='VnNNb2RlLTY=', mode='FEST')
    FestChallenge = Mode(id='VnNNb2RlLTc=', mode='FEST')
    FestTriColor = Mode(id='VnNNb2RlLTg=', mode='FEST')
    Private = Mode(id='VnNNb2RlLTU=', mode='PRIVATE')

    @staticmethod
    def name(mode: Mode):
        if mode == ModeEnum.Regular:
            return 'Regular'
        elif mode == ModeEnum.Challenge:
            return 'Challenge'
        elif mode == ModeEnum.Open:
            return 'Open'
        elif mode == ModeEnum.X:
            return 'X'
        elif mode == ModeEnum.Fest:
            return 'Fest'
        elif mode == ModeEnum.FestOpen:
            return 'FestOpen'
        elif mode == ModeEnum.FestChallenge:
            return 'FestChallenge'
        elif mode == ModeEnum.FestTriColor:
            return 'FestTriColor'
        elif mode == ModeEnum.Private:
            return 'Private'


# placeholder
_('Regular')
_('Challenge')
_('Open')
_('X')
_('Fest')
_('FestOpen')
_('FestChallenge')
_('FestTriColor')
_('Private')


# _('Regular Battle')
# _('Anarchy Battle (Series)')
# _('Anarchy Battle (Open)')
# _('X Battle')
# _('Splatfest Battle')


@dataclass
class Stage:
    id: str
    name: str
    image_url: str

    def __eq__(self, other):
        return isinstance(other, Stage) and self.id == other.id


@dataclass
class Weapon:
    id: str
    name: str
    image_url: str


@dataclass
class BattleSetting:
    rule: Rule
    mode: Mode
    stage: tuple[Stage, Stage]


@dataclass
class JobSetting:
    stage: Stage
    weapons: tuple[Weapon, Weapon, Weapon, Weapon]


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
    regular: list[BattleSchedule]
    challenge: list[BattleSchedule]
    open: list[BattleSchedule]
    x: list[BattleSchedule]
    fest: list[BattleSchedule]
    coop: list[JobSchedule]


class ScheduleParser:
    @staticmethod
    def schedules(schedules: str) -> Schedules:
        data = json.loads(schedules)
        regular_schedules = [
            BattleSchedule(
                setting=BattleSetting(
                    rule=Rule(
                        id=node['regularMatchSetting']['vsRule']['id'],
                        rule=node['regularMatchSetting']['vsRule']['rule'],
                        name=node['regularMatchSetting']['vsRule']['name'],
                    ),
                    mode=ModeEnum.Regular,
                    stage=(
                        Stage(
                            id=node['regularMatchSetting']['vsStages'][0]['id'],
                            name=node['regularMatchSetting']['vsStages'][0]['name'],
                            image_url=node['regularMatchSetting']['vsStages'][0]['image']['url'],
                        ),
                        Stage(
                            id=node['regularMatchSetting']['vsStages'][1]['id'],
                            name=node['regularMatchSetting']['vsStages'][1]['name'],
                            image_url=node['regularMatchSetting']['vsStages'][1]['image']['url'],
                        ),
                    )
                ),
                start_time=datetime.datetime.fromisoformat(node['startTime']),
                end_time=datetime.datetime.fromisoformat(node['endTime']),
            )
            for node in data['data']['regularSchedules']['nodes'] if node['regularMatchSetting'] is not None
        ]
        challenge_schedules = [
            BattleSchedule(
                setting=BattleSetting(
                    rule=Rule(
                        id=node['bankaraMatchSettings'][0]['vsRule']['id'],
                        rule=node['bankaraMatchSettings'][0]['vsRule']['rule'],
                        name=node['bankaraMatchSettings'][0]['vsRule']['name'],
                    ),
                    mode=ModeEnum.Challenge,
                    stage=(
                        Stage(
                            id=node['bankaraMatchSettings'][0]['vsStages'][0]['id'],
                            name=node['bankaraMatchSettings'][0]['vsStages'][0]['name'],
                            image_url=node['bankaraMatchSettings'][0]['vsStages'][0]['image']['url'],
                        ),
                        Stage(
                            id=node['bankaraMatchSettings'][0]['vsStages'][1]['id'],
                            name=node['bankaraMatchSettings'][0]['vsStages'][1]['name'],
                            image_url=node['bankaraMatchSettings'][0]['vsStages'][1]['image']['url'],
                        ),
                    )
                ),
                start_time=datetime.datetime.fromisoformat(node['startTime']),
                end_time=datetime.datetime.fromisoformat(node['endTime']),
            )
            for node in data['data']['bankaraSchedules']['nodes'] if node['bankaraMatchSettings'] is not None
        ]
        open_schedules = [
            BattleSchedule(
                setting=BattleSetting(
                    rule=Rule(
                        id=node['bankaraMatchSettings'][1]['vsRule']['id'],
                        rule=node['bankaraMatchSettings'][1]['vsRule']['rule'],
                        name=node['bankaraMatchSettings'][1]['vsRule']['name'],
                    ),
                    mode=ModeEnum.Open,
                    stage=(
                        Stage(
                            id=node['bankaraMatchSettings'][1]['vsStages'][0]['id'],
                            name=node['bankaraMatchSettings'][1]['vsStages'][0]['name'],
                            image_url=node['bankaraMatchSettings'][1]['vsStages'][0]['image']['url'],
                        ),
                        Stage(
                            id=node['bankaraMatchSettings'][1]['vsStages'][1]['id'],
                            name=node['bankaraMatchSettings'][1]['vsStages'][1]['name'],
                            image_url=node['bankaraMatchSettings'][1]['vsStages'][1]['image']['url'],
                        ),
                    )
                ),
                start_time=datetime.datetime.fromisoformat(node['startTime']),
                end_time=datetime.datetime.fromisoformat(node['endTime']),
            )
            for node in data['data']['bankaraSchedules']['nodes'] if node['bankaraMatchSettings'] is not None
        ]
        x_schedules = [
            BattleSchedule(
                setting=BattleSetting(
                    rule=Rule(
                        id=node['xMatchSetting']['vsRule']['id'],
                        rule=node['xMatchSetting']['vsRule']['rule'],
                        name=node['xMatchSetting']['vsRule']['name'],
                    ),
                    mode=ModeEnum.X,
                    stage=(
                        Stage(
                            id=node['xMatchSetting']['vsStages'][0]['id'],
                            name=node['xMatchSetting']['vsStages'][0]['name'],
                            image_url=node['xMatchSetting']['vsStages'][0]['image']['url'],
                        ),
                        Stage(
                            id=node['xMatchSetting']['vsStages'][1]['id'],
                            name=node['xMatchSetting']['vsStages'][1]['name'],
                            image_url=node['xMatchSetting']['vsStages'][1]['image']['url'],
                        ),
                    ),
                ),
                start_time=datetime.datetime.fromisoformat(node['startTime']),
                end_time=datetime.datetime.fromisoformat(node['endTime']),
            )
            for node in data['data']['xSchedules']['nodes'] if node['xMatchSetting'] is not None
        ]
        fest_schedules = [
            BattleSchedule(
                setting=BattleSetting(
                    rule=Rule(
                        id=node['festMatchSetting']['vsRule']['id'],
                        rule=node['festMatchSetting']['vsRule']['rule'],
                        name=node['festMatchSetting']['vsRule']['name'],
                    ),
                    mode=ModeEnum.Fest,
                    stage=(
                        Stage(
                            id=node['festMatchSetting']['vsStages'][0]['id'],
                            name=node['festMatchSetting']['vsStages'][0]['name'],
                            image_url=node['festMatchSetting']['vsStages'][0]['image']['url'],
                        ),
                        Stage(
                            id=node['festMatchSetting']['vsStages'][1]['id'],
                            name=node['festMatchSetting']['vsStages'][1]['name'],
                            image_url=node['festMatchSetting']['vsStages'][1]['image']['url'],
                        ),
                    ),
                ),
                start_time=datetime.datetime.fromisoformat(node['startTime']),
                end_time=datetime.datetime.fromisoformat(node['endTime']),
            )
            for node in data['data']['festSchedules']['nodes'] if node['festMatchSetting'] is not None
        ]
        coop_schedules = [
            JobSchedule(
                setting=JobSetting(
                    stage=Stage(
                        id=node['setting']['coopStage']['id'],
                        name=node['setting']['coopStage']['name'],
                        image_url=node['setting']['coopStage']['thumbnailImage']['url'],
                    ),
                    weapons=(
                        Weapon(
                            id='',
                            name=node['setting']['weapons'][0]['name'],
                            image_url=node['setting']['weapons'][0]['image']['url'],
                        ),
                        Weapon(
                            id='',
                            name=node['setting']['weapons'][1]['name'],
                            image_url=node['setting']['weapons'][1]['image']['url'],
                        ),
                        Weapon(
                            id='',
                            name=node['setting']['weapons'][2]['name'],
                            image_url=node['setting']['weapons'][2]['image']['url'],
                        ),
                        Weapon(
                            id='',
                            name=node['setting']['weapons'][3]['name'],
                            image_url=node['setting']['weapons'][3]['image']['url'],
                        ),
                    )
                ),
                start_time=datetime.datetime.fromisoformat(node['startTime']),
                end_time=datetime.datetime.fromisoformat(node['endTime']),
            )
            for node in data['data']['coopGroupingSchedule']['regularSchedules']['nodes']
        ]

        return Schedules(
            regular=regular_schedules,
            challenge=challenge_schedules,
            open=open_schedules,
            x=x_schedules,
            fest=fest_schedules,
            coop=coop_schedules,
        )

    @staticmethod
    def stages(schedules: str) -> list[Stage]:
        data = json.loads(schedules)
        return [
            Stage(
                id=node['id'],
                name=node['name'],
                image_url=node['originalImage']['url']
            )
            for node in data['data']['vsStages']['nodes']
        ]


class Judgement:
    Win = "WIN"
    Lose = "Lose"


class Knockout(Judgement):
    Neither = "NEITHER"


@dataclass
class Gear:
    name: str
    primary: str
    additional: list[str]
    brand: str


@dataclass
class PlayerResult:
    kill: int
    death: int
    assist: int
    special: int


@dataclass
class Player:
    id: str
    name: str
    byname: str
    paint: int
    myself: bool
    weapon: Weapon
    result: PlayerResult
    head_gear: Gear
    clothing_gear: Gear
    shoes_gear: Gear


@dataclass
class BattlePlayer(Player):
    paint: int
    kill: int
    death: int
    assist: int
    special: int


@dataclass
class Battle:
    id: str
    rule: Rule
    mode: Mode
    stage: Stage
    judgement: Judgement
    knockout: Knockout


@dataclass
class Team:
    score: float
    tricolor_role: str
    judgement: Judgement
    players: list[Player]
    order: int


class Rank:
    Gold = 'GOLD'
    Silver = 'SILVER'


@dataclass
class Award:
    name: str
    rank: Rank


@dataclass
class BattleDetail(Battle):
    my_team: Team
    other_teams: list[Team]
    duration: int
    start_time: datetime.datetime
    awards: list[Award]


class BattleParser:
    @staticmethod
    def battle_histories(histories: str) -> list[Battle]:
        data = json.loads(histories)
        return [
            Battle(
                id=node['id'],
                rule=Rule(
                    id=node['vsRule']['id'],
                    rule=node['vsRule']['rule'],
                    name=node['vsRule']['name'],
                ),
                mode=Mode(
                    id=node['vsMode']['id'],
                    mode=node['vsMode']['mode'],
                ),
                stage=Stage(
                    id=node['vsStage']['id'],
                    name=node['vsStage']['name'],
                    image_url=node['vsStage']['image']['url'],
                ),
                judgement=node['judgement'],
                knockout=node['knockout'],
            )
            for node in data['data']['latestBattleHistories']['historyGroups']['nodes']
        ]

    @staticmethod
    def battle_detail(detail: str) -> BattleDetail:
        data = json.loads(detail)
        node = data['data']['vsHistoryDetail']
        return BattleDetail(
            id=node['id'],
            rule=Rule(
                id=node['vsRule']['id'],
                rule=node['vsRule']['rule'],
                name=node['vsRule']['name'],
            ),
            mode=Mode(
                id=node['vsMode']['id'],
                mode=node['vsMode']['mode'],
            ),
            stage=Stage(
                id=node['vsStage']['id'],
                name=node['vsStage']['name'],
                image_url=node['vsStage']['image']['url'],
            ),
            judgement=node['judgement'],
            knockout=node['knockout'],
            my_team=Team(

            )
        )


async def _init_bot_data(context: ContextTypes.DEFAULT_TYPE):
    logger.info('Initialized bot data')
    context.bot_data.setdefault(BotData.NintendoAppVersion, config.get(config.NINTENDO_APP_VERSION))
    context.bot_data.setdefault(BotData.S3SVersion, config.get(config.NINTENDO_S3S_VERSION))
    context.bot_data.setdefault(BotData.WebviewVersion, config.get(config.NINTENDO_WEBVIEW_VERSION))
    context.bot_data.setdefault(BotData.GraphQLRequestMap, config.get(config.NINTENDO_GRAPHQL_REQUEST_MAP))
    context.bot_data.setdefault(BotData.RegisteredUsers, set())
    context.bot_data.setdefault(BotData.StageImageIDs, dict())
    context.bot_data.setdefault(BotData.BattleImageIDs, dict())
    context.bot_data.setdefault(BotData.JobImageIDs, dict())


def init_bot_data(application: Application):
    application.job_queue.run_custom(
        _init_bot_data,
        job_kwargs={
            'run_date': datetime.datetime.utcnow(),
            'misfire_grace_time': None,
        })
