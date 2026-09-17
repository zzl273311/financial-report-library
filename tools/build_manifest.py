#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成 report-platform/data/reports.js 报告清单
================================================
从各报告的 HTML 中自动抽取「核心指标」「核心结论摘要」「PDF 页数」，
公司名 / 代码 / 行业 / 期次等由下面的 SOURCES 表人工校对后写入。

新增报告：在 SOURCES 里加一行，然后重跑本脚本。

    python3 build_manifest.py            # 生成 data/reports.js
    python3 build_manifest.py --dry-run  # 只打印，不写文件
"""

import argparse
import html as H
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))   # 财报分析/
OUT = os.path.join(os.path.dirname(__file__), '..', 'data', 'reports.js')

# ---------------------------------------------------------------------------
# 人工校对的报告目录
#   src    : 相对 财报分析/ 的报告 HTML 路径
#   slug   : 平台内目录名（ASCII）
#   manual : 版式特殊、无法自动抽取指标/摘要时在此覆盖
# ---------------------------------------------------------------------------
SOURCES = [
    # —— 白酒 / 食品饮料 ——
    dict(src='财报分析/五粮液与贵州茅台财报对比分析.html', slug='wuliangye-moutai',
         company='五粮液 × 贵州茅台', code='000858.SZ / 600519.SH', sector='白酒', short='白酒双雄',
         period='2016 — 2026H1', note='十年双巨头对比 · 附 2026 年半年度',
         tags=['格局重置', '销售费用率十年一轮回', '渠道蓄水池反向', '量价机制分化']),
    dict(src='山西汾酒/山西汾酒财报分析.html', slug='fenjiu',
         company='山西汾酒', code='600809.SH', sector='白酒', short='汾酒',
         period='2016 — 2026H1', note='十年财务研究 · 清香型龙头',
         tags=['清香型', '十年 CAGR', '类现金', 'ROE']),
    dict(src='泸州老窖/泸州老窖财报分析.html', slug='luzhou-laojiao',
         company='泸州老窖', code='000568.SZ', sector='白酒', short='老窖',
         period='2016 — 2026H1', note='十年财务研究 · 浓香型龙头',
         tags=['浓香型', '国窖 1573', '分红率', 'ROE']),
    dict(src='伊利股份/伊利股份财报分析报告.html', slug='yili',
         company='伊利股份', code='600887.SH', sector='乳制品', short='伊利',
         period='2016 — 2026H1', note='十年财务研究 · 附 2026 半年度',
         tags=['乳制品龙头', '澳优商誉减值', '分红率', '净现金']),
    dict(src='海天味业/海天味业财报分析.html', slug='haitian',
         company='海天味业', code='603288.SH', sector='调味品', short='海天',
         period='2021 — 2026H1', note='A 股 + H 股 · 附 2026 半年度',
         tags=['调味品', '毛利率修复', '净现金', '分红']),
    dict(src='农夫山泉/农夫山泉财报分析.html', slug='nongfu-spring',
         company='农夫山泉', code='9633.HK', sector='包装饮用水', short='农夫',
         period='FY2017 — 2026H1', note='IFRS · 人民币',
         tags=['包装水市占率第一', '舆情修复', '经营现金流', '派息率']),
    dict(src='金龙鱼/金龙鱼财报分析.html', slug='jinlongyu',
         company='金龙鱼', code='300999.SZ', sector='粮油食品', short='金龙鱼',
         period='FY2019 — 2026H1', note='CAS · 创业板',
         tags=['厨房食品', '饲料原料', '净利率', '分红率']),
    dict(src='东阿阿胶/东阿阿胶财报分析.html', slug='dongeejiao',
         company='东阿阿胶', code='000423.SZ', sector='中药', short='东阿',
         period='2021 — 2026H1', note='五年财务深度分析',
         tags=['困境反转', '现金堡垒', '全额分红', '应收账款']),
    dict(src='同仁堂/同仁堂财报分析.html', slug='tongrentang',
         company='同仁堂', code='600085.SH', sector='中药', short='同仁堂',
         period='2016 — 2026H1', note='十年全产业链财务研究',
         tags=['老字号', '全产业链', '分红率', 'ROE']),
    dict(src='片仔癀/片仔癀财报分析.html', slug='pianzaihuang',
         company='片仔癀', code='600436.SH', sector='中药', short='片仔癀',
         period='2019 — 2026H1', note='七年对比 · 附 2026 半年报',
         tags=['国家绝密配方', '中华老字号', '医药制造', '日化']),
    dict(src='华润三九/report/华润三九财报分析报告.html', slug='cr-sanjiu',
         company='华润三九', code='000999.SZ', sector='中药', short='三九',
         period='2016 — 2026H1', note='十年 · 附 2026 半年度',
         tags=['并购驱动', '规模跃升盈利停滞', '商誉', 'CHC']),
    dict(src='万华化学/万华化学财报分析报告.html', slug='wanhua',
         company='万华化学', code='600309.SH', sector='基础化工', short='万华',
         period='2016 — 2026H1', note='十年 · 附 2026 半年度',
         tags=['MDI 龙头', '毛利率十年最低', '自由现金流', '石化一体化']),
    # —— 银行 / 保险 / 综合金融 ——
    dict(src='招商银行/招商银行财报对比分析.html', slug='cmb',
         company='招商银行', code='600036.SH / 03968.HK', sector='股份行', short='招行',
         period='2006 — 2026H1', note='二十年长周期 · 含 2026 年半年度',
         tags=['净息差两端拆解', '递延所得税一次性利润', '拨备覆盖率归因', 'RWA 与资本约束']),
    dict(src='江苏银行/财报分析/江苏银行财报对比分析.html', slug='jsbank',
         company='江苏银行', code='600919.SH', sector='城商行', short='苏银',
         period='2011 — 2026H1', note='十五个会计年度 · 附 2026 年半年度',
         tags=['营业支出增速超营收', '不良率上市以来最优', '规模跨越式扩张', '净息差 −59BP']),
    dict(src='工商银行/工商银行财报分析.html', slug='icbc',
         company='中国工商银行', code='601398.SH / 1398.HK', sector='国有大行', short='工行',
         period='2021 — 2025', note='五年对比 · 附 2026 半年报',
         tags=['以量补价', '净息差 −14BP', '核心一级资本', 'ROE 五年下行']),
    dict(src='建设银行/财报分析/中国建设银行财报对比分析.html', slug='ccb',
         company='中国建设银行', code='601939.SH / 0939.HK', sector='国有大行', short='建行',
         period='2021 — 2025', note='五年对比 · 附 2026 半年报',
         tags=['总资产五年 +50.85%', '净息差 −17BP', '拨备覆盖率', '以量补价']),
    dict(src='农业银行/农业银行财报对比分析.html', slug='abc',
         company='中国农业银行', code='601288.SH / 1288.HK', sector='国有大行', short='农行',
         period='2021 — 2025', note='五年对比 · 附 2026 半年报',
         tags=['乡村振兴', '净息差 −14BP', '核心一级资本 10.80%', '县域金融']),
    dict(src='中国银行/财报分析/中国银行财报对比分析.html', slug='boc',
         company='中国银行', code='601988.SH / 3988.HK', sector='国有大行', short='中行',
         period='2021 — 2025', note='五年对比 · 附 2026 半年报',
         tags=['全球化程度最高', '净息差 −14BP', '核心一级资本 12.53%', '综合化经营']),
    dict(src='中国人寿/中国人寿财报分析报告.html', slug='china-life',
         company='中国人寿', code='601628.SH / 2628.HK', sector='寿险', short='国寿',
         period='2025 — 2026H1', note='2025 年报 ＋ 2026 中期',
         tags=['总保费破 7,000 亿', 'NBV +35.7%', '内含价值行业首位', '权益敞口']),
    dict(src='中国平安/中国平安财报分析报告.html', slug='ping-an',
         company='中国平安', code='601318.SH / 02318.HK', sector='综合金融', short='平安',
         period='2021 — 2026H1', note='五年 ＋ 2026 中期报告',
         tags=['营运利润增速 > 净利润', '归母净资产破万亿', '内含价值', '寿险改革']),
    # —— 通信 / 运营商 ——
    dict(src='中国电信/中国电信财报分析.html', slug='china-telecom',
         company='中国电信', code='601728.SH / 0728.HK', sector='电信运营商', short='中国电信',
         period='2021 — 2026H1', note='五年 ＋ 2026 中期 · 含口径切换说明',
         tags=['增值税税目调整', '产数增速降至 +0.5%', '自由现金流 +121.3%', '派息率 75%'],
         manual=dict(summary='中国电信已从"用户规模驱动"切换到"AI 转型 + 现金流回报"阶段。2025 年营收 5,239.25 亿元仅增 0.1%、归母净利 331.85 亿元仅增 0.5%，产业数字化增速由 +19.0%（2022）降至 +0.5%（2025），第二曲线同步减速且应收账款余额 +28.9%。2026 上半年表观营收 −3.9%、归母 −14.9%，公司称主因增值税税目调整、可比口径基本稳定。亮点在现金流量表：2026H1 经营现金流 +28.4%、自由现金流 +121.3%、资产负债率降至 45.8%，派息率已提升至 75%。')),
    # —— 能源 / 化工 ——
    dict(src='中国石油/财报分析/中国石油财报对比分析.html', slug='petrochina',
         company='中国石油', code='601857.SH / 00857.HK', sector='石油石化', short='中石油',
         period='2021 — 2025', note='五年财务数据对比',
         tags=['油价决定方向', '单位操作成本 −3.1%', '一体化抗周期', '资产负债率']),
    dict(src='中国石化/财报分析/中国石化财报对比分析.html', slug='sinopec',
         company='中国石化', code='600028.SH / 00386.HK', sector='石油石化', short='中石化',
         period='2021 — 2025', note='五年财务数据对比',
         tags=['四大事业部', '净现金转净债务', '分红率 81.0%', '炼化毛利']),
    dict(src='中国海油/财报分析/中国海洋石油财报对比分析.html', slug='cnooc',
         company='中国海洋石油', code='600938.SH / 00883.HK', sector='石油石化', short='中海油',
         period='2021 — 2025', note='五年财务数据对比',
         tags=['产量 +24.6% 对冲油价', '桶油成本 −8.2%', '净产量 777.3 百万桶', '高分红']),
    dict(src='藏格矿业/财报分析/藏格矿业财报对比分析.html', slug='zangge',
         company='藏格矿业', code='000408.SZ', sector='钾肥 · 锂盐 · 铜', short='藏格',
         period='2015 — 2026H1', note='11 年长周期 · 附 2026 半年度',
         tags=['危机—出清—重构', '参股铜矿利润放大器', '借壳上市', '紫金矿业入主']),
    # —— 消费 / 互联网 / 医药 ——
    dict(src='腾讯控股/腾讯控股财报对比分析.html', slug='tencent',
         company='腾讯控股', code='00700.HK', sector='互联网', short='腾讯',
         period='2021 — 2026H1', note='五年 ＋ 2026 上半年',
         tags=['毛利率五年 +13.1pp', '非 IFRS 归母', '自由现金流', '增值服务']),
    dict(src='网易/网易财报分析.html', slug='netease',
         company='网易', code='9999.HK / NTES', sector='互联网游戏', short='网易',
         period='2019 — 2026H1', note='US GAAP · 附 2026 上半年',
         tags=['游戏', '有道', '云音乐', '研发费用']),
    dict(src='美团/美团财报分析报告.html', slug='meituan',
         company='美团', code='03690.HK', sector='科技零售', short='美团',
         period='2018 — 2026H1', note='核心分析期 2026Q2 / 上半年',
         tags=['外卖大战代价年', '2026Q2 扭亏', '经调整净利 +69.0%', '核心本地商业']),
    dict(src='拼多多/拼多多财报分析.html', slug='pdd',
         company='拼多多', code='NASDAQ: PDD', sector='电商', short='拼多多',
         period='FY2016 — 2026H1', note='US GAAP · 20-F ＋ 6-K',
         tags=['Temu', '净利首次下滑', '现金类资产占 95%', '无有息负债']),
    dict(src='泡泡玛特/泡泡玛特财报对比分析.html', slug='popmart',
         company='泡泡玛特', code='09992.HK', sector='潮流玩具', short='泡泡玛特',
         period='2020 — 2026H1', note='IFRS · 五年连续可比',
         tags=['IP 运营闭环', '全渠道零售', '会员运营', '海外扩张']),
    dict(src='老铺黄金/老铺黄金财报分析.html', slug='laopu-gold',
         company='老铺黄金', code='6181.HK', sector='黄金珠宝', short='老铺',
         period='FY2021 — 2026H1', note='IFRS · 全自营渠道',
         tags=['古法黄金奢侈品化', '存货占总资产 80.2%', '经营现金流转正', '外部融资']),
    dict(src='比音勒芬/比音勒芬财报分析.html', slug='byjlf',
         company='比音勒芬', code='002832.SZ', sector='高端服饰', short='比音',
         period='2016 — 2026H1', note='十年 ＋ 2026 中期',
         tags=['零金融负债', '毛利率 75%+', '收入利润背离', '商标无形资产']),
    dict(src='华润医药/华润医药财报分析.html', slug='cr-pharma',
         company='华润医药', code='3320.HK', sector='医药商业', short='华润医药',
         period='2019 — 2026H1', note='HKFRS · 七年 ＋ 2026 中期',
         tags=['分销 vs 制药双模型', '利润引擎切换', '制药分部 CAGR 16.73%', '净利含税率贡献']),
    dict(src='亚马芬体育/亚马芬体育财报分析.html', slug='amersports',
         company='亚马芬体育', code='NYSE: AS', sector='高端运动服饰', short='亚玛芬',
         period='FY2021 — 2026H1', note='IFRS · 美元',
         tags=['Arc\u2019teryx / Salomon', '大中华区占比 33.6%', '经调整 EBITDA 率', '资本结构操作']),
    dict(src='英矽智能/财报分析/英矽智能财报对比分析.html', slug='insilico',
         company='英矽智能', code='HKEX: 3696', sector='AI 制药', short='英矽',
         period='IPO — 2026H1', note='招股书 ＋ 2025 年报 ＋ 2026 中报',
         tags=['优先股公允价值变动', '经调整口径', 'AI 平台对外授权', 'Rentosertib III 期']),
    dict(src='中烟香港/中烟香港财报分析.html', slug='ctic-hk',
         company='中烟香港', code='06055.HK', sector='烟草专营', short='中烟香港',
         period='2020 — 2026H1', note='HKFRS · 年度 ＋ 中期',
         tags=['烟草进出口垄断通道', '巴西经营业务', '新型烟草', '港元计价']),
    dict(src='9961/携程集团财报分析报告.html', slug='ctrip',
         company='携程集团', code='9961.HK / TCOM.O', sector='在线旅游', short='携程',
         period='2020 — 2026H1', note='US GAAP ＋ IFRS 调节表',
         tags=['OTA 龙头', '国际业务', '20-F', '季度业绩公告']),
    # —— 专题（非单公司）——
    dict(src='投资组合筛选/投资组合筛选_10家公司排序.html', slug='portfolio-screen',
         company='投资组合筛选', code='30 → 10 家', sector='跨公司比较', short='组合',
         period='2026-09', note='基于 29 份报告的质量—安全—回报排序',
         tags=['质量评分', '安全边际', '股东回报', '组合结构'],
         manual=dict(summary='从工作区 29 份已生成的财报分析报告中，按「质量—安全—回报」三维评分选出 10 家并排序。报告明确声明：全部 29 份报告均无 PE / PB / 市值数据，因此本排序是质量驱动的排序、不是性价比排序，真实建仓前须补一层估值确认；同时列出落选公司的具体原因与组合结构一览。',
                     metrics=[])),
]


# --------------------------------------------------------------------------- 抽取
def strip(x):
    return re.sub(r'\s+', ' ', H.unescape(re.sub(r'<[^>]+>', '', x))).strip()


def grab_class(s, cls, limit=8):
    out = []
    for m in re.finditer(
            r'<[a-z]+[^>]*class="[^"]*(?<![\w-])%s(?![\w-])[^"]*"[^>]*>(.*?)</[a-z]+>' % re.escape(cls),
            s, re.S | re.I):
        out.append(strip(m.group(1)))
        if len(out) >= limit:
            break
    return out


def extract_metrics(body):
    """① 标准类 metric-value/metric-label；② 平安式 metric-val/metric-lab；③ 腾讯式紧凑写法"""
    vals = grab_class(body, 'metric-value') or grab_class(body, 'metric-val')
    labs = grab_class(body, 'metric-label') or grab_class(body, 'metric-lab')
    pairs = []
    for v, l in zip(vals, labs):
        if not v or not l:
            continue
        # label 里常见「2025 年营业收入（亿元）同比 +11.62%」→ 拆成 label + note
        m = re.match(r'^(.*?)\s*(同比\s*[+−\-].*|较.*|历史.*|行业.*|（.*?）.*)$', l)
        label, note = l, ''
        if m and len(m.group(1)) > 2:
            label, note = m.group(1).strip(), m.group(2).strip()
        pairs.append(dict(value=v, label=label[:34], note=note[:30]))
    return pairs[:5]


def extract_summary(body):
    """优先取「核心结论」后的第一段实体段落；否则取正文第一段较长文字。"""
    plain = strip(body)
    for anchor in ('核心结论', '一、核心结论'):
        i = plain.find(anchor)
        if i == -1:
            continue
        seg = plain[i + len(anchor): i + len(anchor) + 1400]
        # 去掉章节编号残余，取第一段有实质内容的句子
        seg = re.sub(r'^\s*\d+(\.\d+)*\s*', '', seg)
        parts = re.split(r'(?<=[。！？])', seg)
        acc = ''
        for p in parts:
            candidate = (acc + p).strip()
            if len(candidate) >= 90:
                return candidate[:320]
            acc = candidate
        if len(seg.strip()) >= 60:
            return seg.strip()[:320]
    # 退路：正文第一段 60 字以上的段落
    for m in re.finditer(r'<p[^>]*>(.*?)</p>', body, re.S):
        t = strip(m.group(1))
        if len(t) >= 80:
            return t[:320]
    return ''


def pdf_pages(path):
    if not path or not os.path.exists(path):
        return 0
    try:
        import fitz                                     # PyMuPDF（default venv 已装）
        with fitz.open(path) as d:
            return d.page_count
    except Exception:
        pass
    try:
        import subprocess
        out = subprocess.run(['mdls', '-name', 'kMDItemNumberOfPages', '-raw', path],
                             capture_output=True, text=True).stdout.strip()
        return int(out) if out.isdigit() else 0
    except Exception:
        return 0


# 响应式补丁会刷新文件 mtime，故优先用「报告内文声明的日期」，
# 其次用备份包里的原始 mtime，最后才退回当前文件 mtime。
_BACKUP_TAR = os.path.join(ROOT, '.bak_responsive_20260917', 'reports-html-original.tar.gz')
_orig_mtime = {}


def load_original_mtimes():
    if _orig_mtime or not os.path.exists(_BACKUP_TAR):
        return _orig_mtime
    import tarfile
    try:
        with tarfile.open(_BACKUP_TAR) as t:
            for m in t.getmembers():
                if m.name.endswith('.html'):
                    _orig_mtime[os.path.normpath(m.name).lstrip('./')] = m.mtime
    except Exception:
        pass
    return _orig_mtime


def report_date(src, text):
    """报告自称的生成/编制日期 → 'YYYY-MM-DD'；找不到则用原始 mtime。"""
    m = re.search(r'(?:报告日期|编制日期|成文日期|报告生成日|生成日期|发布日期)[：:]\s*'
                  r'(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})', text)
    if m:
        return '%04d-%02d-%02d' % (int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.search(r'编制日期[：:]\s*(\d{4})\s*年\s*(\d{1,2})\s*月', text)
    if m:
        return '%04d-%02d-01' % (int(m.group(1)), int(m.group(2)))
    rel = os.path.relpath(src, ROOT)
    mt = load_original_mtimes().get(rel) or os.path.getmtime(src)
    import time
    return time.strftime('%Y-%m-%d', time.localtime(mt))


def make_id(slug, period):
    """'2016 — 2026H1' → '2016-2026h1'"""
    p = period.lower().replace('—', '-').replace('–', '-')
    p = re.sub(r'[^a-z0-9-]+', '-', p).strip('-')
    p = re.sub(r'-{2,}', '-', p)
    return '%s-%s' % (slug, p)


# --------------------------------------------------------------------------- 生成
def js_str(x):
    return json.dumps(x, ensure_ascii=False)


def build():
    companies = []
    warns = []
    for e in SOURCES:
        src = os.path.join(ROOT, e['src'])
        if not os.path.exists(src):
            warns.append('缺失：%s' % e['src'])
            continue
        s = open(src, encoding='utf-8', errors='replace').read()
        body = s.split('<body', 1)[-1]
        t = re.search(r'<title>(.*?)</title>', s, re.S)
        title = strip(t.group(1)) if t else e['company']
        man = e.get('manual') or {}

        metrics = man.get('metrics')
        if metrics is None:
            metrics = extract_metrics(body)
        summary = man.get('summary') or extract_summary(body)
        if not summary:
            warns.append('无摘要：%s' % e['src'])

        # 同目录下的同名 PDF
        base = os.path.splitext(src)[0]
        pdf_src = base + '.pdf'
        slug = e['slug']
        rid = make_id(slug, e['period'])

        rep = dict(
            id=rid, title=title, period=e['period'], periodNote=e['note'],
            publishedAt=report_date(src, strip(s)),
            html='reports/%s/%s' % (slug, os.path.basename(src)),
            pdf=('docs/%s/%s' % (slug, os.path.basename(pdf_src))) if os.path.exists(pdf_src) else '',
            pages=pdf_pages(pdf_src),
            tags=e['tags'], metrics=metrics, summary=summary,
            _src=src, _pdf_src=pdf_src if os.path.exists(pdf_src) else '',
        )
        companies.append(dict(id=slug, name=e['company'], code=e['code'],
                              sector=e['sector'], short=e['short'], reports=[rep]))
    return companies, warns


def render(companies):
    L = []
    L.append('/* 财报分析报告库 · 数据清单')
    L.append(' * 由 tools/build_manifest.py 自动生成，请勿手工编辑；新增报告请改该脚本的 SOURCES 表后重跑。')
    L.append(' * 用 script 标签直接加载（而非 fetch JSON），保证 file:// 双击离线打开也能正常工作。')
    L.append(' */')
    L.append('window.REPORT_LIBRARY = {')
    L.append('  meta: {')
    L.append('    title: "财报分析 · 报告库",')
    L.append('    subtitle: "Financial Report Analysis Library",')
    L.append('    updatedAt: "%s"' % __import__('time').strftime('%Y-%m-%d'))
    L.append('  },')
    L.append('  companies: [')
    for i, c in enumerate(companies):
        L.append('    {')
        L.append('      id: %s,' % js_str(c['id']))
        L.append('      name: %s,' % js_str(c['name']))
        L.append('      code: %s,' % js_str(c['code']))
        L.append('      sector: %s,' % js_str(c['sector']))
        L.append('      short: %s,' % js_str(c['short']))
        L.append('      reports: [')
        for j, r in enumerate(c['reports']):
            L.append('        {')
            L.append('          id: %s,' % js_str(r['id']))
            L.append('          title: %s,' % js_str(r['title']))
            L.append('          period: %s,' % js_str(r['period']))
            L.append('          periodNote: %s,' % js_str(r['periodNote']))
            L.append('          publishedAt: %s,' % js_str(r['publishedAt']))
            L.append('          html: %s,' % js_str(r['html']))
            if r['pdf']:
                L.append('          pdf: %s,' % js_str(r['pdf']))
            if r['pages']:
                L.append('          pages: %d,' % r['pages'])
            L.append('          tags: [%s],' % ', '.join(js_str(x) for x in r['tags']))
            if r['metrics']:
                L.append('          metrics: [')
                for m in r['metrics']:
                    L.append('            { value: %s, label: %s, note: %s },'
                             % (js_str(m['value']), js_str(m['label']), js_str(m['note'])))
                L.append('          ],')
            L.append('          summary: %s' % js_str(r['summary']))
            L.append('        }%s' % (',' if j < len(c['reports']) - 1 else ''))
        L.append('      ]')
        L.append('    }%s' % (',' if i < len(companies) - 1 else ''))
    L.append('  ]')
    L.append('};')
    return '\n'.join(L) + '\n'


def sync_files(companies):
    """把报告 HTML / PDF 复制进平台目录，并清理清单里已不存在的旧目录。"""
    import shutil
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    want_reports, want_docs = set(), set()
    copied = 0
    for c in companies:
        for r in c['reports']:
            for kind, src, rel in (('reports', r['_src'], r['html']),
                                   ('docs', r['_pdf_src'], r['pdf'])):
                if not src or not rel:
                    continue
                dst = os.path.join(base, rel)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
                copied += 1
                (want_reports if kind == 'reports' else want_docs).add(
                    os.path.dirname(os.path.join(base, rel)))

    removed = []
    for kind, want in (('reports', want_reports), ('docs', want_docs)):
        root = os.path.join(base, kind)
        if not os.path.isdir(root):
            continue
        for name in os.listdir(root):
            p = os.path.join(root, name)
            if os.path.isdir(p) and p not in want:
                removed.append(os.path.relpath(p, base))
                shutil.rmtree(p)
    return copied, removed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--no-sync', action='store_true', help='只生成清单，不复制报告文件')
    args = ap.parse_args()

    companies, warns = build()
    out = render(companies)

    n_rep = sum(len(c['reports']) for c in companies)
    print('公司 %d 家 ｜ 报告 %d 份 ｜ 清单 %d 字节' % (len(companies), n_rep, len(out)))
    print('无 PDF 的报告：', [r['html'] for c in companies for r in c['reports'] if not r['pdf']] or '无')
    print('无指标卡的报告：', [r['html'] for c in companies for r in c['reports'] if not r['metrics']] or '无')
    if warns:
        print('\n'.join('⚠ ' + w for w in warns))

    if args.dry_run:
        print('\n--- 预览前 60 行 ---')
        print('\n'.join(out.splitlines()[:60]))
        return 0

    if not args.no_sync:
        copied, removed = sync_files(companies)
        print('已同步文件 %d 个' % copied + ('；清理旧目录：%s' % removed if removed else ''))

    with open(os.path.abspath(OUT), 'w', encoding='utf-8') as f:
        f.write(out)
    print('已写入', os.path.abspath(OUT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
