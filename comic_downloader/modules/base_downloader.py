"""Базовый модуль скачивания комиксов
"""

from abc import ABC, abstractmethod
import argparse
import os
import aiohttp

class BaseDownloader(ABC):
    def __init__(
        self, *,
        comic_name: str|None = None,
        first: int|float|str|None = None,
        last: int|float|str|None = None,
        is_write_description: bool|None = None,
        is_write_img_description: bool|None = None,
        folder: str|os.PathLike|None = None,
        use_async: bool|None = None
    ):
        args, _ = self.arg_parser.parse_known_args()

        self.comic_name: str = comic_name or args.comic

        self.first: str
        first = first or args.first
        if first is None:
            raise ValueError("first is None")
        else:
            self.first = str(first)

        self.last: str|None
        last = last or args.last
        if last is None:
            self.last = last
        else:
            self.last = str(last)

        self.is_write_description: bool
        if is_write_description is None:
            self.is_write_description = args.desc
        else:
            self.is_write_description = is_write_description

        self.is_write_img_description: bool
        if is_write_img_description is None:
            self.is_write_img_description = args.imgtitle
        else:
            self.is_write_img_description = is_write_img_description

        self.folder: str
        if folder is None:
            self.folder = args.folder
        elif isinstance(folder, os.PathLike):
            self.folder = folder.__fspath__()
        else:
            self.folder = folder

        self.use_async: bool
        if use_async is None:
            self.use_async = not args.no_async
        else:
            self.use_async = use_async

    @property
    def _params(self):
        return dict({
            "comic_name": self.comic_name,
            "first": self.first,
            "last": self.last,
            "is_write_description": self.is_write_description,
            "is_write_img_description": self.is_write_img_description,
            "folder": self.folder,
            "use_async": self.use_async
        })

    @property
    def arg_parser(self) -> argparse.ArgumentParser:
        """Парсер аргументов командной строки
        """
        parser = argparse.ArgumentParser()
        parser.add_argument(
            'comic',
            help = 'Ссылка на главную страницу комикса',
            type = str
        )
        parser.add_argument(
            'first',
            nargs = '?',
            help = 'Номер первой страницы, число',
            type = str,
            default = 1
        )
        parser.add_argument(
            '-last',
            nargs = '?',
            help = (
                'Номер последней страницы, число. '
                'Если больше возможного, то качается до последнего существующего.'
            ),
            type = str,
            default = None
        )
        parser.add_argument(
            '-desc',
            help = 'Сохранять описания в текстовый файл',
            action = 'store_true'
        )
        parser.add_argument(
            '-imgtitle',
            help = 'Сохранять title изображений в текстовый файл',
            action = 'store_true'
        )
        parser.add_argument(
            '-folder',
            help = 'Директория сохранения',
            type = str,
            default = '.'
        )
        parser.add_argument(
            '-no-async',
            help = 'Отключение быстрого (асинхронного) скачивания',
            action = 'store_true'
        )
        return parser

    @abstractmethod
    def _comic_main_page_link(self) -> str:
        """Получение ссылки на главную страницу комикса"""

    def _check_corrects_file(self, filepath: str|os.PathLike) -> bool:
        """Проверка файла на существование и корректность"""
        return os.path.exists(filepath) and os.path.getsize(filepath) > 8

    @staticmethod
    def _clear_text_multiplespaces(text: str) -> str:
        """Очистка от множественных пробелов и переносов строки"""
        text = "\n".join(line.strip() for line in text.splitlines())
        while "  " in text:
            text = text.replace("  ", " ")
        while "\n\n\n" in text:
            text = text.replace("\n\n\n", "\n\n")
        return text.strip()

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

    @abstractmethod
    def find_last(self) -> int:
        """Поиск номера следующей за последней доступной страницы комикса на сервере

        Return
        ------
        int
            Номер страницы, которую надо проверять для обновления

            Если на сервере есть страницы с 1 по 10, но 11 ещё не вышла, то вернётся именно 11
        """

    @abstractmethod
    async def async_find_last(
        self,
        async_session: aiohttp.ClientSession|None=None
    ) -> int:
        """Асинхронный поиск номера следующей за последней доступной страницы комикса на сервере

        Parameters
        ----------
        session: ClientSession | None
            Сессия для проведения асинхронных запросов
            Если не передана, то будет производиться обычный поиск

        Return
        ------
        int
            Номер страницы, которую надо проверять для обновления

            Если на сервере есть страницы с 1 по 10, но 11 ещё не вышла, то вернётся именно 11
        """

    @abstractmethod
    def downloadcomic(self) -> int:
        """Скачивание заданных страниц комикса от first до last

        Return
        ------
        int
            Номер первой недоступной страницы
            При следующей проверке в аргумент first надо поместить именно это значение

            Если на сервере есть страницы с 1 по 10, но 11 ещё не вышла, то вернётся именно 11
        """

    @abstractmethod
    async def async_downloadcomic(self) -> int:
        """Асинхронное скачивание заданных страниц комикса от first до last

        Return
        ------
        int
            Номер первой недоступной страницы
            При следующей проверке в аргумент first надо поместить именно это значение

            Если на сервере есть страницы с 1 по 10, но 11 ещё не вышла, то вернётся именно 11
        """

class BasePageDownloader(BaseDownloader):
    """Загрузчик одной страницы комикса

    Parameters
    ----------
    page: int | str
        Номер скачиваемой страницы
    """
    def __init__(self, page: int|str|None = None, **kwargs):
        super().__init__(**kwargs)
        self.page = page

    @abstractmethod
    def _comic_file_page_link(self) -> str:
        """Получение ссылки на страницу комикса"""

    @abstractmethod
    def _comic_file_link(self) -> str:
        """Получение ссылки на файл страницы комикса на сервере"""

    @abstractmethod
    def _comic_filename(self) -> str:
        """Получение имени файла страницы комикса"""

    @abstractmethod
    def _comic_page_title(self) -> str:
        """Получение заголовка страницы комикса"""

    @abstractmethod
    def _comic_page_description(self) -> str|None:
        """Получение описания страницы комикса

        Return
        ------
        str
            Текст описания
            Если is_write_description и is_write_img_description установлены в True,
            то они разделяются пустыми строками и строкой с 5 дефисами

        None
            Если описания нет, возвращается None
        """

    @abstractmethod
    def download_comic_page(self) -> int|None:
        """Скачивание одной страницы комикса

        Parameters
        ----------
        page: int | str
            Номер скачиваемой страницы

        Return
        ------
        int
            Номер страницы, которая только что успешно скачалась, либо

        None
            Маркер, что скачивание не удалось
        """

    @abstractmethod
    async def async_download_comic_page(
        self,
        session: aiohttp.ClientSession|None = None
    ) -> int|None:
        """Асинхронное скачивание одной страницы комикса

        Parameters
        ----------
        session: ClientSession | None
            Сессия для проведения асинхронных запросов
            Если не передана, то будет производиться обычное скачивание

        Return
        ------
        int
            Номер страницы, которая только что успешно скачалась, либо

        None
            Маркер, что скачивание не удалось
        """
