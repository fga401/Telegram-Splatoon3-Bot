import asyncio
import datetime
import logging
import re
from typing import Callable

import cv2
import numpy as np
import pytz
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, Application

import config
from bot.data import Schedules, BattleSchedule, JobSchedule, Stage, BotData, Profile, ModeEnum, ScheduleParser, RuleEnum
from bot.nintendo import download_image, stage_schedule
from bot.utils import whitelist_filter, current_profile, format_schedule_time
from locales import _

logger = logging.getLogger('bot.schedules')


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
    battle_stages: list[tuple[Stage, Stage]] = list({(b.setting.stage[0].id, b.setting.stage[1].id): b.setting.stage for b in schedules.regular + schedules.challenge + schedules.open + schedules.x + schedules.fest}.values())
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


class BattleQueryFilter:
    regexp = r'([rcox]+( [talgc]+)?)?( |$)(\d{1,2}( \d{0,2})?)?'
    __compiled = re.compile(regexp)

    @staticmethod
    def validate(args: list[str]) -> bool:
        text = ' '.join(args)
        return BattleQueryFilter.__compiled.match(text) is not None

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
            alpha.append('rcoxf')  # default mode
        if len(alpha) == 1:
            alpha.append('talgc')  # default rule
        if 'r' in alpha[0]:
            mode.add(ModeEnum.Regular)
        if 'c' in alpha[0]:
            mode.add(ModeEnum.Challenge)
        if 'o' in alpha[0]:
            mode.add(ModeEnum.Open)
        if 'x' in alpha[0]:
            mode.add(ModeEnum.X)
        if 'f' in alpha[0]:
            mode.add(ModeEnum.Fest)

        if 't' in alpha[1]:
            rule.add(RuleEnum.TurfWar)
        if 'a' in alpha[1]:
            rule.add(RuleEnum.Area)
        if 'l' in alpha[1]:
            rule.add(RuleEnum.Loft)
        if 'g' in alpha[1]:
            rule.add(RuleEnum.Goal)
        if 'c' in alpha[1]:
            rule.add(RuleEnum.Clam)

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
            if schedule.setting.rule not in rule:
                return False
            if not (lowerbound <= schedule.start_time < upperbound or lowerbound < schedule.end_time <= upperbound or (schedule.start_time <= lowerbound and upperbound <= schedule.end_time)):
                return False
            return True

        schedules.regular = list(filter(_filter_schedule, schedules.regular))
        schedules.challenge = list(filter(_filter_schedule, schedules.challenge))
        schedules.open = list(filter(_filter_schedule, schedules.open))
        schedules.x = list(filter(_filter_schedule, schedules.x))
        schedules.fest = list(filter(_filter_schedule, schedules.fest))
        return schedules


async def output_battle_schedule(schedule: BattleSchedule, update: Update, context: ContextTypes.DEFAULT_TYPE):
    profile = current_profile(context)
    battle_cache: dict[str, str] = context.bot_data[BotData.BattleImageIDs]
    file_id = battle_cache[battle_key(schedule.setting.stage)]
    text = '\n'.join([
        _('Time: <code>{start_time}</code> ~ <code>{end_time}</code>'),
        _('Mode: <code>{mode}</code>'),
        _('Stage:'),
        _('  - <code>{stage_1}</code>'),
        _('  - <code>{stage_2}</code>'),
        _('Rule: <code>{rule}</code>'),
    ]).format(
        start_time=format_schedule_time(schedule.start_time.astimezone(pytz.timezone(profile.timezone))),
        end_time=format_schedule_time(schedule.end_time.astimezone(pytz.timezone(profile.timezone))),
        mode=_(ModeEnum.name(schedule.setting.mode)),
        stage_1=schedule.setting.stage[0].name,
        stage_2=schedule.setting.stage[1].name,
        rule=schedule.setting.rule.name,
    )
    await update.message.reply_photo(photo=file_id, caption=text)


async def battle_schedule_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    profile = current_profile(context)
    args = context.args
    if not BattleQueryFilter.validate(args):
        await update.message.reply_text(text=_('Invalid query arguments.\n\n') + _message_battle_schedule_query_instruction(_))
        return
    resp = await stage_schedule(profile)
    schedules = ScheduleParser.schedules(resp)
    filtered_schedules = BattleQueryFilter.filter(args, schedules, pytz.timezone(profile.timezone))
    ordered_schedules = sorted(filtered_schedules.x + filtered_schedules.open + filtered_schedules.challenge + filtered_schedules.regular + filtered_schedules.fest, key=lambda x: x.end_time, reverse=True)
    if len(ordered_schedules) == 0:
        await update.message.reply_text(text=_("No matching schedules after filtering."))
    for schedule in ordered_schedules:
        await output_battle_schedule(schedule, update, context)


def _message_battle_schedule_query_instruction(_: Callable[[str], str]):
    return '\n'.join([
        _('Parameters: [MODE] [RULE] [TIME]'),
        _('[MODE]'),
        _('  - r: {regular}'),
        _('  - c: {challenge}'),
        _('  - o: {open}'),
        _('  - x: {x}'),
        _('  - fest: {fest}'),
        _('[RULE]'),
        _('  - t: {turf_war}'),
        _('  - a: {area}'),
        _('  - l: {loft}'),
        _('  - g: {goal}'),
        _('  - c: {clam}'),
        _('[TIME]'),
        _('  - N: Next N Schedules'),
        _('  - X Y: Schedules between X and Y'),
        _('Example:'),
        _('  - /schedules: Default arguments. Next 2 schedules for all modes.'),
        _('  - /schedules o 20 24: {open} schedules between 20:00 and 24:00.'),
        _('  - /schedules x a 2: {x} schedules with {area} in next 4 hours if existing.'),
    ]).format(
        regular=_(ModeEnum.Regular.name),
        challenge=_(ModeEnum.Challenge.name),
        open=_(ModeEnum.Open.name),
        x=_(ModeEnum.X.name),
        fest=_(ModeEnum.Fest.name),
        turf_war=_(RuleEnum.TurfWar.name),
        area=_(RuleEnum.Area.name),
        loft=_(RuleEnum.Loft.name),
        goal=_(RuleEnum.Goal.name),
        clam=_(RuleEnum.Clam.name),
    )


class JobQueryFilter:
    regexp = r'\d?'
    __compiled = re.compile(regexp)

    @staticmethod
    def validate(args: list[str]) -> bool:
        text = ' '.join(args)
        return JobQueryFilter.__compiled.match(text) is not None

    @staticmethod
    def filter(args: list[str], schedules: Schedules) -> Schedules:
        N = 2
        if len(args) > 0 and int(args[0]) > 0:
            N = int(args[0])
        schedules.coop = schedules.coop[:N]
        return schedules


async def output_job_schedule(schedule: JobSchedule, update: Update, context: ContextTypes.DEFAULT_TYPE):
    profile = current_profile(context)
    job_cache: dict[str, str] = context.bot_data[BotData.JobImageIDs]
    file_id = job_cache[job_key(schedule)]
    if (schedule.start_time - datetime.datetime.now().astimezone(pytz.UTC)).total_seconds() >= 0:
        second = int((schedule.start_time - datetime.datetime.now().astimezone(pytz.UTC)).total_seconds())
        time_text = _('Job will start in {time}.')
    else:
        second = int((schedule.end_time - datetime.datetime.now().astimezone(pytz.UTC)).total_seconds())
        time_text = _('Job will be over in {time}.')
    hour = second // 60 // 60
    minute = second // 60 % 60
    if hour == 0:
        time = _('{minute}m').format(minute=minute)
    else:
        time = _('{hour}h {minute}m').format(hour=hour, minute=minute)
    text = '\n'.join([
        _('Time: <code>{start_time}</code> ~ <code>{end_time}</code>'),
        _('Stage: <code>{stage}</code>'),
        _('Weapon:'),
        _('  - <code>{weapon_1}</code>'),
        _('  - <code>{weapon_2}</code>'),
        _('  - <code>{weapon_3}</code>'),
        _('  - <code>{weapon_4}</code>'),
        _('{remaining_text}')
    ]).format(
        start_time=format_schedule_time(schedule.start_time.astimezone(pytz.timezone(profile.timezone))),
        end_time=format_schedule_time(schedule.end_time.astimezone(pytz.timezone(profile.timezone))),
        stage=schedule.setting.stage.name,
        weapon_1=schedule.setting.weapons[0].name,
        weapon_2=schedule.setting.weapons[1].name,
        weapon_3=schedule.setting.weapons[2].name,
        weapon_4=schedule.setting.weapons[3].name,
        remaining_text=time_text.format(time=time)
    )
    await update.message.reply_photo(photo=file_id, caption=text)


async def job_schedule_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    profile = current_profile(context)
    args = context.args
    if not JobQueryFilter.validate(args):
        await update.message.reply_text(text=_('Invalid query arguments.\n\n') + _message_job_schedule_query_instruction(_))
        return
    resp = await stage_schedule(profile)
    schedules = ScheduleParser.schedules(resp)
    filtered_schedules = JobQueryFilter.filter(args, schedules)
    ordered_schedules = sorted(filtered_schedules.coop, key=lambda x: x.end_time, reverse=True)
    if len(ordered_schedules) == 0:
        await update.message.reply_text(text=_("No matching schedules after filtering."))
    for schedule in ordered_schedules:
        await output_job_schedule(schedule, update, context)


def _message_job_schedule_query_instruction(_: Callable[[str], str]):
    return '\n'.join([
        _('Parameters: [Next]'),
        _('[Next]'),
        _('  - N: Next N Schedules'),
        _('Example:'),
        _('  - /schedules: Default arguments. Next 2 schedules.'),
        _('  - /schedules 3: Next 3 schedules.'),
    ])


def init_schedules(application: Application):
    application.add_handlers(handlers)


handlers = [
    CommandHandler('schedules', battle_schedule_query, filters=whitelist_filter),
    CommandHandler('coop_schedules', job_schedule_query, filters=whitelist_filter),
]
