import datetime
import sqlite3
from typing import Any
import click
from flask import current_app
import pandas as pd
from pandas import DataFrame

from fintech.blueprints.admin.patterns import HSPattern, find_patterns


def all_time_high_algo(date: datetime.date) -> list[list[Any]]:
    conn = sqlite3.connect(current_app.config['DB_PATH'])
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    collected_records = []
    for table in tables:
        table_name = table[0]
        
        if table_name.isupper():
            query = f"SELECT * FROM '{table_name}' WHERE Date = ?"
            cursor.execute(query, (date,))
            record = cursor.fetchone()  # Fetch one record

            if record:
                collected_records.append([table_name] + list(record))

    cursor.close()
    conn.close()

    return collected_records


def get_symbols() -> list[Any]:
    conn = sqlite3.connect(current_app.config['DB_PATH'])
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT DISTINCT Symbol FROM NiftyData")
    symbols = cursor.fetchall()
    conn.close()
    return symbols


def get_plotting_data(symbol: str) -> dict[str, list[Any]]:
    df = pd.read_sql_query(
            f"SELECT * FROM NiftyData WHERE Symbol = '{symbol}'",
            sqlite3.connect(current_app.config['DB_PATH'])
        )
    df['Date'] = pd.to_datetime(df['Date']).dt.date
    df['Open'] = df['Open'].astype(float)
    df['High'] = df['High'].astype(float)
    df['Low'] = df['Low'].astype(float)
    df['Close'] = df['Close'].astype(float)
    df['Volume'] = df['Volume'].astype(int)
    return {
        'Date': [f"'{date}'" for date in df['Date']],
        'Open': [f"{val:.6f}" for val in df['Open']],
        'High': [f"{val:.6f}" for val in df['High']],
        'Low': [f"{val:.6f}" for val in df['Low']],
        'Close': [f"{val:.6f}" for val in df['Close']],
        'Volume': [val for val in df['Volume']]
    }