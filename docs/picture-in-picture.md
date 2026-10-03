# 对话画中画

把 dsh 网页对话放进 Android 系统画中画小窗。用的是系统 PiP，不需要悬浮窗权限。

## 怎么用

能不能进小窗只由 Android 系统的应用画中画开关决定，App 里没有单独的开关。「设置 → 配置 → 系统画中画设置」显示当前状态（系统已允许 / 系统已关闭 / 设备不支持），点一下会打开系统的画中画设置页；打不开时退回到应用信息页。

系统允许时：

- 在对话页回桌面或切到别的应用，对话会进入小窗。
- 在网页里点返回、主页或设置按钮回到原生界面时，不进小窗。
- 原生的启动页、设置页、终端页本身不进小窗，但已经打开的小窗可以浮在它们上面。
- 锁屏、DSH 正在停止或已被你停止时，不进小窗。
- 小窗上有一个按钮，在横版和竖版之间切换。改的是网页的视口宽高，手机方向不变，选择会记住。
- 点系统的展开按钮，或者在原生启动页再点「进入」，回到同一个网页，接着输入。
- 关掉小窗只关网页预览，后台的 DSH 继续运行。

需要 Android 8.0+，并且设备支持画中画。小窗适合查看；要输入或做复杂操作，先展开。

## 实现

| 文件 | 内容 |
|---|---|
| `ui/PictureInPictureActivity.java` | 进入条件、系统参数、横竖切换、停止后收起 |
| `ui/PictureInPictureFrame.java` | 小窗里缩放同一个网页 |
| `util/PictureInPicturePolicy.java` | 纯逻辑：进入条件、宽高比、缩放、视口；单测 `PictureInPicturePolicyTest` |
| `ui/WebPreviewActivity.java`、`low` 的 `ui/GeckoPreviewActivity.java` | 继承 `PictureInPictureActivity` |

- 清单里只有 `WebPreviewActivity` 和 `GeckoPreviewActivity` 声明了 `supportsPictureInPicture` 和 `singleTask`，原生启动、设置、终端的 Activity 都不继承这个基类。
- 系统是否允许用 AppOps 的 `OPSTR_PICTURE_IN_PICTURE` 判断（`allowed()`）。小窗显示期间系统那边被关掉，小窗会直接关闭。
- Android 12+ 交给系统自动进入（`setAutoEnterEnabled`）。Android 8–11 在 `onUserLeaveHint` 里主动进入。
- App 自己打开其他页面时（文件选择、外部浏览器、`startActivityForResult`、回原生页），先撤掉自动进入，免得多出一个小窗。
- 小窗期间网页视口固定不变，只做缩放，不重新加载。横竖切换会交换视口的宽和高，让网页重新排版，文字不会旋转。宽高比限制在 1:2.39 到 2.39:1 之间，超出部分留边，不裁切。
- 横竖切换是系统 `RemoteAction`。每个网页实例用自己的随机 action、不可变的 `PendingIntent` 和不导出的接收器，Activity 销毁时取消。
- 布局选择存在 `picture_in_picture_layout`（`auto` / `portrait` / `landscape`），经 `ConfigStore` 读写，会进入配置备份和恢复。
- 只有完全看不见时（`onStop`）网页才暂停，`onStart` 时恢复。小窗显示期间每 500 ms 读一次内存里的 Web 代次和停止状态：DSH 停止或重启换了代次，小窗就关掉。不探测端口，也不结束进程。
- 进入小窗时收起软键盘。

系统回收进程后，按浏览器原有的恢复流程处理。

## 验证情况

`PictureInPicturePolicyTest` 有覆盖。本仓库还没有系统地做过真机验收（见 [HANDOVER.md](../HANDOVER.md) 第 8 节）。

## 参考

- [Android 画中画指南](https://developer.android.com/develop/ui/views/picture-in-picture)
- [PictureInPictureParams.Builder](https://developer.android.com/reference/android/app/PictureInPictureParams.Builder)
