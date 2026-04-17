# ChatBI - 对话式数据分析平台
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](http://159.75.111.169:8501)  
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

## 简介
ChatBI 是一个基于大模型（智谱 GLM-4-Flash）的自然语言查询系统，能够将业务问题自动转换为 SQL，并返回数据表格和图表。支持多种图表类型（柱状图、折线图、饼图），并具备缓存、只读数据库、密码保护等生产级特性。

## 界面预览

![ChatBI 主界面](./images/chatbi-demo.png)

## 功能特点
- 🔍 **自然语言转 SQL**：用户用中文提问，自动生成可执行的 SQL 语句。
- 📊 **自动图表生成**：根据数据特征和用户意图，自动选择柱状图、折线图或饼图。
- 🗃️ **特殊字段支持**：正确处理包含连字符、斜杠的字段名（如 `sub-category`）。
- ⚡ **缓存机制**：相同问题 1 小时内直接返回结果，节省 API 调用。
- 🔒 **安全加固**：数据库只读模式，防止误操作；可选密码认证。
- 🐳 **容器化部署**：提供 Dockerfile，一键启动。
- ⚙️ **系统服务**：支持 systemd，开机自启，异常自动重启。

## 适用场景对比

| 维度 | 传统提数流程 (提需求 → 排期 → 写SQL → 取数) | ChatBI (自然语言即时取数) |
|------|-----------------------------------------------|--------------------------|
| 响应速度 | 小时级 ~ 天级 | 秒级 |
| 使用门槛 | 需要懂 SQL | 业务人员直接提问 |
| 迭代成本 | 改需求需重新走流程 | 追问即可修改条件 |

## 技术栈
- **Python 3.10**
- **Streamlit** – 快速构建 Web 界面
- **OpenAI API**（兼容智谱 GLM-4-Flash）
- **SQLite** – 轻量级数据库
- **Matplotlib / Seaborn** – 数据可视化

## 项目结构
```
chatbi_project/
├── common/ # 通用模块
│ ├── llm_client.py
│ ├── sql_executor.py
│ ├── visualizer.py
│ └── error_handler.py
├── tests/ # 测试脚本
│ ├── test_core.py
│ └── test_visualize.py
├── logs/ # 日志目录（自动生成）
├── charts/ # 图表输出目录（自动生成）
├── app.py
├── chatbi_core.py
├── schema_info.txt
├── prompt_template.txt
├── prepare_data.py
├── requirements.txt
├── .env.example
├── Dockerfile
├── chatbi.service.example
├── .gitignore
├── README.md
└── LICENSE
```

## 快速开始

### 环境要求
- Python 3.10+
- 智谱 AI API Key（[免费申请](https://open.bigmodel.cn/)）

### 安装步骤

1. **克隆仓库**
   ```bash
   git clone https://github.com/kinao-python/chatbi-project.git
   cd chatbi-project
   ```

2. **创建虚拟环境并安装依赖**
   ```bash
   python3 -m venv chatbi_env
   source chatbi_env/bin/activate
   pip install -r requirements.txt
   ```

3. **配置 API Key**
   ```bash
   cp .env.example .env
   # 编辑 .env 文件，填入你的智谱 API Key
   nano .env
   ```

4. **准备数据**  
   执行以下脚本自动下载 Superstore 数据集并导入 SQLite（约 3MB）：
   ```bash
   python prepare_data.py
   ```
   确保 `superstore.db` 文件出现在项目根目录。

5. **运行应用**
   ```bash
   streamlit run app.py --server.port 8501 --server.address 0.0.0.0
   ```
   访问 `http://localhost:8501` 或 `http://你的服务器IP:8501`。

### Docker 部署
```bash
# 构建镜像
docker build -t chatbi .

# 运行容器（挂载数据库文件和环境变量）
docker run -d -p 8501:8501 \
  -v $(pwd)/superstore.db:/app/superstore.db \
  -v $(pwd)/.env:/app/.env \
  --name chatbi chatbi
```

### systemd 服务（Linux）
1. 将 `chatbi.service.example` 复制为 `/etc/systemd/system/chatbi.service` 并修改路径。
2. 重新加载 systemd：`sudo systemctl daemon-reload`
3. 启动服务并设置开机自启：
   ```bash
   sudo systemctl enable chatbi
   sudo systemctl start chatbi
   ```
4. 查看状态：`sudo systemctl status chatbi`


## 效果评估

基于 **20 条** 典型业务查询测试集（涵盖聚合、过滤、排序、时间函数、分组、计算列等），当前版本评估结果如下：

| 指标 | 数值 |
|------|------|
| ✅ **可执行成功率**（SQL 能跑通且有数据） | **80%** (16/20) |
| 平均响应时间 | 1.86 秒 |
| SQL 精确匹配率（仅供参考） | 5% (1/20) |

> **可执行成功率是核心指标**，反映模型对业务逻辑的理解是否正确。精确匹配率较低（仅5%）是因为 LLM 生成的 SQL 在别名、空格、大小写、函数写法（如 `SUM(sales)` vs `sum(sales) as total_sales`）上与标准答案存在差异，但这些差异不影响查询结果的正确性。评估脚本和测试集位于 `evaluation/` 目录，可自行复现。

## 常见问题

### 1. API 调用失败，提示余额不足或认证错误
- 检查 `.env` 中的 API Key 是否正确。
- 确认智谱账户有足够余额（免费额度通常够用）。

### 2. 生成的 SQL 执行失败或返回空结果
- 查看日志文件 `chatbi.log` 中的错误信息。
- 检查 `schema_info.txt` 是否与实际数据库字段一致。
- 尝试修改 `prompt_template.txt`，增加更明确的字段说明。

### 3. 图表未生成
- 确认问题中包含“画图”、“柱状图”、“折线图”、“饼图”等关键词。
- 检查查询结果数据格式是否适合绘制图表（如柱状图需要两列，一列类别一列数值）。
- 查看 `charts/` 目录是否有图片生成。

### 4. 服务无法访问（外部）
- 确保服务器防火墙开放了 8501 端口。
- 如果在云服务器上，检查安全组规则。

## 贡献
欢迎提交 Issue 和 Pull Request。详细请参阅 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 许可证
本项目采用 MIT 许可证，详见 [LICENSE](LICENSE) 文件。

## 联系方式
- 作者：kinao-python
- GitHub：[https://github.com/kinao-python/chatbi-project](https://github.com/kinao-python/chatbi-project)
