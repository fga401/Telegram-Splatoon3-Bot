import collections
import datetime
import json
from typing import Callable

import pytz

from bot.data import CoopDetail, Profile, Coop, CommonParser, BossResult, Boss, CoopPlayerResult, CoopPlayer, Uniform, SpecialWeapon, WaveResult, EventWave, EnemyResult, Enemy, ScaleResult
from bot.utils import format_detail_time


class CoopParser:
    @staticmethod
    def coop_histories(histories: str) -> list[Coop]:
        data = json.loads(histories)
        return [
            Coop(
                id=node['id'],
                after_grade_name=node['afterGrade']['name'],
                after_grade_point=node['afterGradePoint'],
                grade_point_diff=node['gradePointDiff'],
                stage=CommonParser.stage(node['coopStage'], image_name=None),
                weapons=[
                    CommonParser.weapon(weapon)
                    for weapon in node['weapons']
                ],
                boss=CoopParser.__boss_result(node['bossResult'])
            )
            for group in data['data']['coopResult']['historyGroups']['nodes'] for node in group['historyDetails']['nodes']
        ]

    @staticmethod
    def coop_detail(detail: str) -> CoopDetail:
        data = json.loads(detail)
        node = data['data']['coopHistoryDetail']
        return CoopDetail(
            id=node['id'],
            after_grade_name=node['afterGrade']['name'],
            after_grade_point=node['afterGradePoint'],
            grade_point_diff=None,
            stage=CommonParser.stage(node['coopStage']),
            weapons=[
                CommonParser.weapon(weapon)
                for weapon in node['weapons']
            ],
            boss=CoopParser.__boss_result(node['bossResult']),
            result_wave=node['resultWave'],
            my_result=CoopParser.__coop_player_result(node['myResult']),
            member_results=[
                CoopParser.__coop_player_result(result)
                for result in node['memberResults']
            ],
            wave_results=[
                CoopParser.__wave_result(result)
                for result in node['waveResults']
            ],
            enemy_results=[
                EnemyResult(
                    defeat_count=result['defeatCount'],
                    team_defeat_count=result['teamDefeatCount'],
                    pop_count=result['popCount'],
                    enemy=Enemy(
                        id=result['enemy']['id'],
                        name=result['enemy']['name'],
                        image_url=result['enemy']['image']['url'],
                    ),
                )
                for result in node['enemyResults']
            ],
            start_time=datetime.datetime.fromisoformat(node['playedTime']),
            rule=node['rule'],
            danger=node['dangerRate'],
            smell=node['smellMeter'],
            scale=CoopParser.__scale_result(node['scale']),
            job_point=node['jobPoint'],
            job_score=node['jobScore'],
            job_rate=node['jobRate'],
            job_bonus=node['jobBonus'],
        )

    @staticmethod
    def __boss_result(node) -> BossResult | None:
        if node is None:
            return None
        if 'image' in node['boss']:
            image_url = node['boss']['image']['url']
        else:
            image_url = ''
        return BossResult(
            defeat_boss=node['hasDefeatBoss'],
            boss=Boss(
                id=node['boss']['id'],
                name=node['boss']['name'],
                image_url=image_url,
            ),
        )

    @staticmethod
    def __coop_player_result(node) -> CoopPlayerResult:
        return CoopPlayerResult(
            player=CoopParser.__coop_player(node['player']),
            weapons=[
                CommonParser.weapon(weapon)
                for weapon in node['weapons']
            ],
            special_weapon=CoopParser.__special_weapon(node['specialWeapon']),
            defeat_enemy_count=node['defeatEnemyCount'],
            deliver_count=node['deliverCount'],
            golden_assist_count=node['goldenAssistCount'],
            golden_deliver_count=node['goldenDeliverCount'],
            rescue_count=node['rescueCount'],
            rescued_count=node['rescuedCount']
        )

    @staticmethod
    def __coop_player(node) -> CoopPlayer:
        return CoopPlayer(
            id=node['id'],
            name=node['name'],
            byname=node['byname'],
            name_id=node['nameId'],
            nameplate=CommonParser.nameplate(node['nameplate']),
            uniform=Uniform(
                id=node['uniform']['id'],
                name=node['uniform']['name'],
                image_url=node['uniform']['image']['url'],
            ),
        )

    @staticmethod
    def __special_weapon(node) -> SpecialWeapon:
        return SpecialWeapon(
            id=node.get('id', ''),
            weapon_id=node.get('weaponId', 0),
            name=node['name'],
            image_url=node['image']['url'],
        )

    @staticmethod
    def __wave_result(node) -> WaveResult:
        if node['eventWave'] is not None:
            event_wave = EventWave(
                id=node['eventWave']['id'],
                name=node['eventWave']['name'],
            )
        else:
            event_wave = None
        return WaveResult(
            wave_number=node['waveNumber'],
            water_level=node['waterLevel'],
            event_wave=event_wave,
            deliver_norm=node['deliverNorm'],
            golden_pop_count=node['goldenPopCount'],
            team_deliver_count=node['teamDeliverCount'],
            special_weapons=[
                CoopParser.__special_weapon(sp)
                for sp in node['specialWeapons']
            ]
        )

    @staticmethod
    def __scale_result(node) -> ScaleResult | None:
        if node is None:
            return None
        return ScaleResult(
            gold=node['gold'],
            silver=node['silver'],
            bronze=node['bronze'],
        )


def _clean_emoji(clean: bool) -> str:
    if clean:
        return '✅'
    else:
        return '❌'


def _message_coop_detail(_: Callable[[str], str], coop: CoopDetail, profile: Profile) -> str:
    if coop.clean:
        judgement_text = _('{clean_emoji} CLEAN').format(clean_emoji=_clean_emoji(coop.clean))
    else:
        judgement_text = _('{clean_emoji} DEFEAT').format(clean_emoji=_clean_emoji(coop.clean))
    smell_bar = _message_smell_bar(coop.smell)
    player_results = [coop.my_result, *coop.member_results]
    text = '\n'.join(filter(lambda s: s is not None, [
        _('<b>[ {judgement_text} ]</b>  {smell_bar}'),
        _('    - Start Time: <code>{start_time}</code>'),
        _('    - Stage: <code>{stage}</code>'),
        _('    - Hazard Level: <code>{danger}%</code>'),
        _('    - grade: <code>{grade_name} {grade_point}</code>'),
        _('    - Point: <code>{job_score} * {job_rate} + {job_bonus} = {job_point}</code>'),
        _('    - Count:  🟡 <code>{golden_deliver_count}</code>    🟠 <code>{deliver_count}</code>'),
        _message_scale_bar(_, coop.scale),
        _('<b>[ Waves ]</b>'),
        *[_message_wave(_, wave, coop.boss, coop.result_wave == 0 or coop.result_wave > wave.wave_number) for wave in coop.wave_results],
        _('<b>[ Team ]</b>'),
        *[_message_player(_, player) for player in player_results],
        _('<b>[ Boss Defeated ]</b>'),
        *[_message_enemy(_, enemy) for enemy in coop.enemy_results],
    ])).format(
        judgement_text=judgement_text, smell_bar=smell_bar,
        start_time=format_detail_time(coop.start_time.astimezone(pytz.timezone(profile.timezone))),
        stage=coop.stage.name,
        danger=f'{int(coop.danger * 100):d}',
        grade_name=coop.after_grade_name, grade_point=coop.after_grade_point,
        job_score=coop.job_score, job_rate=coop.job_rate, job_bonus=coop.job_bonus, job_point=coop.job_point,
        golden_deliver_count=sum([player.golden_deliver_count for player in player_results]),
        deliver_count=sum([player.deliver_count for player in player_results]),
    )
    return text


def _message_smell_bar(smell: int) -> str:
    remain = 5 - smell
    return '[ ({smell}/5) {smell_segment}&gt;{remain_segment} ]'.format(
        smell=smell,
        smell_segment='=' * smell,
        remain_segment='-' * remain,
    )


def _message_scale_bar(_: Callable[[str], str], scale: ScaleResult) -> str | None:
    if scale is None:
        return None
    return _('    - Scale:  🥉 <code>{bronze}</code>    🥈 <code>{silver}</code>    🥇 <code>{gold}</code>').format(
        gold=scale.gold,
        silver=scale.silver,
        bronze=scale.bronze,
    )


def _message_wave(_: Callable[[str], str], wave: WaveResult, boss_result: BossResult, clean: bool) -> str:
    if wave.wave_number == 4:
        wave_name = 'XTRAWAVE'
        wave_banner = boss_result.boss.name
    else:
        wave_name = _('Wave {wave_number}').format(wave_number=wave.wave_number)
        wave_banner = '{team_deliver_count}/{deliver_norm}  [{golden_pop_count}]'.format(
            team_deliver_count=wave.team_deliver_count,
            deliver_norm=wave.deliver_norm,
            golden_pop_count=wave.golden_pop_count,
        )
    if wave.water_level == 2:
        tide = _('High Tide')
    elif wave.water_level == 1:
        tide = _('Normal Tide')
    elif wave.water_level == 0:
        tide = _('Low Tide')
    else:
        tide = ''
    if wave.event_wave is not None:
        event = _('        - Event: <code>{event}</code>').format(event=wave.event_wave.name)
    else:
        event = None
    text = '\n'.join(filter(lambda s: s is not None, [
        _('    <b>[ {clean_emoji} {wave_name} ]</b>  <code>{wave_banner}</code>'),
        _('        - Tide: <code>{tide}</code>'),
        event,
        _message_wave_sp(_, wave),
    ])).format(
        clean_emoji=_clean_emoji(clean),
        wave_name=wave_name,
        wave_banner=wave_banner,
        tide=tide,
        golden_pop_count=wave.golden_pop_count,
    )
    return text


def _message_wave_sp(_: Callable[[str], str], wave: WaveResult) -> str | None:
    if len(wave.special_weapons) == 0:
        return None
    sp_count = collections.Counter([sp.name for sp in wave.special_weapons])
    text = '\n'.join([
        _('        - Special Weapons:'),
        *[_('            - <code>{sp}</code>{cnt}').format(sp=sp, cnt=f'<b>  *  {cnt}</b>' if cnt > 1 else '') for sp, cnt in sp_count.items()],
    ])
    return text


def _message_player(_: Callable[[str], str], player: CoopPlayerResult) -> str:
    text = '\n'.join([
        _('    <b>[ <code>{player_name}</code> ]</b>'),
        _('        - Boss Defeated: <code>{defeat_enemy_count}</code>'),
        _('        - Deliver:  🟡 <code>{golden_deliver_count}({golden_assist_count})</code>    🟠 <code>{deliver_count}</code>'),
        _('        - Rescue:  🛟 <code>{rescue_count}</code>    ☠ <code>{rescued_count}</code>'),
        _('        - Weapons:'),
        *[_('            - <code>{weapon}</code>').format(weapon=weapon.name) for weapon in player.weapons],
        _('        - Special Weapon: <code>{special_weapon}</code>'),
    ]).format(
        player_name=player.player.name,
        defeat_enemy_count=player.defeat_enemy_count,
        golden_deliver_count=player.golden_deliver_count,
        golden_assist_count=player.golden_assist_count,
        deliver_count=player.deliver_count,
        rescue_count=player.rescue_count,
        rescued_count=player.rescued_count,
        special_weapon=player.special_weapon.name,
    )
    return text


def _message_enemy(_: Callable[[str], str], enemy: EnemyResult) -> str:
    if enemy.team_defeat_count == enemy.pop_count:
        clean = '  <b>Clean!</b>'
    else:
        clean = ''
    return _('    - <code>{enemy_name}</code>:  <code>{team_defeat_count}({defeat_count})/{pop_count}</code>{clean}').format(
        enemy_name=enemy.enemy.name,
        team_defeat_count=enemy.team_defeat_count,
        defeat_count=enemy.defeat_count,
        pop_count=enemy.pop_count,
        clean=clean,
    )
