# Project: Combinatorial Counting and Permutation Analyzer
# Group Members (Name - Roll No):
#   Dheer Chheda      - 251080019
#   Diyan Shah        - 251080020
#   Aryan Adivarekar  - 251080008
#   Advait Deodhar    - 251080018
#
# Saves every calculation to history.txt (next to this file), one record per line:
#   timestamp|operation|inputs|result

import os
import datetime

# tests.py points this at a temporary file so running the tests never changes the real history.
DEFAULT_HISTORY_FILENAME = "history.txt"
FIELDS = ("timestamp", "operation", "inputs", "result")


def get_history_file_path(filename=None):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename or DEFAULT_HISTORY_FILENAME)


def clean(text):
    # "|" separates fields and newlines separate records, so both become single spaces.
    return " ".join(str(text).replace("|", " ").split())


def save_history_record(operation, inputs, result, filename=None):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = "|".join([timestamp, clean(operation), clean(inputs), clean(result)])
    try:
        with open(get_history_file_path(filename), "a", encoding="utf-8") as f:
            f.write(line + "\n")
        return True
    except OSError:
        return False


def read_history_records(filename=None):
    # Returns (records, skipped). Lines without exactly 4 fields are counted, not fatal.
    records, skipped = [], 0
    try:
        with open(get_history_file_path(filename), encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split("|")
                if len(parts) == len(FIELDS):
                    records.append(dict(zip(FIELDS, (p.strip() for p in parts))))
                elif line.strip():
                    skipped += 1
    except OSError:
        # A missing file just means nothing has been saved yet.
        pass
    return records, skipped


def search_history_records(query, filename=None):
    # Case-insensitive match on the operation name or the inputs.
    # Returns (matches, total number of records, skipped lines).
    records, skipped = read_history_records(filename)
    query = query.strip().lower()
    matches = [r for r in records if query in r["operation"].lower() or query in r["inputs"].lower()]
    return matches, len(records), skipped


def clear_history(filename=None):
    try:
        open(get_history_file_path(filename), "w", encoding="utf-8").close()
        return True
    except OSError:
        return False
