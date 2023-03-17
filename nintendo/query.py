import asyncio
import functools
import json
import re

import requests

import config
import utils
from nintendo.login import get_webview_version, APP_USER_AGENT
from nintendo.utils import ExpiredTokenError

language_map = {
    '简体中文': 'zh-CN',
    'English(US)': 'en-US',
}


@utils.retry_with_backoff()
async def get_graphql_request_map() -> dict[str, str]:
    """Fetch GraphQL request ID from GitHub"""
    file = await asyncio.get_event_loop().run_in_executor(None, requests.get, "https://raw.githubusercontent.com/nintendoapis/splatnet3-types/main/src/graphql.ts")
    raw = re.search(r'export enum RequestId {(?P<raw>(.|\n|\r)*?)}', file.text).group('raw')
    pairs = re.findall(r'\s*(\w+)\s*=\s*\'(\w+)\'\s*', raw)
    return {p[0]: p[1] for p in pairs}


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


async def headbutt(bullet_token: str, language: str, country: str = None, webview_version: str = None):
    """
    Returns a (dynamic!) header used for GraphQL requests.

    :arg force_lang example 'en-US'
    """

    lang = language_map[language]
    country = country

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


@utils.retry_with_backoff(retries=3, skipped_exception=ExpiredTokenError)
async def do_query(gtoken: str, bullet_token: str, language: str, country: str, query: str, varname=None, varvalue=None, webview_version=None) -> str:
    url = config.get(config.NINTENDO_SPLATNET3_GRAPHQL_URL)
    sha = config.get(config.NINTENDO_GRAPHQL_REQUEST_MAP_FALLBACK)[query]
    headers = await headbutt(bullet_token, language, country, webview_version)
    data = gen_graphql_body(sha, varname, varvalue)

    fn = functools.partial(requests.post, url, data=data, headers=headers, cookies=dict(_gtoken=gtoken))
    response: requests.Response = await asyncio.get_event_loop().run_in_executor(None, fn)
    if response.status_code != 200:
        raise ExpiredTokenError(f'response status code is not 200. url = {response.url}, body = {response.text}')
    return response.text
