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

def findLast(i=1):
    while True:
        try:
            num = f"{i:0>4}"
            res = urllib.request.urlopen(f"http://www.collectedcurios.com/SA_{num}_small.jpg")
            if res.getcode()==200:
                i+=1
        except urllib.error.HTTPError as e:
            if e.code==404:
                return i

def downloadcomic(first=1,last=False,folder=''):
    if last==False:
        last = findLast(first)
    for i in range(first, last):
        num = f"{i:0>4}"
        if not os.path.exists(os.path.join(folder, f"SA_{num}_small.jpg")):
            urllib.request.urlretrieve(f"http://www.collectedcurios.com/SA_{num}_small.jpg",os.path.join(folder, f"SA_{num}_small.jpg"))
    return last

if __name__ == '__main__':
    # Берём аргументы запуска
    args = argParser().parse_args()

    r = downloadcomic(args.first,args.last,args.folder)
    exit(r);
