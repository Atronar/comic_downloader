from pathlib import Path
import shutil
import unittest
import asyncio
from comic_downloader.modules import mangalib
import os

class Test_test_mangalib(unittest.TestCase):
    def test_find_last(self):
        comic_name = "kaifuku-jutsushi-no-yarinaoshi"
        folder = os.path.join('TestResults', comic_name)
        page_downloader = mangalib.Downloader(comic_name=comic_name, folder=folder, use_async=False)
        a = page_downloader.find_last()
        print(a)
        last_post = (59, 1, 1)
        self.assertGreaterEqual(a, last_post)
        self.assertEqual(a, last_post, "Обнови last_post в тесте на актуальный")

    def test_async_find_last(self):
        comic_name = "kaifuku-jutsushi-no-yarinaoshi"
        folder = os.path.join('TestResults', comic_name)
        page_downloader = mangalib.Downloader(comic_name=comic_name, folder=folder)
        a = asyncio.run(page_downloader.async_find_last())
        print(a)
        last_post = (59, 1, 1)
        self.assertGreaterEqual(a, last_post)
        self.assertEqual(a, last_post, "Обнови last_post в тесте на актуальный")

    def test_simple_functions(self):
        comic_name = "sousou-no-frieren"
        page = 3
        volume = 2
        chapter = 8
        folder = os.path.join('TestResults', comic_name)
        page_downloader = mangalib.PageDownloader(
            page=page,
            comic_name=comic_name,
            volume=volume,
            chapter=chapter,
            folder=folder,
            is_write_img_description=True,
            is_write_description=True
        )
        data = page_downloader.data

        a = page_downloader._comic_file_link()
        print(a)
        self.assertEqual(a, "https://img33.imgslib.link//manga/sousou-no-frieren/chapters/714063/03_Re5p.png")

        a = page_downloader.chapter_title
        print(a)
        self.assertEqual(a, "Сотая доля")
        
        a = page_downloader._comic_filename()
        #print(a)
        self.assertEqual(a, "0003.jpg")

    def test_download_single(self):
        comic_name = "sousou-no-frieren"
        page = 1
        volume = 1
        chapter = 1
        folder = os.path.join('TestResults', comic_name)
        page_downloader = mangalib.PageDownloader(
            page=page,
            comic_name=comic_name,
            volume=volume,
            chapter=chapter,
            folder=folder,
            is_write_img_description=True,
            is_write_description=True
        )
        shutil.rmtree(folder, ignore_errors=True)
        os.makedirs(folder, exist_ok=True)
        
        ext = os.path.splitext(page_downloader._comic_file_link())[-1] or ".jpg"
        filepath = os.path.join(folder, f"{page_downloader.chapter} - {page_downloader.chapter_title}", page_downloader._comic_filename(ext=ext))
        try:
            os.remove(filepath)
        except FileNotFoundError:
            pass
        a = page_downloader.download_comic_page()
        self.assertTrue(os.path.exists(filepath))
        self.assertGreater(os.path.getsize(filepath), 8)

    def test_async_download_single(self):
        comic_name = "sousou-no-frieren"
        page = 1
        volume = 1
        chapter = 1
        folder = os.path.join('TestResults', comic_name)
        page_downloader = mangalib.PageDownloader(
            page,
            comic_name=comic_name,
            volume=volume,
            chapter=chapter,
            folder=folder,
            is_write_img_description=True,
            is_write_description=True
        )
        shutil.rmtree(folder, ignore_errors=True)
        os.makedirs(folder, exist_ok=True)
        
        ext = os.path.splitext(page_downloader._comic_file_link())[-1] or ".jpg"
        filepath = os.path.join(folder, f"{page_downloader.chapter} - {page_downloader.chapter_title}", page_downloader._comic_filename(ext=ext))
        try:
            os.remove(filepath)
        except FileNotFoundError:
            pass
        a = asyncio.run(page_downloader.async_download_comic_page())
        self.assertTrue(os.path.exists(filepath))
        self.assertGreater(os.path.getsize(filepath), 8)

    def test_download(self):
        comic_name = "kaifuku-jutsushi-no-yarinaoshi"
        start_page = 47
        folder = os.path.join('TestResults', comic_name)
        page_downloader = mangalib.Downloader(
            comic_name=comic_name,
            first=start_page,
            last=start_page + 3,
            folder=folder,
            is_write_img_description=True,
            is_write_description=True,
            use_async=False
        )
        shutil.rmtree(folder, ignore_errors=True)
        os.makedirs(folder, exist_ok=True)

        a = page_downloader.downloadcomic()
        print(a)
        self.assertEqual(a, start_page + 3)

        for file in os.scandir(folder):
            if file.is_file():
                self.assertGreater(file.stat().st_size, 8)
        self.assertEqual(len(list(Path(folder).glob("*/"))), 6)
        self.assertEqual(len(list(Path(folder).rglob("*.jpg"))), 88)

    def test_async_download(self):
        comic_name = "kaifuku-jutsushi-no-yarinaoshi"
        start_page = 47
        folder = os.path.join('TestResults', comic_name)
        page_downloader = mangalib.Downloader(
            comic_name=comic_name,
            first=start_page,
            last=start_page + 3,
            folder=folder,
            is_write_img_description=True,
            is_write_description=True
        )
        shutil.rmtree(folder, ignore_errors=True)
        os.makedirs(folder, exist_ok=True)

        loop = asyncio.get_event_loop()
        a = loop.run_until_complete(page_downloader.async_downloadcomic())
        print(a)
        loop.close()
        self.assertEqual(a, start_page + 3)

        for file in os.scandir(folder):
            if file.is_file():
                self.assertGreater(file.stat().st_size, 8)
        self.assertEqual(len(list(Path(folder).glob("*/"))), 6)
        self.assertEqual(len(list(Path(folder).rglob("*.jpg"))), 88)

if __name__ == '__main__':
    unittest.main()
