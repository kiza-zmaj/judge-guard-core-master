"""
Mozzart Full Ingestion Pipeline (v2.0 - High Performance).
Downloads all official Mozzart betting lists (Web lista kolo + Dnevna ponuda)
directly from the public S3 archive and parses them into a high-resolution
dataset with full-time, first-half (HT), and second-half (SH) closing lines.
Uses zero-backtracking token parser for blazing speed (<0.1s per bulletin).
"""

import os
import sys
import re
import time
import logging
import urllib.parse
import subprocess
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            "/home/kizamladjanijebac/Documents/jude guard/judge-guard-core-master/unified_betting_core/data/mozzart_download_and_parse.log",
            mode="a",
            encoding="utf-8"
        )
    ]
)
logger = logging.getLogger("Mozzart.Ingestion")

S3_BASE = "https://adminko.s3.eu-west-3.amazonaws.com"
BUCKET_LIST_URL = f"{S3_BASE}/?prefix=documents/pdfs/&list-type=2&max-keys=1000"
PDF_STORAGE_DIR = "/home/kizamladjanijebac/Documents/jude guard/judge-guard-core-master/unified_betting_core/data/mozzart_pdfs"
OUTPUT_DIR = "/home/kizamladjanijebac/Documents/jude guard/judge-guard-core-master/unified_betting_core/output/mozzart_parsed"
OUTPUT_CSV = os.path.join(OUTPUT_DIR, "mozzart_historical_odds.csv")


def enumerate_all_pdf_keys():
    """Fetch complete S3 list of all betting bulletin PDFs."""
    logger.info("Connecting to S3 repository to discover all bulletin PDFs...")
    ns = {'s3': 'http://s3.amazonaws.com/doc/2006-03-01/'}
    all_keys = []
    continuation_token = None

    while True:
        url = BUCKET_LIST_URL
        if continuation_token:
            url += f"&continuation-token={urllib.parse.quote(continuation_token)}"
        
        try:
            import requests
            r = requests.get(url, timeout=12)
            root = ET.fromstring(r.text)
            keys = root.findall('.//s3:Key', ns)
            for k in keys:
                if k.text and k.text.lower().endswith('.pdf'):
                    fn = k.text.replace('documents/pdfs/', '').strip().lower()
                    if any(w in fn for w in ['web lista', 'web  lista', 'web_lista', 'weblista', 'dnevna', 'dnavna', 'lista']):
                        all_keys.append(k.text)
            
            is_trunc = root.find('.//s3:IsTruncated', ns)
            next_tok = root.find('.//s3:NextContinuationToken', ns)
            if is_trunc is not None and is_trunc.text == 'true' and next_tok is not None and next_tok.text:
                continuation_token = next_tok.text
            else:
                break
        except Exception as e:
            logger.error(f"Error fetching catalog page: {e}")
            break

    logger.info(f"Discovered {len(all_keys)} target Mozzart betting bulletin PDFs.")
    return all_keys


def download_single_pdf(s3_key):
    """Download single PDF with size validation."""
    filename = s3_key.replace("documents/pdfs/", "").strip()
    safe_fn = re.sub(r'[^\w\-_\.]', '_', filename)
    local_path = os.path.join(PDF_STORAGE_DIR, safe_fn)

    # If already downloaded and valid, return cached
    if os.path.exists(local_path) and os.path.getsize(local_path) > 20_000:
        return {"status": "cached", "path": local_path, "key": s3_key, "filename": filename}

    url = f"{S3_BASE}/documents/pdfs/{urllib.parse.quote(filename)}"
    try:
        import requests
        resp = requests.get(url, timeout=30, stream=True)
        if resp.status_code == 200:
            with open(local_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=65536):
                    f.write(chunk)
            if os.path.getsize(local_path) > 20_000:
                return {"status": "downloaded", "path": local_path, "key": s3_key, "filename": filename}
        return {"status": "failed", "error": f"HTTP {resp.status_code}", "path": local_path}
    except Exception as e:
        return {"status": "failed", "error": str(e), "path": local_path}


def parse_pdf_to_records(pdf_path, filename):
    """
    Ultra-fast, zero-backtracking token-based parser.
    Converts PDF to text via pdftotext -layout and extracts football odds.
    Handles both Dnevna ponuda and Web lista formats, comma and dot decimals.
    """
    txt_path = pdf_path + ".txt"
    try:
        res = subprocess.run(["pdftotext", "-layout", pdf_path, txt_path], capture_output=True, timeout=20)
        if res.returncode != 0 or not os.path.exists(txt_path):
            return []
        with open(txt_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except Exception:
        return []
    finally:
        if os.path.exists(txt_path):
            os.remove(txt_path)

    # Date extraction from text or filename
    date_str = ""
    for line in lines[:25]:
        m_d = re.search(r'(\d{2})\.(\d{2})\.(\d{4})\.?', line)
        if m_d:
            d, m, y = m_d.groups()
            date_str = f"{y}-{m}-{d}"
            break

    if not date_str:
        m_fn = re.search(r'(\d{2})[\._](\d{2})[\._](\d{4})', filename)
        if m_fn:
            d, m, y = m_fn.groups()
            date_str = f"{y}-{m}-{d}"

    matches = {}
    current_sport = "FUDBAL"
    current_league = "FUDBAL"

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Sport detection
        upper = stripped.upper()
        if "FUDBAL" in upper:
            current_sport = "FUDBAL"
        elif any(s in upper for s in ["KOŠARKA", "KOSARKA", "TENIS", "HOKEJ", "RUKOMET"]):
            current_sport = "OTHER"

        if current_sport != "FUDBAL":
            continue

        # League header detection
        if ("Konačan ishod" in stripped or "KONAČAN ISHOD" in stripped) and len(stripped) < 160:
            m_lg = re.match(r'^\s*([A-ZŠĐČĆŽ0-9\s\-\.\/]+?)\s+(?:Konačan|KONAČAN)', line)
            if m_lg:
                lg = m_lg.group(1).strip()
                if lg and len(lg) > 2:
                    current_league = lg
            continue

        # Match row must start with optional day (3 letters), time (HH:MM), and match code (3-6 digits)
        m_start = re.match(r'^(?:([a-zšđčćž]{3})\s+)?(\d{1,2}:\d{2})\s+(\d{3,6})\s+', stripped)
        if not m_start:
            continue

        day_str, time_str, rbr = m_start.groups()
        rest = stripped[m_start.end():]

        # Tokenize rest of line without regex backtracking
        tokens = rest.split()
        team_tokens = []
        odds_tokens = []

        for tok in tokens:
            clean_tok = tok.replace(',', '.')
            if re.match(r'^\d+\.\d+$', clean_tok):
                odds_tokens.append(clean_tok)
            elif not odds_tokens:
                team_tokens.append(tok)

        if len(team_tokens) < 2 or len(odds_tokens) < 3:
            continue

        mid = len(team_tokens) // 2
        home = ' '.join(team_tokens[:mid])
        away = ' '.join(team_tokens[mid:])

        key = (date_str, rbr, home, away)
        if key not in matches:
            matches[key] = {
                "date": date_str,
                "time": time_str,
                "rbr": rbr,
                "league": current_league,
                "home_team": home,
                "away_team": away,
                "source_file": filename,
            }

        entry = matches[key]
        try:
            # Only set ft/dc/ht if not already set or if current values look like standard 1X2 / HT lines
            if len(odds_tokens) >= 3 and "ft_1" not in entry:
                o1, ox, o2 = float(odds_tokens[0]), float(odds_tokens[1]), float(odds_tokens[2])
                if 1.01 <= o1 <= 30.0 and 1.8 <= ox <= 12.0 and 1.01 <= o2 <= 30.0:
                    entry["ft_1"] = o1
                    entry["ft_x"] = ox
                    entry["ft_2"] = o2
            if len(odds_tokens) >= 6 and "dc_1x" not in entry:
                dc1x, dc12, dcx2 = float(odds_tokens[3]), float(odds_tokens[4]), float(odds_tokens[5])
                if 1.01 <= dc1x <= 6.0 and 1.01 <= dc12 <= 3.0 and 1.01 <= dcx2 <= 6.0:
                    entry["dc_1x"] = dc1x
                    entry["dc_12"] = dc12
                    entry["dc_x2"] = dcx2
            if len(odds_tokens) >= 9 and "ht_1" not in entry:
                h1, hx, h2 = float(odds_tokens[6]), float(odds_tokens[7]), float(odds_tokens[8])
                if 1.05 <= h1 <= 20.0 and 1.50 <= hx <= 4.50 and 1.05 <= h2 <= 20.0:
                    entry["ht_1"] = h1
                    entry["ht_x"] = hx
                    entry["ht_2"] = h2
            if len(odds_tokens) >= 12 and "sh_1" not in entry:
                s1, sx, s2 = float(odds_tokens[9]), float(odds_tokens[10]), float(odds_tokens[11])
                if 1.05 <= s1 <= 20.0 and 1.50 <= sx <= 4.50 and 1.05 <= s2 <= 20.0:
                    entry["sh_1"] = s1
                    entry["sh_x"] = sx
                    entry["sh_2"] = s2
        except Exception:
            pass

    return list(matches.values())


def run_full_pipeline(max_workers=8):
    os.makedirs(PDF_STORAGE_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    all_keys = enumerate_all_pdf_keys()
    logger.info(f"Starting parallel download and ingestion of {len(all_keys)} PDFs...")

    # Load existing CSV if available so we don't lose any already parsed records
    all_records = []
    if os.path.exists(OUTPUT_CSV):
        try:
            df_prev = pd.read_csv(OUTPUT_CSV)
            all_records = df_prev.to_dict('records')
            logger.info(f"Loaded {len(all_records)} existing records from {OUTPUT_CSV}")
        except Exception as e:
            logger.warning(f"Could not load previous CSV: {e}")

    downloaded_cnt = 0
    cached_cnt = 0
    failed_cnt = 0

    batch_size = 50
    for b_idx in range(0, len(all_keys), batch_size):
        batch_keys = all_keys[b_idx:b_idx + batch_size]
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            dl_futures = {executor.submit(download_single_pdf, k): k for k in batch_keys}
            for fut in as_completed(dl_futures):
                try:
                    res = fut.result()
                    st = res["status"]
                    if st == "downloaded":
                        downloaded_cnt += 1
                    elif st == "cached":
                        cached_cnt += 1
                    else:
                        failed_cnt += 1
                        continue

                    # Parse immediately with ultra-fast parser
                    recs = parse_pdf_to_records(res["path"], res.get("filename", ""))
                    if recs:
                        all_records.extend(recs)
                except Exception as e:
                    failed_cnt += 1
                    logger.warning(f"Batch item error: {e}")

        logger.info(
            f"Progress: [{min(b_idx + batch_size, len(all_keys))}/{len(all_keys)}] | "
            f"Downloaded: {downloaded_cnt} | Cached: {cached_cnt} | Failed: {failed_cnt} | "
            f"Parsed Matches: {len(all_records)}"
        )

        # Incremental save every 100 files
        if all_records and (b_idx % 100 == 0 or b_idx + batch_size >= len(all_keys)):
            df_temp = pd.DataFrame(all_records).drop_duplicates(
                subset=["date", "time", "home_team", "away_team", "league"]
            )
            df_temp.to_csv(OUTPUT_CSV, index=False)
            logger.info(f"Checkpoint saved: {len(df_temp)} unique matches persisted to {OUTPUT_CSV}")

    # Final save
    if all_records:
        df_final = pd.DataFrame(all_records).drop_duplicates(
            subset=["date", "time", "home_team", "away_team", "league"]
        )
        df_final.to_csv(OUTPUT_CSV, index=False)
        logger.info(f"✅ Ingestion Complete! Total unique matches: {len(df_final)}")
        ht_cnt = df_final["ht_1"].notna().sum() if "ht_1" in df_final.columns else 0
        logger.info(f"✅ Matches with Halftime Odds: {ht_cnt}")
    else:
        logger.warning("No records parsed.")


if __name__ == "__main__":
    run_full_pipeline(max_workers=8)
