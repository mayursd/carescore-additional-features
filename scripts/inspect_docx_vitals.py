#!/usr/bin/env python3
"""
Inspect a DOCX template and report tables that contain vitals headers
(BP, HR, RR, SPO2, Temp, Pain). Useful to find which table to populate.

Usage:
  python scripts/inspect_docx_vitals.py path/to/SOAP_Note_Template.docx

Outputs a summary of tables, first-row header texts, and detected header column indices.
"""
import sys
import argparse
from docx import Document

VITAL_HEADERS = ["bp", "blood pressure", "hr", "heart rate", "rr", "respiratory rate", "spo2", "o2 sat", "temp", "temperature", "pain"]


def normalize(s: str) -> str:
    return (s or "").strip().lower()


def analyze_docx(path: str):
    doc = Document(path)
    tables = list(doc.tables)
    if not tables:
        print("No tables found in document.")
        return 1

    print(f"Found {len(tables)} tables in {path}\n")

    found_any = False
    for ti, tbl in enumerate(tables):
        # Gather first row header texts (safe)
        try:
            first_row = tbl.rows[0]
            header_texts = [c.text.strip() for c in first_row.cells]
        except Exception:
            header_texts = []

        print(f"Table {ti}: rows={len(tbl.rows)} cols={len(first_row.cells) if header_texts else 'unknown'}")
        print("  Header texts:")
        for ci, ht in enumerate(header_texts):
            print(f"    col {ci}: '{ht}'")

        # detect vitals headers
        header_map = {}
        for ci, ht in enumerate(header_texts):
            ht_norm = normalize(ht)
            for v in VITAL_HEADERS:
                if v in ht_norm:
                    header_map.setdefault(v, []).append(ci)

        # More friendly mapping search for common short headers
        simple_map = {}
        for ci, ht in enumerate(header_texts):
            h = normalize(ht)
            if "bp" == h or "blood pressure" in h:
                simple_map['BP'] = ci
            elif "hr" == h or "heart rate" in h:
                simple_map['HR'] = ci
            elif "rr" == h or "respiratory rate" in h:
                simple_map['RR'] = ci
            elif "spo2" in h or "o2" in h or "o2 sat" in h:
                simple_map['SPO2'] = ci
            elif "temp" in h or "temperature" in h:
                simple_map['Temp'] = ci
            elif "pain" in h:
                simple_map['Pain'] = ci

        if header_map or simple_map:
            found_any = True
            print("  Detected vitals headers:")
            for k, v in simple_map.items():
                print(f"    {k}: column {v} (header='{header_texts[v]}')")
            # show any fuzzy matches
            for pattern, cols in header_map.items():
                print(f"    fuzzy match '{pattern}': columns {cols}")

            # show sample second row content if present
            if len(tbl.rows) > 1:
                second_row = tbl.rows[1]
                print("  Second row sample values:")
                for ci, cell in enumerate(second_row.cells):
                    print(f"    col {ci}: '{cell.text.strip()}'")

        print("")

    if not found_any:
        print("No vitals headers detected in any table.")
        return 2

    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Inspect DOCX for vitals table and header positions")
    parser.add_argument("docx_path", help="Path to the DOCX file to inspect")
    args = parser.parse_args(argv)
    return analyze_docx(args.docx_path)


if __name__ == '__main__':
    sys.exit(main())
