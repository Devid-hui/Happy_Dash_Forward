# 手部模型资源与精修依据

核查日期：2026-10-13。推荐采用 Blender Studio 写实手作为体块、比例和拓扑对照，MakeHuman Hands 01 作为当前源网格可追溯的局部修形依据，再以解剖和工具握持资料约束骨轴、权重与接触。没有把任何免费底模判作现成商业级第一人称手资产。

## 已取得并检查的资源

### Blender Human Base Meshes v1.4.1

[官方发布页](https://www.blender.org/download/demo-files/)与[官方下载目录](https://download.blender.org/demo/asset-bundles/human-base-meshes/)提供 CC0 包。本次实际下载 50,643,039 bytes，SHA256 为 `811f43accbb31a88266d932f8f5563b2d13586fca0ba2693aad1f5fe582b3515`，并在 Blender 4.5.14 中禁用自动脚本读取。

实际找到 Dan Ulrich 的 `Hand  - Realistic`：831 个基础顶点、820 个基础面（819 个四边面），有 UV 与一层真实 Multires；评估网格为 3,300 顶点、6,596 三角面。作者元数据说明基于扫描数据。Julien Kaspar 的风格化手为 871 顶点、880 面。两者都没有绑定、动画、皮肤材质或图片贴图，适合造型与变形拓扑基准，不能凭细分直接宣称达到用户要求的最终精度。

包内 README 及这两个手资产的独立 metadata 均明确 CC0。文件另有一个点名 Rain Rig 的旧 License 文本；证据已整体保留，没有把该文本与手资产的独立标记混为一谈。拆出的双手参考文件保留原资产元数据，未改原 ZIP。

- [独立手部参考 BLEND](/Users/lpz/Documents/Codex/2026-10-12/codex-threads-01a12ea7-2c11-7112-8b57-2/outputs/hand-reference-research/blender-studio-hands/official-hand-base-meshes.blend)
- [实际模型检查收据](/Users/lpz/Documents/Codex/2026-10-12/codex-threads-01a12ea7-2c11-7112-8b57-2/outputs/hand-reference-research/blender-studio-hands/REFERENCE_RECEIPT.json)
- [写实手背实际渲染](/Users/lpz/Documents/Codex/2026-10-12/codex-threads-01a12ea7-2c11-7112-8b57-2/outputs/hand-reference-research/blender-studio-hands/realistic-front.png)
- [写实掌面实际渲染](/Users/lpz/Documents/Codex/2026-10-12/codex-threads-01a12ea7-2c11-7112-8b57-2/outputs/hand-reference-research/blender-studio-hands/realistic-back.png)
- [风格化手实际渲染](/Users/lpz/Documents/Codex/2026-10-12/codex-threads-01a12ea7-2c11-7112-8b57-2/outputs/hand-reference-research/blender-studio-hands/stylized-front.png)

### MakeHuman Hands 01

[官方页面](https://static.makehumancommunity.org/assets/assetpacks/hands01.html)逐项标明四个 target 为 CC0。本次已下载并检查包内 metadata，内容为指节、指尖/拇指、大小鱼际的顶点位移，不是新的独立网格或绑定器。

与项目当前 19,158 顶点的原始 OBJ 比较：全部 target 索引有效；所有非零位移均落在左右手区域，两侧记录数相等。原始全权重位移上限约 1.10–6.11 mm，因此不能不经外观检查就全部拉满。采用时应在原始索引阶段应用，再裁出手部、细分、绑定。这里已验证数据的索引范围与作用部位，尚未应用进游戏，也未证明变形后的持握质量。

- [原始 CC0 包](/Users/lpz/Documents/Codex/2026-10-12/codex-threads-01a12ea7-2c11-7112-8b57-2/outputs/hand-reference-research/downloads/hands01_cc0.zip)
- [与当前底模的索引核对](/Users/lpz/Documents/Codex/2026-10-12/codex-threads-01a12ea7-2c11-7112-8b57-2/outputs/hand-reference-research/downloads/hands01-current-base-compatibility.json)

### 绑定方法参考

[Blender Studio Rain v3](https://studio.blender.org/characters/rain/v3/)公开标为 CC-BY，列有 IK/FK 切换和姿态修正。它适合参考成熟角色的控制、局部形变修正与验证方法。这里只核对了官方发布说明，未下载或验证 Rain 的具体手部权重；不把它说成已取得的替换资产。当前研究无需安装插件或开启第三方 BLEND 自动脚本。

另一个实际获取的 [Innerscene CC0 右手](https://www.innerscene.com/tools/library/3d-parts/posable-anatomical-right-hand-f6098b4f)有 16 骨、12,728 三角、无贴图/动画，仍属 MakeHuman 派生，只保留为独立骨架与手性对照。[补充资源核验](/Users/lpz/Documents/Codex/2026-10-12/codex-threads-01a12ea7-2c11-7112-8b57-2/outputs/hand-reference-research/resource-alternatives.md)记录了需要登录的模型及未采用的资源，避免把“网页免费”当作真实可用成品。

## 对本项目有实际约束作用的资料

1. **掌心翻转来自前臂旋前/旋后，腕屈伸是另一类运动。** 左手下托时，前臂应连续转向，腕掌交界保持自然，不能由单个腕节点承担全部朝向差。[解剖运动类型](https://openstax.org/books/anatomy-and-physiology-2e/pages/9-5-types-of-body-movements)
2. **拇指对掌从第一掌骨开始。** 当前 Thumb1/2/3 应对应第一掌骨、近节与远节指骨；不能解释为三节指骨，也不能复制四指的统一转轴。[上肢骨骼](https://openstax.org/books/anatomy-and-physiology-2e/pages/8-2-bones-of-the-upper-limb)
3. **真实接触不能由统一 curl 比例保证。** PIP/DIP 联动在接触物体时会改变；应逐指拟合握柄，单独设置按扳机、托灯、捏袋与握瓶。[Roda-Sales 等，2022](https://peerj.com/articles/14051.pdf)
4. **手掌皮肤褶不是骨关节轴。** 掌垫、大小鱼际、掌弓和甲床应独立建模，不能把可见褶缝直接当 MCP 中心。[Bugbee 与 Botte，1993](https://pubmed.ncbi.nlm.nih.gov/8222413/)
5. **握柄要适配手与动作。** CCOHS 建议用能维持中立腕位的形状；动力握持参考直径 30–50 mm、长度不少于 100 mm，工具重心宜接近握持处。这些是人体工学指导，非游戏美术的硬性认证标准；项目当前约 34 mm 握柄直径与约 133 mm 长度落在该参考范围，但不因此证明姿态自然。[CCOHS 原文](https://www.ccohs.ca/oshanswers/ergonomics/handtools/tooldesign.html)、[NIOSH 原始指南](https://www.cdc.gov/niosh/publications/numbered/2004-164.html)
6. **源文件与运行时分开验收。** 先校骨轴和权重，再做局部体积修正；Blender 中的保体积效果必须落实为 Godot 实际保留的几何、骨骼或形变，不能只看源设置。[Blender Corrective Smooth](https://docs.blender.org/manual/fi/4.5/modeling/modifiers/deform/corrective_smooth.html)

更完整的来源和读取边界见 [解剖与绑定依据](/Users/lpz/Documents/Codex/2026-10-12/codex-threads-01a12ea7-2c11-7112-8b57-2/outputs/hand-reference-research/anatomy-rigging-guidance.md)。解剖图谱和论文在这里用于事实参考，没有把其插图或网格导入游戏。

## 精修决定

保留当前已纠正的左右手性、基本腕向与器具接口。在中立手与握持姿态中对照官方底模，优先补大小鱼际、掌弓、指节/指腹和甲床；每根指骨采用自身铰链与稳定弯曲平面，之后再加浅掌褶和皮肤材质。保持当前已保存版本可恢复，任何新底模或微形变先独立试做并通过掌背、掌面、侧面与第一人称对照后再替换。面数与自动化通过数量均不是外观验收标准。用户已取消必须60FPS的要求。

本轮完成了检索、下载、许可与实际文件核对、真实参考网格渲染及实施依据整理；参考资产尚未直接替换现有游戏手部。完整目标仍未宣布完成。
