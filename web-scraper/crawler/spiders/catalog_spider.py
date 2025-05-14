import scrapy

class CatalogSpider(scrapy.Spider):
    name = "catalog_spider"
    start_urls = ["https://manoa.hawaii.edu/catalog/?s=&post_type=courses"]

    def parse(self, response):
        for content in response.css("div.post-content"):
            # extract and split the full title
            full_title = content.css("h2.entry-title a::text").get(default="").strip()
            parts = full_title.split()
            subject = parts[0] if len(parts) > 0 else ""
            course_number = parts[1] if len(parts) > 1 else ""
            title = " ".join(parts[2:]) if len(parts) > 2 else ""

            # extract course description (including text in nested span tags)
            desc = " ".join(content.css("div.entry-content p *::text").getall()).strip()

            # collect gen-ed tags
            tags = [t.strip() for t in content.css("div.dtags a::text").getall()]

            # collect category names
            categories = [c.strip() for c in content.css("div.entry-meta span.categories a::text").getall()]

            metadata = " ".join(tags + categories)

            yield {
                "subject": subject,
                "course_number": course_number,
                "title": title,
                "desc": desc,
                "metadata": metadata
            }
