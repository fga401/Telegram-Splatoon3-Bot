import datetime
from typing import Callable

import pytz

from bot.data import BattleDetail, Judgement, Profile, ModeEnum
from bot.utils import format_detail_time


class Emoji:
    Victory = '✅'
    Defeat = '❌'


async def _message_battle_detail(_: Callable[[str], str], battle: BattleDetail, profile: Profile) -> str:
    if battle.judgement == Judgement.Win:
        judgement_text = _('Victory {judgement_emoji}').format(judgement_emoji=Emoji.Victory)
    elif battle.judgement == Judgement.Lose:
        judgement_text = _('Defeat {judgement_emoji}').format(judgement_emoji=Emoji.Defeat)
    else:
        judgement_text = ''
    end_time = battle.start_time + datetime.timedelta(seconds=battle.duration)

    return '\n'.join([
        _('<code>[{judgement_text}]</code>'),
        _('  - Start Time: <code>{start_time}</code>'),
        _('  - End Time: <code>{end_time}</code>'),
        _('  - Mode: <code>{mode}</code>'),
        _('  - Rule: <code>{rule}</code>'),
        _('  - Stage: <code>{stage}</code>'),
        _('  - Count: {count_bar}'),
    ]).format(
        judgement_text=judgement_text,
        start_time=format_detail_time(battle.start_time.astimezone(pytz.timezone(profile.timezone))),
        end_time=format_detail_time(end_time.astimezone(pytz.timezone(profile.timezone))),
        mode=ModeEnum.name(battle.mode),
        rule=battle.rule.name,
        stage=battle.stage.name,
    )
