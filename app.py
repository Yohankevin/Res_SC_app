import streamlit as st
import pdfplumber
from docx import Document
import io
from openai import OpenAI
import plotly.graph_objects as go

# ================================
# DeepSeek 接口（新式 OpenAI v1）
# ================================
client = OpenAI(
    #api_key="sk-3d634e1fc268477187539d05dae79227",
    api_key=st.secrets["OPENAI_API_KEY"],  # 建议在 Streamlit Secrets 里放 API Key
    base_url="https://api.deepseek.com"    # DeepSeek 网关
)

# ================================
# 页面配置
# ================================
st.set_page_config(
    page_title="📄 招聘分析",
    layout="centered"
)
st.title("📄 招聘分析")

# ================================
# 文件上传 + JD 输入
# ================================
uploaded_file = st.file_uploader("📎 上传 PDF/Word 简历", type=["pdf", "docx"])
job_desc = st.text_area("✏️ 输入 JD（岗位描述）")

# ================================
# 解析简历内容
# ================================
def extract_text(file, ext):
    if ext == "pdf":
        with pdfplumber.open(io.BytesIO(file.read())) as pdf:
            return "\n".join([p.extract_text() or "" for p in pdf.pages])
    elif ext == "docx":
        doc = Document(io.BytesIO(file.read()))
        return "\n".join([p.text for p in doc.paragraphs])
    else:
        return ""

# ================================
# 人性材质学 · 多维度本地打分
# ================================
def local_multi_score_human_material(resume_text):
    score = {}

    score["核心能力突出性"] = 90 if "核心技术" in resume_text or "独立完成" in resume_text or "负责" in resume_text else 70
    score["能力持续稳定性"] = 85 if "多年" in resume_text or "持续" in resume_text or "长期" in resume_text else 60
    score["阻碍因子预测"] = 50 if "频繁跳槽" in resume_text or "冲突" in resume_text or "离职" in resume_text else 80  # 分高表示低风险
    score["岗位匹配度"] = 80 if "岗位" in resume_text or "职责" in resume_text else 50
    score["班子适应度"] = 85 if "团队合作" in resume_text or "跨部门" in resume_text else 60
    score["生态适应度"] = 90 if "适应" in resume_text or "灵活" in resume_text or "快速融入" in resume_text else 65

    score["综合匹配指数"] = sum(score.values()) / len(score)
    return score

# ================================
# 雷达图可视化
# ================================
def plot_radar(scores):
    categories = list(scores.keys())[:-1]  # 去掉综合
    values = [scores[k] for k in categories]

    fig = go.Figure(
        data=[
            go.Scatterpolar(
                r=values + [values[0]],
                theta=categories + [categories[0]],
                fill='toself'
            )
        ]
    )
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        showlegend=False
    )
    return fig

# ================================
# DeepSeek · 人性材质学 专家报告生成
# ================================
def deepseek_summary(resume, jd):
    prompt = f"""
你是一位山川咨询认证的“人性材质学”资深 HR 顾问，擅长从突出性能力、能力持续性、潜在阻碍因素、班子适应度及企业生态匹配角度分析候选人。

请基于以下简历内容与 JD，输出人性材质学专业分析报告，包含：

【1️⃣ 核心能力突出性】  
分析候选人是否具备可见的突出能力点，是否具备稀缺或高产出能力。

【2️⃣ 能力持续性与稳定性】  
分析候选人过往能力是否持续，是否有波动或不稳定迹象。

【3️⃣ 可能的阻碍因子预测】  
指出是否存在潜在破坏性行为、跳槽风险、组织适应性障碍等。

【4️⃣ 岗位匹配度】  
给出匹配度（百分比）与理由。

【5️⃣ 班子适应度】  
分析与现有核心团队的适配性，包括性格、沟通风格是否协调。

【6️⃣ 企业生态适应度】  
分析候选人是否适应公司当前阶段与文化。

【7️⃣ 推荐工资区间】  
结合能力及市场，给出年薪或月薪范围及理由。

【8️⃣ 人才画像】  
用 5~7 句话总结候选人核心标签、性格、行为风格、发展潜力。

【9️⃣ 结论与建议】  
是否推荐录用、是否需面谈验证哪些重点、如不匹配推荐可转岗方向。

请用中文输出，层次分明，内容专业，避免口水话，保持山川咨询一贯风格。

---
【简历内容】
{resume[:2000]}

---
【JD】
{jd}

请开始生成完整分析报告：
"""
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content

# ================================
# 主执行流程
# ================================
if uploaded_file:
    ext = uploaded_file.name.split(".")[-1].lower()
    resume_text = extract_text(uploaded_file, ext)
    st.success(f"✅ 简历已解析，约 {len(resume_text)} 字")

    # 本地评分
    scores = local_multi_score_human_material(resume_text)
    st.subheader("📊 多维度评分")
    st.write(scores)

    radar = plot_radar(scores)
    st.plotly_chart(radar, use_container_width=True)

    st.subheader("🎯 综合匹配指数")
    st.metric("总分", f"{scores['综合匹配指数']:.1f}")

    if st.button("🔍 候选人报告"):
        if not job_desc.strip():
            st.warning("⚠️ 请先输入 JD！")
        else:
            with st.spinner("DeepSeek 正在生成报告..."):
                result = deepseek_summary(resume_text, job_desc)
                st.subheader("🤖 DeepSeek 候选人报告")
                st.info(result)