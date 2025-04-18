# 金融市场分析功能测试指南

本文档介绍如何测试Trump Truth Social帖子的金融市场影响分析功能。

## 测试方法

有两种方法可以测试市场分析功能：

1. 直接在本地运行测试脚本
2. 通过Docker容器运行测试脚本

## 准备工作

无论使用哪种方法，都需要设置以下环境变量：

```bash
# 设置DeepSeek API密钥（必需）
export DEEPSEEK_API_KEY=your_deepseek_api_key

# 设置飞书Webhook URL（可选，但推荐，否则无法收到通知）
export LARK_WEBHOOK_URL=your_lark_webhook_url
```

## 方法一：直接运行测试脚本

```bash
# 基本用法 - 分析过去30天的最多10条帖子
./test_market_analysis.py --days 30 --limit 10

# 分析过去7天的所有帖子
./test_market_analysis.py --days 7

# 强制重新分析所有帖子（即使之前已分析过）
./test_market_analysis.py --force

# 指定自定义帖子数据文件
./test_market_analysis.py --file ./path/to/your/posts.json
```

## 方法二：通过Docker容器运行测试脚本

我们提供了一个便捷的脚本，可以在Docker容器中运行测试，无需在本地安装Python依赖：

```bash
# 基本用法 - 分析过去30天的最多10条帖子
./run_test_in_docker.sh

# 分析过去7天的最多5条帖子
./run_test_in_docker.sh --days 7 --limit 5

# 强制重新分析所有帖子
./run_test_in_docker.sh --force
```

## 查看结果

1. 程序运行时会实时输出分析进度和结果
2. 如果设置了`LARK_WEBHOOK_URL`，分析结果会发送到飞书频道
3. 分析结果也会保存在`./data/analysis/analysis_results.json`文件中

## 提示词自定义

如果你想自定义AI分析的提示词，可以编辑`./config/prompts.json`文件。该文件包含三种提示词：

1. `market_impact`: 分析帖子内容与金融市场的关系
2. `extract_topics`: 提取帖子的主题关键词
3. `summarize_post`: 生成帖子内容摘要

修改这些提示词可以调整AI分析的重点和输出格式。

## 常见问题

1. **Q: 为什么测试脚本报错说找不到analyze_posts模块？**  
   A: 确保分析模块文件analyze_posts.py存在于项目根目录，且已正确配置好依赖。

2. **Q: 为什么分析结果没有发送到飞书？**  
   A: 检查是否正确设置了LARK_WEBHOOK_URL环境变量，以及飞书机器人是否配置正确。

3. **Q: 如何知道分析是否成功？**  
   A: 脚本会显示成功分析的帖子数量，并在分析完成后输出"测试完成"。

4. **Q: API调用次数过多怎么办？**  
   A: 使用`--limit`参数限制分析的帖子数量，以控制API调用次数。

5. **Q: 如何查看已分析过的帖子？**  
   A: 查看`./data/analysis/analysis_results.json`文件，其中包含所有已分析帖子的结果。 