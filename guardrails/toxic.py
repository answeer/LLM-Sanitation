import os
import sys
import io
import csv
import json
import time
import base64
import shutil
import zipfile
import hashlib
import logging
import mimetypes
import platform
import traceback
import subprocess
from datetime import datetime
from pathlib import Path

import requests
import py7zr

# ---------------------- CONFIG ----------------------
# >>>>> Fill these for your LLM API <<<<<
LLM_API_URL = "https://your-llm-api-endpoint.com/extract-metadata"
LLM_API_KEY = ""  # e.g. "Bearer xxx", leave empty if not needed
LLM_TIMEOUT_SECS = 300

# Prompt guiding the LLM (English, dynamic metadata, JSON-only)
LLM_PROMPT = """You are an Information Extraction assistant.

Task:
Given a contract document as Base64 (binary, could be a PDF converted from DOC/DOCX), extract as many metadata key-value pairs as possible from the content. 
Return a SINGLE valid JSON object (no commentary, no markdown). Keys must be English snake_case. 
Do not invent fields. Omit fields that do not exist. Normalize dates to YYYY-MM-DD if possible.

Examples of metadata (NOT exhaustive, do not limit yourself):
- contract_id, contract_name, parties, effective_date, expiration_date, governing_law, jurisdiction,
- signatures, contact_emails, payment_terms, termination_clause, confidentiality_clause,
- auto_renewal, renewal_terms, service_level, penalties, deliverables, pricing, currency, etc.
If clauses are present, include a "clauses" array of objects: [{ "title": "...", "text": "..." }].

Output strictly JSON only.

Input file info:
- file_name: {file_name}
- mime_type: {mime_type}
- base64_size: {b64_len} characters

Base64 payload:
{b64_payload}
"""

# File types we handle at top-level scan
ALLOWED_EXTS = {".pdf", ".doc", ".docx", ".png", ".jpg", ".jpeg", ".zip", ".7z"}

# ----------------------------------------------------

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

def detect_mime(path: str) -> str:
    ext = Path(path).suffix.lower()
    if ext == ".pdf":
        return "application/pdf"
    if ext == ".doc":
        return "application/msword"
    if ext == ".docx":
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    if ext in (".png",):
        return "image/png"
    if ext in (".jpg", ".jpeg"):
        return "image/jpeg"
    if ext == ".zip":
        return "application/zip"
    if ext == ".7z":
        return "application/x-7z-compressed"
    # fallback
    return mimetypes.guess_type(path)[0] or "application/octet-stream"

def sha256_of_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def file_to_base64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def ensure_dir(p: Path):
    p.parent.mkdir(parents=True, exist_ok=True)

def safe_json_filename(output_folder: Path, src_path: Path) -> Path:
    """
    Use base name as stem; if collision, append 8-char hash of full path.
    Always .json extension.
    """
    stem = src_path.stem
    cand = output_folder / f"{stem}.json"
    if not cand.exists():
        return cand
    short = hashlib.sha1(str(src_path).encode("utf-8")).hexdigest()[:8]
    return output_folder / f"{stem}__{short}.json"

def get_file_type(path: str) -> str:
    ext = Path(path).suffix.lower()
    if ext == ".pdf":
        return "pdf"
    if ext in (".doc", ".docx"):
        return "word"
    if ext in (".png", ".jpg", ".jpeg"):
        return "image"
    if ext == ".zip":
        return "zip"
    if ext == ".7z":
        return "7z"
    return "other"

# ---------- DOC/DOCX -> PDF converters (best-effort multi-backend) ----------

def word_to_pdf_with_pandoc(src: str, dst_pdf: str) -> bool:
    try:
        import pypandoc  # imported lazily to avoid hard dependency if not used
        pypandoc.convert_file(src, "pdf", outputfile=dst_pdf)
        return Path(dst_pdf).exists()
    except Exception as e:
        logging.debug(f"Pandoc conversion failed: {e}")
        return False

def word_to_pdf_with_soffice(src: str, dst_pdf: str) -> bool:
    """
    Requires LibreOffice/OpenOffice 'soffice' in PATH.
    We'll let soffice write to output dir, then move the produced PDF.
    """
    try:
        out_dir = str(Path(dst_pdf).parent)
        cmd = [
            "soffice", "--headless", "--convert-to", "pdf", "--outdir", out_dir, src
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # LibreOffice outputs as <src_stem>.pdf under out_dir
        produced = Path(out_dir) / (Path(src).stem + ".pdf")
        if produced.exists():
            if Path(dst_pdf) != produced:
                shutil.move(str(produced), dst_pdf)
            return True
        return False
    except Exception as e:
        logging.debug(f"soffice conversion failed: {e}")
        return False

def word_to_pdf_with_win32com(src: str, dst_pdf: str) -> bool:
    """
    Windows-only: requires MS Word + pywin32
    """
    if platform.system().lower() != "windows":
        return False
    try:
        import win32com.client  # type: ignore
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False
        doc = word.Documents.Open(str(Path(src).resolve()))
        # 17 = wdFormatPDF
        doc.SaveAs(str(Path(dst_pdf).resolve()), FileFormat=17)
        doc.Close(False)
        word.Quit()
        return Path(dst_pdf).exists()
    except Exception as e:
        logging.debug(f"win32com conversion failed: {e}")
        return False

def convert_word_to_pdf(src: str, dst_pdf: str) -> bool:
    """
    Try multiple backends: pandoc -> soffice -> win32com (Windows).
    """
    Path(dst_pdf).parent.mkdir(parents=True, exist_ok=True)
    if word_to_pdf_with_pandoc(src, dst_pdf):
        return True
    if word_to_pdf_with_soffice(src, dst_pdf):
        return True
    if word_to_pdf_with_win32com(src, dst_pdf):
        return True
    return False

# --------------------------- Archive helpers ---------------------------

def _safe_join(base: Path, *paths) -> Path:
    # prevent path traversal when extracting
    final = base.joinpath(*paths).resolve()
    if base not in final.parents and final != base:
        raise RuntimeError("Unsafe path detected during extraction")
    return final

def extract_zip_safe(zip_path: str, to_dir: Path) -> list[str]:
    extracted = []
    with zipfile.ZipFile(zip_path, "r") as zf:
        for m in zf.infolist():
            if m.is_dir():
                continue
            target = _safe_join(to_dir, m.filename)
            ensure_dir(target)
            with zf.open(m) as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst)
            extracted.append(str(target))
    return extracted

def extract_7z_safe(sevenz_path: str, to_dir: Path) -> list[str]:
    extracted = []
    with py7zr.SevenZipFile(sevenz_path, mode="r") as z:
        z.extractall(path=str(to_dir))
    # collect files
    for root, _, files in os.walk(to_dir):
        for f in files:
            extracted.append(str(Path(root) / f))
    return extracted

# --------------------------- LLM call ---------------------------

def call_llm_api(file_name: str, mime_type: str, b64_payload: str) -> dict:
    prompt = LLM_PROMPT.format(
        file_name=file_name,
        mime_type=mime_type,
        b64_len=len(b64_payload),
        b64_payload=b64_payload
    )
    headers = {"Content-Type": "application/json"}
    if LLM_API_KEY:
        headers["Authorization"] = LLM_API_KEY

    resp = requests.post(
        LLM_API_URL,
        headers=headers,
        json={"prompt": prompt},
        timeout=LLM_TIMEOUT_SECS
    )
    resp.raise_for_status()
    # Expect the service to return already-parsed JSON (dict) or a string JSON
    try:
        data = resp.json()
        if isinstance(data, dict):
            return data
        if isinstance(data, str):
            return json.loads(data)
    except Exception:
        # Last resort: try to parse raw text
        txt = resp.text.strip()
        return json.loads(txt)
    return {}

# --------------------------- CSV checkpointing ---------------------------

def load_processed_from_csv(csv_path: Path) -> set[str]:
    processed = set()
    if not csv_path.exists():
        return processed
    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Only skip rows that previously succeeded
            if row.get("status") == "success":
                processed.add(row.get("file_path", ""))
    return processed

def append_csv_row(csv_path: Path, row: dict, write_header_if_needed=True):
    file_exists = csv_path.exists()
    with open(csv_path, "a", encoding="utf-8", newline="") as f:
        writer = None
        fieldnames = [
            "timestamp_start", "timestamp_end", "file_path", "payload_path",
            "output_json_path", "status", "error_message", "method",
            "payload_mime", "payload_size_bytes", "payload_sha256"
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if write_header_if_needed and not file_exists:
            writer.writeheader()
        writer.writerow(row)
        f.flush()  # ensure durability

# --------------------------- Core processing ---------------------------

def process_single_file(
    src_path: str,
    output_folder: Path,
    csv_path: Path,
    temp_folder: Path
):
    start_ts = datetime.utcnow().isoformat()
    src = Path(src_path)
    ftype = get_file_type(src_path)
    method = ""
    payload_path = None
    out_json_path = None
    error_msg = ""
    status = "success"
    payload_mime = ""
    payload_sha = ""
    payload_size = 0

    try:
        if ftype == "pdf":
            method = "pdf_base64"
            payload_path = src

        elif ftype == "word":
            method = "word_to_pdf_base64"
            # convert to temp PDF
            tmp_pdf = temp_folder / (src.stem + ".pdf")
            ok = convert_word_to_pdf(str(src), str(tmp_pdf))
            if not ok or not tmp_pdf.exists():
                raise RuntimeError("DOC/DOCX to PDF conversion failed (pandoc/soffice/win32com not available or failed).")
            payload_path = tmp_pdf

        elif ftype == "image":
            method = "image_base64"
            payload_path = src

        elif ftype in ("zip", "7z"):
            # extract and recursively process
            method = f"{ftype}_expand"
            sub_dir = temp_folder / (src.stem + "_extracted")
            sub_dir.mkdir(parents=True, exist_ok=True)
            if ftype == "zip":
                inner_files = extract_zip_safe(str(src), sub_dir)
            else:
                inner_files = extract_7z_safe(str(src), sub_dir)
            # Recurse on extracted files
            for inner in inner_files:
                # Only handle allowed extensions; archives may contain many
                if Path(inner).suffix.lower() in ALLOWED_EXTS:
                    process_single_file(inner, output_folder, csv_path, temp_folder)
            # For the archive itself we don't create a JSON; it's a container.
            return

        else:
            method = "skip_unsupported"
            raise RuntimeError(f"Unsupported file type: {src.suffix}")

        # Prepare payload
        payload_mime = detect_mime(str(payload_path))
        payload_sha = sha256_of_file(str(payload_path))
        payload_size = Path(payload_path).stat().st_size
        b64_payload = file_to_base64(str(payload_path))

        # Call LLM
        result = call_llm_api(src.name, payload_mime, b64_payload)
        # augment minimal context
        result = result if isinstance(result, dict) else {}
        result["_source_file_path"] = str(src.resolve())
        result["_payload_file_path"] = str(Path(payload_path).resolve())
        result["_payload_mime"] = payload_mime
        result["_payload_sha256"] = payload_sha
        result["_payload_size_bytes"] = payload_size

        # Save JSON (per input file, same name; add short-hash on collision)
        out_json_path = safe_json_filename(output_folder, src)
        ensure_dir(out_json_path)
        with open(out_json_path, "w", encoding="utf-8") as jf:
            json.dump(result, jf, ensure_ascii=False, indent=2)

    except Exception as e:
        status = "error"
        error_msg = f"{e}\n{traceback.format_exc()}"

    end_ts = datetime.utcnow().isoformat()

    # Append 1 line to CSV immediately
    row = {
        "timestamp_start": start_ts,
        "timestamp_end": end_ts,
        "file_path": str(src.resolve()),
        "payload_path": "" if payload_path is None else str(Path(payload_path).resolve()),
        "output_json_path": "" if out_json_path is None else str(out_json_path.resolve()),
        "status": status,
        "error_message": error_msg,
        "method": method,
        "payload_mime": payload_mime,
        "payload_size_bytes": payload_size,
        "payload_sha256": payload_sha,
    }
    append_csv_row(csv_path, row)

def should_process(file_path: str, processed_success: set[str]) -> bool:
    # Skip if already processed successfully (exact absolute path match)
    try:
        return str(Path(file_path).resolve()) not in processed_success
    except Exception:
        return file_path not in processed_success

def scan_files(root: str) -> list[str]:
    paths = []
    for r, _, files in os.walk(root):
        for name in files:
            p = str(Path(r) / name)
            if Path(p).suffix.lower() in ALLOWED_EXTS:
                paths.append(p)
    return paths

def main():
    setup_logging()
    if len(sys.argv) < 3:
        print("Usage: python extract_contract_metadata.py <input_folder> <output_folder> [checkpoint_csv]")
        sys.exit(1)

    input_folder = Path(sys.argv[1]).resolve()
    output_folder = Path(sys.argv[2]).resolve()
    csv_path = Path(sys.argv[3]).resolve() if len(sys.argv) >= 4 else (output_folder / "output_metadata.csv")

    if not input_folder.exists():
        print(f"Input folder not found: {input_folder}")
        sys.exit(1)

    output_folder.mkdir(parents=True, exist_ok=True)
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    # Load processed-success set for resume
    processed_success = load_processed_from_csv(csv_path)
    logging.info(f"Loaded {len(processed_success)} previously succeeded files from CSV.")

    # Scan for files
    files = scan_files(str(input_folder))
    logging.info(f"Discovered {len(files)} candidate files.")

    # temp workspace
    temp_folder = output_folder / "_tmp_work"
    temp_folder.mkdir(parents=True, exist_ok=True)

    # Process
    for idx, f in enumerate(files, 1):
        if not should_process(f, processed_success):
            continue
        logging.info(f"[{idx}/{len(files)}] Processing: {f}")
        process_single_file(f, output_folder, csv_path, temp_folder)

    logging.info("Done.")

if __name__ == "__main__":
    main()
