import asyncio
import base64
import functools
import hashlib
import json
import logging
import os
import re
import urllib.parse

import requests
from bs4 import BeautifulSoup

import config
import utils.retry
from nintendo.utils import NintendoError

# SET HTTP HEADERS
APP_USER_AGENT = 'Mozilla/5.0 (Linux; Android 11; Pixel 5) ' \
                 'AppleWebKit/537.36 (KHTML, like Gecko) ' \
                 'Chrome/94.0.4606.61 Mobile Safari/537.36'


@utils.retry_with_backoff()
async def get_nsoapp_version() -> str:
    """Fetches the current Nintendo Switch Online app version from the Apple App Store and sets it globally."""
    page = await asyncio.get_event_loop().run_in_executor(None, requests.get, "https://apps.apple.com/us/app/nintendo-switch-online/id1234806557")
    soup = BeautifulSoup(page.text, 'html.parser')
    elt = soup.find("p", {"class": "whats-new__latest__version"})
    version = elt.get_text().replace("Version ", "").strip()
    return version


@utils.retry_with_backoff()
async def get_s3s_version() -> str:
    """Fetch s3s version from GitHub"""
    latest_script = await asyncio.get_event_loop().run_in_executor(None, requests.get, "https://raw.githubusercontent.com/frozenpandaman/s3s/master/s3s.py")
    version = re.search(r'A_VERSION = "([\d.]*)"', latest_script.text).group(1)
    return version


@utils.retry_with_backoff()
async def get_webview_version() -> str:
    """Finds & parses the SplatNet 3 main.js file to fetch the current site version and sets it globally."""
    url = config.get(config.NINTENDO_SPLATNET3_URL)

    app_head = {
        'Upgrade-Insecure-Requests': '1',
        'Accept': '*/*',
        'DNT': '1',
        'X-AppColorScheme': 'DARK',
        'X-Requested-With': 'com.nintendo.znca',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-User': '?1',
        'Sec-Fetch-Dest': 'document'
    }
    app_cookies = {
        '_dnt': '1'  # Do Not Track
    }
    fn = functools.partial(requests.get, url, headers=app_head, cookies=app_cookies)
    home = await asyncio.get_event_loop().run_in_executor(None, fn)
    if home.status_code != 200:
        raise NintendoError('home response status_code was not 200 ')

    soup = BeautifulSoup(home.text, 'html.parser')
    main_js = soup.select_one("script[src*='static']")

    if not main_js:  # failed to parse html for main.js file
        raise NintendoError('failed to parse html for main.js file from home')

    main_js_url = url + main_js.attrs['src']

    app_head = {
        'Accept': '*/*',
        'X-Requested-With': 'com.nintendo.znca',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-Mode': 'no-cors',
        'Sec-Fetch-Dest': 'script',
        'Referer': url  # sending w/o lang, na_country, na_lang params
    }

    fn = functools.partial(requests.get, main_js_url, headers=app_head, cookies=app_cookies)
    main_js_body = await asyncio.get_event_loop().run_in_executor(None, fn)
    if main_js_body.status_code != 200:
        raise NintendoError('main_js_body response status_code was not 200 ')

    pattern = r"\b(?P<revision>[0-9a-f]{40})\b[\S]*?void 0[\S]*?\"revision_info_not_set\"\}`,.*?=`(?P<version>\d+\.\d+\.\d+)-"
    match = re.search(pattern, main_js_body.text)
    if match is None:
        raise NintendoError('failed to parse version from main_js_body')

    version, revision = match.group('version'), match.group('revision')
    ver_string = f'{version}-{revision[:8]}'
    return ver_string


def login_link():
    auth_state = base64.urlsafe_b64encode(os.urandom(36))

    auth_code_verifier = base64.urlsafe_b64encode(os.urandom(32))
    auth_cv_hash = hashlib.sha256()
    auth_cv_hash.update(auth_code_verifier.replace(b"=", b""))
    auth_code_challenge = base64.urlsafe_b64encode(auth_cv_hash.digest())

    body = {
        'state': auth_state,
        'redirect_uri': 'npf71b963c1b7b6d119://auth',
        'client_id': '71b963c1b7b6d119',
        'scope': 'openid user user.birthday user.mii user.screenName',
        'response_type': 'session_token_code',
        'session_token_code_challenge': auth_code_challenge.replace(b"=", b""),
        'session_token_code_challenge_method': 'S256',
        'theme': 'login_form'
    }

    return auth_code_verifier, f'https://accounts.nintendo.com/connect/1.0.0/authorize?{urllib.parse.urlencode(body)}'


async def get_session_token(auth_code_verifier: bytes, link: str, nsoapp_version=None):
    if nsoapp_version is None:
        nsoapp_version = await get_nsoapp_version
    session_token_code = re.search('de=(.*)&', link).group(1)

    app_head = {
        'User-Agent': f'OnlineLounge/{nsoapp_version} NASDKAPI Android',
        'Accept-Language': 'en-US',
        'Accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Content-Length': '540',
        'Host': 'accounts.nintendo.com',
        'Connection': 'Keep-Alive',
        'Accept-Encoding': 'gzip'
    }

    body = {
        'client_id': '71b963c1b7b6d119',
        'session_token_code': session_token_code,
        'session_token_code_verifier': auth_code_verifier.replace(b"=", b"")
    }

    url = 'https://accounts.nintendo.com/connect/1.0.0/api/session_token'

    session = requests.Session()

    fn = functools.partial(session.post, url, headers=app_head, data=body)
    r = await asyncio.get_event_loop().run_in_executor(None, fn)
    try:
        return json.loads(r.text)["session_token"]
    except:
        raise NintendoError(f'Failed to get session token. response = {r.text}')


@utils.retry_with_backoff()
async def get_gtoken(session_token, nsoapp_version=None, s3s_ver=None):
    """Provided the session_token, returns a GameWebToken JWT and account info."""
    f_gen_url = config.get(config.NINTENDO_F_GEN_URL)

    if nsoapp_version is None:
        nsoapp_version = await get_nsoapp_version()
    if s3s_ver is None:
        s3s_ver = await get_s3s_version()

    app_head = {
        'Host': 'accounts.nintendo.com',
        'Accept-Encoding': 'gzip',
        'Content-Type': 'application/json',
        'Content-Length': '436',
        'Accept': 'application/json',
        'Connection': 'Keep-Alive',
        'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 7.1.2)'
    }

    body = {
        'client_id': '71b963c1b7b6d119',
        'session_token': session_token,
        'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer-session-token'
    }

    url = 'https://accounts.nintendo.com/connect/1.0.0/api/token'
    fn = functools.partial(requests.post, url, headers=app_head, json=body)
    r = await asyncio.get_event_loop().run_in_executor(None, fn)
    id_response = json.loads(r.text)

    if 'access_token' not in id_response:
        raise NintendoError(f'Failed to get access_token. json = {id_response}')

    # get user info
    try:
        app_head = {
            'User-Agent': 'NASDKAPI; Android',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f'Bearer {id_response["access_token"]}',
            'Host': 'api.accounts.nintendo.com',
            'Connection': 'Keep-Alive',
            'Accept-Encoding': 'gzip'
        }
    except:
        raise NintendoError(f'Not a valid authorization request. Please delete config.txt and try again. Error from Nintendo (in api/token step): {json.dumps(id_response, indent=2)}')

    url = 'https://api.accounts.nintendo.com/2.0.0/users/me'
    fn = functools.partial(requests.get, url, headers=app_head)
    r = await asyncio.get_event_loop().run_in_executor(None, fn)
    user_info = json.loads(r.text)
    logging.info(f'Nintendo user_info = {user_info}')

    user_nickname = user_info["nickname"]
    user_lang = user_info["language"]
    user_country = user_info["country"]

    # get access token
    body = {}
    try:
        id_token = id_response["id_token"]
        f, uuid, timestamp = await call_f_api(id_token, 1, s3s_ver)

        parameter = {
            'f': f,
            'language': user_lang,
            'naBirthday': user_info["birthday"],
            'naCountry': user_country,
            'naIdToken': id_token,
            'requestId': uuid,
            'timestamp': timestamp
        }
    except:
        raise NintendoError(f'Error(s) from Nintendo: id_response = {json.dumps(id_response, indent=2)}, user_info = {json.dumps(user_info, indent=2)}')

    body["parameter"] = parameter

    app_head = {
        'X-Platform': 'Android',
        'X-ProductVersion': nsoapp_version,
        'Content-Type': 'application/json; charset=utf-8',
        'Content-Length': str(990 + len(f)),
        'Connection': 'Keep-Alive',
        'Accept-Encoding': 'gzip',
        'User-Agent': f'com.nintendo.znca/{nsoapp_version}(Android/7.1.2)',
    }

    url = 'https://api-lp1.znc.srv.nintendo.net/v3/Account/Login'
    fn = functools.partial(requests.post, url, headers=app_head, json=body)
    r = await asyncio.get_event_loop().run_in_executor(None, fn)
    splatoon_token = json.loads(r.text)

    try:
        id_token = splatoon_token["result"]["webApiServerCredential"]["accessToken"]
    except:
        # retry once if 9403/9599 error from nintendo
        try:
            f, uuid, timestamp = await call_f_api(id_token, 1, f_gen_url)
            body["parameter"]["f"] = f
            body["parameter"]["requestId"] = uuid
            body["parameter"]["timestamp"] = timestamp
            app_head["Content-Length"] = str(990 + len(f))
            url = "https://api-lp1.znc.srv.nintendo.net/v3/Account/Login"
            fn = functools.partial(requests.post, url, headers=app_head, json=body)
            r = await asyncio.get_event_loop().run_in_executor(None, fn)
            splatoon_token = json.loads(r.text)
            id_token = splatoon_token["result"]["webApiServerCredential"]["accessToken"]
        except:
            raise NintendoError(f'Error from Nintendo (in Account/Login step): {json.dumps(splatoon_token, indent=2)}')

        f, uuid, timestamp = await call_f_api(id_token, 2, f_gen_url)

    # get web service token
    app_head = {
        'X-Platform': 'Android',
        'X-ProductVersion': nsoapp_version,
        'Authorization': f'Bearer {id_token}',
        'Content-Type': 'application/json; charset=utf-8',
        'Content-Length': '391',
        'Accept-Encoding': 'gzip',
        'User-Agent': f'com.nintendo.znca/{nsoapp_version}(Android/7.1.2)'
    }

    body = {}
    parameter = {
        'f': f,
        'id': 4834290508791808,
        'registrationToken': id_token,
        'requestId': uuid,
        'timestamp': timestamp
    }
    body["parameter"] = parameter

    url = "https://api-lp1.znc.srv.nintendo.net/v2/Game/GetWebServiceToken"
    fn = functools.partial(requests.post, url, headers=app_head, json=body)
    r = await asyncio.get_event_loop().run_in_executor(None, fn)
    web_service_resp = json.loads(r.text)

    try:
        web_service_token = web_service_resp["result"]["accessToken"]
    except:
        # retry once if 9403/9599 error from nintendo
        try:
            f, uuid, timestamp = await call_f_api(id_token, 2, f_gen_url)
            body["parameter"]["f"] = f
            body["parameter"]["requestId"] = uuid
            body["parameter"]["timestamp"] = timestamp
            url = "https://api-lp1.znc.srv.nintendo.net/v2/Game/GetWebServiceToken"
            fn = functools.partial(requests.post, url, headers=app_head, json=body)
            r = await asyncio.get_event_loop().run_in_executor(None, fn)
            web_service_resp = json.loads(r.text)
            web_service_token = web_service_resp["result"]["accessToken"]
        except:
            raise NintendoError(f'Error from Nintendo (in Game/GetWebServiceToken step): {json.dumps(web_service_resp, indent=2)}')

    return web_service_token, user_nickname, user_lang, user_country


@utils.retry_with_backoff()
async def call_f_api(id_token, step, s3s_ver=None):
    """Passes an naIdToken to the f generation API (default: imink) & fetches the response (f token, UUID, and timestamp)."""
    if s3s_ver is None:
        s3s_ver = await get_s3s_version()
    f_gen_url = config.get(config.NINTENDO_F_GEN_URL)

    try:
        api_head = {
            'User-Agent': f's3s/{s3s_ver}',
            'Content-Type': 'application/json; charset=utf-8'
        }
        api_body = {
            'token': id_token,
            'hash_method': step
        }
        fn = functools.partial(requests.post, f_gen_url, data=json.dumps(api_body), headers=api_head)
        api_response = await asyncio.get_event_loop().run_in_executor(None, fn)
        resp = json.loads(api_response.text)

        f = resp["f"]
        uuid = resp["request_id"]
        timestamp = resp["timestamp"]
        return f, uuid, timestamp
    except:
        try:  # if api_response never gets set
            if api_response.text:
                raise NintendoError(f"Error during f generation:\n{json.dumps(json.loads(api_response.text), indent=2, ensure_ascii=False)}")
            else:
                raise NintendoError(f"Error during f generation: Error {api_response.status_code}.")
        except:
            raise NintendoError(f"Couldn't connect to f generation API ({f_gen_url}). Please try again.")


@utils.retry_with_backoff()
async def get_bullet(web_service_token, user_lang, user_country, web_view_ver=None):
    """Given a gtoken, returns a bulletToken."""

    splatnet3_url = config.get(config.NINTENDO_SPLATNET3_URL)
    if web_view_ver is None:
        web_view_ver = await get_webview_version()

    app_head = {
        'Content-Length': '0',
        'Content-Type': 'application/json',
        'Accept-Language': user_lang,
        'User-Agent': APP_USER_AGENT,
        'X-Web-View-Ver': web_view_ver,
        'X-NACOUNTRY': user_country,
        'Accept': '*/*',
        'Origin': splatnet3_url,
        'X-Requested-With': 'com.nintendo.znca'
    }
    app_cookies = {
        '_gtoken': web_service_token,  # X-GameWebToken
        '_dnt': '1'  # Do Not Track
    }
    url = f'{splatnet3_url}/api/bullet_tokens'
    fn = functools.partial(requests.post, url, headers=app_head, cookies=app_cookies)
    r = await asyncio.get_event_loop().run_in_executor(None, fn)

    if r.status_code == 401:
        raise NintendoError('Unauthorized error (ERROR_INVALID_GAME_WEB_TOKEN). Cannot fetch tokens at this time.')
    elif r.status_code == 403:
        raise NintendoError('Forbidden error (ERROR_OBSOLETE_VERSION). Cannot fetch tokens at this time.')
    elif r.status_code == 204:  # No Content, USER_NOT_REGISTERED
        raise NintendoError('Cannot access SplatNet 3 without having played online.')

    try:
        bullet_resp = json.loads(r.text)
        bullet_token = bullet_resp["bulletToken"]
    except (json.decoder.JSONDecodeError, TypeError):
        raise NintendoError(f'Got non-JSON response from Nintendo (in api/bullet_tokens step): {r.text}')
    except:
        raise NintendoError(f'Error from Nintendo (in api/bullet_tokens step): {json.dumps(bullet_resp, indent=2)}')

    return bullet_token
