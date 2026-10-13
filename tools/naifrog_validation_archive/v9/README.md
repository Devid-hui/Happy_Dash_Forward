# V9 实际验证脚本快照

源文件、bytes、SHA统一见 docs/evidence/naifrog-model-v9/PORTABLE_INDEX.json。producer为作者确认实际执行的CPU/颜色/FLOAT检查；parser与uv为该轮检查依赖；render-floor保存真实GPU raster对照和V8几何身份比对；native保存3mm最终契约与actor文本；standalone保存真正应用导出及输出PCK probe。

这些字节快照不替代生产工具，也未在归档中重新运行。Blender脚本应以 --background --disable-autoexec 使用匹配冻结源；原有绝对默认路径保留，重跑显式指定实际输入。GDScript使用.gd.txt仅作快照，恢复到隔离项目运行必须由拥有引擎锁的任务执行。V8的27组合check只通过V9 geometry-identity对相同raw几何复用，未复用UV/动画/visual结果；详情与限制在证据README。
