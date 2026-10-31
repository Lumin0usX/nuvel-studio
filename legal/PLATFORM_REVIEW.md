# ทะเบียนตรวจเงื่อนไข 50 แพลตฟอร์ม

ตรวจวันที่ 2026-10-31 จาก registry ใน `download_engine.py` พยายามเข้าถึงเอกสารของทุกรายการ
บางหน้าเป็น JavaScript/login/403/429 หรืออ่านได้ไม่ครบ จึงแสดงสถานะค้างอย่างชัดเจน
รายการที่พบเอกสารแต่ยังไม่ได้ยืนยัน operative clauses จะไม่ถูกนับว่าตรวจสิทธิ์ครบแล้ว
URL ของรายการที่อ่านไม่ได้เป็นจุดเริ่มตรวจต่อ ไม่ใช่หลักฐานว่าข้อความปัจจุบันอนุญาต

- **พบข้อจำกัดวิธีเข้าถึง:** อ่านข้อจำกัดที่เกี่ยวกับ automation/download ได้ แต่ไม่ใช่คำวินิจฉัยว่าเว็บไซต์หรือทุกการใช้งานผิดกฎหมาย
- **สิทธิ์มีเงื่อนไข:** มีเส้นทาง/เนื้อหาที่อาจได้รับอนุญาต ต้องทำตามเงื่อนไขของไฟล์และวิธีเข้าถึง ไม่ใช่ blanket approval
- **รอทบทวน/อ่านไม่สำเร็จ/ราย instance:** ยังไม่พร้อมให้ legal clearance
- Routes เป็นเส้นทางที่ประกาศในโค้ด ไม่ใช่ผล live test หรือการรับรองสิทธิ์ ใช้ terms ให้ตรงประเทศ บัญชี และผลิตภัณฑ์จริง
- ทุกแถวมี `legal_clearance=false` เพราะการตรวจนี้ไม่อนุมัติสิทธิ์แทนเจ้าของบริการหรือเจ้าของเนื้อหา

| แพลตฟอร์ม | Routes | สถานะ | ข้อสังเกตและเอกสารทางการ |
| --- | --- | --- | --- |
| YouTube | Video / Audio | พบข้อจำกัดวิธีเข้าถึง | จำกัดการดาวน์โหลดและ automated access เว้นแต่บริการ/ผู้ให้บริการอนุญาต; สิทธิ์ของเจ้าของคลิปเป็นอีกส่วนหนึ่ง · [เอกสาร](https://www.youtube.com/static?template=terms) |
| TikTok | Video / Audio / Image | พบข้อจำกัดวิธีเข้าถึง | ROW terms จำกัด automated scripts; ต้องตรวจฉบับประเทศและวิธีดาวน์โหลดที่อนุญาต · [เอกสาร](https://www.tiktok.com/legal/page/row/terms-of-service/en) |
| Facebook | Video / Audio / Image | เอกสารอ่านไม่สำเร็จ | หน้าที่เปิด redirect ไป login; ยังไม่ยืนยันข้อความ terms ปัจจุบันจากหน้านี้ · [เอกสาร](https://www.facebook.com/terms.php) |
| Instagram | Video / Audio / Image | เอกสารอ่านไม่สำเร็จ | ได้รับ 429; ยังไม่ให้ clearance เรื่อง automated access หรือสิทธิ์ในโพสต์ · [เอกสาร](https://help.instagram.com/581066165581870/) |
| X / Twitter | Video / Audio / Image | พบข้อจำกัดวิธีเข้าถึง | จำกัด scraping โดยไม่มี written permission ยกเว้นที่กฎหมายกำหนด · [เอกสาร](https://x.com/en/tos) |
| Reddit | Video / Audio / Image | พบข้อจำกัดวิธีเข้าถึง | นโยบายห้าม scraping ที่ไม่มี authorized agreement; ต้องตรวจ User Agreement/Developer Terms ด้วย · [เอกสาร](https://support.reddithelp.com/hc/en-us/articles/360043512931-Don-t-break-the-site) |
| Vimeo | Video / Audio | พบข้อจำกัดวิธีเข้าถึง | จำกัด download และ automated access เว้นแต่ได้รับอนุญาตตามบริการ/API/ข้อยกเว้นที่ระบุ · [เอกสาร](https://vimeo.com/legal/) |
| Dailymotion | Video / Audio | รอทบทวน clause/วิธีใช้ | พบเอกสาร; ต้องทบทวนสิทธิ์ download วิธี automated และข้อตกลงของผู้ลงเนื้อหาเพิ่มเติม · [เอกสาร](https://legal.dailymotion.com/en/terms-of-use/) |
| Twitch | Video / Audio | เอกสารอ่านไม่สำเร็จ | หน้าที่อ่านได้เป็น shell สั้น; ยังไม่ตรวจครบ operative clauses ของ terms · [เอกสาร](https://legal.twitch.com/en/legal/terms-of-service/) |
| Bilibili | Video / Audio / Image | เอกสารอ่านไม่สำเร็จ | หน้าเงื่อนไขไม่ส่งข้อความที่อ่านได้; ต้องทบทวนฉบับภาษาจีนปัจจุบัน · [เอกสาร](https://www.bilibili.com/blackboard/protocal/licence.html) |
| Pinterest | Video / Audio / Image | พบข้อจำกัดวิธีเข้าถึง | ห้าม scrape/collect/copy ด้วยวิธี automated ที่ไม่ได้รับอนุญาตล่วงหน้า · [เอกสาร](https://policy.pinterest.com/en/terms-of-service) |
| Bluesky | Video / Audio / Image | รอทบทวน clause/วิธีใช้ | พบ terms; โปรโตคอลสาธารณะไม่ใช่ blanket copyright license ต้องตรวจเนื้อหา/บริการที่ใช้จริง · [เอกสาร](https://bsky.social/about/support/tos) |
| SoundCloud | Audio | สิทธิ์มีเงื่อนไข | terms อนุญาต download ผ่านฟีเจอร์ที่ uploader เปิดและตาม territorial availability; ไม่เท่ากับอนุญาต stream ripping ทุกกรณี · [เอกสาร](https://soundcloud.com/terms-of-use) |
| Bandcamp | Audio | สิทธิ์มีเงื่อนไข | ต้องคง notices/restrictions ของเนื้อหา; ตรวจสิทธิ์จากศิลปิน/การซื้อหรือ free download และวิธีเข้าถึงแยกกัน · [เอกสาร](https://bandcamp.com/terms_of_use) |
| Mixcloud | Audio | รอทบทวน clause/วิธีใช้ | พบ terms; ต้องทบทวน offline listening/download และวิธี automated ก่อนรับรอง extractor · [เอกสาร](https://www.mixcloud.com/terms/) |
| Audiomack | Audio | รอทบทวน clause/วิธีใช้ | พบ terms เรื่องเนื้อหา; ยังไม่ยืนยัน permission ของ automated extraction และไฟล์แต่ละรายการ · [เอกสาร](https://audiomack.com/about/terms-of-service) |
| Flickr | Video / Audio / Image | พบข้อจำกัดวิธีเข้าถึง | จำกัด robots/scraping; ข้อยกเว้น user content ที่เปิด download ไม่ใช่สิทธิ์ดึงทุกภาพ/ใช้ซ้ำทุกแบบ · [เอกสาร](https://www.flickr.com/help/terms) |
| Imgur | Video / Audio / Image | รอทบทวน clause/วิธีใช้ | พบ terms; การเปิดดูภาพไม่ใช่การให้ license ของเจ้าของภาพแก่ผู้ใช้ทุกคน · [เอกสาร](https://imgur.com/tos) |
| Tumblr | Video / Audio / Image | เอกสารอ่านไม่สำเร็จ | help page ชี้ไป current terms แต่หน้า terms ตอบ 406; ต้องอ่านฉบับที่ใช้งานจริง · [เอกสาร](https://help.tumblr.com/knowledge-base/terms-of-service/) |
| Pixiv | Image | เอกสารอ่านไม่สำเร็จ | อ่านเอกสารนโยบายเต็มไม่ได้ในรอบนี้; ต้องตรวจ terms และสิทธิ์ผู้วาด · [เอกสาร](https://policies.pixiv.net/en.html) |
| DeviantArt | Image | เอกสารอ่านไม่สำเร็จ | 403; ต้องตรวจสิทธิ์งานศิลปะและ automation policy ก่อนรับรอง · [เอกสาร](https://www.deviantart.com/about/policy/service) |
| Unsplash | Image | พบข้อจำกัดวิธีเข้าถึง | license ภาพมีเงื่อนไขแยก; terms จำกัด automated tools ยกเว้น API ที่ทำตาม API Terms · [เอกสาร](https://unsplash.com/terms) |
| VK | Video / Audio / Image | เอกสารอ่านไม่สำเร็จ | เข้าถึงข้อความ terms ไม่สำเร็จ; ต้องทบทวนฉบับ/ประเทศที่ใช้จริง · [เอกสาร](https://vk.com/legal/terms) |
| RuTube | Video / Audio | รอทบทวน clause/วิธีใช้ | พบข้อตกลงภาษารัสเซีย; ยังไม่ให้ clearance วิธี extraction และสิทธิ์ของเจ้าของวิดีโอ · [เอกสาร](https://rutube.ru/info/agreement/) |
| Rumble | Video / Audio | รอทบทวน clause/วิธีใช้ | พบ terms; ต้องแยก license ของผู้ลงเนื้อหากับสิทธิ์ใช้บริการ/ดาวน์โหลด · [เอกสาร](https://rumble.com/s/terms) |
| Streamable | Video / Audio | รอทบทวน clause/วิธีใช้ | พบ current terms; ยังไม่ยืนยัน permission ของการดึงไฟล์แบบอัตโนมัติ · [เอกสาร](https://streamable.com/terms) |
| Internet Archive | Video / Audio | เอกสารอ่านไม่สำเร็จ | หน้า terms ไม่ส่งเนื้อหาที่อ่านได้; ต้องดู license ราย item และแยก public files จากเนื้อหายืม/DRM · [เอกสาร](https://archive.org/about/terms) |
| Niconico | Video / Audio | เอกสารอ่านไม่สำเร็จ | ดึงเอกสารไม่สำเร็จ; ต้องตรวจ account/content terms และเนื้อหาที่จำกัดสิทธิ์ · [เอกสาร](https://account.nicovideo.jp/rules/account) |
| Douyin | Video / Audio | เอกสารอ่านไม่สำเร็จ | อ่านได้เพียง landing page ไม่ใช่เนื้อหาข้อตกลงเต็ม; ไม่ใช้ terms ของ TikTok แทนโดยอัตโนมัติ · [เอกสาร](https://www.douyin.com/agreements/) |
| Snapchat | Video / Audio / Image | พบข้อจำกัดวิธีเข้าถึง | จำกัด robots/scripts/automated extraction โดยมีข้อยกเว้นเฉพาะ; Spotlight สาธารณะไม่ใช่ blanket permission · [เอกสาร](https://www.snap.com/terms) |
| LinkedIn | Video / Audio | พบข้อจำกัดวิธีเข้าถึง | จำกัด bots หรือ unauthorized automated methods; ต้องตรวจเส้นทางที่ได้รับอนุญาต · [เอกสาร](https://www.linkedin.com/legal/user-agreement) |
| Telegram | Video / Audio | รอทบทวน clause/วิธีใช้ | เส้นทางในแอปเป็น public embed; ยังต้องตรวจสิทธิ์ของผู้โพสต์และ terms ไม่อนุมานว่าใช้ private channel ได้ · [เอกสาร](https://telegram.org/tos) |
| Weibo | Video / Audio / Image | รอทบทวน clause/วิธีใช้ | พบข้อตกลงภาษาจีน; ต้องตรวจสิทธิ์ในโพสต์ วิธี automated และฉบับที่ผูกกับบัญชี · [เอกสาร](https://weibo.com/signup/v5/protocol) |
| Xiaohongshu / RED | Video / Audio | เอกสารอ่านไม่สำเร็จ | หน้า agreement ไม่ส่งเนื้อหาที่อ่านได้; ต้องแยก Xiaohongshu กับ RED ตามผลิตภัณฑ์/ภูมิภาค · [เอกสาร](https://agree.xiaohongshu.com/h5/terms/ZXXY20220331001/-1) |
| Kick | Video / Audio | รอทบทวน clause/วิธีใช้ | พบ terms; ต้องตรวจสิทธิ์ creator และเงื่อนไขวิธีเข้าถึง clips/VOD · [เอกสาร](https://kick.com/terms-of-service) |
| Odysee | Video / Audio | เอกสารอ่านไม่สำเร็จ | หน้า JavaScript ไม่มีเนื้อหา terms ที่อ่านได้; สิทธิ์ของ uploader ยังต้องตรวจแยก · [เอกสาร](https://odysee.com/$/tos) |
| PeerTube | Video / Audio | ต้องตรวจราย instance | FAQ อธิบายระบบหลาย instance; ไม่ใช่ terms ของทุก server ต้องตรวจ server ที่ URL ชี้ไปและ license ของวิดีโอ · [เอกสาร](https://joinpeertube.org/faq) |
| TED | Video / Audio | สิทธิ์มีเงื่อนไข | terms แยกเนื้อหาบางส่วนที่เป็น CC ออกจาก subscription/commercial content; ตรวจ usage policy และสิทธิ์ดัดแปลง/แยกเสียง · [เอกสาร](https://www.ted.com/about/our-organization/our-policies-terms/ted-com-terms-of-use) |
| 9GAG | Video / Audio | รอทบทวน clause/วิธีใช้ | พบ EULA/terms; ต้องตรวจ license ของแต่ละโพสต์และ automated download เพิ่ม · [เอกสาร](https://about.9gag.com/tos) |
| Medal.tv | Video / Audio | รอทบทวน clause/วิธีใช้ | พบ terms; ไม่ถือว่า creator clip ทุกชิ้นมี permission ให้ดึงและใช้ซ้ำ · [เอกสาร](https://medal.tv/terms) |
| Apple Podcasts | Audio | พบข้อจำกัดวิธีเข้าถึง | Apple จำกัด automated scraping; RSS enclosure ของ publisher อาจมีสิทธิ์แยก ต้องตรวจว่า extractor ใช้เส้นทางใด · [เอกสาร](https://www.apple.com/legal/internet-services/itunes/us/terms.html) |
| Audius | Audio | รอทบทวน clause/วิธีใช้ | พบ terms PDF; ยังต้องตรวจ downloader/API route และ permission ของศิลปิน ไม่ใช้การเป็น decentralized protocol เป็น license · [เอกสาร](https://audius.co/documents/TermsOfUse.pdf) |
| ArtStation | Image | รอทบทวน clause/วิธีใช้ | พบ terms; ต้องตรวจสิทธิ์ artwork/download และวิธี automated เพิ่ม · [เอกสาร](https://www.artstation.com/tos) |
| Behance | Image | รอทบทวน clause/วิธีใช้ | ตรวจพบ Adobe general terms แต่ยังต้องตรวจ supplemental terms ของ Behance และสิทธิ์ของเจ้าของผลงาน · [เอกสาร](https://www.adobe.com/legal/terms.html) |
| Pexels | Image | สิทธิ์มีเงื่อนไข | license อนุญาตใช้/download ภายใต้ข้อห้ามบางแบบ; ต้องตรวจ ToS/API และวิธี automated แยก ไม่ใช่ clearance ของ scraper · [เอกสาร](https://www.pexels.com/license/) |
| 500px | Image | เอกสารอ่านไม่สำเร็จ | official help ชี้ URL นี้ แต่เปิด terms ไม่สำเร็จ; การมีภาพให้ดูไม่แทนใบอนุญาตภาพ · [เอกสาร](https://about.500px.com/terms/) |
| Wallhaven | Image | เอกสารอ่านไม่สำเร็จ | 403; ต้องตรวจนโยบายปัจจุบันและสิทธิ์ของภาพที่นำมาโพสต์ · [เอกสาร](https://wallhaven.cc/terms) |
| ImgBB | Image | รอทบทวน clause/วิธีใช้ | พบ terms ของผู้ให้บริการ hosting; ไม่อนุมานว่าไฟล์ภาพทุกไฟล์ไม่มีลิขสิทธิ์ · [เอกสาร](https://imgbb.com/tos) |
| Lensdump | Image | รอทบทวน clause/วิธีใช้ | พบ terms; ต้องตรวจสิทธิ์ของผู้ลงภาพและวิธี retrieval เพิ่ม · [เอกสาร](https://lensdump.com/terms) |
| Wikimedia Commons | Video / Audio / Image | สิทธิ์มีเงื่อนไข | ต้องทำตาม license ของแต่ละไฟล์เมื่อใช้ต่อ รวม attribution/share-alike ที่ใช้จริง; ตรวจ bot/API rules เพิ่ม · [เอกสาร](https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use) |

เอกสารเพิ่มเติม: [Pexels ToS](https://www.pexels.com/terms-of-service/), [Unsplash terms](https://unsplash.com/terms), [Reddit User Agreement](https://redditinc.com/policies/user-agreement).
