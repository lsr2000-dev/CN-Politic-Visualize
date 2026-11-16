from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "scripts" / "committee_bios.json"
UA = "CN-Politic-Visualize/1.0 (local)"


def request(params: dict) -> dict:
    url = "https://zh.wikipedia.org/w/api.php?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=25) as response:
        return json.loads(response.read().decode("utf-8"))


def find(name: str) -> str | None:
    search = request({
        "action": "query", "list": "search", "srsearch": name,
        "srlimit": "1", "format": "json",
    })
    hits = search.get("query", {}).get("search", [])
    if not hits:
        return None
    title = hits[0]["title"]
    page = request({
        "action": "query", "prop": "extracts", "explaintext": "1",
        "exintro": "1", "format": "json", "redirects": "1", "titles": title,
    })
    for item in page.get("query", {}).get("pages", {}).values():
        return item.get("extract")
    return None


def parse(text: str) -> tuple[int | None, str | None]:
    birth = re.search(r"[（(]\s*(19\d{2}|20\d{2})\s*年", text)
    native = re.search(r"[，,]\s*([^，。；\n]{2,20}?)人", text)
    return (
        int(birth.group(1)) if birth else None,
        native.group(1).strip() if native else None,
    )


def main() -> None:
    bios = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    names = "王庭凯 方红卫 付文化 朱文祥 刘仲华 刘敬桢 安伟 农生文 李贤玉 吴强 邱勇 谷澍 沈莹 张伟 张政 陈杰 陈宏敏 周建国 洪庆 袁洁 黄如 黄志强 常进 普布顿珠 王旭东 肖川 余剑锋".split()
    for i, name in enumerate(names, 1):
        try:
            text = find(name)
            if text:
                birth, native = parse(text)
                print(i, name, birth, native)
                if birth and native:
                    bios[name] = {"birth_year": birth, "native_place": native}
        except Exception as exc:  # noqa: BLE001
            print(i, name, "ERR", exc)
        time.sleep(1.5)
    OUT.write_text(json.dumps(bios, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("missing", [n for n in names if not bios.get(n, {}).get("birth_year")])


if __name__ == "__main__":
    main()
