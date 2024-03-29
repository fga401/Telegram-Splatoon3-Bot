import datetime
import html
import json
from typing import Callable, Union

import pytz

from bot.data import BattleDetail, Judgement, Profile, ModeEnum, Team, Award, Rank, Gear, BattlePlayerResult, Battle, BattlePlayer, CommonParser
from bot.utils import format_detail_time


class BattleParser:
    @staticmethod
    def battle_histories(histories: str) -> list[Battle]:
        data = json.loads(histories)
        return [
            Battle(
                id=node['id'],
                rule=CommonParser.rule(node['vsRule']),
                mode=CommonParser.mode(node['vsMode']),
                stage=CommonParser.stage(node['vsStage']),
                judgement=node['judgement'],
                knockout=node['knockout'],
            )
            for group in data['data']['latestBattleHistories']['historyGroups']['nodes'] for node in group['historyDetails']['nodes']
        ]

    @staticmethod
    def battle_detail(detail: str) -> BattleDetail:
        data = json.loads(detail)
        node = data['data']['vsHistoryDetail']
        return BattleDetail(
            id=node['id'],
            rule=CommonParser.rule(node['vsRule']),
            mode=CommonParser.mode(node['vsMode']),
            stage=CommonParser.stage(node['vsStage']),
            judgement=node['judgement'],
            knockout=node['knockout'],
            my_team=BattleParser.__team_detail(node['myTeam']),
            other_teams=[BattleParser.__team_detail(team) for team in node['otherTeams']],
            duration=node['duration'],
            start_time=CommonParser.datetime(node['playedTime']),
            awards=[BattleParser.__award_detail(award) for award in node['awards']]
        )

    @staticmethod
    def __team_detail(node) -> Team:
        if node['result'] is not None:
            score = node['result']['score']
            if score is None:
                score = node['result']['paintRatio'] * 100
        else:
            score = 0.0001
        players = [BattleParser.__player_detail(play) for play in node['players']]
        return Team(
            score=score,
            tricolor_role=node['tricolorRole'],
            judgement=node['judgement'],
            players=players,
            order=node['order']
        )

    @staticmethod
    def __player_detail(node) -> BattlePlayer:
        if node['result'] is not None:
            result = BattlePlayerResult(
                kill=node['result']['kill'],
                death=node['result']['death'],
                assist=node['result']['assist'],
                special=node['result']['special'],
            )
        else:
            result = None
        return BattlePlayer(
            id=node['id'],
            name=node['name'],
            byname=node['byname'],
            name_id=node['nameId'],
            nameplate=CommonParser.nameplate(node['nameplate']),
            paint=node['paint'],
            myself=node['isMyself'],
            weapon=CommonParser.weapon(node['weapon']),
            result=result,
            head_gear=BattleParser.__gear_detail(node['headGear']),
            clothing_gear=BattleParser.__gear_detail(node['clothingGear']),
            shoes_gear=BattleParser.__gear_detail(node['shoesGear']),
        )

    @staticmethod
    def __gear_detail(node) -> Gear:
        return Gear(
            name=node['name'],
            primary=node['primaryGearPower']['name'],
            additional=[power['name'] for power in node['additionalGearPowers']],
            brand=node['brand']['name']
        )

    @staticmethod
    def __award_detail(node) -> Award:
        return Award(
            name=node['name'],
            rank=node['rank'],
        )


def _judgement_emoji(text: str) -> str:
    if text == Judgement.Win:
        judgement_emoji = '✅'
    elif text == Judgement.Lose or text == Judgement.DeemedLose:
        judgement_emoji = '❌'
    else:
        judgement_emoji = ''
    return judgement_emoji


def _message_battle_detail(_: Callable[[str], str], battle: BattleDetail, profile: Profile) -> str:
    if battle.judgement == Judgement.Win:
        judgement_text = _('{judgement_emoji} VICTORY').format(judgement_emoji=_judgement_emoji(battle.judgement))
    elif battle.judgement == Judgement.Lose or battle.judgement == Judgement.DeemedLose:
        judgement_text = _('{judgement_emoji} DEFEAT').format(judgement_emoji=_judgement_emoji(battle.judgement))
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
        _('<b>[ {judgement_text} ]</b> {count_bar}').format(judgement_text=judgement_text, count_bar=count_bar),
        _('    - Start Time: <code>{start_time}</code>').format(start_time=format_detail_time(battle.start_time.astimezone(pytz.timezone(profile.timezone)))),
        _('    - End Time: <code>{end_time}</code>').format(end_time=format_detail_time(end_time.astimezone(pytz.timezone(profile.timezone)))),
        _('    - Mode: <code>{mode}</code>').format(mode=_(ModeEnum.name(battle.mode))),
        _('    - Rule: <code>{rule}</code>').format(rule=battle.rule.name),
        _('    - Stage: <code>{stage}</code>').format(stage=battle.stage.name),
        *teams_text,
        _message_awards_detail(_, battle.awards),
    ])
    return text


def _message_count_bar(paints: list[Union[float, int]]):
    total = sum(paints)
    segments: list[int] = [int(score * 10 // total) for score in paints]
    if len(segments) == 3:
        attack_1_segment = '≈' * segments[0]
        defense_segment = '=' * (segments[1] // 2)
        attack_2_segment = '≈' * segments[2]
        return '[ {attack_1_score} {attack_1_segment}&gt;/&lt;{defense_segment} {defense_score} {defense_segment}&gt;/&lt;{attack_2_segment} {attack_2_score} ]'.format(
            attack_1_segment=attack_1_segment,
            defense_segment=defense_segment,
            attack_2_segment=attack_2_segment,
            attack_1_score=_score(paints[0]),
            defense_score=_score(paints[1]),
            attack_2_score=_score(paints[2]),
        )
    else:
        return '[ {my_score}{my_segment}&gt;/&lt;{other_segment}{other_score} ]'.format(
            my_segment='≈' * segments[0],
            other_segment='=' * segments[1],
            my_score=_score(paints[0]),
            other_score=_score(paints[1]),
        )


def _score(score: Union[float, int]) -> str:
    if isinstance(score, float):
        return f'{score:.1f}'
    elif isinstance(score, int):
        return f'{score:d}'
    else:
        return ''


def _message_team_detail(_: Callable[[str], str], team: Team, team_name: str) -> str:
    players_text = [_message_player_detail(_, play) for play in team.players]
    return '\n'.join([
        _('<b>[ {judgement_emoji} {team_name} ]</b>').format(
            judgement_emoji=_judgement_emoji(team.judgement),
            team_name=team_name,
        ),
        *players_text,
    ])


def _message_player_detail(_: Callable[[str], str], player: BattlePlayer) -> str:
    myself = '  ' if not player.myself else '*'
    if player.result is None:
        result_text = _('        - K(A)/D/SP: <code>-(-)/-/-</code>')
    else:
        result_text = _('        - K(A)/D/SP: <code>{kill}({assist})/{death}/{special}</code>').format(kill=player.result.kill, assist=player.result.assist, death=player.result.death, special=player.result.special)
    return '\n'.join([
        _('<b>{myself}  [ <code>{name}</code> ]</b>').format(myself=myself, name=html.escape(player.name)),
        _('        - Weapon: <code>{weapon}</code>').format(weapon=player.weapon.name),
        result_text,
        _('        - Point: <code>{paint}</code>').format(paint=player.paint),
    ])


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
        '    - {award_emoji} {award_text}'.format(award_emoji=_award_emoji(award.rank), award_text=award.name)
        for award in awards
    ]
    return '\n'.join([
        _('<b>[ Award ]</b>'),
        *awards_text,
    ])
