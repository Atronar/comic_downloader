"""Модуль скачивания комиксов с HentaiLib
https://hentailib.me/
"""

import json

try:
    import tomlkit as tomllib
except ModuleNotFoundError:
    import tomllib
from typing import Any, TypedDict
import urllib.parse
import asyncio
import aiohttp
from bs4 import BeautifulSoup, SoupStrainer
import httpx
from base_downloader import BaseDownloader
import mangalib

ChapterNumber = mangalib.ChapterNumber

class _BS_JSONPageData(TypedDict):
    p: int
    u: str

class Downloader(mangalib.Downloader):
    def __init__(
        self,
        token: dict[str, str]|None = None,
        token_path: str|None = "config.toml",
        **kwargs
    ):
        BaseDownloader.__init__(self, **kwargs)
        # Страницы могут быть вида 58.1
        self.first: ChapterNumber = ChapterNumber(self.first)
        self.last: ChapterNumber = ChapterNumber(self.last)
        self._COMIC_DOMAIN: str
        if not kwargs.get("_COMIC_DOMAIN"):
            self._COMIC_DOMAIN, self.comic_name = self.comic_name.rsplit("/",1)
        else:
            self._COMIC_DOMAIN = str(kwargs.get("_COMIC_DOMAIN"))
        self.chapters_data: list[dict[str, Any]]|None = None
        self._HEADERS: dict[str, str] = {
            'user-agent': '',
            "referer": f"https://{self._COMIC_DOMAIN}/"
        }

        self.token_path = token_path
        if token:
            self.token = self._clean_token(token)
        elif token_path:
            self.token = get_token(token_path)
        else:
            raise ValueError("token from cookie mangalib_session needed")
        if user_id := kwargs.get("user_id"):
            self.user_id = int(user_id)
        else:
            self.user_id = self._get_user_id()

    @property
    def _params(self):
        params = super()._params
        params.update({
            "_COMIC_DOMAIN": self._COMIC_DOMAIN,
            "token": self.token,
            "token_path": self.token_path,
            "user_id": str(self.user_id),
        })
        return params

    def _clean_token(self, token: dict[str, str]) -> dict[str, str]:
        token['mangalib_session'] = token['mangalib_session'].rstrip(";")
        if token['mangalib_session'][-1] == "=":
            token['mangalib_session'] = urllib.parse.quote(token['mangalib_session'])

        if 'mangalib_remember_web' in token:
            token['mangalib_remember_web'] = token['mangalib_remember_web'].rstrip(";")
            if token['mangalib_remember_web'][-1] == "=":
                mangalib_remember_web = token['mangalib_remember_web'].split('=', 1)
                mangalib_remember_web[1] = urllib.parse.quote(mangalib_remember_web[1])
                token['mangalib_remember_web'] = '='.join([
                    mangalib_remember_web[0],
                    mangalib_remember_web[1]
                ])
        return token

    def _get_user_id(self) -> int:
        mangalib_remember_web = self.token["mangalib_remember_web"].split('=', 1)
        with httpx.Client(
            headers = self._HEADERS,
            cookies = {
                "mangalib_session": self.token["mangalib_session"],
                mangalib_remember_web[0]: mangalib_remember_web[1],
            },
            http2 = True
        ) as client:
            # Айдишник берётся из пути в заголовке редиректа
            resp = client.head(self._COMIC_DOMAIN, allow_redirects=False)
            location = resp.headers.get("location", None)
            if location is None:
                raise ValueError("Кука устарела")
            # Обновляем куку
            if token := resp.cookies.get("mangalib_session"):
                self.token["mangalib_session"] = token
                if self.token_path:
                    update_token(token, path=self.token_path)
        user_id = int(location.rsplit("-", 1)[-1])
        return user_id

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

        # Получаем данные частей
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
            # # Берём номер тома
            # num_volume = self._to_number(chapter.get("volume", None))
            # if num_volume is None:
            #     raise ValueError(f'{num_volume=}')
            # Загрузчик частей
            chapter_downloader = ChapterDownloader(chapter, **self._params)
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

            # Получаем данные частей
            if not self.chapters_data:
                self.chapters_data = await self._async_get_chapters_data(async_session=session)

            # Скачивание
            # Создание списка задач
            tasks: dict[str, dict] = {}
            for chapter in self.chapters_data:
                # Берём номер части
                num_chapter = chapter.get("number", None)
                if num_chapter is None:
                    raise ValueError(f'{num_chapter=}')
                # Если часть до первой нужной, то пропускаем
                if self.first > ChapterNumber(num_chapter):
                    continue
                # Начиная с последней, пропускаем
                if self.last <= ChapterNumber(num_chapter):
                    break
                # Берём номер тома
                # num_volume = chapter.get("volume", None)
                # if num_volume is None:
                #     raise ValueError(f'{num_volume=}')
                # Загрузчик частей
                chapter_downloader = ChapterDownloader(chapter, **self._params)
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

class ChapterDownloader(Downloader, mangalib.ChapterDownloader):
    def __init__(
        self,
        chapter_data: dict[str, Any],
        **kwargs
    ):
        Downloader.__init__(self, **kwargs)
        self.data = self._get_chapter_data(chapter_data)

    @classmethod
    async def async_create(
        cls,
        chapter_data: dict[str, Any],
        **kwargs
    ):
        return cls(chapter_data=chapter_data, **kwargs)

    def _get_chapter_data(
        self,
        chapter_data: dict[str, Any]
    ) -> dict[str, Any]:
        # Инициализируем из доступных данных главу, часть и ид части
        volume: str = chapter_data.get("volume", None)
        if volume is None:
            raise ValueError(f'{volume=}')
        chapter: str = chapter_data.get("number", None)
        if chapter is None:
            raise ValueError(f'{chapter=}')
        chapter_id: int = chapter_data.get("id", None)
        if chapter_id is None:
            raise ValueError(f'{chapter_id=}')

        # Подключение к хентайлибу по http/2
        mangalib_remember_web = self.token["mangalib_remember_web"].split('=', 1)
        with httpx.Client(
            headers=self._HEADERS,
            cookies={
                "mangalib_session": self.token["mangalib_session"],
                mangalib_remember_web[0]: mangalib_remember_web[1],
            },
            http2=True
        ) as client:
            # Нужные нам данные можно получить на первой открытой странице
            url = f"{self._COMIC_DOMAIN}/{self.comic_name}/v{volume}/c{chapter}?ui={self.user_id}&page=1"
            resp = client.get(url)
            # Обновляем куку
            if token := resp.cookies.get("mangalib_session"):
                self.token["mangalib_session"] = token
                if self.token_path:
                    update_token(token, path=self.token_path)
            content_data = BeautifulSoup(
                resp.content,
                "lxml",
                parse_only=SoupStrainer("script", {"id": "pg"})
            ).find("script")
        if content_data:
            # Так как список страниц хранится в жаваскрипте, выдираем его
            json_string = content_data.get_text(strip=True).split("=", 1)[-1].strip(";")
        else:
            raise ValueError(f"Illegal json on {url}")
        pages_data: list[_BS_JSONPageData] = json.loads(json_string)
        # Дописываем данные части нужными данными
        chapter_data.update({
            "pages": [
                {
                    "slug": page_data.get('p'),
                    "url": f"//manga/{self.comic_name}/chapters/{chapter_id}/{page_data.get('u')}"
                }
                for page_data in pages_data
            ]
        })
        return chapter_data

    async def _async_get_chapter_data(
        self,
        chapter_data: dict[str, Any]
    ) -> dict[str, Any]:
        return self._get_chapter_data(chapter_data)

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

class PageDownloader(Downloader, mangalib.PageDownloader):
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

        self.chapter = chapter

        self.data: dict[str, str|int]
        if data:
            self.data = data
        else:
            # Отсутствующие данные страницы можно получить, зная часть
            if not chapter_data:
                if self.chapter is None:
                    raise ValueError("chapter is None")
                # Перебираем части, ища нужную - они списком
                chapters_data = self._get_chapters_data(use_async=False)
                for chapters_item in chapters_data:
                    if chapters_item.get("number", None) == self.chapter:
                        # chapters_item не содержит информации страниц,
                        # для этого надо отправить запрос на получение
                        # (делается при создании ChapterDownloader)
                        chapter_kwargs = kwargs.copy()
                        chapter_kwargs.update(use_async=False)
                        chapter_data = ChapterDownloader(chapters_item, **chapter_kwargs).data
                        break
                if not chapter_data:
                    raise ValueError("Page data is None")
            # Часть содержит данные всех страниц, ищем текущую
            for chapter_page in chapter_data.get("pages", []):
                if chapter_page.get("slug") == page:
                    self.data = chapter_page
                    break

        self.volume: str
        if volume:
            self.volume = volume
        else:
            # Отсутствующий том можно получить, зная часть
            if not chapter_data:
                if self.chapter is None:
                    raise ValueError("chapter is None")
                # Перебираем части, ища нужную - они списком
                chapters_data = self._get_chapters_data(use_async=False)
                for chapters_item in chapters_data:
                    if chapters_item.get("number", None) == self.chapter:
                        # chapters_item содержит номер тома
                        chapter_data = chapters_item
                        break
                if not chapter_data:
                    raise ValueError("volume is None")
            # Том указан вместе с номером части
            volume = chapter_data.get("volume", None)
            if volume is None:
                raise ValueError("chapter_title is None")
            self.volume = volume

        self.chapter_title: str
        if chapter_title:
            self.chapter_title = chapter_title
        else:
            # Отсутствующий заголовок можно получить, зная часть
            if not chapter_data:
                if self.chapter is None:
                    raise ValueError("chapter is None")
                # Перебираем части, ища нужную - они списком
                chapters_data = self._get_chapters_data(use_async=False)
                for chapters_item in chapters_data:
                    if chapters_item.get("number", None) == self.chapter:
                        # chapters_item содержит заголовок части
                        chapter_data = chapters_item
                        break
                if not chapter_data:
                    raise ValueError("chapter_title is None")
            # Заголовок части указан вместе с номером части
            chapter_title = chapter_data.get("name", None)
            if chapter_title is None:
                if "name" not in chapter_data.keys():
                    raise ValueError("chapter_title is None")
                chapter_title = ""
            self.chapter_title = chapter_title

        self.page: int
        if page:
            self.page = page
        else:
            if not (slug := self.data.get("slug")):
                raise ValueError("page is None")
            self.page = int(slug)

def get_token(path: str = "config.toml") -> dict[str, str]:
    """Получение токена mangalib_session из файла

    Сам токен должен быть заранее записан в файл из соответствующей куки на сайте в виде
    mangalib_session = "***токен***"
    mangalib_remember_web = "remember_web_***=***"
    """
    with open(path, "rb") as file:
        config = tomllib.load(file)
    return {
        'mangalib_session': str(config['mangalib_session']),
        'mangalib_remember_web': str(config['mangalib_remember_web']),
    }

def update_token(token: str, path: str = "config.toml"):
    """Обновление токена в файле
    """
    # Для обновления нужен tomlkit, но его установка необязательна -
    # без него обновление токена должно игнорироваться
    try:
        with open(path, "rb") as file:
            config = tomllib.load(file)
        config['mangalib_session'] = token
        with open(path, "wt", encoding="utf-8") as file:
            # unwrap() предотвращает запись бесконечно созданных переносов строк
            tomllib.dump(config.unwrap(), file) # type: ignore
    except AttributeError:
        pass

if __name__ == '__main__':
    downloader = Downloader()

    # Скачивание
    r_chapter = downloader.downloadcomic()
    # Возвращаемое значение — номер новой нескачанной страницы
    r = '.'.join(map(str, r_chapter.data[:2]))
    print(r)
