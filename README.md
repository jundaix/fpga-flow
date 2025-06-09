# FPGA智能开发工作流程

🚀 基于LangGraph的智能FPGA开发助手，提供从需求分析到代码生成的完整开发流程。

## 项目简介

本项目是一个智能化的FPGA开发工作流程系统，集成了多个AI智能体，能够帮助开发者完成：

- 📋 **需求分析和规划** - 智能分析用户需求，制定开发计划
- 💻 **代码生成** - 自动生成高质量的Verilog代码
- 🧪 **测试台生成** - 自动创建完整的测试台代码
- 🔍 **仿真验证** - 集成仿真工具进行验证
- 🐛 **调试优化** - 智能调试和代码优化

## 功能特性

- ✨ **多智能体协作** - 基于LangGraph的智能体工作流
- 🎯 **交互式开发** - 支持命令行和Web UI两种交互方式
- 🔧 **完整工具链** - 集成Icarus Verilog仿真工具
- 📁 **项目管理** - 自动创建和管理项目文件结构
- 🎨 **现代化UI** - 基于Streamlit的美观Web界面

## 环境要求

- Python >= 3.12
- uv (Python包管理器)
- Icarus Verilog (可选，用于仿真)

## 安装指南

### 1. 安装uv

如果您还没有安装uv，请先安装：

```bash
# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. 克隆项目

```bash
git clone <your-repo-url>
cd fpga-flow
```

### 3. 创建虚拟环境并安装依赖

```bash
# 使用uv创建虚拟环境并安装依赖
uv sync
```

### 4. 配置API密钥

编辑 `conf.yaml` 文件，配置您的OpenAI API密钥：

```yaml
# FPGA多智能体系统配置文件

# 基础模型配置
BASIC_MODEL:
  base_url: https://api.openai.com/v1  # 或您的API服务地址
  model: "gpt-4"  # 或其他支持的模型
  api_key: "your-api-key-here"  # 请替换为您的API密钥
```

## 使用教程

### 方式一：命令行交互模式

使用uv运行主工作流程：

```bash
# 激活虚拟环境并运行
uv run python workflow.py
```

启动后，您将看到交互式界面：

```
============================================================
🚀 欢迎使用FPGA智能开发工作流程!
============================================================
这个工具将帮助您完成从需求分析到代码生成的完整FPGA开发流程。
您可以随时输入 'quit' 或 'exit' 退出程序。

📝 请描述您的FPGA设计需求:
   例如: '设计一个8位计数器，带使能和复位功能'
   或者: '实现一个FIFO缓冲器，深度为16，数据位宽8位'
--------------------------------------------------
💡 您的需求: 
```

### 方式二：Web UI界面

启动Streamlit Web界面：

```bash
# 运行Web界面
uv run streamlit run ui/fpga_workflow_app.py
```

然后在浏览器中打开 `http://localhost:8501` 访问Web界面。

### 使用示例

#### 示例1：创建8位计数器

```
💡 您的需求: 设计一个8位计数器，带使能和复位功能
```

系统将自动：
1. 分析需求并制定开发计划
2. 生成Verilog代码
3. 创建测试台
4. 进行仿真验证
5. 生成完整的项目文件

#### 示例2：创建FIFO缓冲器

```
💡 您的需求: 实现一个FIFO缓冲器，深度为16，数据位宽8位
```

## 项目结构

```
fpga-flow/
├── agents/                 # AI智能体定义
│   ├── __init__.py
│   └── fpga_agents.py     # FPGA开发智能体
├── config/                 # 配置模块
│   ├── __init__.py
│   ├── agents.py          # 智能体配置
│   ├── configuration.py   # 系统配置
│   └── loader.py          # 配置加载器
├── graph/                  # 工作流图定义
│   ├── __init__.py
│   ├── builder.py         # 图构建器
│   ├── nodes.py           # 节点定义
│   └── types.py           # 类型定义
├── llms/                   # 大语言模型接口
│   ├── __init__.py
│   └── llm.py             # LLM封装
├── prompts/                # 提示词模板
│   ├── __init__.py
│   ├── fpga_coder.md      # 代码生成提示词
│   ├── fpga_planner.md    # 规划提示词
│   ├── fpga_tester.md     # 测试提示词
│   ├── planner_model.py   # 规划模型
│   └── template.py        # 模板工具
├── tools/                  # 开发工具
│   ├── __init__.py
│   ├── file_operations_tool.py  # 文件操作工具
│   └── iverilog_tool.py   # Icarus Verilog工具
├── ui/                     # 用户界面
│   ├── __init__.py
│   ├── fpga_workflow_app.py      # Streamlit应用
│   ├── fpga_workflow_app_refactored.py
│   ├── ui_components.py   # UI组件
│   ├── ui_state_manager.py # 状态管理
│   └── workflow_manager.py # 工作流管理
├── utils/                  # 工具函数
│   ├── __init__.py
│   └── verilog_extractor.py # Verilog代码提取
├── workspace/              # 工作空间（生成的项目）
├── conf.yaml              # 配置文件
├── pyproject.toml         # 项目配置
├── uv.lock                # 依赖锁定文件
└── workflow.py            # 主工作流程
```

## 开发指南

### 添加新的智能体

1. 在 `agents/fpga_agents.py` 中定义新的智能体
2. 在 `prompts/` 目录下添加相应的提示词模板
3. 在 `graph/nodes.py` 中添加对应的节点
4. 更新 `graph/builder.py` 中的图构建逻辑

### 添加新的工具

1. 在 `tools/` 目录下创建新的工具模块
2. 实现工具的核心功能
3. 在智能体中注册新工具

### 自定义提示词

编辑 `prompts/` 目录下的Markdown文件来自定义智能体的行为。

## 故障排除

### 常见问题

1. **API密钥错误**
   - 检查 `conf.yaml` 中的API密钥配置
   - 确保API密钥有效且有足够的配额

2. **依赖安装失败**
   ```bash
   # 清理缓存并重新安装
   uv cache clean
   uv sync --reinstall
   ```

3. **仿真工具未找到**
   - 安装Icarus Verilog：`sudo apt-get install iverilog` (Linux)
   - 或从官网下载安装包

4. **端口占用**
   ```bash
   # 指定其他端口运行Streamlit
   uv run streamlit run ui/fpga_workflow_app.py --server.port 8502
   ```

## 贡献指南

欢迎提交Issue和Pull Request！

1. Fork本项目
2. 创建特性分支：`git checkout -b feature/amazing-feature`
3. 提交更改：`git commit -m 'Add amazing feature'`
4. 推送分支：`git push origin feature/amazing-feature`
5. 提交Pull Request

## 许可证

本项目采用MIT许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 联系方式

如有问题或建议，请通过以下方式联系：

- 提交Issue：[GitHub Issues](https://github.com/your-username/fpga-flow/issues)
- 邮箱：your-email@example.com

---

⭐ 如果这个项目对您有帮助，请给我们一个Star！