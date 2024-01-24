import unittest
from comic_downloader import rss

class Test_test_rss(unittest.TestCase):
    def test_get_db(self):
        a = rss.RSSDB(rss.DB_NAME).get_db()
        print(a)
        
    def test_get_row(self):
        a = rss.RSSDB(rss.DB_NAME).get_db()
        b = a[0]
        print(b)
        
    def test_get_data(self):
        a = rss.RSSDB(rss.DB_NAME).get_db()
        b = a.data
        print(b)
        
if __name__ == '__main__':
    unittest.main()
