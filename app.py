# app.py
import streamlit as st
from chatbi_core import ask_question
import pandas as pd

# 页面配置
st.set_page_config(page_title="ChatBI - 对话式数据分析", page_icon="📊", layout="wide")
# 简单密码认证
if "authenticated" not in st.session_state:
    password = st.sidebar.text_input("请输入访问密码", type="password")
    if password == st.secrets["ACCESS_PASSWORD"]:
        st.session_state.authenticated = True
    else:
        st.sidebar.error("密码错误")
        st.stop()

# 标题
st.title("📊 ChatBI - 对话式数据分析平台")
st.markdown("输入自然语言问题，系统将自动生成 SQL 并返回查询结果及图表。")

# 初始化会话状态
if "messages" not in st.session_state:
    st.session_state.messages = []  # 每条消息格式: {"role": "user/assistant", "content": str, "result": dict}

# --------------------- 辅助函数：处理问题 ---------------------
def process_question(question: str, visualize: bool = True):
    """
    处理用户问题，将结果存入 session_state，然后刷新页面显示。
    """
    # 1. 添加用户消息
    st.session_state.messages.append({"role": "user", "content": question})

    # 2. 调用核心函数
    with st.spinner("正在思考..."):
        result = ask_question(question, visualize=visualize)

    # 3. 构建助手消息（友好化错误）
    if result['error']:
        error_msg = result['error']
        # 判断是否为 SQL 语法错误（常见于非查询输入）
        if "syntax error" in error_msg.lower() or "near" in error_msg.lower():
            assistant_content = "❓ 您的问题似乎不是数据查询。请尝试问一些关于销售额、利润、地区、品类等数据相关的问题。"
        else:
            assistant_content = f"❌ 查询失败：{error_msg}"
        # 注意：此时 result 中可能包含不完整的 data，但我们在历史中不会展示数据表格，所以无需额外处理
    else:
        df = result['data']
        if df.empty:
            assistant_content = "⚠️ 查询成功，但没有匹配的数据。请检查条件或换一个问法。"
        else:
            assistant_content = f"查询完成，共 {len(df)} 行"
            # 其他数据展示将在历史消息循环中根据 result 渲染

    # 将助手消息存入（附带完整 result，用于后续展示数据）
    st.session_state.messages.append({
        "role": "assistant",
        "content": assistant_content,
        "result": result   # 保存完整 result，包含 sql, data, chart_path
    })

# --------------------- 侧边栏 ---------------------
with st.sidebar:
    st.markdown("### 工具")
    if st.button("清空对话历史", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# --------------------- 示例问题按钮 ---------------------
st.markdown("### 试试这些问题：")
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("📊 各地区销售额（柱状图）", use_container_width=True):
        process_question("各个地区的总销售额是多少？画柱状图")
        st.rerun()
with col2:
    if st.button("📈 销售额趋势（折线图）", use_container_width=True):
        process_question("2023年各月销售额趋势，画折线图")
        st.rerun()
with col3:
    if st.button("💰 科技品类利润分析", use_container_width=True):
        process_question("科技品类的平均利润和平均利润率是多少？")
        st.rerun()

# --------------------- 显示历史消息 ---------------------
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        # 如果是助手消息且包含 result，且 result 无错误且有数据，则展示详细信息
        if msg["role"] == "assistant" and "result" in msg:
            result = msg["result"]
            if not result.get('error') and result.get('data') is not None:
                df = result['data']
                if not df.empty:
                    # 单行单列直接显示数值
                    if df.shape == (1, 1):
                        value = df.iloc[0, 0]
                        st.success(f"结果：{value}")
                    else:
                        st.write(f"共 {len(df)} 行")
                        st.dataframe(df, use_container_width=True, height=400)
                    # 显示 SQL（可折叠）
                    with st.expander("查看生成的 SQL"):
                        st.code(result['sql'], language='sql')
                    # 显示图表
                    if result.get('chart_path'):
                        st.image(result['chart_path'])

# --------------------- 聊天输入框 ---------------------
if prompt := st.chat_input("请输入您的问题..."):
    process_question(prompt)
    st.rerun()
