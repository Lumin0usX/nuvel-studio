from platform_runtime import install_instructions

PLATFORMS = (
    ("YouTube", "Youtube", "youtube", "#ff6378"),
    ("TikTok", "TikTok", "tiktok", "#61ded8"),
    ("Facebook", "Facebook", "facebook", "#689fff"),
    ("Instagram", "Instagram", "instagram", "#e98ac5"),
    ("X / Twitter", "Twitter", "twitter", "#cbd5e1"),
    ("Reddit", "Reddit", "reddit", "#ff976f"),
    ("Vimeo", "Vimeo", "vimeo", "#70ceef"),
    ("Dailymotion", "Dailymotion", "dailymotion", "#a899ff"),
    ("Twitch", "TwitchClips", "twitch", "#bd93ff"),
    ("Bilibili", "BiliBili", "bilibili", "#78c8ee"),
    ("Pinterest", "Pinterest", "pinterest", "#ff8697"),
)


def platform_support():
    """Inspect local extractors; this is not a network availability test."""
    try:
        from yt_dlp.extractor import get_info_extractor
        from yt_dlp.version import __version__
    except ImportError:
        return "ยังไม่ได้ติดตั้ง yt-dlp", {name: "missing" for name, *_ in PLATFORMS}
    states = {}
    for name, key, *_ in PLATFORMS:
        try:
            states[name] = "supported" if get_info_extractor(key).working() else "broken"
        except (KeyError, AttributeError, ImportError):
            states[name] = "missing"
    return __version__, states


def download_error(exc):
    detail = str(exc)
    lower = detail.lower()
    if "unsupported url" in lower:
        hint = "ยังไม่รองรับลิงก์นี้ ลองใช้ลิงก์คลิปโดยตรงหรืออัปเดตผ่าน install.bat"
    elif "drm" in lower:
        hint = "คลิปนี้มี DRM โปรแกรมไม่รองรับการดาวน์โหลดเนื้อหานี้"
    elif any(word in lower for word in ("cookie", "decrypt", "dpapi")):
        hint = "อ่าน cookies ไม่สำเร็จ ลองปิดเบราว์เซอร์ หรือใช้ไฟล์ cookies.txt / Firefox"
    elif any(word in lower for word in ("login", "sign in", "private", "authentication", "403")):
        hint = "คลิปอาจต้องล็อกอิน เลือก cookies จากบัญชีที่เปิดคลิปนี้ได้"
    else:
        hint = "ลองใช้ลิงก์คลิปโดยตรง และอัปเดตผ่าน install.bat หากเว็บเปลี่ยนระบบ"
    return hint.replace("install.bat", install_instructions()) + "\n\nรายละเอียด: " + detail
