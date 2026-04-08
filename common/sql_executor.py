# common/sql_executor.py
import sqlite3
import pandas as pd
import logging
import os

logger = logging.getLogger(__name__)

class SQLExecutor:
    """封装 SQLite 数据库操作，支持只读模式"""
    def __init__(self, db_path: str, readonly: bool = True):
        """
        参数:
            db_path: 数据库文件路径（绝对或相对）
            readonly: 是否以只读模式打开（默认 True，防止修改）
        """
        self.db_path = db_path
        self.readonly = readonly

    def execute(self, sql: str):
        """
        执行 SQL 查询，返回 (df, error)
        成功时 df 为 DataFrame，error 为 None
        失败时 df 为 None，error 为错误信息字符串
        """
        try:
            # 检查数据库文件是否存在
            if not os.path.exists(self.db_path):
                raise FileNotFoundError(f"数据库文件不存在: {self.db_path}")

            # 只读模式：使用 URI 参数 ?mode=ro
            if self.readonly:
                uri = f"file:{self.db_path}?mode=ro"
                conn = sqlite3.connect(uri, uri=True)
                # 额外确保只读（PRAGMA query_only）
                conn.execute("PRAGMA query_only = 1")
            else:
                conn = sqlite3.connect(self.db_path)

            df = pd.read_sql_query(sql, conn)
            conn.close()
            logger.info(f"SQL 执行成功，返回 {len(df)} 行")
            return df, None

        except Exception as e:
            logger.error(f"SQL 执行失败: {e}\nSQL: {sql}")
            return None, str(e)
