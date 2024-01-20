"""Модуль скачивания комиксов с AComics
https://acomics.ru
"""

import argparse
import os
import sys
import urllib.request as urllib
from bs4 import BeautifulSoup

def arg_parser():
    """Парсер аргументов командной строки
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'comic',
        help='Ссылка на главную страницу комикса на acomics',
        type=str
    )
    parser.add_argument(
        'first',
        nargs='?',
        help='Первый номер, число',
        type=int,
        default=1
    )
    parser.add_argument(
        '-last',
        nargs='?',
        help=(
            'Последний номер, число.'
            'Если больше возможного, то качается до последнего существующего.'
        ),
        type=int,
        default=False
    )
    parser.add_argument(
        '-desc',
        nargs='?',
        help='Сохранять ли описания, автоматически True, если указан imgtitle, True/False',
        default=False,
        choices=['True', 'False']
    )
    parser.add_argument(
        '-imgtitle',
        nargs='?',
        help='Сохранять ли title изображений в описаниях, True/False',
        type=bool,
        default=False,
        choices=[True, False]
    )
    parser.add_argument(
        '-folder',
        help='Директория сохранения',
        type=str,
        default=''
    )
    return parser

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

def writetxt(file, desc):
    """Запись текстового описания в файл"""
    for descr in desc:
        if descr.name in ['p', 'div', 'em', 'strong', 'span', 'h3', 'h2', 'h1']:
            writetxt(file, descr)
        elif descr.name == 'hr':
            file.write('-----\n')
        elif descr.name == 'br':
            file.write('\n')
        elif descr.name == 'a':
            writetxt(file, descr.contents)
            file.write(f" ({descr['href']})")
        elif descr.name == 'img':
            file.write(f"(# {descr['src']} #)")
        else:
            file.write(f"{descr}")

def writefile(mainpage, num, description, imgtitle, folder):
    """Скачивание страницы комикса"""
    with urllib.urlopen(f"{mainpage}/{num}") as file:
        htmlpage = BeautifulSoup(file.read(), "lxml")
    htmlpage_mainImage = htmlpage.find('img', id='mainImage').extract()
    img = f"https://acomics.ru{htmlpage_mainImage['src']}"
    if imgtitle:
        if 'title' in f"{htmlpage_mainImage}":
            imgtitle_text=htmlpage_mainImage['title']
        else:
            imgtitle = False
    title = htmlpage.find("span", "title").contents[0]
    if title[-1] == '.':
        title=title[:-1]
    htmlpage_description = htmlpage.find("div", "description")
    if htmlpage_description:
        htmlpage_description = htmlpage_description.extract()
    if description and htmlpage_description:
        desc = htmlpage_description.contents
    else:
        desc = False

    urllib.urlretrieve(img, os.path.join(folder, f"{num} - {make_safe_filename(title)}.jpg"))
    if desc or imgtitle:
        with open(
            os.path.join(folder, f"{num} - {make_safe_filename(title)}.txt"),
            "w",
            encoding="utf-8"
        ) as file:
            if imgtitle:
                file.write(imgtitle_text)
            if imgtitle and desc:
                file.write("\n\n-----\n\n")
            if desc:
                writetxt(file, desc)

def downloadacomic(
    mainpage,
    first=1,
    last=False,
    desc=False,
    imgtitle=False,
    folder=''
):
    """Скачивание заданных страниц комикса от first до last

    Parameters
    ----------
    mainpage: 
        ...
        
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
    with urllib.urlopen(mainpage) as file:
        last_ = int(
            BeautifulSoup(
                file.read(),
                "lxml"
            ).find('a', 'read2')['href']
            .split('/')[-1]
        )
    if last and last_ + 1>last:
        last_=last-1
    if imgtitle:
        desc=imgtitle
    for num in range(first, last_ + 1):
        writefile(mainpage, num, desc, imgtitle, folder)
    return last_ + 1

if __name__ == '__main__':
    # Берём аргументы запуска
    args = arg_parser().parse_args()

    if args.desc == 'True':
        desc=True
    else:
        desc=False
    if args.imgtitle == 'True':
        imgtitle=True
    else:
        imgtitle=False
    # Скачивание
    r = downloadacomic(args.comic, args.first, args.last, desc, imgtitle, args.folder)
    # Возвращаемое значение — номер новой нескачанной страницы
    sys.exit(r)
