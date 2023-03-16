import logging

from telegram.ext import ContextTypes

import nintendo.login
from bot.data import BotData


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
