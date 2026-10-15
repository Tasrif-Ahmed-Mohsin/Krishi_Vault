"""Cut the farmer interview into the pitch's opening clip: chosen segments, English subtitles burned in,
HDR (iPhone HLG) tone-mapped to SDR, cleaned and levelled sound, 1920x1080 H.264, no metadata (the
original carries the phone's GPS location).

Usage: python make_hook_video.py <ffmpeg.exe> <source.MOV> <cuts.json> <out.mp4> <work dir>
cuts.json: {"segments": [[start, end], ...], "subtitles": [[start, end, "text", "Q" or "A"], ...] (times in the SOURCE),
            "label": "Field interview · October 2026"}
"""
import json
import subprocess
import sys
from pathlib import Path

ffmpeg, source, cuts_file, out, work = sys.argv[1:6]
cuts = json.loads(Path(cuts_file).read_text(encoding="utf-8"))
segments = cuts["segments"]
work = Path(work)
work.mkdir(parents=True, exist_ok=True)
FADE = 0.12  # seconds of audio fade at every cut, so joins do not click


def to_output_time(t):
    """Map a time in the source onto the cut timeline (None if it was cut out)."""
    offset = 0.0
    for a, b in segments:
        if a <= t <= b:
            return offset + (t - a)
        offset += b - a
    return None


def ass_time(t):
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


events = []
for a, b, text, who in cuts["subtitles"]:
    oa, ob = to_output_time(a), to_output_time(b)
    if oa is None or ob is None:
        raise SystemExit(f"subtitle {a}-{b} crosses a cut: {text}")
    style = r"{\i1\c&HC9D6CC&}" if who == "Q" else ""  # our interviewer: italic, softer colour
    events.append(f"Dialogue: 0,{ass_time(oa)},{ass_time(ob)},Sub,,0,0,0,,{style}{text}")
total = sum(b - a for a, b in segments)
if cuts.get("label"):
    events.append(f"Dialogue: 1,{ass_time(0.3)},{ass_time(4.0)},Label,,0,0,0,,{{\\fad(400,400)}}{cuts['label']}")

ass = work / "subs.ass"
ass.write_text("\n".join([
    "[Script Info]", "ScriptType: v4.00+", "PlayResX: 1920", "PlayResY: 1080", "WrapStyle: 0", "",
    "[V4+ Styles]",
    "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
    # white text on a dark, slightly see-through box, bottom centre
    "Style: Sub,Segoe UI Semibold,54,&H00FFFFFF,&H00FFFFFF,&H4023330F,&H4023330F,0,0,0,0,100,100,0,0,3,14,0,2,160,160,70,1",
    # small gold label, top left
    "Style: Label,Segoe UI Semibold,36,&H0017A3E8,&H0017A3E8,&H4023330F,&H4023330F,0,0,0,0,100,100,1,0,3,10,0,7,70,70,60,1",
    "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    *events, "",
]), encoding="utf-8")

tonemap = ("zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=hable:desat=0,"
           "zscale=t=bt709:m=bt709:r=tv,format=yuv420p")
parts, labels = [], []
for i, (a, b) in enumerate(segments):
    d = b - a
    parts.append(f"[0:v]trim={a}:{b},setpts=PTS-STARTPTS,scale=1920:1080:flags=lanczos,{tonemap}[v{i}]")
    parts.append(f"[0:a]atrim={a}:{b},asetpts=PTS-STARTPTS,afade=t=in:d={FADE},afade=t=out:st={d - FADE:.3f}:d={FADE}[a{i}]")
    labels.append(f"[v{i}][a{i}]")
n = len(segments)
sub_path = str(ass).replace("\\", "/").replace(":", "\\:")
parts.append(f"{''.join(labels)}concat=n={n}:v=1:a=1[vc][ac]")
parts.append(f"[vc]fade=t=in:d=0.5,fade=t=out:st={total - 0.6:.3f}:d=0.6,subtitles='{sub_path}'[vout]")
parts.append("[ac]highpass=f=90,afftdn=nr=10:nf=-40,loudnorm=I=-16:TP=-1.5:LRA=11,"
             f"afade=t=out:st={total - 0.6:.3f}:d=0.6[aout]")

cmd = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", source,
       "-filter_complex", ";".join(parts), "-map", "[vout]", "-map", "[aout]",
       "-c:v", "libx264", "-preset", "slow", "-crf", "25", "-profile:v", "high", "-pix_fmt", "yuv420p",
       "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
       "-r", "30", "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2",
       "-map_metadata", "-1", "-map_chapters", "-1", "-movflags", "+faststart", out]
subprocess.run(cmd, check=True)
print(f"wrote {out}: {total:.1f} s, {n} segments, {len(cuts['subtitles'])} subtitles")
