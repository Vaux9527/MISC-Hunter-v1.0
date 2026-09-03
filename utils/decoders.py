'''
MISC Hunter 解码库
从 useful_or_not/decoder.py 提取并改造:
    - 去掉菜单和交互, 保留纯解码逻辑
    - auto_base_decode 改为返回结构化的解码记录(插件需要逐层结果)
    - Base58/Base91 依赖第三方库, 1.0 暂不内置(装库后可参照 try_b85 补上)
'''

import base64
import string


def is_printable(s, threshold=0.9):
    """判断字符串是否大部分可打印, 避免把乱码当解码结果"""
    if not s:
        return False
    count = sum(c in string.printable for c in s)
    return count / len(s) > threshold


def _clean(content):
    """去掉换行/空格/回车, 统一解码前的输入格式"""
    return content.replace("\n", "").replace(" ", "").replace("\r", "")


def _looks_readable(raw, threshold=0.9):
    """
    字节级可读性检查: 在"解码后的原始字节"上统计可打印占比
    达标 -> 返回解码文本; 不达标 -> 返回 None
    注意: 必须在原始字节上检查, 不能先 decode("utf-8", errors="ignore")
    再检查——ignore 会静默丢弃乱码字节, 让占比虚高, 造成假阳性
    """
    if not raw:
        return None
    count = sum(1 for b in raw if 32 <= b <= 126 or b in (9, 10, 13))
    if count / len(raw) <= threshold:
        return None
    return raw.decode("utf-8", errors="replace")


def try_b64(content):
    """尝试 Base64 解码; 失败或结果不可读 -> 返回 None"""
    try:
        c = _clean(content)
        missing = 4 - len(c) % 4
        if missing != 4:
            c += "=" * missing
        return _looks_readable(base64.b64decode(c))
    except Exception:
        return None


def try_b32(content):
    """尝试 Base32 解码; 失败或结果不可读 -> 返回 None"""
    try:
        c = _clean(content).upper()
        missing = 8 - len(c) % 8
        if missing != 8:
            c += "=" * missing
        return _looks_readable(base64.b32decode(c))
    except Exception:
        return None


def try_b16(content):
    """尝试 Base16(hex) 解码; 失败或结果不可读 -> 返回 None"""
    try:
        c = _clean(content)
        return _looks_readable(base64.b16decode(c))
    except Exception:
        return None


def try_b85(content):
    """尝试 Base85 解码(先 a85 再 b85); 失败或结果不可读 -> 返回 None"""
    try:
        c = _clean(content)
        for fn in (base64.a85decode, base64.b85decode):
            try:
                readable = _looks_readable(fn(c))
                if readable is not None:
                    return readable
            except Exception:
                continue
        return None
    except Exception:
        return None


# 自动解码时按这个顺序尝试
# 顺序有讲究: 字符集越窄的越先试(hex 全在 base32/64 字符集内, 先解窄的)
_DECODERS = [
    ("Base16", try_b16),
    ("Base32", try_b32),
    ("Base64", try_b64),
    ("Base85", try_b85),
]


def decode_chain(content, max_layers=20):
    """
    递归解 Base 套娃
    从 content 开始, 逐层尝试所有解码器, 解到解不动为止
    返回: [{"decoder": "Base64", "result": "..."}, ...] 每层一条记录
    防死循环: 结果必须变化(res != current) + 最多 max_layers 层
    """
    layers = []
    current = content.strip()

    for _ in range(max_layers):
        for name, fn in _DECODERS:
            res = fn(current)
            if res and res != current:
                layers.append({"decoder": name, "result": res})
                current = res
                break
        else:
            # for 循环完整跑完没 break = 所有解码器都解不动了
            break

    return layers
