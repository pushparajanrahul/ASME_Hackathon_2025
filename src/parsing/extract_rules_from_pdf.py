import fitz  # The PyMuPDF library
import pandas as pd
from pathlib import Path
import re

def is_footer_line(line):
    """
    Checks if a given line of text matches known footer patterns using regular expressions.
    This handles dynamic content like page numbers and dates.
    """
    line = line.strip()
    footer_patterns = [
        re.compile(r'^Formula SAE®? Rules \d{4}$'),
        re.compile(r'^© \d{4} SAE International$'),
        re.compile(r'^Page \d+ of \d+$'),
        re.compile(r'^Version \d\.\d\s+\d{1,2}\s\w+\s\d{4}$')
    ]
    for pattern in footer_patterns:
        if pattern.match(line):
            return True
    return False

def clean_rule_text(text):
    """
    Cleans up newline characters from extracted text based on the specified logic.
    The order of replacement is critical.
    """
    if not isinstance(text, str):
        return text
    # 1. Replace three consecutive newlines with two spaces and a newline
    text = text.replace('\n\n\n', '  \n')
    # 2. Replace two consecutive newlines with one space and a newline
    text = text.replace('\n\n', ' \n')
    # 3. Replace any remaining single newlines with a single space
    text = text.replace('\n', ' ')
    return text

def extract_rules_from_pdf(pdf_path):
    """
    Extracts rules, titles, and text from a PDF document.
    """
    doc = fitz.open(pdf_path)
    rules_data = []
    category_titles = {}
    current_rule_text = ""
    current_rule_number = None

    print("Scanning Table of Contents for category titles...")
    toc_title_pattern = re.compile(r'^([A-Z]{1,})\s+-\s+(.+)', re.MULTILINE)
    for page_num in range(min(20, len(doc))):
        page_text = doc[page_num].get_text()
        matches = toc_title_pattern.findall(page_text)
        for code, title in matches:
            clean_title = title.split('..')[0].strip()
            if code not in category_titles:
                category_titles[code] = clean_title
    print(f"Found {len(category_titles)} main category titles.")

    def _find_content_start_page(doc):
        toc_pattern = re.compile(r'\.{5,}')
        last_toc_page = 0
        for page_num in range(min(20, len(doc))):
            page = doc[page_num]
            if toc_pattern.search(page.get_text()):
                last_toc_page = page_num
        start_page = last_toc_page + 1
        print(f"Dynamically found end of Table of Contents on page {last_toc_page + 1}.")
        print(f"Starting main content extraction from page {start_page + 1}.")
        return start_page

    rule_heading_pattern = re.compile(r'^[A-Z]{1,2}\.\d{1,2}(?:\.\d{1,2})*\s')
    start_page = _find_content_start_page(doc)

    for page_num in range(start_page, len(doc)):
        page = doc[page_num]
        links = page.get_links()
        link_rects = [link['from'] for link in links]
        blocks = page.get_text("blocks")
        for block in blocks:
            if block[6] != 0: continue
            
            block_rect = fitz.Rect(block[:4])
            is_hyperlink = any(r.intersects(block_rect) for r in link_rects)

            if is_hyperlink:
                process_this_block = False
                new_rule_num_in_block = None
                block_text_peek = block[4]
                for line in block_text_peek.split('\n'):
                    match = rule_heading_pattern.match(line)
                    if match:
                        new_rule_num_in_block = line.split()[0]
                        break
                if new_rule_num_in_block:
                    if new_rule_num_in_block.count('.') >= 3:
                        process_this_block = True
                else:
                    if current_rule_number and current_rule_number.count('.') >= 3:
                        process_this_block = True
                if not process_this_block:
                    continue

            block_text = block[4]
            lines = block_text.split('\n')
            for line in lines:
                if is_footer_line(line):
                    continue

                match = rule_heading_pattern.match(line)
                if match:
                    if current_rule_number:
                        rules_data.append({'rule_num': current_rule_number, 'rule_text': current_rule_text.strip()})
                    current_rule_number = line.split()[0]
                    current_rule_text = ' '.join(line.split()[1:])
                elif current_rule_number:
                    current_rule_text += "\n" + line

    if current_rule_number:
        rules_data.append({'rule_num': current_rule_number, 'rule_text': current_rule_text.strip()})

    processed_rules = []
    for rule in rules_data:
        rule_num, full_text = rule['rule_num'], rule['rule_text']
        num_dots = rule_num.count('.')
        if num_dots <= 2 and '\n' in full_text:
            parts = full_text.split('\n', 1)
            title, body = parts[0].strip(), parts[1].strip()
        elif num_dots >= 3:
            title, body = "", full_text.strip()
        else:
            title, body = full_text.strip(), ""
        processed_rules.append({'rule_num': rule_num, 'rule_title': title, 'rule_text': body})

    return pd.DataFrame(processed_rules), category_titles