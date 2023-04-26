# Telegram-Splatoon3-Bot
## Run
```bash
pip install -r requirements.txt
python main.py -c ./config/dev.json -t <bot_token> -U <tg_user_name> -s <channel_id> --overwrite logging.level=info
```
- channel_id - id of the telegram channel used for caching image.
## Usage
commands:
- /monitor
- /schedules
- /coop_schedules
- /profiles
- /admin
