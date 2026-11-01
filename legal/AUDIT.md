# ผลตรวจการดาวน์โหลดและการแจกจ่าย NÜVEL Studio

> Licensing update — 2026-11-01: the owner selected **GPL-3.0-only** for
> eligible original code, Copyright © 2026 Lumin0usX. Earlier Proprietary or
> decision-pending statements below are historical observations, not the current
> license grant. See [COPYRIGHT](../COPYRIGHT), [license decision](LICENSE-RECOMMENDATION.md),
> [brand notice](../BRAND-NOTICE.md) and [third-party notices](../THIRD_PARTY_NOTICES.md).
> Local Strategy B history remediation is complete; the current sprite uses
> Feather 4.29.2 under MIT. Earlier unknown-sprite and no-local-rewrite statements
> are superseded. No remote update or publication is implied. Public Windows and
> macOS binary releases remain **BLOCKED**. This license change does not clear
> dependencies, assets or packages for distribution, or validate pending code.

วันที่ 2026-10-31 · เริ่มตรวจจาก `ea27c53` · แจกฟรีผ่าน GitHub ตามที่เจ้าของระบุ

**สถานะ: ยังไม่พร้อมรับรองการแจกแพ็กเกจว่าปฏิบัติตามข้อกำหนดครบถ้วน**
เอกสารนี้เป็นผลตรวจโค้ดและเอกสารเบื้องต้น ไม่ใช่ความเห็นทางกฎหมายเฉพาะประเทศ
ยังไม่ได้ระบุประเทศเป้าหมาย ไม่เปลี่ยน repo เป็น public และไม่เปลี่ยน Proprietary
เป็น open source อัตโนมัติ การแจกฟรีไม่ทดแทนสิทธิ์ในเนื้อหาหรือหน้าที่ตาม license

## สิ่งที่แก้ในรอบนี้

- กำหนด `allow_unplayable_formats=False`, `usenetrc=False`, `cachedir=False`
  ในตัวดาวน์โหลด/metadata reader ของ GUI และตัวดาวน์โหลด Tk รุ่นเดิม
  ผู้เรียก API ไม่สามารถเปิดตัวเลือกเหล่านี้ผ่าน request ได้
- เปลี่ยนรายชื่อแพลตฟอร์มเป็นข้อความ ไม่แสดงหรือแพ็ก artwork ของ 50 แพลตฟอร์ม
  เอาภาพและตัววาดโลโก้ออกจากต้นไม้ไฟล์ปัจจุบัน โดยรักษารายชื่อ การค้นหา
  และสถานะตัวรองรับแต่ละโหมด รวมถึงแบรนด์ NÜVEL ของแอปเอง
- เพิ่มข้อความเรื่องสิทธิ์และการไม่เป็นพันธมิตรครบ 4 ภาษา
- เพิ่ม `repository_audit.py`, `dependency_audit.py`, การตรวจ credential ใน CI
  และใน release workflow พร้อมป้องกันไฟล์ cookies/HAR/credentials ใน `.gitignore`
- เจ้าของมอบหมายให้เลือกแนวทาง FFmpeg: เลือก LGPL สำหรับแพ็กใหม่ทั้งสอง OS;
  builder ต้องรับ binary พร้อม hash/source/build materials และไม่ fallback ไป
  แพ็ก GPL จาก imageio; **ยังไม่มี LGPL binary ที่ผ่าน native acceptance**
- ไม่แก้ประวัติ Git ไม่เพิกถอนคีย์ของบุคคลอื่น และไม่ทดสอบความใช้ได้ของคีย์ที่พบ

## A. ตรวจเป็นรายฟีเจอร์

| ฟีเจอร์ | หลักฐานทางเทคนิค | ข้อจำกัด/การดำเนินการ |
| --- | --- | --- |
| Video / Audio ด้วย yt-dlp | ตัวเลือกสร้างจาก URL/โหมด/คุณภาพที่ตรวจแล้ว; ไม่รับ arbitrary yt-dlp flags จาก UI | ไม่มีการตรวจใบอนุญาตของแต่ละ URL; ผู้มีสิทธิ์เข้าดูอาจไม่มีสิทธิ์ทำสำเนา |
| DRM | ไม่พบหน้ารับคีย์, CDM/Widevine integration หรือโค้ด DRM removal ในแอป; ปิด unplayable formats ชัดเจน | **ไม่ใช่ข้อพิสูจน์ว่า dependency ไม่มีกลไกหลบ technical measures ทุกชนิด** |
| Player/protocol challenges | yt-dlp มี signature/JavaScript challenge handling และ `yt-dlp-ejs`; ตัวอย่างใน `extractor/youtube/jsc/_builtin/ejs.py` | แยกตรวจกลไกนี้จาก DRM และเงื่อนไขของบริการ; ยังไม่ให้ legal clearance |
| Public URLs | `http`/`https`; generic extractor อาจรับเว็บนอก catalog 50 แห่งด้วย | public ไม่ใช่ public domain; การตรวจ 50 แห่งไม่ครอบคลุมทุก URL ที่ engines รับได้ |
| Images โดยตรง | ตรวจ magic bytes และสตรีมไฟล์; ชื่อซ้ำไม่ทับไฟล์เดิม | URL ภาพไม่แสดงใบอนุญาตหรือสิทธิ์การนำไปใช้ต่อ |
| Gallery / อัลบั้ม | gallery-dl CLI แยก process, `--config-ignore`, `--no-input`, image-only filter | ลิงก์ profile อาจดึงหลายโพสต์; การไม่มี DRM ไม่แปลว่าการดึงจำนวนมากได้รับอนุญาต |
| Cookies | ค่าเริ่มต้น `none`; เลือก browser/ไฟล์เอง; yt-dlp jar ตั้ง `filename=None`; gallery ไม่มี `--cookies-export` และไม่อ่าน user config | browser cookie extraction อาจถอดรหัสฐานข้อมูลในเครื่องตามสิทธิ์ผู้ใช้; ไม่ใช่ DRM removal แต่เป็นข้อมูลรับรองที่ต้องได้รับอนุญาตให้ใช้ |
| Account access | ไม่พบระบบขโมยบัญชี, credential guessing หรือระบบปลด paywall ของแอปเอง | cookies อาจเข้าถึง private/subscriber content ที่บัญชีดูได้; แอปไม่สามารถพิสูจน์สิทธิ์ในการดาวน์โหลดได้ และยังต้องทบทวนพฤติกรรม extractor |
| Metadata preview | ดึง metadata โดยไม่เริ่ม download; thumbnail อาจทำ request ไปที่ต้นทาง | ยังเป็น automated access; ห้ามเรียกว่าไม่มีผลต่อ ToS เพียงเพราะไม่บันทึกวิดีโอ |
| Local platform search | ค้นเฉพาะ registry ในเครื่อง | ไม่ใช่ search API ของแพลตฟอร์ม และไม่ใช่การรับรองสิทธิ์ |
| Audio extraction / MP3 / resizing | อาจแปลงเนื้อหา; `best` ของภาพเก็บ bytes เดิม | ต้องตรวจสิทธิ์ทำสำเนา/ดัดแปลง รวมถึงเงื่อนไข ND ของ license ที่ใช้จริง |
| Rights metadata | `image_quality.py` เก็บ ICC แต่ไม่คัดลอก metadata ทั้งหมดเมื่อ resize; default original ไม่ re-encode | **ค้างก่อนแจก:** ต้องจัดการ copyright/attribution/EXIF/XMP/IPTC และตรวจ metadata ใน video/audio conversion ไม่ให้ลบข้อมูลสิทธิ์โดยไม่ตั้งใจ; รอบนี้ยังไม่อ้างว่าแก้ครบ |

GitHub ตรวจ circumvention claims ทั้งด้านเทคนิคและกฎหมาย ไม่ใช้เพียงการมี/ไม่มีคำว่า DRM
เป็นข้อยุติ: [GitHub DMCA policy](https://docs.github.com/en/site-policy/content-removal-policies/dmca-takedown-policy).
ตัวอย่างข้อจำกัดที่อ่านได้ชัดเจน ได้แก่
[YouTube](https://www.youtube.com/static?template=terms),
[TikTok ROW](https://www.tiktok.com/legal/page/row/terms-of-service/en),
[X](https://x.com/en/tos), [Pinterest](https://policy.pinterest.com/en/terms-of-service),
[Vimeo](https://vimeo.com/legal/),
[Reddit](https://support.reddithelp.com/hc/en-us/articles/360043512931-Don-t-break-the-site).
การอนุญาตของเจ้าของเนื้อหาอาจยังไม่ใช่การอนุญาตใช้วิธีอัตโนมัติจากผู้ให้บริการ

ดู [ทะเบียนครบ 50 รายการ](PLATFORM_REVIEW.md): แยกข้อจำกัดที่ยืนยันได้,
license แบบมีเงื่อนไข, เรื่องที่ยังต้องอ่าน clause เพิ่ม และเอกสารที่เข้าถึงไม่ได้
ไม่มีรายการใดถูกตีความว่าเว็บไซต์ทั้งหมดผิดกฎหมาย หรือว่าอนุญาตทุกการดาวน์โหลด

## B. FFmpeg และ dependencies

### หลักฐานแยกตามระบบ

| ตัวที่ตรวจ | ผลจริง |
| --- | --- |
| macOS environment: imageio-ffmpeg 0.6.0 / FFmpeg 7.1 | SHA-256 `6d175a4743ca50256e89a8cdd731100f9cee33bd79aeea46894d209410dc6617`; `--enable-gpl`, libx264, libx265; `-L` ระบุ GPL version 2 or later |
| macOS `.app`: `Contents/Frameworks/bin/ffmpeg` | SHA-256 `aff8eb0bd7d1c53c1a7f32d0545330dcbee762e893e66a29c58ff683e5b3bcff`; version/configuration/GPL 2-or-later เช่นเดียวกัน; hash ต่างจากไฟล์ก่อนแพ็ก |
| Windows x64 | ข้อมูลเดิมจากเจ้าของว่า GPLv3+; **ไม่พบ binary ปัจจุบันในเครื่องนี้ให้ตรวจซ้ำ** จึงไม่ยืนยัน version/configuration/hash/license ของ Windows จากผล Mac |

BSD ของ Python wrapper `imageio-ffmpeg` ไม่ใช่ license ของ FFmpeg binary
ตรวจ exact binary ด้วย `-version`, `-L` และ hash เสมอ
[FFmpeg legal documentation](https://ffmpeg.org/legal.html) อธิบายความต่าง GPL/LGPL
และความจำเป็นของ source ที่ตรงกับ binary ไม่ใช่เพียงใส่เครดิตหรือ URL ต้นทาง

**ช่องว่างที่ยืนยันได้:** source tree/builders ยังไม่มี corresponding source ของ
FFmpeg และไลบรารีที่ลิงก์ไว้ครบ ไม่พบชุด build scripts/patches/notices ที่ผูกกับ binary
ทั้งสองระบบแบบตรวจสอบย้อนกลับได้ เก็บ stdout และ inventory ของ 34 distributions,
99 notice files ไว้ใน `dist/legal-audit-20261031/dependencies/` นี่เป็น inventory ของ
environment ที่ตรวจ ไม่ใช่ SBOM ครบถ้วนของ release หรือหลักฐานว่าปฏิบัติครบแล้ว

การตัดสินใจล่าสุด: เลือกข้อ 2 สำหรับแพ็กใหม่ ดู
[ข้อกำหนดและจุดค้าง LGPL](FFMPEG-LGPL.md) รายการด้านล่างอธิบายทางเลือก
ไม่ได้หมายความว่าดำเนินการสองแนวทางนี้เสร็จแล้ว:

1. **คง GPL executable แบบ CLI:** จัดหา exact corresponding source ของ FFmpeg,
   static libraries, patches/configure/build scripts และ license/notices ให้ครบ
   ผูกกับ hash ของไฟล์ที่แจก จัดส่ง source ให้ผู้รับเข้าถึงตาม GPL รุ่นที่ใช้
   ทบทวนเงื่อนไขประกอบการแจกกับผู้เชี่ยวชาญก่อนออก release
2. **เปลี่ยนเป็น LGPL build:** ต้องตรวจทั้งสอง OS ว่าไม่เปิด GPL/nonfree parts,
   ตรวจ dependencies และ source obligations ด้วย และทดสอบ codec path ใหม่ก่อน
   แพ็ก Mac ใหม่เลือก VideoToolbox แทน libx264; source development ที่ไม่ได้เลือก
   bundle ใหม่ยังรักษา engine เดิม การทดสอบ source จึงยังไม่ยืนยัน LGPL path
   probe VideoToolbox ในบริบทนี้ล้มเหลวด้วย OSStatus -12908; ยังไม่ยืนยันสาเหตุ

การเรียกโปรแกรมแยกด้วย subprocess เป็นข้อเท็จจริงทางสถาปัตยกรรม ไม่ใช่คำรับรองว่า
GUI ต้องเป็น GPL หรือว่าแจกได้โดยไม่ต้องทำอะไรเพิ่ม
[GNU GPL FAQ](https://www.gnu.org/licenses/gpl-faq.en.html#MereAggregation)
แยก aggregation กับ combined work ตามลักษณะการเชื่อมต่อ
อ่าน [GPLv2](https://raw.githubusercontent.com/FFmpeg/FFmpeg/n7.1/COPYING.GPLv2)
และ [GPLv3](https://raw.githubusercontent.com/FFmpeg/FFmpeg/n7.1/COPYING.GPLv3) สำหรับวิธีส่งมอบ source ที่ใช้จริง

### นอกเหนือจาก FFmpeg

- gallery-dl 1.32.17: metadata/header ระบุ GPL version 2; builder แยก CLI และแนบ
  `gallery_dl` source + LICENSE + BUILD.txt แต่ยังไม่ได้ยืนยัน source closure ของ
  requests/transitive libraries/Python/PyInstaller bootloader ทั้ง executable
- ต้องตรวจความเข้ากันได้ของ license ของ dependency แต่ละตัว ไม่อนุมานว่า subprocess
  แก้ปัญหา license ภายใน gallery CLI ได้ โดยเฉพาะ metadata GPLv2 กับ dependencies
  Apache-2.0: [คำอธิบาย GNU](https://www.gnu.org/licenses/rms-why-gplv3.en.html)
  นี่เป็นประเด็นให้ทบทวน ไม่ใช่คำวินิจฉัยว่ามีการละเมิดแล้ว
- yt-dlp, yt-dlp-ejs, curl-cffi, certifi, pywebview, Pillow, Python และ native
  runtime ของแต่ละ OS ต้องมี notices/เงื่อนไขตามรุ่นที่แพ็กจริง
- ฟอนต์เดิม EN 5 / TH 5 / JP 3 / CN 3 ไม่เปลี่ยน และเก็บ OFL/copyright เดิมไว้
  อีเมลผู้สร้างใน license เหล่านี้ไม่ใช่ secret ที่ควรลบทิ้งโดยอัตโนมัติ
- License ไม่ได้ตัดประเด็นสิทธิบัตร codec หรือสิทธิ์ในสื่อที่ผู้ใช้ดาวน์โหลด

## C. ชื่อและโลโก้

เลือกแนวทางข้อความธรรมดาเพื่อลดการพึ่งพาสิทธิ์ใน artwork และไม่เปลี่ยน registry
ไม่ได้อ้างว่าโลโก้ทุกแบรนด์ต้องห้าม ตัวอย่าง
[TikTok design guidelines](https://developers.tiktok.com/docs/en/getting-started-design-guidelines)
กล่าวถึง written permission และ [YouTube brand resources](https://brand.youtube/)
มีแนวทางแยกจากการอนุญาตดาวน์โหลดเนื้อหา

ภาพแพลตฟอร์มเก่ายังอยู่ใน Git history และแพ็กเกจเก่า การลบใน HEAD ไม่ลบสำเนาเหล่านั้น
ไม่ได้ force-push หรือถอน release เก่าในรอบนี้ แบรนด์ NÜVEL ที่เจ้าของส่งมาให้ยังอยู่เดิม
แต่ยังไม่พบหลักฐานใน repo ว่าได้รับสิทธิ์แจก brand kit จากผู้สร้างครบแล้ว ต้องยืนยัน provenance
ก่อนเผยแพร่กว้าง ชื่อแพลตฟอร์มแบบข้อความก็ยังต้องใช้อย่างไม่ทำให้สับสน

## D. Repository / ความลับ / ข้อมูลส่วนตัว

### ขอบเขตและผลตรวจ

- Git clone นี้ไม่ shallow; ณ เริ่มตรวจมี 25 commits, 462 blob objects และ 4 tag objects
  สแกน object database ทั้งหมด รวม object ที่ไม่มี ref อ้างถึง และ working tree ของซอร์ส
- heuristic scan ไม่พบ credential ส่วนตัวที่เข้า pattern ในซอร์ส/ประวัติที่ตรวจ
  **ไม่ใช่การรับรองว่าไม่มี secret ทุกชนิด**: ค่าเข้ารหัส รูปภาพ ประเภทคีย์ใหม่ หรือ
  ข้อมูลที่ไม่เข้า pattern อาจไม่ถูกตรวจพบ
- พบตัวระบุอีเมลผู้เขียนหนึ่งชุดใน commit metadata และพาธเครื่องในเอกสารประวัติ
  รายงานเก็บเฉพาะ fingerprints/ตำแหน่ง ไม่พิมพ์ค่าอีเมลหรือ credentials
  ไม่ได้เขียน history ใหม่หรือเปลี่ยนอัตลักษณ์ผู้เขียนโดยพลการ
- แยกสแกนแอปเก่าที่อยู่ในเครื่อง พบ 46 credential-like patterns ใน dependency
  extractors: Google API identifiers, JWT/client configuration, AWS access-key ID
  และค่าคงที่อื่น ๆ ไม่พบหลักฐานว่าเป็น secret ส่วนตัวของเจ้าของแอป และไม่ได้ยืนยันว่า
  ใช้งานได้หรือได้รับอนุญาตให้ใช้ ต้องทบทวน upstream; ไม่ทดลองใช้/เพิกถอนคีย์ของผู้อื่น
- ไม่ได้ fetch refs ใหม่ในรอบสแกน เพราะ shell เชื่อมต่อ GitHub ไม่ได้ ไม่ครอบคลุม
  remote-only PR/deleted refs, GitHub caches, forks, release/Actions artifacts, LFS
  payloads, OS credential stores หรือทุกสำเนาบนเครื่องอื่น
- การตรวจสำเนาแอปเก่าแยกจากซอร์ส และมี FFmpeg ขนาดเกินขีดจำกัดตัวสแกน 32 MiB;
  ไม่อ้างว่าสแกน binary ใหญ่เหล่านั้นครบทุก byte ด้วยตัวตรวจ secret นี้

ถ้าพบ secret จริง ให้ revoke/rotate ก่อน แล้วประเมิน refs/forks/caches และประวัติ
การลบไฟล์ใน commit ล่าสุดอย่างเดียวไม่เพียงพอ
[GitHub sensitive-data removal](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository)
ไม่ควร rewrite หรือ force-push ก่อนวางแผนผลต่อทุกเครื่องและได้รับอนุญาต

### License / provenance ก่อนแจกฟรี

`LICENSE` ปัจจุบันยังไม่อนุญาตใช้/คัดลอก/build โดยทั่วไปหากไม่มี written permission
จึงยังไม่ตรงกับการตั้งใจให้คนทั่วไปใช้แอปฟรี ต้องตัดสินใจขอบเขตสิทธิ์สำหรับผู้รับ
ดู [ข้อเสนอ permission สำหรับ freeware](FREEWARE-PERMISSION-DRAFT.md)
ยังไม่แก้ license หลักหรือเปลี่ยนเป็น open source แทนเจ้าของ
[GitHub licensing documentation](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository)
อธิบายสิทธิ์ view/fork บน public GitHub แยกจาก software license

ไม่พบ vendored source libraries ขนาดใหญ่ในต้นไม้ซอร์สปัจจุบันนอกเหนือจากฟอนต์/งานภาพ
แต่ Git history และชื่อ copyright ไม่ใช่หลักฐานว่าผู้พัฒนามีสิทธิ์ในทุกบรรทัดที่นำมาใช้
ต้องยืนยันที่มาของโค้ด/brand kit กับเจ้าของ ห้ามถือผล pattern scan เป็น provenance audit ที่สมบูรณ์

## วิธีตรวจซ้ำ

```bash
python repository_audit.py --fail-on-secrets --output dist/audit/source-history.json
python repository_audit.py --include-built-apps --output dist/audit/with-local-app.json
python dependency_audit.py --output dist/audit/dependencies --ffmpeg /path/to/ffmpeg
```

ไม่แชร์ไฟล์ raw ที่มี credentials ลง issue/chat โดยไม่ redact เครื่องมือไม่เรียกบริการ
ตรวจคีย์ภายนอก และ CI ไม่ upload แม้แต่ redacted report เป็น artifact

## งานก่อนการเผยแพร่ที่ยังเหลือ

1. ตัดสินใจสิทธิ์การใช้แอปฟรีและยืนยัน ownership/provenance; `LICENSE` ยังไม่เปลี่ยน
2. สร้างและตรวจ LGPL FFmpeg ของแต่ละ OS พร้อม corresponding source/notices/build materials
3. ปิดรายการ rights-metadata handling และทบทวน engine/extractor ที่มี client credentials/challenge handling
4. ทบทวน platform/region/instance ที่ยัง pending หรืออ่านเอกสารไม่ได้ และเส้นทาง API/permission
5. ตรวจ release artifacts/remote refs/ข้อมูลส่วนตัวก่อนเปิด repo หรือแจกใหม่
6. รัน native Windows/macOS tests และตรวจ packages จริงอีกครั้ง แล้วจึงตัดสินใจเผยแพร่

รอบนี้ไม่เผยแพร่ release ใหม่และไม่อ้างว่าแอปปลอดความเสี่ยงทางกฎหมายทั้งหมด
