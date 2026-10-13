# 左手整体自然度修复

本批次已经写入 Godot 项目并完成局部运行验证。目标是解决拇指根鼓包、虎口硬切、腕掌尖凹和手指扭曲，保持整根拇指向前、指腹贴器具、甲面朝外以及肘部低于腕和肩的走向。完整四阶段 goal 仍在执行。

## 改动与依据

实际检查 CC0 MakeHuman 原始网格／权重／关节标记、Blender Studio CC0 基础手和 Rain 官方源文件后，恢复中立皮肤与原始成熟权重，移除左手旧权重限幅、18 次平滑及 36 次普通 Smooth。整掌重新形成斜托弧线，拇指根无需独自承担旧版的大角度扭转；修正四指拟合的实际掌位置，取消用压缩皮肤掩盖错误抓握。原始甲面和右手形体保留。

导出使用标准中立 inverse bind 与带主握姿的默认关节变换，三种器具从中立解算，再转换到运行默认姿态。三档导出均核对实际 GLB 蒙皮，不把已经变形的手再次变形。Godot 对左手各材质统一线性顶点色，消除 body／nail 导入差异形成的暗锯齿。

肩肘保持正常两段方向。最新版实际稳托左肘弯曲约 60.76–63.84°，完全伸直为 0°；最大动态腕角 54.04°，55° 原界限未改。器具展示的转角与靠近位置收敛，保留器具接触与骨长。

## 可核验的结果

- 源母版 SHA-256：`06e36f74a2abbb3dda173b070c3431ed6a15d4f4d872958242597a3eab5e08dd`。
- 主 GLB：`e7834dfcb1367b77ac89d1365c0f3b43e83635f6e9ed20d33c98292e5830804c`。三档身份见 `production-sha256.json`。
- 手部契约 651 项、静态资产契约、谱灯玩法 37 项全部 PASS，没有引擎／脚本错误，见 `native-final/validation.json` 与相应日志。
- 同一资产的三个原生近景和 236 张实际动作帧全部为 1920×1080，捕获前后输入哈希一致。第一人称包含 idle、shot、flash、luminol、salt、mud，侧面包含举灯与收手。
- 独立完整器具手形审查：三种握姿各 210,816 个三角面无严格非相邻交叉。共享顶点、相切和共面情况不在这个结论内。
- 盐袋 solid-angle 全点检查发现封边最大 0.632 mm、袋身最大 0.072 mm 的浅重叠，不能称为皮肤／器具绝对零重叠。旧 4.17 mm 深穿插为单射线误判，独立复核和原始数据均保留。
- 右手中立／已变形顶点、完整权重、根变换及骨矩阵与保留基线差值为零。

最终独立报告位于 `../left-hand-independent-review/final-corrected/README.md`；同目录 `independent-final-summary.json` 对应这一冻结版本。

这组结果证明当前修复可导入并运行，且解决了本轮具体畸形。美术自然度通过实际图像判断，检查数量和面数不等于顶级商业质量。本轮为受控原生动画检查，尚未把它算作真人或普通输入的完整三报告逃生。

## 实际预览与恢复

近景：`native-final/closeups/front_side.png`、`underside.png`、`first_person.png`。完整第一人称序列：`native-final/first_person-motion.mp4`；左右侧序列为 `native-final/left-oblique-motion.mp4`、`right-oblique-motion.mp4`。原始帧与动作分段保留于三个视角目录。

最后扩大到现有 13 场景回归：12 场景及两次档案进程重启通过，奶龙场景有 4 项嘴部／开口形变失败；正式奶龙仍为旧版，候选未接入。输入哈希保持一致，详见 `integration-suite/validation.json` 及 `suite.log`。这四项失败保留为整体闭环待处理内容，不放宽门槛或把整套回归报为通过。

失败候选和修改前文件分别保留在 `production-before/`、`production-before-salt-release/`、`native-first-wrist-fail/`、`native-before-salt-and-nail-fix/`；不得把这些候选的检查混作最新版证据。

项目实现说明：`/Users/lpz/Documents/Happy_Dash_Forward/docs/implementation/LEFT_HAND_BINDING_REVIEW.md`。完整源实现与盐袋／材质修正分别见 `SOURCE_IMPLEMENTATION.md`、`SALT_AND_RUNTIME_NAIL_CORRECTION.md`。
