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

## Load Database
This may take a while depending on which embedding model you use.
```bash
cd model
python load_db.py
```

## Start Langgraph API
```bash
cd app
python main.py
```

## Start Webserver
```bash
cd web
npm install
npm run dev
```

# Scrapy Spider Setup Tutorial

This guide will help you set up a Python virtual environment, install the required packages, and run your Scrapy spider that extracts text from both HTML and PDF pages.

## Step 1: Create a Virtual Environment

Open your terminal and run the following command to create a virtual environment named `.venv`:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
scrapy crawl policy_spider -o ./data/results.json -s LOG_LEVEL=INFO
```

## Starting Neo4j Docker Container
```
docker run \
    --publish=7474:7474 --publish=7687:7687 \
    --volume=$HOME/neo4j/data:/data \
    neo4j
```