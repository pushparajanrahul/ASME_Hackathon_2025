import os
import pandas as pd
from neo4j import GraphDatabase
from dotenv import load_dotenv
from pathlib import Path

# --- Load Environment Variables ---
# This setup assumes the script is initiated from the project root (e.g., by main.py)
# It correctly finds the .env file in the ./config/ directory.
env_path = Path('.') / 'config' / '.env'
load_dotenv(dotenv_path=env_path)

# Export credentials so they can be imported and checked by main.py
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

class Neo4jUploader:
    """Handles connection and data uploading to Neo4j from Excel files."""
    def __init__(self, uri, user, password):
        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            self.driver.verify_connectivity()
            print(" Successfully connected to Neo4j.")
        except Exception as e:
            print(f" Failed to connect to Neo4j: {e}")
            raise

    def close(self):
        if self.driver:
            self.driver.close()

    def run_query(self, query, **params):
        """Runs a Cypher query against the database."""
        with self.driver.session() as session:
            session.run(query, **params)

    def upload_rulebook_from_excel(self, file_path):
        """
        Processes a single Excel file and uploads its sheets (Level1, 2, 3) to Neo4j.
        """
        try:
            # --- 1. Parse Rulebook Name from Filename ---
            filename = os.path.basename(file_path)
            # Example: "AD - ADMINISTRATIVE REGULATION.xlsx" -> "ADMINISTRATIVE REGULATION"
            rulebook_name = filename.split(' - ')[1].replace('.xlsx', '')
            print(f"\nProcessing rulebook: '{rulebook_name}'...")

            # --- 2. Create the Root Rulebook Node ---
            self.run_query("MERGE (rb:Rulebook {name: $name})", name=rulebook_name)
            
            xls = pd.ExcelFile(file_path)

            # --- 3. Process Level 1 Sheet ---
            if 'Level1' in xls.sheet_names:
                df1 = pd.read_excel(xls, 'Level1').dropna(how='all')
                for _, row in df1.iterrows():
                    self.run_query(
                        "MERGE (r:Rule {rule_id: $rule_id}) ON CREATE SET r.title = $title, r.level = 1",
                        rule_id=row['Level1_rule_number'], title=row['Level1_rule_title']
                    )
                    self.run_query(
                        "MATCH (rb:Rulebook {name: $book_name}) MATCH (r:Rule {rule_id: $rule_id}) MERGE (rb)-[:CONTAINS_CATEGORY]->(r)",
                        book_name=rulebook_name, rule_id=row['Level1_rule_number']
                    )
            
            # --- 4. Process Level 2 Sheet ---
            if 'Level2' in xls.sheet_names:
                df2 = pd.read_excel(xls, 'Level2').dropna(how='all').fillna('')
                for _, row in df2.iterrows():
                    parent_id = ".".join(str(row['Level2_rule_number']).split('.')[:-1])
                    self.run_query(
                        "MERGE (r:Rule {rule_id: $rule_id}) ON CREATE SET r.title = $title, r.text = $text, r.level = 2",
                        rule_id=row['Level2_rule_number'], title=row['Level2_rule_title'], text=row['Level2_rule_text']
                    )
                    self.run_query(
                        "MATCH (p:Rule {rule_id: $parent_id}), (c:Rule {rule_id: $child_id}) MERGE (p)-[:HAS_SUB_RULE]->(c)",
                        parent_id=parent_id, child_id=row['Level2_rule_number']
                    )

            # --- 5. Process Level 3 Sheet ---
            if 'Level3' in xls.sheet_names:
                df3 = pd.read_excel(xls, 'Level3').dropna(how='all').fillna('')
                for _, row in df3.iterrows():
                    parent_id = ".".join(str(row['Level3_rule_number']).split('.')[:-1])
                    self.run_query(
                        "MERGE (r:Rule {rule_id: $rule_id}) ON CREATE SET r.text = $text, r.level = 3",
                        rule_id=row['Level3_rule_number'], text=row['Level3_rule_text']
                    )
                    self.run_query(
                        "MATCH (p:Rule {rule_id: $parent_id}), (c:Rule {rule_id: $child_id}) MERGE (p)-[:HAS_SUB_RULE]->(c)",
                        parent_id=parent_id, child_id=row['Level3_rule_number']
                    )
            
            print(f" Finished uploading '{rulebook_name}'.")

        except Exception as e:
            print(f" Error processing file {file_path}: {e}")