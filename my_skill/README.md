# My Skill

这是一个面向微信聊天分析的本地原型项目。

当前先提供一个最小可用能力：

- 从当前打开的微信聊天窗口实验性批量采集可见聊天文本

## 快速开始

先打开微信并进入目标联系人的聊天窗口，然后把焦点点到聊天记录区域，再运行：

```powershell
python -m my_skill.app.cli collect-wechat-window --output ".\my_skill\data\visible_chat.txt"
```

建议第一次先小范围测试：

```powershell
python -m my_skill.app.cli collect-wechat-window --output ".\my_skill\data\visible_chat.txt" --rounds 3 --delay 3.5
```

## 工作方式

脚本会：

1. 倒计时，给你切回微信的时间
2. 模拟 `Ctrl+A` 与 `Ctrl+C`
3. 读取剪贴板文本
4. 模拟 `PageUp` 向上翻历史
5. 自动去重并保存结果

## 注意

- 这是实验版，依赖当前微信窗口支持复制可见聊天内容
- 运行期间尽量不要碰鼠标和键盘
- 如果当前微信版本对聊天区复制支持不好，结果会不稳定
- 脚本会同时保存一份原始片段文件，方便后续清洗
