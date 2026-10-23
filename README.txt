NÜVEL STUDIO
===========

แอปพร้อมใช้ (เมื่อมีการเผยแพร่ Release)
ดาวน์โหลด ZIP สำหรับ Windows x64 หรือ Mac Apple Silicon จาก GitHub Releases
แตกไฟล์แล้วเปิด NÜVEL Studio.exe หรือ YTDL Studio.app ไม่ต้องติดตั้ง Python/Git
อัปเดตครั้งต่อไป: Settings > App updates
repo เป็น private จึงต้องตั้ง GitHub token แบบ Contents: read-only ในแอปครั้งแรก
token เก็บใน Windows Credential Manager / macOS Keychain
เครื่องที่รันจาก source ต้อง build เวอร์ชันนี้หนึ่งครั้งก่อนใช้การติดตั้งอัปเดตในแอป
รายละเอียดการใช้งานและเผยแพร่ release ดู README.md

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
โค้ดต้นฉบับของโปรเจกต์สงวนสิทธิ์ตาม LICENSE
