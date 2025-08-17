import os
import base64
import io
import re
from openai import OpenAI
from neo4j import GraphDatabase
from PIL import Image
from dotenv import load_dotenv
from pathlib import Path

# --- Load Environment Variables ---
env_path = Path('.') / 'config' / '.env'
load_dotenv(dotenv_path=env_path)

# --- Configuration Dictionary ---
RAG_CONFIG = {
    "NEO4J_URI": os.getenv("NEO4J_URI"),
    "NEO4J_USER": os.getenv("NEO4J_USER"),
    "NEO4J_PASSWORD": os.getenv("NEO4J_PASSWORD"),
    "VLLM_API_URL": os.getenv("VLLM_API_URL"),
    "VLLM_MODEL": os.getenv("VLLM_MODEL"),
}

class RAGQueryClient:
    """
    Handles the entire Retrieve-Augment-Generate pipeline for DesignQA.
    """
    def __init__(self, config):
        self.config = config
        self.neo4j_driver = GraphDatabase.driver(
            config["NEO4J_URI"], auth=(config["NEO4J_USER"], config["NEO4J_PASSWORD"])
        )
        self.vllm_client = OpenAI(api_key="EMPTY", base_url=config["VLLM_API_URL"])
        print("✅ RAGQueryClient initialized successfully.")

    def _get_rule_from_kg(self, rule_id, question=""):
        """Fetches a rule's full text and title from the Neo4j KG."""
        if not rule_id:
            return "No rule specified."
        with self.neo4j_driver.session() as session:
            result = session.run(
                "MATCH (n:Rule {rule_id: $rule_id}) RETURN n.text AS text, n.title AS title",
                rule_id=rule_id
            )
            record = result.single()
            if record:
                title = record['title'] or ""
                text = record['text'] or ""
                # For 'retrieval' questions asking to "state exactly", return title and text.
                if "state exactly" in question:
                    return f"{title}\n{text}".strip() if title else text.strip()
                # For compliance tasks, provide full context with the rule number.
                return f"Rule {rule_id} ({title}):\n{text}".strip()
        return f"Rule {rule_id} was not found in the Knowledge Graph."

    def _get_rules_by_term(self, term):
        """Finds all rules containing a specific term for the 'Compilation' task."""
        if not term: return ""
        with self.neo4j_driver.session() as session:
            result = session.run(
                """
                MATCH (r:Rule)
                WHERE toLower(r.title) CONTAINS toLower($term) OR toLower(r.text) CONTAINS toLower($term)
                RETURN r.rule_id AS rule_id ORDER BY r.rule_id
                """,
                term=term
            )
            return ",".join([record["rule_id"] for record in result])

    def _encode_image_to_base64(self, image_path):
        """Encodes an image file to a base64 string."""
        with Image.open(image_path) as img:
            if img.mode != 'RGB': img = img.convert('RGB')
            buffered = io.BytesIO()
            img.save(buffered, format="JPEG")
            return base64.b64encode(buffered.getvalue()).decode('utf-8')

    def query_compliance(self, question, image_path, rule_id):
        """Orchestrates the full RAG pipeline for image-based tasks."""
        rule_text = self._get_rule_from_kg(rule_id, question) if rule_id else ""
        base64_image = self._encode_image_to_base64(image_path)
        
        few_shot_prompt = """
        Example of how to answer:
        Explanation: The image shows the car's wheelbase dimension is 1525 mm. This is equal to the minimum required wheelbase, therefore it complies.
        Answer: yes
        """
        
        prompt_text = f"Query: {question}\n"
        if "Rule" in rule_text: prompt_text += f"Rule Context: {rule_text}\n"
        #prompt_text += f"Follow the output format of this example:\n{few_shot_prompt}"

        try:
            response = self.vllm_client.chat.completions.create(
                model=self.config["VLLM_MODEL"],
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_text},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }],
                max_tokens=300, temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"An error occurred while contacting the VLLM server: {e}"

    def close(self):
        self.neo4j_driver.close()