# -*- coding: utf8 -*-
import logging
import telebot
import settings
import random

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError, OperationalError

from models import User, CurrentBet, SystemState

# Init session connection
engine = create_engine(settings.DB_URI)
Session = sessionmaker(bind=engine)
session = Session()

# Init logging
logger = telebot.logger
telebot.logger.setLevel(logging.DEBUG)

# Init bot
bot = telebot.TeleBot(settings.TELEGRAM_TOKEN)

@bot.message_handler(commands=['start'])
def setup_keyboard_and_user(message):
    logger.warning(message)

    # Create new user record if not exist
    try:
        user = User(
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
            telegram_id=message.from_user.id
        )
        session.add(user)
        session.commit()
    except IntegrityError:
        session.rollback()
        logger.warning("User: {0} already exist".format(
            message.from_user.id
            )
        )

    user = session.query(User).filter_by(
        telegram_id=message.from_user.id).first() 

    user_markup = telebot.types.ReplyKeyboardMarkup(True, False)
    user_markup.row(settings.KEYBOARD_UP.decode('utf8'), settings.KEYBOARD_DOWN.decode('utf8'))
    user_markup.add(
        settings.KEYBOARD_RANDOM.decode('utf8'),
        settings.KEYBOARD_CHART_SHORT.decode('utf8')
    )
    user_markup.add(
        settings.KEYBOARD_CHART.decode('utf8'),
        settings.KEYBOARD_CASHIER.decode('utf8'))
    bot.send_message(
        message.from_user.id,
        random.choice(settings.TXT_BET_BALANCE).format(user.balance),
        reply_markup=user_markup
    )


@bot.message_handler(
    content_types=["text"],
    func=lambda mes: mes.text.encode('utf8') in (settings.KEYBOARD_CHART, settings.KEYBOARD_CHART_SHORT))
def send_chart(message):
    logger.warning(message)
    state = session.query(SystemState).first()
    bot.send_message(
        message.chat.id,
        settings.TXT_CHART.format(
            state.previous_price,
            state.current_price,
            state.predicted_price
            )
    )
    if message.text.encode('utf8') == settings.KEYBOARD_CHART_SHORT:
        photo = open(settings.CHART_14, 'rb')
        bot.send_photo(message.chat.id, photo)
    else:
        for img_path in settings.ALL_CHARTS:
            photo = open(img_path[0], 'rb')
            bot.send_photo(message.chat.id, photo)


@bot.message_handler(
    content_types=["text"],
    func=lambda mes: mes.text.encode('utf8') in (
        settings.KEYBOARD_UP,
        settings.KEYBOARD_DOWN,
        settings.KEYBOARD_RANDOM)
    )
def make_bet(message):
    # Get current user
    user = session.query(User).filter_by(
        telegram_id=message.from_user.id).first()
    if user.balance < settings.DEFAULT_BET:
        bot.send_message(message.chat.id, settings.TXT_NO_MONEY)
        return None

    # Get system state
    system_state = session.query(SystemState).first()
    
    # Define bets direction and type
    if message.text.encode('utf8') == settings.KEYBOARD_RANDOM:
        bet_source = settings.BetSource.oracle
        if system_state.current_price >= system_state.predicted_price:
            bet_type = settings.BetType.down
        else:
            bet_type = settings.BetType.up
    else:
        bet_source = settings.BetSource.user
        if message.text.encode('utf8') == settings.KEYBOARD_UP:
            bet_type = settings.BetType.up
        else:
            bet_type = settings.BetType.down
    
    # Make a bet
    try:
        bet = CurrentBet(
            bet_type=bet_type,
            bet_source=bet_source,
            user=user
        )
        session.add(bet)
        session.commit()
        bot.send_message(message.chat.id, random.choice(settings.TXT_BET_RESPONSE))
    except IntegrityError:
        session.rollback()
        logger.warning("Current bet: {0} already exist".format(
            message.from_user.id
            )
        )
        bot.send_message(message.chat.id, settings.TXT_BET_DONE)
    except OperationalError:
        session.rollback()
        logger.warning("System state change".format(
            message.from_user.id
            )
        )
        bot.send_message(message.chat.id, settings.TXT_BET_LOCK)


@bot.message_handler(
    content_types=["text"],
    func=lambda mes: settings.KEYBOARD_CASHIER == mes.text.encode('utf8'))
def show_cashier(message):
    """
    Return balance info
    """
    user = session.query(User).filter_by(
        telegram_id=message.from_user.id).first()
    bot.send_message(message.chat.id, random.choice(settings.TXT_BET_BALANCE).format(user.balance))


@bot.message_handler(content_types=["text"])
def any_msg(message):
    """
    Process all messages
    """
    bot.send_message(
        message.chat.id,
        settings.TXT_AI_FIRST
    )

if __name__ == '__main__':
    bot.polling(none_stop=True)