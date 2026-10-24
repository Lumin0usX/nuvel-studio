# NÜVEL Studio — Windows x64

## แอปพร้อมใช้และอัปเดตในแอป

ดาวน์โหลด **NUVEL-Studio-Windows-x64.zip** จาก Releases ของ repo ส่วนตัว
แตก ZIP ทั้งโฟลเดอร์ แล้วเปิด **NÜVEL Studio.exe** โดยไม่ต้องติดตั้ง Python หรือ Git
เก็บโฟลเดอร์ `_internal` ไว้ข้างไฟล์ exe เสมอ ต้องมี Microsoft Edge WebView2 Runtime
ซึ่งโดยปกติติดตั้งมาแล้วบน Windows 10/11

อัปเดตครั้งถัดไปผ่าน **Settings → App updates** ได้เลย สำหรับ repo ส่วนตัว
ตั้ง fine-grained GitHub token ที่อ่าน Contents ของ repo นี้ได้เพียงครั้งแรก
แอปเก็บ token ใน Windows Credential Manager ไม่เขียนลงไฟล์ตั้งค่า
รายละเอียดการออก release อยู่ใน [README.md](README.md#download-the-ready-to-use-app)

ขั้นตอนด้านล่างสำหรับผู้ที่ต้องการ build จาก source เอง

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

ZIP สำหรับส่งต่ออยู่ใน `dist/windows-<เวลาที่ build>` แตก ZIP แล้วเปิด `.exe` ได้
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
