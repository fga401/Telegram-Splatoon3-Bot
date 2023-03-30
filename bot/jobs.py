import asyncio
import datetime
import logging

import cv2
from telegram.ext import ContextTypes, Application

import config
import nintendo.login
import nintendo.query
from bot.data import BotData, UserData, Profile
from bot.nintendo import update_token, home, stage_schedule, download_image
from bot.schedules import ScheduleParser, update_schedule_image
from nintendo.utils import ExpiredTokenError

logger = logging.getLogger('bot.job')


async def update_nso_version_job(context: ContextTypes.DEFAULT_TYPE):
    version = await nintendo.login.update_nsoapp_version()
    logger.info(f'Updated Nintendo Online App version. version = {version}')

    version = await nintendo.login.update_webview_version()
    logger.info(f'Updated webview version. version = {version}')

    graphql_request_map = await nintendo.query.update_graphql_query_map()
    logger.info(f'Updated GraphQL request map. map = {graphql_request_map}')

    version = await nintendo.login.update_s3s_version()
    logger.info(f'Updated s3s version. version = {version}')


async def keep_alive_job(context: ContextTypes.DEFAULT_TYPE):
    tasks = []
    registered_users: set = context.bot_data[BotData.RegisteredUsers]
    for user in registered_users:
        profiles = context.application.user_data[user][UserData.Profiles].values()
        for profile in profiles:
            tasks.append(home(profile))
    results = await asyncio.gather(*tasks, return_exceptions=True)
    exceptions = [f'{r}' for r in results if isinstance(r, Exception)]
    if len(exceptions) > 0:
        raise RuntimeError('\n'.join(exceptions))


async def update_schedule_images_job(context: ContextTypes.DEFAULT_TYPE):
    registered_users: set = context.bot_data[BotData.RegisteredUsers]
    if len(registered_users) == 0:
        logger.error(f'No registered users for stage query.')
    profiles = [
        p
        for user in registered_users if len(context.application.user_data[user][UserData.Profiles]) > 0
        for p in context.application.user_data[user][UserData.Profiles].values()
    ]
    if len(profiles) == 0:
        logger.error(f'No profiles for stage query.')
    profile = profiles[0]

    resp = await stage_schedule(profile)
    logger.info(f'Got schedules. schedules={resp}')
    await update_schedule_image(resp, profile, context, force=False)


def init_jobs(application: Application):
    application.job_queue.run_custom(
        update_nso_version_job,
        job_kwargs={
            'trigger': 'interval',
            'seconds': config.get(config.NINTENDO_VERSION_UPDATE_INTERVAL),
            'next_run_time': datetime.datetime.utcnow(),
            'misfire_grace_time': None,
        })
    application.job_queue.run_custom(
        keep_alive_job,
        job_kwargs={
            'trigger': 'interval',
            'seconds': config.get(config.NINTENDO_TOKEN_UPDATE_INTERVAL),
            'next_run_time': datetime.datetime.utcnow(),
            'misfire_grace_time': None,
        })
    application.job_queue.run_custom(
        update_schedule_images_job,
        job_kwargs={
            'trigger': 'cron',
            'hour': '*/2',
            'minute': '0',
            'second': '5',
            'timezone': datetime.timezone.utc,
            'next_run_time': datetime.datetime.utcnow(),
            'misfire_grace_time': None,
        })
