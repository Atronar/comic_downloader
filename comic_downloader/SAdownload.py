import urllib.request
import os
import argparse

# Чтение аргументов командной строки
def argParser():
    parser = argparse.ArgumentParser()
    parser.add_argument('first',nargs='?',help='Первый номер, число',type=int,default=1)
    parser.add_argument('-last',help='Последний номер, число. Если больше возможного, то качается до последнего существующего.',type=int,default=False)
    parser.add_argument('-folder',help='Директория сохранения',type=str,default='')
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

def download_comic_page(page,folder=''):
    comic_filepath = os.path.join(folder, _comic_filename(page))
    if not os.path.exists(comic_filepath):
        urllib.request.urlretrieve(
            _comic_file_link(page),
            comic_filepath
        )

def downloadcomic(first=1,last=False,folder=''):
    if last==False:
        last = findLast(first)
    for i in range(first, last):
        download_comic_page(i, folder=folder)
    return last

if __name__ == '__main__':
    # Берём аргументы запуска
    args = argParser().parse_args()

    r = downloadcomic(args.first,args.last,args.folder)
    exit(r);
