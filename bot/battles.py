import datetime
from typing import Callable

import pytz

from bot.data import BattleDetail, Judgement, Profile, ModeEnum, Team, Player, Award, Rank
from bot.utils import format_detail_time


def _judgement_emoji(text: str) -> str:
    if text == Judgement.Win:
        judgement_emoji = '✅'
    elif text == Judgement.Lose:
        judgement_emoji = '❌'
    else:
        judgement_emoji = ''
    return judgement_emoji



def _message_battle_detail(_: Callable[[str], str], battle: BattleDetail, profile: Profile) -> str:
    if battle.judgement == Judgement.Win:
        judgement_text = _('{judgement_emoji} Victory').format(judgement_emoji=Emoji.Victory)
    elif battle.judgement == Judgement.Lose:
        judgement_text = _('{judgement_emoji} Defeat').format(judgement_emoji=Emoji.Defeat)
    else:
        judgement_text = ''
    end_time = battle.start_time + datetime.timedelta(seconds=battle.duration)
    teams = sorted([battle.my_team, *battle.other_teams], key=lambda t: t.order)
    if len(teams) == 3:
        # tri-color
        attack_1 = next(filter(lambda t: t.tricolor_role == 'ATTACK1', teams), None)
        attack_2 = next(filter(lambda t: t.tricolor_role == 'ATTACK2', teams), None)
        defense = next(filter(lambda t: t.tricolor_role == 'DEFENSE', teams), None)
        team_names = [''] * 3
        team_names[teams.index(attack_1)] = _('Attacking')
        team_names[teams.index(attack_2)] = _('Attacking')
        team_names[teams.index(defense)] = _('Defending')
        paints = [attack_1.score, defense.score, attack_2.score]
    else:
        my = battle.my_team
        other = battle.other_teams[0]
        team_names = [''] * 2
        team_names[teams.index(my)] = _('My Team')
        team_names[teams.index(other)] = _('Other Team')
        paints = [my.score, other.score]
    count_bar = _message_count_bar(paints)
    teams_text = [_message_team_detail(_, team, name) for name, team in zip(team_names, teams)]
    text = '\n'.join([
        _('<b>[{judgement_text}]</b>'),
        _('  - Start Time: <code>{start_time}</code>'),
        _('  - End Time: <code>{end_time}</code>'),
        _('  - Mode: <code>{mode}</code>'),
        _('  - Rule: <code>{rule}</code>'),
        _('  - Stage: <code>{stage}</code>'),
        _('  - Count: {count_bar}'),
        *teams_text,
        _message_awards_detail(_, battle.awards),
    ]).format(
        judgement_text=judgement_text,
        start_time=format_detail_time(battle.start_time.astimezone(pytz.timezone(profile.timezone))),
        end_time=format_detail_time(end_time.astimezone(pytz.timezone(profile.timezone))),
        mode=ModeEnum.name(battle.mode),
        rule=battle.rule.name,
        stage=battle.stage.name,
        count_bar=count_bar,
    )
    return text


def _message_count_bar(paints: list[float]):
    total = sum(paints)
    segments: list[int] = [int(score // total) for score in paints]
    if len(segments) == 3:
        attack_1_segment = '≈' * segments[0]
        defense_segment = '=' * (segments[1] // 2)
        attack_2_segment = '≈' * segments[2]
        return '[{attack_1_score}{attack_1_segment}>/<{defense_segment}{defense_score}{defense_segment}>/<{attack_2_segment}{attack_2_score}]'.format(
            attack_1_segment=attack_1_segment,
            defense_segment=defense_segment,
            attack_2_segment=attack_2_segment,
            attack_1_score=paints[0],
            defense_score=paints[1],
            attack_2_score=paints[2],
        )
    else:
        return '[{my_score}{my_segment}>/<{other_segment}{other_score}]'.format(
            my_segment='≈' * segments[0],
            other_segment='=' * segments[1],
            my_score=paints[0],
            other_score=paints[1],
        )


def _message_team_detail(_: Callable[[str], str], team: Team, team_name: str) -> str:
    players_text = [_message_player_detail(_, play) for play in team.players]
    if team.judgement == Judgement.Win:
        judgement_emoji = Emoji.Victory
    elif team.judgement == Judgement.Lose:
        judgement_emoji = Emoji.Defeat
    else:
        judgement_emoji = ''
    return '\n'.join([
        _('<b>[{judgement_emoji} {team_name}]</b>'),
        *players_text,
    ]).format(
        judgement_emoji=judgement_emoji,
        team_name=team_name,
    )


def _message_player_detail(_: Callable[[str], str], player: Player) -> str:
    myself = ' ' if not player.myself else '*'
    return '\n'.join([
        _('{myself} <code>{name}</code>'),
        _('    - Weapon: <code>{weapon}</code>'),
        _('    - K(A)/D/SP: <code>{kill}({assist})/{death}/{special}</code>'),
        _('    - Point: <code>{paint}</code>'),
    ]).format(
        myself=myself,
        name=player.name,
        weapon=player.weapon.name,
        paint=player.paint,
        kill=player.result.kill,
        assist=player.result.assist,
        death=player.result.death,
        special=player.result.special,
    )


def _award_emoji(text: str) -> str:
    if text == Rank.Gold:
        award_emoji = '🥇'
    elif text == Rank.Silver:
        award_emoji = '🥈'
    else:
        award_emoji = ''
    return award_emoji


def _message_awards_detail(_: Callable[[str], str], awards: list[Award]) -> str:
    awards_text = [
        '  - {award_emoji} {award_text}'.format(award_emoji=award.rank, award_text=award.name)
        for award in awards
    ]
    return '\n'.join([
        _('<b>[Award]</b>'),
        *awards_text,
    ])
