'''
MISC HUNTER 入口

用法:
    python hunter.py <文件1> [文件2 ...]

流程:
    1. 命令行接收目标文件
    2. 递归分析队列: 每轮产出的新文件自动重新进队列
    3. 每轮 findings 打印到终端
    4. 全部结束后写 output/report.txt

示例:
    python hunter.py samples/snake.jpg
'''

import sys
from datetime import datetime

from core.engine import Engine
from plugins.file_type import FileTypeDetector
from plugins.zip_detector import ZipDetector
from plugins.zip_extractor import ZipExtractor
from plugins.decoder import DecoderPlugin
from plugins.strings_analyzer import StringsAnalyzer
from utils.paths import OUTPUT_DIR, ensure_dirs

PLUGINS = [
    FileTypeDetector(),
    ZipDetector(),
    ZipExtractor(),
    DecoderPlugin(),
    StringsAnalyzer(),
]

# 终端输出统一 UTF-8 (Windows 控制台默认 GBK 会乱码)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SEVERITY_MARK = {"INFO": "[+]", "WARNING": "[!]", "ERROR": "[x]"}


def print_findings(context):
    """终端呈现一轮分析的所有 findings(含找到的具体内容)"""
    for f in context.findings:
        mark = SEVERITY_MARK.get(f["severity"], "[?]")
        print(f"  {mark} {f['message']}")
        data = f.get("data") or {}

        # 各种 finding 的详细内容, 直接展示在终端
        if f["code"] == "FLAG_FOUND":
            print(f"     >>> FLAG: {data['flag']}")
        elif f["code"] == "DECODED":
            for i, layer in enumerate(data.get("layers", [])):
                text = layer["result"].strip()
                if len(text) > 200:
                    text = text[:200] + "..."
                print(f"     解码第{i+1}层 [{layer['decoder']}]: {text}")
        elif f["code"] == "STRINGS_EXTRACTED":
            for s in data.get("preview", []):
                print(f"     | {s}")
            if data.get("count", 0) > len(data.get("preview", [])):
                print(f"     | ... 共{data['count']}条, 完整内容见文件")


def run_analysis(targets):
    """递归分析队列, 返回所有轮次的 context 列表(供报告使用)"""
    analyzed = set()
    contexts = []

    while targets:
        target = targets.pop()
        if target in analyzed:
            continue
        analyzed.add(target)

        print(f"\n[分析] {target}")
        context = Engine(target, PLUGINS).run()
        contexts.append(context)
        print_findings(context)

        for file in context.extracted_files:
            path = file["path"]
            if path not in analyzed:
                print(f"  [+] 提取新文件: {path}")
                targets.append(path)

    return contexts


def write_report(contexts):
    """把每轮分析的 findings/extracted 汇总成 output/report.txt"""
    ensure_dirs()
    lines = []
    lines.append("=" * 44)
    lines.append("MISC HUNTER REPORT")
    lines.append("=" * 44)
    lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    all_flags = []

    for ctx in contexts:
        lines.append("-" * 44)
        lines.append(f"目标: {ctx.target}")

        # 文件类型: 从 FileTypeDetector 的 finding 里找
        ftype = "未知"
        for f in ctx.findings:
            if f["code"] == "FILE_TYPE_DETECTED":
                ftype = f["data"].get("type", "未知")
        lines.append(f"文件类型: {ftype}")
        lines.append("")

        lines.append("Findings:")
        for f in ctx.findings:
            mark = SEVERITY_MARK.get(f["severity"], "[?]")
            lines.append(f"  {mark} [{f['code']}] {f['message']}")
            if f["code"] == "FLAG_FOUND":
                all_flags.append(f["data"]["flag"])
        lines.append("")

        if ctx.extracted_files:
            lines.append("Extracted:")
            for e in ctx.extracted_files:
                lines.append(f"  - {e['path']}")
            lines.append("")

    lines.append("=" * 44)
    lines.append("FLAG 汇总")
    lines.append("=" * 44)
    if all_flags:
        for flag in all_flags:
            lines.append(f"  flag: {flag}")
    else:
        lines.append("  未发现 flag")
    lines.append("")
    lines.append("=" * 44)

    report_path = OUTPUT_DIR / "report.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return report_path


def main():
    targets = sys.argv[1:]
    if not targets:
        print("用法: python hunter.py <文件1> [文件2 ...]")
        print("示例: python hunter.py samples/snake.jpg")
        return

    ensure_dirs()
    contexts = run_analysis(targets)
    report_path = write_report(contexts)
    print(f"\n[完成] 报告已写入: {report_path}")


if __name__ == "__main__":
    main()
