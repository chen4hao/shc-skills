"""使用 OpenCC 進行中文簡繁轉換。

用法: uv run python3 opencc_convert.py <INPUT_PATH> <OUTPUT_PATH> [--config CONFIG]
  INPUT_PATH: 輸入檔案路徑
  OUTPUT_PATH: 輸出檔案路徑
  --config: OpenCC 轉換配置（預設 "s2twp"，即簡體→繁體臺灣用語）

常用配置：
  s2twp  簡體 → 繁體（臺灣用語）【預設】
  s2t    簡體 → 繁體
  t2s    繁體 → 簡體
  s2hk   簡體 → 繁體（香港用語）
  tw2sp  繁體（臺灣）→ 簡體
"""
import argparse, sys

parser = argparse.ArgumentParser(description="OpenCC Chinese conversion")
parser.add_argument('input_path', help='Input file path')
parser.add_argument('output_path', help='Output file path')
parser.add_argument('--config', default='s2twp', help='OpenCC config (default: s2twp)')
args = parser.parse_args()

try:
    import opencc
except ImportError:
    print("❌ OpenCC 未安裝，請執行: uv pip install opencc-python-reimplemented")
    sys.exit(1)

converter = opencc.OpenCC(args.config)

with open(args.input_path, 'r', encoding='utf-8') as f:
    content = f.read()

converted = converter.convert(content)

with open(args.output_path, 'w', encoding='utf-8') as f:
    f.write(converted)

# 統計
in_chars = len(content)
out_chars = len(converted)
diff_chars = sum(1 for a, b in zip(content, converted) if a != b)
print(f"✅ 轉換完成: {args.config}")
print(f"  輸入: {args.input_path} ({in_chars} 字元)")
print(f"  輸出: {args.output_path} ({out_chars} 字元)")
print(f"  變更: {diff_chars} 字元被轉換")
