# คู่มือติดตั้งระบบแจ้งซ่อมออนไลน์ + พิมพ์อัตโนมัติ (หว้ากอ)

## 1. ไฟล์และโฟลเดอร์ที่เตรียมไว้ให้บน Google Drive แล้ว
- **Google Sheets (ปลายทางเก็บข้อมูล + คิวพิมพ์):** `1k47ZtI4e4PMCZO7-VqouOFpVTgEyZHezY0j87bgD1w8` (`รายการแจ้งซ่อม`)
- **แม่แบบใบแจ้งซ่อม (Template Doc):** `1FmRIg-RrLkNWMWv9Dv8b_g1dr0cdEGq3kgiqaqzJuLY` (`Template_ใบแจ้งซ่อม`)
- **โฟลเดอร์เก็บใบแจ้งซ่อม (เฉพาะ Google Doc):** `1_zNg4ILVpf1ATLF-hOZopfK2Cmhn4gVv` (`เอกสารใบแจ้งซ่อม (Doc)`)

*(รหัส ID ทั้งหมดถูกใส่ไว้ในไฟล์ `Code.gs` เรียบร้อยแล้ว ไม่ต้องแก้เพิ่ม)*

---

## 2. ขั้นตอนติดตั้งฝั่ง Google Apps Script (Web App)
1. เปิดไฟล์ Google Sheets **รายการแจ้งซ่อม**
2. ไปที่เมนู **ส่วนขยาย (Extensions) > Apps Script**
3. ในไฟล์ `Code.gs` ให้ลบโค้ดเดิมออก แล้ววางโค้ดจากไฟล์ `Code.gs` ที่สร้างให้
4. กดปุ่ม `+` ข้างคำว่า **Files** เลือก **HTML** ตั้งชื่อว่า `index` (ระบบจะได้ `index.html`) แล้ววางโค้ดจากไฟล์ `index.html`
5. กด **บันทึก (Ctrl+S)**
6. กดปุ่ม **ทำให้ใช้งานได้ (Deploy) > การทำให้ใช้งานได้รายการใหม่ (New deployment)**
   - ประเภท: **เว็บแอป (Web app)**
   - ดำเนินการในชื่อ (Execute as): **ฉัน (Me)**
   - ผู้ที่มีสิทธิ์เข้าถึง (Who has access): **ทุกคน (Anyone)**
7. กด **Deploy** และอนุญาตสิทธิ์ (Authorize access) จากนั้น **คัดลอก Web App URL** เก็บไว้ (URL นี้ใช้ส่งให้เจ้าหน้าที่กรอกฟอร์ม และนำไปใส่ในสคริปต์เครื่องปริ้น)

---

## 3. ขั้นตอนติดตั้งฝั่งเครื่องคอมพิวเตอร์ที่ต่อเครื่องปริ้น (Windows)
1. สร้างโฟลเดอร์บนคอม เช่น `C:\WaghorPrintAgent\` แล้วนำไฟล์ `waghor_print_agent.py` ไปวางไว้
2. *(แนะนำเพื่อการพิมพ์เงียบที่เสถียรที่สุด)* ดาวน์โหลด **SumatraPDF (Portable 64-bit)** แตกไฟล์แล้วนำ `SumatraPDF.exe` มาวางไว้ในโฟลเดอร์ `C:\WaghorPrintAgent\` คู่กัน
3. เปิดไฟล์ `waghor_print_agent.py` แก้ไข 2 จุดด้านบน:
   - `WEB_APP_URL`: วาง Web App URL ที่ได้จากข้อ 2
   - `PRINTER_NAME`: ใส่ชื่อเครื่องปริ้นใน Windows (หรือปล่อยว่าง `""` เพื่อใช้ Default Printer)
4. ทดสอบรันผ่าน Command Prompt:
   ```cmd
   python C:\WaghorPrintAgent\waghor_print_agent.py
   ```
5. **ตั้งให้เปิดทำงานอัตโนมัติเมื่อเปิดเครื่องคอม (รองรับคิวค้างเมื่อคอม/เครื่องปริ้นดับ):**
   - กด `Win + R` พิมพ์ `shell:startup` แล้วกด Enter
   - สร้างไฟล์ `start_print_agent.bat` ไว้ในโฟลเดอร์นั้น โดยใส่คำสั่ง:
     ```bat
     @echo off
     start /min "" pythonw "C:\WaghorPrintAgent\waghor_print_agent.py"
     ```
   - เมื่อคอมดับหรือเครื่องปริ้นปิด รายการแจ้งซ่อมใหม่จะถูกเก็บค้างไว้ในแท็บ `PrintQueue` (สถานะ `PENDING`) และทันทีที่เปิดคอม/เปิดเครื่องปริ้น ระบบจะดึงคิวที่ค้างอยู่มาพิมพ์ให้ครบทุกใบอัตโนมัติครับ
