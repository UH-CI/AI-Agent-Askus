from html2text import HTML2Text

from manoa_agent.loaders.website_loader import WebLoader
from manoa_agent.parsers.html_parser import HTMLParser

h = HTML2Text()
parser = HTMLParser(h, ids=["content"])
loader = WebLoader(urls=["https://www.hawaii.edu/its/help-desk/"], html_parser=parser)

for doc in loader.lazy_load():
    print(doc)
