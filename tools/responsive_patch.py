#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
财报分析报告 HTML —— 响应式适配补丁
================================================
给由 financial-report-analysis / Kami 模板生成的报告加上"适应各种屏幕"的能力，
特点是 **只作用于屏幕（@media screen），完全不改动打印 / PDF 排版**。

做四件事：
  1. 补 <meta name="viewport">          —— 移动端最关键的一步（缺失时手机会按 980px 虚拟宽度渲染）
  2. 注入屏幕端响应式 CSS 层             —— 边距收缩、指标卡换行、标题降级、表格不压字
  3. 把每个 <table> 包进横向滚动容器      —— 宽表（11~13 列）在窄屏可左右滑动，不压塌表头
  4. 给 @font-face 补 font-display: swap —— 报告字体走 jsdelivr CDN，慢或被墙时正文
     会先空白数秒才回退；swap 让正文立刻用回退字体可见（不影响字形来源与打印）

幂等：重复运行不会重复注入。

用法：
    python3 responsive_patch.py <文件或目录> [更多路径...]
    python3 responsive_patch.py --check <路径>     # 只报告状态，不写文件
"""

import argparse
import glob
import os
import re
import sys

MARK = "rsp-mobile-adapt"
# CSS 版本标记：改动适配层 CSS 时把 vN 递增，重跑补丁即可把旧版本整块替换掉。
# （否则 inject_css 见到旧标记就跳过，老报告永远拿不到新规则）
STYLE_VER = MARK + "-v3"

VIEWPORT = '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">'

# ---------------------------------------------------------------- CSS 适配层
# 宽表最小宽度：按列数分档，避免中文被挤成"一列一个字"
# 每列约 62px，使列内至少能容纳 4~5 个汉字再换行
COL_MIN_PX = 62
COL_MAX_BUCKET = 16
# 图表 SVG：viewBox 宽 >= 此值才当作"图表"包装（小于此值多为装饰性图标）
FIG_MIN_W = 400
_WIDE_RULES = "\n".join(
    "  .rsp-w%d > table { min-width: %dpx; }" % (n, n * COL_MIN_PX)
    for n in range(5, COL_MAX_BUCKET + 1)
)
_WIDE_RULES_MQ = "\n".join(
    "  .rsp-w%d > table { min-width: %dpx !important; }" % (n, n * COL_MIN_PX)
    for n in range(5, COL_MAX_BUCKET + 1)
)

CSS = """
<!-- {mark} : 响应式适配层（仅屏幕生效，不影响打印/PDF） -->
<style id="{mark}">
/* {ver} */
/* ========== 1. 全局：屏幕端基础修正 ========== */
@media screen {{
  html {{ -webkit-text-size-adjust: 100%; text-size-adjust: 100%; }}
  body {{ overflow-wrap: break-word; }}
  img, svg, canvas, video, iframe {{ max-width: 100%; }}
  svg[viewBox], svg[viewbox] {{ height: auto; }}

  /* 网格容器（两列对比等）：网格项默认 min-width:auto，会被内部宽表撑破
     容器、把整页顶出横向滚动（报告里 .two-col 就栽在这上面）。放开收缩，
     让里面的 .rsp-table 自己去横向滑动。 */
  .risk-grid > *, .two-col > * {{ min-width: 0; }}

  /* 表格横向滚动容器：宽表不压字、不撑破页面 */
  .rsp-table {{
    max-width: 100%;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    overscroll-behavior-x: contain;
    margin: 8pt 0;
    position: relative;
  }}
  .rsp-table > table {{ margin: 0; }}
  .rsp-table::-webkit-scrollbar {{ height: 7px; }}
  .rsp-table::-webkit-scrollbar-track {{ background: transparent; }}
  .rsp-table::-webkit-scrollbar-thumb {{ background: #D8D1C4; border-radius: 4px; }}
  /* 内容确实溢出时，右侧给一层渐变暗示"还能往右滑" */
  .rsp-table[data-rsp-scroll] {{
    background: linear-gradient(to left, rgba(167,63,45,.10), rgba(167,63,45,0) 28px);
    background-repeat: no-repeat;
    background-position: right center;
    background-size: 28px 100%;
  }}
}}

/* ========== 2. 平板 / 窄窗口：边距先收，避免内容被挤 ========== */
@media screen and (max-width: 900px) {{
  body {{ padding: 22px 22px 46px 22px !important; }}
  .report-header {{ flex-wrap: wrap; gap: 12pt; }}
  .metrics {{ flex-wrap: wrap; gap: 10pt 18pt; }}
  .metric {{ flex: 1 1 42%; min-width: 0; }}
  .report-footer {{ flex-wrap: wrap; gap: 4pt 14pt; }}

  /* 宽表改为横向滚动：给每列保留最小可读宽度，不再把汉字挤成竖排 */
{wide_mq}
}}

/* ========== 3. 手机：指标卡两列、页头转纵向 ========== */
@media screen and (max-width: 720px) {{
  body {{
    max-width: 100% !important;
    padding: 18px 16px 44px 16px !important;
    font-size: 10.5pt;
  }}
  h2 {{ font-size: 15pt !important; margin: 20pt 0 7pt 0 !important; }}
  h3 {{ font-size: 12.5pt !important; }}
  h1 {{ font-size: 19pt !important; }}
  p, li {{ line-height: 1.62; }}
  ul, ol {{ padding-left: 17pt; }}

  .report-header {{ flex-direction: column; align-items: stretch; gap: 8pt; }}
  .price-block {{ text-align: left; padding-top: 0; }}
  .price-current {{ font-size: 24pt !important; }}
  .ticker-name {{ font-size: 21pt !important; }}
  .ticker-sub {{ font-size: 9.5pt !important; }}

  .metrics {{ gap: 9pt 12pt; }}
  .metric {{ flex: 1 1 45%; }}
  .metric-value {{ font-size: 15pt !important; }}
  .metric-label {{ font-size: 8.5pt !important; white-space: normal !important; }}

  table, .kami-table {{ font-size: 9pt !important; }}
  .longtable {{ font-size: 8.5pt !important; }}
  .wide {{ font-size: 7.5pt !important; }}
  .dense {{ font-size: 8pt !important; }}
  table th, table td, .kami-table th, .kami-table td {{ padding: 5pt 6pt !important; }}

  blockquote, .quote, .note, .warn, .callout, .risk-item {{ padding: 9pt 11pt !important; }}
  .risk-grid {{ grid-template-columns: 1fr !important; }}
  .report-footer {{ flex-direction: column; align-items: flex-start; gap: 3pt; }}
}}

/* ========== 3b. 图表：窄屏保持图纸原尺寸 + 横向滑动 ========== */
/* 报告里的图表是 SVG：viewBox 宽 680 + width:100%。缩到手机宽度（约 350px）
   只剩 0.5×，图内字号从 11px 掉到 5px 完全不可读；而 SVG <text> 不会自动换行，
   单纯放大字号必然溢出图框。这里改为**保持图纸原尺寸、允许左右滑动**——
   与上面宽表同一套策略，宁可滑也不塌字号。仅屏幕生效，打印/PDF 不受影响。 */
@media screen and (max-width: 720px) {{
  .rsp-fig {{
    max-width: 100%;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    overscroll-behavior-x: contain;
    /* 图纸一定宽于屏幕，直接给右侧一层渐变，暗示"还能往右滑" */
    background: linear-gradient(to left, rgba(167,63,45,.09), rgba(167,63,45,0) 26px);
    background-repeat: no-repeat;
    background-position: right center;
    background-size: 26px 100%;
  }}
  .rsp-fig > svg {{ min-width: var(--rsp-fig-w, 680px); }}
  .rsp-fig::-webkit-scrollbar {{ height: 7px; }}
  .rsp-fig::-webkit-scrollbar-track {{ background: transparent; }}
  .rsp-fig::-webkit-scrollbar-thumb {{ background: #D8D1C4; border-radius: 4px; }}
}}

/* ========== 4. 小屏手机：指标卡单列、边距收到最紧 ========== */
@media screen and (max-width: 430px) {{
  body {{ padding: 14px 12px 38px 12px !important; }}
  h2 {{ font-size: 14pt !important; }}
  h3 {{ font-size: 11.5pt !important; }}
  .ticker-name {{ font-size: 19pt !important; }}
  .price-current {{ font-size: 21pt !important; }}
  .metric {{ flex: 1 1 100%; }}
  .metric-value {{ font-size: 16pt !important; }}
  ul, ol {{ padding-left: 15pt; }}
  table, .kami-table {{ font-size: 8.5pt !important; }}
}}

/* ========== 5. 打印：把包裹层还原成透明，PDF 版式与补丁前完全一致 ========== */
@media print {{
  .rsp-table {{ margin: 0; padding: 0; overflow: visible !important; background: none !important; }}
  .rsp-table > table {{ margin: 8pt 0; min-width: 0 !important; }}
  [class*="rsp-w"] > table {{ min-width: 0 !important; }}
}}
</style>
"""

# 模板里用 {{ }} 书写字面量花括号，这里统一还原成单个花括号
CSS = (CSS.replace("{mark}", MARK)
          .replace("{ver}", STYLE_VER)
          .replace("{wide_mq}", _WIDE_RULES_MQ)
          .replace("{{", "{").replace("}}", "}"))

# 让溢出表格带上"可滑动"视觉暗示（纯装饰，失败无副作用）
JS = """
<!-- {mark} : 溢出表格滑动提示 -->
<script>
(function(){{
  function mark(){{
    var boxes = document.querySelectorAll('.rsp-table');
    for (var i=0;i<boxes.length;i++){{
      var b = boxes[i];
      if (b.scrollWidth > b.clientWidth + 4) b.setAttribute('data-rsp-scroll','');
      else b.removeAttribute('data-rsp-scroll');
    }}
  }}
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mark);
  else mark();
  window.addEventListener('resize', function(){{ clearTimeout(window.__rspT); window.__rspT=setTimeout(mark,180); }});
}})();
</script>
""".replace("{mark}", MARK).replace("{{", "{").replace("}}", "}")

# 已注入的适配层 JS 整块，用于版本升级时原地替换
JS_CHUNK_RE = re.compile(
    r'<!--\s*' + re.escape(MARK) + r'\s*:[^>]*?-->\s*<script>.*?</script\s*>',
    re.S | re.I)

# 自检：注入内容里不应再残留双花括号
assert "{{" not in CSS and "}}" not in CSS, "CSS 模板花括号还原失败"
assert "{{" not in JS and "}}" not in JS, "JS 模板花括号还原失败"


def ensure_viewport(s: str) -> str:
    """补 viewport meta；已有则原样保留。"""
    if re.search(r'<meta[^>]+name\s*=\s*["\']viewport["\']', s, re.I):
        return s
    m = re.search(r'<meta\s+charset[^>]*>', s, re.I)
    if m:
        return s[:m.end()] + "\n" + VIEWPORT + s[m.end():]
    m = re.search(r'<head[^>]*>', s, re.I)
    if m:
        return s[:m.end()] + "\n" + VIEWPORT + s[m.end():]
    return VIEWPORT + "\n" + s


# 已注入的适配层 CSS 整块（含前面的注释），用于版本升级时原地替换
CSS_CHUNK_RE = re.compile(
    r'<!--\s*' + re.escape(MARK) + r'\s*:[^>]*?-->\s*'
    r'<style\s+id=["\']' + re.escape(MARK) + r'["\'][^>]*>.*?</style\s*>',
    re.S | re.I)


def inject_css(s: str) -> str:
    """把适配层插到 </head> 之前（位于报告自带 <style> 之后，同权重下后者胜出）。

    已注入过则整块替换：CSS 会随脚本升级（如新增 .rsp-fig 规则），
    若见到旧标记直接跳过，老报告就永远拿不到新规则。
    """
    if CSS_CHUNK_RE.search(s):
        return CSS_CHUNK_RE.sub(lambda _m: CSS, s, count=1)
    m = re.search(r'</head\s*>', s, re.I)
    if m:
        return s[:m.start()] + CSS + s[m.start():]
    # 极端情况：没有 head，塞到 </body> 前
    m = re.search(r'</body\s*>', s, re.I)
    if m:
        return s[:m.start()] + CSS + s[m.start():]
    return s + CSS


def inject_js(s: str) -> str:
    """溢出提示脚本（纯装饰，失败无副作用）；已存在则整块替换，保证与脚本同步。"""
    if JS_CHUNK_RE.search(s):
        return JS_CHUNK_RE.sub(lambda _m: JS, s, count=1)
    m = re.search(r'</body\s*>', s, re.I)
    if m:
        return s[:m.start()] + JS + s[m.start():]
    return s + JS


# ---------------------------------------------------------------- 字体加载策略
FONT_FACE_RE = re.compile(r'@font-face\s*\{[^}]*\}', re.I)


def _face_has_font_display(block: str) -> bool:
    return bool(re.search(r'font-display\s*:', block, re.I))


def needs_font_display(s: str) -> bool:
    """是否还有缺 font-display 的 @font-face。"""
    return any(not _face_has_font_display(m.group(0)) for m in FONT_FACE_RE.finditer(s))


def ensure_font_display(s: str) -> tuple:
    """给缺 font-display 的 @font-face 补上 `font-display: swap`。

    报告用的是外链 CDN 字体（jsdelivr）。默认 font-display 等价于 block：
    字体没到之前正文是**不可见**的，慢网/被墙时要空白好几秒。
    swap 让正文立刻以回退字体渲染，字体到达后再替换。

    只改加载节奏，不改字形来源，对打印/PDF（WeasyPrint 用系统字体）无影响。
    返回 (新文本, 补充条数)。
    """
    n = 0

    def repl(m):
        nonlocal n
        block = m.group(0)
        if _face_has_font_display(block):
            return block
        open_i = block.index('{')
        close_i = block.rindex('}')
        body = block[open_i + 1:close_i]
        semi = body.rfind(';')
        n += 1
        if semi == -1:
            return block[:open_i + 1] + ' font-display: swap;' + body + block[close_i:]
        ins = open_i + 1 + semi + 1
        return block[:ins] + ' font-display: swap;' + block[ins:]

    return FONT_FACE_RE.sub(repl, s), n


def count_cols(table_html: str) -> int:
    """数出该表格第一行有多少个 th/td，用于决定是否给它最小列宽。"""
    tr = re.search(r'<tr\b[^>]*>(.*?)</tr\s*>', table_html, re.S | re.I)
    if not tr:
        return 0
    return len(re.findall(r'<t[hd]\b', tr.group(1), re.I))


def wrap_tables(s: str) -> tuple:
    """把每个顶层 <table>…</table> 包进 .rsp-table；宽表另加 .rsp-wN 控制最小列宽。
    返回 (新文本, 新包裹数)。"""
    if 'class="rsp-table' in s:      # 已包裹过，保持幂等
        return s, 0
    n = 0

    def repl(m):
        nonlocal n
        n += 1
        html_ = m.group(0)
        cols = count_cols(html_)
        cls = "rsp-table"
        if cols >= 5:
            cls += " rsp-w%d" % min(cols, COL_MAX_BUCKET)
        return '<div class="%s">%s</div>' % (cls, html_)

    new = re.sub(r'<table\b[^>]*>.*?</table\s*>', repl, s, flags=re.S | re.I)
    return new, n


def _fig_width(svg_open_tag: str):
    """从 <svg …> 起始标签里取出 viewBox 宽度；取不到返回 None。"""
    m = re.search(r'view[Bb]ox\s*=\s*["\']([\d.\s]+)["\']', svg_open_tag)
    if not m:
        return None
    parts = m.group(1).split()
    if len(parts) != 4:
        return None
    try:
        return float(parts[2])
    except ValueError:
        return None


def count_big_figs(s: str) -> int:
    """数出需要包装的图表 SVG（viewBox 宽 >= FIG_MIN_W）。"""
    return sum(1 for m in re.finditer(r'<svg\b[^>]*>', s, re.I)
               if (_fig_width(m.group(0)) or 0) >= FIG_MIN_W)


def wrap_figs(s: str) -> tuple:
    """把图表 SVG 包进 .rsp-fig 横向滚动容器，图纸保持原尺寸。

    SVG 用 viewBox + width:100% 自适应，窄屏会同比例缩到 0.5×，
    图内字号塌到 4~5px；而 SVG <text> 不换行，放大字号必溢出图框。
    包装后由 CSS 在窄屏给 svg 设 min-width（取 viewBox 宽），改为左右滑动。
    装饰性小图标（viewBox 宽 < FIG_MIN_W）不处理。
    返回 (新文本, 新包裹数)。
    """
    if 'class="rsp-fig' in s:        # 已包裹过，保持幂等
        return s, 0
    n = 0

    def repl(m):
        nonlocal n
        svg = m.group(0)
        head = svg[:svg.index('>') + 1]
        w = _fig_width(head)
        if w is None or w < FIG_MIN_W:
            return svg
        n += 1
        return '<div class="rsp-fig" style="--rsp-fig-w:%gpx">%s</div>' % (w, svg)

    new = re.sub(r'<svg\b[^>]*>.*?</svg\s*>', repl, s, flags=re.S | re.I)
    return new, n


def process(path: str, check_only: bool = False) -> dict:
    with open(path, encoding='utf-8', errors='replace') as f:
        src = f.read()

    has_vp = bool(re.search(r'<meta[^>]+name\s*=\s*["\']viewport["\']', src, re.I))
    has_css = (STYLE_VER in src) and (JS_CHUNK_RE.search(src) is not None)
    n_tables = len(re.findall(r'<table\b', src, re.I))
    n_wrapped = len(re.findall(r'class="rsp-table', src))
    n_figs = count_big_figs(src)
    n_figwrapped = len(re.findall(r'class="rsp-fig', src))
    need_fd = needs_font_display(src)

    if check_only or (has_vp and has_css and n_tables == n_wrapped
                      and n_figs == n_figwrapped and not need_fd):
        return dict(path=path, viewport=has_vp, css=has_css, fonts=need_fd,
                    tables=n_tables, wrapped=n_wrapped,
                    figs=n_figs, figwrapped=n_figwrapped, changed=False)

    out, wrapped = wrap_tables(src)   # 先包裹表格（此时还没注入标记，幂等判断靠 class）
    out, n_fig = wrap_figs(out)       # 再包裹图表
    out = ensure_viewport(out)
    out, n_fd = ensure_font_display(out)
    out = inject_css(out)
    out = inject_js(out)

    with open(path, 'w', encoding='utf-8') as f:
        f.write(out)

    return dict(path=path, viewport=True, css=True, fonts=False,
                faces=n_fd, tables=n_tables, wrapped=n_wrapped + wrapped,
                figs=n_figs, figwrapped=n_figwrapped + n_fig, changed=True)


def collect(paths):
    files = []
    for p in paths:
        if os.path.isdir(p):
            files += sorted(glob.glob(os.path.join(p, '**', '*.html'), recursive=True))
        elif os.path.isfile(p):
            files.append(p)
    return [f for f in files if '.bak_' not in f and '/raw/' not in f
            and not f.startswith('report-platform/tools')]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('paths', nargs='+')
    ap.add_argument('--check', action='store_true', help='只检查不写入')
    args = ap.parse_args()

    files = collect(args.paths)
    if not files:
        print('没有找到 HTML 文件')
        return 1

    total_tables = total_wrapped = total_figs = total_figwrapped = total_faces = changed = 0
    print(f"{'状态':<6}{'表格':>10}{'图表':>9}{'字体':>7}  文件")
    print('-' * 92)
    for f in files:
        r = process(f, check_only=args.check)
        total_tables += r['tables']
        total_wrapped += r['wrapped']
        total_figs += r['figs']
        total_figwrapped += r['figwrapped']
        total_faces += r.get('faces', 0)
        if r['changed']:
            changed += 1
        pending = ((r['tables'] != r['wrapped']) or (r['figs'] != r['figwrapped'])
                   or (not r['css']) or r.get('fonts', False))
        flag = '已更新' if r['changed'] else ('待处理' if pending else 'OK')
        vp = 'vp' if r['viewport'] else '--'
        fd = ('+%d' % r['faces']) if r.get('faces') else ('缺' if r.get('fonts') else 'ok')
        fg = '%d/%d' % (r['figwrapped'], r['figs'])
        print(f"{flag:<6}{r['wrapped']:>4}/{r['tables']:<5}{fg:>9}{fd:>7}  {vp}  {f}")

    print('-' * 92)
    print(f"文件 {len(files)} 份｜已修改 {changed} 份｜表格包裹 {total_wrapped}/{total_tables}"
          f"｜图表包裹 {total_figwrapped}/{total_figs}｜font-display 补充 {total_faces} 处")
    return 0


if __name__ == '__main__':
    sys.exit(main())
