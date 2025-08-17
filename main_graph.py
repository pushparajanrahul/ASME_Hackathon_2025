import os
import glob
from src.graph.kg_ingestion import Neo4jUploader, NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD

def run_ingestion():
    """
    Finds all Excel rulebooks and orchestrates the upload process to Neo4j.
    """
    # First, check if the required credentials were loaded successfully
    if not all([NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD]):
        print(" Error: Neo4j credentials not found in ./config/.env file!")
        print("Please ensure the file exists and contains the correct variables.")
        return

    uploader = Neo4jUploader(NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD)
    
    # Define the directory where your Excel files are stored
    data_directory = './structured_rules/'
    excel_files = glob.glob(os.path.join(data_directory, "*.xlsx"))
    
    if not excel_files:
        print(f" Warning: No Excel files (.xlsx) were found in the '{data_directory}' directory.")
        print("Please check the path and make sure your rulebooks are there.")
    else:
        print(f"Found {len(excel_files)} rulebooks to process...")
        for file_path in excel_files:
            uploader.upload_rulebook_from_excel(file_path)
    
    uploader.close()
    print("\n🚀 All rulebooks have been processed.")

if __name__ == "__main__":
    # This block executes when you run `python main.py` from your root directory
    run_ingestion()