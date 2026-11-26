"""
Waghor Auto-Print Agent (Windows)
---------------------------------
- ตรวจสอบคิวพิมพ์จาก Google Apps Script Web App ทุกๆ POLL_INTERVAL_SECONDS วินาที
- เช็กสถานะเครื่องปริ้นบน Windows ก่อนสั่งพิมพ์ หากเครื่องปริ้นปิด/ออฟไลน์ จะคงสถานะคิวไว้เป็น PENDING
- เมื่อเครื่องปริ้นพร้อม จะดาวน์โหลด PDF ชั่วคราวจาก Apps Script สั่งพิมพ์เงียบเข้าเครื่องปริ้น
  แล้วแจ้ง Apps Script เปลี่ยนสถานะเป็น PRINTED และลบไฟล์ PDF ชั่วคราวทิ้งทันที
"""

import base64
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from pathlib import Path

# ================= ตั้งค่าก่อนใช้งาน =================
# 1. วาง URL ของ Web App ที่ได้จากการ Deploy Google Apps Script
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbwcUeTiWoxetMbZHburOufSYC99Mp746wqmr5hkYD2dlrkLk14oqRaZ94WJD9kdSEnblw/exec"

# 2. รหัสลับต้องตรงกับ CONFIG.PRINT_API_KEY ในไฟล์ Code.gs
PRINT_API_KEY = "WAGHOR-PRINT-2026-SECRET"

# 3. ชื่อเครื่องปริ้นใน Windows (เว้นว่าง "" เพื่อใช้เครื่องปริ้น Default ของ Windows)
PRINTER_NAME = "Brother DCP-T220 Printer"

# 4. ที่อยู่ของ SumatraPDF.exe สำหรับสั่งพิมพ์เงียบ (แนะนำให้โหลด SumatraPDF Portable มาวางโฟลเดอร์เดียวกับสคริปต์นี้)
SUMATRA_PDF_PATH = str(Path(__file__).parent / "SumatraPDF.exe")

# 5. ความถี่ในการเช็กคิวพิมพ์ (วินาที)
POLL_INTERVAL_SECONDS = 15
# ===================================================


def api_get(params: dict) -> dict:
    params["key"] = PRINT_API_KEY
    query = urllib.parse.urlencode(params)
    url = f"{WEB_APP_URL}?{query}"
    req = urllib.request.Request(url, headers={"User-Agent": "WaghorPrintAgent/1.0"})
    with urllib.request.urlopen(req, timeout=45) as resp:
        raw = resp.read().decode("utf-8")
        return json.loads(raw)


def get_target_printer_status() -> tuple[bool, str, str]:
    """
    ตรวจสอบสถานะเครื่องปริ้นบน Windows ผ่าน PowerShell (ไม่ต้องลงไลบรารีเสริม)
    คืนค่า: (พร้อมพิมพ์หรือไม่, ชื่อเครื่องปริ้น, สถานะข้อความ)
    """
    if os.name != "nt":
        return False, PRINTER_NAME or "Unknown", "รองรับการพิมพ์อัตโนมัติบน Windows เท่านั้น"

    if PRINTER_NAME:
        ps_cmd = (
            f"Get-Printer -Name '{PRINTER_NAME}' -ErrorAction SilentlyContinue | "
            "Select-Object Name, PrinterStatus, WorkOffline | ConvertTo-Json -Compress"
        )
    else:
        ps_cmd = (
            "$def = (Get-CimInstance Win32_Printer | Where-Object { $_.Default -eq $true } | Select-Object -First 1); "
            "if ($def) { Get-Printer -Name $def.Name | Select-Object Name, PrinterStatus, WorkOffline | ConvertTo-Json -Compress }"
        )

    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            capture_output=True,
            text=True,
            timeout=15,
        )
        out = (res.stdout or "").strip()
        if not out:
            return False, PRINTER_NAME or "Default", "ไม่พบเครื่องปริ้นที่กำหนด"

        info = json.loads(out)
        name = info.get("Name", PRINTER_NAME)
        status = str(info.get("PrinterStatus", ""))
        work_offline = bool(info.get("WorkOffline", False))

        # สถานะที่ไม่พร้อมพิมพ์ (Offline, Error, PaperOut, DoorOpen, Paused ฯลฯ)
        blocked_keywords = ("Offline", "Error", "Paper", "Paused", "NotAvailable", "UserIntervention")
        if work_offline or any(k.lower() in status.lower() for k in blocked_keywords):
            return False, name, f"เครื่องปริ้นไม่พร้อม ({status}, Offline={work_offline})"

        return True, name, f"พร้อมพิมพ์ ({status})"
    except Exception as exc:
        return False, PRINTER_NAME or "Default", f"ตรวจสอบเครื่องปริ้นไม่ได้: {exc}"


def prepare_printable_pdf(pdf_bytes: bytes) -> str:
    """
    เรนเดอร์หน้าแรกของ PDF ให้เป็น Raster PDF 300 DPI คมชัดสูงผ่าน Chromium PDFium Engine
    แก้ปัญหาไดรเวอร์เครื่องพิมพ์ Brother DCP แทนที่ฟอนต์ Sarabun ด้วยฟอนต์หนาขนาดใหญ่ 18-22
    ทำให้ตัวอักษร, ขอบ, ตาราง, ขนาด ออกมาตรงกับหน้า Google Doc 100% และอยู่หน้าเดียวเสมอ
    """
    fd, out_path = tempfile.mkstemp(suffix=".pdf", prefix="waghor_repair_raster_")
    os.close(fd)

    try:
        import pypdfium2 as pdfium
        from PIL import Image

        doc = pdfium.PdfDocument(pdf_bytes)
        pil_images = []
        for page in doc:
            img = page.render(scale=300 / 72).to_pil()
            if img.mode != "RGB":
                img = img.convert("RGB")
            pil_images.append(img)
        doc.close()

        if pil_images:
            pil_images[0].save(
                out_path,
                "PDF",
                resolution=300,
                save_all=True,
                append_images=pil_images[1:]
            )
        return out_path
    except Exception as exc:
        print(f"[WARN] Rasterize PDF ไม่สำเร็จ ({exc}) -> ใช้ PDF ต้นฉบับ")
        with open(out_path, "wb") as f:
            f.write(pdf_bytes)
        return out_path


def print_pdf_silent(pdf_path: str, printer_name: str) -> None:
    """สั่งพิมพ์ PDF แบบเงียบ (แนะนำ SumatraPDF.exe)"""
    if os.path.exists(SUMATRA_PDF_PATH):
        cmd = [
            SUMATRA_PDF_PATH,
            "-print-to", printer_name,
            "-print-settings", "noscale,paper=A4",
            "-silent",
            pdf_path,
        ]
        subprocess.run(cmd, check=True, timeout=60)
    else:
        # Fallback: ใช้คำสั่งพิมพ์ของ Windows (ต้องมีโปรแกรมอ่าน PDF เช่น Edge/Acrobat เป็นค่าเริ่มต้น)
        os.startfile(pdf_path, "print")
        time.sleep(8)


def process_pending_jobs() -> None:
    resp = api_get({"action": "queue"})
    if not resp.get("ok"):
        print(f"[ERROR] ดึงคิวไม่สำเร็จ: {resp.get('error')}")
        return

    jobs = resp.get("jobs", [])
    if not jobs:
        return

    print(f"[QUEUE] พบคิวรอพิมพ์ {len(jobs)} รายการ -> กำลังตรวจสอบสถานะเครื่องปริ้น...")
    ready, printer_name, status_msg = get_target_printer_status()
    if not ready:
        print(f"[WAIT] {printer_name}: {status_msg} (เก็บคิวรอไว้จนกว่าเครื่องปริ้นจะพร้อม)")
        return

    print(f"[PRINTER] {printer_name}: {status_msg}")

    for job in jobs:
        job_id = job["jobId"]
        doc_id = job["docId"]
        doc_title = job.get("docTitle", job_id)
        print(f"[PRINTING] กำลังดึงและพิมพ์: {doc_title} ({job_id})")

        tmp_pdf = None
        try:
            pdf_resp = api_get({"action": "pdf", "docId": doc_id})
            if not pdf_resp.get("ok"):
                print(f"[ERROR] โหลด PDF ไม่สำเร็จ ({job_id}): {pdf_resp.get('error')}")
                continue

            pdf_bytes = base64.b64decode(pdf_resp["pdfBase64"])
            tmp_pdf = prepare_printable_pdf(pdf_bytes)

            print_pdf_silent(tmp_pdf, printer_name)

            mark_resp = api_get({
                "action": "markPrinted",
                "jobId": job_id,
                "printer": printer_name,
            })
            if mark_resp.get("ok"):
                print(f"[DONE] พิมพ์สำเร็จและอัปเดตคิวแล้ว: {job_id}")
            else:
                print(f"[WARN] พิมพ์แล้วแต่อัปเดตสถานะไม่สำเร็จ: {mark_resp.get('error')}")
        except Exception as exc:
            print(f"[ERROR] เกิดข้อผิดพลาดระหว่างพิมพ์ {job_id}: {exc}")
        finally:
            if tmp_pdf and os.path.exists(tmp_pdf):
                try:
                    os.remove(tmp_pdf)
                except OSError:
                    pass


def main() -> None:
    if "วาง_DEPLOYMENT_ID_ที่นี่" in WEB_APP_URL:
        print("กรุณาแก้ไขตัวแปร WEB_APP_URL ในไฟล์ waghor_print_agent.py ก่อนใช้งาน")
        sys.exit(1)

    print("=== Waghor Auto-Print Agent เริ่มทำงาน ===")
    print(f"ตรวจสอบคิวทุก {POLL_INTERVAL_SECONDS} วินาที | กด Ctrl+C เพื่อหยุด")
    while True:
        try:
            process_pending_jobs()
        except Exception as exc:
            print(f"[NETWORK/RETRY] เชื่อมต่อไม่ได้ชั่วคราว ({exc}) จะลองใหม่รอบถัดไป...")
        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
