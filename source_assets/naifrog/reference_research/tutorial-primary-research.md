# 奶蛙教程与 Godot 导入：作者及官方来源核验

核验日期：2026-10-13。范围仅含教程作者页面、作者自己的课程说明与官方手册；未播放或看完下列视频，未下载视频、课程资产或执行外部脚本，未生成模型，也未修改生产仓库。视频判断来自本次直接读取的 YouTube 标题、作者描述、页面章节数据。Godot 建议固定引用 4.5 手册，Blender 固定引用 4.5 LTS 手册，避免 `stable` 链接今后换版造成混淆。

当前造型目标来自主任务已查看的参考：小头、短颈、宽梨形黄色身体、巨大浅米色腹部、站立且稍长的腿、橄榄色手脚。本文件给出的是方法适配判断，不代表任何教程原角色已符合参考。

## 1. 三个作者视频

| 来源 | 已核实身份与范围 | 对奶蛙的可借用方法及限制 |
| --- | --- | --- |
| [Crowfriend Games — Blender to Godot from Scratch](https://www.youtube.com/watch?v=0aLCOJWvuc4) | 作者为 Crowfriend Games；2025-09-03 发布，约 2 小时 7 分。作者描述明确列出青蛙从零建模、绑定、动画、导入 Godot 与 AnimationTree，且有作者填写的章节。 | 最适合参考整条 Blender → Godot 流程，尤其权重与引擎接入。造型必须按奶蛙参考重新调整，不能复制教程比例。描述中的“导入成功”是作者自己的演示，不是本项目验收。 |
| [Blender Study — Modeling a frog character - Blender Tutorial](https://www.youtube.com/watch?v=t6uP7VKiIgI) | 作者为 Blender Study；2020-07-05 发布，24:12。作者描述只明确承诺青蛙建模与渲染，链接了参考图和另一个渲染设置教程；本次未发现页面章节点。 | 可借参考图驱动的卡通形体与展示渲染。不能据描述推定有骨骼、蒙皮、游戏动画或 Godot 导入内容；旧版 Filmic、降噪等渲染设置也不能当作 Godot 外观保证。 |
| [SouthernShotty — Blender 3D - EASY Low Poly Frog Character Rig](https://www.youtube.com/watch?v=NN4xM3dQKtg) | 作者为 SouthernShotty；2020-08-27 发布，18:03。[作者自己的 Skillshare 课程页](https://www.skillshare.com/en/classes/bring-your-illustrations-to-life-with-blender-3d/1598809277)将此准确 ID 列为青蛙动画教程，并在公开文字中说明该补充视频涉及 Shape Keys；课程本体明确不覆盖动画。 | 可借简单青蛙的形状键表情与动画思路。标题出现 Rig 不能证明它提供完整骨骼走路系统；Shape Keys 不能替代腿部权重、接地与 Godot 动画检查。 |

Crowfriend 的发现链已由主任务保存：[Games in Progress 发现页](https://www.gamesinprogress.com/indie-game-developers/john-makes-games/blender-to-godot-from-scratch) → 页面嵌入视频 ID `0aLCOJWvuc4` → 作者 YouTube 页。发现页仅用于定位，以上内容结论来自作者页直接核对。

Crowfriend 的作者章节与 YouTube 页面章节数据相符，以下是与主任务有关的时间点（标题作中文概述）：

| 时间 | 内容定位 |
| --- | --- |
| 00:00:00 / 00:02:55 | 参考与寻找形体 |
| 00:14:32 / 00:16:15 | 后腿与第二次调整 |
| 00:29:48 / 00:37:30 | 骨骼与权重绘制 |
| 00:42:44 / 00:58:18 | 比例调整与手臂 |
| 01:15:40 | 动画与姿势 |
| 01:17:38 / 01:19:21 | Godot 接入与作者检查导入结果 |
| 01:23:45 / 01:26:41 | AnimationTree 与查文档 |
| 01:34:45 | UV 展开 |
| 01:52:08 / 01:58:26 | 贴图与法线图 |
| 02:06:09 | 作者游戏测试 |

SouthernShotty 页面也显示章节，但数据明确归属 `engagement-panel-macro-markers-auto-chapters`，因此它们是 YouTube 自动章节，不能标成作者章节。可作为定位线索：约 00:30 身体、03:33 脚、05:44 眼睛、09:09 贴图设置、10:36 上色、14:48 Shape Keys、16:21 动画；未经视频播放核实这些自动标签的准确性。Crowfriend 的章节归属 `description-chapters`，与描述时间戳互相印证。

## 2. Blender Studio 官方 Yule Frog

[官方章节页](https://studio.blender.org/training/3d-printing/chapter/yule-frog/)明确将目标设为用于 3D 打印的青蛙摆件。课程分为基础形体、眼睛、腿、帽子、脚与嘴的雕刻、连接腿与眼睑、收尾。可借其形体建立、脚趾与嘴部细化方法；帽子不属于当前参考，3D 打印摆件的网格也不能直接证明可用于游戏动画。

[官方源文件页](https://studio.blender.org/training/3d-printing/yule-frog-blend-file/)标出作者 Hjalti Hjalmarsson，并称文件是本章最终 `.blend`；当前页面标签为 Blender 5.1 File。版本标签已核实，实际文件能否在已安装 Blender 中打开仍须由下载与检查报告确认。此处不推定文件具有可用的游戏骨骼、权重或动画；许可与获取情况由主任务的资产核验负责。

## 3. Godot 4.5 官方导入原则

[可用 3D 格式](https://docs.godotengine.org/en/4.5/tutorials/assets_pipeline/importing_3d_scenes/available_formats.html)推荐 glTF 2.0，支持 `.glb` 与 `.gltf`。`.blend` 直导也先调用本机 Blender 导出 glTF，因此同样受 glTF 能力限制；每位执行导入的协作者需要 Blender，Android 与 Web 编辑器不能调用外部程序。用于交付与复现时，建议保留 `.blend` 源文件，并另交付经过核对的 `.glb`，这是针对本任务的工作建议。该页还要求有 Shape Keys 的模型启用只导出变形骨骼，以避免错误着色。

[模型导出注意事项](https://docs.godotengine.org/en/4.5/tutorials/assets_pipeline/importing_3d_scenes/model_export_considerations.html)说明 Godot 的资产正面为 `+Z`，Blender 对应 `-Y`；导出前应核对物体变换与默认休息姿势，提前三角化可提高结果一致性。引擎与 Blender 的灯光效果不同，最终灯光应在 Godot 中评估。

[导入配置](https://docs.godotengine.org/en/4.5/tutorials/assets_pipeline/importing_3d_scenes/import_configuration.html)提供动画导入开关、烘焙 FPS、裁剪以及 `.blend` 的采样和分轨设置。FPS 应匹配建模时基准；限制播放范围可能误剪动画；强制采样用于减少 Blender/glTF 插值差异。Godot 4.0 起可把 glTF 仅导入为 AnimationLibrary，再供 AnimationPlayer 使用。存在动画资源并不表示已经搭好 AnimationTree。

[高级导入设置](https://docs.godotengine.org/en/4.5/tutorials/assets_pipeline/importing_3d_scenes/advanced_import_settings.html)支持模型与动画预览、动画保存到外部文件，以及切片。切片要求源文件只有一个名为 `default` 的动画；可分别设帧范围和循环。默认优化器通常保留，若怀疑其破坏动画再进行对照。外置材质的改动须把模型放进实际场景预览，因为高级导入预览仍显示原材质。

## 4. Blender 4.5 LTS 官方 glTF 导出原则

[官方 glTF 2.0 手册](https://docs.blender.org/manual/en/4.5/addons/import_export/scene_gltf2.html)确认可导出网格、受支持材质、骨骼蒙皮和形状键动画。导出器只识别受支持的材质节点，不能指望任意 Blender 节点网络原样到达 Godot；简单 Principled BSDF 色块更便于核验黄色身体、浅米腹和橄榄手脚，复杂效果需要另查支持或烘焙。

动画可导出的核心是物体 TRS、骨骼姿势与 Shape Key 数值；材质、灯光和物理属性动画会被忽略。Actions 默认模式仅导出活动动作或已关联至 NLA 的动作。4.4 起采用 Slotted Actions，合并行为发生变化，不能照搬旧教程的轨道命名假设。应核对本次导出的动作名称与数量。

导出 Shape Keys 时须同时启用形状键数据和形状键动画；采样、休息姿势、播放范围、只导出变形骨骼及动作间重置都可能影响结果。由骨骼驱动的形状键采样要求对应网格直接隶属骨架。约束和程序化运动应以导出后的实际动画为检查对象，不能仅看 Blender 视口。

## 5. 对本任务的选择与验收边界

推荐顺序是用 Blender Study 或 Yule Frog 的方法理解形体、用 SouthernShotty 补形状键表达、用 Crowfriend 参考绑定到 Godot 的完整链路，再以固定版本官方手册决定导出选项。这里的“可借”表示方法相关性；本次没有观看教程操作，也没有复现其结果。

教程、标题、章节和文档均不能替代以下实际验收：奶蛙正面/侧面/背面比例与色块；抬腿、屈膝、伸臂时的变形；嘴眼表情；导出后骨骼、权重与动作数量；Godot 中方向、尺寸、材质、阴影；动画循环、脚部接地及状态过渡。本文件未执行这些检查，因此不声称任何资源已经符合奶蛙外观或游戏可用标准。

## 本地可复查证据

- `source-pages/crowfriend-discovery.html`：主任务保存的发现页，canonical 和嵌入 ID 可复查。
- `source-pages/{crowfriend,blenderstudy,southernshotty}-youtube.html` 与对应 `-metadata.json`：本次从各作者 YouTube watch 页面直接读取的原始页面和内嵌数据。
- `source-pages/tutorial-video-primary-verification.json`：精简身份、日期、作者描述、完整章节和原始 HTML SHA-256；明确标注未播放视频。
- `source-pages/blender45-gltf.{html,txt}`、`godot45-{formats,export,import,advanced}.{html,txt}`：本次官方页面直接读取，均返回 HTTP 200。网页读取器对部分 Blender 页返回抓取错误，直接读取官方 URL 补足；未把抓取器错误误当网页不存在。
- `source-pages/yule-{frog,blend-file}-tutorial-text.txt`：从主任务已保存的官方 HTML 提取的可读文本。
- Skillshare 公开作者说明与课程文字经网页读取器核对；直接 HTTP 获取返回 403，未宣称保存了该页原始 HTML，也未进入付费课程。
