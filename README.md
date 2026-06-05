# GEO 关键词问题池

第三方云仓 / 鞋服云仓 / 小红书电商仓配 / GEO 关键词标题批量生成项目。

## 项目说明

为新亦源（56XYYY）电商仓配业务批量生成 SEO / GEO 候选关键词标题池，用于后续内容营销。

## 文件结构

- `01_鞋服云仓_服装电商仓配.txt` ~ `15_大促爆单预售履约.txt` — 15个分类标题文件
- `all_titles.txt` — 去重后合并标题（30,326条）
- `selected_top_1000.txt` — 筛选 top 1000
- `selected_top_100.txt` — 筛选 top 100
- `selected_geo_30.txt` — GEO 最优 30 条
- `generate_keyword_titles.py` — 主生成脚本（支持断点续跑）
- `merge_fast.py` — 合并筛选脚本
- `dedupe_index.json` — 去重索引

## 使用方式

```bash
# 设置环境变量
export MIMO_API_KEY=your_key
export MIMO_BASE_URL=https://token-plan-sgp.xiaomimimo.com/v1
export MIMO_MODEL=mimo-v2.5-pro

# 运行生成
python3 generate_keyword_titles.py
```
