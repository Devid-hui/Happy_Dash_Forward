# 当前开发版独立 macOS 应用预检

这份应用验证导出和资源交付链路。新奶龙 V5 眼周、UV／PBR 尚在独立目录制作，应用仍使用当前正式旧奶龙；这不是最终四阶段交付包或商业美术验收。

应用：`TheMidnightAcademy-preflight.app`。官方模板来自 Godot 4.7.2-stable，1281349702 字节模板包的 SHA256 与官方资产 digest 一致；提取的 macos.zip 也记录了 SHA256。模板位于当前聊天工作目录，没有安装到全局目录。

## 实际结果

- `--export-release macOS` 返回0，无脚本／引擎错误。
- 导出 Universal 2 应用，真实 Info.plist 包含 arm64／x86_64，最低系统版本13.00／11.00。
- 导出的 release 应用在本目录启动主菜单并按30迭代退出，未指定源码仓库路径；仅为 headless 启动验证，不是图形／输入验收。
- 随后 release 应用以 Metal4／Forward+／Apple M4 Pro 实际录制8张1920×1080主菜单图，字体和按钮可见，无脚本／引擎错误。MovieMaker的60FPS仅为录制时间基准，不是游戏运行性能。
- 本地 ad-hoc 签名的 `codesign --verify --deep --strict` 返回0；没有 Apple Developer ID 公证或发布。
- 同版本4.7.2校验引擎直接读取该应用内的实际 PCK，没有向运行命令提供源码仓库路径。21个 GLB 导入资源、9张实际4096×4096环境贴图及主场景／World／玩家／五只追猎者，共46项加载检查通过。
- 包内主手部／器具为229800三角、38骨；报告125512三角，塔83268三角，废车529190三角。这里是每资源全部网格合计，森林资源还包含多个LOD，不能作为同时绘制量。
- 导出前后运行源码／资源哈希一致；临时 custom_template/release 路径已还原，永久预设保留可移植配置。

## 保留的失败及修正

初次尝试对 release 二进制传外部 `--script`。该官方 release 的实际 `--help` 不提供这个入口，探针没有执行；仅停止本任务拥有的进程，失败回执保留。随后改由同版本校验引擎读取应用内 PCK，这一结果与 release 应用正常输入分别记账。

资源探针最初在 World 销毁后立即退出，出现 AudioStream／OggPacketSequence 未释放。verbose 记录明确指向音频；现有 smoke 测试本就等待音频混音线程。本次只修外部探针：让检查协程先返回、释放场景，再按现有fixture等待1秒。重跑无 SCRIPT ERROR／ERROR，也无泄漏警告，没有修改游戏音频逻辑或放宽检查。

主回执：`validation.json`、`native-load-receipt.json`。诊断及失败日志完整保留。

实际应用图还暴露右侧提示句号孤行。仅源码提示改为两行自然短句；同版本原生source场景重新录制8张1080图并实际检查，见 `native-menu-fixed-source/menu00000007.png`。这项源码修正晚于本应用快照；最终模型接入后导出时一并带入，不把修后源码图称为此快照二进制图。

## 未完成的验收

Mac仍处锁屏状态，正常鼠标／键盘、三报告逃生、原生应用的档案重开尚未验证。新奶龙正式三档接入后，需完整回归并重新生成最终应用及资源包；当前预检成功不意味着整项目完成。

依据：[Godot官方macOS导出说明](https://docs.godotengine.org/en/stable/tutorials/export/exporting_for_macos.html)、[4.7.2实际macOS导出源码](https://github.com/godotengine/godot/blob/4.7.2-stable/platform/macos/export/export_plugin.cpp)。
