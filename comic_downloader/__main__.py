import subprocess as sp
import urllib.error

from win10toast import ToastNotifier

import rss

def main():
    toaster = ToastNotifier()
    db = rss.RSSDB(rss.DB_NAME)
    db.service_db()

    rss_list = db.get_db().raw
    procs=[]

    # Sequantial Art
    procs.append(sp.run(f'python SAdownload.py {rss_list[0][4]} -folder "{rss_list[0][3]}"'))
    print("Процесс SA добавлен")
    if procs[0].returncode > rss_list[0][4]:
        db.set_last_num(1, procs[0].returncode)
        toaster.show_toast("RSS", f"Обновление: {rss_list[0][1]}")
    else:
        db.set_last_chk(1)
    print("Процесс SA завершён")

    # Acomics
    for rss_item in rss_list[1:]:
        try:
            procs.append(
                sp.Popen(
                    f'python acomicsdownload.py {rss_item[2]} {rss_item[4]} '
                    f'-folder "{rss_item[3]}"'
                    f'{" -desc" if str(rss_item[7])=="True" else ""}'
                    f'{" -imgtitle" if str(rss_item[8])=="True" else ""}'
                )
            )
            print(f"Процесс {rss_item[1]} добавлен")
        except urllib.error.URLError as err:
            print(err)

    for rss_item in rss_list[1:]:
        procs[rss_item[0]-1].wait()
        if procs[rss_item[0]-1].returncode > rss_item[4]:
            db.set_last_num(rss_item[0], procs[rss_item[0]-1].returncode)
            toaster.show_toast("RSS", f"Обновление: {rss_item[1]}")
        else:
            db.set_last_chk(rss_item[0])
        print(f"Процесс {rss_item[1]} завершён")

if __name__ == '__main__':
    main()
