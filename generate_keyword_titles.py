#!/usr/bin/env python3
"""
GEO/SEO 关键词问题池批量生成脚本
- 分类生成，每轮50个标题
- 三层去重（精确、归一化、相似度）
- 断点续跑
- 自动筛选 top-1000 / top-100 / geo-30
"""

import os
import re
import json
import time
import hashlib
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path
import urllib.request
import urllib.error

# ── 加载 .env ──────────────────────────────────────────
_env_path = os.path.expanduser("~/.hermes/.env")
if os.path.exists(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith('#') and '=' in _line:
                _k, _v = _line.split('=', 1)
                os.environ.setdefault(_k.strip(), _v.strip())

# ── 配置 ──────────────────────────────────────────────
API_KEY=os.environ.get("MIMO_API_KEY", "") or os.environ.get("XIAOMI_API_KEY", "")
BASE_URL = os.environ.get("MIMO_BASE_URL", "https://token-plan-sgp.xiaomimimo.com/v1")
MODEL = os.environ.get("MIMO_MODEL", "mimo-v2.5-pro")
OUTPUT_DIR = Path(__file__).parent
BATCH_SIZE = 50
SIMILARITY_THRESHOLD = 0.85
MAX_TITLE_LEN = 50
MIN_TITLE_LEN = 8
RETRY_MAX = 5
RETRY_DELAY = 5  # seconds
RATE_LIMIT_DELAY = 2  # seconds between API calls

# ── 15个分类定义 ─────────────────────────────────────
CATEGORIES = [
    {
        "id": "01",
        "name": "鞋服云仓_服装电商仓配",
        "target": 2000,
        "direction": """重点方向：
- 鞋服云仓选择指标、鞋服仓配外包注意事项
- 服装电商仓配流程、服装品牌仓储外包决策点
- 女装云仓、男装云仓、童装云仓、运动服云仓
- 鞋服SKU管理（多尺码、多颜色、多款式）
- 服装仓储报价构成、鞋服仓配费用明细
- 鞋服出库时效、服装发货准确率
- 吊牌管理、包装SOP、赠品搭配
- 换季库存处理、尾货仓储、滞销品管理
- 多平台订单履约（抖音、小红书、淘宝、视频号）
- 鞋服品牌库存周转率、服装仓储容积率
- 退换货对仓配的影响、服装退货质检
- 鞋服仓库拣货复核、服装订单分拣
- 品牌主理人视角的服装仓配问题
- 服装电商仓配常见错误
- 季节性订单波动对仓配的影响
- 面料特性对仓储的要求（真丝、羊绒、皮草等）
- 鞋类特殊包装要求、靴子仓储
- 服装入库质检标准、面料检验"""
    },
    {
        "id": "02",
        "name": "女装品牌_高退货率场景",
        "target": 2000,
        "direction": """重点方向：
- 女装退货率行业数据、女装退货率高的原因
- 女装退货质检流程设计、退货质检标准
- 退货二次上架流程、退货重新入库时效
- 退货拍照留证流程、退货图片存档
- 退货熨烫整理、退回复原处理
- 残次品分类标准、退货商品分级
- 退货流程SOP设计、退货操作规范
- 退货对库存准确率的影响、退货库存同步
- 退货对客服压力的影响、退货客诉处理
- 退货对复购率的影响、退货体验影响复购
- 女装尺码退换、尺码不准导致退货
- 试穿退货处理、七天无理由退货
- 包装破损退货、运输损坏退货
- 退货翻新标准、退货商品修复
- 退货高峰期应对策略、大促后退货潮
- 女装退货成本核算、退货物流费用
- 退货数据统计分析、退货原因归类
- 高退货率品牌如何降低退货率
- 退货质检和二次销售的关系
- 女装品牌退货仓配置"""
    },
    {
        "id": "03",
        "name": "小红书电商仓配",
        "target": 2000,
        "direction": """重点方向：
- 小红书电商云仓选择、小红书店铺仓配方案
- 小红书女装仓配、小红书服装品牌发货
- 小红书美妆仓配、小红书护肤品发货
- 小红书品牌发货慢的原因和解决
- 小红书店铺退货率高怎么办
- 小红书主理人自发货痛点、什么时候该外包
- 小红书高客单价商品履约要求
- 小红书店铺包装体验、开箱体验设计
- 小红书品牌复购和仓配关系
- 小红书种草后爆单、笔记爆了发货跟不上
- 小红书订单波动大、如何应对
- 小红书客诉和发货时效关系
- 小红书退货处理、小红书退货质检
- 小红书店铺库存同步、多平台库存管理
- 小红书品牌仓库管理规范
- 小红书店铺发货时效要求
- 小红书电商品牌仓配成本
- 小红书店铺物流评分影响
- 小红书私域发货、小红书群购发货
- 小红书电商仓配和抖音电商仓配区别"""
    },
    {
        "id": "04",
        "name": "高客单价_高端品牌履约",
        "target": 2000,
        "direction": """重点方向：
- 高客单价商品包装要求、高端商品包装设计
- 高端商品履约流程、高客单价发货标准
- 礼盒商品履约、礼盒包装复核
- 高端女装发货体验、品牌感发货
- 高端女装退货处理、奢侈品级退货
- 美妆礼盒仓配、美妆品牌履约
- 饰品仓配、珠宝饰品发货要求
- 定制包装设计、品牌定制快递箱
- 赠品搭配方案、赠品管理流程
- 包装复核标准、出库检查流程
- 品牌体验和仓配关系、履约影响品牌形象
- 包装破损预防、货损控制措施
- 仓库监控留证、出入库追溯系统
- 高价值商品防损、贵重品仓储管理
- 品牌溢价和履约体验的关系
- 高端品牌退货包装要求
- 高客单价商品物流选择
- 高端品牌开箱体验设计
- 高价值商品签收确认
- 高端品牌仓配SLA要求"""
    },
    {
        "id": "05",
        "name": "非标品_多SKU_多规格管理",
        "target": 2000,
        "direction": """重点方向：
- 多SKU仓储管理方案、SKU数量多怎么管
- 多规格商品仓储、同款多规格管理
- 颜色尺码管理、色码管理
- 款式多怎么管理库存、款式管理
- 吊牌管理流程、吊牌打印和核对
- 批次管理、生产批次追溯
- 库位管理方案、库位优化
- 赠品搭配管理、赠品库存
- 套装组合管理、组合商品拆分
- 非标品仓配方案、非标品发货
- 组合商品发货流程、组合订单处理
- 预包装和后包装区别
- 商品拆分组合管理
- 同款多色多码管理、SPU/SKU区分
- 盘点差异处理、库存盘点方法
- 错发漏发追溯、发货差错原因分析
- 非标品入库质检、商品编码规则
- 非标品库位规划、热销品库位优化
- 非标品拣货效率、拣货路径优化
- 非标品包装标准"""
    },
    {
        "id": "06",
        "name": "自发货转云仓临界点",
        "target": 2000,
        "direction": """重点方向：
- 什么时候该停止自发货、自发货到多少单该外包
- 自发货多少单会崩、自发货瓶颈
- 自建仓成本计算、自建仓隐性成本
- 自发货人工成本、打包发货人工费用
- 仓库外包临界点、电商外包仓储时机
- 中小电商品牌要不要外包仓储决策
- 从家里发货到云仓发货、家庭仓库升级
- 主理人品牌仓配转型、独立品牌仓库升级
- 小团队发货压力、2-3人团队发货瓶颈
- 订单增长后仓库管理问题
- 自发货库存混乱、手工管理库存问题
- 自建仓和外包仓成本对比模型
- 从手工表格到WMS系统的转型
- 仓库人员招聘成本、仓库员工管理难度
- 打包出错率、自发货差错率
- 发货延迟原因和解决
- 品牌月销多少适合用云仓
- 自发货到云仓的过渡方案
- 云仓合同最小起订量
- 品牌成长阶段的仓配策略"""
    },
    {
        "id": "07",
        "name": "直播电商_视频号电商_抖音电商履约",
        "target": 2000,
        "direction": """重点方向：
- 直播电商仓配方案、直播间发货
- 视频号小店发货要求、视频号仓配
- 抖音小店仓配方案、抖音电商发货
- 爆单后发货跟不上、爆单应急发货
- 直播爆单后仓库产能不足
- 大促订单波动处理、订单波峰管理
- 预售订单和现货订单管理、预售发货
- 直播退货高峰处理、直播退货率
- 直播间赠品搭配、赠品发货管理
- 直播订单复核标准、直播发货检查
- 抖音小店超时发货处罚、发货时效
- 视频号小店退货处理流程
- 爆单后库存不准、实时库存同步
- 直播电商售后仓配、售后发货
- 直播电商仓库排班、弹性人力
- 大促临时人力配置、临时打包工
- 直播电商物流成本控制
- 抖音直播间闪购发货
- 视频号直播间订单处理
- 直播电商多SKU拣货"""
    },
    {
        "id": "08",
        "name": "区域云仓_广州华南广东珠三角",
        "target": 2000,
        "direction": """重点方向：
- 广州云仓推荐指标、广州云仓选择
- 华南云仓分布、华南区域仓配
- 广东云仓选择、广东电商仓配
- 珠三角云仓优势、珠三角仓配网络
- 深圳电商云仓、深圳仓配方案
- 佛山电商仓配、佛山云仓
- 东莞云仓、东莞仓配
- 广州鞋服云仓、广州服装仓配
- 华南服装仓配、华南鞋类仓配
- 珠三角小红书电商仓配
- 广州女装云仓、广州女装发货
- 广东小红书电商仓、广东小红书发货
- 华南直播电商仓配、广州直播发货
- 广州美妆云仓、广州美妆发货
- 珠三角退货仓、广东退货处理
- 广东高客单价品牌仓配
- 华南云仓和华东云仓对比
- 广州云仓物流时效、珠三角发货速度
- 广东云仓收费标准
- 华南区域云仓覆盖范围"""
    },
    {
        "id": "09",
        "name": "云仓SLA_服务边界",
        "target": 2000,
        "direction": """重点方向：
- 云仓SLA关键指标、SLA怎么定
- 出库时效标准、出库时效保障
- 错发漏发赔付标准、错发率指标
- 库存准确率标准、库存准确率保障
- 售后响应时效、售后处理速度
- 退货处理时效标准、退货入库时效
- 大促保障条款、大促SLA特殊要求
- 赔付规则设计、赔偿标准
- 服务边界定义、云仓责任范围
- 合同条款注意事项、云仓合同风险
- 异常件处理流程、异常件责任划分
- 破损赔付标准、货损赔偿
- 超时发货处罚、超时发货责任
- 售后工单处理、售后工单流程
- 客诉责任划分、客诉处理
- 外包仓合同风险、合同陷阱
- 云仓服务降级条款
- SLA违约处理
- 云仓服务范围边界
- 仓配合同续约注意事项"""
    },
    {
        "id": "10",
        "name": "WMS库存可视化细分词",
        "target": 2000,
        "direction": """重点方向：
- 服装WMS系统选型、服装仓储管理系统
- 鞋服库存同步方案、实时库存同步
- 小红书店铺库存管理、小红书库存同步
- 多平台库存同步方案、跨平台库存
- 库位管理优化、库位分配策略
- 批次管理系统、批次追溯
- 异常库存处理、库存异常预警
- 退货入库同步、退货库存回传
- 库存不准原因、库存差异处理
- 错发漏发追溯系统、发货追溯
- WMS和OMS对接、系统集成
- WMS和电商平台同步、API对接
- 退货后库存回传、退货库存更新
- 多仓库存同步、分布式库存
- 库存冻结管理、库存锁定
- 预售库存管理、预售锁库存
- WMS报表分析、库存数据分析
- WMS条码管理、条码扫描
- 库存周转率分析、滞销品预警
- WMS系统切换注意事项"""
    },
    {
        "id": "11",
        "name": "对比型长尾词",
        "target": 2000,
        "direction": """重点方向：
- 自建仓 vs 第三方云仓成本和效率对比
- 普通云仓 vs 精细化云仓服务区别
- 低价云仓 vs 服务型云仓怎么选
- 一件代发 vs 云仓仓配区别
- 代发仓 vs 品牌云仓区别
- 仓储外包 vs 自发货哪个好
- 鞋服云仓 vs 普通电商仓区别
- 小红书电商仓配 vs 淘宝电商仓配
- 直播电商仓配 vs 传统电商仓配
- 高客单价云仓 vs 普通云仓
- 区域云仓 vs 全国仓哪个好
- 自建仓 vs 外包仓成本对比模型
- 低价仓配和高服务仓配区别
- 标品仓配 vs 非标品仓配
- B2B仓配 vs B2C仓配
- 现货仓配 vs 预售仓配
- 共享仓 vs 独立仓
- 第三方仓 vs 前置仓
- 本地云仓 vs 异地云仓
- 平台仓 vs 第三方云仓"""
    },
    {
        "id": "12",
        "name": "美妆护肤香水仓配",
        "target": 2000,
        "direction": """重点方向：
- 美妆云仓选择、美妆仓配方案
- 护肤品仓配要求、护肤品仓储
- 香水仓配特殊要求、香水发货
- 美妆批次管理、美妆生产批次
- 美妆效期管理、临期品处理
- 美妆礼盒发货、美妆套装发货
- 美妆赠品搭配、小样管理
- 美妆破损预防、易碎品包装
- 液体商品仓配、液体发货包装
- 香水易碎品发货、香水防震
- 小红书美妆品牌仓配
- 美妆退货质检、美妆退货流程
- 美妆试用装管理、赠品库存
- 美妆库存同步、美妆SKU管理
- 美妆包装复核、出库检查
- 美妆品牌履约体验
- 美妆温控仓储、化妆品存储条件
- 美妆标签管理、成分标签
- 护肤品退换货处理
- 美妆大促仓配保障"""
    },
    {
        "id": "13",
        "name": "礼盒饰品潮玩仓配",
        "target": 2000,
        "direction": """重点方向：
- 礼盒商品仓配方案、礼盒包装流程
- 饰品仓配要求、饰品仓储管理
- 潮玩仓配方案、潮玩发货
- 礼盒包装复核标准、礼盒出库检查
- 饰品防丢件措施、小件商品管理
- 潮玩盲盒发货、盲盒仓储
- 礼盒破损预防、礼盒防震包装
- 饰品退货质检、饰品退换货
- 礼盒赠品搭配、礼盒内衬管理
- 非标礼盒仓储、定制礼盒管理
- 高价值饰品出库、贵重品发货
- 潮玩库存管理、潮玩SKU管理
- 礼盒大促发货、礼盒节日促销
- 饰品小件多SKU管理
- 礼盒包装SOP、礼盒包装标准
- 潮玩批次管理、潮玩限量版
- 饰品包装防氧化、银饰仓储
- 礼盒组合订单、多件组合发货
- 潮玩预售发货、限量品抢购
- 饰品仓储温湿度要求"""
    },
    {
        "id": "14",
        "name": "退货逆向物流_售后仓配",
        "target": 2000,
        "direction": """重点方向：
- 退货逆向物流方案、逆向物流管理
- 售后仓配方案、售后仓库配置
- 退货质检流程设计、质检标准
- 退货拍照留证、退货图片管理
- 退货重新上架流程、二次上架时效
- 退货残次分类、残次品处理
- 退货工单管理、退货工单流程
- 退货与客服协同、退货客服配合
- 逆向物流时效、退货物流速度
- 退货仓配置、退货仓管理
- 售后仓功能、售后仓设计
- 退货入库同步、退货系统同步
- 退货库存回传、退货库存更新
- 售后客诉处理流程、客诉响应
- 退货责任划分、退货费用分摊
- 退货高峰期处理、大促退货
- 退货数据分析、退货率统计
- 退货商品翻新、退货修复
- 逆向物流成本优化
- 退货仓和正向仓分离"""
    },
    {
        "id": "15",
        "name": "大促爆单预售履约",
        "target": 2000,
        "direction": """重点方向：
- 大促仓配保障方案、618/双11仓配
- 爆单发货策略、爆单产能应对
- 预售订单履约流程、预售发货管理
- 现货订单和预售订单分开管理
- 大促临时人力配置、临时工管理
- 爆单后库存不准、库存实时同步
- 大促错发漏发预防、发货差错控制
- 直播爆单仓库产能不足
- 大促退货高峰处理、退货缓冲
- 预售转现货管理、预售发货节奏
- 大促仓库排班、弹性排班
- 大促出库时效保障、发货速度
- 大促拣货复核加强、检查加严
- 大促包装耗材准备、耗材储备
- 大促SLA特殊条款、大促服务保障
- 大促仓配成本核算、峰值成本
- 大促前库存盘点、备货检查
- 大促发货分波次策略
- 大促后退货处理预案
- 大促物流合作商对接"""
    }
]

# ── 模板提示词 ──────────────────────────────────────
SYSTEM_PROMPT = """你是一个SEO/GEO关键词分析师。你的任务是为电商仓配行业生成客户真实会搜索的问题型标题。

严格要求：
1. 只输出编号列表，每行一个标题
2. 格式：序号. 标题
3. 每个标题12-45个中文字符
4. 像真实客户会搜索的问题
5. 适合SEO和GEO
6. 有明确搜索意图和商业决策价值
7. 标题类型可以是：问题型、标准型、对比型、避坑型、临界点型、流程型、场景型、清单型、诊断型、决策型

禁止生成：
- 纯品牌宣传标题
- 泛泛的"云仓是什么"类标题
- 广告口吻标题
- 小红书/公众号/短视频风格标题
- 情绪化标题党
- 过于宽泛的标题
- 无搜索意图的标题

以下是你要避免生成的已有强势标题（不要和这些重复或过于相似）：
云仓怎么选、第三方云仓靠谱吗、上海云仓推荐、云仓发货靠谱吗、电商云仓外包、
什么是云仓、云仓和仓库有什么区别、中高端品牌为什么选择云仓、云仓服务商怎么选、
云仓有什么优势、云仓发货安全吗、云仓收费标准是什么、第三方云仓推荐、
云仓哪家比较好、专业云仓服务商、云仓助力品牌增长"""

# ── 工具函数 ──────────────────────────────────────────

def normalize(text: str) -> str:
    """归一化：去掉标点、空格、编号、大小写"""
    text = text.strip()
    text = re.sub(r'^\d+[\.\、\)\]\s]+', '', text)
    text = re.sub(r'[，。？！、；：""''（）【】《》\s\.\,\?\!\;\:\"\'\(\)\[\]\<\>]', '', text)
    text = text.lower()
    text = unicodedata.normalize('NFKC', text)
    return text


def similarity(a: str, b: str) -> float:
    """计算两个标题的相似度"""
    na = normalize(a)
    nb = normalize(b)
    if na == nb:
        return 1.0
    return SequenceMatcher(None, na, nb).ratio()


def is_similar_to_any(title: str, existing: list, threshold: float = SIMILARITY_THRESHOLD) -> bool:
    """检查标题是否与已有标题相似"""
    nt = normalize(title)
    for et in existing:
        ne = normalize(et)
        if nt == ne:
            return True
        if SequenceMatcher(None, nt, ne).ratio() >= threshold:
            return True
    return False


def quality_check(title: str) -> bool:
    """质量检查"""
    title = title.strip()
    if not title:
        return False
    if len(title) < MIN_TITLE_LEN or len(title) > MAX_TITLE_LEN:
        return False
    
    # 禁止的模式
    forbidden = [
        r'值得信赖', r'专业可靠', r'实力雄厚', r'首选', r'不二之选',
        r'助力.*增长', r'赋能', r'揭秘', r'震惊', r'万万没想到',
        r'建议收藏', r'必看', r'干货分享', r'盘点\d+大',
        r'选择.*的\d+个理由', r'强烈推荐',
        r'专业云仓服务商', r'首选云仓',
    ]
    for pat in forbidden:
        if re.search(pat, title):
            return False
    
    # 禁止只有名词堆砌
    if not re.search(r'[怎为什如何是否有哪些哪些什么应该如何哪]', title) and \
       not re.search(r'[vs比和与]', title, re.IGNORECASE) and \
       not re.search(r'[区别对比差异优劣]', title) and \
       not re.search(r'[吗呢吧]', title) and \
       not re.search(r'[流程方案标准指标策略]', title):
        # 如果没有任何疑问/对比/流程关键词，可能是纯名词
        if len(title) < 20:
            return False
    
    return True


def clean_title(title: str) -> str:
    """清洗标题"""
    title = title.strip()
    # 去掉编号
    title = re.sub(r'^\d+[\.\、\)\]\s]+', '', title)
    # 去掉引号
    title = re.sub(r'^["""\']+|["""\']+$', '', title)
    # 去掉多余空格
    title = re.sub(r'\s+', ' ', title).strip()
    return title


def call_api(prompt: str, max_tokens: int = 4000) -> str:
    """调用 MiMo API"""
    url = f"{BASE_URL}/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    payload = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": max_tokens,
        "temperature": 0.92,
        "top_p": 0.95,
    }).encode('utf-8')
    
    for attempt in range(RETRY_MAX):
        try:
            req = urllib.request.Request(url, data=payload, headers=headers, method='POST')
            with urllib.request.urlopen(req, timeout=90) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                return data['choices'][0]['message']['content']
        except (urllib.error.URLError, urllib.error.HTTPError, Exception) as e:
            print(f"  API调用失败 (attempt {attempt+1}/{RETRY_MAX}): {e}")
            if attempt < RETRY_MAX - 1:
                wait = RETRY_DELAY * (attempt + 1)
                print(f"  等待 {wait}s 后重试...")
                time.sleep(wait)
            else:
                raise


def parse_titles(raw: str) -> list:
    """从API返回中解析标题"""
    titles = []
    for line in raw.split('\n'):
        line = line.strip()
        if not line:
            continue
        # 去掉编号
        line = re.sub(r'^\d+[\.\、\)\]\s]+', '', line)
        # 去掉markdown列表标记
        line = re.sub(r'^[-*]\s+', '', line)
        # 去掉引号
        line = re.sub(r'^["""\']+|["""\']+$', '', line)
        line = line.strip()
        if not line:
            continue
        # 跳过太短的
        if len(line) < MIN_TITLE_LEN:
            continue
        # 跳过太长的
        if len(line) > MAX_TITLE_LEN:
            continue
        # 跳过看起来是解释的
        if re.match(r'^(注|说明|以上|以下是|下面|补充|注意|备注)', line):
            continue
        if len(line) > 15 and '：' in line[:10]:
            # 可能是"说明：xxxx"格式
            continue
        titles.append(line)
    return titles


def load_existing(filepath: Path) -> list:
    """加载已有文件中的标题"""
    titles = []
    if filepath.exists():
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    titles.append(line)
    return titles


def save_titles(filepath: Path, titles: list):
    """保存标题到文件"""
    with open(filepath, 'w', encoding='utf-8') as f:
        for t in titles:
            f.write(t + '\n')


def load_dedupe_index() -> dict:
    """加载去重索引"""
    idx_path = OUTPUT_DIR / "dedupe_index.json"
    if idx_path.exists():
        with open(idx_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_dedupe_index(index: dict):
    """保存去重索引"""
    idx_path = OUTPUT_DIR / "dedupe_index.json"
    with open(idx_path, 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)


def build_prompt(category: dict, existing_recent: list, round_num: int) -> str:
    """构建生成提示词"""
    direction = category['direction']
    cat_name = category['name'].replace('_', '/')
    
    recent_block = ""
    if existing_recent:
        recent_block = "\n\n以下是最近已生成的标题（必须避免重复和相似）：\n"
        for i, t in enumerate(existing_recent[-60:], 1):
            recent_block += f"{t}\n"
    
    prompt = f"""请为"{cat_name}"方向生成 {BATCH_SIZE} 个SEO/GEO关键词型标题。

{direction}

这是第 {round_num} 轮生成。请确保与之前生成的标题不重复、不相似。
{recent_block}

要求：
1. 每行一个标题，格式：序号. 标题
2. 每个标题12-45个中文字符
3. 像真实客户会搜索的问题
4. 有明确搜索意图和商业决策价值
5. 不要泛泛的云仓科普词
6. 不要品牌宣传
7. 不要广告口吻
8. 不要情绪化标题党
9. 偏细分长尾词、偏决策词

请生成 {BATCH_SIZE} 个标题："""
    return prompt


def generate_for_category(cat: dict):
    """为一个分类生成标题"""
    filepath = OUTPUT_DIR / f"{cat['id']}_{cat['name']}.txt"
    existing = load_existing(filepath)
    target = cat['target']
    
    print(f"\n{'='*60}")
    print(f"分类 {cat['id']}: {cat['name']}")
    print(f"目标: {target}, 已有: {len(existing)}")
    print(f"{'='*60}")
    
    if len(existing) >= target:
        print(f"  ✓ 已达到目标数量，跳过")
        return existing
    
    all_titles = existing[:]
    round_num = len(existing) // BATCH_SIZE + 1
    
    while len(all_titles) < target:
        needed = target - len(all_titles)
        batch_target = min(BATCH_SIZE, needed)
        
        print(f"\n  第 {round_num} 轮 (已有 {len(all_titles)}/{target}, 需要 {batch_target})...")
        
        recent = all_titles[-60:] if len(all_titles) > 60 else all_titles
        prompt = build_prompt(cat, recent, round_num)
        
        try:
            raw = call_api(prompt)
        except Exception as e:
            print(f"  ✗ API调用失败: {e}")
            print(f"  保存当前进度并继续下一个分类...")
            save_titles(filepath, all_titles)
            return all_titles
        
        new_titles = parse_titles(raw)
        print(f"  解析到 {len(new_titles)} 个标题")
        
        # 去重并添加
        added = 0
        for t in new_titles:
            if not quality_check(t):
                continue
            if not is_similar_to_any(t, all_titles):
                all_titles.append(t)
                added += 1
        
        print(f"  去重后新增 {added} 个, 总计 {len(all_titles)}")
        
        # 保存进度
        save_titles(filepath, all_titles)
        
        round_num += 1
        
        # 限速
        time.sleep(RATE_LIMIT_DELAY)
    
    print(f"\n  ✓ 分类 {cat['id']} 完成: {len(all_titles)} 个标题")
    return all_titles


def build_all_titles():
    """合并所有分类标题到 all_titles.txt"""
    all_titles = []
    seen = []
    
    for cat in CATEGORIES:
        filepath = OUTPUT_DIR / f"{cat['id']}_{cat['name']}.txt"
        titles = load_existing(filepath)
        
        added = 0
        for t in titles:
            if not is_similar_to_any(t, seen):
                seen.append(t)
                all_titles.append(t)
                added += 1
        
        print(f"  {cat['id']}_{cat['name']}: {len(titles)} 个, 跨分类去重后新增 {added}")
    
    save_titles(OUTPUT_DIR / "all_titles.txt", all_titles)
    print(f"\n  all_titles.txt: {len(all_titles)} 个标题")
    return all_titles


def select_top_n(all_titles: list, n: int, output_name: str, strict_threshold: float = None):
    """从全部标题中筛选top-N"""
    threshold = strict_threshold or SIMILARITY_THRESHOLD
    
    # 评分关键词权重
    high_value_keywords = [
        # 鞋服 +4
        '鞋服', '服装', '女装', '男装', '运动服', '童装',
        # 小红书 +4
        '小红书',
        # 退货 +3
        '退货', '退换', '逆向', '售后',
        # 高客单价 +3
        '高客单价', '高端', '礼盒', '饰品', '潮玩', '美妆',
        # WMS +3
        'WMS', '库存', '库位', '同步',
        # SLA +3
        'SLA', '时效', '赔付', '服务边界', '合同',
        # 区域 +3
        '广州', '华南', '广东', '珠三角', '深圳', '佛山', '东莞',
        # 非标品 +2
        '多SKU', '多规格', '非标品', '多尺码', '多颜色', '多款式',
        # 自发货 +2
        '自发货', '临界点', '自建仓', '外包',
        # 直播 +2
        '直播', '抖音', '视频号', '爆单',
        # 对比型 +2
        '区别', '对比', 'vs', '哪个好',
        # 大促 +2
        '大促', '预售', '618', '双11',
        # 决策词 +2
        '怎么选', '怎么看', '怎么定', '怎么做', '如何',
        # 流程型 +1
        '流程', '方案', '标准', '规范', 'SOP',
        # 清单型 +1
        '必须', '确认', '注意', '检查',
    ]
    
    def score(title: str) -> int:
        s = 0
        for kw in high_value_keywords:
            if kw in title:
                s += 1
        # 偏好中等长度
        if 15 <= len(title) <= 40:
            s += 1
        # 偏好包含问号
        if '?' in title or '？' in title:
            s += 1
        # 惩罚太短
        if len(title) < 15:
            s -= 2
        return s
    
    # 评分排序
    scored = [(t, score(t)) for t in all_titles]
    scored.sort(key=lambda x: -x[1])
    
    # 严格去重后取top
    selected = []
    for t, s in scored:
        if len(selected) >= n:
            break
        if not is_similar_to_any(t, selected, threshold):
            selected.append(t)
    
    save_titles(OUTPUT_DIR / output_name, selected)
    print(f"  {output_name}: {len(selected)} 个标题 (阈值 {threshold})")
    return selected


# ── 主流程 ──────────────────────────────────────────

def main():
    if not API_KEY:
        print("错误: 未设置 MIMO_API_KEY 环境变量")
        print("请运行: export MIMO_API_KEY=your_key")
        return
    
    print("=" * 60)
    print("GEO/SEO 关键词问题池批量生成")
    print(f"API: {BASE_URL}")
    print(f"模型: {MODEL}")
    print(f"输出目录: {OUTPUT_DIR}")
    print(f"每轮批量: {BATCH_SIZE}")
    print(f"相似度阈值: {SIMILARITY_THRESHOLD}")
    print("=" * 60)
    
    start_time = time.time()
    
    # 第一阶段：逐分类生成
    all_cat_titles = {}
    for cat in CATEGORIES:
        titles = generate_for_category(cat)
        all_cat_titles[cat['id']] = len(titles)
    
    # 第二阶段：合并
    print("\n" + "=" * 60)
    print("合并所有标题到 all_titles.txt")
    print("=" * 60)
    all_titles = build_all_titles()
    
    # 第三阶段：筛选
    print("\n" + "=" * 60)
    print("筛选 Top 标题")
    print("=" * 60)
    select_top_n(all_titles, 1000, "selected_top_1000.txt", strict_threshold=0.85)
    select_top_n(all_titles, 100, "selected_top_100.txt", strict_threshold=0.82)
    select_top_n(all_titles, 30, "selected_geo_30.txt", strict_threshold=0.80)
    
    # 保存去重索引
    dedupe_index = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_all_titles": len(all_titles),
        "categories": all_cat_titles,
        "similarity_threshold": SIMILARITY_THRESHOLD,
    }
    save_dedupe_index(dedupe_index)
    
    elapsed = time.time() - start_time
    
    # 最终统计
    print("\n" + "=" * 60)
    print("任务完成")
    print("=" * 60)
    for cat in CATEGORIES:
        filepath = OUTPUT_DIR / f"{cat['id']}_{cat['name']}.txt"
        count = len(load_existing(filepath))
        print(f"  {cat['id']}_{cat['name']}: {count}/{cat['target']}")
    print(f"\n  all_titles.txt: {len(all_titles)}")
    print(f"  selected_top_1000.txt: 已生成")
    print(f"  selected_top_100.txt: 已生成")
    print(f"  selected_geo_30.txt: 已生成")
    print(f"  总耗时: {elapsed/60:.1f} 分钟")


if __name__ == "__main__":
    main()
