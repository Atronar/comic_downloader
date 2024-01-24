from pathlib import Path
import shutil
from typing import Iterable
import unittest
import asyncio
from comic_downloader import acomicsdownload
import os

class Test_test_AC(unittest.TestCase):
    def test_find_last(self):
        page_downloader = acomicsdownload.PageDownloader(comic_name="~romac")
        a = page_downloader.find_last()
        print(a)
        last_post = 121
        self.assertGreaterEqual(a, last_post)
        self.assertEqual(a, last_post, "Обнови last_post в тесте на актуальный")

    def test_async_find_last(self):
        page_downloader = acomicsdownload.PageDownloader(comic_name="~romac")
        a = asyncio.run(page_downloader.async_find_last())
        print(a)
        last_post = 121
        self.assertGreaterEqual(a, last_post)
        self.assertEqual(a, last_post, "Обнови last_post в тесте на актуальный")

    def test_simple_functions(self):
        comic_name = "~romac"
        page_downloader = acomicsdownload.PageDownloader(47, comic_name=comic_name)
        htmlpage = page_downloader._comic_get_content_page()

        a = page_downloader._comic_file_link
        print(a)
        self.assertEqual(a, "https://acomics.ru/upload/!c/alexiuss/romac/000047-1uxwo4fk9t.gif")

        title = page_downloader._comic_page_title
        a = page_downloader._comic_filename()
        #print(a)
        self.assertEqual(a, "47 - [ Концептология ] ： Стиральния.jpg")

    def test_download_single(self):
        comic_name = "~romac"
        page = 2
        folder = os.path.join('TestResults', comic_name)
        page_downloader = acomicsdownload.PageDownloader(
            page,
            comic_name=comic_name,
            folder=folder,
            is_write_img_description=True,
            is_write_description=True
        )
        shutil.rmtree(folder, ignore_errors=True)
        os.makedirs(folder)

        filepath = os.path.join(folder, page_downloader._comic_filename())
        filepath_desc = os.path.join(folder, page_downloader._comic_filename(ext=".txt"))
        try:
            os.remove(filepath)
            os.remove(filepath_desc)
        except FileNotFoundError:
            pass
        a = page_downloader.download_comic_page()
        self.assertTrue(os.path.exists(filepath))
        self.assertGreater(os.path.getsize(filepath), 8)
        self.assertTrue(os.path.exists(filepath_desc))
        self.assertGreater(os.path.getsize(filepath_desc), 8)

    def test_async_download_single(self):
        comic_name = "~romac"
        page = 2
        folder = os.path.join('TestResults', comic_name)
        page_downloader = acomicsdownload.PageDownloader(
            page,
            comic_name=comic_name,
            folder=folder,
            is_write_img_description=True,
            is_write_description=True
        )
        shutil.rmtree(folder, ignore_errors=True)
        os.makedirs(folder)

        filepath = os.path.join(folder, page_downloader._comic_filename())
        filepath_desc = os.path.join(folder, page_downloader._comic_filename(ext=".txt"))
        try:
            os.remove(filepath)
            os.remove(filepath_desc)
        except FileNotFoundError:
            pass
        a = asyncio.run(page_downloader.async_download_comic_page())
        self.assertTrue(os.path.exists(filepath))
        self.assertGreater(os.path.getsize(filepath), 8)
        self.assertTrue(os.path.exists(filepath_desc))
        self.assertGreater(os.path.getsize(filepath_desc), 8)

    def test_download(self):
        comic_name = "~the-Last-Demons-of-Tolochin"
        start_page = 47
        folder = os.path.join('TestResults', comic_name)
        page_downloader = acomicsdownload.Downloader(
            comic_name=comic_name,
            first=start_page,
            last=start_page + 20,
            folder=folder,
            is_write_img_description=True,
            is_write_description=True,
            use_async=False
        )
        shutil.rmtree(folder, ignore_errors=True)
        os.makedirs(folder)

        a = page_downloader.downloadcomic()
        print(a)
        self.assertEqual(a, start_page + 20)

        for file in os.scandir(folder):
            self.assertGreater(file.stat().st_size, 8)
        self.assertEqual(len(list(Path(folder).glob("*.jpg"))), 20)

    def test_async_download(self):
        comic_name = "~the-Last-Demons-of-Tolochin"
        start_page = 47
        folder = os.path.join('TestResults', comic_name)
        page_downloader = acomicsdownload.Downloader(
            comic_name=comic_name,
            first=start_page,
            last=start_page + 20,
            folder=folder,
            is_write_img_description=True,
            is_write_description=True
        )
        shutil.rmtree(folder, ignore_errors=True)
        os.makedirs(folder)

        loop = asyncio.get_event_loop()
        a = loop.run_until_complete(page_downloader.async_downloadcomic())
        print(a)
        loop.close()
        self.assertEqual(a, start_page + 20)

        for file in os.scandir(folder):
            self.assertGreater(file.stat().st_size, 8)
        self.assertEqual(len(list(Path(folder).glob("*.jpg"))), 20)

if __name__ == '__main__':
    unittest.main()
