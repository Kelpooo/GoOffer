# 面试题抽取脚本

这个脚本会做 4 件事：

1. 抓取公开文章网页，或读取本地文本
2. 提取相对干净的正文
3. 调用 DeepSeek 生成结构化前端题库 JSON
4. 自动把结果保存到本地文件

当前版本的抽题 Prompt 已调整为“高召回”策略：

- 尽量多抽题
- 尽量拆细粒度知识点
- 允许后续去重，不优先做摘要式合并

## 1. 准备 API Key

PowerShell:

```powershell
$env:DEEPSEEK_API_KEY="你的_API_Key"
```

## 2. 直接抓网页并落盘

```powershell
python .\extract_questions.py `
  --url "https://www.cnblogs.com/ypSharing/p/19991915" `
  --title "2026 前端面试八股文〖超全完整版〗" `
  --output ".\frontend_questions.json" `
  --raw-output ".\frontend_questions_raw.txt"
```

如果文章站点会拦普通请求（例如部分掘金、CSDN 页面），可以强制用浏览器模式：

```powershell
python .\extract_questions.py `
  --url "https://juejin.cn/post/7613211639155949568" `
  --title "掘金文章" `
  --fetch-mode browser `
  --output ".\juejin_questions.json" `
  --raw-output ".\juejin_questions_raw.txt"
```

默认 `--fetch-mode auto` 会先走普通请求，遇到常见拦截页面后自动回退到浏览器抓取。

成功后会输出一段简短 JSON，里面有：

- `question_count`
- `output`
- `raw_output`

## 3. 用本地文本文件跑

```powershell
python .\extract_questions.py `
  --input-file ".\article.txt" `
  --title "前端八股样本" `
  --output ".\frontend_questions.json"
```

## 4. 常用参数

- `--model`：默认 `deepseek-v4-flash`
- `--fetch-mode`：`auto` / `http` / `browser`
- `--base-url`：默认 `https://api.deepseek.com/chat/completions`
- `--max-chars`：默认 `50000`
- `--temperature`：默认 `0.1`

## 5. 浏览器模式说明

如果你第一次用 `--fetch-mode browser`，可能需要先安装 Chromium：

```powershell
playwright install chromium
```

## 6. 当前脚本定位

这是一版最小可用脚本，适合你先把流程跑通：

- `公开链接 -> 正文 -> 大模型抽题 -> JSON 文件`

后面你可以继续加：

- 批量 URL 输入
- 去重归一
- 多板块抽取
- 审核状态字段
- 数据库入库
