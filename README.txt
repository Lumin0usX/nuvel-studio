NÜVEL STUDIO
===========

สถานะ: เผยแพร่เฉพาะซอร์สโค้ด ยังไม่มี binary Windows/macOS ให้ดาวน์โหลด
โค้ดต้นฉบับในขอบเขตของโปรเจกต์ใช้ GPL-3.0-only; Copyright © 2026 Lumin0usX
ส่วนประกอบของบุคคลที่สามยังใช้ license ของตนเอง ดู THIRD_PARTY_NOTICES.md
เก็บ tags และ release entries เดิมไว้เพื่ออ้างอิงประวัติ ไม่ใช่แพ็กเกจพร้อมใช้
ซอร์ส ZIP จาก GitHub ไม่ใช่ตัวแอป และขณะนี้ไม่มีแพ็กเกจสำหรับอัปเดตในแอป

การแพ็กจาก source ยังต้องมี LGPL FFmpeg พร้อม source/build materials ที่ผ่านการตรวจ
การ build สำเร็จในเครื่องไม่ใช่การอนุมัติให้แจก binary

Build จาก source

Windows
1. ติดตั้ง Python 3.10+ แบบ x64 และเลือก Add Python to PATH
2. เปิด build_windows.bat เพื่อเตรียมส่วนประกอบและสร้างแอป
3. เปิด shortcut "NÜVEL Studio" ในโฟลเดอร์โปรเจกต์ โดยไม่มี Terminal
อัปเดต: ปิดแอป แล้วเปิด update.bat

macOS Apple Silicon
1. ติดตั้ง Python 3.12+ แบบ ARM64 หรือ universal2
2. ดับเบิลคลิก build_macos.command เพื่อเตรียมส่วนประกอบและ build
3. เมื่อสำเร็จ เปิด "NÜVEL Studio.app" ในโฟลเดอร์โปรเจกต์ โดยไม่มี Terminal
อัปเดต: ปิดแอป แล้วเปิด update_macos.command จากโฟลเดอร์ Git clone
ระบบ build และตรวจแอปใหม่ก่อนแทนที่รุ่นเก่า ไม่ต้องเลือกโหมดหรือไล่หาโฟลเดอร์เวลา

วาง URL เลือกวิดีโอ เสียง หรือภาพ เลือกคุณภาพและปลายทาง แล้วเริ่มดาวน์โหลด
สถานะแพลตฟอร์มแสดงความสามารถของ extractor ที่ติดตั้ง ไม่ใช่การรับประกันทุก URL
คลิปที่ต้องใช้บัญชีสามารถเลือก cookies ได้ โปรแกรมไม่แก้ไฟล์ cookies ต้นฉบับ

รายละเอียด: README.md, README-Windows.md และ README-macOS.md
โค้ดต้นฉบับในขอบเขตของโปรเจกต์ใช้ GPL-3.0-only ตาม LICENSE และ COPYRIGHT
