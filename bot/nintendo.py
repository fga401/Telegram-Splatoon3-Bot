import logging

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

import nintendo.login
from bot.data import BotData, Profile, UserData
from bot.utils import whitelist_filter
from nintendo import query


async def update_nsoapp_version_job(context: ContextTypes.DEFAULT_TYPE):
    version = await nintendo.login.get_nsoapp_version()
    logging.info(f'Updated Nintendo Online App version. version = {version}')
    context.bot_data[BotData.NintendoAppVersion] = version


async def update_s3s_version_job(context: ContextTypes.DEFAULT_TYPE):
    version = await nintendo.login.get_s3s_version()
    logging.info(f'Updated s3s version. version = {version}')
    context.bot_data[BotData.S3SVersion] = version


async def update_webview_version_job(context: ContextTypes.DEFAULT_TYPE):
    version = await nintendo.login.get_webview_version()
    logging.info(f'Updated webview version. version = {version}')
    context.bot_data[BotData.WebviewVersion] = version


async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    profile: Profile = context.user_data[UserData.Profiles][context.user_data[UserData.Current]]
    data = await nintendo.query.home(profile.gtoken, profile.bullet_token, profile.language)
    logging.warning(f'home data = {data}')


handlers = [
    CommandHandler('test', test, filters=whitelist_filter),
]
