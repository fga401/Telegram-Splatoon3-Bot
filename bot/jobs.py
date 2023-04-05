import asyncio
import datetime
import logging

from telegram import Update
from telegram.ext import ContextTypes, Application, CommandHandler

import config
import nintendo.login
import nintendo.query
from bot.battles import _message_battle_detail, BattleParser
from bot.coops import CoopParser, _message_coop_detail
from bot.data import BotData, UserData
from bot.nintendo import home, stage_schedule, battles, battle_detail, coops, coop_detail
from bot.schedules import update_schedule_image
from bot.utils import current_profile
from locales import _

logger = logging.getLogger('bot.job')


async def monitor_battle(context: ContextTypes.DEFAULT_TYPE):
    profile = current_profile(context, user_id=context.job.user_id)

    resp = await battles(profile)
    battle_histories = BattleParser.battle_histories(resp)
    battle_ids = [b.id for b in battle_histories]
    last_battle_id = context.user_data[UserData.LastBattle]
    if last_battle_id is None:
        last_battle_id = battle_ids[0]
    try:
        cnt = battle_ids.index(last_battle_id)
    except ValueError:
        cnt = len(battle_ids)
    for battle_id in battle_ids[:cnt][::-1]:
        resp = await battle_detail(profile, battle_id)
        detail = BattleParser.battle_detail(resp)
        text = _message_battle_detail(_, detail, profile)
        await context.bot.send_message(chat_id=context.job.chat_id, text=text)
    if len(battle_ids) > 0:
        context.user_data[UserData.LastBattle] = battle_ids[0]

    resp = await coops(profile)
    coop_histories = CoopParser.coop_histories(resp)
    coop_ids = [c.id for c in coop_histories]
    last_coop_id = context.user_data[UserData.LastCoop]
    if last_coop_id is None:
        last_coop_id = coop_ids[0]
    try:
        cnt = coop_ids.index(last_coop_id)
    except ValueError:
        cnt = len(coop_ids)
    for coop_id in coop_ids[:cnt][::-1]:
        resp = await coop_detail(profile, coop_id)
        detail = CoopParser.coop_detail(resp)
        text = _message_coop_detail(_, detail, profile)
        await context.bot.send_message(chat_id=context.job.chat_id, text=text)
    if len(coop_ids) > 0:
        context.user_data[UserData.LastCoop] = coop_ids[0]


async def monitor_battle_job(update: Update, context: ContextTypes.DEFAULT_TYPE):
    job_name = f'monitor_{update.message.from_user.id}'
    if context.user_data[UserData.Monitoring]:
        await update.message.reply_text(text=_('Stop monitoring the updates.'))
        jobs = context.job_queue.get_jobs_by_name(job_name)
        for job in jobs:
            job.schedule_removal()
        context.user_data[UserData.Monitoring] = False
    else:
        await update.message.reply_text(text=_('Start monitoring the updates.'))
        context.user_data[UserData.LastBattle] = None
        context.user_data[UserData.LastCoop] = None
        context.job_queue.run_custom(
            monitor_battle,
            job_kwargs={
                'trigger': 'interval',
                'seconds': config.get(config.NINTENDO_MONITOR_INTERVAL),
                'next_run_time': datetime.datetime.utcnow(),
                'misfire_grace_time': None,
            },
            name=job_name,
            chat_id=update.message.chat_id,
            user_id=update.message.from_user.id,
        )
        context.user_data[UserData.Monitoring] = True


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
    await update_schedule_image(resp, profile, context, force=False)


def init_jobs(application: Application):
    application.job_queue.run_custom(
        update_nso_version_job,
        job_kwargs={
            'trigger': 'interval',
            'seconds': config.get(config.NINTENDO_VERSION_UPDATE_INTERVAL),
            'next_run_time': datetime.datetime.utcnow(),
            'misfire_grace_time': None,
        }
    )
    application.job_queue.run_custom(
        keep_alive_job,
        job_kwargs={
            'trigger': 'interval',
            'seconds': config.get(config.NINTENDO_TOKEN_UPDATE_INTERVAL),
            'next_run_time': datetime.datetime.utcnow(),
            'misfire_grace_time': None,
        }
    )
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
        }
    )
    application.add_handlers(handlers)


handlers = [
    CommandHandler('monitor', monitor_battle_job)
]
