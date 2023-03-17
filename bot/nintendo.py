import logging
from copy import copy

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

import nintendo.login
from bot.data import BotData, Profile, UserData
from bot.utils import whitelist_filter
from nintendo import query
from nintendo.utils import ExpiredTokenError


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


async def update_graphql_request_map_job(context: ContextTypes.DEFAULT_TYPE):
    graphql_request_map = await nintendo.query.get_graphql_request_map()
    logging.info(f'Updated GraphQL request map. map = {graphql_request_map}')
    context.bot_data[BotData.GraphQLRequestMap] = graphql_request_map


async def update_token(context: ContextTypes.DEFAULT_TYPE = None):
    """update profile inplace"""
    if context:
        nsoapp_version = context.bot_data[BotData.NintendoAppVersion]
        s3s_version = context.bot_data[BotData.S3SVersion]
        webview_version = context.bot_data[BotData.WebviewVersion]
    else:
        nsoapp_version = await nintendo.login.get_nsoapp_version()
        s3s_version = await nintendo.login.get_s3s_version()
        webview_version = await nintendo.login.get_webview_version()

    profile = context.user_data[UserData.Profiles][context.user_data[UserData.Current]]
    session_token = profile.session_token
    web_service_token, user_nickname, user_lang, user_country = await nintendo.login.get_gtoken(session_token, nsoapp_version, s3s_version)
    bullet_token = await nintendo.login.get_bullet(web_service_token, user_lang, user_country, webview_version)

    profile = copy(profile)
    profile.account_name = user_nickname
    profile.gtoken = web_service_token
    profile.bullet_token = bullet_token
    profile.country = user_country
    return profile


def auto_update_token(fn):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE = None):
        try:
            await fn(update, context)
        except ExpiredTokenError as e:
            logging.error(e)
            await update_token(context)
            await fn(update, context)
        except:
            raise

    return wrapper


@auto_update_token
async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f'test')
    profile: Profile = context.user_data[UserData.Profiles][context.user_data[UserData.Current]]
    data = await nintendo.query.do_query(profile.gtoken, profile.bullet_token, profile.language, profile.country, 'HomeQuery', varname='naCountry', varvalue=profile.country, webview_version=context.bot_data[BotData.WebviewVersion])
    logging.warning(f'home data = {data}')


handlers = [
    CommandHandler('test', test, filters=whitelist_filter),
]
