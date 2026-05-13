import gradio as gr
import pandas as pd
import json
from openai import OpenAI
from pathlib import Path
import convertexcel2json
import os
from dotenv import load_dotenv

INTERNAL_BASE_URL = "https://api.deepseek.com"
INTERNAL_MODEL_NAME = "deepseek-chat"
DISPLAY_MODEL_NAME = "deepseek动态量化部署"
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY")

if not INTERNAL_API_KEY:
    raise ValueError("API Key 缺失！请检查根目录下的 .env 文件是否配置正确。")

# ==========================================
# 1. 核心格式化工具 (告别 None 和丑陋空括号)
# ==========================================
def clean_format(disease, time, icd):
    """智能清洗单元格，如果有病程和ICD才加括号，空值直接隐身"""
    # 强制将系统空值 None 变成人类看不见的空字符串 ""
    d = "" if disease is None else str(disease).strip()
    t = "" if time is None else str(time).strip()
    i = "" if icd is None else str(icd).strip()
    
    # 如果没写病，格子直接变成绝对空白
    if not d or d == "无":
        return ""
        
    # 准备一个专门装“括号里附加信息”的小推车
    extras = []
    if t and t != "未知":
        extras.append(f"病程:{t}")
    if i and i != "无编码":
        extras.append(f"ICD:{i}")
        
    # 如果小推车里有货，就把它们组装进括号里；没货就只输出疾病名！
    if extras:
        return f"{d} ({' | '.join(extras)})"
    return d

# ==========================================
# 2. 大模型审核引擎 (保持上一版精准的免死金牌)
# ==========================================
# ==========================================
# 2. 大模型审核引擎 (加入 I-d 层级)
# ==========================================
# ==========================================
# 2. 大模型审核引擎 (加入《指导手册》权威设定与 I-d 层级)
# ==========================================
def call_llm_for_review(clean_text: str) -> dict:
    client = OpenAI(api_key=INTERNAL_API_KEY, base_url=INTERNAL_BASE_URL)
    
    # 🌟 修改点：在最开头加入了最高权重的【核心指令】，锁定《人口死因监测工作指导手册》
    sys_prompt = """你是一个极其严谨的人口死因监测审核专家与资深ICD-10编码员。
【核心指令】你所有的逻辑推演和审核判定，必须严格以国家《人口死因监测工作指导手册》为唯一权威准绳！禁止使用任何未经该手册确认的边缘医学知识。

【核心质控规则】（必须严格执行）
1. 真正的死因因果链条：医学上的因果关系是【自下而上】的！即：如果是完整的链条，必须是 I-d 引起 I-c，I-c 引起 I-b，I-b 引起 I-a。
2. 起始原因原则（最底层溯源）：医生填报的【根本死因】，必须与死因链条中【最底层且有内容的起始疾病】一致（例如：有d选d，无d有c选c，无c有b选b，只有a选a）。
3. ⚠️ 病程逻辑倒置检查（方向极度重要）：
   - 作为“原因”的疾病，其病程必须【大于或等于】作为“结果”的疾病。
   - 正确逻辑示范：I-b(病程15年) 引起 I-a(病程2天) 是完全正常的！
   - 错误逻辑示范：I-b(病程2天) 引起 I-a(病程15年) 才是病程逻辑倒置！因为短病程绝对不可能引起长病程。
4. 晚期并发症禁忌（精确打击靶点）：【根本死因】绝对不能是“心力衰竭、呼吸衰竭、休克、心肺骤停、猝死”。
   👉 【免死金牌（极其重要）】：上述晚期并发症作为 I-a（直接死因）是【完全合法且符合医学常理】的！你【绝对不允许】因为 I-a 填写了呼吸衰竭、心力衰竭等并发症而判为异常！
5. ICD-10 编码精准校验：必须逐一核对案卷中所有出现的疾病与其附带的ICD编码是否匹配。

【输出要求】
请严格返回纯净的JSON对象，绝对不要包含```json等Markdown代码块符号。必须包含思考链：
{
  "step1_找底层": "分析死因链，明确指出因果关系（谁引起谁），以及最底层的起始疾病是什么，根本死因是否与之一致。",
  "step2_查编码": "逐一核查ICD编码是否与疾病名相符？",
  "status": "正常" 或 "异常",
  "error_reason": "如果异常，必须明确指出具体违规点。如果全对填无"
}
"""
    
    user_prompt = f"请审核案卷：\n{clean_text}\n请输出纯JSON："

    try:
        response = client.chat.completions.create(
            model=INTERNAL_MODEL_NAME,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"}, 
            temperature=0.0 
        )
        
        raw_content = response.choices[0].message.content.strip()
        if raw_content.startswith("```json"):
            raw_content = raw_content[7:]
        elif raw_content.startswith("```"):
            raw_content = raw_content[3:]
        if raw_content.endswith("```"):
            raw_content = raw_content[:-3]
        
        return json.loads(raw_content.strip())
        
    except json.JSONDecodeError as e:
        return {"status": "格式崩溃", "error_reason": f"大模型吐出了乱码：{raw_content}"}
    except Exception as e:
        return {"status": "API异常", "error_reason": f"网络或系统报错: {str(e)}"}
    
    
def get_stitched_time(data_dict):
    """把散落在字典里的‘数字’和‘单位’缝起来"""
    val = ""
    unit = ""
    for k, v in data_dict.items():
        # 寻找包含“时间”或“间隔”的字段
        if "时间" in k or "间隔" in k or "死" in k:
            v_str = str(v).strip()
            # 如果是单位（年月日小时分秒），存入 unit
            if v_str in ["年", "月", "日", "天", "小时", "分钟", "秒"]:
                unit = v_str
            # 如果是数字（含小数点），存入 val
            elif v_str.replace('.', '', 1).isdigit():
                val = v_str
    return f"{val}{unit}" if val else unit

# ==========================================
# 3. Gradio 交互逻辑 (输出原生 HTML 表格版)
# ==========================================
def process_file(file_obj, start_row, end_row, progress=gr.Progress()):
    if file_obj is None:
        return "<div style='color:red; font-size:16px; padding:10px;'>系统提示：请先上传文件</div>"
        
    if start_row < 2:
        return "<div style='color:red; font-size:16px; padding:10px;'>错误：起始行不能小于2（第1行是表头）</div>"
    if start_row > end_row:
        return "<div style='color:red; font-size:16px; padding:10px;'>错误：起始行不能大于终止行</div>"

    try:
        progress(0, desc="正在解析数据...")
        excel_path = Path(file_obj.name)
        output_json_path = excel_path.with_suffix('.json')
        
        convertexcel2json.excel_to_json(excel_path, 0, output_json_path)
        
        with open(output_json_path, 'r', encoding='utf-8') as f:
            records = json.load(f)
            
        start_index = int(start_row) - 2
        end_index = int(end_row) - 1
        
        records_to_process = records[start_index:end_index]
        total = len(records_to_process)
        
        if total == 0:
             return "<div style='color:orange; font-size:16px; padding:10px;'>系统提示：选定的行数范围内没有数据</div>"

        results = []
        for i, record in enumerate(records_to_process):
            progress((i + 1) / total, desc=f"AI 正在审核第 {i+1}/{total} 条数据...")
            
            age = record.get("age", "")
            i_dict = record.get("I", {})

            ia_disease = i_dict.get("a", {}).get("疾病名称")
            ia_time = get_stitched_time(i_dict.get("a", {}))
            ia_icd = i_dict.get("a", {}).get("ICD10编码")
            
            ib_disease = i_dict.get("b", {}).get("疾病名称")
            ib_time = get_stitched_time(i_dict.get("b", {}))
            ib_icd = i_dict.get("b", {}).get("ICD10编码")
            
            ic_disease = i_dict.get("c", {}).get("疾病名称")
            ic_time = get_stitched_time(i_dict.get("c", {}))
            ic_icd = i_dict.get("c", {}).get("ICD10编码")
            
            id_disease = i_dict.get("d", {}).get("疾病名称")
            id_time = get_stitched_time(i_dict.get("d", {}))
            id_icd = i_dict.get("d", {}).get("ICD10编码")
            
            root_cause_dict = record.get("root_cause", {})
            root_cause = root_cause_dict.get("根本死亡原因") or record.get("根本死亡原因") or record.get("根本死因")
            
            root_icd = None
            for k, v in record.items():
                if isinstance(k, str) and "根本" in k and "编码" in k:
                    if v:  
                        root_icd = v
                        break  
            
            if not root_icd:
                for k, v in root_cause_dict.items():
                    if isinstance(k, str) and "编码" in k:
                        if v:
                            root_icd = v
                            break
            
            ia_display = clean_format(ia_disease, ia_time, ia_icd)
            ib_display = clean_format(ib_disease, ib_time, ib_icd)
            ic_display = clean_format(ic_disease, ic_time, ic_icd)
            id_display = clean_format(id_disease, id_time, id_icd)
            root_display = clean_format(root_cause, None, root_icd) 
            
            clean_text = f"【患者年龄】: {age}\n【死因链条】:\nI-a: {ia_display}\nI-b: {ib_display}\nI-c: {ic_display}\nI-d: {id_display}\n【根本死因】: {root_display}"
            
            ai_result = call_llm_for_review(clean_text)
            excel_row_num = int(start_row) + i
            
            # 🌟 注意这里：换行符改成了网页专用的 <br>
            results.append({
                "Excel行号": f"第 {excel_row_num} 行",
                "年龄": age,
                "I-a (病程|ICD)": ia_display,
                "I-b (病程|ICD)": ib_display,
                "I-c (病程|ICD)": ic_display,
                "I-d (病程|ICD)": id_display,
                "填报的根本死因 (ICD)": root_display,
                "AI质控状态": "✅ 正常" if ai_result.get("status") == "正常" else "❌ 异常",
                "AI逻辑推演": f"【溯源】{ai_result.get('step1_找底层', '')}<br><br>【查码】{ai_result.get('step2_查编码', '')}",
                "AI审核意见": str(ai_result.get("error_reason", "")).replace('\n', '<br>')
            })
            
        # 🌟 绝杀：手捏原生 HTML 表格，彻底摆脱交互劫持
        html_str = """
        <style>
            .native-table { width: 100%; border-collapse: collapse; font-family: sans-serif; font-size: 14px; background-color: white; }
            .native-table th { background-color: #f3f4f6; color: #374151; font-weight: bold; padding: 12px 8px; text-align: left; border: 1px solid #e5e7eb; }
            .native-table td { padding: 10px 8px; border: 1px solid #e5e7eb; vertical-align: top; word-break: break-word; line-height: 1.6; }
            .native-table tr:nth-child(even) { background-color: #f9fafb; }
            .native-table tr:hover { background-color: #f3f4f6; } /* 鼠标悬停时整行变色 */
        </style>
        <div style="overflow-x: auto;">
        <table class="native-table">
            <thead>
                <tr>
                    <th style="width: 6%;">Excel行号</th>
                    <th style="width: 4%;">年龄</th>
                    <th style="width: 10%;">I-a (病程|ICD)</th>
                    <th style="width: 10%;">I-b (病程|ICD)</th>
                    <th style="width: 10%;">I-c (病程|ICD)</th>
                    <th style="width: 10%;">I-d (病程|ICD)</th>
                    <th style="width: 12%;">填报的根本死因 (ICD)</th>
                    <th style="width: 6%;">AI质控状态</th>
                    <th style="width: 18%;">AI逻辑推演</th>
                    <th style="width: 14%;">AI审核意见</th>
                </tr>
            </thead>
            <tbody>
        """
        for row in results:
            html_str += "<tr>"
            html_str += f"<td>{row['Excel行号']}</td>"
            html_str += f"<td>{row['年龄']}</td>"
            html_str += f"<td>{row['I-a (病程|ICD)']}</td>"
            html_str += f"<td>{row['I-b (病程|ICD)']}</td>"
            html_str += f"<td>{row['I-c (病程|ICD)']}</td>"
            html_str += f"<td>{row['I-d (病程|ICD)']}</td>"
            html_str += f"<td>{row['填报的根本死因 (ICD)']}</td>"
            html_str += f"<td style='font-weight:bold; color:{'green' if '正常' in row['AI质控状态'] else 'red'};'>{row['AI质控状态']}</td>"
            html_str += f"<td>{row['AI逻辑推演']}</td>"
            html_str += f"<td>{row['AI审核意见']}</td>"
            html_str += "</tr>"
        
        html_str += "</tbody></table></div>"
        
        return html_str
        
    except Exception as e:
        return f"<div style='color:red; font-size:16px; padding:10px;'>系统报错: {str(e)}</div>"

# ==========================================
# 4. Gradio 页面布局 (原生 HTML 接收器)
# ==========================================
with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🏥 智能死因推断与编码溯源双轨审核系统")
    with gr.Row():
        with gr.Column(scale=1):
            model_name_display = gr.Textbox(label="模型名称", value=DISPLAY_MODEL_NAME, interactive=False)
            
            start_row = gr.Number(label="起始行 (Excel行号，含表头算起)", value=2, precision=0) 
            end_row = gr.Number(label="终止行 (Excel行号)", value=6, precision=0)
            
        with gr.Column(scale=2):
            file_input = gr.File(label="上传 Excel 文件", file_types=[".xlsx", ".xls"])
            analyze_btn = gr.Button("🚀 启动时间线与编码核查引擎", variant="primary", size="lg")
            
    with gr.Row():
        # 🌟 核心修改：抛弃难用的 gr.Dataframe，使用 gr.HTML 接收原生网页表格
        output_html = gr.HTML(label="📊 综合病理与编码质控结果")

    # 绑定事件
    analyze_btn.click(fn=process_file, inputs=[file_input, start_row, end_row], outputs=output_html)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)

