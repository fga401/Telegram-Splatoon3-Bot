import asyncio
import functools
import json
import logging
import re

import requests

import config
import utils
from nintendo.login import get_webview_version, APP_USER_AGENT

# TODO: update from Internet
translate_rid = {
    'HomeQuery': '22e2fa8294168003c21b00c333c35384',  # blank vars
    'LatestBattleHistoriesQuery': '0176a47218d830ee447e10af4a287b3f',  # INK / blank vars - query1
    'RegularBattleHistoriesQuery': '3baef04b095ad8975ea679d722bc17de',  # INK / blank vars - query1
    'BankaraBattleHistoriesQuery': '0438ea6978ae8bd77c5d1250f4f84803',  # INK / blank vars - query1
    'PrivateBattleHistoriesQuery': '8e5ae78b194264a6c230e262d069bd28',  # INK / blank vars - query1
    'XBattleHistoriesQuery': '6796e3cd5dc3ebd51864dc709d899fc5',  # INK / blank vars - query1
    'VsHistoryDetailQuery': '291295ad311b99a6288fc95a5c4cb2d2',  # INK / req "vsResultId" - query2
    'CoopHistoryQuery': '2fd21f270d381ecf894eb975c5f6a716',  # SR  / blank vars - query1
    'CoopHistoryDetailQuery': '379f0d9b78b531be53044bcac031b34b',  # SR  / req "coopHistoryDetailId" - query2
    'MyOutfitCommonDataEquipmentsQuery': 'd29cd0c2b5e6bac90dd5b817914832f8'  # for Lean's seed checker
}

language_map = {
    '简体中文': 'zh-CN',
    'English(US)': 'en-US',
}


@utils.retry_with_backoff()
async def get_request_ids() -> str:
    """Fetch GraphQL request ID from GitHub"""
    file = await asyncio.get_event_loop().run_in_executor(None, requests.get, "https://raw.githubusercontent.com/nintendoapis/splatnet3-types/main/src/graphql.ts")
    raw_map = re.search(r'export enum RequestId {(?P<raw_map>(.|\n|\r)*?)}', file.text).group('raw_map')
    pairs = re.findall(r'\s*(\w+)\s*=\s*\'(\w+)\'\s*', raw_map)
    logging.error(f'{pairs}')
    return None


def gen_graphql_body(sha256hash, varname=None, varvalue=None):
    """Generates a JSON dictionary, specifying information to retrieve, to send with GraphQL requests."""
    great_passage = {
        "extensions": {
            "persistedQuery": {
                "sha256Hash": sha256hash,
                "version": 1
            }
        },
        "variables": {}
    }

    if varname is not None and varvalue is not None:
        great_passage["variables"][varname] = varvalue

    return json.dumps(great_passage)


async def headbutt(bullet_token: str, language: str, force_lang: str = None, webview_version: str = None):
    """
    Returns a (dynamic!) header used for GraphQL requests.

    :arg force_lang example 'en-US'
    """

    if force_lang:
        lang = force_lang
        country = force_lang[-2:]
    else:
        lang = language_map[language]
        country = lang[-2:]

    if webview_version is None:
        webview_version = await get_webview_version()

    splatoon_url = config.get(config.NINTENDO_SPLATNET3_URL)

    graphql_head = {
        'Authorization': f'Bearer {bullet_token}',  # update every time it's called with current global var
        'Accept-Language': lang,
        'User-Agent': APP_USER_AGENT,
        'X-Web-View-Ver': webview_version,
        'Content-Type': 'application/json',
        'Accept': '*/*',
        'Origin': splatoon_url,
        'X-Requested-With': 'com.nintendo.znca',
        'Referer': f'{splatoon_url}?lang={lang}&na_country={country}&na_lang={lang}',
        'Accept-Encoding': 'gzip, deflate'
    }
    return graphql_head


async def home(gtoken: str, bullet_token: str, language: str):
    url = config.get(config.NINTENDO_SPLATNET3_GRAPHQL_URL)
    sha = translate_rid["HomeQuery"]
    headers = await headbutt(bullet_token, language)

    fn = functools.partial(requests.post, url, data=gen_graphql_body(sha), headers=headers, cookies=dict(_gtoken=gtoken))
    response: requests.Response = await asyncio.get_event_loop().run_in_executor(None, fn)
    logging.info(f'home. response = {response.json()}')
