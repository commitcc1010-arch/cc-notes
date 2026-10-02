"""Compare each runnable ```python block with the ```text block that immediately follows it.
Usage: .fix_outputs.py <file> [--apply]   (--apply replaces mismatched outputs with fresh ones)"""
import re, subprocess, sys

path = sys.argv[1]
apply = "--apply" in sys.argv
text = open(path, encoding="utf-8").read()
blocks = [(m.group(1), m.start(), m.end(), m.start(2), m.end(2))
          for m in re.finditer(r"(?ms)^```(\w*)\n(.*?)^```[ \t]*$", text)]
edits, changed = [], 0
for i, (lang, start, end, bs, be) in enumerate(blocks):
    if lang != "python" or text[bs:be].lstrip().startswith("# not-runnable"):
        continue
    if i + 1 >= len(blocks) or blocks[i + 1][0] != "text" or text[end:blocks[i + 1][1]].strip():
        continue
    _, _, _, ts, te = blocks[i + 1]
    proc = subprocess.run([sys.executable, "-c", text[bs:be]], capture_output=True, text=True, timeout=30)
    line = text[:start].count("\n") + 1
    if proc.returncode != 0:
        print(f"RUN FAIL at line {line}")
        continue
    if proc.stdout.strip() != text[ts:te].strip():
        changed += 1
        print(f"DIFF at line {line}")
        if apply:
            edits.append((ts, te, proc.stdout if proc.stdout.endswith("\n") else proc.stdout + "\n"))
for ts, te, new in reversed(edits):
    text = text[:ts] + new + text[te:]
if apply and edits:
    open(path, "w", encoding="utf-8").write(text)
print("changed", changed)
