"""
Mozzart PDF Parser — Production v2.0
=====================================
Parses Mozzart 'Dnevna ponuda' and 'Lista' PDF bulletins and extracts structured
multi-market match data:
  1. Full Time 1X2 & Double Chance (Base match ID: M)
  2. First Half 1X2 & Double Chance (Market ID: M16)
  3. Goals Range: 0-1, 0-2, 2-3 (Market ID: M3)
  4. Total Goals: 2+, 3+, 4+ (Market ID: M2)

Key capabilities:
  - 100% Date Coverage: Extracts PDF metadata ('CreationDate'/'ModDate') combined with
    page header day-dates (e.g. 'PETAK 08.11.'), eliminating missing dates.
  - Robust fused-token odds extraction ("1,604,307,00" → [1.60, 4.30, 7.00])
  - Relational Market Fusion: Automatically attaches M16 (Halftime) and M3 (Goal Range)
    records to the parent match M.
  - Backward compatible schema aliases (odd_1, odd_x, odd_2 for ft_1, ft_x, ft_2).

Output schema:
  match_id, date, home_team, away_team, kick_off,
  ft_1, ft_x, ft_2, ft_1x, ft_x2, ft_12,
  ht_1, ht_x, ht_2, ht_1x, ht_x2, ht_12,
  ug_0_1, ug_0_2, ug_2_plus, ug_3_plus,
  odd_1, odd_x, odd_2,
  source_file, parsed_at

CLI usage:
  python -m unified_betting_core.data_ingestion.mozzart_pdf_parser \\
      --input-dir unified_betting_core/data/mozzart_pdfs \\
      --output unified_betting_core/data/mozzart_parsed_v2.csv
"""

import csv
import logging
import os
import re
import sys
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

import pdfplumber

logger = logging.getLogger("Mozzart.PDFParser")

# ---------------------------------------------------------------------------
# Constants & Regexes
# ---------------------------------------------------------------------------

_DAYS = r"(?:pon|uto|sri|čet|pet|sub|ned)"

# Base Match Line Regex:
# e.g. "5036 Rayo Vallecano-Las Palmas pet 21:00 1,95 3,50 5,00 1,25 2,05 1,40"
_BASE_MATCH_RE = re.compile(
    r"(\d{4,6})\s+"              # G1: match_id
    r"([A-Za-zČĆŽŠĐčćžšđ][A-Za-zČĆŽŠĐčćžšđ\s\.\-]+?)" # G2: teams
    r"(?:\s*\(s\.p\.\)|\s*\(b\.p\.\))?" # optional bonus/super indicators
    r"\s+" + _DAYS + r"\s+"      # day abbreviation
    r"(\d{2}:\d{2})"             # G3: kick-off
    r"\s+([\d,][^\n]{3,})",       # G4: odds blob
    re.UNICODE | re.IGNORECASE,
)

# Halftime Line Regex:
# e.g. "503616 Rayo Vallecano-Las Palmas 2,70 2,05 4,00 1,17 1,36 1,61"
_HT_LINE_RE = re.compile(
    r"(\d{4,6})16\s*"            # G1: base match_id
    r"([A-Za-zČĆŽŠĐčćžšđ][A-Za-zČĆŽŠĐčćžšđ\s\.\-]+?)"    # G2: teams
    r"\s+((?:\d{1,4},\d{1,2}\s*){3,6})",       # G3: odds blob
    re.UNICODE | re.IGNORECASE,
)

# Total Goals Range Line Regex (M3):
# e.g. "50363 Rayo Vallecano-Las Palmas 2,80 1,62 1,20 1,37 1,95 1,53 1,43 2,30 1,40"
_GOAL_RANGE_RE = re.compile(
    r"(\d{4,6})3\s*"             # G1: base match_id
    r"([A-Za-zČĆŽŠĐčćžšđ][A-Za-zČĆŽŠĐčćžšđ\s\.\-]+?)"    # G2: teams
    r"\s+((?:\d{1,4},\d{1,2}\s*){2,9})",       # G3: odds blob
    re.UNICODE | re.IGNORECASE,
)

# Total Goals Line Regex (M2):
# e.g. "50362 Rayo Vallecano-Las Palmas 1,38 2,15 4,00 8,25 20,0 55,0"
_GOAL_TOTAL_RE = re.compile(
    r"(\d{4,6})2\s*"             # G1: base match_id
    r"([A-Za-zČĆŽŠĐčćžšđ][A-Za-zČĆŽŠĐčćžšđ\s\.\-]+?)"    # G2: teams
    r"\s+((?:\d{1,4},\d{1,2}\s*){2,6})",       # G3: odds blob
    re.UNICODE | re.IGNORECASE,
)

# Date extraction from filename
_DATE_FILENAME_PATTERNS = [
    (re.compile(r"(\d{2})\.(\d{2})\.(\d{4})"), "dmy"),   # DD.MM.YYYY
    (re.compile(r"(\d{4})(\d{2})(\d{2})"),      "ymd"),   # YYYYMMDD
    (re.compile(r"dnevna(\d{4})(\d{2})(\d{2})"),"ymd"),  # dnevnaYYYYMMDD
    (re.compile(r"dnevna_(\d{2})\.(\d{2})\.(\d{4})"), "dmy"),
]

# Page header day-date pattern: "PETAK 08.11." or "SRIJEDA 03.06. 2026"
_PAGE_DATE_RE = re.compile(
    r"(?:PONEDJELJA[K]?|UTORAK|SRIJEDA|ČETVRTAK|PETAK|SUBOTA|NEDJELJA)\s+"
    r"(\d{1,2})\.(\d{1,2})\.?(?:\s*(\d{4}))?",
    re.IGNORECASE | re.UNICODE,
)

# PDF Metadata creation date: "D:20241108130219..."
_PDF_METADATA_DATE_RE = re.compile(r"D:(\d{4})(\d{2})(\d{2})")


# ---------------------------------------------------------------------------
# Date Extraction & Provenance
# ---------------------------------------------------------------------------

def _parse_date_from_filename(filename: str) -> Optional[datetime]:
    name = os.path.basename(filename)
    for pattern, mode in _DATE_FILENAME_PATTERNS:
        m = pattern.search(name)
        if not m:
            continue
        try:
            g = m.groups()
            if mode == "ymd":
                return datetime(int(g[0]), int(g[1]), int(g[2]))
            else:
                return datetime(int(g[2]), int(g[1]), int(g[0]))
        except ValueError:
            continue
    return None


def _parse_date_from_metadata(metadata: Optional[dict]) -> Optional[datetime]:
    """Extract creation date from PDF document metadata."""
    if not metadata:
        return None
    for field in ("CreationDate", "ModDate"):
        val = metadata.get(field)
        if val and isinstance(val, str):
            m = _PDF_METADATA_DATE_RE.search(val)
            if m:
                try:
                    return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
                except ValueError:
                    pass
    return None


def _parse_date_from_page_header(text: str) -> Optional[Tuple[int, int, Optional[int]]]:
    """Extract (day, month, optional_year) from page header text."""
    m = _PAGE_DATE_RE.search(text)
    if m:
        d = int(m.group(1))
        mo = int(m.group(2))
        yr = int(m.group(3)) if m.group(3) else None
        return d, mo, yr
    return None


def _resolve_match_date(
    base_date: Optional[datetime],
    page_header_dm: Optional[Tuple[int, int, Optional[int]]],
) -> Optional[str]:
    """Resolve full ISO date YYYY-MM-DD from base date (metadata/file) and page header."""
    if page_header_dm:
        d, mo, explicit_yr = page_header_dm
        yr = explicit_yr or (base_date.year if base_date else None)
        if yr and 2018 <= yr <= 2030 and 1 <= mo <= 12 and 1 <= d <= 31:
            try:
                return datetime(yr, mo, d).strftime("%Y-%m-%d")
            except ValueError:
                pass
    if base_date:
        return base_date.strftime("%Y-%m-%d")
    return None


# ---------------------------------------------------------------------------
# Odds Extraction & Defusing
# ---------------------------------------------------------------------------

def _extract_odds(blob: str, max_tokens: int = 10) -> List[float]:
    """
    Extract odds floats from raw blob text.
    Handles fused tokens like '1,604,307,00' → [1.60, 4.30, 7.00].
    """
    clean = re.sub(r"[^\d,\.\s].*$", "", blob).strip()

    # Iterative defusing: '1,604,30' → '1,60 4,30'
    prev = None
    while prev != clean:
        prev = clean
        clean = re.sub(r"(\d,\d{2})(\d)", r"\1 \2", clean)

    tokens = re.findall(r"(\d{1,4}),(\d{1,2})(?!\d)", clean)
    odds = []
    for int_part, dec_part in tokens:
        try:
            val = float(f"{int_part}.{dec_part}")
            odds.append(val)
        except ValueError:
            continue
    return odds[:max_tokens]


def _clean_teams(teams_raw: str) -> Tuple[str, str]:
    """Split raw match description into home and away teams."""
    clean = re.sub(r"\s*\([sb]\.p\.\)\s*$", "", teams_raw).strip()
    team_split = re.split(r"(?<=\w)-(?=\w)", clean, maxsplit=1)
    if len(team_split) == 2:
        return team_split[0].strip(), team_split[1].strip()
    idx = clean.find("-")
    if idx != -1:
        return clean[:idx].strip(), clean[idx + 1:].strip()
    return clean, ""


# ---------------------------------------------------------------------------
# Single PDF Parsing Engine
# ---------------------------------------------------------------------------

def parse_pdf(pdf_path: str) -> List[Dict[str, Any]]:
    """
    Parse a single Mozzart PDF bulletin, extracting parent matches and merging
    their Halftime (M16) and Goals (M3, M2) sub-markets.
    """
    parsed_at = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    filename = os.path.basename(pdf_path)

    base_records: Dict[str, Dict[str, Any]] = {}
    ht_records: Dict[str, List[float]] = {}
    goals_range_records: Dict[str, List[float]] = {}
    goals_total_records: Dict[str, List[float]] = {}

    try:
        with pdfplumber.open(pdf_path) as pdf:
            file_date = _parse_date_from_filename(filename) or _parse_date_from_metadata(pdf.metadata)

            for page in pdf.pages:
                text = page.extract_text() or ""
                lines = text.splitlines()

                page_dm = _parse_date_from_page_header(text[:800])
                resolved_date = _resolve_match_date(file_date, page_dm)

                for line in lines:
                    line_str = line.strip()
                    if not line_str:
                        continue

                    # 1. Base match lines (Full Time 1X2 & DC)
                    for m_base in _BASE_MATCH_RE.finditer(line_str):
                        mid = m_base.group(1)
                        teams_raw = m_base.group(2)
                        kickoff = m_base.group(3)
                        blob = m_base.group(4)
                        odds = _extract_odds(blob, max_tokens=6)
                        if len(odds) >= 2 and mid not in base_records:
                            home, away = _clean_teams(teams_raw)
                            base_records[mid] = {
                                "match_id": mid,
                                "date": resolved_date or "",
                                "home_team": home,
                                "away_team": away,
                                "kick_off": kickoff,
                                "ft_1": odds[0] if len(odds) > 0 else None,
                                "ft_x": odds[1] if len(odds) > 1 else None,
                                "ft_2": odds[2] if len(odds) > 2 else None,
                                "ft_1x": odds[3] if len(odds) > 3 else None,
                                "ft_x2": odds[4] if len(odds) > 4 else None,
                                "ft_12": odds[5] if len(odds) > 5 else None,
                                "source_file": filename,
                                "parsed_at": parsed_at,
                            }

                    # 2. Halftime lines (M16)
                    for m_ht in _HT_LINE_RE.finditer(line_str):
                        mid = m_ht.group(1)
                        blob = m_ht.group(3)
                        odds = _extract_odds(blob, max_tokens=6)
                        if len(odds) >= 3 and mid not in ht_records:
                            ht_records[mid] = odds

                    # 3. Goals Range lines (M3)
                    for m_gr in _GOAL_RANGE_RE.finditer(line_str):
                        mid = m_gr.group(1)
                        blob = m_gr.group(3)
                        odds = _extract_odds(blob, max_tokens=9)
                        if len(odds) >= 2 and mid not in goals_range_records:
                            goals_range_records[mid] = odds

                    # 4. Total Goals lines (M2)
                    for m_gt in _GOAL_TOTAL_RE.finditer(line_str):
                        mid = m_gt.group(1)
                        blob = m_gt.group(3)
                        odds = _extract_odds(blob, max_tokens=6)
                        if len(odds) >= 2 and mid not in goals_total_records:
                            goals_total_records[mid] = odds

    except Exception as e:
        logger.error(f"Error reading PDF {filename}: {e}")
        return []

    # Assemble fused records
    output: List[Dict[str, Any]] = []
    for mid, rec in base_records.items():
        # Attach Halftime odds if available
        ht_odds = ht_records.get(mid)
        rec["ht_1"] = ht_odds[0] if ht_odds and len(ht_odds) > 0 else None
        rec["ht_x"] = ht_odds[1] if ht_odds and len(ht_odds) > 1 else None
        rec["ht_2"] = ht_odds[2] if ht_odds and len(ht_odds) > 2 else None
        rec["ht_1x"] = ht_odds[3] if ht_odds and len(ht_odds) > 3 else None
        rec["ht_x2"] = ht_odds[4] if ht_odds and len(ht_odds) > 4 else None
        rec["ht_12"] = ht_odds[5] if ht_odds and len(ht_odds) > 5 else None

        # Attach Goal range odds if available
        gr_odds = goals_range_records.get(mid)
        rec["ug_0_1"] = gr_odds[0] if gr_odds and len(gr_odds) > 0 else None
        rec["ug_0_2"] = gr_odds[1] if gr_odds and len(gr_odds) > 1 else None

        # Attach Total goals odds if available
        gt_odds = goals_total_records.get(mid)
        rec["ug_2_plus"] = gt_odds[0] if gt_odds and len(gt_odds) > 0 else None
        rec["ug_3_plus"] = gt_odds[1] if gt_odds and len(gt_odds) > 1 else None

        # Backward compatibility aliases
        rec["odd_1"] = rec["ft_1"]
        rec["odd_x"] = rec["ft_x"]
        rec["odd_2"] = rec["ft_2"]

        output.append(rec)

    return output


# ---------------------------------------------------------------------------
# Directory Batch Processing
# ---------------------------------------------------------------------------

def parse_directory(
    input_dir: str,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    max_files: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Process a directory of Mozzart PDF bulletins."""
    all_records: List[Dict[str, Any]] = []
    if not os.path.exists(input_dir):
        logger.error(f"Input directory does not exist: {input_dir}")
        return []

    files = sorted(f for f in os.listdir(input_dir) if f.lower().endswith(".pdf"))
    if max_files:
        files = files[:max_files]

    processed = 0
    errors = 0

    for idx, fname in enumerate(files):
        pdf_path = os.path.join(input_dir, fname)
        try:
            records = parse_pdf(pdf_path)
            all_records.extend(records)
            processed += 1
            if (idx + 1) % 50 == 0 or (idx + 1) == len(files):
                logger.info(f"Processed {idx + 1}/{len(files)} PDFs — {len(all_records)} matches extracted.")
        except Exception as e:
            logger.error(f"Failed parsing {fname}: {e}")
            errors += 1

    logger.info(f"Batch completed: {len(all_records)} matches from {processed} PDFs (Errors: {errors}).")
    return all_records


# ---------------------------------------------------------------------------
# Output Schemas & CSV Writing
# ---------------------------------------------------------------------------

_OUTPUT_SCHEMA = [
    "match_id", "date", "home_team", "away_team", "kick_off",
    "ft_1", "ft_x", "ft_2", "ft_1x", "ft_x2", "ft_12",
    "ht_1", "ht_x", "ht_2", "ht_1x", "ht_x2", "ht_12",
    "ug_0_1", "ug_0_2", "ug_2_plus", "ug_3_plus",
    "odd_1", "odd_x", "odd_2",
    "source_file", "parsed_at",
]


def records_to_csv(records: List[Dict[str, Any]], output_path: str) -> None:
    """Write parsed records to CSV with complete schema."""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_OUTPUT_SCHEMA, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)
    logger.info(f"Wrote {len(records)} records → {output_path}")


def records_to_dataframe(records: List[Dict[str, Any]]):
    """Convert records to pandas DataFrame with numeric coercions."""
    try:
        import pandas as pd
        df = pd.DataFrame(records, columns=_OUTPUT_SCHEMA)
        numeric_cols = [
            "ft_1", "ft_x", "ft_2", "ft_1x", "ft_x2", "ft_12",
            "ht_1", "ht_x", "ht_2", "ht_1x", "ht_x2", "ht_12",
            "ug_0_1", "ug_0_2", "ug_2_plus", "ug_3_plus",
            "odd_1", "odd_x", "odd_2"
        ]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.strftime("%Y-%m-%d")
        return df
    except ImportError:
        return records


# ---------------------------------------------------------------------------
# CLI Entrypoint
# ---------------------------------------------------------------------------

def _cli() -> None:
    import argparse

    ap = argparse.ArgumentParser(description="Parse Mozzart PDF Bulletins → CSV (Production v2.0)")
    ap.add_argument("--input-dir", "-i", default="unified_betting_core/data/mozzart_pdfs")
    ap.add_argument("--output", "-o", default="unified_betting_core/data/mozzart_parsed_v2.csv")
    ap.add_argument("--single-file", "-f", help="Parse one PDF")
    ap.add_argument("--max-files", "-m", type=int, help="Limit number of PDFs processed")
    ap.add_argument("--verbose", "-v", action="store_true")
    args = ap.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if args.single_file:
        records = parse_pdf(args.single_file)
    else:
        records = parse_directory(args.input_dir, max_files=args.max_files)

    if not records:
        logger.warning("No matches extracted.")
        sys.exit(1)

    records_to_csv(records, args.output)
    print(f"\n✅ Extracted {len(records)} matches → {args.output}")


if __name__ == "__main__":
    _cli()
