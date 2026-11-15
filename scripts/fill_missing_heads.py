from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEED = ROOT / "scripts" / "central_seed.py"

HEADS = {
    "government:energy": ("王宏志", "局长", "D"),
    "government:defense_science": ("单忠德", "局长", "D"),
    "government:tobacco": ("张建民", "局长", "D"),
    "government:forestry": ("刘国洪", "局长", "D"),
    "government:railway": ("宋修德", "局长", "D"),
    "government:disease_control": ("沈洪兵", "局长", "D"),
    "government:fire_rescue": ("周天", "局长", "D"),
    "government:hk_liaison": ("周霁", "主任", "D"),
    "government:macau_liaison": ("郑新聪", "主任", "D"),
    "government:hk_security": ("董经纬", "署长", "D"),
}

lines = SEED.read_text(encoding="utf-8").splitlines()
for index, line in enumerate(lines):
    for node_id, (name, title, start) in HEADS.items():
        prefix = f'    ("{node_id}",'
        if line.startswith(prefix) and line.rstrip().endswith("[]),"):
            lines[index] = line.rstrip()[:-4] + f'[("{name}", "{title}", {start}, None, "principal")]),'
            break
SEED.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("updated", len(HEADS))
