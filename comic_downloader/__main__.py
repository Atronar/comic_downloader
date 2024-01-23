import subprocess as sp
import urllib.error

from win10toast import ToastNotifier

import rss

def main():
    toaster = ToastNotifier()
    db = rss.RSSDB(rss.DB_NAME)
    db.service_db()

    rss_list = db.get_db()
    procs: dict[int, sp.Popen] = {}

    # Sequantial Art
    rss_item = rss_list[0]
    procs[rss_item.id] = (
        sp.Popen(
            f'python "{rss_item.exec_module_path}" "{rss_item.url}" {rss_item.last_num} '
            f'-folder "{rss_item.dir}"'
        )
    )
    print(f"Процесс {rss_item.name} добавлен")
    if procs[rss_item.id].returncode > rss_item.last_num:
        db.set_last_num(rss_item.id, procs[rss_item.id].returncode)
        toaster.show_toast("RSS", f"Обновление: {rss_item.name}")
    else:
        db.set_last_chk(rss_item.id)
    print(f"Процесс {rss_item.name} завершён")

    # Acomics
    for rss_item in rss_list[1:]:
        try:
            procs[rss_item.id] = (
                sp.Popen(
                    f'python "{rss_item.exec_module_path}" "{rss_item.url}" {rss_item.last_num} '
                    f'-folder "{rss_item.dir}"'
                    f'{" -desc" if rss_item.desc else ""}'
                    f'{" -imgtitle" if rss_item.imgtitle else ""}'
                )
            )
            print(f"Процесс {rss_item.name} добавлен")
        except urllib.error.URLError as err:
            print(err)
            raise(err)

    for rss_item in rss_list[1:]:
        procs[rss_item.id].wait()
        if procs[rss_item.id].returncode > rss_item.last_num:
            db.set_last_num(rss_item.id, procs[rss_item.id].returncode)
            toaster.show_toast("RSS", f"Обновление: {rss_item.name}")
        else:
            db.set_last_chk(rss_item.id)
        print(f"Процесс {rss_item.name} завершён")

if __name__ == '__main__':
    main()
