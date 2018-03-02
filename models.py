# Models description for Zhigultoken bot
from sqlalchemy import (
    Column, Integer, String, ForeignKey, Enum, DateTime, func, Float)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import settings

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    first_name = Column(String)
    last_name = Column(String)
    telegram_id = Column(Integer, unique=True)
    balance = Column(Integer, default=settings.DEFAULT_BALANCE)

    current_bet = relationship("CurrentBet", uselist=False, back_populates="user")
    bet_history = relationship("BetHistory", back_populates="user")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(
        DateTime, server_default=func.now(), server_onupdate=func.now()
    )

    def __repr__(self):
        return "<User(first_name={0}, last_name={1}, telegram_id={2})>".format(
            self.first_name, self.last_name, self.telegram_id)


class BetMixin(object):
     amount = Column(Integer, default=settings.DEFAULT_BET)
     bet_type = Column(Enum(settings.BetType))
     bet_source = Column(Enum(settings.BetSource))
     created_at = Column(DateTime, server_default=func.now())


class CurrentBet(BetMixin, Base):
     __tablename__ = 'current_bets'
     id = Column(Integer, primary_key=True)
     user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
     user = relationship("User", back_populates="current_bet")

     def __repr__(self):
        return "<CurrentBet(user_id='{0}', bet_type='{1}', bet_source='{2}')>".format(
            self.user_id, self.bet_type, self.bet_source)


class BetHistory(BetMixin, Base):
    __tablename__ = 'bet_history'
    result = Column(Integer)
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    user = relationship("User", back_populates="bet_history")


class SystemMixin(object):
    current_price = Column(Float)
    predicted_price = Column(Float)


class SystemHistory(SystemMixin, Base):
    __tablename__ = 'system_history'
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, server_default=func.now())


class SystemState(SystemMixin, Base):
    __tablename__ = 'system_state'
    id = Column(Integer, primary_key=True)
    updated_at = Column(
        DateTime, server_default=func.now(), server_onupdate=func.now()
    )
    previous_price = Column(Float)


class NextState(Base):
    __tablename__ = 'next_states'
    id = Column(Integer, primary_key=True)
    future_price = Column(Float)

if __name__ == '__main__':

    # Create database
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.exc import IntegrityError

    import os
    conn_str = 'postgresql://{user}:{password}@{host}:{port}/{db_name}'
    engine = create_engine(
        conn_str.format(
            user=os.getenv('APP_USER', 'zhigulbot_user'),
            password=os.getenv('APP_USER_PASSWORD', 'zhigulbot_password'),
            host=os.getenv('APP_HOST', 'zhigultoken-db'),
            port=os.getenv('APP_PORT', 5432),
            db_name=os.getenv('APP_DATABASE', 'zhigulbot'),
            )
        )
    Base.metadata.create_all(engine)
    
    # Set initial state
    with open('data/initial_state.csv', 'r') as secret_file:
        previous_price, current_price, prediction = secret_file.read().split(',')
    initial_state = SystemState(
        previous_price=previous_price,
        current_price=current_price,
        predicted_price=prediction
        )
    Session = sessionmaker(bind=engine)
    session = Session()
    session.add(initial_state)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        print('Initial state already added')

    # Create history
    with open('data/train.csv', 'r') as history_file:
        history_list = list(map(float, history_file))

    price_history_objects = []
    for i in range(len(history_list)):
        current_price = history_list[i]
        prediction = 0.0
        price_history_objects.append(
            SystemHistory(
                id=i+1,
                current_price=current_price,
                predicted_price=prediction
            )
        )
    session.bulk_save_objects(price_history_objects)
    session.commit()
    # Update sequence object
    session.execute(
        "ALTER SEQUENCE {0}_id_seq RESTART WITH {1}".format(
            SystemHistory.__tablename__, len(price_history_objects) + 1))

    # Create future states
    with open('data/test.csv', 'r') as future_file:
        future_list = list(map(float, future_file))

    future_price_objects = []
    for i in range(len(future_list)):
        future_price = future_list[i]
        future_price_objects.append(
            NextState(
                id=i+1,
                future_price=future_price
            )
        )
    session.bulk_save_objects(future_price_objects)
    session.commit()
    # Update sequence object
    session.execute(
        "ALTER SEQUENCE {0}_id_seq RESTART WITH {1}".format(
            NextState.__tablename__, len(future_price_objects) + 1))

