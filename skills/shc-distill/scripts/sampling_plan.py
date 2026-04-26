"""產生 SRT Read 呼叫的 sampling plan

用法：
  uv run python3 sampling_plan.py <SRT路徑> [--mode zh-podcast|en-translation]

依據規則：
  - feedback_chinese_podcast_srt_reading.md (中文演講/Q&A 純中文流程)
  - feedback_srt_read_budget.md (英文訪談+翻譯子代理)
  - feedback_srt_read_short_interview.md (<400 條短訪談)

避免主代理心算 offset 錯誤、超出讀量上限。stdout 印出可直接複製的 Read 工具呼叫清單。
"""
import argparse
import math
import sys
from pathlib import Path


def count_srt_entries(srt_path: Path) -> tuple[int, int]:
    """回傳 (條目數, 行數)。SRT 條目以空行分隔，每條約 4 行（序號+時間戳+文字+空行）。"""
    text = srt_path.read_text(encoding="utf-8", errors="replace")
    lines = text.split("\n")
    entries = sum(1 for ln in lines if ln.strip().isdigit() and ln.strip() != "0")
    return entries, len(lines)


def plan_zh_podcast(entries: int, total_lines: int) -> list[tuple[int, int, str]]:
    """純中文演講/Q&A 規則：依條目數選 plan。回傳 [(offset, limit, label), ...]"""
    if entries < 400:
        return [
            (0, 500, "head 0-4:50"),
            (max(total_lines - 200, 500), 200, "tail 最後 ~200 行"),
        ]
    if 400 <= entries < 800:
        # ~1500 行：head 400 + mid 400 + mid 400 + tail 200
        return [
            (0, 400, "head 0-3:50"),
            (round(total_lines * 0.30), 400, "mid1 ~30%"),
            (round(total_lines * 0.60), 400, "mid2 ~60%"),
            (max(total_lines - 200, 0), 200, "tail 最後 200 行"),
        ]
    if 800 <= entries < 1500:
        # ~2000 行：head 300 + mid×3 (各 400) + tail 236
        return [
            (0, 300, "head 0-2:50"),
            (round(total_lines * 0.20), 400, "mid1 ~20%"),
            (round(total_lines * 0.42), 400, "mid2 ~42%"),
            (round(total_lines * 0.65), 400, "mid3 ~65%"),
            (max(total_lines - 236, 0), 236, "tail 最後 236 行"),
        ]
    # >=1500：~2500 行，head 300 + 5 段等間距 + tail 236
    plan = [(0, 300, "head 0-2:50")]
    # 5 段 mid，每段 400 行，覆蓋 15%-85% 區間
    for i in range(5):
        ratio = 0.15 + i * 0.14  # 15%, 29%, 43%, 57%, 71%
        plan.append((round(total_lines * ratio), 400, f"mid{i+1} ~{int(ratio*100)}%"))
    plan.append((max(total_lines - 236, 0), 236, "tail 最後 236 行"))
    return plan


def plan_en_translation(entries: int, total_lines: int) -> list[tuple[int, int, str]]:
    """英文訪談+翻譯子代理規則：head + tail 共 700 行硬上限。中段由子代理回傳。"""
    if entries < 400:
        # 短訪談例外
        return [
            (0, 500, "head 0-4:50"),
            (max(total_lines - 200, 500), 200, "tail 最後 200 行"),
        ]
    return [
        (0, 500, "head limit=500（英文 SRT 規則）"),
        (max(total_lines - 200, 0), 200, "tail 最後 200 行"),
    ]


def main():
    parser = argparse.ArgumentParser(description="產生 SRT Read 呼叫的 sampling plan")
    parser.add_argument("srt_path", help="SRT 檔絕對路徑")
    parser.add_argument(
        "--mode",
        choices=["zh-podcast", "en-translation"],
        default="zh-podcast",
        help="zh-podcast: 純中文無翻譯子代理（讀量~2000 行）；en-translation: 英文+翻譯子代理（700 行硬上限）",
    )
    args = parser.parse_args()

    srt = Path(args.srt_path)
    if not srt.exists():
        print(f"❌ 檔案不存在：{srt}", file=sys.stderr)
        sys.exit(1)

    entries, total_lines = count_srt_entries(srt)
    print(f"SRT_PATH={srt}")
    print(f"ENTRIES={entries}")
    print(f"TOTAL_LINES={total_lines}")
    print(f"MODE={args.mode}")
    print()

    if args.mode == "zh-podcast":
        plan = plan_zh_podcast(entries, total_lines)
    else:
        plan = plan_en_translation(entries, total_lines)

    total_read = sum(lim for _, lim, _ in plan)
    print(f"PLAN ({len(plan)} 個 Read，總計 {total_read} 行):")
    for i, (offset, limit, label) in enumerate(plan, 1):
        print(f"  Read #{i}: offset={offset:5d} limit={limit:4d}  # {label}")
    print()

    upper = 2000 if args.mode == "zh-podcast" else 700
    if total_read > upper * 1.25:
        print(f"⚠️  總讀量 {total_read} 行超過建議上限 {upper} 行的 1.25x", file=sys.stderr)

    print("# 直接複製為同訊息並行 Read 工具呼叫：")
    for offset, limit, _ in plan:
        print(
            f'Read(file_path="{srt}", offset={offset}, limit={limit})'
        )


if __name__ == "__main__":
    main()
