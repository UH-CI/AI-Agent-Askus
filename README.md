# AI-Agent-Askus

## Conda Environment
```bash
conda env create --name ai-agent-askus --file environment.yml
```

## Run Web Scraper
```bash
cd web-scraper
scrapy crawl manoa -O data/urls.json
```

## LLM
Qwen/Qwen2-72B-Instruct

## Embedding Model
infgrad/stella_en_1.5B_v5/2_Dense_1024

## Manoa News
https://manoa.hawaii.edu/news/archive.php

## TODO
FAQ Database
General Database
Live Data