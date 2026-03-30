import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
project = json.loads((ROOT/"01_CONFIG/project_config.json").read_text(encoding="utf-8"))
sp = project["section_plan"]
sections = []
t = 0
sections.append({"label":"title_intro","start":t,"end":t+sp["title_intro_sec"],"loop_variant":"loop_clean.mp4","title":"intro"}); t += sp["title_intro_sec"]
sections.append({"label":"intro","start":t,"end":t+sp["intro_sec"],"loop_variant":"loop_clean.mp4"}); t += sp["intro_sec"]
sections.append({"label":"body_a","start":t,"end":t+sp["body_a_sec"],"loop_variant":"loop_zoom_drift.mp4"}); t += sp["body_a_sec"]
sections.append({"label":"hook_a","start":t,"end":t+sp["hook_a_sec"],"loop_variant":"loop_glow_breath.mp4","lyric_style":"hook_highlight"}); t += sp["hook_a_sec"]
sections.append({"label":"body_b","start":t,"end":t+sp["body_b_sec"],"loop_variant":"loop_vignette_pulse.mp4"}); t += sp["body_b_sec"]
sections.append({"label":"climax","start":t,"end":t+sp["climax_sec"],"loop_variant":"loop_climax_lift.mp4","lyric_style":"hook_highlight"}); t += sp["climax_sec"]
sections.append({"label":"outro","start":max(0, project["song_duration_sec"]-sp["outro_sec"]-sp["title_outro_sec"]),"end":max(0, project["song_duration_sec"]-sp["title_outro_sec"]),"loop_variant":"loop_vignette_pulse.mp4"})
sections.append({"label":"title_outro","start":max(0, project["song_duration_sec"]-sp["title_outro_sec"]),"end":project["song_duration_sec"],"loop_variant":"loop_clean.mp4","title":"outro"})
(ROOT/"03_WORK/sections/timeline.json").write_text(json.dumps({"sections":sections}, indent=2), encoding="utf-8")
print("Timeline written.")
