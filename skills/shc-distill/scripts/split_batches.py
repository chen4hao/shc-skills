"""拆分 SRT 字幕為多個翻譯批次。

用法: uv run python3 split_batches.py <INPUT_SRT> <OUTPUT_DIR> [NUM_BATCHES]
  INPUT_SRT: 清理後的英文 SRT 檔案路徑
  OUTPUT_DIR: 批次檔案輸出目錄
  NUM_BATCHES: 批次數量（預設 5）
"""
import re, os, sys, math

def split_srt(input_path, output_dir, num_batches=5):
    with open(input_path) as f:
        content = f.read()
    blocks = [b.strip() for b in re.split(r'\n\n+', content.strip()) if '-->' in b]
    per_batch = math.ceil(len(blocks) / num_batches)
    for i in range(num_batches):
        batch = blocks[i*per_batch : (i+1)*per_batch]
        if not batch:
            continue
        path = os.path.join(output_dir, f"en_batch_{i+1}.srt")
        with open(path, 'w') as f:
            for block in batch:
                f.write(f"{block}\n\n")
        print(f"Batch {i+1}: {len(batch)} entries -> {path}")
    print(f"Total: {len(blocks)} entries in {num_batches} batches")

num_batches = int(sys.argv[3]) if len(sys.argv) > 3 else 5
split_srt(sys.argv[1], sys.argv[2], num_batches)
