import sqlite3
from contextlib import closing as dbclosing

DB_NAME = "rss.db"

def service_db():
    """Обслуживание БД"""
    with dbclosing(sqlite3.connect(DB_NAME)) as connection:
        with connection as cursor:
            cursor.execute('vacuum')
    print("БД rss.db успешно оптимизирована")

def get_db() -> list[tuple[str|int]]:
    """Получить данные из БД"""
    with dbclosing(sqlite3.connect(DB_NAME)) as connection:
        with connection as cursor:
            res = cursor.execute('select * from rss_list')
            res = res.fetchall()
    return res

def set_last_num(rss_id: int, last_num: int):
    """Обновить номер первого непрочитанного"""
    with dbclosing(sqlite3.connect(DB_NAME)) as connection:
        with connection as cursor:
            cursor.execute(
                """update rss_list
                set last_num=?,
                        last_chk=datetime('now'),
                        last_upd=datetime('now')
                where id=?""",
                (last_num, rss_id)
            )

def set_last_chk(rss_id: int):
    """Обновить время последней проверки"""
    with dbclosing(sqlite3.connect(DB_NAME)) as connection:
        with connection as cursor:
            cursor.execute(
                """update rss_list
                set last_chk=datetime('now')
                where id=?""",
                (rss_id,)
            )
