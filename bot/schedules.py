import asyncio
import datetime
import json
import logging

import cv2
import numpy as np
from telegram.ext import ContextTypes

import config
from bot.data import Schedules, BattleSchedule, BattleSetting, JobSchedule, JobSetting, Rule, Stage, Weapon, BotData, Profile
from bot.nintendo import download_image

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


def battle_key(battle_stages: tuple[str, str]) -> str:
    return f'{battle_stages[0]} {battle_stages[1]}'


async def upload_battle_image(battle_stages: tuple[str, str], context: ContextTypes.DEFAULT_TYPE):
    stage_cache: dict[str, bytes] = context.bot_data[BotData.StageImageIDs]
    battle_cache: dict[str, str] = context.bot_data[BotData.BattleImageIDs]

    first_buf = stage_cache[battle_stages[0]]
    second_buf = stage_cache[battle_stages[1]]

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
    battle_stages = list({(b.setting.stage[0].id, b.setting.stage[1].id) for b in schedules.regular + schedules.challenge + schedules.open + schedules.x})
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