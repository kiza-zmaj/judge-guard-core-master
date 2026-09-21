"""
Mozzart PDF Downloader
Fetches complete catalog from public S3 bucket and downloads all
'Dnevna ponuda' PDF files with date extraction from filename.
"""

import logging
import os
import re
import time
import urllib.parse
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import requests

logger = logging.getLogger("Mozzart.Downloader")

S3_BASE = "https://adminko.s3.eu-west-3.amazonaws.com"
S3_BUCKET_URL = f"{S3_BASE}/?prefix=documents/pdfs/&list-type=2&max-keys=1000"
PDF_BASE = f"{S3_BASE}/documents/pdfs"

# Regex patterns for date extraction from filename
DATE_PATTERNS = [
    r"(\d{2})\.(\d{2})\.(\d{4})\.",   # DD.MM.YYYY.
    r"(\d{2})\.(\d{2})\.(\d{4})",     # DD.MM.YYYY
    r"(\d{4})(\d{2})(\d{2})",         # YYYYMMDD
]


def parse_date_from_filename(filename: str) -> datetime | None:
    """Extract date from Mozzart PDF filename."""
    name = os.path.basename(filename)
    for pat in DATE_PATTERNS:
        m = re.search(pat, name)
        if m:
            g = m.groups()
            try:
                if len(g[0]) == 4:  # YYYYMMDD
                    return datetime(int(g[0]), int(g[1]), int(g[2]))
                else:  # DD.MM.YYYY
                    return datetime(int(g[2]), int(g[1]), int(g[0]))
            except ValueError:
                continue
    return None


def get_s3_catalog() -> list[dict]:
    """
    Fetches full S3 bucket listing and returns all 'Dnevna ponuda' PDFs
    with parsed dates.
    """
    logger.info("Fetching S3 catalog from Mozzart bucket...")
    all_entries = []
    continuation_token = None

    while True:
        url = S3_BUCKET_URL
        if continuation_token:
            url += f"&continuation-token={urllib.parse.quote(continuation_token)}"

        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
        except Exception as e:
            logger.error(f"S3 catalog fetch failed: {e}")
            break

        root = ET.fromstring(resp.text)
        ns = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}

        keys = root.findall(".//s3:Key", ns) or root.findall(".//Key")
        for k in keys:
            key = k.text or ""
            if not key.endswith(".pdf"):
                continue
            filename = key.replace("documents/pdfs/", "")
            # Only Dnevna ponuda files
            if "dnevna" not in filename.lower() and "Dnevna" not in filename:
                continue

            date_obj = parse_date_from_filename(filename)
            encoded = urllib.parse.quote(filename)
            all_entries.append({
                "s3_key": key,
                "filename": filename,
                "url": f"{PDF_BASE}/{encoded}",
                "date": date_obj,
                "date_str": date_obj.strftime("%Y-%m-%d") if date_obj else "unknown",
            })

        # Check for pagination
        is_truncated = root.find(".//s3:IsTruncated", ns) or root.find(".//IsTruncated")
        next_token = root.find(".//s3:NextContinuationToken", ns) or root.find(".//NextContinuationToken")

        if is_truncated is not None and is_truncated.text == "true" and next_token is not None:
            continuation_token = next_token.text
        else:
            break

    # Sort by date
    all_entries.sort(key=lambda x: x["date"] or datetime.min)
    logger.info(f"Found {len(all_entries)} Dnevna ponuda PDFs in S3 catalog.")
    return all_entries


def download_pdf(entry: dict, output_dir: str, overwrite: bool = False) -> dict:
    """Download a single PDF, returns status dict."""
    safe_name = re.sub(r'[^\w\-_\.]', '_', entry["filename"])
    out_path = os.path.join(output_dir, f"{entry['date_str']}_{safe_name}")

    if not overwrite and os.path.exists(out_path):
        size = os.path.getsize(out_path)
        if size > 10_000:  # Valid PDF > 10KB
            return {"status": "cached", "path": out_path, "entry": entry}

    try:
        resp = requests.get(entry["url"], timeout=30, stream=True)
        resp.raise_for_status()
        with open(out_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=65536):
                f.write(chunk)
        size = os.path.getsize(out_path)
        return {"status": "downloaded", "path": out_path, "size": size, "entry": entry}
    except Exception as e:
        return {"status": "error", "error": str(e), "path": out_path, "entry": entry}


def download_all(
    output_dir: str,
    workers: int = 6,
    overwrite: bool = False,
    date_from: str | None = None,
    date_to: str | None = None,
) -> list[dict]:
    """
    Download all Dnevna ponuda PDFs to output_dir.
    Optional date filtering: date_from/date_to in 'YYYY-MM-DD' format.
    Returns list of result dicts.
    """
    os.makedirs(output_dir, exist_ok=True)
    catalog = get_s3_catalog()

    # Date filtering
    if date_from:
        df = datetime.strptime(date_from, "%Y-%m-%d")
        catalog = [e for e in catalog if e["date"] and e["date"] >= df]
    if date_to:
        dt = datetime.strptime(date_to, "%Y-%m-%d")
        catalog = [e for e in catalog if e["date"] and e["date"] <= dt]

    logger.info(f"Downloading {len(catalog)} PDFs to {output_dir} (workers={workers})")

    results = []
    downloaded = cached = errors = 0

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(download_pdf, entry, output_dir, overwrite): entry
            for entry in catalog
        }
        for i, future in enumerate(as_completed(futures), 1):
            result = future.result()
            results.append(result)
            status = result["status"]
            if status == "downloaded":
                downloaded += 1
            elif status == "cached":
                cached += 1
            else:
                errors += 1
                logger.warning(f"Error: {result.get('error')} — {result['entry']['filename']}")

            if i % 25 == 0 or i == len(catalog):
                logger.info(
                    f"Progress: {i}/{len(catalog)} | "
                    f"Downloaded: {downloaded} | Cached: {cached} | Errors: {errors}"
                )
            time.sleep(0.05)  # polite rate limiting

    logger.info(
        f"Complete. Downloaded: {downloaded}, Cached: {cached}, Errors: {errors}"
    )
    return results


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "/tmp/mozzart_pdfs_all"
    download_all(out, workers=6, date_from="2022-01-01")
