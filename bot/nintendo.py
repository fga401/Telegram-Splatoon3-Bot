import functools
import inspect
import logging

import numpy as np
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

import nintendo.login
import nintendo.query
from bot.data import Profile, UserData
from bot.utils import whitelist_filter
from nintendo.utils import ExpiredTokenError

logger = logging.getLogger('bot.nintendo')


async def update_token(profile: Profile):
    """update profile inplace"""
    session_token = profile.session_token
    web_service_token, user_nickname, user_lang, user_country = await nintendo.login.get_gtoken(session_token)
    bullet_token = await nintendo.login.get_bullet(web_service_token, user_lang, user_country)

    profile.account_name = user_nickname
    profile.gtoken = web_service_token
    profile.bullet_token = bullet_token
    profile.country = user_country


def auto_update_profile(fn):
    @functools.wraps(fn)
    async def wrapper(*args, **kwargs):
        try:
            return await fn(*args, **kwargs)
        except ExpiredTokenError as e:
            logger.error(e)
            args_name: list = inspect.getfullargspec(fn)[0]
            if 'profile' in args_name:
                idx = args_name.index('profile')
                profile = args[idx]
                await update_token(profile)
            return await fn(*args, **kwargs)
        except:
            raise

    return wrapper


@auto_update_profile
async def home(profile: Profile) -> str:
    return await nintendo.query.do_query(profile.gtoken, profile.bullet_token, profile.language, profile.country, nintendo.query.QueryKey.HomeQuery, varname='naCountry', varvalue=profile.country)


@auto_update_profile
async def stage_schedule(profile: Profile) -> str:
    return await nintendo.query.do_query(profile.gtoken, profile.bullet_token, profile.language, profile.country, nintendo.query.QueryKey.StageScheduleQuery)


async def download_image(profile: Profile, url: str) -> np.ndarray:
    return await nintendo.query.download_image(profile.gtoken, profile.bullet_token, profile.language, profile.country, url)


async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.warning(f'test')
    profile: Profile = context.user_data[UserData.Profiles][context.user_data[UserData.Current]]
    data = await stage_schedule(profile)
    logger.warning(f'home data = {data}')


handlers = [
    CommandHandler('test', test, filters=whitelist_filter),
]
