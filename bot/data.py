import datetime
import logging
from dataclasses import dataclass

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
    CoopImageIDs = "COOP_IMAGE_IDS"


class UserData:
    Profiles = 'PROFILES'
    Current = 'CURRENT'
    Pending = 'PENDING'
    Verifier = 'VERIFIER'
    MessageID_Name = 'MSG_ID_NAME'
    MessageID_Link = 'MSG_ID_LINK'
    MessageID_Timezone = 'MSG_ID_TZ'
    LastBattle = 'LAST_BATTLE'
    LastCoop = 'LAST_COOP'
    Monitoring = 'MONITORING'


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
        return isinstance(other, Mode) and self.id == other.id and self.mode == other.mode


class ModeEnum:
    Regular = Mode(id='VnNNb2RlLTE=', mode='REGULAR')
    Challenge = Mode(id='VnNNb2RlLTI=', mode='BANKARA')
    Open = Mode(id='VnNNb2RlLTUx', mode='BANKARA')
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
class CoopSetting:
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
class CoopSchedule(Schedule):
    setting: CoopSetting


@dataclass
class Schedules:
    # TODO: bigRun
    # TODO: teamContest
    regular: list[BattleSchedule]
    challenge: list[BattleSchedule]
    open: list[BattleSchedule]
    x: list[BattleSchedule]
    fest: list[BattleSchedule]
    coop: list[CoopSchedule]


class Judgement:
    Win = 'WIN'
    Lose = 'LOSE'
    DeemedLose = 'DEEMED_LOSE'


class Knockout(Judgement):
    Neither = 'NEITHER'


@dataclass
class Gear:
    name: str
    primary: str
    additional: list[str]
    brand: str


@dataclass
class BattlePlayerResult:
    kill: int
    death: int
    assist: int
    special: int


@dataclass
class Badge:
    id: str
    image_url: str


@dataclass
class Color:
    a: float
    b: float
    g: float
    r: float


@dataclass
class Background:
    id: str
    image_url: str
    text_color: Color


@dataclass
class Nameplate:
    background: Background
    badges: list[Badge | None]


@dataclass
class Player:
    id: str
    name: str
    byname: str
    name_id: str
    nameplate: Nameplate


@dataclass
class BattlePlayer(Player):
    myself: bool
    paint: int
    weapon: Weapon
    result: BattlePlayerResult
    head_gear: Gear
    clothing_gear: Gear
    shoes_gear: Gear


@dataclass
class Battle:
    id: str
    rule: Rule
    mode: Mode
    stage: Stage
    judgement: str
    knockout: str


@dataclass
class Team:
    score: float | int
    tricolor_role: str
    judgement: str
    players: list[BattlePlayer]
    order: int


class Rank:
    Gold = 'GOLD'
    Silver = 'SILVER'


@dataclass
class Award:
    name: str
    rank: str


@dataclass
class BattleDetail(Battle):
    my_team: Team
    other_teams: list[Team]
    duration: int
    start_time: datetime.datetime
    awards: list[Award]


class Diff:
    Keep = 'KEEP'
    Up = 'UP'
    Down = 'DOWN'


@dataclass
class Boss:
    id: str
    name: str
    image_url: str


@dataclass
class BossResult:
    boss: Boss
    defeat_boss: bool


@dataclass
class Coop:
    id: str
    after_grade_name: str
    after_grade_point: int
    grade_point_diff: str | None
    stage: Stage
    weapons: list[Weapon]
    boss: BossResult

    @property
    def clear(self) -> bool:
        return self.grade_point_diff == Diff.Up


@dataclass
class Uniform:
    id: str
    name: str
    image_url: str


@dataclass
class CoopPlayer(Player):
    uniform: Uniform


@dataclass
class SpecialWeapon:
    id: str
    weapon_id: int
    name: str
    image_url: str


@dataclass
class CoopPlayerResult:
    player: CoopPlayer
    weapons: list[Weapon]
    special_weapon: SpecialWeapon
    defeat_enemy_count: int
    deliver_count: int
    golden_assist_count: int
    golden_deliver_count: int
    rescue_count: int
    rescued_count: int


@dataclass
class EventWave:
    id: str
    name: str


@dataclass
class WaveResult:
    wave_number: int
    water_level: int
    event_wave: EventWave
    deliver_norm: int
    golden_pop_count: int
    team_deliver_count: int
    special_weapons: list[SpecialWeapon]


@dataclass
class Enemy:
    id: str
    name: str
    image_url: str


@dataclass
class EnemyResult:
    defeat_count: int
    team_defeat_count: int
    pop_count: int
    enemy: Enemy


@dataclass
class ScaleResult:
    gold: int
    silver: int
    bronze: int


@dataclass
class CoopDetail(Coop):
    result_wave: int
    my_result: CoopPlayerResult
    member_results: list[CoopPlayerResult]
    wave_results: list[WaveResult]
    enemy_results: list[EnemyResult]
    start_time: datetime.datetime
    rule: str
    danger: float
    smell: int
    scale: ScaleResult
    job_point: int
    job_score: int
    job_rate: float
    job_bonus: int

    @property
    def clear(self) -> bool:
        return self.result_wave == 0


class CommonParser:
    @staticmethod
    def badge(node) -> Badge | None:
        if node is None:
            return None
        return Badge(
            id=node['id'],
            image_url=node['image']['url'],
        )

    @staticmethod
    def nameplate(node) -> Nameplate:
        return Nameplate(
            background=Background(
                id=node['background']['id'],
                image_url=node['background']['image']['url'],
                text_color=Color(
                    a=node['background']['textColor']['a'],
                    b=node['background']['textColor']['b'],
                    g=node['background']['textColor']['g'],
                    r=node['background']['textColor']['r'],
                ),
            ),
            badges=[
                CommonParser.badge(badge)
                for badge in node['badges']
            ]
        )

    @staticmethod
    def weapon(node) -> Weapon:
        return Weapon(
            id=node.get('id', ''),
            name=node['name'],
            image_url=node['image']['url'],
        )

    @staticmethod
    def stage(node, image_name='image') -> Stage:
        if image_name is not None:
            image_url = node[image_name]['url']
        else:
            image_url = ''
        return Stage(
            id=node.get('id', ''),
            name=node['name'],
            image_url=image_url,
        )

    @staticmethod
    def rule(node) -> Rule:
        return Rule(
            id=node['id'],
            rule=node.get('rule', ''),
            name=node['name'],
        )

    @staticmethod
    def mode(node) -> Mode:
        return Mode(
            id=node['id'],
            mode=node['mode'],
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
    context.bot_data.setdefault(BotData.CoopImageIDs, dict())


def init_bot_data(application: Application):
    application.job_queue.run_custom(
        _init_bot_data,
        job_kwargs={
            'run_date': datetime.datetime.utcnow(),
            'misfire_grace_time': None,
        })
