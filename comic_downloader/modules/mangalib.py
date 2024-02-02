"""Модуль скачивания комиксов с MangaLib
https://mangalib.me/
"""

from collections import UserList
import os
import time
from typing import Any, Final, Iterable, Iterator, overload
import asyncio
import aiofile
import aiohttp
import requests
from base_downloader import BaseDownloader, BasePageDownloader

class ChapterNumber(UserList):
    """Класс, представляющий номер части, которая может состоять как из одного числа,
    так и из набора чисел, разделённых точкой

    Реализованы следующие операции: =, !=, <, >, <=, >=, +, -, bool, str
    Сравнение производится от старших чисел слева к младшим справа
    Отсутствующие позиции считаются за 0 и младшие нули усекаются
    Сложение и вычитание производится в рамках своей позиции: (a.b)+(c.d.e)=(a+c).(b+d).e
    False возвращается только если все позиции False
    """
    def __init__(self, initlist: Iterable[int]|int|float|str|None=None):
        if isinstance(initlist, int):
            initlist = [initlist, ]
        elif isinstance(initlist, (float, str)):
            clean_initlist = f"{initlist}".rstrip()
            if '.' in clean_initlist:
                clean_initlist = clean_initlist.rstrip('0').rstrip('.')
            if clean_initlist:
                initlist = list(map(int, clean_initlist.split(".")))
            else:
                initlist = []
        if initlist is not None:
            initlist = list(initlist)
            while initlist and initlist[-1]==0:
                del initlist[-1]
            if not all(isinstance(item, int) for item in initlist):
                raise ValueError("not int in ChapterNumber")
        super().__init__(initlist=initlist)

    def __lt__(self, other: list|UserList|int|float):
        if isinstance(other, int):
            other = [other, ]
        elif isinstance(other, float):
            other = list(map(int, f"{other}".split(".")))
        other_data = self.__cast(other)
        if len(self.data) == len(other_data):
            for self_item, other_item in zip(self.data, other_data):
                if self_item < other_item:
                    return True
                if self_item > other_item:
                    return False
            return False
        min_len = min(len(self.data), len(other_data))
        min_self = self.__class__(self.data[:min_len])
        min_other = self.__class__(other_data[:min_len])
        if min_self != min_other:
            return min_self < min_other
        return len(self.data) < len(other_data)

    def __le__(self, other: list|UserList|int|float):
        return not (self > other)

    def __eq__(self, other):
        if isinstance(other, int):
            other = [other, ]
        elif isinstance(other, float):
            other = list(map(int, f"{other}".split(".")))
        elif not isinstance(other, Iterable):
            raise ValueError(other)
        other_data = self.__cast(other)
        if len(self.data) == len(list(other_data)):
            for self_item, other_item in zip(self.data, other_data):
                if self_item != other_item:
                    return False
            return True
        return False

    def __gt__(self, other: list|UserList|int|float):
        if isinstance(other, int):
            other = [other, ]
        elif isinstance(other, float):
            other = self.__class__(f"{other}")
        other_data = self.__cast(other)
        if len(self.data) == len(other_data):
            for self_item, other_item in zip(self.data, other_data):
                if self_item > other_item:
                    return True
                if self_item < other_item:
                    return False
            return False
        min_len = min(len(self.data), len(other_data))
        min_self = self.__class__(self.data[:min_len])
        min_other = self.__class__(other_data[:min_len])
        if min_self != min_other:
            return min_self > min_other
        return len(self.data) > len(other_data)

    def __ge__(self, other: list|UserList|int|float):
        return not (self < other)

    def __cast(self, other):
        return other.data if isinstance(other, UserList) else other

    def __add__(self, other: Iterable|int|float):
        if isinstance(other, int):
            other = [other, ]
        elif isinstance(other, float):
            other = self.__class__(f"{other}")

        if isinstance(other, UserList):
            other_data = other.data
        elif isinstance(other, type(self.data)):
            other_data = other
        else:
            other_data = list(other)

        len_self = len(self.data)
        len_other = len(other_data)
        max_len = max(len_self, len_other)
        norm_self_data = self.data + [0]*(max_len-len_self)
        norm_other_data = other_data + [0]*(max_len-len_other)

        return self.__class__(map(sum, zip(norm_self_data, norm_other_data)))

    def __radd__(self, other: Iterable|int|float):
        return self.__add__(other)

    def __iadd__(self, other: Iterable|int|float):
        self.data = (self + other).data
        return self

    def __neg__(self):
        return self.__class__(map(lambda x: -x, self.data))

    def __sub__(self, other: Iterable|int|float):
        return self + (-self.__class__(other))

    def __rsub__(self, other: Iterable|int|float):
        return self.__sub__(other)

    def __isub__(self, other: Iterable|int|float):
        self.data = (self - other).data
        return self

    def __bool__(self) -> bool:
        for item in self.data:
            if item:
                return True
        return False

    def __str__(self) -> str:
        return '.'.join(map(str, self.data))

    def __iter__(self) -> Iterator[int]:
        return super().__iter__()

class Downloader(BaseDownloader):
    _COMIC_DOMAIN: Final[str] = "https://mangalib.me"
    _API_DOMAIN: Final[str] = "https://api.lib.social"
    _IMG_DOMAIN: Final[tuple[str, ...]] = (
        "https://img33.imgslib.link",
        "https://img2.mixlib.me"
    )
    _HEADERS: Final[dict[str, str]] = {
        'user-agent': ''
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Страницы могут быть вида 58.1
        self.first: ChapterNumber = ChapterNumber(self.first)
        self.last: ChapterNumber = ChapterNumber(self.last)
        self.comic_name = self.comic_name.rsplit("/",1)[-1]
        self.chapters_data: list[dict[str, Any]]|None = None

    @overload
    def _to_number(self, number: int|float) -> ChapterNumber: ...
    @overload
    def _to_number(self, number: None) -> None: ...
    @overload
    def _to_number(self, number: str) -> ChapterNumber|None: ...
    def _to_number(self, number):
        if number is None:
            return None
        try:
            return ChapterNumber(f"{number}")
        except ValueError:
            return None

    def _comic_main_page_link(self) -> str:
        return f"{self._COMIC_DOMAIN}/{self.comic_name}"

    def _get_chapters_data(self, use_async: bool=True) -> list[dict[str, Any]]:
        url = f"{self._API_DOMAIN}/api/manga/{self.comic_name}/chapters"
        if use_async:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(self._async_get_chapters_data())

        resp = requests.get(url, timeout=60)
        data = resp.json().get("data", [])
        return data

    async def _async_get_chapters_data(
        self,
        async_session: aiohttp.ClientSession|None = None
    ) -> list[dict[str, Any]]:
        # Без сессии используем обычный запрос
        if async_session:
            _request = async_session.request
        else:
            _request = aiohttp.request

        url = f"{self._API_DOMAIN}/api/manga/{self.comic_name}/chapters"
        async with _request('GET', url) as resp:
            data = (await resp.json()).get("data", [])
        return data

    def find_last(self) -> ChapterNumber:
        if not self.chapters_data:
            self.chapters_data = self._get_chapters_data(use_async=False)

        # Вытаскиваем из ссылки номер последней существующей страницы
        data_last: str|int = self.chapters_data[-1].get("number", 0)
        last = self._to_number(data_last)
        if last is None:
            raise ValueError(f'last={data_last}')
        # ...и возвращаем не менее, чем следующую
        self.last = last + ([0]*len(last) + [1])
        return self.last

    async def async_find_last(
        self,
        async_session: aiohttp.ClientSession|None=None
    ) -> ChapterNumber:
        if not self.chapters_data:
            self.chapters_data = await self._async_get_chapters_data(async_session=async_session)

        # Запросов не делается, просто возвращаем как обычно
        return self.find_last()

    def downloadcomic(self) -> ChapterNumber:
        # Асинхронное скачивание
        if self.use_async:
            loop = asyncio.get_event_loop()
            last_success = loop.run_until_complete(self.async_downloadcomic())
            loop.close()
            return last_success

        # Обычное скачивание
        # Установка последней части при её отсутствии
        if not self.last:
            self.last = self.find_last()

        if self.first >= self.last:
            return self.last

        if not self.chapters_data:
            self.chapters_data = self._get_chapters_data(use_async=False)

        # Последовательно скачиваем части,
        # запоминаем, на какой части необходимо начинать следующее скачивание
        last_success: ChapterNumber|None = None
        all_chapters_correct = True
        for chapter in self.chapters_data:
            # Берём номер части
            num_chapter = self._to_number(chapter.get("number", None))
            if num_chapter is None:
                raise ValueError(f'{num_chapter=}')
            # Если часть до первой нужной, то пропускаем
            if self.first > ChapterNumber(num_chapter):
                continue
            # Начиная с последней, прекращаем
            if self.last <= ChapterNumber(num_chapter):
                break
            # Берём номер тома
            num_volume = self._to_number(chapter.get("volume", None))
            if num_volume is None:
                raise ValueError(f'{num_volume=}')
            # Загрузчик частей
            chapter_downloader = ChapterDownloader(num_volume, num_chapter, **self._params)
            # Количество страниц, которые мы должны скачать
            pages_in_chapter = len(chapter_downloader.data.get("pages", []))
            # Количество страниц, которые мы скачали
            succesed_pages = 0
            # Последовательно скачиваем страницы
            for page_downloader in chapter_downloader:
                if page_downloader.download_comic_page() is not None:
                    succesed_pages = succesed_pages + 1
            # Если ДО ЭТОГО части были скачаны успешно,
            if all_chapters_correct:
                # ...запоминаем успешность этого шага скачивания...
                all_chapters_correct = (succesed_pages == pages_in_chapter)
                # ...и номер шага, НЕЗАВИСИМО ОТ ЕГО УСПЕШНОСТИ
                last_success = num_chapter

        # Успешных скачиваний не было — возвращаем первый
        if last_success is None:
            return self.first
        # Все скачивания успешны — возвращаем последний (который не качали)
        if all_chapters_correct:
            return self.last
        # Были неуспешные скачивания, возвращаем первый неуспешный
        return last_success

    async def async_downloadcomic(self) -> ChapterNumber:
        async with aiohttp.ClientSession() as session:
            # Установка последней страницы при её отсутствии
            if not self.last:
                self.last = await self.async_find_last(async_session=session)

            if self.first >= self.last:
                return self.last

            if not self.chapters_data:
                self.chapters_data = await self._async_get_chapters_data(async_session=session)

            # Скачивание
            # Создание списка задач
            tasks: dict[str, dict] = {}
            # reversed, так как задачи выполняются последний пришёл - первый ушёл,
            # а нам надо по порядку
            for chapter in reversed(self.chapters_data):
                # Берём номер части
                num_chapter = chapter.get("number", None)
                if num_chapter is None:
                    raise ValueError(f'{num_chapter=}')
                # Если часть до первой нужной, то пропускаем
                if self.first > ChapterNumber(num_chapter):
                    break
                # Начиная с последней, пропускаем
                if self.last <= ChapterNumber(num_chapter):
                    continue
                # Берём номер тома
                num_volume = chapter.get("volume", None)
                if num_volume is None:
                    raise ValueError(f'{num_volume=}')
                # Загрузчик частей
                chapter_downloader = await ChapterDownloader.async_create(
                    num_volume,
                    num_chapter,
                    **self._params
                )
                # Количество страниц, которые мы должны скачать
                pages_in_chapter = len(chapter_downloader.data.get("pages", []))
                # Создаём задачи
                tasks[num_chapter] = {
                    'pages_in_chapter': pages_in_chapter,
                    'tasks': [],
                    'results': None,
                    'succesed_pages': 0
                }
                # reversed, так как задачи выполняются последний пришёл - первый ушёл,
                # а нам надо по порядку
                for page_downloader in reversed(chapter_downloader):
                    tasks[num_chapter]['tasks'].append(
                        asyncio.create_task(
                            page_downloader.async_download_comic_page(session=session)
                        )
                    )
                # Запуск задач (но идём дальше)
                tasks[num_chapter]['results'] = asyncio.gather(*(tasks[num_chapter]['tasks']))
            # Ожидание результатов
            for num_chapter, task in tasks.items():
                results: list[int|None] = await task['results']
                # Чистка результатов
                task['succesed_pages'] = sum(1 for result in results if result is not None)
                del task['results']
                del task['tasks']

        # Возврат следующей к скачиванию страницы
        for num_chapter, task in tasks.items():
            if task['pages_in_chapter'] != task['succesed_pages']:
                # Были неуспешные скачивания, возвращаем первый неуспешный
                return ChapterNumber(num_chapter)
        # Все скачивания успешны — возвращаем последний (который не качали)
        return self.last

class ChapterDownloader(Downloader):
    def __init__(
        self,
        volume: str|ChapterNumber,
        chapter: str|ChapterNumber,
        **kwargs
    ):
        super().__init__(**kwargs)
        if isinstance(volume, ChapterNumber):
            volume = str(volume)
        if isinstance(chapter, ChapterNumber):
            chapter = str(chapter)
        if not self.use_async:
            self.data = self._get_chapter_data(volume, chapter, use_async=self.use_async)

    @classmethod
    async def async_create(
        cls,
        volume: str|ChapterNumber,
        chapter: str|ChapterNumber,
        **kwargs
    ):
        """Создание объекта ChapterDownloader с использованием асинхронных методов
        """
        self = cls(
            volume=volume,
            chapter=chapter,
            **kwargs
        )
        self.data = await self._async_get_chapter_data(volume, chapter)
        return self

    def _get_chapter_data(self, volume: str, chapter: str, use_async: bool=True) -> dict[str, Any]:
        url = (
            f"{self._API_DOMAIN}"
            f"/api/manga/{self.comic_name}/chapter?number={chapter}&volume={volume}"
        )
        if use_async:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(self._async_get_chapter_data(volume, chapter))

        resp = requests.get(url, timeout=60)
        data = resp.json().get("data", {})
        if toast := data.get("toast", None):
            raise ValueError(toast.get("message", ""), data)
        return data

    async def _async_get_chapter_data(self, volume, chapter) -> dict[str, Any]:
        url = (
            f"{self._API_DOMAIN}"
            f"/api/manga/{self.comic_name}/chapter?number={chapter}&volume={volume}"
        )
        async with aiohttp.request('GET', url) as resp:
            data = (await resp.json()).get("data", {})
        if toast := data.get("toast", None):
            raise ValueError(toast.get("message", ""), data)
        return data

    def __iter__(self):
        for page in self.data.get("pages", []):
            yield PageDownloader(
                page = page.get("slug"),
                volume = self.data.get("volume"),
                chapter = self.data.get("number"),
                chapter_title = self.data.get("name"),
                data = page,
                **self._params
            )

    def __reversed__(self):
        for page in reversed(self.data.get("pages", [])):
            yield PageDownloader(
                page = page.get("slug"),
                volume = self.data.get("volume"),
                chapter = self.data.get("number"),
                chapter_title = self.data.get("name"),
                data = page,
                **self._params
            )

class PageDownloader(BasePageDownloader, Downloader):
    def __init__(
        self,
        page: int|None = None,
        volume: str|None = None,
        chapter: str|None = None,
        chapter_title: str|None = None,
        data: dict[str, str|int]|None = None,
        **kwargs
    ):
        super().__init__(page=page, **kwargs)

        chapter_data = None

        self.volume = volume
        self.chapter = chapter

        self.chapter_title: str
        if chapter_title:
            self.chapter_title = chapter_title
        else:
            if not chapter_data:
                if self.volume is None or self.chapter is None:
                    raise ValueError("volume or chapter is None")
                chapter_kwargs = kwargs.copy()
                chapter_kwargs.update(use_async=False)
                chapter_data = ChapterDownloader(self.volume, self.chapter, **chapter_kwargs).data
            chapter_title = chapter_data.get("name", None)
            if chapter_title is None:
                raise ValueError("chapter_title is None")
            self.chapter_title = chapter_title

        self.data: dict[str, str|int]
        if data:
            self.data = data
        else:
            if not chapter_data:
                if self.volume is None or self.chapter is None:
                    raise ValueError("volume or chapter is None")
                chapter_kwargs = kwargs.copy()
                chapter_kwargs.update(use_async=False)
                chapter_data = ChapterDownloader(self.volume, self.chapter, **chapter_kwargs).data
            for chapter_page in chapter_data.get("pages", []):
                if chapter_page.get("slug") == page:
                    self.data = chapter_page
                    break

        self.page: int
        if page:
            self.page = page
        else:
            if not (slug := self.data.get("slug")):
                raise ValueError("page is None")
            self.page = int(slug)

    def _comic_file_page_link(self) -> str:
        if self.page is None:
            raise ValueError("page is None")
        if self.chapter is None:
            raise ValueError("chapter is None")
        if self.volume is None:
            raise ValueError("volume is None")
        return f"{self._comic_main_page_link()}/v{self.volume}/c{self.chapter}?page={self.page}"

    def _comic_file_link(self, img_domain: int=0) -> str:
        if img_domain in range(len(self._IMG_DOMAIN)):
            return f"{self._IMG_DOMAIN[img_domain]}{self.data.get('url')}"
        return f"{self._IMG_DOMAIN[0]}{self.data.get('url')}"

    def _comic_filename(self, ext: str=".jpg") -> str:
        # Дописываем точку к расширению, если отсутствует
        if ext and not ext.startswith("."):
            ext = f".{ext}"
        return self.make_safe_filename(f"{self._comic_page_title()}{ext}")

    def _comic_page_title(self) -> str:
        if self.page is None:
            raise ValueError("page is None")
        return f"{self.page:0>4}"

    def _comic_page_description(self) -> str|None:
        return None

    def download_comic_page(self) -> int|None:
        if not self.data:
            raise ValueError("data is None")
        # Путь к скачанному файлу
        ext = os.path.splitext(self._comic_file_link())[-1] or ".jpg"
        if self.chapter and self.chapter_title:
            chapter_folder = self.make_safe_filename(f"{self.chapter} - {self.chapter_title}")
        elif self.chapter_title:
            chapter_folder = self.make_safe_filename(self.chapter_title)
        elif self.chapter:
            chapter_folder = self.make_safe_filename(self.chapter)
        else:
            raise ValueError("self.chapter_title or self.chapter is None")
        chapter_dir = os.path.join(
            self.folder,
            chapter_folder
        )
        comic_filepath = os.path.join(
            chapter_dir,
            self._comic_filename(ext=ext)
        )

        # Перескачивать уже существующий файл не нужно
        if not self._check_corrects_file(comic_filepath):
            if not os.path.isdir(chapter_dir):
                os.makedirs(chapter_dir)
            # Скачивание
            try:
                for img_domain in range(len(self._IMG_DOMAIN)):
                    try:
                        with requests.get(
                            self._comic_file_link(img_domain=img_domain),
                            headers = self._HEADERS,
                            timeout = 180
                        ) as resp:
                            with open(comic_filepath, 'wb') as file:
                                file.write(resp.content)
                        break
                    except requests.exceptions.RequestException as exc:
                        if img_domain+1==len(self._IMG_DOMAIN):
                            raise exc
            except TimeoutError:
                time.sleep(5)
                return None

        # В случае успеха вернём номер страницы, иначе None
        if self._check_corrects_file(comic_filepath):
            return self.page
        return None

    async def async_download_comic_page(
        self,
        session: aiohttp.ClientSession|None = None
    ) -> int|None:
        if self.page is None:
            raise ValueError("page is None")
        # Без сессии скачиваем страницу обычным запросом
        if session:
            _request = session.request
        else:
            _request = aiohttp.request

        # Путь к скачанному файлу
        ext = os.path.splitext(self._comic_file_link())[-1] or ".jpg"
        if self.chapter and self.chapter_title:
            chapter_folder = self.make_safe_filename(f"{self.chapter} - {self.chapter_title}")
        elif self.chapter_title:
            chapter_folder = self.make_safe_filename(self.chapter_title)
        elif self.chapter:
            chapter_folder = self.make_safe_filename(self.chapter)
        else:
            raise ValueError("self.chapter_title or self.chapter is None")
        chapter_dir = os.path.join(
            self.folder,
            chapter_folder
        )
        comic_filepath = os.path.join(
            chapter_dir,
            self._comic_filename(ext=ext)
        )

        # Перескачивать уже существующий файл не нужно
        if not self._check_corrects_file(comic_filepath):
            if not os.path.isdir(chapter_dir):
                os.makedirs(chapter_dir)
            # Скачивание
            try:
                for img_domain in range(len(self._IMG_DOMAIN)):
                    try:
                        async with _request(
                            "GET",
                            self._comic_file_link(img_domain),
                            headers=self._HEADERS
                        ) as resp:
                            async with aiofile.async_open(comic_filepath, 'wb') as file:
                                await file.write(await resp.read())
                        break
                    except Exception as exc:
                        raise exc
            except TimeoutError:
                await asyncio.sleep(1)
                return None

        # В случае успеха вернём номер страницы, иначе None
        if self._check_corrects_file(comic_filepath):
            return self.page
        return None

if __name__ == '__main__':
    downloader = Downloader()

    # Скачивание
    r_chapter = downloader.downloadcomic()
    # Возвращаемое значение — номер новой нескачанной страницы
    r = '.'.join(r_chapter.data[:2])
    print(r)
