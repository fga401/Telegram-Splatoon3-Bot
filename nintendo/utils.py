import urllib.parse

link_prefix = 'npf71b963c1b7b6d119://auth#'
link_prefix_len = len(link_prefix)


class NintendoError(Exception):
    pass


def is_valid_login_link(link: str) -> bool:
    if not link.startswith(link_prefix):
        return False
    args = link[link_prefix_len:]
    query = urllib.parse.parse_qs(args)
    return 'session_state' in query and 'session_token_code' in query and 'state' in query
