import shutil
import unittest
import asyncio
from comic_downloader.modules import SAdownload
import os

class Test_test_SA(unittest.TestCase):
    def test_find_last(self):
        downloader = SAdownload.Downloader()
        a = downloader.find_last()
        print(a)
        last_post = 1245
        self.assertGreaterEqual(a, last_post)
        self.assertEqual(a, last_post, "Обнови last_post в тесте на актуальный")

    def test_simple_functions(self):
        downloader = SAdownload.PageDownloader(47)
        a = downloader._comic_file_link
        print(a)
        self.assertEqual(a, "https://www.collectedcurios.com/SA_0047_small.jpg")

        a = downloader._comic_filename
        print(a)
        self.assertEqual(a, "SA_0047_small.jpg")

    def test_download_single(self):
        comic_name = "SA"
        page = 47
        folder = os.path.join('TestResults', comic_name)
        shutil.rmtree(folder, ignore_errors=True)
        os.makedirs(folder)
        downloader = SAdownload.PageDownloader(page, folder=folder)
        filepath = os.path.join(folder, downloader._comic_filename)
        try:
            os.remove(filepath)
        except FileNotFoundError:
            pass
        a = downloader.download_comic_page()
        self.assertTrue(os.path.exists(filepath))
        self.assertGreater(os.path.getsize(filepath), 8)

    def test_download(self):
        comic_name = "SA"
        start_page = 147
        folder = os.path.join('TestResults', comic_name)
        shutil.rmtree(folder, ignore_errors=True)
        os.makedirs(folder)

        downloader = SAdownload.Downloader(first=start_page, last=start_page + 20, folder=folder, use_async=False)
        a = downloader.downloadcomic()
        print(a)
        self.assertEqual(a, start_page + 20)

        page_downloader = SAdownload.PageDownloader()
        for page in range(start_page, start_page + 20):
            page_downloader.page = page
            filepath = os.path.join(folder, page_downloader._comic_filename)
            self.assertTrue(os.path.exists(filepath))
            self.assertGreater(os.path.getsize(filepath), 8)

    def test_async_download(self):
        comic_name = "SA"
        start_page = 147
        folder = os.path.join('TestResults', comic_name)
        shutil.rmtree(folder, ignore_errors=True)
        os.makedirs(folder)

        loop = asyncio.get_event_loop()
        downloader = SAdownload.Downloader(first=start_page, last=start_page + 20, folder=folder)
        a = loop.run_until_complete(downloader.async_downloadcomic())
        print(a)
        loop.close()
        self.assertEqual(a, start_page + 20)

        page_downloader = SAdownload.PageDownloader()
        for page in range(start_page, start_page + 20):
            page_downloader.page = page
            filepath = os.path.join(folder, page_downloader._comic_filename)
            self.assertTrue(os.path.exists(filepath))
            self.assertGreater(os.path.getsize(filepath), 8)

if __name__ == '__main__':
    unittest.main()
