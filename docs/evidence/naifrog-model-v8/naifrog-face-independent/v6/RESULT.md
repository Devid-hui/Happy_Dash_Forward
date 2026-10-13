V6 未通过独立眼口几何验收。SOURCE 和实际 LOD0 GLB 的 27 个静态形变组合中，9 个 Open=1 状态均有 84 对非邻接严格内部三角形交叉；18 个 Open=0/.5 状态为零。所有采样状态退化三角形为零。

首对 SOURCE loop-triangle 288574/605560 对应 mesh polygon 144287/302906。前者是 mouth 周围的原始外皮连接区，后者是显式 mouth patch。另一个实例是 polygon 144287/302907。独立 edge–plane 算法复核的 10 对全部有两个严格穿面见证；首见证的对方三角形重心坐标为 (0.368293789, 0.241726508, 0.389979702)，排除了仅共边、点接触及闭口近接触的解释。具体顶点、位置及 edge parameters 见 crossing-witnesses.json。

Body 原始 FACE INT 区域为左眼 3150、右眼 3150、嘴 3700 三角形，共 10000。SOURCE 加入真实外围一圈 818 个三角形，共检查 10818；GLB 本轮加入的一圈是 483，共 10483，因为该版检查器以导出后的原始 UV 顶点身份扩展一圈，未跨 UV 重复点扩展。下一版检查器已改为 canonical source vertex IDs；本轮结果及已执行检查器已单独保留，未伪称这两个一圈范围相同。实际 GLB Body 315081 顶点和 606610 个三角形全部匹配 SOURCE，坐标与三种 morph delta 最大误差均为零，身份歧义为零；显式 10000 个 ROI 三角形完整匹配。

双眼真实 front-cap 与显式 front-annulus 的投影三角形交集，使用其平面高度差在所有交集多边形顶点求最小值，涵盖三角形内部。所有 27 个组合未发现 cap 穿透；SOURCE 与 GLB 的最小 signed normal gap 同为 0.002981785274 m，即 2.981785 mm。因此不能宣称所有实际离散面严格满足名义 3.000 mm 间距。

面方向诊断独立于交叉检测：Open=1 时有 713 个面相对 Basis 法线反向；Blink=0、Focus=1、Open=0/.5 时有 148 个；组合后最大 861。共享边最大新增二面角为 112.644896°。这些是几何方向变化记录，不单独当作连续时间或视觉褶皱证明。

范围仅为 {0,.5,1}³ 的 27 个 authored rest morph 组合、明确眼口 FACE ROI 及上述外围一圈，SOURCE 与 GLB 分别检查。没有检测骨骼动画、足底、全角色自交、无穷时间或视觉效果，没有启动 Godot，也没有修改生产资源。strict crossing 使用固定长度 1e-8 m、退化面积 1e-12 m²、严格 barycentric margin 1e-7；共享任何真实 canonical 顶点的邻接三角形排除，边/点接触不算严格交叉。同平面面积重叠单独分类。synthetic 10/10 与 cap synthetic 3/3 均通过。

三份输入的检查前后 SHA 完全相同。frozen-inputs/ 中保存并重新校验了 SOURCE、GLB 与 manifest 原始字节；frozen-receipt.json 记录身份。executed-validator/ 保留本轮实际执行的脚本。完整状态、例子和范围见 report.json，紧凑汇总见 summary.json。
