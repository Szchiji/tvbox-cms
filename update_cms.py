#!/usr/bin/env python3
"""Probe MacCMS endpoints and rewrite tvbox_cms.json. Timeouts keep the old entry."""
import json
import ssl
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

OUT = Path("tvbox_cms.json")
CTX = ssl.create_default_context()

CANDIDATES = [
    ("量子", "https://cj.lziapi.com/api.php/provide/vod/"),
    ("量子备用", "https://lzizy1.com/api.php/provide/vod/"),
    ("量子采集", "https://cj.lzcaiji.com/api.php/provide/vod/"),
    ("量子影视", "http://www.lzzy.tv/api.php/provide/vod/"),
    ("非凡", "https://cj.ffzyapi.com/api.php/provide/vod/"),
    ("非凡备用", "https://ffzy.tv/api.php/provide/vod/"),
    ("非凡API", "https://api.ffzyapi.com/api.php/provide/vod/"),
    ("红牛", "https://www.hongniuzy2.com/api.php/provide/vod/"),
    ("红牛备用", "https://www.hongniuzy3.com/api.php/provide/vod/"),
    ("暴风", "https://bfzyapi.com/api.php/provide/vod/"),
    ("光速", "https://api.guangsuapi.com/api.php/provide/vod/"),
    ("索尼", "https://suoniapi.com/api.php/provide/vod/"),
    ("极速", "https://jszyapi.com/api.php/provide/vod/"),
    ("无尽", "https://api.wujinapi.me/api.php/provide/vod/"),
    ("无尽备用", "https://api.wujinapi.com/api.php/provide/vod/"),
    ("樱花", "https://m3u8.apiyhzy.com/api.php/provide/vod/"),
    ("百度", "https://api.apibdzy.com/api.php/provide/vod/"),
    ("iKun", "https://ikunzyapi.com/api.php/provide/vod/"),
    ("iKun主站", "https://www.ikunzy.com/api.php/provide/vod/"),
    ("U酷", "https://api.ukuapi.com/api.php/provide/vod/"),
    ("U酷88", "https://api.ukuapi88.com/api.php/provide/vod/"),
    ("闪电", "https://sdzyapi.com/api.php/provide/vod/"),
    ("闪电备用", "https://xsd.sdzyapi.com/api.php/provide/vod/"),
    ("火狐", "https://hhzyapi.com/api.php/provide/vod/"),
    ("虎牙", "https://www.huyaapi.com/api.php/provide/vod/"),
    ("最大", "https://api.zuidapi.com/api.php/provide/vod/"),
    ("最大备用", "http://zuidazy.me/api.php/provide/vod/"),
    ("如意", "https://cj.rycjapi.com/api.php/provide/vod/"),
    ("魔都", "https://www.mdzyapi.com/api.php/provide/vod/"),
    ("魔都动漫", "https://caiji.moduapi.cc/api.php/provide/vod/"),
    ("金鹰", "https://jyzyapi.com/provide/vod/"),
    ("金鹰主站", "https://jinyingzy.com/api.php/provide/vod/"),
    ("速播", "https://subocaiji.com/api.php/provide/vod/"),
    ("360", "https://360zy.com/api.php/provide/vod/"),
    ("360备用", "https://360zyzz.com/api.php/provide/vod/"),
    ("茅台", "https://caiji.maotaizy.cc/api.php/provide/vod/"),
    ("茅台备用", "https://caiji.maotai999.vip/api.php/provide/vod/"),
    ("爱奇艺资源", "https://iqiyizyapi.com/api.php/provide/vod/"),
    ("新浪", "https://api.xinlangapi.com/xinlangapi.php/provide/vod/"),
    ("电影天堂", "http://caiji.dyttzyapi.com/api.php/provide/vod/"),
    ("天涯", "https://tyyszy.com/api.php/provide/vod/"),
    ("天涯备用", "https://tyyszyapi.com/api.php/provide/vod/"),
    ("豆瓣资源", "https://caiji.dbzy5.com/api.php/provide/vod/"),
    ("豆瓣主站", "https://dbzy.tv/api.php/provide/vod/"),
    ("牛牛", "https://api.niuniuzy.me/api.php/provide/vod/"),
    ("猫眼", "https://api.maoyanapi.top/api.php/provide/vod/"),
    ("西瓜", "https://caiji.xgzyapi.com/api.php/provide/vod/"),
    ("艾旦", "https://lovedan.net/api.php/provide/vod/"),
    ("无水印", "https://api.wsyzy.net/api.php/provide/vod/"),
    ("OK资源", "https://api.okzyw.net/api.php/provide/vod/"),
    ("鸭鸭", "https://cj.yayazy.net/api.php/provide/vod/"),
    ("快车", "https://caiji.kuaichezy.org/api.php/provide/vod/"),
    ("1080", "https://api.1080zyku.com/inc/apijson.php"),
    ("优质", "https://api.yzzy-api.com/inc/apijson.php"),
    ("巨量", "https://api.juliang.live/api/provide/vod/"),
    ("玉兔", "https://apiyutu.com/api.php/provide/vod/"),
    ("卧龙", "https://collect.wolongzyw.com/api.php/provide/vod/"),
    ("黑木耳", "https://json.heimuer.xyz/api.php/provide/vod/"),
    ("天空", "https://api.tiankongapi.com/api.php/provide/vod/"),
    ("飞速", "https://www.feisuzyapi.com/api.php/provide/vod/"),
    ("快播", "https://caiji.kczyapi.com/api.php/provide/vod/"),
]


def probe(name, api):
    url = api + ("&" if "?" in api else "?") + "ac=list&pg=1"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 TVBox"})
    try:
        with urllib.request.urlopen(req, timeout=12, context=CTX) as resp:
            raw = resp.read(700).decode("utf-8", "ignore")
    except Exception as exc:
        return name, api, "keep", str(exc)[:80]
    ok = '"code"' in raw and "list" in raw and "vod_" in raw
    if ok:
        return name, api, "ok", raw[:40]
    return name, api, "drop", raw[:40].replace("\n", " ")


def site(name, api):
    return {
        "key": "cms_" + name,
        "name": name,
        "type": 1,
        "api": api,
        "searchable": 1,
        "quickSearch": 1,
        "filterable": 0,
        "changeable": 1,
    }


def main():
    old = {}
    if OUT.exists():
        try:
            for item in json.loads(OUT.read_text()).get("sites", []):
                old[item.get("api", "").rstrip("/")] = item.get("name") or item.get("key")
        except Exception:
            old = {}

    results = []
    with ThreadPoolExecutor(16) as pool:
        futs = [pool.submit(probe, n, a) for n, a in CANDIDATES]
        for fut in as_completed(futs):
            results.append(fut.result())

    order = {api: i for i, (_, api) in enumerate(CANDIDATES)}
    picked = []
    seen = set()
    for name, api, status, info in sorted(results, key=lambda r: order.get(r[1], 999)):
        key = api.rstrip("/")
        if key in seen:
            continue
        if status == "ok" or (status == "keep" and key in old):
            picked.append(site(name, api))
            seen.add(key)
            print(status.upper(), name, info)
        else:
            print("DROP", name, info)

    if len(picked) < 8:
        raise SystemExit("too few live sites, refuse to overwrite")

    data = {
        "spider": "",
        "wallpaper": "",
        "sites": picked,
        "parses": [
            {"name": "Json并发", "type": 2, "url": "Parallel"},
            {"name": "Json轮询", "type": 2, "url": "Sequence"},
        ],
        "flags": ["youku", "qq", "iqiyi", "qiyi", "letv", "sohu", "tudou", "pptv", "mgtv", "wasu", "bilibili", "m3u8"],
        "ads": ["mimg.*=http", "vip\\.ffzy", "vip\\.lz", "v\\.cdnlz"],
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    print("wrote", len(picked), "sites")


if __name__ == "__main__":
    main()
