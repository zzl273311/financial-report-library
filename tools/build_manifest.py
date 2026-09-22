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
    # —— 专题（非单公司）· 置于最前，便于优先查看 ——
    dict(src='投资组合筛选/投资组合筛选_10家公司排序.html', slug='portfolio-screen',
         company='投资组合筛选', code='56 家 → 10 家', sector='跨公司比较', short='组合',
         period='2026-09 第 3 版', note='基于 55 份报告（覆盖 56 家公司）的质量—安全—回报排序',
         tags=['五维评分', '样本扩充至 56 家', '组合结构', '拒绝采信清单', '五类高质量假象'],
         manual=dict(summary='从工作区 55 份已生成的财报分析报告（覆盖 56 家公司）中，按「生意质量 25% ＋ 盈利质量与现金转化 20% ＋ 成长性 20% ＋ 资产负债表安全 20% ＋ 股东回报 15%」五维加权评分选出 10 家并排序：贵州茅台、海天味业、中国海油、农夫山泉、腾讯控股、药明康德、紫金矿业、洛阳钼业、网易、渣打银行。第 3 版新增 11 家公司（紫金矿业、洛阳钼业、渣打银行、中银香港、汇丰控股、珀莱雅、香港中华煤气、浦发银行、上海银行、北京银行、美团），其中前三家评分高于第 2 版第 10 名，直接挤掉山西汾酒、中国平安与招商银行。报告明确声明：55 家中 54 家无 PE / PB / 市值（仅携程 1 家有），因此本排序是质量驱动的排序、不是性价比排序；同时设"拒绝采信清单"（五粮液异常数据、东阿阿胶不可引用列、华润医药税率型增长），系统拆解"五类高质量假象"（非现金利润、资产处置型增长、以信用换收入、加杠杆分红、行业利润与现金流长期背离），并逐家说明落选原因与评分—排序差异，含"资源合并敞口 28% 越线"的主动坦白。',
                     metrics=[])),
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
    # —— 医药研发外包（CXO）——
    dict(src='药明康德/药明康德财报分析.html', slug='wuxi',
         company='药明康德', code='603259.SH / 02359.HK', sector='医药研发外包', short='药明',
         period='2018 — 2026H1', note='八年 ＋ 2026 中期 · CRDMO 龙头',
         tags=['归母 +102.65% 含 59.10 亿资产处置', '在手订单 664.30 亿', 'TIDES 收入 +96.0%', '美国客户占 71.97%']),
    # —— 基础化工 ——
    dict(src='万华化学/万华化学财报分析报告.html', slug='wanhua',
         company='万华化学', code='600309.SH', sector='基础化工', short='万华',
         period='2016 — 2026H1', note='十年 · 附 2026 半年度',
         tags=['MDI 龙头', '毛利率十年最低', '自由现金流', '石化一体化']),
    # —— 银行 / 保险 / 综合金融 ——
    dict(src='渣打银行/渣打银行财报分析.html', slug='stanchart',
         company='渣打集团', code='02888.HK / STAN.LN', sector='国际银行', short='渣打',
         period='2014 — 2026H1', note='十二个年度 ＋ 2026 中期 · 基本 vs 列账双基准',
         tags=['净息差 2.03% 领先中资行', '基本口径到普通股股东仅 57.7%',
               '第三阶段保障比率 52%/68% 为 2018 年来最低', 'CET1 14.1%、股息 +65%',
               '2026 起改列账基准披露']),
    dict(src='汇丰控股/汇丰控股财报对比分析.html', slug='hsbc',
         company='汇丰控股', code='00005.HK', sector='国际银行', short='汇丰',
         period='2021 — 2026H1', note='五年半 · 列账 vs 固定汇率双基准',
         tags=['2025 利润"假跌"：剔一次性后主业 +7%', '2026H1 +23.48% 半数为基数反转',
               '香港分部 ATROE 44.3%', '减值率连升三期至 0.47%', '恒生私有化压 CET1 至 14.1%']),
    dict(src='中银香港/中银香港财报分析.html', slug='boc-hk',
         company='中银香港', code='02388.HK', sector='国际银行', short='中银香港',
         period='2016 — 2026H1', note='十年研究 · 港币 · HKFRS',
         tags=['账面净息差十年走平是两段反向运动抵消', '2025 净息差守住靠负债成本降 72BP',
               '第二阶段拨备 +367.1%：真正的风险信号', 'CET1 跳升 3.99pp 主因 RWA 计量变更',
               '2024 年贷款十年来首次负增长', '贷存比率 58.4% 十年最低']),
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
    dict(src='浦发银行/财报分析/浦发银行财报对比分析.html', slug='spdb',
         company='上海浦东发展银行', code='600000.SH', sector='股份行', short='浦发',
         period='2016 — 2025', note='十年对比 · 附 2026 半年报',
         tags=['逾期／不良剪刀差长期化', '零售不良反超对公', '迁徙率全面跳升', '核心一级资本距红线 99BP']),
    dict(src='北京银行/财报分析/北京银行财报分析.html', slug='bobj',
         company='北京银行', code='601169.SH', sector='城商行', short='京行',
         period='2021 — 2026H1', note='五年对比 · 含 2026 年半年度',
         tags=['Q4 单季亏损 9.78 亿', '减值增量全来自金融投资', '逾期／不良 151.9%', '核心一级资本距底线 62BP']),
    dict(src='上海银行/上海银行财报分析.html', slug='bosc',
         company='上海银行', code='601229.SH', sector='城商行', short='沪行',
         period='2016 — 2026H1', note='十年财务研究（上市当年起）· 附 2026 年半年度与一季度',
         tags=['拨备覆盖率七年 −92.21pp 首破 200%', '2026Q2 单季集中确认 47.40 亿',
               '信用卡分期口径双列（2019 三读）', 'ROE 七年单边下行无一年回升']),
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
    dict(src='中国移动/中国移动财报分析.html', slug='china-mobile',
         company='中国移动', code='00941.HK / 600941.SH', sector='电信运营商', short='中国移动',
         period='2021 — 2026H1', note='五年 ＋ 2026 中期 · 含增值税口径说明',
         tags=['派息率 75%', '资本开支四连降', '算力与 AIDC 第二曲线', '红利属性']),
    dict(src='中国联通/财报分析/中国联通财报对比分析.html', slug='china-unicom',
         company='中国联通', code='600050.SH / 0762.HK', sector='电信运营商', short='中国联通',
         period='2016 — 2026H1', note='十年 ＋ 2026 中期',
         tags=['自由现金流 +24.7%', '增值税 6%→9% 永久冲击', '归母仅占集团净利 43.9%', '分红率 56%']),
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
    # —— 有色金属 / 矿业 ——
    dict(src='紫金矿业/紫金矿业财报分析.html', slug='zijin-mining',
         company='紫金矿业', code='601899.SH / 2899.HK', sector='有色金属·矿业', short='紫金',
         period='2016 — 2026H1', note='十年 ＋ 2026 上半年 · 金铜锂多金属全球化矿业',
         tags=['矿产品 31.5% 收入贡献 74.6% 利润', '金价单克毛利 +178.9%', '矿产铜增速降至 −5.7%',
               '权益法收益占归母 10.5%', '资产负债率三连降至 49.55%']),
    dict(src='洛阳钼业/洛阳钼业财报分析.html', slug='cmoc',
         company='洛阳钼业', code='603993.SH / 03993.HK', sector='有色金属·矿业', short='洛钼',
         period='2020 — 2025', note='六年 · 铜钴矿业 ＋ IXM 贸易双轮驱动',
         tags=['归母净利 203.39 亿六年增 7.7 倍', '扣非(+55.56%)快于归母(+50.30%)', '矿山端 30.1% 收入贡献 78.0% 毛利',
               '经营现金流 −35.64% 全属营运资本占用', '开启黄金板块 · 铜金两极'],
         manual=dict(summary='洛阳钼业 2025 年交出一份「量价齐升 ＋ 利润成色干净」的年报：营业收入 2,066.84 亿元同比 −2.98%，归母净利润 203.39 亿元同比 +50.30%（连续六年创新高，六年增 7.7 倍）。表观下滑完全来自 IXM 贸易端「提质控量」（收入 −4.39%），而矿山端收入 777.13 亿元同比 +19.08%、毛利率 52.85% 提升 7.71 个百分点；矿山端以 30.1% 的收入（抵销前口径）贡献了 78.0% 的毛利，这是理解本公司利润结构的核心。利润质量在资源类公司中属上乘：扣非归母 204.07 亿元同比 +55.56%，快于归母，非经常性损益为净拖累 −0.69 亿元；扣非加权 ROE 26.70% 高于加权 ROE 26.61%，说明 ROE 提升完全来自主业；实际税率由 38.47% 降至 31.67%，是顺向助力而非粉饰；2025 年无 Q4 塌陷（Q4 归母 60.59 亿元创单季新高，占全年 29.8%）。经营现金流 208.43 亿元同比 −35.64% 与净利润方向相反，但完全由三项营运资本 −235.89 亿元的方向性摆动解释（其中钴库存因刚果金出口禁令激增 156.75%），具可逆性，不应解读为经营恶化。风险面：矿山端约 79% 收入来自刚果（金）的地域集中度、铜价单变量驱动、贸易衍生品公允价值变动损失 76.88 亿元、速动比率由 1.08 降至 0.98 跌破 1.0。2025 年正式开启黄金板块（厄瓜多尔奥丁矿业 5.81 亿加元 ＋ 巴西 4 座在产金矿 10.15 亿美元），2026 年黄金年化产量指引 6—8 吨，战略由「铜钴为主」转向「铜金两极」。')),
    # —— 煤炭 / 电力 ——
    dict(src='中国神华/中国神华财报分析.html', slug='shenhua',
         company='中国神华', code='601088.SH / 01088.HK', sector='煤炭一体化', short='神华',
         period='2016 — 2026H1', note='十年 ＋ 2026 中期 · 煤电路港航一体化',
         tags=['分红率 79.1%', '分红下限 65%', '长协占自产动力煤 86.5%', '并购后杠杆待周期检验']),
    dict(src='600795/国电电力财报分析.html', slug='guodian-power',
         company='国电电力', code='600795.SH', sector='电力', short='国电电力',
         period='2019 — 2026H1', note='七年 ＋ 2026 上半年 · 常规能源发电平台',
         tags=['煤电价剪刀差', '扣非净利 +45.23%', '自由现金流首次转正', '新能源装机占比 36.28%'],
         manual=dict(summary='国电电力已走完一轮完整的煤价周期检验：2021 年煤价暴涨致扣非归母亏损 41.64 亿元，2022 年电价市场化改革落地后扭亏，2023—2025 年扣非利润连续三年改善（48.70 → 46.66 → 67.76 亿元）。2025 年最具迷惑性——归母净利润 71.61 亿元同比 −27.15%，但扣非归母 67.76 亿元同比 +45.23%、创七年新高，表观下滑完全源于 2024 年 51.65 亿元转让国电建投 50% 股权的一次性投资收益基数。同期自由现金流首次转正（+78.54 亿元），分红率由 36.28% 提升至 60.02%；新能源控股装机占比升至 36.28%，水电随大渡河双江口电站投产形成第二利润支柱。2026 上半年剪刀差反转（煤价 +0.64%、电价 −16.40 元/兆瓦时），扣非归母 −18.25%，公司正处在由火电周期股向「水电 ＋ 新能源」现金流资产过渡的关键验证期。')),
    # —— 公用事业 ——
    dict(src='香港中华煤气/香港中华煤气财报分析.html', slug='towngas',
         company='香港中华煤气', code='00003.HK', sector='公用事业 · 城市燃气', short='中华煤气',
         period='2016 — 2026H1', note='十年 ＋ 2026 中期 · 港币 · HKFRS',
         tags=['十年营收 +90.24% 而归母 −22.51%', '分红率 114.82%、十年分红为自由现金流 2.03 倍',
               '2026H1 归母 +22.82% 而经营溢利 −4.45%', '燃料成本增速为收入增速 1.98 倍',
               '内地接驳业务随房地产下行萎缩']),
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
    dict(src='珀莱雅/珀莱雅财报分析报告.html', slug='proya',
         company='珀莱雅', code='603605.SH', sector='化妆品', short='珀莱雅',
         period='2017 — 2026H1', note='九年 ＋ 2026 上半年 · 国货化妆品龙头',
         tags=['主品牌首次负增长', '销售费用率 53.13%', '花知晓 9.24 亿商誉', '分红率 52.58%']),
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
    dict(src='香港交易所/香港交易所财报分析.html', slug='hkex',
         company='香港交易所', code='00388.HK / 80388', sector='交易所 · 市场基础设施', short='港交所',
         period='2016 — 2026H1', note='HKFRS · 十年 ＋ 2026 中期 · 含结算业务口径还原',
         tags=['支柱二税负吞掉 9.1 亿元利润', 'ADT 传动比仅 0.51', '保证金回报率 1.78%', '自有资金仅占总资产 6.8%']),
    dict(src='01299/友邦保险财报分析.html', slug='aia',
         company='友邦保险', code='01299.HK / 81299', sector='寿险 · 泛亚保险集团', short='友邦',
         period='2020 — 2026H1', note='IFRS（IFRS 9 / 17）· 营运利润 / EV / NBV / CSM 框架',
         tags=['NBV 创新高 55.16 亿美元', '资本效率提升 24.7%', 'CSM 649.45 亿美元', '偿付能力缓冲收窄']),
    dict(src='9961/携程集团财报分析报告.html', slug='ctrip',
         company='携程集团', code='9961.HK / TCOM.O', sector='在线旅游', short='携程',
         period='2020 — 2026H1', note='US GAAP ＋ IFRS 调节表',
         tags=['OTA 龙头', '国际业务', '20-F', '季度业绩公告']),
    # —— 房地产投资信托 / 收租资产 ——
    dict(src='领展房产基金/领展房产基金财报分析.html', slug='link-reit',
         company='领展房产基金', code='0823.HK', sector='房地产投资信托', short='领展',
         period='FY2018 — FY2026', note='REIT · 港元 · 附中期业绩',
         tags=['可分派总额 −6.4%', 'DPU 回到 FY2018 水平', '香港续租租金 −8.2%', '非核心资产出售 + 回购']),
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
