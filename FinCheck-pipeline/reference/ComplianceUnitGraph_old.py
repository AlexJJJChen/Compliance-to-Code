# 绘图函数

STYLE_CONFIG = {
        "NODE": {
            "root": {
                "color": "#6D8A7E", 
                "size": 30, 
                "label": {
                    "color": "#FFFFFF",
                    "fontWeight": "bolder",
                    "textBorderColor": "#3A4A43",
                    "textBorderWidth": 2
                }
            },
            "law": {
                "color": "#B5C2B8", 
                "size": 20, 
                "label": {
                    "color": "#4E6056",
                    "fontWeight": "bold",
                    "textBorderColor": "#FFFFFF",
                    "textBorderWidth": 1
                }
            },
            "meu": {
                "color": "#D1D9D4", 
                "size": 10, 
                "label": {
                    "color": "#6D8A7E",
                    "textBorderColor": "#F5F7F6",
                    "textBorderWidth": 1
                }
            },
            "ref_law": {
                "color": "#E8EAE6", 
                "size": 16, 
                "label": {
                    "color": "#909E95",
                    "textBorderColor": "#FFFFFF",
                    "textBorderWidth": 0.5
                }
            },
            "ref_meu": {
                "color": "#E8EAE6", 
                "size": 14, 
                "label": {
                    "color": "#909E95",
                    "fontStyle": "italic"
                }
            },
            "ref_generic": {
                "color": "#E8EAE6", 
                "size": 14, 
                "label": {
                    "color": "#909E95",
                    "textBorderColor": "#FFFFFF",
                    "textBorderWidth": 0.5
                }
            }
        },
        "EDGE": {
            "hierarchy": {
                "color": "#A3B2A8", 
                "width": 1.2, 
                "type": "solid", 
                "label": "#7A8D84"
            },
            "default": {
                "color": "#DCE1DD", 
                "width": 0.8, 
                "type": "solid", 
                "label": "#B5C2B8"
            }
        },
        "RELATION": {
            "refer_to": {
                "color": "#5B8DB6", 
                "width": 2, 
                "type": "dashed", 
                "label": "#2A4E6E"
            },
            "combine": {
                "color": "#7CA17D", 
                "width": 2, 
                "label": "#3F5940"
            },
            "depend": {
                "color": "#8874A3", 
                "width": 2, 
                "label": "#4A3B61"
            },
            "exclude": {
                "color": "#B1443C", 
                "width": 2, 
                "label": "#7D2F28"
            },
            "only_include": {
                "color": "#5F8EA9", 
                "width": 2, 
                "label": "#2F5266"
            },
            "mutual": {
                "color": "#5D9B82", 
                "width": 2, 
                "label": "#2D5948"
            },
            "override": {
                "color": "#9E86B8", 
                "width": 2, 
                "label": "#634D7B"
            },
            # 新增默认关系配置
            "default": {
                "color": "#9E9E9E",
                "width": 1.5,
                "type": "dotted",
                "label": "#757575"
            }
        },
        "GLOBAL": {
            "title_color": "#4E6056",
            "legend_color": "#7A8D84",
            "background_color": "#FFFFFF"
        }
    }

import os
import pandas as pd
from pyecharts import options as opts
from pyecharts.charts import Graph
from pyecharts.commons.utils import JsCode

def format_target(t):
    """格式化法律节点名称"""
    if isinstance(t, str) and t.startswith("LAW_"):
        return f"Law_{t.split('_')[1]}"
    return t

def generate_meu_graph(file_name, STYLE_CONFIG):
    if '.' in file_name:
        file_name = file_name.split('.')[0]

    # 构建文件路径
    base_dir = "law_to_MEU"
    meu_csv = os.path.join(base_dir, "st_4_MEU_relations", "MEU_with_relation", "GT", f"{file_name}.xlsx")
    output_html = os.path.join(base_dir, "st_5_MEU_Graph_HTML", "GT", f"{file_name}.html")

    # 读取数据
    print(meu_csv)
    meu_df = pd.read_excel(meu_csv, engine='openpyxl')

    # 1. 按 MEU_id 去重（保留第一个出现的记录）
    meu_df = meu_df.drop_duplicates(subset=['MEU_id'], keep='first')

    # 2. 构建关系数据框
    relations_df = meu_df[meu_df['relation'].notna()].copy()  # 筛选非空relation行
    relations_df = relations_df[['MEU_id', 'relation', 'target']]
    relations_df = relations_df.rename(columns={'MEU_id': 'source'})
    # ==== 并列拆分逻辑 ====
    # 处理空值并拆分字符串
    relations_df['target'] = relations_df['target'].fillna('').astype(str)
    # 拆分成列表并展开
    relations_df = (
        relations_df.assign(target=relations_df['target'].str.split(';'))  # 拆分成分号分隔的列表
        .explode('target')                                                  # 展开为多行
        .reset_index(drop=True)                                             # 重置索引
    )
    # 清理空白字符并过滤空值
    relations_df['target'] = relations_df['target'].str.strip()
    relations_df = relations_df[relations_df['target'].ne('')]
    relations_df["target"] = relations_df["target"].apply(format_target)

    # 初始化图形元素
    nodes = [{
        "name": "Root",
        "symbolSize": STYLE_CONFIG["NODE"]["root"]["size"],
        "itemStyle": {"color": STYLE_CONFIG["NODE"]["root"]["color"]},
        "label": {"show": True, **STYLE_CONFIG["NODE"]["root"]["label"]}
    }]
    edges = []

    # 创建基础树状结构
    for _, row in meu_df.iterrows():
        meu_id = row["MEU_id"]
        
        try:
            law_num = meu_id.split('_')[1]
            law_node = f"Law_{law_num}"
        except IndexError:
            continue

        # 添加法条节点
        if not any(n["name"] == law_node for n in nodes):
            nodes.append({
                "name": law_node,
                "symbolSize": STYLE_CONFIG["NODE"]["law"]["size"],
                "itemStyle": {"color": STYLE_CONFIG["NODE"]["law"]["color"]},
                "label": {"show": True, **STYLE_CONFIG["NODE"]["law"]["label"]}
            })
            edges.append({
                "source": law_node,
                "target": "Root",
                "lineStyle": {k: v for k, v in STYLE_CONFIG["EDGE"]["hierarchy"].items() if k != "label"},
                "label": {"show": False}
            })

        # 添加MEU节点
        nodes.append({
            "name": meu_id,
            "symbolSize": STYLE_CONFIG["NODE"]["meu"]["size"],
            "value": f"Subject: {row['subject']}<br>Condition: {row['condition']}<br>Constraint: {row['constraint']}<br>Context: {row['contextual_info']}", 
            "itemStyle": {"color": STYLE_CONFIG["NODE"]["meu"]["color"]},
            "label": {"show": True, **STYLE_CONFIG["NODE"]["meu"]["label"]}
        })
        edges.append({
            "source": meu_id,
            "target": law_node,
            "lineStyle": {k: v for k, v in STYLE_CONFIG["EDGE"]["hierarchy"].items() if k != "label"},
            "label": {"show": False}
        })

    # 处理关系数据
    for _, row in relations_df.iterrows():
        src, rel, tgt = row["source"], row["relation"], row["target"]
        
        # 自动补全缺失节点
        for node in [src, tgt]:
            if not any(n["name"] == node for n in nodes):
                node_type = "ref_law" if node.startswith("Law_") else "ref_meu" if node.startswith("MEU_") else "ref_generic"
                
                nodes.append({
                    "name": node,
                    "symbolSize": STYLE_CONFIG["NODE"][node_type]["size"],
                    "itemStyle": {"color": STYLE_CONFIG["NODE"][node_type]["color"]},
                    "label": {"show": True, **STYLE_CONFIG["NODE"][node_type]["label"]}
                })
                
                if node.startswith("Law_"):
                    edges.append({
                        "source": node,
                        "target": "Root",
                        "lineStyle": {k: v for k, v in STYLE_CONFIG["EDGE"]["hierarchy"].items() if k != "label"},
                        "label": {"show": False}
                    })

        # 添加关系边（修改此处逻辑）
        edge_style = STYLE_CONFIG["RELATION"].get(rel, STYLE_CONFIG["RELATION"]["default"])
        edges.append({
            "source": src,
            "target": tgt,
            "lineStyle": {k: v for k, v in edge_style.items() if k != "label"},
            "label": {
                "show": True,
                "formatter": rel,
                "color": edge_style["label"],
                "fontSize": 12
            }
        })

    # 生成可视化图表
    graph = (
        Graph(init_opts=opts.InitOpts(
            width="1600px", 
            height="900px",
            bg_color=STYLE_CONFIG["GLOBAL"]["background_color"]
        ))
        .add(
            "",
            nodes,
            edges,
            repulsion=15000,
            edge_symbol=["circle", "arrow"],
            tooltip_opts=opts.TooltipOpts(
                formatter=JsCode("""
                    function(params) {
                        if (params.dataType === 'node') {
                            return params.data.value || params.data.name;
                        }
                    }
                """)
            )
        )
        .set_global_opts(
            title_opts=opts.TitleOpts(
                title="MEU Decision Graph",
                title_textstyle_opts=opts.TextStyleOpts(
                    color=STYLE_CONFIG["GLOBAL"]["title_color"],
                    font_size=20
                )
            ),
            legend_opts=opts.LegendOpts(
                orient="vertical",
                pos_left="2%",
                pos_top="20%",
                textstyle_opts=opts.TextStyleOpts(
                    color=STYLE_CONFIG["GLOBAL"]["legend_color"]
                ),
                selected_map={
                    "法律条款": True,
                    "业务规则": True,
                    "参考关系": True
                }
            )
        )
    )

    os.makedirs(os.path.dirname(output_html), exist_ok=True)
    graph.render(output_html)
    print(f"保存到: {output_html}")
    


# 定义文件目录路径
directory_path = r"law_to_MEU/st_4_MEU_relations/MEU_with_relation/GT"


filenames = [
    f for f in os.listdir(directory_path) if f.endswith('.xlsx')
]



