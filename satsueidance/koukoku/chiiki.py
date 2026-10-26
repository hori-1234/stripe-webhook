from flask import request
import ipaddress


def get_visitor_device():
    user_agent = request.headers.get("User-Agent", "").lower()

    if "ipad" in user_agent or "tablet" in user_agent:
        return "タブレット"

    if "iphone" in user_agent or "android" in user_agent or "mobile" in user_agent:
        return "スマホ"

    return "PC"
    

def get_visitor_ip():
    ip = request.headers.get("CF-Connecting-IP", "").strip()

    if not ip:
        return None

    try:
        address = ipaddress.ip_address(ip)

        if not address.is_global:
            return None

        return str(address)

    except ValueError:
        return None


PREFECTURE_CODES = {
    "01": "北海道", "02": "青森県", "03": "岩手県",
    "04": "宮城県", "05": "秋田県", "06": "山形県",
    "07": "福島県", "08": "茨城県", "09": "栃木県",
    "10": "群馬県", "11": "埼玉県", "12": "千葉県",
    "13": "東京都", "14": "神奈川県", "15": "新潟県",
    "16": "富山県", "17": "石川県", "18": "福井県",
    "19": "山梨県", "20": "長野県", "21": "岐阜県",
    "22": "静岡県", "23": "愛知県", "24": "三重県",
    "25": "滋賀県", "26": "京都府", "27": "大阪府",
    "28": "兵庫県", "29": "奈良県", "30": "和歌山県",
    "31": "鳥取県", "32": "島根県", "33": "岡山県",
    "34": "広島県", "35": "山口県", "36": "徳島県",
    "37": "香川県", "38": "愛媛県", "39": "高知県",
    "40": "福岡県", "41": "佐賀県", "42": "長崎県",
    "43": "熊本県", "44": "大分県", "45": "宮崎県",
    "46": "鹿児島県", "47": "沖縄県"
}


def get_visitor_prefecture():
    country = request.headers.get("CF-IPCountry", "").upper()

    if country != "JP":
        return "不明"

    region_code = request.headers.get("CF-Region-Code", "").strip().upper()

    if region_code.startswith("JP-"):
        region_code = region_code[3:]

    return PREFECTURE_CODES.get(region_code, "不明")
    

def check_region_headers():
    return {
        "country": request.headers.get("CF-IPCountry", ""),
        "region_code": request.headers.get("CF-Region-Code", ""),
        "region": request.headers.get("CF-Region", "")
    }

def get_visitor_prefecture_from_ip():
    import json
    import urllib.request
    import urllib.error

    ip = get_visitor_ip()

    if not ip:
        return "不明"

    try:
        url = f"https://api.db-ip.com/v2/free/{ip}"

        with urllib.request.urlopen(url, timeout=3) as response:
            data = json.load(response)

        if data.get("countryCode") != "JP":
            return "不明"

        region = data.get("stateProv", "").strip()

        if region in PREFECTURE_CODES.values():
            return region

        return "不明"

    except (
        urllib.error.URLError,
        TimeoutError,
        ValueError,
        KeyError,
        TypeError
    ):
        return "不明"
