# MISC Hunter

> **MISC Hunter is a modular CTF MISC analysis toolkit designed to automate repetitive file-analysis, extraction, steganography detection, and recursive artifact analysis workflows.**
>
> MISC Hunter 是一个模块化的 CTF MISC 分析工具，用于自动化执行重复性的文件分析、数据提取、隐写检测和递归分析流程。

**版本: v1.0** · 纯 Python 标准库实现，零第三方依赖，Kali Linux / Windows 均可运行

---

## 定位

工具负责大量重复、机械、规则明确的工作；人负责最终推理、联想和判断。

```text
输入一个可疑文件
    ↓
自动识别文件类型 → 自动运行常见分析 → 发现异常特征
    ↓
自动调用对应插件 → 提取隐藏数据 → 新文件重新进入分析队列(递归)
    ↓
输出结果、日志、报告 —— 需要人类推理的部分清晰呈现给用户
```

找到就给（flag 自动报告），找不到就把原料给人类（字符串/解码结果呈现到终端与报告）。

## 快速开始

```bash
python hunter.py <文件1> [文件2 ...]
```

示例（仓库自带 CTF 样本）：

```bash
python hunter.py samples/snake.jpg
```

`snake.jpg` 是 JPEG + 尾部隐藏 ZIP 的拼接样本，ZIP 内含 Base64 编码的提示文本。
运行后自动完成：类型识别 → ZIP 定位 → ZIP 切出 → ZIP 解压 → Base64 检测与解码 → 字符串提取。

运行产物:

```text
output/
├── report.txt              # 汇总报告: 每轮目标的分析 + FLAG 汇总
└── extracted/              # 所有提取/生成的文件
    ├── extracted_278260.zip       # 从 JPEG 尾部切出的 ZIP
    ├── key / cipher               # ZIP 内部文件
    ├── key.decoded.txt            # Base64 解码出的明文
    └── *.strings.txt              # 可打印字符串提取(供人类查看)
```

## 实际运行效果

```text
[分析] samples/snake.jpg
  [+] 该文件实际为JPEG
  [!] 发现疑似嵌入式ZIP数据
  [+] ZIP数据提取成功
  [+] 提取新文件: output\extracted\key
  [+] 提取新文件: output\extracted\cipher

[分析] ...\key
  [+] 发现编码内容并解码(1层)
     解码第1层 [Base64]: What is Nicki Minaj's favorite song that refers to snakes?
  [+] 提取新文件: ...\key.decoded.txt

[完成] 报告已写入: output\report.txt
```

## 架构

```text
hunter.py (CLI 入口)
    │  命令行接收目标 → 递归队列
    ▼
Engine (项目经理: 不懂业务, 只负责流程)
    │  1. 创建 AnalysisContext(中央数据库)
    │  2. 创建 Logger
    │  3. 依次运行插件(异常隔离: 单插件崩溃不影响整体)
    ▼
Plugin (插件: 各干一件事)
    │  读 context.target → 分析 → 写 findings / extracted_files
    ▼
提取出的新文件 → 重新进入分析队列 → 递归直到没有新内容
```

### 核心对象

| 对象 | 职责 |
|---|---|
| `AnalysisContext` | 中央数据库: target / findings / extracted_files / logs |
| `Logger` | 日志: 时间戳 + 级别(INFO/WARNING/ERROR) |
| `Engine` | 流程控制: 创建 context/logger, 顺序运行插件, **异常隔离**(try/except + continue) |
| `Plugin` | 插件基类, 子类实现 `run(context)` 返回 finding |

### 插件间通信规则

插件之间**不直接依赖**。产物落盘 → 记入 `extracted_files` → 由递归队列作为新 target 接力分析。
明文的来历(source/method/offset)记录在提取条目中，供报告追溯。

### 异常隔离

每个插件调用包在 `try/except Exception` 中：插件崩溃 → 记 ERROR 日志(插件名 + 原因) → 跳过继续。
用 `Exception` 而非 `BaseException`，保证用户 Ctrl+C 不被吞掉。

## 插件清单 (v1.0)

| 插件 | 功能 |
|---|---|
| `file_type.py` | 魔数识别: JPEG/PNG/GIF/PDF/ZIP |
| `zip_detector.py` | 定位嵌入式/独立 ZIP (PK 头偏移) |
| `zip_extractor.py` | 按偏移切出 ZIP + `zipfile` 解压内部文件(防路径穿越: 只取 basename) |
| `decoder.py` | 自动检测 Base64 → 解码 → 递归解 Base 套娃 → 明文落盘 |
| `strings_analyzer.py` | 三层递进: flag/ctf 模式 → 敏感关键字 → 全量字符串提取 |

### 解码库 `utils/decoders.py`

从交互工具提炼的纯函数: `try_b64/b32/b16/b85` (失败返回 None 而非抛异常)、
`decode_chain` (套娃解码, 字符集越窄越先试防抢答误判, 双层防死循环)。
可读性检查在**原始字节**上做，避免 `errors="ignore"` 丢字节造成的假阳性。

### 独立工具 `tools/decoder_cli.py`

早期独立开发的交互式解码工具箱(粘贴即用): 二进制/十进制/十六进制转 ASCII、
Base16/32/64/85 解码、URL/Unicode 解码、自动递归解多层 Base 套娃、进制互转。
`python tools/decoder_cli.py` 直接运行。

## 目录结构

```text
MISC_Hunter/
├── core/            # context / engine / logger / plugin
├── plugins/         # 分析插件(每个只解决一种问题)
├── utils/           # paths(输出路径统一管理) / decoders(解码库)
├── tools/           # 独立 CLI 工具
├── samples/         # 测试样本
├── tests/           # 流程验证脚本
├── output/          # 运行产物(不入库)
├── hunter.py        # 入口: CLI + 递归队列 + 报告
└── requirements.txt
```

## 设计原则

1. **模块化** — 一个插件只解决一种问题，插件间不互相依赖
2. **可失败** — 单个插件崩溃不影响整体分析(异常隔离)
3. **可解释** — 每条 finding 带 code/message/severity，日志可完整追溯
4. **有结果才扩散** — 只有提取出真实文件才进入下一轮递归
5. **递归分析** — 提取出的文件自动重新进队列，直到没有新内容
6. **机械自动化，推理留人类** — 编码/提取/穷举自动化；密钥、算法线索、联想留给人类

## 版本路线

| 版本 | 主题 | 内容 |
|---|---|---|
| **1.0** ✅ | 能用的流水线 | CLI + 递归队列 + 报告 + 基础插件(类型/ZIP/解码/字符串) |
| **2.0** | 覆盖面 | PNG 专项(chunk/CRC/宽高)、metadata、LSB、XOR/凯撒爆破、密钥解密框架(pycryptodome: Serpent/AES 等) |
| **3.0** | 深度与接力 | 外部工具矩阵(zsteg/F5/steghide)、递归策略深化、人机接力(人类答案回填解密)、zip 密码爆破 |
| **4.0** | AI 辅助层 | LLM 做总结/建议/解释 —— 确定性分析仍是核心 |

## 环境要求

- Python 3.8+
- 无第三方依赖（v1.0）

```bash
python hunter.py              # 查看用法
python tools/decoder_cli.py   # 交互解码工具
```
