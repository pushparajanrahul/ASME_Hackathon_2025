# ASME_Hackathon_2025

Powerpoint Presentation [here](https://docs.google.com/presentation/d/1o9Y9cwQ8u98wjftxNFlAM0JQ7NkSDWjM/edit?usp=drive_link&ouid=107658843354389870397&rtpof=true&sd=true)!


# DesignQA Benchmark Solution: A Tuned RAG System for Engineering Documents

This repository contains a complete, end-to-end solution for the **DesignQA benchmark**, which tests a Vision-Language Model's ability to understand and reason about complex engineering documents. Our approach utilizes a custom **Tuned Retrieval-Augmented Generation (RAG)** pipeline that leverages a structured **Knowledge Graph (KG)** to provide precise context to a Vision-Language Model.

This system was developed to address the core challenges of the benchmark, specifically the need for accurate information retrieval from dense technical manuals and the multimodal analysis of text and engineering drawings.

---

## 🚀 Key Features

* **Knowledge Graph Backend**: The entire FSAE rulebook is ingested into a **Neo4j** graph database, creating a structured and queryable source of truth.
* **Precision Retrieval**: Instead of generic semantic search, our system uses precise **Cypher queries** to retrieve the exact rule required, eliminating retrieval errors.
* **Vision-Language Model (VLLM)**: We use the powerful **LLaVA** model, served with the high-performance `vLLM` inference engine on an NVIDIA A100 GPU, to analyze technical drawings and text.
* **Automated Evaluation**: The project includes a comprehensive script to run the full DesignQA benchmark, generating predictions for all 6 subsets and preparing them for the official evaluation script.
* **Modular & Scalable**: The code is organized into distinct modules for KG ingestion (`main.py`), RAG querying (`rag_query_client.py`), and evaluation (`run_benchmark.py`), making it easy to maintain and extend.



---

## 🏛️ Project Architecture

Our solution follows a robust, multi-stage architecture:

1.  **Extraction**: The `main.py` script parses the structured Excel rulebooks, enrich the hierarchical structure by categorizing the rules into a tree structure Level1 (rule number with 1 decimal) -> level2 (rule number with 2 decimal) -> Level3 (rule number with 3 decimal), preserving the semantic flow. It also ensures a pretty print including removing boiler plates, newline removal, hyperlinked rules as plain text, 
2.  **KG Ingestion**: The `main_graph.py` script then uses this structured Excel rulebooks, creating a hierarchical graph in Neo4j with `Rulebook` and `Rule` nodes.
3.  **VLLM Server**: A dedicated server hosts the LLaVA model using `vLLM`, providing a high-throughput API for multimodal inference.
4.  **RAG Pipeline**: The `run_benchmark.py` script orchestrates the evaluation by:
    * **Retrieving** factual data from the Neo4j KG (for Rule Extraction tasks).
    * **Augmenting** a prompt with retrieved rules, images, and contextual instructions.
    * **Generating** a final answer by querying the VLLM server.

---

## 📂 Project Structure

```
.
├── config/
│   └── .env                  # Environment variables (DB credentials, API URLs)
├── design_qa/
│   └── dataset/              # Original DesignQA benchmark datasets
├── eval/
│   ├── full_evaluation.py    # Official evaluation script
│   └── metrics/              # Evaluation metrics module
├── predictions/
│   └── ...                   # Output CSVs with model predictions will be saved here
├── src/
│   ├── graph/
│   │   └── kg_ingestion.py   # Neo4j uploader class
│   │── rag_query/
│   │    └── rag_query_client.py   # RAG pipeline logic class
│   └── parsing/
│        └── extract_rules_from_pdf.py   # parsing the PDF and extracting the rules
│        └── structred_excel_files.py   # Defining the structure maintainin the Semantic Flow
│
├── llava_template.jinja      # Chat template for the VLLM
├── main.py                   # Main script to run PF parsing and extraction maintaining Semantic Flow
├── main_graph.py             # Main script to run KG ingestion
└── run_benchmark.py          # Main script to run the full benchmark
```

---

## 💻 How to Run

### **1. Setup**

1.  Clone the repository.
2.  Create and activate a new Conda environment.
    ```bash
    conda create -n vllm_env python=3.10 -y
    conda activate vllm_env
    ```
3.  Install dependencies. First install PyTorch with CUDA support, then the rest.
    ```bash
    # Install PyTorch for CUDA 12.1+
    pip3 install torch torchvision torchaudio --index-url [https://download.pytorch.org/whl/cu121](https://download.pytorch.org/whl/cu121)

    # Install vLLM and other key packages
    pip install "vllm<0.8.0" xformers transformers neo4j pandas openpyxl "python-dotenv<2.0.0" tqdm sentence_transformers rouge nltk 
    ```
4.  Set up your credentials in `./config/.env`.

### **2. Build the Knowledge Graph**

Run the ingestion script once to populate your Neo4j database from the Excel files in `./structured_text/`.
```bash
python main.py
```

### **3. Run the Full Benchmark Evaluation**

This is a 3-step process using two terminals.

**Terminal 1: Start the VLLM Server**
```bash
python -m vllm.entrypoints.openai.api_server \
    --model llava-hf/llava-1.5-13b-hf \
    --host 0.0.0.0 \
    --download-dir /path/to/your/scratch/folder \
    --chat-template ./llava_template.jinja
```

**Terminal 2: Generate Predictions**
This script will run for a long time, creating the 6 prediction CSVs in the `./predictions/` folder.
```bash
python run_benchmark.py
```

**Terminal 2: Calculate Final Score**
After the benchmark runner is finished, execute the official evaluation script.
```bash
python eval/full_evaluation.py \
    --path_to_retrieval ./predictions/retrieval_predictions.csv \
    --path_to_compilation ./predictions/compilation_predictions.csv \
    --path_to_definition ./predictions/definition_predictions.csv \
    --path_to_presence ./predictions/presence_predictions.csv \
    --path_to_dimension ./predictions/dimension_predictions.csv \
    --path_to_functional_performance ./predictions/functional_performance_predictions.csv
```
This will generate the final `results.txt` file with your system's score.
