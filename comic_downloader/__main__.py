import subprocess as sp
import urllib.error

from win10toast import ToastNotifier

import rss

def main():
    toaster = ToastNotifier()
    db = rss.RSSDB(rss.DB_NAME)
    db.service_db()

    rss_list = db.get_db()
    procs = []

    procs_temp_len = len(procs)
    # Sequantial Art
    rss_item = rss_list[0]
    procs.append(sp.run(f'python SAdownload.py {rss_item.last_num} -folder "{rss_item.dir}"'))
    print("Процесс SA добавлен")
    if procs[0].returncode > rss_item.last_num:
        db.set_last_num(rss_item.id, procs[0].returncode)
        toaster.show_toast("RSS", f"Обновление: {rss_item.name}")
    else:
        db.set_last_chk(rss_item.id)
    print("Процесс SA завершён")

    procs_temp_len = len(procs)
    # Acomics
    for rss_item in rss_list[1:]:
        try:
            procs.append(
                sp.Popen(
                    f'python acomicsdownload.py {rss_item.url} {rss_item.last_num} '
                    f'-folder "{rss_item.dir}"'
                    f'{" -desc" if rss_item.desc else ""}'
                    f'{" -imgtitle" if rss_item.imgtitle else ""}'
                )
            )
            print(f"Процесс {rss_item.name} добавлен")
        except urllib.error.URLError as err:
            print(err)

    for rss_item in rss_list[1:]:
        procs[rss_item.id-procs_temp_len].wait()
        if procs[rss_item.id-procs_temp_len].returncode > rss_item.last_num:
            db.set_last_num(rss_item.id, procs[rss_item.id-procs_temp_len].returncode)
            toaster.show_toast("RSS", f"Обновление: {rss_item.name}")
        else:
            db.set_last_chk(rss_item.id)
        print(f"Процесс {rss_item.name} завершён")

if __name__ == '__main__':
    main()
