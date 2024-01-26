from collections import UserDict
from datetime import datetime
import os
import sqlite3
from contextlib import closing as dbclosing
from typing import Any, Iterable, Self, overload

DB_NAME = "rss.db"

class RSSRow(UserDict):
    _KEYS = (
        'id', 
        'name', 
        'url', 
        'dir', 
        'last_num', 
        'last_chk', 
        'last_upd', 
        'desc', 
        'imgtitle', 
        'exec_module_path', 
        'ended',
    )

    """Строка данных из БД"""
    def __init__(self, data: sqlite3.Row|dict[str, Any]|tuple[Any, ...]):
        self.data: dict[str, Any]
        if isinstance(data, dict):
            self.data = dict(zip(data.keys(), data.values()))
        elif isinstance(data, tuple):
            self.data = dict(zip(self._KEYS, data))
        else:
            self.data = dict(zip(data.keys(), tuple(data)))

        self.id: int = self.data['id']
        """Идентификатор записи в БД"""

        self.name: str = self.data['name']
        """Название комикса"""

        self.url: str = self.data['url']
        """Ссылка на комикс"""

        self.dir: str = self.make_safe_path(self.data['dir'])
        """Путь для скачивания"""

        self.last_num: int
        """Номер выпуска, с которого необходимо производить обновление"""
        if self.data['last_num'] > 0:
            self.last_num = self.data['last_num']
        else:
            self.last_num = 1

        self.last_chk: datetime
        """Время последней проверки"""
        if self.data['last_chk'] is None:
            self.last_chk = datetime.fromordinal(1)
        else:
            self.last_chk = datetime.fromisoformat(self.data['last_chk'])

        self.last_upd: datetime
        """Время последнего успешного обновления"""
        if self.data['last_upd'] is None:
            self.last_upd = datetime.fromordinal(1)
        else:
            self.last_upd = datetime.fromisoformat(self.data['last_upd'])

        self.desc: bool
        """Скачивать ли описания"""
        if isinstance(self.data['desc'], int):
            self.desc = bool(self.data['desc'])
        else:
            self.desc = str(self.data['desc']).lower()=="true"

        self.imgtitle: bool
        """Скачивать ли всплывающий текст на изображениях"""
        if isinstance(self.data['imgtitle'], int):
            self.imgtitle = bool(self.data['imgtitle'])
        else:
            self.imgtitle = str(self.data['imgtitle']).lower()=="true"

        self.exec_module_path: str = self.data['exec_module_path']
        """Путь к исполняемому файлу, производящему скачивание"""

        self.ended: bool
        """Закончен ли комикс"""
        if isinstance(self.data['ended'], int):
            self.ended = bool(self.data['ended'])
        else:
            self.ended = str(self.data['ended']).lower()=="true"

    @property
    def raw(self) -> tuple:
        """Возврат кортежа чистых данных, как они должны храниться в БД"""
        return tuple(self.values())

    @staticmethod
    def make_safe_path(path: str, create_path: bool=True) -> str:
        """Преобразование пути в абсолютный и безопасный
        """
        safe_path = os.path.abspath(path)
        drive, dir_ = os.path.splitdrive(safe_path)
        safe_path = os.path.join(
            os.sep,
            f"{drive}{os.sep}",
            *map(
                __class__.make_safe_filename,
                dir_.split(os.sep)
            )
        )
        if create_path and not os.path.exists(safe_path):
            os.makedirs(safe_path)
        return safe_path

    @staticmethod
    def make_safe_filename(filename: str) -> str:
            """
            # Преобразование имени файла в безопасное
            # https://stackoverflow.com/questions/7406102/create-sane-safe-filename-from-any-unsafe-string
            """
            illegal_chars = "/\\?%*:|\"<>"
            illegal_unprintable = {chr(c) for c in (*range(31), 127)}
            reserved_words = {
                'CON', 'CONIN$', 'CONOUT$', 'PRN', 'AUX', 'CLOCK$', 'NUL',
                'COM0', 'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
                'LPT0', 'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9',
                'LST', 'KEYBD$', 'SCREEN$', '$IDLE$', 'CONFIG$'
            }
            if os.path.splitext(filename)[0].upper() in reserved_words: return f"__{filename}"
            if set(filename)=={'.'}: return filename.replace('.', '\uff0e', 1)
            return "".join(
                chr(ord(c)+65248) if c in illegal_chars else c
                for c in filename
                if c not in illegal_unprintable
            ).rstrip()

    def __str__(self):
        return str(self.raw)

    def __repr__(self):
        return f"RSSRow({repr(self.data)})"

    def __eq__(self, other: Self) -> bool:
        return self.raw == other.raw

    def __lt__(self, other: Self) -> bool:
        return self.id < other.id

    def __le__(self, other: Self) -> bool:
        return self == other or self < other

    def __gt__(self, other: Self) -> bool:
        return self.id > other.id

    def __ge__(self, other: Self) -> bool:
        return self == other or self > other

    def __getitem__(self, index: int|str) -> int|str:
        if isinstance(index, int):
            return self.raw[index]
        return self.data[index]

class RSSData:
    """Данные из БД"""
    def __init__(self, data: Iterable[sqlite3.Row|RSSRow]):
        self.data = [row if isinstance(row, RSSRow) else RSSRow(row) for row in data]

    @property
    def raw(self) -> list[tuple]:
        """Возврат «чистых» данных, как они должны храниться в БД"""
        return [row.raw for row in self.data]

    def __str__(self):
        return str(self.raw)

    def __repr__(self):
        return f"RSSData({repr(self.data)})"

    def __eq__(self, other: Self) -> bool:
        return self.raw == other.raw

    @overload
    def __getitem__(self, index: slice) -> Self: ...
    @overload
    def __getitem__(self, index: int) -> RSSRow: ...
    def __getitem__(self, index: int|slice):
        if isinstance(index, slice):
            return RSSData(self.data[index])
        return self.data[index]

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
            connection.row_factory = sqlite3.Row
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
