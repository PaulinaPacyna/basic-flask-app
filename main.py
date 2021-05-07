import datetime
import pandas as pd
import pyodbc
import numpy as np
import requests
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__, template_folder='./')

connection = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};Server=PINA;Database=HW1;UID=sa;PWD=ieShe6Oh')

cursor = connection.cursor()


@app.route('/')
def index():
    return redirect(url_for('games'))


def make_where(statements):
    if not statements:
        return ''
    else:
        return 'where ' + ' and '.join(statements)


@app.route('/games')
def games():
    params = []
    statements = []
    game_name = request.args.get('game_name')
    if game_name:
        params += ['%' + game_name + '%']
        statements += ['GAME_NAME like ?']
    start = request.args.get('start')
    if start:
        params += [start]
        statements += ['RELEASE_date >= ?']
    end = request.args.get('end')
    if end:
        params += [end]
        statements += ['RELEASE_date <= ?']
    score = request.args.get('score')
    if score:
        params += [score]
        statements += ['SCORE >= ?']

    data = cursor.execute('SELECT * FROM Games ' + make_where(statements), *params)
    return render_template('games.html', data=data)


@app.route('/buy', methods=["POST"])
def buy():
    id = request.form.get('id')
    game = cursor.execute('SELECT GAME_ID, GAME_NAME, RELEASE_DATE, PRICE, Score FROM ' +
                          'Games where GAME_ID = ?', id).fetchone()
    order_id = 1 + cursor.execute("SELECT MAX(ORDER_ID) FROM ORDERS").fetchone()[0]
    today = datetime.date.today()
    discount = (today - game[2]) < datetime.timedelta(days=365 * 3)
    u = cursor.execute("INSERT  INTO Orders(ORDER_ID,ORDER_DATE,GAME_ID,NET_AMOUNT,DISCOUNT,GROSS_AMOUNT)" +
                       "VALUES(?, ?, ?, ?, ?, ?)",
                       order_id,
                       today.strftime("%Y-%m-%d"),
                       id,
                       game[3],
                       0.2 if discount else None,
                       1
                       )
    print(u)
    cursor.commit()
    return f"""
    <p>You have bought \"{game[1]}\" game</p>
    <a href="/" role="button" >Go back </a>
    """


@app.route('/orders', methods=['GET'])
def get_orders():
    data = cursor.execute("""SELECT ORDER_ID, ORDER_DATE, DISCOUNT, GROSS_AMOUNT,  GAME_NAME, round(PRICE, 2) as PRICE
                            FROM ORDERS O JOIN GAMES G ON G.GAME_ID=O.GAME_ID""").fetchall()
    data = pd.DataFrame([list(d) for d in data],
                        columns=['ORDER_ID', 'ORDER_DATE', 'DISCOUNT', 'GROSS_AMOUNT',  'GAME_NAME', 'PRICE'])
    data['GROSS_AMOUNT'] = data['GROSS_AMOUNT'].astype(float)
    data['GROSS_AMOUNT'] = np.round(data['GROSS_AMOUNT'], 2)
    data['PRICE'] = data['PRICE'].astype(float)
    data['PRICE'] = np.round(data['PRICE'], 2)
    return render_template("orders.html", data=data.to_records())


app.run(debug=True)
connection.close()
