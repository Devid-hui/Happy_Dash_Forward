# 新奶蛙实现准备：只读源核查

日期：2026-10-13。本阶段只读现有源码并写下方案；没有运行资产构建、生成模型或修改生产文件。实际实施等待 root 确认本轮远端推送完成。

## 已有证据与源码范围

父任务交接的图谱检查为 CLI Verify，项目 `happy-dash-forward-audit-20261012`，索引代际 `2026-10-13T02:07:37Z`，ready、1,655 nodes / 4,335 edges；builder 的 51 个符号分页完毕。builder、actor、tests 与模型 contract 的覆盖结果为 metadata_match/no_recorded_issue，属于最佳努力，没有据此声称全库无缺口。

本子任务没有直接 MCP 图谱工具，沿用父任务证据，并实际读取以下精确文件，未冒称直接 MCP 检查：

- `/Users/lpz/Documents/Happy_Dash_Forward/tools/build_nailong_asset.py`：1–235、345–516、build 与 export。SHA-256 `c5640cbd0f194c2faee695db3c4c9bbf82e123608fc9554d986e928237a35664`。
- `/Users/lpz/Documents/Happy_Dash_Forward/scripts/enemies/hunter_visual.gd`：1–235。SHA-256 `c435c0caaf72f06b475092d0a946e70a2d959df50ceff2396d39fe03ca78cd42`。
- `/Users/lpz/Documents/Happy_Dash_Forward/tests/nailong_model_contract.gd`：完整文件。SHA-256 `0409f329cc7b9cc1754117aaaea35a6869e80ad45c48c5cbc97ad2480e7c344d`。
- `/Users/lpz/Documents/Happy_Dash_Forward/tests/nailong_model_preview.gd`：1–125，实际预览角度与时间点。

图谱的结构交接覆盖 `_ready` / model preview 调用者与 `_prepare_asset`、`_has_joint_lid_grid`、`_is_shared_eyelid_face` 等被调用者。本次额外结论来自上述源码。

## 可以保留的接口

1. **24 根骨骼的名称与层级契约**。现有骨架是 root、pelvis、spine、belly、neck、head、jaw、tail，加左右各 8 根 upper_arm、forearm、palm、thigh、shin、foot、eye、brow。名称可继续保持，但所有 rest 位置需要按奶蛙重定。
2. **六段原生动作名称**：idle、walk、chase、warn、charge、recover。保持 root_motion=False，位移、碰撞与导航继续由游戏逻辑决定。现有参考时长分别为 3.2、1.0、0.68、0.8、0.50、2.0 秒，30 FPS；时长可作初始状态机兼容基线，动作形态需要重做。
3. **蒙皮输出约束**：每个顶点最多 4 根骨骼影响并归一化。这与 contract 的四影响变形采样一致。
4. **NLA/glTF 导出约定**：骨骼与形状键同名六轨、显式选中 mesh/armature、NLA_TRACKS、skins、UV、normal、tangent、材料；保留可编辑 `.blend` 母版与 runtime `.glb`。
5. **运行时资源共享与实例独立性**：共享 mesh/material 与资产缓存，各实例拥有独立 Skeleton3D 与 AnimationPlayer；手动动画推进和暂停冻结规则保留。
6. **坐标规则**：现有 builder 是 Blender Z-up/+Y-facing，glTF 到 Godot Y-up/-Z-facing。继续按项目实际约定验证，不能因教程一般约定而自动翻转角色。

`tail` 骨可保留兼容名称与层级，奶蛙身体不创建可见尾巴，tail 对新 mesh 的权重为 0，相关摆尾动画也归零。是否将其改作其他用途须由 root 决定；本方案不借名称改变既有含义。

## 必须重新制作的造型、UV 与变形

**主轮廓从新图建立。** 现有 BODY_PROFILE 在 z≈1.8–2.4 处维持很宽的头部，facial_volume 增加奶龙式脸颊、吻部和下巴；旧短手、短腿、爪、粉掌垫与尾巴均不移植。新轮廓为小头、短颈过渡、宽梨形躯干、大浅米腹、站立稍长腿和深橄榄手脚。

以旧 actor 约 2.8 的总高作为游戏尺寸初稿，建议先测试“头部宽约躯干最宽处的 0.40–0.50、头段高约总高的 0.16–0.20、脚到腿根约总高的 0.30–0.36”的比例区间。这些是拟定的可测设计目标，来自对低分辨率照片的轮廓判断，不是图中真实三维尺寸。具体值由新模型正面与 3/4 视角核对后定。

**连续皮肤采用新的拓扑。** 可沿用数学插值、mesh 建立与 limb sweep 的工具思路，但不要直接使用旧 profile、融合区、旧 mouth boolean、旧眼睑 patch 或其 shape targets。躯干到头、肩、髋要有连续平滑过渡，保留肩、膝与嘴眼周围有意义的环线；不能以旧 remesh 的 280 次平滑参数自动宣称完成解剖与变形。

**眼口从新参考重新设计。** 上置小眼与绿色眼圈、黑瞳孔需要匹配小头比例，避免旧大眼面孔。小嘴需要新的闭口边界与开口拓扑，口腔、嘴缘、舌头若保留则要具有真实内向深度、边界对应和可测的连续形变；不采用隐藏平面或叠加球体遮住旧开口。Blink/Focus/Open 的命名可保留，但目标顶点与组合逻辑重新编写，联合姿态不能使眼睑穿插或边界开裂。

**UV 与材质按实际网格建立。** 现有 `skin_uv` 对全 mesh 采用圆柱映射，源代码本身不能证明手、脚、肩和腿没有拉伸或重叠。新身体、手掌、脚与口部应有适合各区域的 UV 岛，背部/内侧放缝并检查 checker。浅米腹必须够大并贴合宽梨形正面；它是皮肤色块，避免看起来像贴上的厚硬圆片。手脚使用深橄榄色，删除旧粉掌垫和棕爪配置。4K 贴图分辨率不代替纹理与表面质量，保持柔和哑光与克制细节。

**高精源文件可编辑性由数据证明。** 交付母版保留命名清楚的 skin、眼、口等结构、可编辑 UV、材质、24 骨与六动作。runtime 来自真正可复现的母版导出；既验证接近镜头轮廓与表情，又验证距离 LOD。LOD 以形体、关节和嘴眼变形为依据，不能机械把旧 decimate=.09/.28/.22 当作新角色适用值。

## 当前权重与动作代码的迁移风险

`continuous_weights` 的头区 1.51–1.82、手臂 x/z 区间、腿区 .52–.85、foot/shin .13–.53、neck 1.36–1.60 全部属于旧身体的位置。新腿更长、头更小，必须从新骨架与对应表面重新测量分区。宽腹部下沿需要平滑分配到 pelvis/spine/belly，而不是随着单侧 thigh 扯开腿间区域。保留分区权重连续、四影响与归一化的原则。

`animations` 当前足底探针固定为 x≈±.40、y=-.07/.31、z=.018；这是旧脚轮廓。新橄榄脚必须按实际 sole 顶点范围计算接地，不只对 4 个旧坐标采样。warn、chase、charge 的腿弯曲与足部修正需要结合新大腿/小腿长度重算；看正面脚不穿地还不足以证明侧面不滑或脚掌不折。

旧探针仅按 foot 骨矩阵刚性变形。如果新足底包含 shin/thigh 的混合权重，探针修正不等于实际蒙皮顶点的最低高度；应测量完整足底。现有修正只沿世界 Z 抬升，不能消除支撑期的水平滑脚。pelvis.local Y 被当作世界高度、foot.local Y 的偏移及脚角抵消都依赖旧骨轴/roll，新 rest 矩阵必须再次核对。idle/recover 当前没有进入足底补偿分支，也应参与真正的接地采样。

此外 `chase=.68s` 在 30 FPS 下被 `round` 到 20 帧，关键帧跨度约为 .6667 秒，而 manifest 仍写 .68。六段动作时长应在真实导出数据里确认，既核对循环首尾，也核对 warn 单向蓄力终点到 charge 的过渡；不能只照抄 manifest。

spine 前倾、jaw 开合、belly 呼吸和 pelvis 起伏的骨骼空间以新 rest 矩阵核对。root 固定不妨碍身体与腿的正确运动，但不能靠前倾或 scale 把不合适的旧模型伪装成参考。

当前 `ANIMATION_BOUNDS` 与 builder manifest 也是旧 pose union。最终逐 LOD、逐 clip、多个时刻测量真正蒙皮+shape-key 顶点的并集，并加明确余量；不凭静止 aabb 或沿用旧常数声称无裁剪。

## 旧 contract 中需要辨别的断言

保留：24 bones、六实时时间轴动作、资源共享、实例姿态独立、状态选择、暂停冻结、接地、所有变形包围盒包含关系和 LOD 递减。

旧资产结构断言包括“至少 6 个 facial parts”“主 skin 名称含 NailongSkin”“LOD0 200k–400k”“Open 在某轴超过 .065”。这些不能强迫新奶蛙拥有错误比例、过多碎片或夸大的嘴。root 应在看见新拓扑和新视觉目标后，保留真正适用的预算，把不再适用的旧造型断言改成新的几何/变形证据，而非直接删除表情、连续性或性能验收。

运行时目前对 `SharedEyelidFace_` 和 `LidB###F###` grid 有特判，移动恢复会据此决定是否另写 Focus。新眼睑若采用新的整体连续拓扑，需要明确适配该逻辑；不能仅照搬 metadata 让旧特判通过，或复用曾经失败的嘴眼几何。

## 实施与交付次序

1. root 确认远端推送完成后，在新的奶蛙资产命名空间制作，保留旧资源供恢复；新生成器遵守现有 bone/clip/runtime 接口。
2. 首先完成真正的新连续母体和正面、3/4、侧面、背面初稿核对，再细化 UV、眼口、手脚与材质。侧背在参考不足时标明是设计补全。
3. 按新骨架重新绑定，制作六动作与表情组合；完整检查肩、腹、髋、膝、手腕、眼口和接地。
4. 导出数据检查真实 skins、joints、weights、UV、morphs、animations 与名称，检查重复 target/path 通道；实际导入 Godot，再运行与新角色适配后的 contract 和游戏测试。
5. 实际捕获 Godot 中正面/3/4/侧背、脸、手脚、六状态与夜景。预览相机取景跟随新小头位置，不能继续用旧 face/mouth 高度拍错部位。
6. 只有数据、源文件、近景外观、实际运行与必要测试共同通过后才提升为生产资产。所有检查报告区分已执行与未执行。
