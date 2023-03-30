import asyncio
import datetime
import json
import logging
import re
from typing import Callable

import cv2
import numpy as np
import pytz
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, Application

import config
from bot.data import Schedules, BattleSchedule, BattleSetting, JobSchedule, JobSetting, Rule, Stage, Weapon, BotData, Profile, Mode
from bot.nintendo import download_image, stage_schedule
from bot.utils import whitelist_filter, current_profile, format_time
from locales import _

logger = logging.getLogger('bot.schedules')


class ScheduleParser:

    @staticmethod
    def schedules(data: str) -> Schedules:
        data = json.loads(data)
        regular_schedules = [
            BattleSchedule(
                setting=BattleSetting(
                    rule=Rule(
                        id=node['regularMatchSetting']['vsRule']['rule'],
                        name=node['regularMatchSetting']['vsRule']['name'],
                    ),
                    mode=Mode.Regular,
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
            for node in data['data']['regularSchedules']['nodes']
        ]
        challenge_schedules = [
            BattleSchedule(
                setting=BattleSetting(
                    rule=Rule(
                        id=node['bankaraMatchSettings'][0]['vsRule']['rule'],
                        name=node['bankaraMatchSettings'][0]['vsRule']['name'],
                    ),
                    mode=Mode.Challenge,
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
            for node in data['data']['bankaraSchedules']['nodes']
        ]
        open_schedules = [
            BattleSchedule(
                setting=BattleSetting(
                    rule=Rule(
                        id=node['bankaraMatchSettings'][1]['vsRule']['rule'],
                        name=node['bankaraMatchSettings'][1]['vsRule']['name'],
                    ),
                    mode=Mode.Open,
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
            for node in data['data']['bankaraSchedules']['nodes']
        ]
        x_schedules = [
            BattleSchedule(
                setting=BattleSetting(
                    rule=Rule(
                        id=node['xMatchSetting']['vsRule']['rule'],
                        name=node['xMatchSetting']['vsRule']['name'],
                    ),
                    mode=Mode.X,
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
            for node in data['data']['xSchedules']['nodes']
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
                            name=node['setting']['weapons'][0]['name'],
                            image_url=node['setting']['weapons'][0]['image']['url'],
                        ),
                        Weapon(
                            name=node['setting']['weapons'][1]['name'],
                            image_url=node['setting']['weapons'][1]['image']['url'],
                        ),
                        Weapon(
                            name=node['setting']['weapons'][2]['name'],
                            image_url=node['setting']['weapons'][2]['image']['url'],
                        ),
                        Weapon(
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
            coop=coop_schedules,
        )

    @staticmethod
    def stages(data: str) -> list[Stage]:
        data = json.loads(data)
        return [
            Stage(
                id=node['id'],
                name=node['name'],
                image_url=node['originalImage']['url']
            )
            for node in data['data']['vsStages']['nodes']
        ]


def bytes_to_image(data: bytes) -> np.ndarray:
    buf = np.asarray(bytearray(data), dtype=np.uint8)
    img = cv2.imdecode(buf, -1)
    return img


def battle_key(battle_stages: tuple[Stage, Stage]) -> str:
    return f'{battle_stages[0].id} {battle_stages[1].id}'


async def upload_battle_image(battle_stages: tuple[Stage, Stage], context: ContextTypes.DEFAULT_TYPE):
    stage_cache: dict[str, bytes] = context.bot_data[BotData.StageImageIDs]
    battle_cache: dict[str, str] = context.bot_data[BotData.BattleImageIDs]

    first_buf = stage_cache[battle_stages[0].id]
    second_buf = stage_cache[battle_stages[1].id]

    first_image = bytes_to_image(first_buf)
    second_image = bytes_to_image(second_buf)

    first_image = cv2.resize(first_image, (1280, 720))
    second_image = cv2.resize(second_image, (1280, 720))

    output = cv2.hconcat([first_image, second_image])
    buf: bytes = cv2.imencode('.jpg', output)[1].tobytes()
    message = await context.bot.send_photo(chat_id=config.get(config.BOT_STORAGE_CHANNEL), photo=buf)
    battle_cache[battle_key(battle_stages)] = message.photo[0].file_id


def job_key(job: JobSchedule) -> str:
    return f'{job.start_time.timestamp()}'


async def upload_job_image(job: JobSchedule, profile: Profile, context: ContextTypes.DEFAULT_TYPE):
    job_cache: dict[str, str] = context.bot_data[BotData.JobImageIDs]

    download_tasks = [download_image(profile, job.setting.stage.image_url)]
    for weapon in job.setting.weapons:
        download_tasks.append(download_image(profile, weapon.image_url))
    buffers = await asyncio.gather(*download_tasks)
    images = [bytes_to_image(buf) for buf in buffers]

    weapons = [cv2.resize(image, (360, 360)) for image in images[1:]]
    stage = cv2.resize(images[0], (1280, 720))
    weapons = cv2.vconcat([cv2.hconcat(weapons[:2]), cv2.hconcat(weapons[2:])])
    output = cv2.hconcat([stage, weapons])
    buf: bytes = cv2.imencode('.jpg', output)[1].tobytes()
    message = await context.bot.send_photo(chat_id=config.get(config.BOT_STORAGE_CHANNEL), photo=buf)
    job_cache[job_key(job)] = message.photo[0].file_id


async def update_schedule_image(data: str, profile: Profile, context: ContextTypes.DEFAULT_TYPE, force=False):
    stages = ScheduleParser.stages(data)
    stage_cache: dict[str, bytes] = context.bot_data[BotData.StageImageIDs]
    battle_cache: dict[str, str] = context.bot_data[BotData.BattleImageIDs]
    job_cache: dict[str, str] = context.bot_data[BotData.JobImageIDs]

    if force:
        stage_cache.clear()
        battle_cache.clear()
        job_cache.clear()

    download_tasks = []
    stage_ids = []
    for stage in stages:
        if stage.id not in stage_cache:
            stage_ids.append(stage.id)
            download_tasks.append(download_image(profile, stage.image_url))
    images = await asyncio.gather(*download_tasks)
    result = {stage_id: image_id for stage_id, image_id in zip(stage_ids, images)}
    stage_cache.update(result)

    schedules = ScheduleParser.schedules(data)
    # distinct stage
    battle_stages: list[tuple[Stage, Stage]] = list({(b.setting.stage[0].id, b.setting.stage[1].id): b.setting.stage for b in schedules.regular + schedules.challenge + schedules.open + schedules.x}.values())
    upload_battle_tasks = []
    for battle_stage in battle_stages:
        if battle_key(battle_stage) not in battle_cache:
            upload_battle_tasks.append(upload_battle_image(battle_stage, context))

    jobs = [job for job in schedules.coop]
    upload_job_tasks = []
    for job in jobs:
        if job_key(job) not in job_cache:
            upload_job_tasks.append(upload_job_image(job, profile, context))

    results = await asyncio.gather(*(upload_battle_tasks + upload_job_tasks), return_exceptions=True)
    error_cnt = 0
    for r in results:
        if isinstance(r, Exception):
            logger.error(f'Failed to upload image. error = {r}')
            error_cnt += 1
    logger.info(f'Updated schedules images. number = {len(results) - error_cnt}')


class QueryFilter:
    regexp = r'([rcox]+( [talgc]+)?)?( |$)(\d{1,2}( \d{0,2})?)?'
    __compiled = re.compile(regexp)

    @staticmethod
    def validate(args: list[str]) -> bool:
        text = ' '.join(args)
        return QueryFilter.__compiled.match(text) is not None

    @staticmethod
    def filter(args: list[str], schedules: Schedules, tz: datetime.tzinfo) -> Schedules:

        mode = set()
        rule = set()
        lowerbound = datetime.datetime.now()
        upperbound = datetime.datetime.now()
        alpha: list[str] = []
        digit: list[int] = []
        for arg in args:
            if arg.isalpha():
                alpha.append(arg.lower())
            else:
                digit.append(int(arg))

        if len(alpha) == 0:
            alpha.append('rcox')  # default mode
        if len(alpha) == 1:
            alpha.append('talgc')  # default rule
        if 'r' in alpha[0]:
            mode.add(Mode.Regular)
        if 'c' in alpha[0]:
            mode.add(Mode.Challenge)
        if 'o' in alpha[0]:
            mode.add(Mode.Open)
        if 'x' in alpha[0]:
            mode.add(Mode.X)

        if 't' in alpha[1]:
            rule.add('TURF_WAR')
        if 'a' in alpha[1]:  # AREA
            rule.add('AREA')
        if 'l' in alpha[1]:  # LOFT
            rule.add('LOFT')
        if 'g' in alpha[1]:  # GOAL
            rule.add('GOAL')
        if 'c' in alpha[1]:  # CLAM
            rule.add('CLAM')

        if len(digit) == 0:
            digit.append(2)  # default time
        if len(digit) == 1:
            N = max(digit[0], 1)
            lowerbound = datetime.datetime.now(pytz.UTC)
            upperbound = lowerbound + datetime.timedelta(hours=2 * (N - 1))
        if len(digit) == 2:
            if digit[1] < digit[0]:
                digit[1] += 24
            local = datetime.datetime.now(pytz.UTC).replace(microsecond=0, second=0, minute=0).astimezone(tz)
            start_offset = digit[0] - local.hour
            end_offset = digit[1] - local.hour
            utc = local.astimezone(pytz.UTC)
            lowerbound = utc + datetime.timedelta(hours=start_offset)
            upperbound = utc + datetime.timedelta(hours=end_offset)

        def _filter_schedule(schedule: BattleSchedule) -> bool:
            if schedule.setting.mode not in mode:
                return False
            if schedule.setting.rule.id not in rule:
                return False
            if not (lowerbound <= schedule.start_time < upperbound or lowerbound < schedule.end_time <= upperbound or (schedule.start_time <= lowerbound and upperbound <= schedule.end_time)):
                return False
            return True

        schedules.regular = list(filter(_filter_schedule, schedules.regular))
        schedules.challenge = list(filter(_filter_schedule, schedules.challenge))
        schedules.open = list(filter(_filter_schedule, schedules.open))
        schedules.x = list(filter(_filter_schedule, schedules.x))

        return schedules


async def output_battle_schedule(schedule: BattleSchedule, update: Update, context: ContextTypes.DEFAULT_TYPE):
    profile = current_profile(context)
    battle_cache: dict[str, str] = context.bot_data[BotData.BattleImageIDs]
    file_id = battle_cache[battle_key(schedule.setting.stage)]
    mode_text = ''
    if schedule.setting.mode == Mode.Regular:
        mode_text = _('Regular Battle')
    elif schedule.setting.mode == Mode.Challenge:
        mode_text = _('Anarchy Battle (Series)')
    elif schedule.setting.mode == Mode.Open:
        mode_text = _('Anarchy Battle (Open)')
    elif schedule.setting.mode == Mode.X:
        mode_text = _('X Battle')

    text = '\n'.join([
        _('Time: <code>{start_time}</code> ~ <code>{end_time}</code>'),
        _('Mode: {mode}'),
        _('Stage:\n  - {stage_1}\n  - {stage_2}'),
        _('Rule: {rule}'),
    ]).format(
        start_time=format_time(schedule.start_time.astimezone(pytz.timezone(profile.timezone))),
        end_time=format_time(schedule.end_time.astimezone(pytz.timezone(profile.timezone))),
        mode=mode_text,
        stage_1=schedule.setting.stage[0].name,
        stage_2=schedule.setting.stage[1].name,
        rule=schedule.setting.rule.name,
    )
    await update.message.reply_photo(photo=file_id, caption=text)


async def schedule_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    profile = current_profile(context)
    resp = await stage_schedule(profile)
    schedules = ScheduleParser.schedules(resp)

    args = context.args
    if not QueryFilter.validate(args):
        # TODO validate
        pass
    filtered_schedules = QueryFilter.filter(args, schedules, pytz.timezone(profile.timezone))
    ordered_schedules = sorted(filtered_schedules.x + filtered_schedules.open + filtered_schedules.challenge + filtered_schedules.regular, key=lambda x: x.end_time, reverse=True)
    for schedule in ordered_schedules:
        await output_battle_schedule(schedule, update, context)

# Parameters: [MODE] [RULE] [TIME]
# [RULE]
#   - r: Regular Battle
#   - c: Anarchy Battle (Series)
#   - o: Anarchy Battle (Open)
#   - x: X Battle
# [RULE]
#   - t: {}
#   - a: {}
#   - l: {}
#   - g: {}
#   - c: {}
# [TIME]
#   - N: Next N Schedules
#   - X Y: Schedules between X and Y
# Example:
#   - (None arguments): Default arguments. Next 2 schedules for all modes.
#   - o 20 24: Anarchy Battle (Open) schedules between 20:00 and 24:00
#   - x a 2: X Battle schedules with {} in next 4 hours if existing.
def __message_schedule_query_instruction(_: Callable[[str], str]):
    return _('  - format: <code>{regexp}</code>\n  - example: <code>o 20 24</code>, <code>MyProfile</code>').format(regexp=QueryFilter.regexp)


def init_schedules(application: Application):
    application.add_handlers(handlers)


handlers = [
    CommandHandler('schedules', schedule_query, filters=whitelist_filter),
    CommandHandler('coop_schedules', schedule_query, filters=whitelist_filter),
]
