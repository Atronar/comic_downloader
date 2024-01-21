from pathlib import Path
import shutil
from typing import Iterable
import unittest
import asyncio
from comic_downloader import acomicsdownload
import os

class Test_test_AC(unittest.TestCase):
    def test_find_last(self):
        a = acomicsdownload.find_last("~romac")
        print(a)
        last_post = 121
        self.assertGreaterEqual(a, last_post)
        self.assertEqual(a, last_post, "Обнови last_post в тесте на актуальный")

    def test_download_single(self):
        page = 2
        title = "[ Введение ] - в котором Чарльз встречает самодержца пустоши"
        filepath = os.path.join('TestResults', acomicsdownload._comic_filename(page, title=title))
        filepath_desc = os.path.join('TestResults', acomicsdownload._comic_filename(page, title=title, ext=".txt"))
        try:
            os.remove(filepath)
            os.remove(filepath_desc)
        except FileNotFoundError:
            pass
        a = acomicsdownload.download_comic_page("~romac", page, folder='TestResults')
        self.assertTrue(os.path.exists(filepath))
        self.assertGreater(os.path.getsize(filepath), 8)
        self.assertTrue(os.path.exists(filepath_desc))
        self.assertGreater(os.path.getsize(filepath_desc), 8)

    def test_download(self):
        comic_name = "~romac"
        start_page = 47
        folder = os.path.join('TestResults', comic_name)
        shutil.rmtree(folder, ignore_errors=True)
        os.makedirs(folder)

        a = acomicsdownload.downloadcomic(comic_name, start_page, start_page + 20, folder=folder)
        print(a)
        self.assertEqual(a, start_page + 20)

        for file in os.scandir(folder):
            self.assertGreater(file.stat().st_size, 8)
        self.assertEqual(len(list(Path(folder).glob("*.jpg"))), 20)

    def test_async_download(self):
        comic_name = "~romac"
        start_page = 47
        folder = os.path.join('TestResults', comic_name)
        shutil.rmtree(folder, ignore_errors=True)
        os.makedirs(folder)

        loop = asyncio.get_event_loop()
        a = loop.run_until_complete(acomicsdownload.async_downloadcomic(comic_name, start_page, start_page + 20, folder=folder))
        print(a)
        loop.close()
        self.assertEqual(a, start_page + 20)
        
        for file in os.scandir(folder):
            self.assertGreater(file.stat().st_size, 8)
        self.assertEqual(len(list(Path(folder).glob("*.jpg"))), 20)

if __name__ == '__main__':
    unittest.main()
