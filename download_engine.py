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
    ("Bluesky", "Bluesky", "bluesky", "#0085ff"),
    ("SoundCloud", "Soundcloud", "soundcloud", "#ff7700"),
    ("Bandcamp", "Bandcamp", "bandcamp", "#1da0c3"),
    ("Mixcloud", "Mixcloud", "mixcloud", "#9da9e8"),
    ("Audiomack", "Audiomack", "audiomack", "#ffa200"),
    ("Flickr", "Flickr", "flickr", "#ff0084"),
    ("Imgur", "Imgur", "imgur", "#1bb76e"),
    ("Tumblr", "Tumblr", "tumblr", "#97b0cf"),
    ("Pixiv", None, "pixiv", "#0096fa"),
    ("DeviantArt", None, "deviantart", "#05cc47"),
    ("Unsplash", None, "unsplash", "#eeeeee"),
    ("VK", "VK", "vk", "#0077ff"),
    ("RuTube", "Rutube", "rutube", "#90b6f1"),
    ("Rumble", "Rumble", "rumble", "#85c742"),
    ("Streamable", "Streamable", "streamable", "#009fff"),
    ("Internet Archive", "ArchiveOrg", "archive", "#d8d8d8"),
    ("Niconico", "Niconico", "niconico", "#eeeeee"),
    ("Douyin", "Douyin", "douyin", "#61ded8"),
    ("Snapchat", "SnapchatSpotlight", "snapchat", "#fffc00"),
)

# Domains also travel with the API response; the UI must not maintain another registry.
PLATFORM_DOMAINS = dict(
    youtube=('youtube.com', 'youtu.be'), tiktok=('tiktok.com',),
    facebook=('facebook.com', 'fb.watch'), instagram=('instagram.com',),
    twitter=('x.com', 'twitter.com'), reddit=('reddit.com', 'redd.it'),
    vimeo=('vimeo.com',), dailymotion=('dailymotion.com', 'dai.ly'),
    twitch=('twitch.tv',), bilibili=('bilibili.com', 'b23.tv'),
    pinterest=('pinterest.com', 'pin.it'), bluesky=('bsky.app',),
    soundcloud=('soundcloud.com', 'on.soundcloud.com'), bandcamp=('bandcamp.com',),
    mixcloud=('mixcloud.com',), audiomack=('audiomack.com',), flickr=('flickr.com', 'flic.kr'),
    imgur=('imgur.com',), tumblr=('tumblr.com',), pixiv=('pixiv.net',),
    deviantart=('deviantart.com', 'sta.sh'), unsplash=('unsplash.com',),
    vk=('vk.com', 'vkvideo.ru'), rutube=('rutube.ru',), rumble=('rumble.com',),
    streamable=('streamable.com',), archive=('archive.org',), niconico=('nicovideo.jp', 'nico.ms'),
    douyin=('douyin.com',), snapchat=('snapchat.com',))
AUDIO_ONLY = frozenset(('soundcloud', 'bandcamp', 'mixcloud', 'audiomack'))


def platform_modes(slug, status, engine):
    """Separate media capabilities; module presence is not a live-site test."""
    if slug == 'archive':
        image_status = 'unsupported'
    else:
        image_status = ('supported' if slug in engine['modules'] else 'unsupported') if engine['available'] else 'missing'
    return dict(video_status='unsupported' if slug in AUDIO_ONLY else status,
                audio_status=status, image_status=image_status)


def platform_support():
    """Inspect local extractors; this is not a network availability test."""
    try:
        from yt_dlp.extractor import get_info_extractor
        from yt_dlp.version import __version__
    except ImportError:
        return "ยังไม่ได้ติดตั้ง yt-dlp", {name: "missing" if key else "unsupported" for name, key, *_ in PLATFORMS}
    states = {}
    for name, key, *_ in PLATFORMS:
        if key is None:
            states[name] = 'unsupported'
            continue
        try:
            states[name] = "supported" if get_info_extractor(key).working() else "broken"
        except (KeyError, AttributeError, ImportError):
            states[name] = "missing"
    return __version__, states


def download_error(exc):
    detail = str(exc)
    lower = detail.lower()
    if 'requested format is not available' in lower:
        hint = 'ต้นทางไม่มีไฟล์ตามเพดานความละเอียดที่เลือก ลองเพิ่มความละเอียดหรือเลือกสูงสุดจากต้นทาง'
    elif "unsupported url" in lower:
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
