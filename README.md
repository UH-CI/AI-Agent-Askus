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

## Config File
```yml
# Config for ITS RAG
embedding: "dunzhang/stella_en_1.5B_v5" # Hugging Face embedding model, additional libraries may need to be installed to use other models
llm: "gemma2:27b" # Ollama model https://ollama.com/search
```

## Load Database
This may take a while depending on which embedding model you use.
```bash
cd model
python reload_database.py
```

## Start Langgraph API
```bash
cd model
python agent_demo.py
```

## Start Webserver
```bash
cd web
npm install
npm run dev
```

## Run Web Scraper
```bash
cd web-scraper
scrapy crawl manoa -O data/urls.json
```