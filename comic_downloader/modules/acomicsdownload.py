"""Модуль скачивания комиксов с AComics
https://acomics.ru
"""

import os
import sys
from typing import Final, Iterable
import urllib.request
import asyncio
import aiofile
import aiohttp
from bs4 import BeautifulSoup, PageElement, SoupStrainer, Tag
from base_downloader import BaseDownloader, BasePageDownloader

class Downloader(BaseDownloader):
    _COMIC_DOMAIN: Final[str] = "https://acomics.ru"
    _REQUEST_HEADERS: Final = {'Cookie': 'ageRestrict=100'}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.comic_name = self.comic_name.rsplit("/",1)[-1]
        if not self.comic_name.startswith("~"):
            self.comic_name = f"~{self.comic_name}"

    @property
    def _comic_main_page_link(self) -> str:
        return f"{self._COMIC_DOMAIN}/{self.comic_name}"

    def html_to_text(self, elements_list: Iterable[PageElement]|Tag) -> str:
        """Преобразование списка html-элементов страницы в более читаемый вид

        Parameters
        ----------
        elements_list: Iterable[PageElement]
            Список html-элементов: тегов, содержащихся в них строк
            Также могут быть сами теги

        Return
        ------
        str
            Человекочитаемый текст без html-тегов

            <a href=https://ссылка>Текст ссылки</a>
            заменяются на
            Текст ссылки (https://ссылка)

            <img src=https://ссылка_на_картинку>
            заменяются на
            (# https://ссылка_на_картинку #)

            <br> заменяется на перевод строки
            <hr> заменяется на 5 дефисов и перевод строки
        """
        text = ""
        for page_element in elements_list:
            if isinstance(page_element, str):
                text += page_element
            elif isinstance(page_element, Tag):
                if page_element.name in [
                    'div', 'span', 'p',
                    'em', 'strong',
                    'h3', 'h2', 'h1'
                ]:
                    # Обрабатываем содержимое тега
                    text += self.html_to_text(page_element)
                elif page_element.name == 'hr':
                    text += '-----\n'
                elif page_element.name == 'br':
                    text += '\n'
                elif page_element.name == 'a':
                    # Текст ссылки (https://ссылка)
                    text += (
                        f"{self.html_to_text(page_element.children)} "
                        f"({page_element.attrs.get('href', '')})"
                    )
                elif page_element.name == 'img':
                    # (# https://ссылка_на_картинку #)
                    text += f"(# {page_element.attrs.get('src')} #)"
                else:
                    raise ValueError(page_element)
            else:
                raise ValueError(page_element)
        return self._clear_text_multiplespaces(text)

    def find_last(self) -> int:
        # Устанавливаем куку для обхода ограничения возраста
        req = urllib.request.Request(self._comic_main_page_link, headers=self._REQUEST_HEADERS)

        # На самой странице ищем ссылку, указывающую на чтение с конца
        with urllib.request.urlopen(req) as file:
            read_menu = BeautifulSoup(
                file.read(),
                "lxml",
                parse_only=SoupStrainer('li', 'read-menu-item-short')
            )
        # Внутри класса ссылки на начало, конец и список. Нужен конец
        link_last: Tag = read_menu.find_all('a', limit=2)[1]
        href = link_last.attrs.get('href', '')
        # Вытаскиваем из ссылки номер последней существующей страницы
        last = int(href.split('/')[-1])
        # ...и возвращаем следующую
        self.last = last + 1
        return self.last

    async def async_find_last(
        self,
        async_session: aiohttp.ClientSession|None=None
    ) -> int:
        # Без сессии используем обычный запрос
        if async_session:
            _request = async_session.request
        else:
            _request = aiohttp.request

        # На самой странице ищем ссылку, указывающую на чтение с конца
        async with _request(
            "GET",
            self._comic_main_page_link,
            headers = self._REQUEST_HEADERS
        ) as file:
            read_menu = BeautifulSoup(
                await file.read(),
                "lxml",
                parse_only=SoupStrainer('li', 'read-menu-item-short')
            )
        # Внутри класса ссылки на начало, конец и список. Нужен конец
        link_last: Tag = read_menu.find_all('a', limit=2)[1]
        href = link_last.attrs.get('href', '')
        # Вытаскиваем из ссылки номер последней существующей страницы
        last = int(href.split('/')[-1])
        # ...и возвращаем следующую
        return last + 1

    def downloadcomic(self) -> int:
        # Асинхронное скачивание
        if self.use_async:
            loop = asyncio.get_event_loop()
            last_success = loop.run_until_complete(self.async_downloadcomic())
            loop.close()
            return last_success

        # Обычное скачивание
        # Установка последней страницы при её отсутствии
        if not self.last:
            self.last = self.find_last()
        else:
            self.last = min(self.last, self.find_last())

        if self.first >= self.last:
            return self.last

        # Загрузчик страниц
        page_downloader = PageDownloader(**self._params)

        # Последовательно скачиваем страницы,
        # запоминаем, на какой странице необходимо начинать следующее скачивание
        last_success = self.first
        for num in range(self.first, self.last):
            page_downloader.page = num
            if (result := page_downloader.download_comic_page()) and last_success == result:
                last_success = result + 1
        return last_success

    async def async_downloadcomic(self) -> int:
        async with aiohttp.ClientSession() as session:
            # Установка последней страницы при её отсутствии
            if not self.last:
                self.last = await self.async_find_last(async_session=session)
            else:
                self.last = min(self.last, await self.async_find_last(async_session=session))

            if self.first >= self.last:
                return self.last

            # Скачивание
            # Создание списка задач
            tasks = []
            for page in range(self.first, self.last):
                # Загрузчик страниц
                page_downloader = PageDownloader(page, **self._params)
                tasks.append(page_downloader.async_download_comic_page(session=session))
            # Запуск задач
            results = await asyncio.gather(*tasks)
            # Чистка результатов
            results: list[int] = sorted(filter(bool, results))

        # Возврат следующей к скачиванию страницы
        if self.last - self.first == len(results):
            # Длина списка результатов совпадает с количеством запрошенных страниц
            return max(results) + 1
        # Результатов меньше запрошенного, вероятно есть нескачанное
        # Ищем первую пропущенную страницу и возвращаем её
        last_success = self.first
        for i in results:
            if last_success == i:
                last_success += 1
            else:
                return last_success
        return last_success

class PageDownloader(BasePageDownloader, Downloader):
    def __init__(self, page: int|str|None = None, **kwargs):
        super().__init__(**kwargs)
        self.page = page
        self.content: BeautifulSoup|None = None

    def _comic_get_content_page(self) -> BeautifulSoup:
        """Получение html-контента, содержащего всю необходимую информцию"""
        # Устанавливаем куку для обхода ограничения возраста
        req = urllib.request.Request(self._comic_file_page_link, headers=self._REQUEST_HEADERS)

        with urllib.request.urlopen(req) as file:
            self.content = BeautifulSoup(
                file.read(),
                "lxml",
                parse_only=SoupStrainer('div', 'common-content')
            )
        return self.content

    async def _async_comic_get_content_page(
        self,
        async_session: aiohttp.ClientSession|None=None
    ) -> BeautifulSoup:
        """Асинхронное получение html-контента, содержащего всю необходимую информцию"""
        # Без сессии скачиваем страницу обычным запросом
        if async_session:
            _request = async_session.request
        else:
            _request = aiohttp.request

        async with _request('GET',
            self._comic_file_page_link,
            headers = self._REQUEST_HEADERS
        ) as file:
            content_page = BeautifulSoup(
                await file.read(),
                "lxml",
                parse_only=SoupStrainer('div', 'common-content')
            )
        return content_page

    @property
    def _comic_file_page_link(self) -> str:
        if self.page is None:
            raise ValueError("page is None")
        return f"{self._comic_main_page_link}/{self.page}"

    @property
    def _comic_file_link(self) -> str:
        if self.content is None:
            self.content = self._comic_get_content_page()

        img = self.content.find("img", "issue")
        if isinstance(img, Tag) and (src := img.attrs.get('src', None)):
            return f"{self._COMIC_DOMAIN}{src}"
        raise ValueError(self.content)

    def _comic_filename(self, ext: str=".jpg") -> str:
        if self.page is None:
            raise ValueError("page is None")
        # Дописываем точку к расширению, если отсутствует
        if ext and not ext.startswith("."):
            ext = f".{ext}"

        if title := self._comic_page_title:
            return self.make_safe_filename(f"{self.page} - {title}{ext}")
        return self.make_safe_filename(f"{self.page}{ext}")

    @property
    def _comic_page_title(self) -> str:
        if self.content is None:
            self.content = self._comic_get_content_page()

        span = self.content.find("span", "title")
        if span:
            return span.get_text(strip=True).rstrip(".")
        raise ValueError(self.content)

    @property
    def _comic_page_description(self) -> str|None:
        if self.content is None:
            self.content = self._comic_get_content_page()

        page_description: list[str] = []
        # Достаём текст из всплывающего сообщения на самом изображении
        if self.is_write_img_description:
            img = self.content.find("img", "issue")

            if not isinstance(img, Tag):
                raise ValueError(self.content)

            if img_description := img.attrs.get('title', None):
                page_description.append(img_description)

        # Достаём текст из поля описания
        if self.is_write_description:
            issue_description_text = self.content.find("section", "issue-description-text")

            if isinstance(issue_description_text, Tag):
                # Форматируем html-разметку в читаемый вид
                description_list = issue_description_text.children
                if description := self.html_to_text(description_list).strip():
                    page_description.append(description)
            elif isinstance(issue_description_text, str):
                # Добавляем чистую строку
                if description := issue_description_text.strip():
                    page_description.append(description)
            else:
                raise ValueError(self.content)

        # Сводим текст
        if page_description:
            return "\n\n-----\n\n".join(page_description)
        return None

    def download_comic_page(self) -> int|None:
        if self.page is None:
            raise ValueError("page is None")
        # Путь к скачанному файлу
        comic_filepath = os.path.join(
            self.folder,
            self._comic_filename()
        )
        comic_filepath_description = os.path.join(
            self.folder,
            self._comic_filename(ext=".txt")
        )

        # Перескачивать уже существующий файл не нужно
        if not self._check_corrects_file(comic_filepath):
            # Скачивание
            urllib.request.urlretrieve(self._comic_file_link, comic_filepath)

        # Перескачивать уже существующий файл описания не нужно
        if not self._check_corrects_file(comic_filepath_description):
            # Описание при странице
            if description := self._comic_page_description:
                with open(comic_filepath_description, "w", encoding="utf-8") as file:
                    file.write(description)

        # В случае успеха вернём номер страницы, иначе None
        if self._check_corrects_file(comic_filepath):
            return int(self.page)
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
        comic_filepath = os.path.join(
            self.folder,
            self._comic_filename()
            )
        comic_filepath_description = os.path.join(
            self.folder,
            self._comic_filename(ext=".txt")
        )

        # Перескачивать уже существующий файл не нужно
        if not self._check_corrects_file(comic_filepath):
            # Скачивание
            async with _request("GET", self._comic_file_link) as resp:
                async with aiofile.async_open(comic_filepath, 'wb') as file:
                    await file.write(await resp.read())

        # Перескачивать уже существующий файл описания не нужно
        if not self._check_corrects_file(comic_filepath_description):
            # Описание при странице
            if description := self._comic_page_description:
                async with aiofile.async_open(
                    comic_filepath_description,
                    "w",
                    encoding="utf-8"
                ) as file:
                    await file.write(description)

        # В случае успеха вернём номер страницы, иначе None
        if self._check_corrects_file(comic_filepath):
            return int(self.page)
        return None

if __name__ == '__main__':
    downloader = Downloader()

    # Скачивание
    r = downloader.downloadcomic()
    # Возвращаемое значение — номер новой нескачанной страницы
    print(r)
