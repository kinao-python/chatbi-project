import os
import copy
import time
import logging
from typing import Dict, Any
from common.llm_client import LLMClient
from common.sql_executor import SQLExecutor
from common.visualizer import Visualizer
from common.error_handler import classify_error
import pandas as pd
from dotenv import load_dotenv

# 日志配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)          # 自动创建 logs 目录
LOG_FILE = os.path.join(LOG_DIR, 'chatbi.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # 添加 %(name)s
    filename=LOG_FILE,
    filemode='a'
)
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

# 读取 schema 和 prompt
schema_path = os.path.join(BASE_DIR, 'schema_info.txt')
prompt_path = os.path.join(BASE_DIR, 'prompt_template.txt')
with open(schema_path, 'r', encoding='utf-8') as f:
    SCHEMA = f.read()
with open(prompt_path, 'r', encoding='utf-8') as f:
    PROMPT_TEMPLATE = f.read()
SYSTEM_PROMPT = PROMPT_TEMPLATE.format(schema=SCHEMA)

# 数据库路径
DB_PATH = os.path.join(BASE_DIR, 'superstore.db')

# 初始化模块
executor = SQLExecutor(db_path=DB_PATH, readonly=True)
viz = Visualizer(output_dir='charts', max_title_length=50)
llm_client = LLMClient()

# 缓存
CACHE = {}
CACHE_TTL = 3600  # 缓存有效期1小时

# 危险SQL关键词
DANGER_SQL_KEYWORDS = ['DROP', 'ALTER', 'DELETE', 'INSERT', 'UPDATE', 'CREATE']

def ask_question(question: str, visualize: bool = False, history: list = None) -> Dict[str, Any]:
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
        cached_sql, cached_error, cached_chart_path, cached_time = CACHE[question]
        if time.time() - cached_time < CACHE_TTL:
            logger.info(f"使用缓存元数据: {question}")
            # 重新构建结果，但 data 需要重新查询
            result = {
                'sql': cached_sql,
                'data': None,
                'error': cached_error,
                'chart_path': cached_chart_path
            }
            # 如果没有错误，则重新执行 SQL 获取数据
            if not cached_error:
                df, exec_error = executor.execute(cached_sql)
                if exec_error:
                    result['error'] = classify_error(exec_error)
                else:
                    result['data'] = df
                    logger.info(f"缓存命中后重新查询成功，返回 {len(df)} 行")
            # 如果缓存中已有错误，直接返回错误信息
            return result
        else:
            del CACHE[question]
            logger.info(f"缓存已过期: {question}")

    try:
        logger.info(f"处理问题: {question}")
        # 构建带历史的系统提示
        system_prompt_with_history = SYSTEM_PROMPT
        if history and len(history) > 0:
            context = "\n\n## 历史对话（仅用于理解上下文，不要重复输出历史SQL）\n"
            for turn in history[-3:]:  # 最多3轮
                context += f"用户问过: {turn['user']}\n我生成的SQL: {turn['sql']}\n\n"
            system_prompt_with_history += context
            logger.info(f"附带历史上下文，共 {len(history)} 轮")
        sql, error = llm_client.generate_sql(system_prompt_with_history, question)
        if error:
            result['error'] = classify_error(error)   # 统一友好化
            return result

        # 安全过滤：禁止危险SQL
        if any(keyword in sql.upper() for keyword in DANGER_SQL_KEYWORDS):
            error_msg = "禁止执行修改/删除类SQL操作"
            result['error'] = classify_error(error_msg)
            logger.warning(f"危险SQL: {sql}")
            return result

        result['sql'] = sql
        logger.info(f"生成的SQL: {sql}")

        # 执行 SQL 查询
        df, error = executor.execute(sql)
        if error:
            result['error'] = classify_error(error)
        else:
            result['data'] = df
            logger.info(f"查询成功，返回 {len(df)} 行")

        # 生成可视化图表
        if visualize:
            chart_path = viz.plot(df, question)
            result['chart_path'] = chart_path

    except Exception as e:
        result['error'] = classify_error(str(e))
        logger.error(f"处理失败: {e}")

    # 只缓存轻量级信息
    cache_entry = (result['sql'], result['error'], result['chart_path'], time.time())
    CACHE[question] = cache_entry

    # 记录耗时
    elapsed = time.time() - start_time
    logger.info(f"总耗时：{elapsed:.2f}秒")

    return result

def execute_sql(sql: str, visualize: bool = False) -> Dict[str, Any]:
    result = {
        'sql': sql,
        'data': None,
        'error': None,
        'chart_path': None,
        'warning': None
    }

    # 处理多条语句（分号分割）
    statements = [s.strip() for s in sql.split(';') if s.strip()]
    if len(statements) > 1:
        result['warning'] = f"检测到 {len(statements)} 条 SQL 语句，仅执行第一条。"
        sql_to_execute = statements[0]
    else:
        sql_to_execute = sql

    try:
        df, error = executor.execute(sql_to_execute)
        if error:
            result['error'] = classify_error(error)
        else:
            # ========== 处理重复列名 ==========
            if df.columns.duplicated().any():
                # 生成新列名：重复的列名后面加数字后缀
                new_cols = []
                col_count = {}
                for col in df.columns:
                    if col in col_count:
                        col_count[col] += 1
                        new_cols.append(f"{col}_{col_count[col]}")
                    else:
                        col_count[col] = 0
                        new_cols.append(col)
                df.columns = new_cols
                logger.warning(f"检测到重复列名，已自动重命名: {df.columns.tolist()}")
            # =================================
            result['data'] = df
            if visualize:
                chart_path = viz.plot(df, "用户自定义SQL")
                result['chart_path'] = chart_path
    except Exception as e:
        result['error'] = classify_error(str(e))
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
