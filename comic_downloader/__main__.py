import subprocess as sp
import urllib.error
import sys

from win10toast import ToastNotifier

import rss

def get_result(out: bytes, err: bytes) -> int|float:
    if err:
        write_log(err)
        print(err)
        return -1
    try:
        if out.strip().isdigit():
            return int(out)
        return float(out)
    except ValueError:
        write_log(out)
        print(err)
        return -1

def write_log(log: bytes, file: str='.log'):
    with open(file, 'ab') as f:
        f.write(log)

def main():
    toaster = ToastNotifier()
    db = rss.RSSDB(rss.DB_NAME)
    db.service_db()

    rss_list = db.get_db()
    procs: dict[int, sp.Popen] = {}

    # Добавление задач
    for rss_item in rss_list:
        if rss_item.ended:
            # Завершённые комиксы пропускаем
            continue
        try:
            procs[rss_item.id] = (
                sp.Popen(
                    f'python "{rss_item.exec_module_path}" "{rss_item.url}" {rss_item.last_num} '
                    f'-folder "{rss_item.dir}"'
                    f'{" -desc" if rss_item.desc else ""}'
                    f'{" -imgtitle" if rss_item.imgtitle else ""}'
                    f'{" -no-async" if "-no-async" in sys.argv else ""}',
                    stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.PIPE
                )
            )
            print(f"{rss_item.name} добавлен")
        except urllib.error.URLError as err:
            print(err)
            raise err

    # Ожидание ответов
    for rss_item in rss_list:
        if rss_item.ended:
            # Завершённые комиксы пропускаем
            continue
        print(f"Скачивание {rss_item.name}")
        procs[rss_item.id].wait()
        new_last_num = get_result(*(procs[rss_item.id].communicate()))
        if new_last_num - rss_item.last_num > 0.001:
            db.set_last_num(rss_item.id, new_last_num)
            toaster.show_toast(
                "RSS",
                f"Обновление: {rss_item.name}\n"
                f"Добавлена {new_last_num-1} страница"
            )
        else:
            db.set_last_chk(rss_item.id)
        print(f"Скачивание {rss_item.name} завершено")

if __name__ == '__main__':
    main()
