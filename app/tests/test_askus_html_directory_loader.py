import unittest
from dotenv import load_dotenv
from loaders.html import HtmlDirectoryLoader


class TestAskUsHtmlDirectoryLoader(unittest.TestCase):
    def setUp(self):
        load_dotenv(override=True)
    
    def test_html_loader(self):
        print("Testing AskUs HTML Directory Loader")
        loader = HtmlDirectoryLoader("tests/data/html")
        self.assertEqual(len(loader.load()), 9)

if __name__ == "__main__":
    unittest.main()