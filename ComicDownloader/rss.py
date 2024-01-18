import sqlite3
from contextlib import closing as dbclosing
import subprocess as sp
from win10toast import ToastNotifier
import urllib.error

# Обслуживание БД
def service_db():
    with dbclosing(sqlite3.connect("rss.db")) as connection:
        with connection as cursor:
            cursor.execute('vacuum')
    print("БД rss.db успешно оптимизирована")

# Получить данные из БД
def get_db():
    with dbclosing(sqlite3.connect("rss.db")) as connection:
        with connection as cursor:
            res = cursor.execute('select * from rss_list')
            res = res.fetchall()
    return res

def set_last_num(rss_id,last_num):
    with dbclosing(sqlite3.connect("rss.db")) as connection:
        with connection as cursor:
            cursor.execute("""update rss_list
                                    set last_num=?, 
                                         last_chk=datetime('now'),
                                         last_upd=datetime('now')
                                    where id=?""",(last_num,rss_id))

def set_last_chk(rss_id):
    with dbclosing(sqlite3.connect("rss.db")) as connection:
        with connection as cursor:
            cursor.execute("""update rss_list
                                    set last_chk=datetime('now') 
                                    where id=?""",(rss_id))

if __name__ == '__main__':
    toaster = ToastNotifier()
    service_db()

    rss_list = get_db()
    procs=[]
    
    # Sequantial Art
    procs.append(sp.run(f'python SAdownload.py {rss_list[0][4]} -folder "{rss_list[0][3]}"'))
    print("Процесс SA добавлен")
    if procs[0].returncode > rss_list[0][4]:
        set_last_num(1,procs[0].returncode)
        toaster.show_toast("RSS",f"Обновление: {rss_list[0][1]}")
    else:
        set_last_chk("1")
    print("Процесс SA завершён")
    
    # Acomics
    for rss in rss_list[1:]:
        #print('python acomicsdownload.py '+str(rss[1])+' '+str(rss[3])+' -folder "'+rss[2]+'" -desc '+rss[6]+' -imgtitle '+rss[7])
        try:
            procs.append(sp.Popen(f'python acomicsdownload.py {rss[2]} {rss[4]} -folder "{rss[3]}" -desc {rss[7]} -imgtitle {rss[8]}'))
            print(f"Процесс {rss[1]} добавлен")
        except urllib.error.URLError as e:
            print(e)
        #print(rss)

    for rss in rss_list[1:]:
        procs[rss[0]-1].wait()
        if procs[rss[0]-1].returncode > rss[4]:
            set_last_num(rss[0],procs[rss[0]-1].returncode)
            toaster.show_toast("RSS",f"Обновление: {rss[1]}")
        else:
            set_last_chk(f"{rss[0]}")
        print(f"Процесс {rss[1]} завершён")
