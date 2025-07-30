# RAG Evaluation Framework

This framework provides tools for extracting, chunking, and evaluating Wikipedia question-answering data for RAG (Retrieval Augmented Generation) evaluation.

## Components

1. **Data Processing Script (`process_data.py`)**: Extracts and chunks Wikipedia text from Natural Questions dataset
2. **Vector Database Creation Script (`create_vector_db.py`)**: Creates ChromaDB vector databases and evaluates retrieval performance

## Usage Instructions

### Step 1: Activate Environment

```bash
source activate house_finance_env
```

### Step 2: Process Data

Process the Natural Questions dataset to extract documents, chunk them, and extract questions:

```bash
python process_data.py \
  --jsonl_path v1.0_sample_nq-dev-sample.jsonl \
  --output_dir data \
  --chunk_size 1000 \
  --chunk_overlap 200
```

Optional parameters:
- `--keep_html`: Keep HTML in document text (default: remove HTML)

This will create the following files in the `data` directory:
- `data/chunks/nq_chunks_1000_200_clean.json`: Chunked documents
- `data/questions/nq_chunks_1000_200_clean_questions.json`: Questions with answers
- `data/nq_chunks_1000_200_clean_info.json`: Dataset information

### Step 3: Create Vector Database and Evaluate Retrieval

Create a ChromaDB vector database for the processed data and evaluate retrieval performance:

```bash
python create_vector_db.py \
  --data_dir data \
  --db_dir vectordb \
  --dataset_id nq_chunks_1000_200_clean \
  --k 2
```

This will:
1. Create a ChromaDB vector database in the `vectordb` directory
2. Evaluate retrieval performance with `k=2` (retrieving 2 documents per question)
3. Save evaluation results to `data/nq_chunks_1000_200_clean_evaluation_k2.json`

## Customizing Parameters

You can experiment with different parameters to optimize retrieval performance:

- **Chunk size**: Adjust `--chunk_size` to create larger or smaller chunks
- **Chunk overlap**: Adjust `--chunk_overlap` to increase or decrease overlap between chunks
- **Top K**: Adjust `--k` to retrieve more or fewer documents per question
- **HTML removal**: Use `--keep_html` to keep HTML in document text

## Evaluation Metrics

The evaluation results include:
- **Accuracy**: Percentage of questions where the gold document was retrieved
- **Retrieved chunks**: Top K chunks retrieved for each question
- **Gold answers**: HTML and clean text versions of gold standard answers

## Example Workflow

```bash
# Process data with different chunk sizes
python process_data.py --chunk_size 500 --chunk_overlap 100
python process_data.py --chunk_size 1000 --chunk_overlap 200
python process_data.py --chunk_size 2000 --chunk_overlap 400

# Evaluate with different k values
python create_vector_db.py --dataset_id nq_chunks_500_100_clean --k 1
python create_vector_db.py --dataset_id nq_chunks_500_100_clean --k 3
python create_vector_db.py --dataset_id nq_chunks_500_100_clean --k 5
```

## Note on Embeddings

The default embedding function uses the OpenAI text-embedding-ada-002 model. If you want to use a different embedding function, you'll need to modify the `embedding_function` in the `VectorDatabaseCreator` class in `create_vector_db.py`.
