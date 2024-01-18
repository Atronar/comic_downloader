import sqlite3
from contextlib import closing as dbclosing

# Обслуживание БД
def service_db():
    with dbclosing(sqlite3.connect("rss.db")) as connection:
        with connection as cursor:
            cursor.execute('vacuum')
    print("БД rss.db успешно оптимизирована")

# Получить данные из БД
def get_db():
    with dbclosing(sqlite3.connect("rss.db")) as connection:
        with connection as cursor:
            res = cursor.execute('select * from rss_list')
            res = res.fetchall()
    return res

def set_last_num(rss_id,last_num):
    with dbclosing(sqlite3.connect("rss.db")) as connection:
        with connection as cursor:
            cursor.execute("""update rss_list
                                    set last_num=?, 
                                         last_chk=datetime('now'),
                                         last_upd=datetime('now')
                                    where id=?""",(last_num,rss_id))

def set_last_chk(rss_id):
    with dbclosing(sqlite3.connect("rss.db")) as connection:
        with connection as cursor:
            cursor.execute("""update rss_list
                                    set last_chk=datetime('now') 
                                    where id=?""",(rss_id))
