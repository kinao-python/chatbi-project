FROM python:3.10-slim
WORKDIR /app
COPY . /app

# 清华国内源安装依赖，解决超时问题
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
