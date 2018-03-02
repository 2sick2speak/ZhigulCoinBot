import os
import enum

# Get token
with open('secret.txt', 'r') as secret_file:
    TELEGRAM_TOKEN = secret_file.read().strip('\n')

DB_URI = 'postgresql://{user}:{password}@{host}:{port}/{db_name}'.format(
    user=os.getenv('APP_USER', 'zhigulbot_user'),
    password=os.getenv('APP_USER_PASSWORD', 'zhigulbot_password'),
    host=os.getenv('APP_HOST', 'zhigultoken-db'),
    port=os.getenv('APP_PORT', 5432),
    db_name=os.getenv('APP_DATABASE', 'zhigulbot'),
)
# Keyboard text
# Dirty hacks with byte representations for emoji support
KEYBOARD_UP = b'\xf0\x9f\x9a\x80 ' + str.encode('Топим вверх')
KEYBOARD_DOWN = b'\xf0\x9f\x9a\xbd ' + str.encode('Сливаем')
KEYBOARD_RANDOM = b'\xf0\x9f\x99\x8f ' + str.encode('Согласен с оракулом')
KEYBOARD_CHART = b'\xf0\x9f\x93\x91 ' + str.encode('Историческая справка')
KEYBOARD_CASHIER = b'\xf0\x9f\x92\xb0 ' + str.encode('Мой счет')
KEYBOARD_CHART_SHORT = b'\xf0\x9f\x93\x88 ' + str.encode('Teкущий курс')

# System setup

DEFAULT_BALANCE = 3000
DEFAULT_BET = 10
SYSTEM_UPDATE_PERIOD = 10 # In minutes

class BetSource(enum.Enum):
    user = 1
    oracle = 2

class BetType(enum.Enum):
    up = 1
    down = 2

# Bot responses

TXT_BET_RESPONSE = [
    'Чотко, дерзко',
    'Воу, воу, полегче',
]

TXT_BET_BALANCE = [
    'Ваш баланс: {0}. Крутите барабан!',
    'Количество доступных жигулькоинов: {0}'
]

TXT_CHART = "Текущее состояние жигулькоина: цена изменилась {0} -> {1}. Оракул предсказывает {2}"
TXT_NO_MONEY = "Все полимеры потрачены"
TXT_BET_DONE = """Ставки сделаны, ставок больше нет.
Cледующая ставка возможна при изменении системы через {0} минут
""".format(SYSTEM_UPDATE_PERIOD)
TXT_BET_LOCK = "Пересчитываем состояние системы. Попробуйте через пару секунд"
TXT_AI_FIRST = "Поддержка естественного языка и general AI будет после ICO"

# Chart path

CHART_ALL = 'images/chart_all.png'
CHART_60 = 'images/chart_60.png'
CHART_14 = 'images/chart_14.png'
ALL_CHARTS = [
    (CHART_ALL, 'Исторический график жигулькойна за все время', -1),
    (CHART_60, 'Исторический график жигулькойна за 2 месяца', 60),
    (CHART_14, 'Исторический график жигулькойна за 2 недели', 14)
]

# ML Model path

ML_MODEL_PATH = 'trained_model/xgboost_predict.model'
MODEL_DEPTH = 60