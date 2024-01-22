import unittest
from comic_downloader import rss

class Test_test_rss(unittest.TestCase):
    def test_get_db(self):
        a = rss.get_db()
        print(a)
        
    def test_get_row(self):
        a = rss.get_db()
        b = rss.RSSRow(a[0])
        print(b)
        
    def test_get_data(self):
        a = rss.get_db()
        b = rss.RSSData(a)
        print(b)

if __name__ == '__main__':
    unittest.main()
