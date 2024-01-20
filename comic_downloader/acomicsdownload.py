from bs4 import BeautifulSoup
import urllib.request as urllib
import argparse
import os

# Чтение аргументов командной строки
def arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('comic',help='Ссылка на главную страницу комикса на acomics',type=str)
    parser.add_argument('first',nargs='?',help='Первый номер, число',type=int,default=1)
    parser.add_argument('-last',nargs='?',help='Последний номер, число. Если больше возможного, то качается до последнего существующего.',type=int,default=False)
    parser.add_argument('-desc',nargs='?',help='Сохранять ли описания, автоматически True, если указан imgtitle, True/False',default=False,choices=['True','False'])
    parser.add_argument('-imgtitle',nargs='?',help='Сохранять ли title изображений в описаниях, True/False',type=bool,default=False,choices=[True,False])
    parser.add_argument('-folder',help='Директория сохранения',type=str,default='')
    return parser

def filenamefilter(value):
    for c in '\/:*?"<>|':
        value = value.replace(c,'.')
    return value

def writetxt(file,desc):
    for descr in desc:
        if descr.name in ['p','div','em','strong','span','h3','h2','h1']:
            writetxt(file,descr)
        elif descr.name == 'hr':
            file.write('-----\n')
        elif descr.name == 'br':
            file.write('\n')
        elif descr.name == 'a':
            writetxt(file,descr.contents)
            file.write(f" ({descr['href']})")
        elif descr.name == 'img':
            file.write(f"(# {descr['src']} #)")
        else:
            file.write(f"{descr}")

def writefile(mainpage,num,description,imgtitle,folder):
    htmlpage = BeautifulSoup(urllib.urlopen(f"{mainpage}/{num}").read(),"lxml")
    htmlpage_mainImage = htmlpage.find('img',id='mainImage').extract()
    img = f"https://acomics.ru{htmlpage_mainImage['src']}"
    if imgtitle:
        if 'title' in f"{htmlpage_mainImage}":
            imgtitle_text=htmlpage_mainImage['title']
        else:
            imgtitle = False
    title = htmlpage.find("span","title").contents[0]
    if title[-1]=='.':
        title=title[:-1]
    htmlpage_description = htmlpage.find("div","description")
    if htmlpage_description:
        htmlpage_description = htmlpage_description.extract()
    if description and htmlpage_description:
        desc = htmlpage_description.contents
    else:
        desc = False

    urllib.urlretrieve(img,os.path.join(folder, f"{num} - {filenamefilter(title)}.jpg"))
    if desc or imgtitle:
        with open(os.path.join(folder, f"{num} - {filenamefilter(title)}.txt"),"w",encoding="utf-8") as file:
            if imgtitle:
                file.write(imgtitle_text)
            if imgtitle and desc:
                file.write("\n\n-----\n\n")
            if desc:
                writetxt(file,desc)
            
def downloadacomic(mainpage,first=1,last=False,desc=False,imgtitle=False,folder=''):
    last_ = int(BeautifulSoup(urllib.urlopen(mainpage).read(),"lxml").find('a','read2')['href'].split('/')[-1])
    if last and last_+1>last:
        last_=last-1
    if imgtitle:
        desc=imgtitle
    for num in range(first,last_+1):
        writefile(mainpage,num,desc,imgtitle,folder)
    return last_+1
    
if __name__ == '__main__':
    # Берём аргументы запуска
    args = arg_parser().parse_args()

    if args.desc=='True':
        desc=True
    else:
        desc=False
    if args.imgtitle=='True':
        imgtitle=True
    else:
        imgtitle=False
    r = downloadacomic(args.comic,args.first,args.last,desc,imgtitle,args.folder)
    exit(r)
