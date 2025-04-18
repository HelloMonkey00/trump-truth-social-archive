# Trump Truth Social Archive

一个自动抓取和分析特朗普在Truth Social上发布内容的工具。该项目可以定期爬取Truth Social上的特朗普账号发布的内容，并通过人工智能进行分析，包括金融市场影响分析、主题提取以及生成摘要。

## 功能特点

- 自动抓取Truth Social上特朗普发布的内容
- 对新发布的内容进行金融市场影响分析
- 分析文本内容与股票市场、行业、公司股价或汇率的关系
- 自动提取帖子中的主题关键词
- 生成中文摘要
- 通过飞书机器人自动推送分析结果
- 支持周期性运行，持续监控更新
- 支持自定义AI提示词

## 环境要求

- Python 3.8 或更高版本
- Deepseek API 密钥（用于AI分析）
- 飞书机器人 Webhook URL（用于通知，可选）

## 安装

1. 克隆此仓库:
   ```
   git clone https://github.com/yourusername/trump-truth-social-archive.git
   cd trump-truth-social-archive
   ```

2. 安装依赖:
   ```
   pip install -r requirements.txt
   ```

3. 设置环境变量:
   ```
   export DEEPSEEK_API_KEY="your_deepseek_api_key_here"
   export LARK_WEBHOOK_URL="your_lark_webhook_url_here" # 可选
   ```

## 使用方法

该项目提供了多种运行模式，可以通过命令行参数进行控制：

### 1. 仅抓取数据

```
python run.py scrape [--pages N]
```

参数:
- `--pages`: 指定最大抓取页数，默认为3页

### 2. 仅分析数据

```
python run.py analyze [--limit N]
```

参数:
- `--limit`: 指定最大分析帖子数，默认为5条

### 3. 执行完整周期（抓取+分析）

```
python run.py cycle [--pages N] [--limit M] [--delay S]
```

参数:
- `--pages`: 指定最大抓取页数，默认为3页
- `--limit`: 指定最大分析帖子数，默认为5条
- `--delay`: 抓取和分析之间的延迟时间(秒)，默认为0秒

### 4. 持续运行模式

```
python run.py continuous [--pages N] [--limit M] [--interval S]
```

参数:
- `--pages`: 指定最大抓取页数，默认为3页
- `--limit`: 指定最大分析帖子数，默认为5条
- `--interval`: 每次运行周期之间的间隔时间(秒)，默认为3600秒(1小时)

## 自定义提示词

可以通过编辑 `config/prompts.json` 文件来自定义AI分析提示词。该文件包含以下配置项：

- `market_impact`: 用于分析帖子内容与金融市场关系的提示词
- `extract_topics`: 用于提取帖子主题的提示词
- `summarize_post`: 用于生成摘要的提示词

修改这些提示词可以调整AI分析的侧重点和输出效果。

## 项目结构

```
trump-truth-social-archive/
│
├── run.py              # 主运行脚本
├── scrape.py           # 爬虫脚本
├── analyze_posts.py    # AI分析脚本
├── config/             # 配置文件目录
│   └── prompts.json    # AI提示词配置
├── data/               # 存储抓取的数据
│   ├── posts.json      # 帖子原始数据
│   └── analysis/       # 分析结果数据
│       └── results.json
│
└── logs/               # 日志文件
    ├── scrape.log
    └── analysis.log
```

## 注意事项

- 该项目需要Deepseek API密钥才能进行AI分析
- 请确保遵守Truth Social的服务条款和robots.txt政策
- 大量请求可能会导致IP被临时封禁
- Deepseek API调用会产生费用，请注意控制使用量

## 许可证

此项目遵循MIT许可证 - 详细内容请查看LICENSE文件