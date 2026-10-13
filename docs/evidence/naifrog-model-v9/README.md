# 奶蛙 V9 冻结证据归档

本目录归档已完成的 V9 实际报告、完整日志、10 张 CPU 图、4 张 GPU/CPU mask 以及执行脚本快照，所有复制保持原字节并逐 SHA 核验。源→仓库相对路径、bytes、SHA 和依赖资产身份见 PORTABLE_INDEX.json；收尾统计与范围见 CLOSING_RECEIPT.json。本子任务没有运行引擎/检查器、修改生产源码/模型或执行 Git。

- producer/：冻结身份、验证后身份、完整 UV 判重、源与三档 GLB 数据契约、全部 FLOATAccessor 有限性、四套实际足底检查/summary、表面→UV→PNG 颜色诊断及10张CPU预览。freeze-identities.json 是当前正式资产身份入口。
- native/：完整生产套件、targeted-contract JSON/原始stdout、import/preview/floor-probe日志。实际 V9 是3853 checks、276 sampled states、37943652 vertex evaluations、failures空；不能沿用V8的37835000。生产套件实际报告 import、failure gate、13场景合同、两个archive restart进程全部PASS。
- render-floor/：实际GPU/CPU四mask、完整report及V8→V9 geometry-identity。feet视图左右脚IoU均1、bottom delta0；three_quarter最多1px差。最低world脚底约0.001m。此处的Godot server bake是CPU重建且忽略morph，不是最终GPU顶点回读；实际GPU证据是raster silhouette。报告确认sole active morph delta0，对其他部位不能借此省略形变。
- standalone/：实际macOS export、release executable headless菜单入口启动、exact editor从真实输出PCK加载资源、codesign验证及preset/input恢复回执。四项exit均0、errors空，preset_restored与inputs_unchanged均true。release二进制实际以 --headless --quit-after 30 启动；editor/PCK probe另用 --headless --main-pack。这不代表可见GUI、普通键鼠整局或release二进制完整游戏验收。大型.app/.zip/.pck不重复归档。

实际V9 UV检查 complete/ok=true、status=clear：Body选定UV atlas的606058三角形、1971402候选对全部完成，正面积重叠0、零UV面积三角0。该检查针对NaifrogContinuousSkin的UV，不把它扩称为所有独立mesh互相判重、几何自交或动画检测。四套source足底每套502样本、442支撑样本，约1mm、超3mm/穿地均0；native契约已启用3mm支撑上限，旧V8的14mm不能替代此结果。颜色诊断是实际11点采样，cover均1，最大sRGB误差约.001809；并非逐texel色彩证明。

geometry-identity.json实测SOURCE Basis/三morph/topology/ROI与GLB canonical物理身份不变，UV并不相同、bone/support也另验，因此仅复用 ../naifrog-model-v8/naifrog-face-independent/v8/report.json 中27个raw authored rest morph组合的有限眼口FACE ROI/外围一圈几何结果。没有在V9新跑这27组合；不复用V8的UV、足底、native画面或全部运动结论。闭眼前睑/回封二面角诊断仍保留，几何通过不等于商业级美术认可。

实际执行脚本快照在 tools/naifrog_validation_archive/v9：producer、parser、uv、render-floor、native、standalone。UV checker SHA已与V9报告匹配；actor SHA已与targeted及GPU报告匹配。native contract源码为当前3mm版快照，runtime未单列test-script SHA，不补造原始字段。.gd以.gd.txt保存避免成为生产额外脚本；.log与.cfg只追加.txt后缀。历史绝对路径/参数未静默重写，重跑应使用匹配身份的当前输入与显式路径。

没有复制大型Blender/GLB二进制，因为当前正式6个source/LOD/manifest已逐SHA与producer冻结清单核对一致。归档依赖这些现有正式资产；同一路径以后被替换时不能继续当成V9输入。pack的哈希、模板来源与实际bundle信息保留在standalone/validation.json，不把未归档APP/PCK称为已经提交到仓库。普通整局输入、连续时间数学证明、全角色自交、稳定60FPS或商业美术认可均未由本归档声称。native/graph-final-reindex.txt仅保留当时诊断，最终代码图谱刷新由根任务完成，模型二进制身份来自SHA核对。
