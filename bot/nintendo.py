import functools
import inspect
import logging

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

import nintendo.login
import nintendo.query
from bot.battles import _message_battle_detail, BattleParser
from bot.coops import CoopParser, _message_coop_detail
from bot.data import Profile, UserData
from bot.utils import whitelist_filter
from locales import _
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


def auto_logging(fn):
    @functools.wraps(fn)
    async def wrapper(*args, **kwargs):
        data = await fn(*args, **kwargs)
        logger.debug(f'Got Nintendo responce. {fn.__name__} = {data}')
        return data

    return wrapper


@auto_logging
@auto_update_profile
async def home(profile: Profile) -> str:
    return await nintendo.query.do_query(profile.gtoken, profile.bullet_token, profile.language, profile.country, nintendo.query.QueryKey.HomeQuery, varname='naCountry', varvalue=profile.country)


@auto_logging
@auto_update_profile
async def stage_schedule(profile: Profile) -> str:
    return await nintendo.query.do_query(profile.gtoken, profile.bullet_token, profile.language, profile.country, nintendo.query.QueryKey.StageScheduleQuery)


@auto_logging
@auto_update_profile
async def battles(profile: Profile) -> str:
    return await nintendo.query.do_query(profile.gtoken, profile.bullet_token, profile.language, profile.country, nintendo.query.QueryKey.LatestBattleHistoriesQuery)


@auto_logging
@auto_update_profile
async def coops(profile: Profile) -> str:
    return await nintendo.query.do_query(profile.gtoken, profile.bullet_token, profile.language, profile.country, nintendo.query.QueryKey.CoopHistoryQuery)


@auto_logging
@auto_update_profile
async def battle_detail(profile: Profile, vs_id: str) -> str:
    return await nintendo.query.do_query(profile.gtoken, profile.bullet_token, profile.language, profile.country, nintendo.query.QueryKey.VsHistoryDetailQuery, varname='vsResultId', varvalue=vs_id)


@auto_logging
@auto_update_profile
async def coop_detail(profile: Profile, coop_id: str) -> str:
    return await nintendo.query.do_query(profile.gtoken, profile.bullet_token, profile.language, profile.country, nintendo.query.QueryKey.CoopHistoryDetailQuery, varname='coopHistoryDetailId', varvalue=coop_id)


async def download_image(profile: Profile, url: str) -> bytes:
    return await nintendo.query.download_image(profile.gtoken, profile.bullet_token, profile.language, profile.country, url)


async def test1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    profile: Profile = context.user_data[UserData.Profiles][context.user_data[UserData.Current]]
    files = [
        'regular_battle_detail.json',
        'challenge_battle_detail.json',
        'open_battle_detail.json',
        'x_battle_deatil.json',
        'fest_open_battle_detail.json',
        'fest_challenge_battle_detail.json',
        'fest_tri_color_battle_detail.json',
    ]
    for file in files:
        with open(f'./json/{file}', 'r', encoding='utf-8') as f:
            data = f.read()
            detail = BattleParser.battle_detail(data)
            text = _message_battle_detail(_, detail, profile)
            await update.message.reply_text(text=text)


async def test2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    profile: Profile = context.user_data[UserData.Profiles][context.user_data[UserData.Current]]
    files = [
        'coop_detail_1.json',
        'coop_detail_2.json',
    ]
    for file in files:
        with open(f'./json/{file}', 'r', encoding='utf-8') as f:
            data = f.read()
            detail = CoopParser.coop_detail(data)
            text = _message_coop_detail(_, detail, profile)
            await update.message.reply_text(text=text)


async def test3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.warning(f'test')
    profile: Profile = context.user_data[UserData.Profiles][context.user_data[UserData.Current]]
    # data = await battle_detail(profile, "VnNIaXN0b3J5RGV0YWlsLXUtcTRncm9td3dvdDJjdnk1aGFubW06UkVDRU5UOjIwMjMwNDA1VDEyNTU1MV83MzVlYWRmZS04NTkxLTRiN2MtODNlMy1hYjYxMzg1YjdhMWE=")
    data = await stage_schedule(profile)
    logger.warning(f'home data = {data}')
    with open('stage_schedule.json', 'w', encoding='utf-8') as f:
        f.write(data)


handlers = [
    CommandHandler('test1', test1, filters=whitelist_filter),
    CommandHandler('test2', test2, filters=whitelist_filter),
    CommandHandler('test3', test3, filters=whitelist_filter),
]
