# 新奶蛙模型契约：实施与验收边界

最新状态：根任务已成功导入新模型并实际运行契约；第一次运行因本测试将 PackedFloat32Array 直接构造成 PackedFloat64Array 的 API 错误中断。六个 surface 的 cache 未建立造成后继足底/morph 为零，不能据此判定模型失败。本子任务已只修复这三行数组类型/读取，没有修改任何阈值，也未启动引擎；真实几何结论待根任务锁内重跑。最初实施记录保留在下文，最新修复身份见 WEIGHT_ARRAY_FIX_RECEIPT.json。正式 actor、旧测试、runner、资产和已提交的历史归档没有由本子任务修改。

唯一生产写入为 `tests/naifrog_model_contract.gd`、同名 `.tscn` 和 `.gd.uid`。根任务负责 actor/runner、引擎共享锁和后续索引更新。`--candidate-script` 沿用旧契约的参数，先运行隔离 actor；新正式路径经根确认是 `res://assets/refined/naifrog/naifrog_lod0.glb`，同目录 LOD1/2。脚本通过实际 MODEL_PATH 的 `_lod0.glb` 后缀读取三份原生文件，输出每份 SHA256，不把旧候选结果作为新奶蛙数据。

## 新参考的约束

已实际查看 `work/naifrog/user-references/naifrog-primary-reference.png`（144×257）。可辨识的是小头、非常大的浅色椭圆腹部、下垂长臂、深色手掌与脚部，以及外张且弯曲的腿。照片分辨率不足以锁定背部、脚趾数、微小材质纹理和复杂口内结构。因此旧角色的大头、多张独立口腔/唇舌网格与夸张张嘴位移没有继续作为形象要求。新的正面、斜面、侧面和六动作画面仍需原生视觉验收；数值通过不代表这张参考的美术验收完成。

## 对旧契约的最小语义调整

| 旧断言/缺口 | 新契约 |
|---|---|
| 至少六个面部 morph 部件 | 不限定拆分数量；每档实际 Blink/Focus/Open 的非零几何与同一 mesh/channel 的运行权重变化必须同时存在 |
| 特定 `NailongSkin` 名称、Open Y 位移大于 6.5cm、固定 idle/warn 权重时刻 | 按真实 morph 名称、实际动画极值时间取证；不规定旧比例或张嘴幅度 |
| 20万到40万面、固定每档小于上档40% | 实数记录唯一 Mesh 资源的三角数与单实例提交量，要求三档实际递减，不添加未经批准的预算 |
| 只验证 LOD0 的五个时刻 | 三档、六动作的九个等分时间，额外包括真实 Blink/Focus/Open 通道的最大/最小键时刻 |
| 数值检查忽略 rigid 节点、只认四骨权重 | 先混合所有实际 morph，再对四/八权重完整蒙皮；rigid mesh 按真实节点变换纳入 |
| 只有 Director 整体盒 | 同时检验整体 actor-local 盒与每个 renderer 的 mesh-local `custom_aabb`；转换实际坐标系后检查 |
| 顶点最低 Y 大于 -0.015 被称为接地 | 完整网格防穿地；另识别左右实际脚底 patch，静止双足距平面不超过 +0.015m，gait 至少一足支撑 |
| 对象身份不同就称独立 | 另一实例的骨姿、morph、时钟、动画时间、状态和 LOD 在首实例更新后保持不变 |
| 暂停只看动画时间 | 暂停完整姿态/时间/状态不变，恢复后 physics 时钟与实际动画时间继续前进；手动回调无重复推进 |

## 具体保留的边界

每份原生 LOD 都必须有一套 24 骨 skeleton 和六个明确的 `idle/walk/chase/warn/charge/recover` 动作，实际 duration > 0.3 秒、存在轨道且原生骨姿/morph 确实变化。三档骨名称/层级/rest、mesh 名称、shape 索引顺序以及 Skin palette/bind 必须相容，才能让现有静态 mesh swap 使用 LOD0 skeleton/animation。几何变了可以是新形象；三档彼此误绑定不能算兼容。

五个实例和重开场景都只准备一次缓存；每档实际 Mesh、active material 和 material_override 资源共享，Skeleton3D/AnimationPlayer 对象以及姿态保持独立。每份数组完整验证 finite、权重归一、索引合法和 rest 三角非退化。三角数按唯一 Mesh 资源计数，不乘五实例；每个 actor 的实际提交量另列。这里没有跨资源的几何位置重复面去重，不能把面数当作视觉质量。

保留原状态机优先级：眩晕 recover、预警 warn、冲锋 charge、按速度 walk/chase、站立冷却 recover、移动冷却继续 gait。移动冷却的真实疲态 overlay 另外测两个 gait、五个时间、三种呼吸时钟，并要求 overlay 后完整原生表情权重精确保持，仍按全顶点检查包围盒与脚底，不只检查原六 clips。actor transform、root bone 平移、skeleton/model frame 不得暗中移动。pelvis 的合法步态平移不被误称为拉长骨骼。

足底识别方案已与建模任务和根任务对齐：实际 native 数组中的该侧 `foot_left/foot_right` 骨权重至少 0.5，且 rest 位置 y≤0.04m；逐档记录完整 patch 顶点数。每个 patch 的最低点用完整 shape+skin 后的位置计算，未以脚骨、四个探针或全身最低点代替。静止 idle/warn/recover 要求左右两足支撑；walk/chase/charge 和移动冷却至少一足支撑，不强制摆动脚也贴地。没有飞行阶段豁免。建模任务的逐档 source sole IDs 与最终 stance 回执仍待真实源产出；若实际分配不满足当前约定，应明确修正模型/映射并记录证据，不松动 +/-1.5cm 阈值来取得通过。

## 证据与限制

实际通过已安装 CLI 识别图谱 project `happy-dash-forward-audit-20261012`，generation `2026-10-13T02:07:37Z`，ready 1655 nodes / 4335 edges。旧 builder/actor/model contract 三路径 coverage 完整返回，无更多页，均 metadata_match/no_recorded_issue；这是 best effort 无已记录缺口，不证明源或关系穷尽。`_skin_bounds` search 完整返回一项、trace both 返回有限原生关系；实际源码可见 `_run` 调用它，因此没有用图中的零 caller 作无人调用结论。已实际读取完整旧契约/actor与相关 builder 来源。新增代码未入当前图谱，本轮用精确源码回退，根任务需更新索引。

本子任务只做文本结构/必需断言检查；根任务已对前一版实际执行 headless --check-only，退出0且无 SCRIPT ERROR/ERROR。最后一次精确非零 morph 与原生权重保持修正仍需根任务重解析最终 SHA；任何 parser 通过都不等于真实几何运行通过。Godot 的 parser、真实导入、完整数值运行和视觉画面由根任务取得共享锁后执行；未运行时状态必须保留为 pending。九个等分时刻与实际表情极值覆盖所声明的取样，不是每个连续插值时刻的数学证明；如果包围盒靠近极值，要增加实际键间/骨轨极值取样或依据作者完整曲线构造保守 envelope，不能换成随意扩大盒。原生真实 terrain/完整关卡中的脚底与遮挡仍需根任务后续验收。

官方 API 依据：

- [Mesh 数组类型](https://docs.godotengine.org/en/stable/classes/class_mesh.html)：骨索引与权重可为四或八个影响，不能静默丢弃后四项。
- [MeshInstance3D](https://docs.godotengine.org/en/stable/classes/class_meshinstance3d.html)：仅 skeleton 的 bake 忽略 blendshape，不能拿它代替组合形变的全顶点证据；本契约直接读真实数组再组合。
- [Skeleton3D](https://docs.godotengine.org/en/stable/classes/class_skeleton3d.html)：global bone pose 是相对 skeleton，不是 world；这里显式纳入 skeleton-to-actor 与 Skin bind。
- [GeometryInstance3D](https://docs.godotengine.org/en/stable/classes/class_geometryinstance3d.html)：custom_aabb 是 mesh 局部渲染盒，material_override 替换表面材质，因此检验实际 active material。
- [Animation](https://docs.godotengine.org/en/stable/classes/class_animation.html)：通过真实 track key 时间与数值查取表达极值，不捏造固定闭眼/张嘴时刻。

精确文件 SHA 与当前 commit 见同目录 `IMPLEMENTATION_RECEIPT.json`。以上方案没有要求稳定60FPS，也没有把任何旧 .app、pack 或旧奶龙检查声称为新奶蛙交付。
