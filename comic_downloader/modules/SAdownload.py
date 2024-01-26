"""Модуль скачивания комикса Sequential Art
https://www.collectedcurios.com/sequentialart.php
"""

import os
from typing import Final
import urllib.request
import asyncio
import aiofile
import aiohttp
import requests
from base_downloader import BaseDownloader, BasePageDownloader

class Downloader(BaseDownloader):
    _COMIC_DOMAIN: Final[str] = "https://www.collectedcurios.com"

    def _comic_main_page_link(self) -> str:
        return f"{self._COMIC_DOMAIN}/sequentialart.php"

    def find_last(self, force_add_mode: bool=False) -> int:
        """Поиск номера следующей за последней доступной страницы комикса на сервере

        Parameters
        ----------
        force_add_mode: bool
            Принудительное использование последовательного постраничного поиска
            При exists_page более 500 не используется
            По умолчанию используется бинарный поиск

        Return
        ------
        int
            Номер страницы, которую надо проверять для обновления

            Если на сервере есть страницы с 1 по 10, но 11 ещё не вышла, то вернётся именно 11
        """
        # Если нынешняя страница слишком большая,
        # то бинарный поиск чаще может оказаться избыточным,
        # например, если в итоге нужная страница окажется следующей
        with requests.Session() as session:
            if not force_add_mode or self.first < 500:
                self.last = self._find_last_mul(session=session)
            else:
                self.last = self._find_last_add(session=session)
        return self.last

    def _find_last_mul(self, session: requests.Session|None=None) -> int:
        """Бинарный поиск номера следующей за последней доступной
        страницы комикса на сервере
        """
        exists_page = PageDownloader(self.first)
        if exists_page.page is None:
            raise ValueError("page is None")
        exists_page.page = int(exists_page.page)
        min_ = exists_page.page
        max_ = exists_page.page
        step = 1
        max_need_search = True

        def find_max_handler():
            """Сдвиг поиска и верхней грани вверх с удвоением шага"""
            nonlocal min_, exists_page, step, max_
            if exists_page.page is None:
                raise ValueError("page is None")
            exists_page.page = int(exists_page.page)
            min_ = exists_page.page
            exists_page.page += step
            step *= 2
            max_ = exists_page.page

        def set_min_handler():
            """Сдвиг нижней грани вверх, центрирование поиска между гранями"""
            nonlocal min_, exists_page, max_
            if exists_page.page is None:
                raise ValueError("page is None")
            exists_page.page = int(exists_page.page)
            min_ = exists_page.page
            exists_page.page = (min_ + max_) // 2

        def set_max_handler():
            """Сдвиг верхней грани вниз, центрирование поиска между гранями"""
            nonlocal min_, exists_page, max_
            if exists_page.page is None:
                raise ValueError("page is None")
            exists_page.page = int(exists_page.page)
            max_ = exists_page.page
            exists_page.page = (min_ + max_) // 2

        while True:
            resp_code = self._findlast_check(exists_page._comic_file_link(), session=session)
            # Страница существует, поэтому ...
            if resp_code == 200:
                if max_need_search:
                    # ..., так как верхнюю грань не нашли, сдвигаем её вверх до найденной
                    find_max_handler()
                elif exists_page.page - min_ > 0:
                    # ..., так как верхняя грань известна, сдвигаем нижнюю грань вверх до найденной
                    set_min_handler()
                else:
                    # ..., так как верхняя и нижняя грань совпали, возвращаем найденное
                    return exists_page.page + 1
            # Страница не существует, поэтому ...
            elif resp_code == 404:
                if max_need_search:
                    # ... это искомая верхняя грань, далее будет идти лишь сдвиг граней
                    max_need_search = False
                    set_max_handler()
                elif exists_page.page - min_ > 0:
                    # ... сдвигаем верхнюю грань вниз до несуществующей
                    set_max_handler()
                else:
                    # ..., так как верхняя и нижняя грань совпали, возвращаем найденное
                    return exists_page.page
            else:
                raise requests.HTTPError(f"{resp_code} http code error")

    def _find_last_add(self, session: requests.Session|None=None) -> int:
        """Последовательный поиск номера следующей за последней доступной
        страницы комикса на сервере
        """
        exists_page = PageDownloader(self.first)
        if exists_page.page is None:
            raise ValueError("page is None")
        exists_page.page = int(exists_page.page)
        while True:
            resp_code = self._findlast_check(exists_page._comic_file_link(), session=session)
            # Страница существует, поэтому ...
            if resp_code == 200:
                # ... переходим к следующей
                exists_page.page += 1
            # Страница не существует, поэтому ...
            elif resp_code == 404:
                # ... возвращаем найденное
                return exists_page.page
            else:
                raise requests.HTTPError(f"{resp_code} http code error")

    def _findlast_check(self, comic_file_link: str, session: requests.Session|None=None) -> int:
        """Запрос страницы комикса на сервере
        Возвращается код ответа
        """
        if session:
            _get = session.get
        else:
            _get = requests.get
        with _get(comic_file_link) as response:
            return response.status_code

    async def async_find_last(
        self,
        async_session: None=None,
        force_add_mode: bool=False
    ) -> int:
        """Поиск номера следующей за последней доступной страницы комикса на сервере

        Поскольку асинхронность при используемом поиске не имеет смысла,
        данная функция — всего лишь async синоним find_last()

        Parameters
        ----------
        force_add_mode: bool
            Принудительное использование последовательного постраничного поиска
            При exists_page более 500 не используется
            По умолчанию используется бинарный поиск

        Return
        ------
        int
            Номер страницы, которую надо проверять для обновления

            Если на сервере есть страницы с 1 по 10, но 11 ещё не вышла, то вернётся именно 11
        """
        return self.find_last(force_add_mode=force_add_mode)

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

        if self.first >= self.last:
            return self.last

        # Последовательно скачиваем страницы,
        # запоминаем, на какой странице необходимо начинать следующее скачивание
        last_success = self.first
        for num in range(self.first, self.last):
            # Загрузчик страниц
            page_downloader = PageDownloader(num, **self._params)
            if (result := page_downloader.download_comic_page()) and last_success == result:
                last_success = result + 1
        return last_success

    async def async_downloadcomic(self) -> int:
        # Если последняя страница не указана, то узнаём её, собственно, номер
        if not self.last:
            self.last = self.find_last()

        if self.first >= self.last:
            return self.last

        # Скачивание
        async with aiohttp.ClientSession() as session:
            # Создание списка задач
            tasks = []
            # reversed, так как задачи выполняются последний пришёл - первый ушёл, а нам надо по порядку
            for page in reversed(range(self.first, self.last)):
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
    def _comic_file_page_link(self) -> str:
        if self.page is None:
            raise ValueError("page is None")
        return f"{self._comic_main_page_link()}?s={self.page}"

    def _comic_file_link(self) -> str:
        return f"{self._COMIC_DOMAIN}/{self._comic_page_title()}_small.jpg"

    def _comic_filename(self) -> str:
        file_link = self._comic_file_link()
        return file_link.rsplit("/", 1)[-1]

    def _comic_page_title(self) -> str:
        if self.page is None:
            raise ValueError("page is None")
        return f"SA_{self.page:0>4}"

    def _comic_page_description(self) -> str|None:
        return None

    def download_comic_page(self) -> int|None:
        if self.page is None:
            raise ValueError("page is None")
        # Путь к скачанному файлу
        comic_filepath = os.path.join(self.folder, self._comic_filename())
        # Перескачивать уже существующий файл не нужно
        if not self._check_corrects_file(comic_filepath):
            urllib.request.urlretrieve(
                self._comic_file_link(),
                comic_filepath
            )
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
        # Без сессии скачиваем страницу обычным способом
        if not session:
            return self.download_comic_page()

        # Путь к скачанному файлу
        comic_filepath = os.path.join(self.folder, self._comic_filename())
        # Перескачивать уже существующий файл не нужно
        if not self._check_corrects_file(comic_filepath):
            async with session.get(self._comic_file_link()) as resp:
                async with aiofile.async_open(comic_filepath, 'wb') as file:
                    await file.write(await resp.read())
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
