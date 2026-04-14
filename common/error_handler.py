# common/error_handler.py
import logging

logger = logging.getLogger(__name__)

def classify_error(error_msg: str) -> str:
    """
    将原始错误消息转换为用户友好的中文提示。
    参数:
        error_msg: 原始错误字符串（来自 LLM、数据库或代码异常）
    返回:
        友好的提示字符串
    """
    if not error_msg:
        return "未知错误"

    error_lower = error_msg.lower()

    # 1. SQL 语法错误（通常由 LLM 生成非 SQL 或错误 SQL 导致）
    if "syntax error" in error_lower or "near" in error_lower:
        return "❓ 您的问题似乎不是数据查询。请尝试问一些关于销售额、利润、地区、品类等数据相关的问题。"

    # 2. 表不存在
    if "no such table" in error_lower:
        return "❓ 查询涉及的数据表不存在，请检查您的提问是否与销售数据相关。"

    # 3. 列不存在
    if "no such column" in error_lower:
        return "❓ 查询中使用了不存在的字段，请尝试换一种问法或检查字段名。"

    # 4. 数据库文件不存在
    if "database file does not exist" in error_lower or "no such file" in error_lower:
        return "❌ 系统错误：数据库文件缺失，请联系管理员。"

    # 5. 只读模式违规（尝试修改数据）
    if "attempt to write a readonly database" in error_lower:
        return "⚠️ 系统仅支持查询操作，不能修改数据。"

    # 6. 来自 LLM 模块的自定义错误（已比较友好）
    if "生成的内容不是有效的 SQL" in error_msg:
        return error_msg  # 保持原样

    # 7. 其他未分类的错误
    logger.warning(f"未分类的错误: {error_msg}")
    return f"❌ 查询失败：{error_msg}"
