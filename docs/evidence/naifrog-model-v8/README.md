# 奶蛙 V8 验证证据归档

归档保留原始报告字节、历史路径、实际执行脚本与 SHA256。PORTABLE_INDEX.json 将源文件映射到仓库相对路径，所有复制逐个核验；没有重写原始报告。此目录与 tools/naifrog_validation_archive 是本归档的全部仓库写入范围，未改模型资产/actor/runner，也未执行 Git。

- full-v8/：10 张最终 CPU 图、真实脚底/三档 GLB/UV 色彩采样/全 FLOATAccessor 有限性报告，以及完成的 producer 日志。CPU 图不能代替原生画面。
- naifrog-native-v8/：实际 Godot 导入、3853 checks / 276 states / 37835000 vertex evaluations、预览与运行回执，全部 PASS。覆盖的是报告所列实际状态/完整顶点，而非无限连续时间或整局通关。
- naifrog-face-independent/v8/：SOURCE 与 LOD0 GLB 各 27 个 raw rest morph 组合的完整 report、summary、RESULT、边诊断归属与 frozen receipt。限定眼口 FACE ROI 和 canonical 外围一圈；严格交叉/退化/相对 Basis 法线反向均为零，最小 front-cap 间距为 3.081819661mm。闭眼前睑与回封交界的二面角诊断仍保留，未写成商业级美术验收通过。
- naifrog-face-independent/v6/、repair-history/：V6 的失败、两个独立算法的穿面 witness，以及 V6 构建上下文/V7 UV region 错误日志。V6 不能被当前 V8 替代，也不能把 V6 范围差异冒充同样覆盖。
- naifrog-contract-review/：原始测试方案、PackedFloat32Array API 错误及三行修复回执。该目录文中的 pending 是当时状态；后续 V8 PASS 以 naifrog-native-v8/ 的真实回执为准。
- naifrog-face-independent/kernel-probes/：算法合成/初步探针；这些不是 V8 整模验收。

实际 checker 快照在 tools/naifrog_validation_archive/independent-face-v6、independent-face-v8；两版 strict kernel 保持原字节。parser 2853f1b8… 与两版 report 输入身份一致。producer CPU/UV 诊断与 FLOAT accessor 脚本也保留。UV 全图独立 checker 已冻结，归档时最终 V8 运行尚未完，不把小型 helper probe 记成最终模型证据。native actor 候选 SHA 已与 V8 运行回执核对；native contract 是当前修复后的源码快照，原运行 report 未单列 test-script SHA，因此不补造该原始字段。

正式 V8 source/LOD0 二进制已在 source_assets/naifrog/model 与 assets/refined/naifrog，按 frozen receipt 再核 SHA，PORTABLE_INDEX 的 existing_formal_v8_binary_references 记录对应关系，未复制大二进制。V6 冻结大二进制按归档范围排除；其 manifest/report/witness/脚本完整保留，但不能承诺仅靠本归档重跑 V6 全模型。19 张现有真实 1080p 原生图保留在 docs/previews/naifrog，此处不重复复制。

.log 文件只追加 .txt 后缀，字节保持不变。Runtime、下载、缓存、pyc、blend1 和大量迭代图/源均未复制。归档时仍等待最终 UV 全图报告/完整日志与 game-source-contract/inspect 完整回执，具体待补项列于 PORTABLE_INDEX。根任务可在两项真正结束后追加，不能把运行中的文件当最终结果。

## V8 历史收尾状态

已补入全部完成的 game-source-contract/inspect、UV判重/世界位置诊断以及full-production-suite/接触阴影预览日志。V8原生3853 checks、276 states、37835000 vertex evaluations通过，生产13场景合同及两个archive restart进程通过；源数据contract完整且通过。UV全图检查 complete=true、ok=false、status=overlap，24对均在同臂区域（region4 7对、region5 17对），跨区域0，不能写全通过。站立支撑基线约0.014m位于原+0.015m合同内，但不是精确贴地。闭眼二面角诊断继续保留，不能称商业美术通过。

先前文中的运行中/pending描述是归档建立时状态，现以本收尾段和PORTABLE_INDEX.historical_v8_status为准。V9修复与新报告由根任务另行记录，不扩入本归档。当前正式二进制路径是历史链接而非不可变V8副本，index列出收尾时当前SHA与是否仍匹配。大型冻结源/GLB未重复复制，V6输入二进制未归档；因此完整性限于所选有效证据/脚本/图像，不承诺仅靠本目录重跑全部历史模型。Godot自动生成PNG.import源侧导入设置已单列，不当作复制回执或新验证。
