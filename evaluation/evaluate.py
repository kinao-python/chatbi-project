import sys
import os
import json
import time

# 将项目根目录添加到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from chatbi_core import ask_question

def normalize_sql(sql):
    """标准化SQL：去除多余空格、换行，转小写，便于比较（仅用于内部参考）"""
    if not sql:
        return ""
    return ' '.join(sql.lower().split())

def evaluate():
    # 加载测试用例
    with open('test_queries.json', 'r', encoding='utf-8') as f:
        tests = json.load(f)

    total = len(tests)
    exact_match = 0      # 精确匹配（仅供参考）
    exec_success = 0     # 可执行成功率（核心指标）
    total_time = 0.0

    print(f"开始评估，共 {total} 个测试用例...\n")

    for i, test in enumerate(tests, 1):
        question = test['question']
        expected_sql = test['sql']
        print(f"[{i}/{total}] 问题: {question}")

        start = time.time()
        res = ask_question(question, visualize=False)
        elapsed = time.time() - start
        total_time += elapsed

        generated_sql = res['sql'] if res['sql'] else ""

        # 精确匹配（仅供参考，不对外强调）
        if normalize_sql(generated_sql) == normalize_sql(expected_sql):
            exact_match += 1
            print(f"  SQL 精确匹配")
        else:
            # 可选：打印差异（避免过长，只打印前80字符）
            print(f"  SQL 不匹配 (生成: {generated_sql[:80]}...)")

        # 执行成功率：无错误且有数据
        if res['error']:
            print(f"  ❌ 执行失败: {res['error']}")
        else:
            if res['data'] is not None and not res['data'].empty:
                exec_success += 1
                print(f"  ✅ 执行成功，返回 {len(res['data'])} 行")
            else:
                print(f"  ⚠️ 执行成功但返回空数据")

        print(f"  耗时: {elapsed:.2f} 秒\n")

    # 输出统计结果
    print("=" * 50)
    print(f"评估结果 (共 {total} 条):")
    print(f"  SQL 精确匹配率: {exact_match/total*100:.1f}% ({exact_match}/{total})  (仅供参考)")
    print(f"  ✅ 可执行成功率: {exec_success/total*100:.1f}% ({exec_success}/{total})  (核心指标)")
    print(f"  平均耗时: {total_time/total:.2f} 秒")
    print("=" * 50)

if __name__ == "__main__":
    evaluate()
