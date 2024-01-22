from datetime import datetime
import sqlite3
from contextlib import closing as dbclosing
from typing import Iterable, Self, Sequence

DB_NAME = "rss.db"

class RSSRow:
    """Строка данных из БД"""
    def __init__(self, data: Sequence[str|int]):
        self.id: int = int(data[0])
        self.name: str = str(data[1])
        self.url: str = str(data[2])
        self.dir: str = str(data[3])
        self.last_num: int = int(data[4])
        self.last_chk: datetime = datetime.fromisoformat(str(data[5]))
        self.last_upd: datetime = datetime.fromisoformat(str(data[6]))
        if isinstance(data[7], int):
            self.desc: bool = bool(data[7])
        else:
            self.desc: bool = data[7].lower()=="true"
        if isinstance(data[8], int):
            self.imgtitle: bool = bool(data[8])
        else:
            self.imgtitle: bool = data[8].lower()=="true"

    @property
    def raw(self) -> tuple[int, str, str, str, int, str, str, str, str]:
        return (
            self.id,
            self.name,
            self.url,
            self.dir,
            self.last_num,
            self.last_chk.isoformat(sep=" "),
            self.last_upd.isoformat(sep=" "),
            str(self.desc),
            str(self.imgtitle)
        )

    def __str__(self):
        return str(self.__dict__)

    def __repr__(self):
        return f"RSSRow({repr(self.__dict__)}.values())"

    def __eq__(self, other: Self) -> bool:
        return self.raw == other.raw

class RSSData:
    """Данные из БД"""
    def __init__(self, data: Iterable[Sequence[str|int]]):
        self.data = [RSSRow(row) for row in data]

    @property
    def raw(self) -> list[tuple[int, str, str, str, int, str, str, str, str]]:
        return [row.raw for row in self.data]

    def __str__(self):
        return str([row.__dict__ for row in self.data])

    def __repr__(self):
        return f"RSSData({repr(self.data)})"

    def __eq__(self, other: Self) -> bool:
        return self.raw == other.raw

class RSSDB:
    """Класс работы с БД"""
    def __init__(self, db_name: str):
        self.db_name = db_name

    def service_db(self):
        """Обслуживание БД"""
        with dbclosing(sqlite3.connect(self.db_name)) as connection:
            with connection as cursor:
                cursor.execute('vacuum')
        print("БД rss.db успешно оптимизирована")

    def get_db(self) -> RSSData:
        """Получить данные из БД"""
        with dbclosing(sqlite3.connect(self.db_name)) as connection:
            with connection as cursor:
                res = cursor.execute('select * from rss_list')
                res = res.fetchall()
        return RSSData(res)

    def set_last_num(self, rss_id: int, last_num: int):
        """Обновить номер первого непрочитанного"""
        with dbclosing(sqlite3.connect(self.db_name)) as connection:
            with connection as cursor:
                cursor.execute(
                    """update rss_list
                    set last_num=?,
                            last_chk=datetime('now'),
                            last_upd=datetime('now')
                    where id=?""",
                    (last_num, rss_id)
                )

    def set_last_chk(self, rss_id: int):
        """Обновить время последней проверки"""
        with dbclosing(sqlite3.connect(self.db_name)) as connection:
            with connection as cursor:
                cursor.execute(
                    """update rss_list
                    set last_chk=datetime('now')
                    where id=?""",
                    (rss_id,)
                )

def service_db():
    """Обслуживание БД"""
    return RSSDB(DB_NAME).service_db()

def get_db():
    """Получить данные из БД"""
    return RSSDB(DB_NAME).get_db().raw

def set_last_num(rss_id: int, last_num: int):
    """Обновить номер первого непрочитанного"""
    return RSSDB(DB_NAME).set_last_num(rss_id, last_num)

def set_last_chk(rss_id: int):
    """Обновить время последней проверки"""
    return RSSDB(DB_NAME).set_last_chk(rss_id)
