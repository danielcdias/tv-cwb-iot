import os
import sqlite3 as sqlite

from prefs import log_factory, prefs

FLAG_NOT_SENT = 0
FLAG_SENT = 1
FLAG_ERROR_NO_BOARD = 2
FLAG_ERROR_NO_SENSOR = 3
FLAG_ERROR_OTHER = 4

DB_TABLE_CREATE = "CREATE TABLE message_queue(id INTEGER PRIMARY KEY AUTOINCREMENT, sent_flag TINYINT NOT NULL " \
                  "DEFAULT 0, topic VARCHAR(100) NOT NULL, payload VARCHAR(100) NOT NULL)"

DB_TABLE_CHECK = "SELECT name FROM sqlite_master WHERE type='table' AND name='message_queue'"

DB_TABLE_INSERT = "INSERT INTO message_queue(topic, payload) VALUES (?, ?)"

DB_TABLE_SELECT_NOT_SENT = "SELECT * FROM message_queue WHERE sent_flag = {}".format(FLAG_NOT_SENT)

DB_TABLE_COUNT_NOT_SENT = "SELECT COUNT(*) FROM message_queue WHERE sent_flag = {}".format(FLAG_NOT_SENT)

DB_TABLE_UPDATE_FLAG = "UPDATE message_queue SET sent_flag = ? WHERE id = ?"

logger = None


def get_logger():
    global logger
    if not logger:
        logger = log_factory.get_new_logger("message_queue")
    return logger


def check_db():
    if not os.path.exists(prefs['db']['folder']):
        os.mkdir(prefs['db']['folder'])
    db_file = prefs['db']['folder'] + os.sep + prefs['db']['file']
    if not os.path.exists(db_file):
        try:
            conn = sqlite.connect(db_file)
            try:
                conn = sqlite.connect(db_file)
                cursor = conn.cursor()
                cursor.execute(DB_TABLE_CHECK)
                row = cursor.fetchone()
                if not row:
                    cursor.execute(DB_TABLE_CREATE)
                cursor.close()
            except Exception as ex:
                if "no such table: message_queue" in str(ex):
                    cursor = conn.cursor()
                    cursor.execute(DB_TABLE_CREATE)
                    cursor.close()
                else:
                    get_logger().error(
                        "Could not create the database (1). Exception: {}".format(ex))
            finally:
                conn.close()
        except Exception as ex:
            get_logger().error(
                "Could not create the database (2). Exception: {}".format(ex))


def connect() -> sqlite.Connection:
    result = None
    check_db()
    try:
        db_file = prefs['db']['folder'] + os.sep + prefs['db']['file']
        result = sqlite.connect(db_file)
    except Exception as ex:
        get_logger().error(
            "Could not connect to the database. Exception: {}".format(ex))
    return result


def add_message(topic: str, payload: str) -> bool:
    get_logger().debug("Adding message to database: topic: {}, payload: {}.".format(topic, payload))
    result = False
    conn = connect()
    try:
        if conn:
            cursor = conn.cursor()
            parms = [topic, payload]
            cursor.execute(DB_TABLE_INSERT, parms)
            conn.commit()
            cursor.close()
            result = True
        else:
            get_logger().error(
                "Could not insert data in the database.")
    except Exception as ex:
        get_logger().error(
            "Could not insert data in the database. Exception: {}".format(ex))
        conn.rollback()
    finally:
        if conn:
            conn.close()
    return result


def get_all_not_sent() -> list:
    result = []
    conn = connect()
    try:
        if conn:
            cursor = conn.cursor()
            cursor.execute(DB_TABLE_SELECT_NOT_SENT)
            rows = cursor.fetchall()
            columns = [column[0] for column in cursor.description]
            for row in rows:
                row_as_dict = dict(zip(columns, row))
                result.append(row_as_dict)
            cursor.close()
    except Exception as ex:
        get_logger().error(
            "Could not read data from the database. Exception: {}".format(ex))
    finally:
        if conn:
            conn.close()
    return result


def get_count_not_sent() -> int:
    result = 0
    conn = connect()
    try:
        if conn:
            cursor = conn.cursor()
            cursor.execute(DB_TABLE_COUNT_NOT_SENT)
            result = cursor.fetchone()[0]
            cursor.close()
    except Exception as ex:
        get_logger().error(
            "Could not read data from the database. Exception: {}".format(ex))
    finally:
        if conn:
            conn.close()
    return result


def update_message(id_message: int, flag: int) -> bool:
    result = False
    conn = connect()
    try:
        if conn:
            cursor = conn.cursor()
            parms = [flag, id_message]
            cursor.execute(DB_TABLE_UPDATE_FLAG, parms)
            conn.commit()
            cursor.close()
            result = True
        else:
            get_logger().error(
                "Could not insert data in the database.")
    except Exception as ex:
        get_logger().error(
            "Could not insert data in the database. Exception: {}".format(ex))
        conn.rollback()
    finally:
        if conn:
            conn.close()
    return result
