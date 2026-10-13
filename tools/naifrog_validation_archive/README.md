# 奶蛙实际验证脚本归档

这些是逐 SHA 保存的验证/诊断脚本，独立目录不会替代生产 builder、actor 或测试。源→仓库路径、字节与 SHA 统一见 docs/evidence/naifrog-model-v8/PORTABLE_INDEX.json。

independent-face-v6 与 independent-face-v8 保存该轮 executed-validator 原件；strict_triangles.py 依赖 NumPy，check_frozen_face.py 通过 Blender 的 bpy/NumPy 执行。建议 Blender 4.5.14 --background --disable-autoexec SOURCE.blend --python CHECKER -- --manifest MANIFEST.json --glb MODEL.glb --parser tools/naifrog_validation_archive/parser/naifrog_inspect.py --out OUTPUT。原始默认参数可能有历史绝对路径，保留而不静默重写；重跑必须显式给当前输入。V6 冻结大二进制未纳入本归档，当前正式 V8 不能代替。

producer/ 保存作者确认实际执行的 CPU 渲染、表面→UV→PNG 采样和全 FLOAT accessor 审计脚本。uv/ 保存冻结独立 UV 全图检查器：标准库、Blender 内置 bpy/NumPy，实际执行报告另查证据目录；它不是本身就能证明 V8 通过。native/ 的 .gd.txt 是源码字节快照，用文本后缀避免在生产编辑器里作为额外脚本导入；actor SHA 绑定原生回执，contract 身份说明见证据 README。
