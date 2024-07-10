from typing import Any
import scrapy
from scrapy.linkextractors import LinkExtractor
from bs4 import BeautifulSoup
import html2text

class ManoaSpider(scrapy.Spider):
    name = "manoa"
    allow_domains = ("www.hawaii.edu",)
    link_extractor = LinkExtractor(allow_domains=allow_domains, canonicalize=True)
    start_urls = ["https://www.hawaii.edu/"]
    h = html2text.HTML2Text()

    def extract_text(self, html):
        soup = BeautifulSoup(html, 'lxml')
        main_tag = soup.find('main')

        if not main_tag:
            return ""

        return self.h.handle(str(main_tag))
    

    def parse(self, response):
        extracted_text = self.extract_text(response.body)
        if extracted_text:
            yield {"url": response.url, "extracted": extracted_text}

        for link in self.link_extractor.extract_links(response):
            yield scrapy.Request(link.url)