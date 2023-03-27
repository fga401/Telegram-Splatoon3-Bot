import asyncio
import functools
import json
import re

import cv2
import numpy as np
import requests

import config
import utils
from nintendo.login import APP_USER_AGENT, WEBVIEW_VERSION
from nintendo.utils import ExpiredTokenError, proxies

language_map = {
    '简体中文': 'zh-CN',
    'English(US)': 'en-US',
}

accepted_languages = {
    'de-DE', 'en-GB', 'en-US', 'es-ES', 'es-MX', 'fr-CA', 'fr-FR', 'it-IT', 'ja-JP', 'ko-KR', 'nl-NL', 'ru-RU', 'zh-CN', 'zh-TW'
}


class QueryKey:
    HomeQuery = 'HomeQuery'
    StageScheduleQuery = 'StageScheduleQuery'


graphql_query_map: dict[str, str] = config.get(config.NINTENDO_GRAPHQL_REQUEST_MAP)


@utils.retry_with_backoff()
async def update_graphql_query_map() -> dict[str, str]:
    """Fetch GraphQL request ID from GitHub"""
    global graphql_query_map
    file = await asyncio.get_event_loop().run_in_executor(None, requests.get, "https://raw.githubusercontent.com/nintendoapis/splatnet3-types/main/src/graphql.ts")
    raw = re.search(r'export enum RequestId {(?P<raw>(.|\n|\r)*?)}', file.text).group('raw')
    pairs = re.findall(r'\s*(\w+)\s*=\s*\'(\w+)\'\s*', raw)
    graphql_query_map = {p[0]: p[1] for p in pairs}
    return graphql_query_map


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


async def headbutt(bullet_token: str, language: str, country: str):
    """Returns a (dynamic!) header used for GraphQL requests."""

    if language not in accepted_languages:
        language = language_map[language]
    country = country

    splatoon_url = 'https://api.lp1.av5ja.srv.nintendo.net'

    graphql_head = {
        'Authorization': f'Bearer {bullet_token}',  # update every time it's called with current global var
        'Accept-Language': language,
        'User-Agent': APP_USER_AGENT,
        'X-Web-View-Ver': WEBVIEW_VERSION,
        'Content-Type': 'application/json',
        'Accept': '*/*',
        'Origin': splatoon_url,
        'X-Requested-With': 'com.nintendo.znca',
        'Referer': f'{splatoon_url}?lang={language}&na_country={country}&na_lang={language}',
        'Accept-Encoding': 'gzip, deflate'
    }
    return graphql_head


@utils.retry_with_backoff(retries=3, skipped_exception=ExpiredTokenError)
async def do_query(gtoken: str, bullet_token: str, language: str, country: str, query: str, varname=None, varvalue=None) -> str:
    url = 'https://api.lp1.av5ja.srv.nintendo.net/api/graphql'
    sha = graphql_query_map[query]
    headers = await headbutt(bullet_token, language, country)
    data = gen_graphql_body(sha, varname, varvalue)

    fn = functools.partial(requests.post, url, data=data, headers=headers, cookies=dict(_gtoken=gtoken), proxies=proxies)
    response: requests.Response = await asyncio.get_event_loop().run_in_executor(None, fn)
    if response.status_code != 200:
        raise ExpiredTokenError(f'response status code is not 200. url = {response.url}, body = {response.text}')
    return response.text


@utils.retry_with_backoff(retries=3, skipped_exception=ExpiredTokenError)
async def download_image(gtoken: str, bullet_token: str, language: str, country: str, url: str) -> bytes:
    headers = await headbutt(bullet_token, language, country)
    fn = functools.partial(requests.get, url, headers=headers, cookies=dict(_gtoken=gtoken), proxies=proxies)
    response: requests.Response = await asyncio.get_event_loop().run_in_executor(None, fn)
    buf = bytearray(response.content)
    return buf
