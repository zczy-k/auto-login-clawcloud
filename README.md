# 项目已修复，可以正常运行登录

# ☁️ ClawCloud Auto-Login / 自动保活

此工作流旨在实现 **每 15 天自动登录一次 ClawCloud (爪云)** 以保持账号活跃。

为了确保自动化脚本顺利运行，**必须**满足以下两个前置条件：
1. ❌ **关闭 Passkey (通行密钥)**：避免脚本无法处理生物识别弹窗。
2. ✅ **开启 2FA (双重验证)**：配合脚本中的 PyOTP 自动生成验证码，绕过异地登录风控。

---

## 🛠️ 配置步骤

### 第一步：Fork 本项目
点击页面右上角的 **Fork** 按钮，将此仓库复制到您的 GitHub 账号下。

### 第二步：开启 GitHub 2FA 并获取密钥
脚本需要通过 2FA 密钥自动计算验证码，因此不能只扫二维码，必须获取**文本密钥**。

1. 登录 GitHub，点击右上角头像 -> **Settings**。
2. 在左侧菜单选择 **Password and authentication**。
3. 找到 "Two-factor authentication" 区域，点击 **Enable 2FA**。
4. 选择 **Set up using an app**。
5. **⚠️ 关键步骤**：
   > 页面显示二维码时，**不要直接点击 Continue**。请点击二维码下方的蓝色小字 **"Setup Key"**（或 "enter this text code"）。
6. **复制显示的字符串密钥**（通常是 16 位字母数字组合）。
   * *注意：同时也请用手机验证器 App (如 Google Auth) 扫描二维码或输入密钥，以完成 GitHub 的验证流程。*

7. **⚠️ 记得把Preferred 2FA method选为Authenticator App，否则脚本不生效**

### 第三步：配置 GitHub Secrets
为了保护您的账号安全，请将敏感信息存储在仓库的 Secrets 中。

1. 进入您的 GitHub 仓库页面。
2. 依次点击导航栏的 **Settings** -> 左侧栏 **Secrets and variables** -> **Actions**。
3. 点击右上角的 **New repository secret** 按钮。
4. 依次添加以下 5 个 Secret：

| Secret 名称 | 填入内容 (Value) | 说明 |
| :--- | :--- | :--- |
| `GH_USERNAME` | **您的 GitHub 账号** | 通常是您的登录邮箱 |
| `GH_PASSWORD` | **您的 GitHub 密码** | 登录用的密码 |
| `GH_2FA_SECRET` | **2FA 密钥** | 第二步中复制的那串字符 (请去除空格) |
| `TG_BOT_TOKEN` | **Telegram Bot Token** | 用于发送通知 |
| `TG_CHAT_ID` | **Telegram Chat ID** | 用于指定接收通知的聊天 |

### 第四步：创建 Telegram 机器人并获取参数
如果你想在每次运行后收到通知，需要额外配置 Telegram Bot。

#### 1）获取 `TG_BOT_TOKEN`
1. 在 Telegram 中搜索 **@BotFather**。
2. 发送 `/newbot`。
3. 按提示设置机器人名称和用户名。
4. 创建完成后，BotFather 会返回一个 Bot Token。
5. 将这个 Token 保存到仓库 Secret：`TG_BOT_TOKEN`。

#### 2）获取 `TG_CHAT_ID`
有两种常见方式：

**方式 A：发送消息后通过 getUpdates 获取**
1. 先在 Telegram 中给你的机器人发送一条任意消息，例如：`hi`。
2. 浏览器打开以下地址，把其中的 `<YOUR_BOT_TOKEN>` 替换成你的真实 token：
   `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
3. 在返回的 JSON 中找到 `chat` -> `id`，这个值就是 `TG_CHAT_ID`。

**方式 B：把机器人拉进群组**
1. 先把机器人加入目标群组。
2. 在群里发送一条消息。
3. 再调用上面的 `getUpdates`。
4. 返回结果中的群组 `chat.id` 一般是负数，把这个值保存到 `TG_CHAT_ID`。

#### 3）通知规则
当前工作流通知逻辑如下：
- ✅ **登录成功时**：发送成功文字说明 + 最终截图 `06_final_result.png`
- ❌ **登录失败时**：发送失败文字说明 + 失败原因 + 最终截图 `06_final_result.png`

### 第五步：启用工作流权限 (⚠️ 重要)
由于是 Fork 的仓库，GitHub 默认可能会禁用 Actions 以防止滥用。

1. 点击仓库顶部的 **Actions** 选项卡。
2. 如果看到警告提示，请点击绿色的 **"I understand my workflows, go ahead and enable them"** 按钮。

### 第六步：手动测试运行
配置完成后，建议手动触发一次以确保一切正常。

1. 点击 **Actions** 选项卡。
2. 在左侧列表中选择 **ClawCloud Run Auto Login**。
3. 点击右侧的 **Run workflow** 下拉菜单 -> 点击绿色 **Run workflow** 按钮。
4. 等待运行完成，查看日志确保显示 `🎉 登录成功`。
5. 去 Telegram 查看是否收到了通知图片和文字说明。

### 第七步：查看运行截图
如果你想查看完整调试截图，而不只是 Telegram 中的最终截图：

1. 进入某次 GitHub Actions 运行详情页。
2. 找到页面中的 **Artifacts**。
3. 下载 `all-debug-screenshots`。
4. 解压后可查看所有步骤截图：
   - `01_home_page.png`
   - `02_after_click_github.png`
   - `03_github_login.png`
   - `04_after_2fa.png`
   - `05_after_authorize.png`
   - `06_final_result.png`

---
**✅ 完成！之后脚本将每隔 15 天自动执行一次保活任务，并通过 Telegram 发送运行结果通知。**

***搬运请标明来源！***
