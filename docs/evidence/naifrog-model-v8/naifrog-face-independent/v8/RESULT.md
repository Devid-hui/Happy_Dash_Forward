V8 通过本轮有限范围的独立 geometry 检查。SOURCE 与实际 LOD0 GLB 各跑完 {0,.5,1}³ 的 27 个 Blink/Focus/Open 组合，非邻接严格内部交叉、退化三角形、相对 Basis 的面法线反向最大数均为零。没有由此判定视觉效果通过。

SOURCE 与 GLB 本轮范围完全相同：左眼 3150、右眼 3150、嘴 4150 个显式 FACE ROI 三角形，共 10450；加 canonical source vertex IDs 扩展的实际外围一圈 846 个，合计 11296。GLB Body 317303 个顶点与 606058 个三角形全部对应 SOURCE；坐标和三种 morph delta 最大误差均为零，顶点身份歧义为零，显式 ROI 完整映射。

真实双眼 front-cap 与前睑 front-annulus 的三角形投影交集上，平面高度差的实际最小 signed normal gap 同为 0.003081819661 m，即 3.081819661 mm。所有采样状态的投影重叠均达到名义 3 mm 间距，没有 cap 穿透。

方向诊断仍独立保留：最大新增共享边二面角 58.814544°，当前最大二面角 148.814928°；最多 126 条边满足“二面角大于 90°，且相对 Basis 新增大于 45°”的诊断条件。该诊断不等于 126 次面反向或严格自交。最严重组合为 Blink=1、Focus=0，与 Open 值无关。按实际 SOURCE FACE metadata 核对的报告前 20 个边例子，均在左眼 front annulus（section 1）与回封（section 2）的交界；不是 mouth。完整方向统计、实例与 metadata 归属保留在 report.json 与 edge-diagnostic-attribution.json，视觉判断仍须看实际闭眼造型。

方法没有改变：strict crossing 核心与 V6 执行版字节相同；固定 length 1e-8 m、退化面积 1e-12 m²、strict barycentric margin 1e-7；共享 canonical 顶点的邻接面排除，边/点接触不算严格内部交叉。同平面面积重叠单独分类。V8 checker 相对 V6 仅修复外围一圈的 canonical 身份扩展，两行；没有降低阈值。synthetic 10/10 已通过，实际检查由同一 kernel 执行。

冻结输入在检查前后 SHA 完全一致：

- SOURCE game_rig.blend: 6f60ab220e2b7c1385cb215a8cb9c01d9ee06cbe80b911627a457a0b778c1cb5
- 实际 LOD0 GLB: af1a219bc38eeb2d9447699544c3c2a10c7638b991e2c0084051fadb6d19ebca
- MODEL_MANIFEST.json: d36f662d98dbc76ad9e312d22a695b282a39f4055922cf60d1b14799843b9255

frozen-inputs/ 保存并再次逐个核对了这三份原始字节；frozen-receipt.json 记录原始和快照路径。executed-validator/ 保存本轮实际执行的脚本，report.json 为完整结果，summary.json 为紧凑汇总。

范围仅为明确眼口 FACE ROI 及 canonical 外围一圈、27 个 raw authored rest morph 组合，SOURCE 和 GLB 分别检查。不涉及骨骼动画、足底、全角色自交、连续时间或视觉验收。未修改生产输入，也没有启动 Godot。检查已经停止，producer 冻结 hold 已解除。
