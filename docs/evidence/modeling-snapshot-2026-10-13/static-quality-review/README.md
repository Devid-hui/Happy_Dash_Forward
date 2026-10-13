# 当前静态资产核对

本轮读取了当前 GLB 和可编辑母版，补足早期记录与真实文件之间的差异，没有重建或替换已完成资产。

| 资产 | 当前母版基于实际 mesh polygons 的三角数 | 当前 GLB 独立 primitive 三角数 | UV / PBR证据 |
| --- | ---: | ---: | --- |
| 输电塔 | 619,860 | 83,268 | 18源mesh均有UV；20运行primitive有UV0与NORMAL，8PBR材料、6图像 |
| 科研报告 | 1,520,636 | 125,512 | 15源mesh均有UV；15运行primitive有UV0与NORMAL，5PBR材料、6图像 |

以上母版统计来自保存网格的 polygons，不声称包括未应用的几何modifier；GLB统计沿用独立primitive口径，不是所有实例或同时提交的三角量。源文件渲染前后SHA一致，`current-source/source-audit.json`保存对象、UV层与图像尺寸，`current-glb-inventory.json`保存实际导出属性。源贴图有2048与4096尺寸。`current-source/*-current-source.png`是新生成的Cycles CPU诊断图，不能冒充Godot或原生整局画面。

塔的实际制作函数使用L截面角钢、节点板／螺栓、瓷绝缘片、线缆与检修梯；报告母版包含分层纸张、书脊、装订线、真实封面及箔字。图像显示当前形体与材质，数量／UV存在并不等于商业美术已验收。最后仍需同一游戏场景的受光与通行检查。

报告的ASSET_MANIFEST保留了旧导出SHA。本轮使用既有`glb_info`读取当前所有POSITION并确认finite，仅刷新报告这一条身份；125,512三角数量不变，没有改变GLB或母版。修改前manifest与差异回执分别保存在本目录。

本轮额外检索到[Poly Haven Modular Electricity Poles](https://polyhaven.com/a/modular_electricity_poles)，其[官方许可](https://polyhaven.com/license)为CC0。它是木质模块电杆及相关电气附件，可作为部件／材质研究候选；不是四脚角钢输电塔。未下载、未执行、未移入本项目，不把检索结果算作模型改进。

图谱实际使用受支持的codebase-memory-mcp CLI Verify，generation `2026-10-13T00:00:38Z`；四路径coverage metadata_match/no_recorded_issue，塔与报告实际函数已精确读取。这个best-effort结果不是索引完整性证明，二进制模型及图像用实际文件补证。
