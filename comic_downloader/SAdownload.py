"""Модуль скачивания комикса Sequential Art
https://www.collectedcurios.com/sequentialart.php
"""

import argparse
import os
import sys
import urllib.request
import urllib.error
import asyncio
import aiohttp

def arg_parser():
    """Парсер аргументов командной строки
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'first',
        nargs = '?',
        help = 'Номер первой страницы, число',
        type = int,
        default = 1
    )
    parser.add_argument(
        '-last',
        help = (
            'Номер последней страницы, число. '
            'Если больше возможного, то качается до последнего существующего.'
        ),
        type = int,
        default = None
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

def _comic_file_link(page: int|str) -> str:
    """Получение ссылки на файл страницы комикса на сервере"""
    return f"http://www.collectedcurios.com/SA_{page:0>4}_small.jpg"

def _comic_filename(page: int|str) -> str:
    """Получение имени файла страницы комикса"""
    file_link = _comic_file_link(page)
    return file_link.rsplit("/", 1)[-1]

def _check_corrects_file(filepath: str|os.PathLike) -> bool:
    """Проверка файла на существование и корректность"""
    return os.path.exists(filepath) and os.path.getsize(filepath) > 8

def find_last(first_unknown_exists_page: int=1, force_add_mode: bool=False) -> int:
    """Поиск номера следующей за последней доступной страницы комикса на сервере

    Parameters
    ----------
    first_unknown_exists_page: int
        Номер первой страницы, доступность которой неизвестна
        Поиск будет вестись, начиная с неё

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
    if not force_add_mode or first_unknown_exists_page < 500:
        return _find_last_mul(first_unknown_exists_page)
    return _find_last_add(first_unknown_exists_page)

def _find_last_mul(first_unknown_exists_page: int=1) -> int:
    """Бинарный поиск номера следующей за последней доступной
    страницы комикса на сервере
    """
    min_ = first_unknown_exists_page
    max_ = first_unknown_exists_page
    step = 1
    max_need_search = True

    def find_max_handler():
        """Сдвиг поиска и верхней грани вверх с удвоением шага"""
        nonlocal min_, first_unknown_exists_page, step, max_
        min_ = first_unknown_exists_page
        first_unknown_exists_page += step
        step *= 2
        max_ = first_unknown_exists_page

    def set_min_handler():
        """Сдвиг нижней грани вверх, центрирование поиска между гранями"""
        nonlocal min_, first_unknown_exists_page, max_
        min_ = first_unknown_exists_page
        first_unknown_exists_page = (min_ + max_) // 2

    def set_max_handler():
        """Сдвиг верхней грани вниз, центрирование поиска между гранями"""
        nonlocal min_, first_unknown_exists_page, max_
        max_ = first_unknown_exists_page
        first_unknown_exists_page = (min_ + max_) // 2

    while True:
        try:
            resp_code = _findlast_check(first_unknown_exists_page)
            # Страница существует, поэтому ...
            if resp_code == 200:
                if max_need_search:
                    # ..., так как верхнюю грань не нашли, сдвигаем её вверх до найденной
                    find_max_handler()
                elif first_unknown_exists_page - min_ > 0:
                    # ..., так как верхняя грань известна, сдвигаем нижнюю грань вверх до найденной
                    set_min_handler()
                else:
                    # ..., так как верхняя и нижняя грань совпали, возвращаем найденное
                    return first_unknown_exists_page + 1
        except urllib.error.HTTPError as err:
            # Страница не существует, поэтому ...
            if err.code == 404:
                if max_need_search:
                    # ... это искомая верхняя грань, далее будет идти лишь сдвиг граней
                    max_need_search = False
                    set_max_handler()
                elif first_unknown_exists_page - min_ > 0:
                    # ... сдвигаем верхнюю грань вниз до несуществующей
                    set_max_handler()
                else:
                    # ..., так как верхняя и нижняя грань совпали, возвращаем найденное
                    return first_unknown_exists_page

def _find_last_add(first_unknown_exists_page: int=1) -> int:
    """Последовательный поиск номера следующей за последней доступной
    страницы комикса на сервере
    """
    while True:
        try:
            resp_code = _findlast_check(first_unknown_exists_page)
            # Страница существует, поэтому ...
            if resp_code == 200:
                # ... переходим к следующей
                first_unknown_exists_page += 1
        except urllib.error.HTTPError as err:
            # Страница не существует, поэтому ...
            if err.code == 404:
                # ... возвращаем найденное
                return first_unknown_exists_page

def _findlast_check(page: int|str) -> int:
    """Запрос страницы комикса на сервере
    Возвращается код ответа
    """
    with urllib.request.urlopen(_comic_file_link(page)) as response:
        return response.getcode()

def download_comic_page(page: int, folder: str|os.PathLike='.') -> int|None:
    """Скачивание одной страницы комикса

    Parameters
    ----------
    page: int
        Номер скачиваемой страницы

    folder: str | PathLike
        Папка, в которую осуществляется скачивание

    Return
    ------
    int
        Номер страницы, которая только что успешно скачалась, либо

    None
        Маркер, что скачивание не удалось
    """
    # Путь к скачанному файлу
    comic_filepath = os.path.join(folder, _comic_filename(page))
    # Перескачивать уже существующий файл не нужно
    if not _check_corrects_file(comic_filepath):
        urllib.request.urlretrieve(
            _comic_file_link(page),
            comic_filepath
        )
    # В случае успеха вернём номер страницы, иначе None
    if _check_corrects_file(comic_filepath):
        return page
    return None

def downloadcomic(
    first: int = 1,
    last: int|None = None,
    folder: str|os.PathLike = '.',
    use_async: bool = True
) -> int:
    """Скачивание заданных страниц комикса от first до last

    Parameters
    ----------
    first: int
        Номер первой страницы, которую ещё не скачивали

    last: int | None
        Номер последней страницы, до которой (не включительно) вести скачивание
        Если страниц существует меньше, то скачиваться будут страницы до последней существующей
        Если не указано, то скачиваться будут страницы до последней существующей

    folder: str | PathLike
        Папка, в которую осуществляется скачивание

    use_async: bool
        Скачивание посредством асинхронной функции
        вместо последовательного постраничного скачивания
        По умолчанию включено

    Return
    ------
    int
        Номер первой недоступной страницы
        При следующей проверке в аргумент first надо поместить именно это значение

        Если на сервере есть страницы с 1 по 10, но 11 ещё не вышла, то вернётся именно 11
    """
    # Асинхронное скачивание
    if use_async:
        loop = asyncio.get_event_loop()
        last_success = loop.run_until_complete(
            async_downloadcomic(
                first = first,
                last = last,
                folder = folder
            )
        )
        loop.close()
        return last_success

    # Обычное скачивание
    # Установка последней страницы при её отсутствии
    if not last:
        last = find_last(first)
    # Последовательно скачиваем страницы,
    # запоминаем, на какой странице необходимо начинать следующее скачивание
    last_success = first
    for i in range(first, last):
        if (result := download_comic_page(i, folder=folder)) and last_success == result:
            last_success = result + 1
    return last_success

async def _async_download_comic_page(
    page: int,
    folder: str|os.PathLike = '.',
    session: aiohttp.ClientSession|None = None
) -> int|None:
    """Асинхронное скачивание одной страницы комикса

    Parameters
    ----------

    page: int
        Номер скачиваемой страницы

    folder: str | PathLike
        Папка, в которую осуществляется скачивание

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
    # Без сессии скачиваем страницу обычным способом
    if not session:
        return download_comic_page(page, folder=folder)

    # Путь к скачанному файлу
    comic_filepath = os.path.join(folder, _comic_filename(page))
    # Перескачивать уже существующий файл не нужно
    if not _check_corrects_file(comic_filepath):
        async with session.get(_comic_file_link(page)) as resp:
            with open(comic_filepath, 'wb') as file:
                file.write(await resp.read())
    # В случае успеха вернём номер страницы, иначе None
    if _check_corrects_file(comic_filepath):
        return page
    return None

async def async_downloadcomic(
    first: int = 1,
    last: int|None = None,
    folder: str|os.PathLike = '.'
) -> int:
    """Асинхронное скачивание заданных страниц комикса от first до last

    Parameters
    ----------
    first: int
        Номер первой страницы, которую ещё не скачивали

    last: int | None
        Номер последней страницы, до которой (не включительно) вести скачивание
        Если страниц существует меньше, то скачиваться будут страницы до последней существующей
        Если не указано, то скачиваться будут страницы до последней существующей

    folder: str | PathLike
        Папка, в которую осуществляется скачивание

    Return
    ------
    int
        Номер первой недоступной страницы
        При следующей проверке в аргумент first надо поместить именно это значение

        Если на сервере есть страницы с 1 по 10, но 11 ещё не вышла, то вернётся именно 11
    """
    # Если последняя страница не указана, то узнаём её, собственно, номер
    if not last:
        last = find_last(first)

    # Скачивание
    async with aiohttp.ClientSession() as session:
        # Создание списка задач
        tasks = [
            _async_download_comic_page(i, folder=folder, session=session)
            for i in range(first, last)
        ]
        # Запуск задач
        results = await asyncio.gather(*tasks)
        # Чистка результатов
        results: list[int] = sorted(filter(bool, results))

    # Возврат следующей к скачиванию страницы
    if last - first == len(results):
        # Длина списка результатов совпадает с количеством запрошенных страниц
        return max(results) + 1
    # Результатов меньше запрошенного, вероятно есть нескачанное
    # Ищем первую пропущенную страницу и возвращаем её
    last_success = first
    for i in results:
        if last_success == i:
            last_success += 1
        else:
            return last_success
    return last_success

if __name__ == '__main__':
    # Берём аргументы запуска
    args = arg_parser().parse_args()

    # Скачивание
    r = downloadcomic(
        first = args.first,
        last = args.last,
        folder = args.folder,
        use_async = not args.no_async
    )
    # Возвращаемое значение — номер новой нескачанной страницы
    sys.exit(r)
