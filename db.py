import mysql.connector
from flask import current_app

def get_connection():
    return mysql.connector.connect(
        host     = current_app.config['DB_HOST'],
        user     = current_app.config['DB_USER'],
        password = current_app.config['DB_PASSWORD'],
        database = current_app.config['DB_NAME'],
        charset  = 'utf8mb4',
    )

def query_one(sql, params=None):
    conn   = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(sql, params or ())
    row = cursor.fetchone()
    cursor.close(); conn.close()
    return row

def query_all(sql, params=None):
    conn   = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(sql, params or ())
    rows = cursor.fetchall()
    cursor.close(); conn.close()
    return rows

def execute(sql, params=None):
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute(sql, params or ())
    conn.commit()
    last_id = cursor.lastrowid
    cursor.close(); conn.close()
    return last_id