import unittest
from comic_downloader import SAdownload

class Test_test_SA(unittest.TestCase):
    def test_find_last(self):
        a = SAdownload.findLast()
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

if __name__ == '__main__':
    unittest.main()
