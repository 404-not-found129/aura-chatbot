[app]

title = Aura AI
package.name = aura
package.domain = com.aura.ai
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
version = 1.6.0

# All required packages. Pure-Python packages install via pip during build.
requirements = python3,kivy==2.3.0,openai,anthropic,google-genai,httpx,httpcore,h11,anyio,certifi,charset-normalizer,idna,urllib3,six,sniffio

# Orientation
orientation = portrait

# Android settings
android.permissions = INTERNET
android.api = 33
android.minapi = 26
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a

# Icons (place a 512x512 icon.png in this folder to use it)
# icon.filename = %(source.dir)s/icon.png

# Fullscreen (0 = show status bar, 1 = hide it)
fullscreen = 0

# Auto-accept Android SDK licenses
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
