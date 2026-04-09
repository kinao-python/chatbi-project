# common/visualizer.py
import os
import time
import matplotlib.pyplot as plt
import seaborn as sns
import logging

logger = logging.getLogger(__name__)

class Visualizer:
    """自动图表生成器"""
    def __init__(self, output_dir='charts', max_title_length=50):
        self.output_dir = output_dir
        self.max_title_length = max_title_length
        os.makedirs(self.output_dir, exist_ok=True)
        # 解决中文显示问题
        plt.rcParams['font.sans-serif'] = ['SimHei']
        plt.rcParams['axes.unicode_minus'] = False

    def plot(self, df, question, filename=None):
        """
        根据 DataFrame 和用户问题自动生成图表并保存。
        参数:
            df: pandas DataFrame
            question: 用户原始问题（用于关键词判断和标题）
            filename: 可选，指定文件名
        返回:
            图片保存路径（成功）或 None（无法生成）
        """
        # 1. 检查数据有效性
        if df is None or df.empty or df.dropna(how='all').empty:
            return None

        # 2. 判断是否需要生成图表（关键词匹配）
        chart_keywords = ['画图', '图表', '可视化', '趋势', '对比', '柱状图', '折线图', '饼图']
        if not any(kw in question for kw in chart_keywords):
            return None

        # 3. 生成唯一文件名
        if filename is None:
            filename = f"chart_{int(time.time())}.png"
        save_path = os.path.join(self.output_dir, filename)

        try:
            # ========== 饼图优先 ==========
            if '饼图' in question:
                # 情况1：两列，第二列数值
                if df.shape[1] == 2 and df.dtypes.iloc[1] in ['int64', 'float64']:
                    plt.figure(figsize=(8, 8))
                    plt.pie(df.iloc[:, 1], labels=df.iloc[:, 0], autopct='%1.1f%%')
                    plt.title(question[:self.max_title_length])
                    plt.tight_layout()
                    plt.savefig(save_path)
                    return save_path
                # 情况2：包含百分比列
                percent_col = None
                for col in df.columns:
                    if 'percent' in col.lower() or '比例' in col:
                        percent_col = col
                        break
                if percent_col:
                    label_col = df.columns[0]
                    plt.figure(figsize=(8, 8))
                    plt.pie(df[percent_col], labels=df[label_col], autopct='%1.1f%%')
                    plt.title(question[:self.max_title_length])
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
            plt.close('all')  # 确保释放内存
