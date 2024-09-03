# AI-Agent-Askus

## Conda Environment
```bash
conda env create --name ai-agent-askus --file environment.yml
conda activate ai-agent-askus
```
## Conda Update Environment
```bash
conda env update --file environment.yml --prune
```

## Run Web Scraper
```bash
cd web-scraper
scrapy crawl manoa -O data/urls.json
```

## LLM
gemma2-9b

## Embedding Model
dunzhang/stella_en_400M_v5