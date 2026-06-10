# 面试宝典网页 MVP

## 启动方式

先生成题库数据：

```powershell
python .\build_mvp_data.py
```

如果要使用题库、招聘导航、简历评审、简历改写、模拟面试题生成，请直接启动本地服务：

```powershell
python .\resume_review_server.py
```

然后打开：

- `http://127.0.0.1:8000/web_mvp/`

如果 8000 端口被占用：

```powershell
$env:RESUME_REVIEW_PORT="8011"
python .\resume_review_server.py
```

## 简历评审模型

- 默认优先读取环境变量 `DEEPSEEK_API_KEY`
- 如果配置了，就调用 DeepSeek 接口
- 当前默认模型：`deepseek-chat`
- 也可以通过环境变量覆盖：

```powershell
$env:DEEPSEEK_MODEL="deepseek-chat"
```

如果没有配置 API Key，也可以用：

- 会自动退回到本地规则评审
- 仍然能做关键词提取、岗位匹配、改写建议、模拟面试题生成
- 但效果会明显弱于大模型版本

## Prompt 模板

提示词已经独立抽出来了：

- `prompt_templates.json`

里面分成了三块：

- `review_*`：简历评审
- `rewrite_*`：生成修改版简历建议
- `interview_*`：生成基于简历的模拟面试题

后面你想改输出风格、加维度、调整面试题偏向，优先改这个文件就行。

## 当前支持

- 前端 / 后端题库切换
- 分类筛选、搜索、随机题、题目详情
- 上一题 / 下一题
- 收藏 / 已掌握
- 模拟面试
- 中大厂招聘入口 + JD 快照
- 上传简历
- AI / 本地规则评审简历
- 关键词提取
- 岗位匹配分析
- 生成修改版简历建议
- 生成基于简历的模拟面试题
