from celery import Celery
import settings
import models
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# ML & DS Libs
import matplotlib
matplotlib.use('Agg')
import pandas as pd
import numpy as np
import xgboost as xgb

app = Celery()

# Load xgboost model
bst = xgb.Booster({'nthread': 4})
bst.load_model(settings.ML_MODEL_PATH)

@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # Calls global_update
    sender.add_periodic_task(
        60.0, #* settings.SYSTEM_UPDATE_PERIOD,
        global_update,
    name='Update system')

@app.task
def global_update():
    print("System update start")

    # Init session connection
    engine = create_engine(settings.DB_URI)
    Session = sessionmaker(bind=engine)
    session = Session()
    session.execute("BEGIN WORK")
    _process_bets(session, engine)
    session.execute("COMMIT WORK")
    session.close()
    print("Start update charts")
    _plot_all_graphs(engine)
    print("End update charts")
    print("System update end")


def _process_bets(session, engine):
    """Process all bets and count differenct"""
    # Lock state tables
    for state_models in (models.CurrentBet, models.SystemState):
        session.execute("LOCK TABLE {0} IN ACCESS EXCLUSIVE MODE".format(
            state_models.__tablename__))

    all_bets = session.query(models.CurrentBet).all()
    current_state = session.query(models.SystemState).one()
    new_price = _get_next_state(session)
    print("Total bets to process: {0}".format(len(all_bets)))
    print("Processing bets")
    for bet in all_bets:
        balance_diff = _select_winner(
            bet, new_price, current_state.current_price, settings.DEFAULT_BET)

        bet.user.balance += balance_diff
        print(
            "Bet processing: new price {0} current_price {1} user_id {2} bet_type {3} balance {4} diff {5}".format(
                new_price,
                current_state.current_price,
                bet.user.id,
                bet.bet_type,
                bet.user.balance,
                balance_diff
            )
        )
        session.add(bet.user)
        # Save to bet history
        history_record = models.BetHistory(
            result=balance_diff,
            user=bet.user,
            bet_type=bet.bet_type,
            bet_source=bet.bet_source
            )
        session.add(history_record)
        session.commit()

    # Update state
    _update_state(session, engine, current_state, new_price)
    print("Processing complete")
    # Clear current bets table
    print("Delete bets")
    session.execute("TRUNCATE TABLE {0}".format(
        models.CurrentBet.__tablename__))


def _update_state(session, engine, current_state, new_price):
    """Update current state"""
    # Save history
    history_record = models.SystemHistory(
        current_price=current_state.current_price,
        predicted_price=current_state.predicted_price)
    session.add(history_record)
    session.commit()
    prediction = _predict_by_ml(engine)
    print("Prediction: {0} New price: {1}".format(prediction[0], new_price))
    # Update state
    current_state.predicted_price = float(prediction[0])
    current_state.previous_price = current_state.current_price
    current_state.current_price = new_price
    session.add(current_state)
    session.commit()


def _select_winner(bet, future_price, current_price, bet_size):
    if future_price == current_price:
        return 0.0
    if bet.bet_type == settings.BetType.up and future_price >= current_price:
        return bet_size
    if bet.bet_type == settings.BetType.down and future_price > current_price:
        return -bet_size
    if bet.bet_type == settings.BetType.up and future_price < current_price:
        return  -bet_size
    if bet.bet_type == settings.BetType.down and future_price < current_price:
        return bet_size


def _get_next_state(session):
    """Run through next state table and get next state"""
    next_state = session.query(models.NextState).order_by(models.NextState.id).first()
    print("Select next state id: {0} price: {1} states left: {2}".format(
        next_state.id, next_state.future_price, session.query(models.NextState).count()))
    next_price = next_state.future_price
    session.delete(next_state)
    session.commit()
    return next_price

def _plot_all_graphs(engine):
    df = pd.read_sql("select current_price from {0}".format(
        models.SystemHistory.__tablename__), engine)
    df.columns = ['ZGLCOIN63']
    for chart_meta in settings.ALL_CHARTS:
        _plot_graph(df, chart_meta)


def _plot_graph(df, chart_meta):
    """Plot single chart"""
    df_slice = df.copy()
    # Slice dataframe
    if chart_meta[2] != -1:
        df_slice = df.ix[df.index[-chart_meta[2]:]]
    # Fit trand line
    z = np.polyfit(df_slice['ZGLCOIN63'].index.values, df_slice['ZGLCOIN63'].values, 1)
    p = np.poly1d(z)
    df_slice['trend'] = p(df_slice['ZGLCOIN63'].index.values)
    df_slice.plot(figsize=(14, 5), title=chart_meta[1]).get_figure().savefig(chart_meta[0])


def _predict_by_ml(engine):
    df = pd.read_sql(
        "select current_price from {0} order by id desc limit {1}".format(
            models.SystemHistory.__tablename__, settings.MODEL_DEPTH), engine)
    raw_prices = df['current_price'].tolist()
    raw_prices.reverse()
    feature_list = _feature_extraction(
        raw_prices
    )
    prediction = bst.predict(
        xgb.DMatrix(feature_list)
    )
    return prediction

def _feature_extraction(line):
    # Max min features
    feature_list = []
    last_week = line[-7:]
    last_month = line[-30:]
    for slices in (last_week, last_month, line):
        feature_list.extend([np.max(slices), np.min(slices), np.median(slices), np.mean(slices)])

    # Raw last month values
    feature_list.extend(last_month)
    # Day-to-day diffs
    feature_list.extend(_day_to_day_diff(last_month))
    last_month_mean = np.mean(last_month)
    # Diffs from average
    feature_list.extend([day_value - last_month_mean for day_value in last_month])
    return feature_list

def _day_to_day_diff(line):
    return [line[i + 1] - line[i] for i in range(0, len(line) - 1)]
