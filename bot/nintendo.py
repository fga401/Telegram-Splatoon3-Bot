import functools
import inspect
import logging

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
            args_name: list = inspect.getfullargspec(fn)[0]
            idx = args_name.index('profile')
            profile = args[idx]
            logger.warning(f'Profile is expired. profile = {profile}, error = {e}')
            try:
                await update_token(profile)
            except Exception as e:
                logger.error(f'Failed to update user profile. profile = {profile}, error = {e}')
                raise
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


@auto_update_profile
async def battles(profile: Profile) -> str:
    return await nintendo.query.do_query(profile.gtoken, profile.bullet_token, profile.language, profile.country, nintendo.query.QueryKey.LatestBattleHistoriesQuery)


@auto_update_profile
async def jobs(profile: Profile) -> str:
    return await nintendo.query.do_query(profile.gtoken, profile.bullet_token, profile.language, profile.country, nintendo.query.QueryKey.CoopHistoryQuery)


@auto_update_profile
async def battle_detail(profile: Profile, vs_id: str) -> str:
    return await nintendo.query.do_query(profile.gtoken, profile.bullet_token, profile.language, profile.country, nintendo.query.QueryKey.VsHistoryDetailQuery, varname='vsResultId', varvalue=vs_id)


@auto_update_profile
async def job_detail(profile: Profile, coop_id: str) -> str:
    return await nintendo.query.do_query(profile.gtoken, profile.bullet_token, profile.language, profile.country, nintendo.query.QueryKey.CoopHistoryDetailQuery, varname='coopHistoryDetailId', varvalue=coop_id)


async def download_image(profile: Profile, url: str) -> bytes:
    return await nintendo.query.download_image(profile.gtoken, profile.bullet_token, profile.language, profile.country, url)


async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.warning(f'test')
    profile: Profile = context.user_data[UserData.Profiles][context.user_data[UserData.Current]]
    data = await battle_detail(profile, "VnNIaXN0b3J5RGV0YWlsLXUtcTRncm9td3dvdDJjdnk1aGFubW06UkVDRU5UOjIwMjMwNDAzVDAxMDE1NF82ZGEzN2RmNy04YmE5LTQ2ZWYtYTU1NC0wZmQ5YjM5OWVhMjI=")
    # data = await battles(profile)
    logger.warning(f'home data = {data}')
    with open('regular_battle_detail.json', 'w', encoding='utf-8') as f:
        f.write(data)

handlers = [
    CommandHandler('test', test, filters=whitelist_filter),
]
