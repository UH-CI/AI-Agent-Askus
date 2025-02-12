import scrapy
from scrapy.crawler import CrawlerProcess
from bs4 import BeautifulSoup
import html2text
from io import BytesIO
from pdfminer.high_level import extract_text
import logging

# Set pdfminer logger to WARNING to suppress debug clutter
logging.getLogger("pdfminer").setLevel(logging.WARNING)

class PolicySpider(scrapy.Spider):
    name = "policy_spider"
    start_urls = [
        "https://www.hawaii.edu/policy/index.php?action=viewPolicyText&policyTextName=title"
    ]

    def __init__(self, *args, **kwargs):
        super(PolicySpider, self).__init__(*args, **kwargs)
        # Set up html2text instance to convert HTML to text.
        self.h = html2text.HTML2Text()
        self.h.ignore_links = True

    def extract_text(self, html):
        """
        Extract text from HTML using BeautifulSoup.
        This version looks for an element with id="content-table".
        """
        soup = BeautifulSoup(html, "lxml")
        content_table = soup.find(id="content-table")
        if not content_table:
            return ""
        return self.h.handle(str(content_table))

    def parse(self, response):
        """
        Parse the main page to extract policy links.
        The links can be found under <td> -> <ul> -> <li> elements.
        """
        links = response.xpath("//td//ul/li//a/@href").getall()
        for url in links:
            absolute_url = response.urljoin(url)
            self.logger.info("Following policy link: %s", absolute_url)
            yield scrapy.Request(absolute_url, callback=self.parse_policy)

    def parse_policy(self, response):
        """
        Handles policy page responses.
        Checks for PDF meta refresh and direct PDF content,
        otherwise falls back to assuming it's an HTML page.
        """
        # Look for meta refresh that might point to a PDF.
        meta_refresh = response.xpath(
            '//meta[@http-equiv="refresh"]/@content'
        ).get()
        if meta_refresh and "URL=" in meta_refresh:
            url_part = meta_refresh.split("URL=")[-1].strip()
            pdf_url = response.urljoin(url_part)
            self.logger.info("Meta refresh detected a PDF at: %s", pdf_url)
            yield scrapy.Request(
                pdf_url,
                callback=self.parse_pdf,
                meta={"handle_httpstatus_list": [302]},
            )
            return

        # Check if the content type indicates PDF content.
        content_type = response.headers.get("Content-Type", b"").decode("utf-8")
        if "application/pdf" in content_type:
            self.logger.info("Direct PDF content detected at: %s", response.url)
            yield from self.parse_pdf(response)
            return

        # Otherwise, process as an HTML policy page.
        yield self.parse_html(response)

    def parse_pdf(self, response):
        """
        Processes PDF responses. Follows a 302 redirect if needed,
        extracts text from PDF using pdfminer, and yields the item.
        """
        if response.status == 302:
            location = response.headers.get("Location")
            if location:
                pdf_url = response.urljoin(location.decode("utf-8"))
                self.logger.info("302 redirect found. Following PDF URL: %s", pdf_url)
                yield scrapy.Request(pdf_url, callback=self.parse_pdf)
            else:
                self.logger.error(
                    "302 response received with no Location header at: %s",
                    response.url,
                )
            return

        try:
            pdf_text = extract_text(BytesIO(response.body))
        except Exception as e:
            self.logger.error("Error extracting text from PDF: %s", e)
            pdf_text = ""
        yield {"url": response.url, "extracted": pdf_text}

    def parse_html(self, response):
        """
        Processes HTML policy pages using the extract_text function.
        """
        extracted = self.extract_text(response.text)
        return {"url": response.url, "extracted": extracted}


if __name__ == "__main__":
    process = CrawlerProcess(settings={
        "ROBOTSTXT_OBEY": False,
        "LOG_LEVEL": "INFO",
        "FEED_FORMAT": "json",
        "FEED_URI": "policies.json",
    })
    process.crawl(PolicySpider)
    process.start()
