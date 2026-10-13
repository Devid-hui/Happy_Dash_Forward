# 奶龙连续眼睑与实测口腔：隔离候选 v3

三档 GLB、全分辨率绑定源和 21 张 CPU 画面已经冻结，身份见 `FINAL_RECEIPT.json`；资产目录的 `FROZEN.json` 指向该回执。此候选可以交给隔离运行测试。闭眼的 C 形外圈、眼周材质拼接仍可见，尚未取得最终美术验收。正式 hunter 资产、`hunter_visual.gd` 和商业资产总清单没有由本子任务改动；本子任务没有启动 Godot 或 Metal。

## 资料与实际参考

先检查 [Blender Studio Rain](https://studio.blender.org/characters/rain/v3/) 的真实本地 `.blend`，再读取官方 [Rigify skin_eye.py](https://github.com/blender/blender-addons/blob/main/rigify/rigs/face/skin_eye.py)。Rain 为 CC-BY 4.0，署名 `Rain Rig (CC) Blender Foundation | studio.blender.org`；候选没有复制参考的网格、骨骼或 GPL 代码。资料地址、源码哈希及官方手册全文请求的 402/403 限制已保存在 v2 `references/reference-receipt.json`。

本轮进一步核查 Rain 的原生上/下眼睑、眼角、折痕控制及 ACTION 约束。直接给动作 frame 20/40 的第一次试验没有驱动几何，结果为零，明确保留为无效参考。随后在原 ACT 控制范围内，将上眼睑 local Y 从 0 改到 −.04 m、下眼睑从 0 改到 +.006 m，保持原 ACTION 约束、禁止 autoexec，实际头部 6395 个顶点最大变化 .039458476 m。见 `references/rain-act-closure-geometry.json` 及 CPU 对照图；该实际控制结果用于上睑承担主要闭合、闭合线低于眼心和眼周连续过渡的设计。

口腔复用了主任务已批准的 `outputs/nailong-mouth-review/accepted-v5/` 小函数，保持实测口缘边界、向内连续延伸的内衬及原 six-clip 表情驱动。批准的 v5 原件及 hash 保留，未使用后续低收益唇缘色改。

## 具体变化

眼球保持原半径 `.109/.069/.110 m`，眼球、虹膜、瞳孔和角膜仍为独立原生网格，不以缩放眨眼。三档使用共同的眼位，中心 Y 为 .750 m。眼皮由贴回实测脸面的上下连续 patch 组成；闭合边缘为细弧线，外缘复用原脸的 BRDF 和实测颜色。当前外圈仍能辨认，技术净距不能替代轮廓与材质的美术验收。

实际 BVH 深度记录在 `final-eye-depth-measurement.json`：sclera 峰值 Y 为 .819、角膜峰值 .8258；原 FaceSurface 中心左/右为 .83152/.83607，眼球已位于原脸面后 12.5/17.1 mm。最终开孔中心约 .809，眼球相对刻意回凹的开孔前凸约 10 mm。这说明遗留的外圈不能继续解释成旧版超过 10 cm 的球体探出；它需要眼周形体与连接的美术改进。

原口内坏片会从侧面形成黑团、黄色远壁或竖片。本候选删除全源 28143 个有记录的内面，三档各删除 15737/5166/1557 面，追加连续内衬。原 916134 个 source 顶点及 ID、留下的三角面都保留，Open/Focus 差量完全相等。清理函数另外验证了清理前后保留的颜色逐字节相等；眼区的重着色是另一个明确的修改。`source_body_topology_unchanged` 已改为 false，不能再声称全源拓扑未变。

左手主线之外的尾部沿用已批准 `.2` 单调长度压缩；原 x/z 不变。源权重与同为 `.2` 的前一稳定 v3 源逐顶点完全一致。最早未压尾的 `body-before-face` baseline 具有不同的合法 tail weights，第一次精确权重比较 false 的记录和诊断保留，未用它冒充相同版本的修复证据。

## 原生动画与导出方法

四片眼睑各有 120 个原生 shape targets。`Blink` 是 B100F0，`Focus` 是 B0F100，其他为 `LidBnnnFnnn`；双轴以 0–100、步长 10 取格点，B0F0 为 Basis。表情采用 Blink × Body.Focus 的双线性权重，不能直接把完整 Blink 和 Focus 的独立差量相加。身体和口腔各保留 Open/Focus 两个 targets。运行端播放原六段 `idle / walk / chase / warn / charge / recover`，本子任务没有新增运行时变形 tick。

独立差量叠加曾产生约 28 mm 穿球，记录在保留的失败档。之后的 30 FPS 强制采样还曾在实际帧间产生约 3 mm 穿球；仅增加 Blender 控制点而不核导出曲线无法消除这个问题。

已在 Blender 4.5.14 的真实 RNA 和 tiny-scene export 中核实：NLA_TRACKS 即使 force sampling 为 false 仍会烘焙成整数帧；ACTIONS + `export_merge_animation='NLA_TRACK'` 才保留已插入的浮点关键时刻。adapter 添加明确的 `--no-force-sampling` 候选参数。省略该参数时仍为 force sampling true + NLA_TRACKS，保持默认行为。本候选显式使用 false + ACTIONS/NLA_TRACK，没有手改二进制 GLB。实际六条动画、float crossing keys 和 target names 全部列于 `frame-and-shape-semantics.json`。Idle 的每片 lid 有 19 个非整数 30 FPS 时刻，Recover 18 个，Warn 7 个。

## 实际验证

| LOD | 实际三角面 | GLB 大小 | 完整 float accessor 值数 | 连续时间眼皮采样最小净距 |
| --- | ---: | ---: | ---: | ---: |
| 0 | 881467 | 76573612 bytes | 20031762 | 3.424571 mm |
| 1 | 254964 | 36802576 bytes | 9344280 | 3.298651 mm |
| 2 | 87277 | 29096272 bytes | 7348519 | 3.298608 mm |

每档真实 GLB 的 24-bone skin、六条动画、normalized weights 与包括稀疏 morph、skin、animation 的 float accessors 均通过。身体 432 条实际骨骼通道无缺失，原时间范围逐条相同；按 glTF linear/slerp、四元数 q/−q 等价比较，最大分量差为 2.7486647e−7。

`exported-face-triangle-audit.json` 从 GLB 读实际权重，检查语义状态和六段 clip 的每个实际 interval 内 1/4、1/2、3/4 时刻。`continuous-interpolation-audit.json` 进一步利用线性区间内角膜净距的凸性，在边界和唯一导数零点求最小值，逐档覆盖 1156 个实际权重区间。空间范围包括每个 lid 顶点、每个三角面的重心和三条边中点；不是对未采样面内每一点、任意后续组合或未来运行骨骼分离的证明。

`integrated-mouth-export-audit.json` 从整资产实际 GLB 对 Body 与 oral Open/Focus 在六 clip 的合并关键时刻及中点进行比较，差量均为零。每档 245 个 oral 权重区间的连续投影面积最小值为正，最低比值 .994585，未发生三角面反转。这不单独证明任意嘴部与 body 碰撞。

源和每档包围盒使用 60 个实际姿态、所有顶点测量，原始测量及有 .08 m 余量的 Godot AABB 在 `MODEL_MANIFEST.json`；source 最低高度 .00697255 m，各档也保持正值。它们属于姿态采样包围盒，完整原生动画的动态边界由隔离 runtime harness 再查。

21 张同源画面均为 Blender 4.5.14 Cycles CPU，640 × 640，8 samples，2 线程：五级 Blink 的正面与 65°、Focus .5/1、90°脸、全身四视角及 Open 0/.82 的正面与 65°。没有以 CPU 图声称 Godot transmission、skin 或性能通过。Blender primitive_extract 的 matmul 曾输出 divide/overflow/invalid warnings；完整实际输出 float 审计仍全部 finite。口腔子任务的有限输入/输出诊断也记录了 finite 且重导出字节相同；底层警告根因尚未证实。

## 复现

从当前聊天目录运行：

```sh
work/runtime/blender/Blender.app/Contents/MacOS/Blender --background --disable-autoexec --threads 2 --python /Users/lpz/Documents/Happy_Dash_Forward/tools/bind_reconstructed_nailong.py -- --input outputs/nailong-surface-refined/final-candidate/nailong-surface-refined.glb --repo /Users/lpz/Documents/Happy_Dash_Forward --output work/nailong/rig-candidate/face-tail-trial-v3 --source-output work/nailong/rig-candidate/face-tail-trial-v3/source --tail-length-scale .2 --config outputs/nailong-face-candidate-v3/eye-frame-config.json --face-helper /Users/lpz/Documents/Happy_Dash_Forward/tools/reconstructed_nailong_face.py --no-force-sampling --skip-previews
```

冻结后复现应另选输出目录，避免覆盖这里的身份。`face-helper-final.py` 与 `adapter-final.py` 是冻结的完整工具快照。最终导出日志 `generate-v3-final-integrated.log`、最终同源 CPU 检查 `inspect-final-corrected.log`、帧间检查 `exported-final-interpolation-audit.log` 可追溯。v2 原件、v3 各失败档和本次之前的稳定 ACTIONS 档全部保留。

图谱通过受支持的 codebase-memory-mcp CLI 0.11.0 使用 Verify；项目 `happy-dash-forward-audit-20261012`，当前代际 `2026-10-12T23:23:43Z`。两路径 coverage 无记录缺口，helper metadata_changed、adapter metadata_match、无更多页。helper 完整源码及 adapter 涉及参数/导出/main 的当前源码已经回退阅读；动态导入造成 helper 的 indexed inbound 为 0，不能据此判断未使用。无记录缺口不证明完整，主任务在所有并行源码稳定后统一重建索引。
