# YTDL Studio — Apple Silicon

## หน้าจอใหม่: Dark Mode

ตัวเปิดปกติใช้ UI สีถ่านแบบด้านผ่าน pywebview / WebKit
ลดแสงและของตกแต่ง เน้นช่องลิงก์ รูปแบบไฟล์ และสถานะดาวน์โหลด
รัน `bash install_macos.command` อีกครั้งเพื่อเพิ่ม dependency ใหม่
จากนั้น `bash start_macos.command` หรือ build `.app` ใหม่
สคริปต์ build รวมโฟลเดอร์ `ui` และตรวจเปิดหน้าจอ WebKit จากแอปที่แพ็กแล้ว
ยังต้องทดสอบหน้าตาบน Mac จริงและสิทธิ์คลิปบอร์ด
หากปุ่มวางอ่านคลิปบอร์ดไม่ได้ ให้กด Command+V ในช่องลิงก์

การตรวจ Tk ด้านล่างใช้กับหน้าจอ classic ที่เก็บไว้เท่านั้น
UI หลักไม่ต้องใช้ Tk; preflight รุ่นใหม่ตรวจ WebKit แทน

โหมด **ภาพ** โหลดไฟล์ภาพโดยตรงและภาพจากโพสต์/อัลบั้มได้
รัน `bash install_macos.command` อีกครั้งเพื่อติดตั้ง gallery-dl ใน environment
สำหรับ `.app` ที่แพ็กแล้ว ติดตั้ง CLI แยกด้วย `brew install gallery-dl`
หรือ `pipx install gallery-dl` แล้วเปิดแอปใหม่ (ตัว build ไม่รวม gallery-dl)
ลิงก์ไฟล์ภาพโดยตรงใช้ได้โดยไม่ต้องมี gallery-dl
สถานะโลโก้จะเปลี่ยนตามโหมดที่เลือก บางแหล่งต้องใช้ cookies จากบัญชีของคุณ

สำหรับ Mac ชิป Apple Silicon ใช้ Python ARM64 แบบ native ไม่ใช้ Rosetta
โค้ดและสคริปต์เตรียมไว้แล้ว แต่ยังไม่ได้ทดสอบบน Mac จริงจากเครื่องพัฒนานี้

## เริ่มใช้งานบน Mac

1. คัดลอกหรือแตก ZIP โปรเจกต์ทั้งโฟลเดอร์ลงใน Mac รวมโฟลเดอร์ `assets`
2. ติดตั้ง **Python 3.12 ขึ้นไป แบบ macOS universal2** จาก https://www.python.org/downloads/macos/ แนะนำ 3.13 โดยใช้ตัวติดตั้งจาก python.org ซึ่งมี Tcl/Tk
3. เปิด `Install Certificates.command` ในโฟลเดอร์ Python ที่ติดตั้ง เพื่อเตรียมใบรับรอง HTTPS
4. เปิด Terminal พิมพ์ `cd ` แล้วลากโฟลเดอร์โปรเจกต์มาวาง จากนั้นกด Enter
5. รัน:

```bash
bash install_macos.command
bash start_macos.command
```

ตัวติดตั้งสร้าง `.venv-macos` แยกจาก Python ระบบ และตรวจ ARM64, Tk, โลโก้,
yt-dlp, curl-cffi และ FFmpeg ก่อนแจ้งว่าติดตั้งสำเร็จ หลังติดตั้งสามารถดับเบิลคลิก
`start_macos.command` ได้ ไม่ต้องใช้ไฟล์ `.bat`

หากมีหลาย Python ให้ระบุด้วย `YTDL_PYTHON=/path/to/python3 bash install_macos.command`
หากใช้ Homebrew ต้องติดตั้ง Tk ที่ตรงรุ่น Python เพิ่มเอง; ตัวติดตั้ง python.org สะดวกกว่า
อย่าคัดลอก `.venv-macos` จากเครื่องอื่น ให้ติดตั้งใหม่บน Mac เป้าหมาย

## สร้างแอป .app

ทำบน Mac Apple Silicon หลังติดตั้งสำเร็จ:

```bash
bash build_macos.command
```

ได้ `dist/<เวลาที่สร้าง>/YTDL Studio.app` และ `YTDL-Studio-macOS-arm64.zip`
ตัว build รวม Python, Tk, ตัวดึงข้อมูล, โลโก้ และ FFmpeg ARM64 แล้วรัน smoke test
จากแอปที่แพ็กจริงก่อนสร้าง ZIP ย้าย `.app` ไป Applications ได้
เครื่องปลายทางไม่ต้องติดตั้ง Python สำหรับตัว `.app` นี้

ไม่สามารถสร้าง macOS binary ด้วย PyInstaller บน Windows ได้ จึงยังไม่มี `.app`
ที่ build สำเร็จแนบมาจากเครื่องพัฒนานี้ สคริปต์ build ต้องรันบน Mac
แอปที่สร้างในเครื่องใช้ ad-hoc signing และยังไม่ได้ notarize; การแจกจ่ายสาธารณะ
ควรลงนาม Developer ID และ notarize กับ Apple เพิ่ม ไม่ต้องปิด Gatekeeper

## การใช้งานและข้อจำกัด

- ปุ่มเปิดโฟลเดอร์ใช้ Finder; ฟอนต์และการเลื่อนปรับสำหรับ Mac
- อ่าน cookies จากเบราว์เซอร์เฉพาะเมื่อเลือกใช้ macOS อาจขออนุญาต Keychain
- ไฟล์ cookies.txt แบบ Netscape เป็นอีกทางเลือก โดยไม่แก้ไขไฟล์ต้นฉบับ
- อัปเดตแบบ source ด้วย `bash install_macos.command`; แบบ .app ต้อง build ใหม่
- บางเว็บรวมถึง YouTube อาจต้องมี JavaScript runtime ที่ yt-dlp รองรับเพิ่มเติม
  และข้อกำหนดการล็อกอินขึ้นอยู่กับแต่ละเว็บ
- สถานะแพลตฟอร์มหมายถึงพบตัวดึงข้อมูล ไม่ใช่การยืนยันว่าดาวน์โหลดได้ทุกคลิป

## ตรวจรับบนเครื่องจริง

เปิด UI ตรวจข้อความไทยและโลโก้ทั้ง 11 แหล่ง ลองแทร็กแพด ปุ่มวางลิงก์
เลือกโฟลเดอร์ และเปิด Finder จากนั้นดาวน์โหลดคลิปที่มีสิทธิ์ใช้เป็น MP4 และ MP3
ทดสอบจาก `.app` อีกครั้งหลังย้ายไป Applications รวมกรณีเส้นทางมีช่องว่าง
การทดสอบ build อัตโนมัติไม่ดาวน์โหลดคลิปหรืออ่าน cookies ส่วนตัว
