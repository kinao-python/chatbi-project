# app.py
import streamlit as st
from chatbi_core import ask_question, execute_sql
import pandas as pd

# 页面配置
st.set_page_config(page_title="ChatBI - 对话式数据分析", page_icon="📊", layout="wide")

# 简单密码认证（避免初始加载时直接报错）
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    password = st.sidebar.text_input("请输入访问密码", type="password")
    if password:
        if password == st.secrets["ACCESS_PASSWORD"]:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.sidebar.error("密码错误")
    else:
        st.sidebar.info("请输入密码以访问")
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

    # 2. 构建历史上下文（从已有消息中提取最近的 user-assistant 对）
    history = []
    msgs = st.session_state.messages
    # 遍历消息，提取成对的 user 和 assistant（assistant 需包含 result.sql）
    i = 0
    while i < len(msgs) - 1:
        if msgs[i]['role'] == 'user' and msgs[i+1]['role'] == 'assistant':
            user_q = msgs[i]['content']
            assistant_sql = msgs[i+1].get('result', {}).get('sql', '')
            if assistant_sql:
                history.append({'user': user_q, 'sql': assistant_sql})
            i += 2
        else:
            i += 1
    # 只保留最近3轮
    history = history[-3:]

    # 3. 调用核心函数
    with st.spinner("正在思考..."):
        result = ask_question(question, visualize=visualize, history=history)

    # 4. 构建助手消息（此时 result['error'] 已经是友好提示）
    if result['error']:
        assistant_content = result['error']   # 直接使用友好错误提示
    else:
        df = result['data']
        if df.empty:
            assistant_content = "⚠️ 查询成功，但没有匹配的数据。请检查条件或换一个问法。"
        else:
            assistant_content = f"查询完成，共 {len(df)} 行"
            # 其他数据展示将在历史消息循环中根据 result 渲染

    # 5.将助手消息存入（附带完整 result，用于后续展示数据）
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

# 在侧边栏添加 SQL 执行器（使用表单，自动清空输入框）
with st.sidebar:
    st.markdown("---")
    st.markdown("### 🛠️ SQL 执行器（高级）")
    with st.form(key="sql_executor_form"):
        sql_input = st.text_area("输入 SQL 语句", height=200)
        submitted = st.form_submit_button("执行 SQL", use_container_width=True)
        if submitted:
            if sql_input:
                with st.spinner("执行中..."):
                    result = execute_sql(sql_input, visualize=True)
                if result['error']:
                    st.error(result['error'])
                else:
                    if result.get('warning'):
                        st.warning(result['warning'])
                    st.success(f"执行成功，返回 {len(result['data'])} 行")
                    st.dataframe(result['data'], use_container_width=True)
                    if result['chart_path']:
                        st.image(result['chart_path'])
                # 表单提交后，输入框会自动清空，无需手动操作 session_state
            else:
                st.warning("请输入 SQL")

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
