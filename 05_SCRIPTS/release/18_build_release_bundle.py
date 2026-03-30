import json, shutil
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
project = json.loads((ROOT/"01_CONFIG/project_config.json").read_text(encoding="utf-8"))
bundle = ROOT/"04_OUTPUT/release_bundle"/project["release_bundle_name"]
if bundle.exists():
    shutil.rmtree(bundle)
bundle.mkdir(parents=True, exist_ok=True)

targets = [
    ROOT/"04_OUTPUT/youtube_16x9/master_clean.mp4",
    ROOT/"04_OUTPUT/youtube_16x9/master_lyrics.mp4",
    ROOT/"04_OUTPUT/youtube_16x9/master_softsubs.mp4",
    ROOT/"04_OUTPUT/vertical_9x16/vertical_lyrics.mp4",
    ROOT/"04_OUTPUT/square_1x1/square_lyrics.mp4",
    ROOT/"04_OUTPUT/delivery_manifest.json",
    ROOT/"03_WORK/reports/release_readiness_report.json",
]
for p in targets:
    if p.exists():
        shutil.copy2(p, bundle/p.name)

teaser_dir = bundle/"teasers"
teaser_dir.mkdir(exist_ok=True)
for p in (ROOT/"04_OUTPUT/teasers").glob("*.mp4"):
    shutil.copy2(p, teaser_dir/p.name)

shutil.copy2(ROOT/"01_CONFIG/project_config.json", bundle/"project_config.json")
print(f"Built release bundle: {bundle}")
