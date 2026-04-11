"""將 SRT 字幕檔轉換為純文字（去除序號和時間戳）。

用法: uv run python3 srt_to_text.py <SRT_FILE> [OUTPUT_FILE]
  SRT_FILE:    輸入的 .clean.srt 檔案路徑
  OUTPUT_FILE: 輸出純文字檔路徑（預設為 SRT_FILE 去掉 .srt 加 .txt）

輸出：每條字幕的文字佔一行，去除序號和時間戳。
適用於主代理用 Read 工具讀取內容撰寫筆記，減少 Read 次數和 context 佔用。
"""
import re, sys, os

srt_path = sys.argv[1]
if len(sys.argv) > 2:
    out_path = sys.argv[2]
else:
    out_path = re.sub(r'\.srt$', '.txt', srt_path)

with open(srt_path, 'r', encoding='utf-8') as f:
    content = f.read()

blocks = re.split(r'\n\n+', content.strip())
lines_out = []
for block in blocks:
    lines = block.strip().split('\n')
    text_lines = []
    for line in lines:
        line = line.strip()
        # 跳過序號行（純數字）和時間戳行（含 -->）
        if re.match(r'^\d+$', line):
            continue
        if '-->' in line:
            continue
        if line:
            text_lines.append(line)
    if text_lines:
        lines_out.append(' '.join(text_lines))

with open(out_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines_out) + '\n')

print(f"  {srt_path} -> {out_path}")
print(f"  {len(lines_out)} 行純文字（原 {len(blocks)} 條字幕）")
