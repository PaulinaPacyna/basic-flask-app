import datetime
import pandas as pd
import pyodbc
import numpy as np
import requests
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__, template_folder="./")


def get_connection():
    return pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};Server=PINA;Database=HW1;UID=sa;PWD=ieShe6Oh"
    )


@app.route("/")
def index():
    return redirect(url_for("games"))


def make_where(statements):
    if not statements:
        return ""
    else:
        return "where " + " and ".join(statements)


@app.route("/games")
def games():
    params = []
    statements = []
    game_name = request.args.get("game_name")
    if game_name:
        params += ["%" + game_name + "%"]
        statements += ["GAME_NAME like ?"]
    start = request.args.get("start")
    if start:
        params += [start]
        statements += ["RELEASE_date >= ?"]
    end = request.args.get("end")
    if end:
        params += [end]
        statements += ["RELEASE_date <= ?"]
    score = request.args.get("score")
    if score:
        params += [score]
        statements += ["SCORE >= ?"]
    with get_connection() as connection:
        with connection.cursor() as cursor:  # this construction calls cursor.close() at the end
            data = cursor.execute(
                "SELECT GAME_ID, GAME_NAME, RELEASE_DATE, PRICE, SCORE FROM Games "
                + make_where(statements),
                *params,
            ).fetchall()
            # somehow, price is displayed with 4 digits after the comma.
            # This is a workaround to round it
            data = pd.DataFrame(
                [list(d) for d in data],
                columns=["GAME_ID", "GAME_NAME", "RELEASE_DATE", "PRICE", "SCORE"],
            )
            data["PRICE"] = data["PRICE"].astype(float)
            data["PRICE"] = np.round(data["PRICE"], 2)
            return render_template("games.html", data=data.to_records())


@app.route("/buy", methods=["POST"])
def buy():
    id = request.form.get("id")
    gross_amount = request.form.get("GROSS_AMOUNT")
    with get_connection() as connection:
        with connection.cursor() as cursor:  # this construction calls cursor.close() at the end
            game = cursor.execute(
                "SELECT GAME_ID, GAME_NAME, RELEASE_DATE, PRICE, Score FROM "
                + "Games where GAME_ID = ?",
                id,
            ).fetchone()
            order_id = (
                1 + cursor.execute("SELECT MAX(ORDER_ID) FROM ORDERS").fetchone()[0]
            )
            today = datetime.date.today()
            discount = (today - game[2]) < datetime.timedelta(days=365 * 3)
            u = cursor.execute(
                "INSERT  INTO Orders(ORDER_ID,ORDER_DATE,GAME_ID,NET_AMOUNT,DISCOUNT,GROSS_AMOUNT)"
                + "VALUES(?, ?, ?, ?, ?, ?)",
                order_id,
                today.strftime("%Y-%m-%d"),
                id,
                game[3],
                0.2 if discount else None,
                gross_amount,
            )
            cursor.commit()
            return f"""
            <p>You have bought \"{game[1]}\" game</p>
            <a href="/" role="button" >Go back </a>
            """


@app.route("/orders", methods=["GET"])
def get_orders():
    with get_connection() as connection:
        with connection.cursor() as cursor:  # this construction calls cursor.close() at the end
            data = cursor.execute(
                """SELECT ORDER_ID, ORDER_DATE, DISCOUNT, GROSS_AMOUNT,  GAME_NAME, round(PRICE, 2) as PRICE
                                    FROM ORDERS O JOIN GAMES G ON G.GAME_ID=O.GAME_ID"""
            ).fetchall()
            # somehow, Gross amount and price was displayed with 4 digits after the comma.
            # This is a workaround to round it
            data = pd.DataFrame(
                [list(d) for d in data],
                columns=[
                    "ORDER_ID",
                    "ORDER_DATE",
                    "DISCOUNT",
                    "GROSS_AMOUNT",
                    "GAME_NAME",
                    "PRICE",
                ],
            )
            data["GROSS_AMOUNT"] = data["GROSS_AMOUNT"].astype(float)
            data["GROSS_AMOUNT"] = np.round(data["GROSS_AMOUNT"], 2)
            data["PRICE"] = data["PRICE"].astype(float)
            data["PRICE"] = np.round(data["PRICE"], 2)
            return render_template("orders.html", data=data.to_records())


@app.route("/delete_order", methods=["POST"])
def delete_order():
    with get_connection() as connection:
        with connection.cursor() as cursor:  # this construction calls cursor.close() at the end
            id = request.form.get("id")
            cursor.execute("""DELETE FROM ORDERS where ORDER_ID = ?""", id)
            cursor.commit()
            return redirect(url_for("get_orders"))


@app.route("/edit_order", methods=["GET", "POST"])
def edit_order():
    with get_connection() as connection:
        with connection.cursor() as cursor:
            if request.method == "GET":
                data = cursor.execute(
                    """SELECT ORDER_ID, ORDER_DATE, GAME_ID, NET_AMOUNT, DISCOUNT, GROSS_AMOUNT 
                                      FROM ORDERS o where o.ORDER_ID= ? """,
                    request.args.get("ORDER_ID"),
                ).fetchone()
                games = cursor.execute("""SELECT GAME_ID, GAME_NAME FROM GAMES""")
                if data:
                    return render_template("edit_order.html", data=data, games=games)
                else:
                    return redirect(url_for("get_orders"))
            if request.method == "POST":
                columns = [
                    "ORDER_DATE",
                    "GAME_ID",
                    "NET_AMOUNT",
                    "DISCOUNT",
                    "GROSS_AMOUNT",
                ]
                statement = (
                    "UPDATE ORDERS SET "
                    + ", ".join([f"{c}=?" for c in columns])
                    + " where ORDER_ID = ?"
                )
                parameters = [request.form.get(c) for c in columns] + [
                    request.form.get("ORDER_ID")
                ]
                print(statement)
                print(parameters)
                print(request.form.get("GAME_ID"))
                cursor.execute(statement, *parameters)
                cursor.commit()
                return redirect(url_for("get_orders"))


app.run(debug=True)
