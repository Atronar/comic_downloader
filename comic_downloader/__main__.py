import subprocess as sp
import urllib.error

from win10toast import ToastNotifier

from rss import service_db, get_db, set_last_chk, set_last_num

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
            desc = ' -desc' if str(rss[7])=='True' else ''
            imgtitle = ' -imgtitle' if str(rss[8])=='True' else ''
            procs.append(sp.Popen(f'python acomicsdownload.py {rss[2]} {rss[4]} -folder "{rss[3]}"{desc}{imgtitle}'))
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

