from datetime import datetime
import os
import sqlite3
from contextlib import closing as dbclosing
from typing import Iterable, Self, overload

DB_NAME = "rss.db"

RowTuple = tuple[int, str, str, str, int, str, str, str|int, str|int, str, str|int]

class RSSRow:
    """Строка данных из БД"""
    def __init__(self, data: RowTuple):
        self.id: int = data[0]
        """Идентификатор записи в БД"""

        self.name: str = data[1]
        """Название комикса"""

        self.url: str = data[2]
        """Ссылка на комикс"""

        self.dir: str = self.make_safe_path(data[3])
        """Путь для скачивания"""

        self.last_num: int = data[4]
        """Номер выпуска, с которого необходимо производить обновление"""

        self.last_chk: datetime = datetime.fromisoformat(data[5])
        """Время последней проверки"""

        self.last_upd: datetime = datetime.fromisoformat(data[6])
        """Время последнего успешного обновления"""

        self.desc: bool
        """Скачивать ли описания"""
        if isinstance(data[7], int):
            self.desc = bool(data[7])
        else:
            self.desc = data[7].lower()=="true"

        self.imgtitle: bool
        """Скачивать ли всплывающий текст на изображениях"""
        if isinstance(data[8], int):
            self.imgtitle = bool(data[8])
        else:
            self.imgtitle = data[8].lower()=="true"

        self.exec_module_path: str = data[9]
        """Путь к исполняемому файлу, производящему скачивание"""

        self.ended: bool
        """Закончен ли комикс"""
        if isinstance(data[8], int):
            self.ended = bool(data[10])
        else:
            self.ended = str(data[10]).lower()=="true"

    @property
    def raw(self) -> RowTuple:
        """Возврат кортежа «чистых» данных, как они должны храниться в БД"""
        return (
            self.id,
            self.name,
            self.url,
            self.dir,
            self.last_num,
            self.last_chk.isoformat(sep=" "),
            self.last_upd.isoformat(sep=" "),
            str(self.desc),
            str(self.imgtitle),
            self.exec_module_path
        )

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
        return str(self.__dict__)

    def __repr__(self):
        return f"RSSRow({repr(self.__dict__)}.values())"

    def __eq__(self, other: Self) -> bool:
        return self.raw == other.raw

    def __getitem__(self, index: int|str) -> int|str:
        if isinstance(index, int):
            return self.raw[index]
        if isinstance(elem:=self.__dict__[index], datetime):
            return elem.isoformat(sep=" ")
        if isinstance(elem:=self.__dict__[index], bool):
            return str(elem)
        return self.__dict__[index]

class RSSData:
    """Данные из БД"""
    def __init__(self, data: Iterable[RowTuple|RSSRow]):
        self.data = [RSSRow(row) if isinstance(row, tuple) else row for row in data]

    @property
    def raw(self) -> list[RowTuple]:
        """Возврат «чистых» данных, как они должны храниться в БД"""
        return [row.raw for row in self.data]

    def __str__(self):
        return str([row.__dict__ for row in self.data])

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
