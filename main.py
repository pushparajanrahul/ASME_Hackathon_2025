from src.parsing.extract_rules_from_pdf import extract_rules_from_pdf
from src.parsing.structred_excel_files import create_structured_excel_files
import pandas as pd
from pathlib import Path
import openpyxl

if __name__ == "__main__":
    
    # Step 1: Extract rules from the PDF
    print("Step 1: Extracting rules from PDF...")
    pdf_path = "design_qa/dataset/docs/FSAE_Rules_2024_V1.pdf"
    all_rules_df, category_titles_map = extract_rules_from_pdf(pdf_path)
    print(f"Extraction complete. Found {len(all_rules_df)} total rules.")

    # Step 2: Structure the extracted rules into categorized Excel files
    print("\nStep 2: Structuring rules into categorized Excel files...")
    create_structured_excel_files(all_rules_df, category_titles_map)
    #create_excel_with_formatted_text(all_rules_df, category_titles_map)
    print("\nProcessing complete.")