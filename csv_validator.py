#!/usr/bin/env python3
"""
csv_validator.py

Prüft CSVDatei

"""

from __future__ import annotations

import csv
import sys
from pathlib import Path
from typing import List, Optional


# ============================================================
# CONFIG
# ============================================================

CSV_PATH = ""  # Optional: Wenn leer, wird argv[1] benutzt.

DELIMITER = ","
QUOTECHAR = '"'
ENCODING = "utf-8-sig"
HAS_HEADER = True
STRICT_PARSING = True

# Erwartete Werte:
EXPECTED_TOTAL_ROWS: Optional[int] = 99        # ink. Header falls HAS_HEADER=True
EXPECTED_DATA_ROWS: Optional[int] = 98           # nur Datenzeilen, no Header
EXPECTED_COLUMNS: Optional[int] = 44             # erwartete Anzahl Spalten
EXPECTED_TOTAL_CELLS: Optional[int] = None        # gesamt gelesene Zellen inkl. Header
EXPECTED_CELLS_PER_ROW: Optional[int] = None    # falls jede Zeile exakt gleich viele Zellen haben soll


ALLOW_EMPTY_ROWS = False
FAIL_ON_ROW_LENGTH_MISMATCH = True



def _resolve_csv_path() -> Path:
    if CSV_PATH.strip():
        return Path(CSV_PATH).expanduser().resolve()

    if len(sys.argv) < 2:
        print("FEHLER: Kein CSV-Pfad angegeben.")
        print("NUTZE: python csv_validator.py <datei.csv>")
        sys.exit(1)

    return Path(sys.argv[1]).expanduser().resolve()


def validate_csv(path: Path) -> int:
    print("=" * 70)
    print("CSV VALIDATOR")
    print("=" * 70)
    print(f"Datei:              {path}")
    print(f"Encoding:           {ENCODING}")
    print(f"Delimiter:          {repr(DELIMITER)}")
    print(f"Quotechar:          {repr(QUOTECHAR)}")
    print(f"Header erwartet:    {HAS_HEADER}")
    print(f"Strict Parsing:     {STRICT_PARSING}")
    print("-" * 70)

    if not path.exists():
        print("FEHLER: Datei existiert da.")
        return 2

    rows: List[List[str]] = []
    empty_row_indices: List[int] = []
    row_length_errors: List[str] = []
    parsing_error: Optional[str] = None

    try:
        with path.open("r", encoding=ENCODING, newline="") as f:
            reader = csv.reader(
                f,
                delimiter=DELIMITER,
                quotechar=QUOTECHAR,
                strict=STRICT_PARSING,
            )

            expected_len_from_first_row: Optional[int] = None

            for row_index, row in enumerate(reader, start=1):
                rows.append(row)

                is_empty = len(row) == 0 or all(cell == "" for cell in row)
                if is_empty:
                    empty_row_indices.append(row_index)

                current_len = len(row)
                if expected_len_from_first_row is None:
                    expected_len_from_first_row = current_len
                elif FAIL_ON_ROW_LENGTH_MISMATCH and current_len != expected_len_from_first_row:
                    row_length_errors.append(
                        f"Zeile {row_index}: {current_len} Spalten statt {expected_len_from_first_row}"
                    )

    except csv.Error as e:
        parsing_error = f"CSV Parsing/Quoting-Fehler: {e}"
    except UnicodeDecodeError as e:
        parsing_error = f"EncodingFehler: {e}"
    except Exception as e:
        parsing_error = f"Allgemeiner Lesefehler: {e}"

    if parsing_error:
        print("FEHLER!!!!")
        print(parsing_error)
        return 1

    total_rows = len(rows)
    header_rows = 1 if HAS_HEADER and total_rows > 0 else 0
    data_rows = max(total_rows - header_rows, 0)
    detected_columns = len(rows[0]) if rows else 0
    total_cells = sum(len(r) for r in rows)

    print("ERGEBNIS")
    print("-" * 70)
    print(f"Geladene Rows gesamt:        {total_rows}")
    print(f"Daten-Rows:                  {data_rows}")
    print(f"Erkannte Columns:            {detected_columns}")
    print(f"Zellen gesamt:               {total_cells}")

    if rows and HAS_HEADER:
        print(f"Header:                      {rows[0]}")
    else:
        print("Header:                      -")

    problems: List[str] = []

    if EXPECTED_TOTAL_ROWS is not None and total_rows != EXPECTED_TOTAL_ROWS:
        problems.append(
            f"Rows gesamt falsch: erwartet {EXPECTED_TOTAL_ROWS}, gefunden {total_rows}"
        )

    if EXPECTED_DATA_ROWS is not None and data_rows != EXPECTED_DATA_ROWS:
        problems.append(
            f"Daten-Rows falsch: erwartet {EXPECTED_DATA_ROWS}, gefunden {data_rows}"
        )

    if EXPECTED_COLUMNS is not None and detected_columns != EXPECTED_COLUMNS:
        problems.append(
            f"Columns falsch: erwartet {EXPECTED_COLUMNS}, gefunden {detected_columns}"
        )

    if EXPECTED_TOTAL_CELLS is not None and total_cells != EXPECTED_TOTAL_CELLS:
        problems.append(
            f"Zellen gesamt falsch: erwartet {EXPECTED_TOTAL_CELLS}, gefunden {total_cells}"
        )

    if EXPECTED_CELLS_PER_ROW is not None:
        for i, row in enumerate(rows, start=1):
            if len(row) != EXPECTED_CELLS_PER_ROW:
                problems.append(
                    f"Zeile {i}: falsche Zellanzahl, erwartet {EXPECTED_CELLS_PER_ROW}, gefunden {len(row)}"
                )

    if row_length_errors:
        problems.extend(row_length_errors)

    if empty_row_indices and not ALLOW_EMPTY_ROWS:
        problems.append(
            f"Leere Zeile: {', '.join(map(str, empty_row_indices))}"
        )

    print("-" * 70)
    if problems:
        print("FEHLER!!!!!")
        print("Gefundene Probleme:")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    print("STATUS: OK")
    print("NO Problems")
    return 0


def main() -> None:
    path = _resolve_csv_path()
    exit_code = validate_csv(path)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
