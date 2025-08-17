import os
import pandas as pd
import re
from tqdm import tqdm
from src.rag_query.rag_query_client import RAGQueryClient, RAG_CONFIG

# --- (Configuration and Helper functions remain the same) ---
DATASET_DIR = './design_qa/dataset'
OUTPUT_DIR = './predictions'

BENCHMARK_FILES = {
    'retrieval': 'rule_extraction/rule_retrieval_qa.csv',
    'compilation': 'rule_extraction/rule_compilation_qa.csv',
    'definition': 'rule_comprehension/rule_definition_qa/rule_definition_qa.csv',
    'presence': 'rule_comprehension/rule_presence_qa/rule_presence_qa.csv',
    'dimension': 'rule_compliance/rule_dimension_qa/context/rule_dimension_qa_context.csv',
    'functional_performance': 'rule_compliance/rule_functional_performance_qa/context/rule_functional_performance_qa.csv'
}

def parse_rule_from_question(question_text):
    match = re.search(r'rule\s+([A-Z0-9.-]+\.[A-Z0-9.-]+)', question_text)
    return match.group(1) if match else None

def parse_term_from_question(question_text):
    match = re.search(r'relevant to\s+`([^`]+)`', question_text)
    return match.group(1) if match else None

def run_full_benchmark():
    if not all(RAG_CONFIG.values()):
        print("❌ Error: Missing config in ./config/.env file!")
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    client = RAGQueryClient(RAG_CONFIG)
    print("🚀 Starting DesignQA Benchmark Evaluation...")

    for subset_name, filename in BENCHMARK_FILES.items():
        csv_path = os.path.join(DATASET_DIR, filename)
        print(f"\n--- Processing subset: {subset_name} ---")
        if not os.path.exists(csv_path):
            print(f"⚠️  Warning: File not found: {csv_path}")
            continue
            
        df = pd.read_csv(csv_path)
        predictions = []

        for index, row in tqdm(df.iterrows(), total=df.shape[0], desc=subset_name):
            question = row['question']
            prediction = ""

            if subset_name in ['retrieval', 'compilation']:
                if subset_name == 'retrieval':
                    rule_id = parse_rule_from_question(question)
                    prediction = client._get_rule_from_kg(rule_id, question)
                elif subset_name == 'compilation':
                    term = parse_term_from_question(question)
                    prediction = client._get_rules_by_term(term)
            else: 
                image_folder_name = filename.replace('.csv', '')
                image_path = os.path.join(DATASET_DIR, image_folder_name, row['image'])
                
                if not os.path.exists(image_path):
                    prediction = f"Error: Image not found at {image_path}"
                else:
                    rule_id = parse_rule_from_question(question)
                    prediction = client.query_compliance(question, image_path, rule_id)
            
            # --- THIS IS THE FIX ---
            # Ensure the prediction is always a string before adding it
            predictions.append(str(prediction))

        df['model_prediction'] = predictions
        output_path = os.path.join(OUTPUT_DIR, f'{subset_name}_predictions.csv')
        df.to_csv(output_path, index=False)
        print(f"✅ Predictions saved to {output_path}")

    client.close()
    print("\n🎉 Benchmark evaluation complete! You can now run the official evaluation script.")

if __name__ == "__main__":
    run_full_benchmark()