import datetime
import os
import urllib.parse

import config

link_prefix = 'npf71b963c1b7b6d119://auth#'
link_prefix_len = len(link_prefix)
update_interval = datetime.timedelta(hours=2).seconds

if config.get(config.NINTENDO_PROXY_ENABLED):
    proxies = {
        'http': os.getenv('http_proxy', config.get(config.NINTENDO_PROXY_HTTP)),
        'https': os.getenv('https_proxy', config.get(config.NINTENDO_PROXY_HTTPS)),
    }
else:
    proxies = {}


class NintendoError(Exception):
    pass


class ExpiredTokenError(NintendoError):
    pass


def is_valid_login_link(link: str) -> bool:
    if not link.startswith(link_prefix):
        return False
    args = link[link_prefix_len:]
    query = urllib.parse.parse_qs(args)
    return 'session_state' in query and 'session_token_code' in query and 'state' in query


def last_update_timestamp(epoch_second: int) -> int:
    return epoch_second // update_interval * update_interval


def next_update_timestamp(epoch_second: int) -> int:
    return (epoch_second // update_interval + 1) * update_interval
