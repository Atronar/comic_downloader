import aiohttp
import asyncio
import urllib.request
import os
import argparse

# Чтение аргументов командной строки
def argParser():
    parser = argparse.ArgumentParser()
    parser.add_argument('first',nargs='?',help='Первый номер, число',type=int,default=1)
    parser.add_argument('-last',help='Последний номер, число. Если больше возможного, то качается до последнего существующего.',type=int,default=None)
    parser.add_argument('-folder',help='Директория сохранения',type=str,default='.')
    parser.add_argument('-no-async',help='Отключение быстрого (асинхронного) скачивания',action='store_true')
    return parser

def _comic_file_link(page):
    return f"http://www.collectedcurios.com/SA_{page:0>4}_small.jpg"

def _comic_filename(page):
    file_link = _comic_file_link(page)
    return file_link.rsplit("/",1)[-1]

def findLast(i=1, force_add_mode=False):
    if not force_add_mode or i < 500:
        return _findLast_mul(i)
    return _findLast_add(i)
                
def _findLast_mul(i=1):
    min_ = i
    max_ = i
    step = 1
    find_max = True

    def find_max_handler():
        nonlocal min_, i, step, max_
        min_ = i 
        i += step
        step *= 2
        max_ = i
        
    def set_min_handler():
        nonlocal min_, i, max_
        min_ = i 
        i = (min_ + max_)//2
        
    def set_max_handler():
        nonlocal min_, i, max_
        max_ = i
        i = (min_ + max_)//2
            
    while True:
        try:
            res = _findlast_check(i)
            if res.getcode()==200:
                if find_max:
                    find_max_handler()
                elif i - min_ > 0:
                    set_min_handler()
                else:
                    return i+1
        except urllib.error.HTTPError as e:
            if e.code==404:
                if find_max:
                    find_max = False
                    set_max_handler()
                elif i - min_ > 0:
                    set_max_handler()
                else:
                    return i
                
def _findLast_add(i=1):
    while True:
        try:
            res = _findlast_check(i)
            if res.getcode()==200:
                i+=1
        except urllib.error.HTTPError as e:
            if e.code==404:
                return i

def _findlast_check(i):
    res = urllib.request.urlopen(_comic_file_link(i))
    return res

def download_comic_page(page: int, folder: str|os.PathLike='.') -> int|None:
    comic_filepath = os.path.join(folder, _comic_filename(page))
    if not os.path.exists(comic_filepath):
        urllib.request.urlretrieve(
            _comic_file_link(page),
            comic_filepath
        )
    if os.path.exists(comic_filepath) and os.path.getsize(comic_filepath)>8:
        return page
    return None

def downloadcomic(first: int=1, last: int|None=None, folder: str|os.PathLike='.', use_async: bool=True):
    if use_async:
        loop = asyncio.get_event_loop()
        last_success = loop.run_until_complete(async_downloadcomic(first=first, last=last, folder=folder))
        loop.close()
        return last_success

    if not last:
        last = findLast(first)
    last_success = first
    for i in range(first, last):
        if (result := download_comic_page(i, folder=folder)) and last_success==result:
            last_success = result+1
    return last_success

async def _async_download_comic_page(session: aiohttp.ClientSession, page: int, folder: str|os.PathLike='.') -> int|None:
    comic_filepath = os.path.join(folder, _comic_filename(page))
    if not os.path.exists(comic_filepath):
        async with session.get(_comic_file_link(page)) as resp:
            with open(comic_filepath, 'wb') as f:
                f.write(await resp.read())
    if os.path.exists(comic_filepath) and os.path.getsize(comic_filepath)>8:
        return page
    return None

async def async_downloadcomic(first: int=1, last: int|None=None, folder: str|os.PathLike='.'):
    # Если последняя страница не указана, то узнаём её, собственно, номер
    if not last:
        last = findLast(first)
        
    # Скачивание
    async with aiohttp.ClientSession() as session:
        # Создание списка задач
        tasks = [_async_download_comic_page(session, i, folder) for i in range(first, last)]
        # Запуск задач
        results = await asyncio.gather(*tasks)
        # Чистка результатов
        results: list[int] = sorted(filter(bool, results))
        
    # Возврат следующей к скачиванию страницы
    if last-first==len(results):
        # Длина списка результатов совпадает с количеством запрошенных страниц
        return max(results)+1
    # Результатов меньше запрошенного, вероятно есть нескачанное
    # Ищем первую пропущенную страницу и возвращаем её 
    last_success = first
    for i in results:
        if last_success==i:
            last_success += 1
        else:
            return last_success
    return last_success

if __name__ == '__main__':
    # Берём аргументы запуска
    args = argParser().parse_args()

    r = downloadcomic(
        first = args.first,
        last = args.last,
        folder = args.folder,
        use_async = not args.no_async
    )
    exit(r);
