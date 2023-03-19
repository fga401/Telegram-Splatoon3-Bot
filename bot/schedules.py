import datetime
import json
import logging

from bot.data import Schedules, BattleSchedule, BattleSetting, JobSchedule, JobSetting, Rule, Stage, Weapon

logger = logging.getLogger('bot.schedules')


def parse_schedules(data: str) -> Schedules:
    data = json.loads(data)
    regular_schedules = [
        BattleSchedule(
            setting=BattleSetting(
                rule=Rule(
                    id=node['regularMatchSetting']['vsRule']['rule'],
                    name=node['regularMatchSetting']['vsRule']['name'],
                ),
                stage=(
                    Stage(
                        id=node['regularMatchSetting']['vsStages'][0]['id'],
                        name=node['regularMatchSetting']['vsStages'][0]['name'],
                        image_url=node['regularMatchSetting']['vsStages'][0]['image']['url'],
                    ),
                    Stage(
                        id=node['regularMatchSetting']['vsStages'][1]['id'],
                        name=node['regularMatchSetting']['vsStages'][1]['name'],
                        image_url=node['regularMatchSetting']['vsStages'][1]['image']['url'],
                    ),
                )
            ),
            start_time=datetime.datetime.fromisoformat(node['startTime']),
            end_time=datetime.datetime.fromisoformat(node['endTime']),
        )
        for node in data['data']['regularSchedules']['nodes']
    ]
    challenge_schedules = [
        BattleSchedule(
            setting=BattleSetting(
                rule=Rule(
                    id=node['bankaraMatchSettings'][0]['vsRule']['rule'],
                    name=node['bankaraMatchSettings'][0]['vsRule']['name'],
                ),
                stage=(
                    Stage(
                        id=node['bankaraMatchSettings'][0]['vsStages'][0]['id'],
                        name=node['bankaraMatchSettings'][0]['vsStages'][0]['name'],
                        image_url=node['bankaraMatchSettings'][0]['vsStages'][0]['image']['url'],
                    ),
                    Stage(
                        id=node['bankaraMatchSettings'][0]['vsStages'][1]['id'],
                        name=node['bankaraMatchSettings'][0]['vsStages'][1]['name'],
                        image_url=node['bankaraMatchSettings'][0]['vsStages'][1]['image']['url'],
                    ),
                )
            ),
            start_time=datetime.datetime.fromisoformat(node['startTime']),
            end_time=datetime.datetime.fromisoformat(node['endTime']),
        )
        for node in data['data']['bankaraSchedules']['nodes']
    ]
    open_schedules = [
        BattleSchedule(
            setting=BattleSetting(
                rule=Rule(
                    id=node['bankaraMatchSettings'][1]['vsRule']['rule'],
                    name=node['bankaraMatchSettings'][1]['vsRule']['name'],
                ),
                stage=(
                    Stage(
                        id=node['bankaraMatchSettings'][1]['vsStages'][0]['id'],
                        name=node['bankaraMatchSettings'][1]['vsStages'][0]['name'],
                        image_url=node['bankaraMatchSettings'][1]['vsStages'][0]['image']['url'],
                    ),
                    Stage(
                        id=node['bankaraMatchSettings'][1]['vsStages'][1]['id'],
                        name=node['bankaraMatchSettings'][1]['vsStages'][1]['name'],
                        image_url=node['bankaraMatchSettings'][1]['vsStages'][1]['image']['url'],
                    ),
                )
            ),
            start_time=datetime.datetime.fromisoformat(node['startTime']),
            end_time=datetime.datetime.fromisoformat(node['endTime']),
        )
        for node in data['data']['bankaraSchedules']['nodes']
    ]
    x_schedules = [
        BattleSchedule(
            setting=BattleSetting(
                rule=Rule(
                    id=node['xMatchSetting']['vsRule']['rule'],
                    name=node['xMatchSetting']['vsRule']['name'],
                ),
                stage=(
                    Stage(
                        id=node['xMatchSetting']['vsStages'][0]['id'],
                        name=node['xMatchSetting']['vsStages'][0]['name'],
                        image_url=node['xMatchSetting']['vsStages'][0]['image']['url'],
                    ),
                    Stage(
                        id=node['xMatchSetting']['vsStages'][1]['id'],
                        name=node['xMatchSetting']['vsStages'][1]['name'],
                        image_url=node['xMatchSetting']['vsStages'][1]['image']['url'],
                    ),
                ),
            ),
            start_time=datetime.datetime.fromisoformat(node['startTime']),
            end_time=datetime.datetime.fromisoformat(node['endTime']),
        )
        for node in data['data']['xSchedules']['nodes']
    ]
    coop_schedules = [
        JobSchedule(
            setting=JobSetting(
                stage=Stage(
                    id=node['setting']['coopStage']['id'],
                    name=node['setting']['coopStage']['name'],
                    image_url=node['setting']['coopStage']['thumbnailImage']['url'],
                ),
                weapon=(
                    Weapon(
                        name=node['setting']['weapons'][0]['name'],
                        image_url=node['setting']['weapons'][0]['image']['url'],
                    ),
                    Weapon(
                        name=node['setting']['weapons'][1]['name'],
                        image_url=node['setting']['weapons'][1]['image']['url'],
                    ),
                    Weapon(
                        name=node['setting']['weapons'][2]['name'],
                        image_url=node['setting']['weapons'][2]['image']['url'],
                    ),
                    Weapon(
                        name=node['setting']['weapons'][3]['name'],
                        image_url=node['setting']['weapons'][3]['image']['url'],
                    ),
                )
            ),
            start_time=datetime.datetime.fromisoformat(node['startTime']),
            end_time=datetime.datetime.fromisoformat(node['endTime']),
        )
        for node in data['data']['coopGroupingSchedule']['regularSchedules']['nodes']
    ]

    return Schedules(
        regular=regular_schedules,
        challenge=challenge_schedules,
        open=open_schedules,
        x=x_schedules,
        coop=coop_schedules,
    )
