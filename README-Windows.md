# NÜVEL Studio — Windows x64

> สถานะ 2026-10-31: build ใหม่ต้องกำหนด `NUVEL_FFMPEG_BUNDLE` เป็น FFmpeg แบบ
> LGPL ที่มี source/build materials ไม่ใช้ GPL binary จาก imageio ในแพ็กใหม่
> ยังไม่มี LGPL binary ของ Windows ที่ตรวจจริงในรอบนี้ ดู [ข้อกำหนด](legal/FFMPEG-LGPL.md)
> และ [ผลตรวจ](legal/AUDIT.md) แอปเดิมยังไม่ถูกแทนที่

## สถานะซอร์สและ binary

ขณะนี้ **ไม่มี binary สำหรับ Windows หรือ macOS ให้ดาวน์โหลด** และยังไม่อนุมัติ
การแจกแพ็กเกจ โค้ดต้นฉบับที่อยู่ในขอบเขตของโปรเจกต์ใช้ **GPL-3.0-only**
ส่วน dependency และ assets ของบุคคลที่สามยังใช้ license ของตนเอง
ดู [LICENSE](LICENSE), [COPYRIGHT](COPYRIGHT) และ [third-party notices](THIRD_PARTY_NOTICES.md)

เก็บ tags และ release entries เดิมไว้เพื่ออ้างอิงประวัติ ไม่ใช่แพ็กเกจพร้อมติดตั้ง
ซอร์ส ZIP ที่ GitHub สร้างอัตโนมัติก็ไม่ใช่ตัวแอป ดู
[สถานะการแจกจ่าย](README.md#source-availability-and-historical-releases)
ตัวอัปเดตในแอปยังคงอยู่สำหรับสำเนาที่ติดตั้งไว้ แต่ไม่มีแพ็กเกจอัปเดตแจกในขณะนี้

ขั้นตอนด้านล่างเป็นการพัฒนาในเครื่อง การแพ็กยังต้องมี LGPL FFmpeg พร้อม source/
build materials ที่ผ่านการตรวจ และต้องผ่านข้อกำหนดอื่นก่อนจะแจก binary ได้

## เริ่มใช้งาน

1. ติดตั้ง Python 3.10+ แบบ x64 และเลือก Add Python to PATH
2. ดับเบิลคลิก **build_windows.bat** ระบบเตรียม environment และส่วนประกอบให้เอง
3. เมื่อ build สำเร็จ เปิด shortcut **NÜVEL Studio** ในโฟลเดอร์โปรเจกต์

แอปที่แพ็กเปิดโดยไม่มี Console และรวม Python, UI, yt-dlp และ FFmpeg ไว้แล้ว
ไฟล์โปรแกรมอยู่ใน `nuvel-windows` อย่าแยก `.exe` ออกจากโฟลเดอร์ `_internal`
Windows ต้องมี Microsoft Edge WebView2 Runtime

ชื่อหลักคือ `nuvel-windows/NÜVEL Studio.exe` และ `NÜVEL Studio.lnk`
รุ่น 2.0 ใช้ชื่อและ product ID ใหม่ทั้งหมด ต้องติดตั้งแพ็กเกจใหม่นี้หนึ่งครั้ง
แล้วตั้งค่าการเข้าถึง GitHub อีกครั้งก่อนใช้อัปเดตในแอป

ZIP ที่สร้างในเครื่องอยู่ใน `dist/windows-<เวลาที่ build>` ยังไม่ใช่แพ็กเกจที่โครงการรับรองสำหรับเผยแพร่
เครื่องปลายทางไม่ต้องติดตั้ง Python แต่ยังต้องมี WebView2 Runtime
ภาพจากโพสต์ใช้ gallery-dl CLI ที่แพ็กเป็นโปรเซสแยกไปด้วยแล้ว
เครื่องปลายทางไม่ต้องติดตั้ง CLI เอง ลิงก์ไฟล์ภาพโดยตรงใช้ตัวดาวน์โหลดในแอป

## อัปเดต

ปิดแอปและรอให้งานดาวน์โหลดจบ แล้วดับเบิลคลิก **update.bat**
ระบบดึงโค้ด เตรียมส่วนประกอบ build และตรวจการเปิดแอปก่อนเปลี่ยนรุ่น
เปิด shortcut **NÜVEL Studio** ในตำแหน่งเดิมหลังอัปเดตสำเร็จ
ต้องใช้ Git clone และบัญชี Git ที่เข้าถึง repo ได้

ถ้าตัวใหม่ไม่ผ่านการตรวจหรือแอปเก่ายังล็อกไฟล์อยู่ จะไม่แทนที่รุ่นเดิม
ระบบเก็บรุ่นก่อนใน `dist` และไม่ลบไฟล์ดาวน์โหลดหรือการตั้งค่า
ตัว build ต้องตรวจ native startup, UI/bridge, ฟอนต์และ engines ให้ผ่าน
ก่อนสร้าง ZIP หรือเปลี่ยนแอป/shortcut

ดูผลตรวจล่าสุดและข้อจำกัดที่ยังต้องยืนยันบน Windows จริงใน
[Windows compatibility audit](WINDOWS-COMPATIBILITY.md)

`install.bat` และ `start.bat` เก็บไว้สำหรับรันซอร์สระหว่างพัฒนา
การใช้งานทั่วไปใช้ build แล้วเปิด shortcut หรือ `.exe` ตามขั้นตอนด้านบน
