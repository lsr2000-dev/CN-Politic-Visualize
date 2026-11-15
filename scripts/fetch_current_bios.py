import json
import re
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from current_roster import CURRENT_PRINCIPALS  # noqa: E402

TAG_RE = re.compile(r"<[^>]+>")
ANCHOR_RE = re.compile(r'<a\s+[^>]*href="([^"]+)"[^>]*>(.*?)</a>', re.I | re.S)


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", TAG_RE.sub(" ", text)).strip()


def candidates(html: str, name: str) -> list[str]:
    found = []
    for href, label in ANCHOR_RE.findall(html):
        if name in clean(label):
            found.append(href)
    return list(dict.fromkeys(found))


def parse_bio(text: str, name: str) -> dict | None:
    plain = clean(text)
    # locate the name's bio paragraph; profile pages usually say "NAME，男，汉族，1965年..."
    positions = [m.start() for m in re.finditer(re.escape(name), plain)]
    for pos in positions:
        window = plain[pos:pos + 600]
        birth = re.search(r"(19[2-9]\d)年(?:\d{1,2}月)?(?:生|出生)", window)
        if not birth:
            continue
        native = None
        m = re.search(r"(?:出生|生)[，,]\s*([\u4e00-\u9fa5]{2,15})人", window)
        if m:
            native = m.group(1)
        else:
            m = re.search(r"籍贯[：:是为\s]*([\u4e00-\u9fa5]{2,15})", window)
            if m:
                native = m.group(1)
        if native in {"人民", "中国", "中华"}:
            native = None
        return {"birth_year": int(birth.group(1)), "native_place": native}
    return None


def main() -> None:
    client = httpx.Client(follow_redirects=True, timeout=15)
    result = {}
    unmatched = []
    for code, teams in CURRENT_PRINCIPALS.items():
        source = next((v[1] for v in teams.values() if v and v[1]), None)
        if not source:
            continue
        try:
            page = client.get(source).content.decode("utf-8", "ignore")
        except Exception as exc:
            print("page fail", code, exc)
            continue
        for category, item in teams.items():
            if not item or not item[0]:
                continue
            name = item[0]
            urls = candidates(page, name)
            bio = None
            for url in urls[:4]:
                if url.startswith("./"):
                    url = source.rsplit("/", 1)[0] + url[1:]
                elif url.startswith("/"):
                    url = "http://district.ce.cn" + url
                elif not url.startswith("http"):
                    url = source.rsplit("/", 1)[0] + "/" + url
                try:
                    profile = client.get(url).content.decode("utf-8", "ignore")
                except Exception:
                    continue
                bio = parse_bio(profile, name)
                if bio:
                    break
            if bio:
                result[name] = bio
            else:
                unmatched.append((code, category, name, len(urls)))
    print("matched", len(result), "unmatched", len(unmatched))
    print(json.dumps(result, ensure_ascii=False, indent=1))
    print("UNMATCHED", json.dumps(unmatched, ensure_ascii=False))
    (ROOT / ".scrape").mkdir(exist_ok=True)
    (ROOT / ".scrape" / "current_bios.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
