import os
import re
import copy
import time
import logging
from typing import Dict, Optional, Any
from common.llm_client import LLMClient
from common.sql_executor import SQLExecutor
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from dotenv import load_dotenv

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='chatbi.log',
    filemode='a'
)
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

# 读取表结构和 Prompt 模板（在模块加载时读取一次）
with open('schema_info.txt', 'r', encoding='utf-8') as f:
    SCHEMA = f.read()

with open('prompt_template.txt', 'r', encoding='utf-8') as f:
    PROMPT_TEMPLATE = f.read()

SYSTEM_PROMPT = PROMPT_TEMPLATE.format(schema=SCHEMA)
# 获取当前文件所在目录，构建数据库绝对路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'superstore.db')
executor = SQLExecutor(db_path=DB_PATH, readonly=True)

llm_client = LLMClient() # 初始化llm_client
CACHE = {}
CACHE_TTL = 3600  # 缓存有效期1小时
MAX_TITLE_LENGTH = 50  # 图表标题最大长度
DB_PATH = '/root/chatbi_project/superstore.db'  # 数据库路径(绝对路径)
DANGER_SQL_KEYWORDS = ['DROP', 'ALTER', 'DELETE', 'INSERT', 'UPDATE', 'CREATE']  # 危险SQL关键词

def auto_plot(df: pd.DataFrame, question: str, output_dir: str = 'charts', filename: Optional[str] = None) -> Optional[str]:
    """
    根据 DataFrame 和用户问题自动生成图表并保存。
    """
    # 1. 检查数据有效性
    if df is None or df.empty or df.dropna(how='all').empty:
        return None

    # 2. 判断是否需要生成图表（关键词匹配）
    chart_keywords = ['画图', '图表', '可视化', '趋势', '对比', '柱状图', '折线图', '饼图']
    if not any(kw in question for kw in chart_keywords):
        return None

    # 3. 初始化配置（解决中文显示）
    plt.rcParams['font.sans-serif'] = ['SimHei']
    plt.rcParams['axes.unicode_minus'] = False

    # 4. 创建保存目录
    os.makedirs(output_dir, exist_ok=True)

    # 5. 生成唯一文件名
    if filename is None:
        filename = f"chart_{int(time.time())}.png"
    save_path = os.path.join(output_dir, filename)

    try:
        # ========== 优先处理饼图（用户明确要求） ==========
        if '饼图' in question:
            # 情况1：数据有两列，且第二列为数值 → 直接用第一列作标签，第二列作数值
            if df.shape[1] == 2 and df.dtypes.iloc[1] in ['int64', 'float64']:
                plt.figure(figsize=(8, 8))
                plt.pie(df.iloc[:, 1], labels=df.iloc[:, 0], autopct='%1.1f%%')
                plt.title(question[:MAX_TITLE_LENGTH])
                plt.tight_layout()
                plt.savefig(save_path)
                return save_path
            # 情况2：数据包含百分比列（列名含"percent"或"比例"）
            percent_col = None
            for col in df.columns:
                if 'percent' in col.lower() or '比例' in col:
                    percent_col = col
                    break
            if percent_col:
                # 取第一列作为标签
                label_col = df.columns[0]
                plt.figure(figsize=(8, 8))
                plt.pie(df[percent_col], labels=df[label_col], autopct='%1.1f%%')
                plt.title(question[:MAX_TITLE_LENGTH])
                plt.tight_layout()
                plt.savefig(save_path)
                return save_path

        # ========== 柱状图 ==========
        if df.shape[1] == 2 and df.dtypes.iloc[1] in ['int64', 'float64']:
            plt.figure(figsize=(10, 6))
            sns.barplot(x=df.columns[0], y=df.columns[1], data=df)
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.savefig(save_path)
            return save_path

        # ========== 折线图（含日期列） ==========
        date_cols = df.select_dtypes(include=['datetime64']).columns
        if len(date_cols) > 0:
            plt.figure(figsize=(12, 6))
            for col in df.columns:
                if col != date_cols[0] and df[col].dtype in ['int64', 'float64']:
                    plt.plot(df[date_cols[0]], df[col], marker='o', label=col)
            plt.legend()
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.savefig(save_path)
            return save_path

        # 未匹配任何规则，不生成图表
        return None
    finally:
        plt.close('all')  # 强制关闭所有图表，释放内存

def ask_question(question: str, visualize: bool = False) -> Dict[str, Any]:
    """
    输入自然语言问题，返回查询结果字典。
    """
    start_time = time.time()
    result = {
        'sql': None,
        'data': None,
        'error': None,
        'chart_path': None
    }

    # 检查缓存
    if question in CACHE:
        cached_result, cached_time = CACHE[question]
        if time.time() - cached_time < CACHE_TTL:
            logger.info(f"使用缓存结果: {question}")
            return cached_result
        else:
            del CACHE[question]
            logger.info(f"缓存已过期: {question}")

    try:
        logger.info(f"处理问题: {question}")
        # 调用 LLM 生成 SQL
        sql, error = llm_client.generate_sql(SYSTEM_PROMPT, question)
        if error:
            result['error'] = error
            return result

        # 安全过滤：禁止危险SQL
        if any(keyword in sql.upper() for keyword in DANGER_SQL_KEYWORDS):
            result['error'] = "禁止执行修改/删除类SQL操作"
            logger.warning(f"危险SQL: {sql}")
            return result

        result['sql'] = sql
        logger.info(f"生成的SQL: {sql}")

        # 执行 SQL 查询
        df, error = executor.execute(sql)
        if error:
            result['error'] = error
        else:
            result['data'] = df
            logger.info(f"查询成功，返回 {len(df)} 行")

        # 生成可视化图表
        if visualize:
            chart_path = auto_plot(df, question)
            result['chart_path'] = chart_path

    except Exception as e:
        result['error'] = str(e)
        logger.error(f"处理失败: {e}")

    # 存储缓存（深拷贝避免数据污染）
    CACHE[question] = (copy.deepcopy(result), time.time())

    # 记录耗时
    elapsed = time.time() - start_time
    logger.info(f"总耗时：{elapsed:.2f}秒")

    return result

if __name__ == "__main__":
    test_q = "各个地区的总销售额是多少？"
    res = ask_question(test_q, visualize=True)
    print(f"SQL: {res['sql']}")
    if res['error']:
        print(f"错误: {res['error']}")
    else:
        print(res['data'].head())
        if res['chart_path']:
            print(f"图表保存路径: {res['chart_path']}")
