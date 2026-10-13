# 奶蛙模型更新：V9 正式接入与交付

2026-10-13。本轮可编辑模型、三档运行资产、表情、六套动作、Godot 正式接入和本地验证已完成。此前全部改动与建模报告已发布为 `17b34a52af23054998b8b715cb586ae250eb50b1`；本报告记录其后的奶蛙专项更新。分支为 `codex/four-stage-modeling`，引擎仍为 Godot 4.7.2。

用户最新范围是先提交已有改动，再集中优化角色，并把参考改为奶蛙。树、第一人称手部、器具、UI、技能和科研成长本轮没有继续制作；相关回归检查保留。稳定 60 FPS 已取消硬门槛。下方验证证明指定结构和运行行为成立，不把面数或测试通过写成“商业级美术已验收”。

## 形体、材质与动画

制作依据为[用户新照片](../previews/naifrog/PRIMARY_REFERENCE.png)。角色重建为较小的圆头、短颈过渡、宽梨形躯干、大面积浅色腹部和较长站立腿；双臂向腹部回收，手掌为深橄榄色，脚背保持黄色、脚趾和脚底为深色。照片没有可见尾巴，正式网格不制作尾巴；兼容骨架中的 tail 骨保持中性且权重为零。

主体为一个闭合连续网格，源主体实测 303,031 顶点、303,238 多边形、606,058 三角面，连接分量为 1，边界边和非流形边均为 0。眼皮和口缘与主体连接，口内有真实腔体及舌头；双眼为独立网格。修正了旧迭代的突出眼圈、张嘴时主体穿插、口缘翻面，以及颜色烘焙重叠导致的黑块和浅色手掌。

主体使用 4096×4096 颜色、粗糙度贴图，源文件内打包图像，运行 GLB 内嵌贴图；粗糙度实际范围约 0.60–0.82。UV 划为 14 个语义区域，掌背另行展开，消除了上版同臂 UV 重叠。保留真实网格法线，未用噪声法线贴图虚构表面细节。

24 根兼容骨骼，六套动作分别为 `idle / walk / chase / warn / charge / recover`。主体每顶点最多四个骨骼影响，权重归一化；LOD 减面后再次整理权重。表情使用 `Blink / Focus / Open` 三个形状键，由实际动画曲线驱动。动画不额外移动游戏物理根，正式 actor 保留共享资源缓存、独立实例骨骼和动作时钟、三档切换及保守动画边界。

| 运行模型 | Godot 实测每实例三角面 | 实测顶点数 | 文件大小 |
| --- | ---: | ---: | ---: |
| LOD0，近景 | 618,634 | 329,143 | 34,869,824 bytes |
| LOD1，中景 | 103,884 | 62,006 | 7,229,692 bytes |
| LOD2，远景 | 31,044 | 21,282 | 3,673,172 bytes |

顶点数包含导出时 UV／法线拆分，不能与源网格顶点数直接比较。面数为主体、双眼和舌头的总和。三份 GLB 均带完整兼容骨架与六动作；Godot 导入后的动作长度分别约 3.2333／1.0333／0.7000／0.8333／0.5333／2.0333 秒，导入器比源时间范围增加约一帧。

正式入口 [hunter_visual.gd](../../scripts/enemies/hunter_visual.gd) 已使用 `assets/refined/naifrog/naifrog_lod0.glb`，中远档切到同目录 LOD1、LOD2。游戏提示、撞击和融合说明中的角色名称同步为奶蛙。旧奶龙源文件和失败候选仍保留为历史材料，导出配置排除旧奶龙运行目录。

## 检查结果及其范围

| 检查 | 本版实际结果 | 范围 |
| --- | --- | --- |
| 可编辑源与三份 GLB 数据 | 源合同、三 GLB 合同全部通过；各 GLB 的 310 个 FLOAT accessor 无非有限值，无 `COLOR_0` 干扰贴图颜色 | 结构、权重、形状键、嵌入图像与动画数据 |
| 完整主体 UV | 606,058 三角面全部建立索引，1,971,402 候选对耗尽；正面积重叠 0、零面积三角面 0 | 当前主体源 UV 全图；阈值 `area_epsilon=0`，不扩大为各 LOD UV 的独立全图检查 |
| 双眼与嘴的 27 组合 | 原始几何穿插、退化及相对 Basis 翻面均为 0；沿冻结眼框法线、在前眼睑与真实眼球 cap 的投影重叠区域中测得最小有符号间距约 3.0818 mm | V8 已执行；V9 通过源与真实 GLB 的位置、morph、三角形、ROI 和眼框 exact identity 比较，仅复用几何结论，UV、视觉和接地重新检查；不是完整三维最近距离验收 |
| 源动作脚底 | 高精源与各 LOD 每份 502 个脚样本，442 个支撑样本；支撑高度 0.999983–1.000013 mm，超过 3 mm 和穿地均为 0 | 六动作实际关键帧，读取整只脚的有效顶点集合 |
| Godot 专项合同 | 3,853 项检查、276 个采样状态、37,943,652 次顶点评估，失败 0 | 三档 morph／蒙皮／刚性部件、支撑、动画边界、五实例共享与独立、暂停／恢复及重建；支撑上限已收紧为 3 mm |
| 实际 GPU 轮廓 | 脚部视图 GPU／CPU mask 完全一致；三分之四视图脚底轮廓最多差 1 像素 | Metal／Forward+、1920×1080、LOD0 的两个 idle 视图；不是所有动画时间的 GPU 顶点证明 |
| 正式回归套件 | 导入、运行器错误拦截自检、13 场景合同、两个档案重启进程全部通过 | 运行器同时检查退出码、成功标记和引擎／脚本 ERROR |
| 独立 macOS 应用 | 导出成功；release headless 菜单入口和后续真实可见菜单窗口均启动成功；签名验证成功；实际导出 PCK 的 46 项资源／World 加载检查失败 0，包含五只追猎者和三档奶蛙 | release 菜单画面、headless 启动与 exact-version editor 的 headless PCK 资源探测分别记录；不声称已在 release GUI 内完成游戏或普通键鼠整局逃生 |

V8 的 24 对 UV 重叠和约 14 mm 支撑高度保留在[历史证据](../evidence/naifrog-model-v8/README.md)，没有覆盖成通过。V9 已按实际 UV 和动画重新制作、导出、检查；当前文件身份见[冻结清单](../evidence/naifrog-model-v9/producer/freeze-identities.json)，本版全部回执见[V9 证据索引](../evidence/naifrog-model-v9/README.md)。

`MODEL_MANIFEST.json` 是导出器产生的制作回执，其中 `validation.godot_run=false` 表示导出步骤未调用 Godot；它不承载后来运行的验收结果。本版实际 Godot 检查保存为独立原生日志和机器报告，并核对同一模型 SHA。

已生成 19 张真实 Metal／Forward+、1920×1080 原生图，包括正／侧／背／三分之四视角、脸、眼口、手脚、六动作和夜间受光。实际查看了整体、眨眼、张嘴预警及脚部相关视图。

![V9 原生三分之四视角](../previews/naifrog/godot_three_quarter.png)

![V9 原生预警动作](../previews/naifrog/godot_warn.png)

## 公开资源和教程如何使用

研究记录及源文件见[资源与教程报告](NAIFROG_RESOURCE_RESEARCH.md)。实际下载并打开了 [methodical pixel 的 CC0 蛙源文件](https://opengameart.org/content/frog-low-poly-animated-3d-model)，核查其网格、骨骼、权重、UV 与 glTF 导出。该样本只有 600 三角面，是四足低模；用于研究流程，没有作为最终奶蛙替换品。

制作指导参考 [Crowfriend Games 的 Blender→Godot 作者教程](https://www.youtube.com/watch?v=0aLCOJWvuc4)、[Blender Studio 的 Yule Frog 教程](https://studio.blender.org/training/3d-printing/chapter/yule-frog/)及已核查的 Blender／Godot 官方导出文档。作者页面、章节、许可与获取限制均留有记录；只核查网页资料，没有声称播放完视频或取得登录后源文件。新奶蛙是根据照片重新制作的网格和贴图。

照片只有 144×257，侧面、背面与完整动作姿态属于制作补全。平滑表面符合本轮参考方向，不把照片压缩颗粒当作皮肤细节。技术检查和预览足以确认这版可直接接入游戏；与参考相似度、闭眼观感及商业级美术标准仍是独立的视觉判断，未由自动测试代替。

## 使用与复现

- 可编辑带骨骼母版：[naifrog_high_rig.blend](../../source_assets/naifrog/model/naifrog_high_rig.blend)。
- 兼容制作源：[naifrog_game_rig.blend](../../source_assets/naifrog/model/naifrog_game_rig.blend)。
- 直接使用：[LOD0](../../assets/refined/naifrog/naifrog_lod0.glb)、[LOD1](../../assets/refined/naifrog/naifrog_lod1.glb)、[LOD2](../../assets/refined/naifrog/naifrog_lod2.glb)。正式工程已经接入，打开 `project.godot` 即可使用。
- 制作器：[build_naifrog_asset.py](../../tools/build_naifrog_asset.py) 与 [naifrog_materials.py](../../tools/naifrog_materials.py)。
- 数据与 UV 检查：[naifrog_inspect.py](../../tools/naifrog_inspect.py)、[naifrog_uv_verify.py](../../tools/naifrog_uv_verify.py)。
- 原生专项：[naifrog_model_contract.tscn](../../tests/naifrog_model_contract.tscn)。完整套件：`python3 tests/run_tests.py --godot /path/to/Godot-4.7.2`。
- 原生预览：Godot 4.7.2 运行 `tests/nailong_model_preview.tscn -- --naifrog`，输出 `docs/previews/naifrog/godot_*.png`。

独立应用与 ZIP 保存在本次聊天的 `outputs/naifrog-standalone-v9/`，不混入可编辑仓库。导出时使用已核验的官方模板，临时模板路径随后逐字节恢复；生产输入前后 SHA 一致。较早的 standalone preflight 和旧 ZIP/PCK 是历史快照，不能代表当前奶蛙。

后续通过 `cua_repl` 按新 APP 的完整路径启动了实际 release 窗口，核对运行进程路径及真实菜单画面，随后关闭本次实例。证据见[可见菜单回执](../evidence/naifrog-release-visible/VISIBLE_MENU_RECEIPT.json)和[窗口原图](../evidence/naifrog-release-visible/visible-menu.jpg)。该记录仅增加可见菜单启动证据，没有开展整局操作或写入科研档案。

Git LFS 管理模型和贴图；检出该分支后应完成 `git lfs pull` 再启动工程。先前 `17b34a5` 的云端失败来自 checkout 未取得实际 LFS 文件，本次已设置 `lfs: true`，云端结果以当前提交对应的 GitHub Actions 为准。

奶蛙主提交为 `9f27f2281b63cad171d28a8402dbe797323c3790`；已从远端独立检出并下载实际 LFS 数据，15 个关键文件逐 SHA 与本地一致。[发布和回读回执](../evidence/naifrog-publication-v9/README.md)记录这一身份。该提交的首轮云端检查已成功取得 LFS 文件，但冷导入在 62% 时触发 120 秒超时，未进入场景测试。工作流随后使用运行器已有的 `--timeout 360` 参数，保留退出码、ERROR 和成功标记三项判定，以及 20 分钟总作业上限。

后续云端冷导入仍在 360 秒超时，末段正在导入多份旧奶龙候选；同时发现可见菜单截图原件为 JPEG、后缀误记为 PNG。现已保留原字节并修正为 `.jpg`，原 SHA 不变；给 `docs/`、`assets/nailong/`、`assets/refined/nailong/` 增加 `.gdignore`，保留历史文件但不参与当前 Godot 资源导入。已按当前 actor、动态 LOD、森林／地表绑定清单、器具与正式 13 场景测试核对依赖。正式资源仍在 `assets/refined/naifrog/` 和其余现用目录；图片预览直接保存到文档目录不受影响。复现依赖旧模型的离线历史候选时，需暂时移开对应 `.gdignore` 并重新导入。第二轮实际失败日志已归档，不将超时记为通过。

提交 `5059734` 的实际云端检查已通过冷导入（185.41 秒）、错误拦截自检、奶蛙专项、其余 11 个场景合同及两次档案重启；唯一失败为 Linux runner 未安装中文字体，UI 合同在“雨”字覆盖断言失败后等待至超时。当前主题已明确列出 `Noto Sans CJK SC` 系统字体候选，macOS 本地完整 UI 合同通过。现仅在 CI 安装 Ubuntu 官方的 `fonts-noto-cjk` 和 `fontconfig`，不修改游戏主题或字体断言；[官方包文件清单](https://packages.ubuntu.com/noble/all/fonts-noto-cjk/filelist)确认包含 NotoSansCJK-Regular/Bold 字体。该轮实际日志已归档，后续完整结果以最终提交的 CI 为准。
