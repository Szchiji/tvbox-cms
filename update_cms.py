#!/usr/bin/env python3
"""Probe MacCMS endpoints and rewrite tvbox_cms.json.

Rules:
- Existing sites are kept verbatim (key, name, flags, categories and any other
  fields) in their current order; searchable/quickSearch are never changed by
  this script (search is curated by hand). Several entries may share one api
  (e.g. the "奈飞·xxx" category views), so existing entries dedupe by key.
- Newly discovered live sites are appended with searchable=0, quickSearch=0.
- Timeouts/errors keep the existing entry as is. Clearly broken existing sites
  are not deleted: they move to the bottom with searchable/quickSearch off.
- Adult / blocked sources are never added; an existing one (e.g. 玉兔) is kept
  but always has searchable/quickSearch forced off.
- Refuses to write if fewer than 8 live sites remain.
Usage: python update_cms.py [--dry-run] [--out PATH]
"""
import argparse
import json
import ssl
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

OUT = Path("tvbox_cms.json")
CTX = ssl.create_default_context()

# Adult or otherwise unwanted sources: matched against name and api URL.
BLOCKLIST = ("apiyutu", "玉兔")

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
    ("360", "https://360zyzz.com/api.php/provide/vod/"),
    ("360备用", "https://360zy.com/api.php/provide/vod/"),
    ("茅台", "https://caiji.maotaizy.cc/api.php/provide/vod/"),
    ("茅台备用", "https://caiji.maotai999.vip/api.php/provide/vod/"),
    ("爱奇艺资源", "https://iqiyizyapi.com/api.php/provide/vod/"),
    ("新浪", "https://api.xinlangapi.com/xinlangapi.php/provide/vod/"),
    ("电影天堂", "http://caiji.dyttzyapi.com/api.php/provide/vod/"),
    ("电影天堂S", "https://caiji.dyttzyapi.com/api.php/provide/vod/"),
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
    ("卧龙", "https://collect.wolongzyw.com/api.php/provide/vod/"),
    ("黑木耳", "https://json.heimuer.xyz/api.php/provide/vod/"),
    ("天空", "https://api.tiankongapi.com/api.php/provide/vod/"),
    ("飞速", "https://www.feisuzyapi.com/api.php/provide/vod/"),
    ("快播", "https://caiji.kczyapi.com/api.php/provide/vod/"),
]


def blocked(name, api):
    text = (name or "") + " " + (api or "")
    return any(b in text for b in BLOCKLIST)


def norm(api):
    # Ignore the query string (e.g. "?from=xxm3u8", used to keep only the
    # direct-m3u8 play group) so a tuned entry still matches its candidate.
    return (api or "").split("?", 1)[0].rstrip("/")


def probe(name, api):
    url = api + ("&" if "?" in api else "?") + "ac=list&pg=1"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 TVBox"})
    try:
        with urllib.request.urlopen(req, timeout=12, context=CTX) as resp:
            raw = resp.read(262144).decode("utf-8", "ignore")
    except Exception as exc:
        return name, api, "keep", str(exc)[:80]
    try:
        body = json.loads(raw)
        items = body.get("list") or []
        ok = bool(items) and isinstance(items[0], dict) and any(k.startswith("vod_") for k in items[0])
    except Exception:
        ok = '"code"' in raw and '"list"' in raw and "vod_" in raw
    if ok:
        return name, api, "ok", raw[:40]
    return name, api, "drop", raw[:40].replace("\n", " ")


def new_site(name, api):
    return {
        "key": "cms_" + name,
        "name": name,
        "type": 1,
        "api": api,
        "searchable": 0,
        "quickSearch": 0,
        "filterable": 0,
        "changeable": 1,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="probe and print, do not write")
    ap.add_argument("--out", default=str(OUT), help="config file to read/write")
    args = ap.parse_args()
    out = Path(args.out)

    old_data = {}
    old_sites = []
    if out.exists():
        try:
            old_data = json.loads(out.read_text(encoding="utf-8"))
            old_sites = [s for s in old_data.get("sites", []) if isinstance(s, dict)]
        except Exception:
            old_data, old_sites = {}, []

    # Probe every existing site plus every candidate, once per api.
    targets = {}
    for s in old_sites:
        targets.setdefault(norm(s.get("api")), (s.get("name") or s.get("key"), s.get("api")))
    for n, a in CANDIDATES:
        targets.setdefault(norm(a), (n, a))
    targets = {k: v for k, v in targets.items() if k and not blocked(*v)}

    with ThreadPoolExecutor(16) as pool:
        results = list(pool.map(lambda v: probe(*v), targets.values()))
    status = {norm(api): (st, info) for _, api, st, info in results}

    picked, seen, seen_keys, broken = [], set(), set(), []
    # 1) existing sites, in their current order, kept verbatim
    for s in old_sites:
        key = norm(s.get("api"))
        site_key = s.get("key")
        if not key or not site_key or site_key in seen_keys:
            continue
        seen.add(key)
        seen_keys.add(site_key)
        if blocked(s.get("name"), s.get("api")):
            s["searchable"] = 0
            s["quickSearch"] = 0
            print("BLOCKED(kept, search off)", s.get("name"))
            picked.append(s)
            continue
        st, info = status.get(key, ("keep", "not probed"))
        if st in ("ok", "keep"):
            picked.append(s)
            print(st.upper(), s.get("name"), "searchable=%s" % s.get("searchable", 0), info)
        else:
            s["searchable"] = 0
            s["quickSearch"] = 0
            broken.append(s)
            print("BROKEN(moved to bottom, search off)", s.get("name"), info)
    # 2) newly discovered live candidates, search off by default
    used_keys = {s.get("key") for s in picked}
    for name, api in CANDIDATES:
        key = norm(api)
        if key in seen or blocked(name, api):
            continue
        st, info = status.get(key, ("drop", ""))
        if st == "ok":
            site = new_site(name, api)
            if site["key"] in used_keys:
                site["key"] += "_" + str(len(picked))
            picked.append(site)
            used_keys.add(site["key"])
            seen.add(key)
            print("NEW", name, info)

    # 3) broken existing sites go last (kept so they can come back)
    picked.extend(broken)

    live = sum(1 for s in picked if status.get(norm(s.get("api")), ("",))[0] == "ok")
    if live < 8:
        raise SystemExit("too few live sites (%d), refuse to overwrite" % live)

    data = dict(old_data) if old_data else {}
    data.setdefault("spider", "")
    data.setdefault("wallpaper", "")
    data["sites"] = picked
    data.setdefault("parses", [
        {"name": "Json并发", "type": 2, "url": "Parallel"},
        {"name": "Json轮询", "type": 2, "url": "Sequence"},
    ])
    data.setdefault("flags", ["youku", "qq", "iqiyi", "qiyi", "letv", "sohu", "tudou", "pptv", "mgtv", "wasu", "bilibili", "m3u8"])
    data.setdefault("ads", ["mimg.*=http", "vip\\.ffzy", "vip\\.lz", "v\\.cdnlz"])
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    json.loads(text)
    searchable = [s.get("name") for s in picked if s.get("searchable")]
    print("sites:", len(picked), "live:", live, "searchable:", searchable)
    if args.dry_run:
        print("dry run, not written")
        return
    out.write_text(text, encoding="utf-8")
    print("wrote", len(picked), "sites to", out)


if __name__ == "__main__":
    main()
