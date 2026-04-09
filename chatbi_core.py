import os
import re
import copy
import time
import logging
from typing import Dict, Optional, Any
from common.llm_client import LLMClient
from common.sql_executor import SQLExecutor
from common.visualizer import Visualizer
import pandas as pd
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
viz = Visualizer(output_dir='charts', max_title_length=50) #初始化模块
llm_client = LLMClient() # 初始化llm_client
CACHE = {}
CACHE_TTL = 3600  # 缓存有效期1小时
DB_PATH = '/root/chatbi_project/superstore.db'  # 数据库路径(绝对路径)
DANGER_SQL_KEYWORDS = ['DROP', 'ALTER', 'DELETE', 'INSERT', 'UPDATE', 'CREATE']  # 危险SQL关键词

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
            chart_path = viz.plot(df, question)
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
