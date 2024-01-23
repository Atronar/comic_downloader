"""Модуль скачивания комиксов с AComics
https://acomics.ru
"""

import argparse
import os
import sys
from typing import Iterable
import urllib.request
import asyncio
import aiofile
import aiohttp
from bs4 import BeautifulSoup, PageElement, SoupStrainer, Tag

def arg_parser():
    """Парсер аргументов командной строки
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'comic',
        help = 'Ссылка на главную страницу комикса на acomics',
        type = str
    )
    parser.add_argument(
        'first',
        nargs = '?',
        help = 'Первый номер, число',
        type = int,
        default = 1
    )
    parser.add_argument(
        '-last',
        nargs = '?',
        help = (
            'Номер последней страницы, число. '
            'Если больше возможного, то качается до последнего существующего.'
        ),
        type = int,
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

def _comic_main_page_link(short_name: str) -> str:
    """Получение ссылки на главную страницу комикса по краткому имени"""
    if not short_name.startswith("~"):
        short_name = f"~{short_name}"
    return f"https://acomics.ru/{short_name}"

def _comic_file_page_link(short_name: str, page: int|str) -> str:
    """Получение ссылки на страницу комикса"""
    return f"{_comic_main_page_link(short_name)}/{page}"

def _comic_filename(page: int|str, title: str|None=None, ext: str=".jpg") -> str:
    """Получение имени файла страницы комикса"""
    # Дописываем точку к расширению, если отсутствует
    if ext and not ext.startswith("."):
        ext = f".{ext}"

    if title:
        return make_safe_filename(f"{page} - {title}{ext}")
    return make_safe_filename(f"{page}{ext}")

def _check_corrects_file(filepath: str|os.PathLike) -> bool:
    """Проверка файла на существование и корректность"""
    return os.path.exists(filepath) and os.path.getsize(filepath) > 8

def _comic_get_content_page(
    comic_name: str,
    page: int|str
) -> BeautifulSoup:
    """Получение html-контента, содержащего всю необходимую информцию"""
    comic_page_link = _comic_file_page_link(comic_name, page)

    # Устанавливаем куку для обхода ограничения возраста
    req = urllib.request.Request(comic_page_link, headers={'Cookie': 'ageRestrict=100'})

    with urllib.request.urlopen(req) as file:
        content_page = BeautifulSoup(
            file.read(),
            "lxml",
            parse_only=SoupStrainer('div', 'common-content')
        )
    return content_page

async def _async_comic_get_content_page(
    comic_name: str,
    page: int|str,
    async_session: aiohttp.ClientSession|None=None
) -> BeautifulSoup:
    """Асинхронное получение html-контента, содержащего всю необходимую информцию"""
    # Без сессии скачиваем страницу обычным запросом
    if async_session:
        _request = async_session.request
    else:
        _request = aiohttp.request

    comic_page_link = _comic_file_page_link(comic_name, page)

    # Устанавливаем куку для обхода ограничения возраста
    headers = {'Cookie': 'ageRestrict=100'}

    async with _request('GET',
        comic_page_link,
        headers = headers
    ) as file:
        content_page = BeautifulSoup(
            await file.read(),
            "lxml",
            parse_only=SoupStrainer('div', 'common-content')
        )
    return content_page

def _comic_file_link(content: Tag) -> str:
    """Получение ссылки на файл страницы комикса на сервере"""
    img = content.find("img", "issue")
    if isinstance(img, Tag) and (src := img.attrs.get('src', None)):
        return f"https://acomics.ru{src}"
    raise ValueError(content)

def _comic_page_title(content: Tag) -> str:
    """Получение заголовка страницы комикса"""
    span = content.find("span", "title")
    if span:
        return span.get_text(strip=True).rstrip(".")
    raise ValueError(content)

def _comic_page_description(
    content: Tag,
    is_write_description: bool = True,
    is_write_img_description: bool = True
) -> str|None:
    """Получение описания страницы комикса

    Parameters
    ----------
    content: Tag
        html-тег, который может содержать другие теги и контент внутри

    is_write_description: bool
        Получать ли описание из соответствующего поля

    is_write_img_description: bool
        Получать ли всплывающий текст на изображении

    Return
    ------
    str
        Текст описания
        Если is_write_description и is_write_img_description установлены в True,
        то они разделяются пустыми строками и строкой с 5 дефисами

    None
        Если описания нет, возвращаетмя None
    """
    page_description: list[str] = []

    # Достаём текст из всплывающего сообщения на самом изображении
    if is_write_img_description:
        img = content.find("img", "issue")

        if not isinstance(img, Tag):
            raise ValueError(content)

        if img_description := img.attrs.get('title', None):
            page_description.append(img_description)

    # Достаём текст из поля описания
    if is_write_description:
        issue_description_text = content.find("section", "issue-description-text")

        if isinstance(issue_description_text, Tag):
            # Форматируем html-разметку в читаемый вид
            description_list = issue_description_text.children
            if description := html_to_text(description_list).strip():
                page_description.append(description)
        elif isinstance(issue_description_text, str):
            # Добавляем чистую строку
            if description := issue_description_text.strip():
                page_description.append(description)
        else:
            raise ValueError(content)

    # Сводим текст
    if page_description:
        return "\n\n-----\n\n".join(page_description)
    return None

def _clear_text_multiplespaces(text: str) -> str:
    """Очистка от множестенных пробелов и переносов строки"""
    text = "\n".join(line.strip() for line in text.splitlines())
    while "  " in text:
        text = text.replace("  ", " ")
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    return text

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

def html_to_text(elements_list: Iterable[PageElement]|Tag) -> str:
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
                text += html_to_text(page_element)
            elif page_element.name == 'hr':
                text += '-----\n'
            elif page_element.name == 'br':
                text += '\n'
            elif page_element.name == 'a':
                # Текст ссылки (https://ссылка)
                text += (
                    f"{html_to_text(page_element.children)} "
                    f"({page_element.attrs.get('href', '')})"
                )
            elif page_element.name == 'img':
                # (# https://ссылка_на_картинку #)
                text += f"(# {page_element.attrs.get('src')} #)"
            else:
                raise ValueError(page_element)
        else:
            raise ValueError(page_element)
    return _clear_text_multiplespaces(text)

def find_last(comic_name: str) -> int:
    """Поиск номера следующей за последней доступной страницы комикса на сервере

    Parameters
    ----------
    comic_name: str
        Короткое имя комикса
        Его можно найти в адресе, начинается с ~

    Return
    ------
    int
        Номер страницы, которую надо проверять для обновления

        Если на сервере есть страницы с 1 по 10, но 11 ещё не вышла, то вернётся именно 11
    """
    # Ссылка на последнюю страницу есть на главной
    mainpage = _comic_main_page_link(comic_name)

    # Устанавливаем куку для обхода ограничения возраста
    req = urllib.request.Request(mainpage, headers={'Cookie': 'ageRestrict=100'})

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
    return last + 1

async def async_find_last(
    comic_name: str,
    async_session: aiohttp.ClientSession|None=None
) -> int:
    """Асинхронный поиск номера следующей за последней доступной страницы комикса на сервере

    Parameters
    ----------
    comic_name: str
        Короткое имя комикса
        Его можно найти в адресе, начинается с ~

    session: ClientSession | None
        Сессия для проведения асинхронных запросов
        Если не передана, то будет производиться обычный поиск

    Return
    ------
    int
        Номер страницы, которую надо проверять для обновления

        Если на сервере есть страницы с 1 по 10, но 11 ещё не вышла, то вернётся именно 11
    """
    # Без сессии используем обычный запрос
    if async_session:
        _request = async_session.request
    else:
        _request = aiohttp.request

    # Ссылка на последнюю страницу есть на главной
    mainpage = _comic_main_page_link(comic_name)

    # Устанавливаем куку для обхода ограничения возраста
    headers = {'Cookie': 'ageRestrict=100'}

    # На самой странице ищем ссылку, указывающую на чтение с конца
    async with _request(
        "GET",
        mainpage,
        headers = headers
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

def download_comic_page(
    comic_name: str,
    page: int,
    is_write_description: bool = True,
    is_write_img_description: bool = True,
    folder: str|os.PathLike = '.'
) -> int|None:
    """Скачивание страницы комикса

    Parameters
    ----------
    comic_name: str
        Короткое имя комикса
        Его можно найти в адресе, начинается с ~

    page: int | str
        Номер скачиваемой страницы

    is_write_description: bool
        Записать ли описание в файл описания

    is_write_img_description: bool
        Записать ли всплывающий текст на изображении в файл описания

    folder: str | PathLike
        Папка, в которую осуществляется скачивание

    Return
    ------
    int
        Номер страницы, которая только что успешно скачалась, либо

    None
        Маркер, что скачивание не удалось
    """
    # Минимальный кусок html-страницы, необходимый для парсинга
    htmlpage = _comic_get_content_page(comic_name, page)

    # Название страницы
    title = _comic_page_title(htmlpage)

    # Путь к скачанному файлу
    comic_filepath = os.path.join(
        folder,
        _comic_filename(page, title=title)
        )
    comic_filepath_description = os.path.join(
        folder,
        _comic_filename(page, title=title, ext=".txt")
    )

    # Перескачивать уже существующий файл не нужно
    if not _check_corrects_file(comic_filepath):
        # Ссылка на изображение
        img = _comic_file_link(htmlpage)
        # Скачивание
        urllib.request.urlretrieve(img, comic_filepath)

    # Перескачивать уже существующий файл описания не нужно
    if not _check_corrects_file(comic_filepath_description):
        # Описание при странице
        description = _comic_page_description(
            htmlpage,
            is_write_description=is_write_description,
            is_write_img_description=is_write_img_description
        )

        if description:
            with open(comic_filepath_description, "w", encoding="utf-8") as file:
                file.write(description)

    # В случае успеха вернём номер страницы, иначе None
    if _check_corrects_file(comic_filepath):
        return page
    return None

def downloadcomic(
    comic_name: str,
    first: int = 1,
    last: int|None = None,
    is_write_description: bool = True,
    is_write_img_description: bool = True,
    folder: str|os.PathLike = '.',
    use_async: bool = True
) -> int:
    """Скачивание заданных страниц комикса от first до last

    Parameters
    ----------
    comic_name: str
        Короткое имя комикса
        Его можно найти в адресе, начинается с ~

    first: int
        Номер первой страницы, которую ещё не скачивали

    last: int | None
        Номер последней страницы, до которой (не включительно) вести скачивание
        Если страниц существует меньше, то скачиваться будут страницы до последней существующей
        Если не указано, то скачиваться будут страницы до последней существующей

    is_write_description: bool
        Записывать ли описание в файл описания

    is_write_img_description: bool
        Записывать ли всплывающий текст на изображении в файл описания

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
                comic_name,
                first = first,
                last = last,
                is_write_description = is_write_description,
                is_write_img_description = is_write_img_description,
                folder = folder
            )
        )
        loop.close()
        return last_success

    # Обычное скачивание
    # Установка последней страницы при её отсутствии
    if not last:
        last = find_last(comic_name)
    else:
        last = min(last, find_last(comic_name))
    # Последовательно скачиваем страницы,
    # запоминаем, на какой странице необходимо начинать следующее скачивание
    last_success = first
    for num in range(first, last):
        if (
            (
                result := download_comic_page(
                    comic_name,
                    num,
                    is_write_description,
                    is_write_img_description,
                    folder
                )
            )
            and last_success == result
        ):
            last_success = result + 1
    return last_success

async def _async_download_comic_page(
    comic_name: str,
    page: int,
    is_write_description: bool = True,
    is_write_img_description: bool = True,
    folder: str|os.PathLike = '.',
    session: aiohttp.ClientSession|None = None
) -> int|None:
    """Асинхронное скачивание одной страницы комикса

    Parameters
    ----------
    comic_name: str
        Короткое имя комикса
        Его можно найти в адресе, начинается с ~

    page: int | str
        Номер скачиваемой страницы

    is_write_description: bool
        Записать ли описание в файл описания

    is_write_img_description: bool
        Записать ли всплывающий текст на изображении в файл описания

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
    # Минимальный кусок html-страницы, необходимый для парсинга
    htmlpage = await _async_comic_get_content_page(comic_name, page, async_session=session)

    # Без сессии скачиваем страницу обычным запросом
    if session:
        _request = session.request
    else:
        _request = aiohttp.request

    # Название страницы
    title = _comic_page_title(htmlpage)

    # Путь к скачанному файлу
    comic_filepath = os.path.join(
        folder,
        _comic_filename(page, title=title)
        )
    comic_filepath_description = os.path.join(
        folder,
        _comic_filename(page, title=title, ext=".txt")
    )

    # Перескачивать уже существующий файл не нужно
    if not _check_corrects_file(comic_filepath):
        # Ссылка на изображение
        img = _comic_file_link(htmlpage)
        # Скачивание
        async with _request("GET", img) as resp:
            async with aiofile.async_open(comic_filepath, 'wb') as file:
                await file.write(await resp.read())

    # Перескачивать уже существующий файл описания не нужно
    if not _check_corrects_file(comic_filepath_description):
        # Описание при странице
        description = _comic_page_description(
            htmlpage,
            is_write_description=is_write_description,
            is_write_img_description=is_write_img_description
        )

        if description:
            async with aiofile.async_open(
                comic_filepath_description,
                "w",
                encoding="utf-8"
            ) as file:
                await file.write(description)

    # В случае успеха вернём номер страницы, иначе None
    if _check_corrects_file(comic_filepath):
        return page
    return None

async def async_downloadcomic(
    comic_name: str,
    first: int = 1,
    last: int|None = None,
    is_write_description: bool = True,
    is_write_img_description: bool = True,
    folder: str|os.PathLike = '.'
) -> int:
    """Асинхронное скачивание заданных страниц комикса от first до last

    Parameters
    ----------
    comic_name: str
        Короткое имя комикса
        Его можно найти в адресе, начинается с ~

    first: int
        Номер первой страницы, которую ещё не скачивали

    last: int | None
        Номер последней страницы, до которой (не включительно) вести скачивание
        Если страниц существует меньше, то скачиваться будут страницы до последней существующей
        Если не указано, то скачиваться будут страницы до последней существующей

    is_write_description: bool
        Записывать ли описание в файл описания

    is_write_img_description: bool
        Записывать ли всплывающий текст на изображении в файл описания

    folder: str | PathLike
        Папка, в которую осуществляется скачивание

    Return
    ------
    int
        Номер первой недоступной страницы
        При следующей проверке в аргумент first надо поместить именно это значение

        Если на сервере есть страницы с 1 по 10, но 11 ещё не вышла, то вернётся именно 11
    """
    async with aiohttp.ClientSession() as session:
        # Установка последней страницы при её отсутствии
        if not last:
            last = await async_find_last(comic_name, async_session=session)
        else:
            last = min(last, await async_find_last(comic_name, async_session=session))

        # Скачивание
        # Создание списка задач
        tasks = [
            _async_download_comic_page(
                comic_name,
                page,
                is_write_description = is_write_description,
                is_write_img_description = is_write_img_description,
                folder = folder,
                session = session
            )
            for page in range(first, last)
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
    args, _ = arg_parser().parse_known_args()

    # Скачивание
    comic_short_name = args.comic.rsplit("/",1)[-1]
    r = downloadcomic(
        comic_short_name,
        first = args.first,
        last = args.last,
        is_write_description = args.desc,
        is_write_img_description = args.imgtitle,
        folder = args.folder,
        use_async = not args.no_async
    )
    # Возвращаемое значение — номер новой нескачанной страницы
    sys.exit(r)
