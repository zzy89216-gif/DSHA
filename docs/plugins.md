# 插件：安装、管理与打包

适用于 Standard 和 Low 两个版本。插件的安装、启用、停用、删除都要到启动页重启 Web 后才生效。

## 内置插件

内置插件随 APK 提供，按受管清单注册，不能删除，也不能用第三方压缩包覆盖。

| 插件 | 作用 | 默认 |
|---|---|---|
| `dsha-mobile` | 手机专属网页界面（0.2.0），见下文 | 启用 |
| `dsh-web-mobile` | 旧的移动端适配（[mexiaosqwq/dsh-web-mobile](https://github.com/mexiaosqwq/dsh-web-mobile)，MIT） | 停用 |
| `dsh-status-overlay` | 流式悬浮条 | 启用 |
| `dsh-task-notifier` | 回合完成通知 | 启用 |
| `dsh-device-shell-guide` | 设备能力引导 | 启用 |
| `dsh-computer-use-android` | Android Computer Use | 启用 |
| `dsh-tool-vscreen` | 虚拟屏工具 | 启用 |
| `dsh-auto-review` | 官方实验性 Auto review 入口 | 启用 |

dsha-mobile 从 v0.1.7-rc2-zzy.7 起内置（zzy.8 起为 0.2.0），源码在 [zzy89216-gif/dsha-mobile](https://github.com/zzy89216-gif/dsha-mobile)：

- 底部标签栏：对话 / 会话 / 新建 / 设置；抽屉打开时底栏仍然可点。
- 侧栏改为抽屉。点抽屉里的会话行会直接打开那个会话：宿主把会话行做成「单击=选中、双击=打开」，抽屉如果在第一次单击就收起，第二次点击就落不到那一行上，历史对话会打不开。长按、拖列表都不当成「要进去」。
- 设置面板全屏打开，键盘弹出时底栏让开，对话区也不再留底栏的空白。
- 在网页「设置 → 通用设置」增加三项：手机模式、动态玻璃、配色。

dsh-web-mobile 仍随包提供，不会被删除。升级到或新装 zzy.7 后，App 会把它停用一次（只做一次，凭据记在 DSH 数据目录）；之后你手动重新启用，它会一直保持启用。

用户停用过的内置插件，升级后保持停用。

## 从链接安装

在「插件」页的「从链接安装」粘贴链接，页面先显示识别结果，确认后点「安装」。支持：

- GitHub 仓库：`owner/repo` 简写、完整 URL 或 `git@github.com:` SSH 地址。
- GitHub `tree` 链接（指定分支和子目录）；`blob` 链接按该文件所在目录处理。分支名带斜杠时通过 GitHub API 解析，不会退回默认分支。
- GitHub archive、codeload 和 Release 附件下载链接。
- Release 页面：只有一个压缩包附件时直接安装；有多个时列出附件名，请复制要装的那个下载链接。
- HTTPS 的 `.zip` / `.tar` / `.tar.gz` / `.tgz` 直链。
- 含一个链接的分享文字。识别到多个链接时会要求只粘贴一个。

HTTPS 证书随 APK 提供，TLS 校验始终开启，不需要先装基础工具。GitHub 访问受限时，先下载压缩包再本地导入。

「插件」页的「社区插件生态」入口会在 App 内打开一个**外部**插件目录站点。该站点不由本项目维护，
与本项目没有隶属或支持关系，内容与可用性都不受本项目控制。在那里选好的插件，仍要通过链接或本地
导入安装，App 不会自动安装。这是目前唯一的外站入口，计划改为不依赖外部目录。

## 本地导入与导出

「导入插件包」用系统文件选择器读取 ZIP、TAR、TAR.GZ、TGZ，按文件内容判断格式，不看扩展名或 MIME。一个压缩包里可以有多个插件目录。默认优先用系统 DocumentsUI；如果选择后没有返回，改用「其他文件选择器」。

「导出插件包」可多选并指定保存位置，生成包含插件和已有依赖的 TAR.GZ，另一台设备可以直接导入。导出不需要存储权限。官方核心随 dsh 环境更新，不能单独导出或替换。

导入同名插件会更新它，并保留原来的停用状态。新版本和依赖都准备好后才替换旧版本，普通失败会还原；写入完成后若遇到强杀或断电，不保证完整回滚。

## 管理

「插件管理」可以按名称或描述搜索、只看第三方插件、按名称或启用状态排序。卡片的「更多」按钮或长按卡片可以复制名称和来源链接、单独导出、删除第三方插件。

第三方插件安装后先保持停用，查看详情并确认后才启用。

删除前会确认，只移除该插件的安装目录、启用登记和来源记录；聊天、设置、其他插件和共享依赖不受影响。需要留存的话先单独导出。

## 在终端安装

内置终端可以直接用 `npm` / `npx`，Python、npm、Git、curl 共用随包证书。

```sh
# 普通依赖和命令行工具：照常用 npm
npm install 包名
npm install -g 工具包名

# 发布到 npm 的 dsh 插件：下载、校验并登记到插件管理
dsha-plugin install 插件包名
dsha-plugin install @作者/插件@1.0.0
```

`dsha-plugin` 还支持 `import`、`export`、`list`、`delete`、`check-updates`、`rollback` 和 `safe-mode on|off|status`，不带参数运行会打印用法。

`dsha-plugin install` 不执行包的安装脚本，要求发布包已构建并声明 `dsh.bundle.patch`。普通 `npm install` 不会改动 dsh 的启用列表。插件只发布在 GitHub 而没有发布到 npm 时，用链接或本地导入。

npm 下载会在官方源和 npmmirror 之间自动选择。

## 插件包要求

- `package.json` 要有合法的 npm 名称、有效的 `version`，并声明 `dsh.bundle.patch`（字符串或字符串数组）。
- 声明的 patch 文件、`main` 和 `cordis.entry` 入口必须存在于包内。
- 只是名字以 `dsh` 开头的普通 npm 库不会被当成插件。
- 名称不能与内置插件或官方核心（`@deepseek-ai/dsh-base`、`@deepseek-ai/dsh-web-app`）相同。

请发布已构建的包（Release 附件或 `npm pack` 产物）。依赖齐全时可以离线导入；缺 `dependencies` 时，App 在独立目录用 pnpm 安装生产依赖再登记。不会执行 prepare / build / install 等脚本。依赖工作区源码、需要现场编译或缺少原生二进制的插件，需要作者提供能在 Linux arm64 容器里运行的完整包。

pnpm 在 proot 下使用硬链接会出错，所以环境固定设置了 `package-import-method=copy`。

限制：

- 压缩包最大 256 MiB；解压后最多 768 MiB、50000 个文件。
- 越界路径、指向包外的软链接、同名冲突、缺少入口都会拒绝，并说明原因。
- 一个包里部分插件安装成功时，会分别列出成功项和失败原因。

## 测试

`scripts/test-plugin-manager.py` 在临时目录里覆盖导出再导入、多插件包、子目录定位、路径拒绝、失败还原、部分成功和删除保护，不访问网络、不调用 pnpm。链接解析由 `app/src/test` 下的 Java 单元测试覆盖。
