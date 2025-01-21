# AI-Agent-Askus

<img width="2032" alt="Screenshot 2024-11-15 at 7 32 59 AM" src="https://github.com/user-attachments/assets/fe4ebd50-dbcb-4de6-9124-c3d11d778f26">

![66f78880-7e9a-4407-b691-83cede70a444_480](https://github.com/user-attachments/assets/c4e614a8-78e7-463e-b4e1-403980022ad2)


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

## Starting Neo4j Docker Container
```
docker run \
    --publish=7474:7474 --publish=7687:7687 \
    --volume=$HOME/neo4j/data:/data \
    neo4j
```