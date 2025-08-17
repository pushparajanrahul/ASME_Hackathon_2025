import pandas as pd
from pathlib import Path
import re
from src.parsing.extract_rules_from_pdf import clean_rule_text

def is_title_case(s):
    """Checks if a string is in title case (e.g., 'General Regulations')."""
    return s.istitle() or s.isupper()

def split_title_and_text(text):
    """
    Intelligently splits a rule's text into a title and the main body.
    """
    lines = text.split('\n')
    first_line = ""
    for line in lines:
        if line.strip():
            first_line = line.strip()
            break

    if first_line and is_title_case(first_line) and len(first_line.split()) < 10:
        title = first_line
        body = ' '.join(text.splitlines()[1:]).strip()
        if not body:
            return title, ""
        return title, body
    else:
        return "", text

def create_structured_excel_files(rules_df, category_titles):
    """
    Processes a DataFrame of rules and organizes them into hierarchical Excel files.
    """
    rules_df['main_category'] = rules_df['rule_num'].apply(lambda x: x.split('.')[0])
    main_categories = rules_df['main_category'].unique()

    output_dir = Path("structured_rules")
    output_dir.mkdir(exist_ok=True)
    print(f"\nSaving structured Excel files to: {output_dir.resolve()}")

    for category in main_categories:
        print(f"Processing category: {category}...")
        category_df = rules_df[rules_df['main_category'] == category].copy()
        main_title = category_titles.get(category, f"{category} Regulations")
        safe_filename = re.sub(r'[\\/*?:"<>|]', "", f"{category} - {main_title}.xlsx")
        excel_path = output_dir / safe_filename

        level1_data, level2_data, level3_data = [], [], []

        for _, row in category_df.iterrows():
            rule_num, title, body = row['rule_num'], row['rule_title'], row['rule_text']
            num_dots = rule_num.count('.')

            if num_dots == 1:
                level1_data.append({'Level1_rule_number': rule_num, 'Level1_rule_title': title})
            elif num_dots == 2:
                # --- APPLY TEXT CLEANING FOR LEVEL 2 ---
                cleaned_body = clean_rule_text(body)
                level2_data.append({'Level2_rule_number': rule_num, 'Level2_rule_title': title, 'Level2_rule_text': cleaned_body})
            elif num_dots >= 3:
                full_text = f"{title} {body}".strip()
                # --- APPLY TEXT CLEANING FOR LEVEL 3 ---
                cleaned_full_text = clean_rule_text(full_text)
                level3_data.append({'Level3_rule_number': rule_num, 'Level3_rule_text': cleaned_full_text})

        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            if level1_data:
                pd.DataFrame(level1_data).to_excel(writer, sheet_name='Level1', index=False)
            if level2_data:
                pd.DataFrame(level2_data).to_excel(writer, sheet_name='Level2', index=False)
            if level3_data:
                pd.DataFrame(level3_data).to_excel(writer, sheet_name='Level3', index=False)
        print(f"   -> Saved {safe_filename}")