# 奶龙 Body 真实 UV／4K 色图隔离候选

本目录现在有实际可编辑 UV、由原色烘焙的真实 4096×4096 PNG、带 TEXCOORD_0／Base Color Texture 的 GLB 和完整 Blender 源副本。原 Body 几何、Basis／Open／Focus、蒙皮权重、原 CORNER 颜色与所有动作曲线保持精确一致。**这是一份 Body 技术候选，整角色 UV/PBR 和最终商业美术仍未完成。** 少量薄面／边界取色偏差在下方完整列出，不由均值或预览图代替。

## 可交接的素材

- `work/nailong/uv-pbr-trial/body_uv_4k_local_islands_candidate.blend`：完整 c3 源的隔离副本，Body 有可编辑 `BodyUV4k`，原 BYTE_COLOR／CORNER `Color` 保留。新的 Base Color 输入为图像；原顶点色没有再次相乘。保存后已实际重新打开核对。
- `work/nailong/uv-pbr-trial/nailong_body_basecolor_4k_local_islands.png`：真实 4K、sRGB、原色无光照 EMIT 烘焙，不是统一色占位图。有效身体像素的 RGB 标准差约 14.07／27.14／28.98（8bit 值）。
- `work/nailong/uv-pbr-trial/body_uv_4k_local_islands_only.glb`：Body＋原 24 骨＋原六 clip 的直接材质/UV 导出证明；不是完整角色的正式替代 GLB。
- `body-source-corner-uv-transfer.npz` 与 `UV_CORNER_TRANSFER_RECEIPT.json`：全部 1,804,153 个 c3 post-mouth SourcePolygonID、对应原角点 VertexID 及 UV。**UV 缝必须按面角点处理，不能只为一个 VertexID 选一个 UV。** `transfer_uv_corners.py` 同时支持三角内原 VertexID 匹配和明确 post-mouth LoopID；新 CDT/radial 面返回 NaN 并要求单独展开。

逐 SHA 身份见 `FROZEN.json`。Face owner 仍在制作变动中的双眼源，因此不把旧 prototype sidecar 当最终双眼冻结文件。已实际核对其当前 sidecar 全部 7,830 ANN 的 post-mouth PID／LoopID／原 VertexID 与 c3 完全相等；证据为 `V5_ANN_SOURCE_CORRESPONDENCE_CHECK.json`。新的透明 normal-only ghost 环也须按其最终 sidecar 的源面角点转移，不由本候选自动生成。

## UV 制作与实测

输入来源是冻结 c3 源，SHA `c3f08b4b01489b5cc548aac7f23717338d24819fbb0e514706d59986bfa6be8c`。实际 Body 为 916,134 vertices／1,804,153 三角面，没有原 UV，材质原为顶点色直接进入 Principled，roughness=.48。所有使用面的共享索引连通分量为 **1**，13,740 个未被面引用的原顶点保持原样。大量小 chart 不是四万个独立几何碎片；39,825 个≤10面 chart 只占 3D 面积约 7.02%，空间分布遍及身体。是否为内部可见表面不能仅由 chart 数量推断。

最初完整 xatlas 求解实际运行 3439.7 s，未重启。它生成 11240×11248、40,761 charts，包含 padding 的占用为69.56%，但实际三角 UV 面积仅10.85%，11个非零3D小面被库忽略成0UV。原输出、缺陷定位和严格像素审查仍保留；没有把69.56%当有效4K面积。

实际查阅对应0.0.11发行源和安装API，再用真实小样确认 `add_uv_mesh` 可以复用既有参数化进行 UV 连通/packing。`resolution` 加非零 `texels_per_unit` 才能固定4096²。源码还说明归一化细UV会受绝对 `FLT_EPSILON` 面积阈值影响；按16384的精确2次幂换算输入单位后，全部面不再被误忽略，未更改几何或原参数化。

11个被忽略面按自身真实3D三角形平面展开补 UV。原图块用2px padding重新排布：8500密度需2张，8000有1个严格内部重叠像素，均未选用；7000单张4K、0退化、0未指派、严格像素重叠0。其真实三角面积32.633%，密度中位419.57px/m。不能把这些 API 探针、未选结果或日志异常写成最终合格。

首次 EXTEND／随后 ADJACENT_FACES 实际烘焙发现薄面取色不足。对**全部**三角面重心采色后，183面误差范数>0.03。整图重新packing虽修原183面，又因其它薄面像素位置改变出现新偏差，因此该版保留为诊断。当前候选只在实际空白右条带放原183面的小岛；所有其它1,803,970面的UV角点逐位相等。小岛来自真实三角平面投影，并明确增加纹理跨度以支撑栅格采样；没有添加毛孔、噪点或改3D形状。

当前独立4096²严格三角内部像素审查：**1,804,153 UV三角均有效，0退化，0重叠像素写入，5,250,634像素／31.2962%覆盖**。共享边界排除，检测不排除亚像素交叠，不能宣称连续曲面零重叠。alpha并不等同几何覆盖；曾对原回执的opaque-alpha名称作修正，最终几何覆盖只取独立三角审查。

## 原色、形变与导出兼容证据

- `BODY_UV_LOCAL_ISLANDS_BAKE_PROOF.json`：UV／材质前后原几何、三个形状、weights、原 CORNER 色和全部 action curves SHA 完全相等。真实 GLB 有 POSITION／NORMAL／TEXCOORD_0／JOINTS_0／WEIGHTS_0、真实 baseColorTexture，**没有 COLOR_0**；原色保留在编辑源但没有再次乘进完整烘焙色图。
- `LOCAL_ISLANDS_SAVED_SOURCE_REOPEN_PROOF.json`：实际重新打开保存源，原状态与原 c3 相等；全部5,412,459个UV角点与所选Atlas逐位一致，内嵌PNG字节与实际写出PNG相等，24骨未变。
- `LOCAL_ISLANDS_ANIMATION_EXPORT_COMPARISON.json`：与冻结c3 LOD0逐项比较原六 clip 的 **432骨频道＋6Body Open／Focus权重频道**，时间、值及插值模式一致，最大数组差**0**。GLB全部浮点 accessor 已实测有限；这不是原生Godot画面或眼周新拓扑证明。
- 12张同源同灯CPU图位于 `compare-local-islands/{before-vcol,after-texture}/`。六对均值显示RGB差约 .000029～.000130，最大单通道差约 .05882；已实际查看正面、后背和65°同源图，未见整体肤色变黑。CPU图保持c3原造型，不能据此接受尚未完成的新眼周。

全量色彩核对：`FULL_BODY_CENTROID_LOCAL_ISLANDS_AUDIT.json` 逐 **1,804,153** 个三角面重心，PNG sRGB先解码线性，再双线性过滤，与原线性角点颜色插值比较。

| 实测 | 当前结果 |
|---|---:|
| 误差范数p99 | .0040143 |
| p99.9 | .0097188 |
| 全量最大值 | **.2258027** |
| >.03的重心 | **27** |
| >.1的重心 | **8** |
| 上述27面的真实总3D面积 | .00045035 m²，Body约.001622% |

100k抽样的最大值仅.04339，不能替代上述全量最大值。残余主要为薄面／边界取色；不能称完全无误差或保证所有连续表面点。此轮已保留有明确收益的局部UV修整，并收束这项隔离试验，**不把它记为整角色／商业美术通过**。正式材质接入后仍需实际Godot各LOD／mipmap／雨夜照明和最终角色原生画面核对。

PBR的金属度0、roughness .48和真实几何法线保持；没有凭空制作统一色roughness/normal图冒充测量。Body真实UV／albedo不完成眼睑、虹膜、口内的新UV，也不完成全角色R22。

## 来源、范围与工具身份

已读Blender4.5 UV／seams／Cycles baking／glTF官方章及实际安装RNA，原文与摘要在 `references/` 和 `REFERENCES.md`。xatlas与bindings均MIT，使用0.0.11私有运行环境；发行tag24d7e3与vendor f700c779源只作能力依据，安装API、4K展开／烘焙／真实GLB另实际执行验证。没有安装全局依赖、修改上游addon、启图形Godot／CUA或编辑生产文件。

本轮图谱是实际支持的CLI，最终generation `2026-10-13T01:19:59Z`，ready1654 nodes／4342 edges。binder `metadata_match/no_recorded_issue`；九个新增最终工具为 `outside_project/unavailable`，10/10完整无更多页，按真实源码、已装API、独立数组／文件检验补证。不是直接MCP调用，coverage没有记录缺口也不证明完整。
