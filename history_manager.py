# Project: Combinatorial Counting and Permutation Analyzer
# Name: [YOUR NAME]  Roll No: [YOUR ROLL NO]
# Module: history_manager.py - Persistent record saving, loading, and searching

import os
import datetime


def get_history_file_path(filename="history.txt"):
    """Returns absolute path to history.txt located alongside this module."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, filename)


def sanitize_field(text):
    """Sanitizes text fields by replacing pipe delimiter and newlines with spaces."""
    cleaned = str(text)
    cleaned = cleaned.replace("|", " ")
    cleaned = cleaned.replace("\r", " ")
    cleaned = cleaned.replace("\n", " ")
    return cleaned.strip()


def save_history_record(operation, inputs_str, result_str, filename="history.txt"):
    """Appends one calculation record to history.txt.
    
    Record format: timestamp|operation|inputs|result
    Any pipe characters in fields are sanitized to spaces.
    Uses UTF-8 encoding.
    """
    file_path = get_history_file_path(filename)
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    clean_op = sanitize_field(operation)
    clean_in = sanitize_field(inputs_str)
    clean_res = sanitize_field(result_str)
    
    record_line = clean_op + "|" + clean_in + "|" + clean_res
    full_line = now_str + "|" + record_line + "\n"
    
    try:
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(full_line)
        return True
    except Exception as e:
        # File errors must not crash the application
        return False


def read_history_records(filename="history.txt"):
    """Reads all history records from history.txt.
    
    Handles missing file, empty file, and skips malformed lines.
    Returns a tuple: (list_of_record_dicts, skipped_malformed_count).
    Each dict contains: 'timestamp', 'operation', 'inputs', 'result'.
    """
    file_path = get_history_file_path(filename)
    
    if not os.path.exists(file_path):
        return ([], 0)
    
    records = []
    skipped_count = 0
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        for raw_line in lines:
            line = raw_line.strip()
            if not line:
                continue
            parts = line.split("|")
            if len(parts) == 4:
                records.append({
                    "timestamp": parts[0].strip(),
                    "operation": parts[1].strip(),
                    "inputs": parts[2].strip(),
                    "result": parts[3].strip()
                })
            else:
                skipped_count = skipped_count + 1
        
        return (records, skipped_count)
    except Exception:
        return ([], 0)


def search_history_records(query, filename="history.txt"):
    """Searches history records matching query in operation or inputs (case-insensitive).
    
    Returns a tuple: (matching_records, total_records_count, skipped_count).
    """
    records, skipped = read_history_records(filename)
    if not query:
        return (records, len(records), skipped)
    
    normalized_query = query.strip().lower()
    matches = []
    for r in records:
        op_match = normalized_query in r["operation"].lower()
        in_match = normalized_query in r["inputs"].lower()
        if op_match or in_match:
            matches.append(r)
    
    return (matches, len(records), skipped)
