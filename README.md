# ZhigulCoinBot
Telegram chatbot for ZhigulCoin binary options trading with ML assistant for [OhMyHack](https://www.hackathon.pravo.ru/) hackaton in Samara 2018.

System simulates stock changes every `SYSTEM_UPDATE_PERIOD` minutes and update state - predictions, current price, charts and process all bets.
Model is trained in *.ipynb file and serialized.

In general it's Telegram interface with simple long-polling backend + periodic celery tasks.

# How to install & start

Required `docker` and `docker-compose` installed

1. Create `infranginx_default` docker network (was too lazy to change it).
2. Add your telegram token to app folder in `secret.txt`
3. Do `docker-compose build`
4. Do `docker-compose up -d`
5. Then you need to feed initial data. Join web container `docker exec -it zhigultokenbot_web_1 /bin/bash`.
6. Do `python3 models.py`
7. Can require `docker-compose restart`.

