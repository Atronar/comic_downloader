import unittest
import asyncio
from comic_downloader import SAdownload
import os

class Test_test_SA(unittest.TestCase):
    def test_find_last(self):
        a = SAdownload.find_last()
        print(a)
        last_post = 1244
        self.assertGreaterEqual(a, last_post)
        self.assertEqual(a, last_post, "Обнови last_post в тесте на актуальный")

    def test_simple_functions(self):
        a = SAdownload._comic_file_link(47)
        print(a)
        self.assertEqual(a, "http://www.collectedcurios.com/SA_0047_small.jpg")

        a = SAdownload._comic_filename(47)
        print(a)
        self.assertEqual(a, "SA_0047_small.jpg")

    def test_download_single(self):
        page = 47
        filepath = os.path.join('TestResults', SAdownload._comic_filename(page))
        try:
            os.remove(filepath)
        except FileNotFoundError:
            pass
        a = SAdownload.download_comic_page(page, 'TestResults')
        self.assertTrue(os.path.exists(filepath))
        self.assertGreater(os.path.getsize(filepath), 8)

    def test_download(self):
        start_page = 147
        for page in range(start_page, start_page + 20):
            filepath = os.path.join('TestResults', SAdownload._comic_filename(page))
            try:
                os.remove(filepath)
            except FileNotFoundError:
                pass

        a = SAdownload.downloadcomic(start_page, start_page + 20, 'TestResults')
        print(a)
        self.assertEqual(a, start_page + 20)

        for page in range(start_page, start_page + 20):
            filepath = os.path.join('TestResults', SAdownload._comic_filename(page))
            self.assertTrue(os.path.exists(filepath))
            self.assertGreater(os.path.getsize(filepath), 8)

    def test_async_download(self):
        start_page = 147
        for page in range(start_page, start_page + 20):
            filepath = os.path.join('TestResults', SAdownload._comic_filename(page))
            try:
                os.remove(filepath)
            except FileNotFoundError:
                pass

        loop = asyncio.get_event_loop()
        a = loop.run_until_complete(SAdownload.async_downloadcomic(start_page, start_page + 20, 'TestResults'))
        print(a)
        loop.close()
        self.assertEqual(a, start_page + 20)

        for page in range(start_page, start_page + 20):
            filepath = os.path.join('TestResults', SAdownload._comic_filename(page))
            self.assertTrue(os.path.exists(filepath))
            self.assertGreater(os.path.getsize(filepath), 8)

if __name__ == '__main__':
    unittest.main()
