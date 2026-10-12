# 外部素材与模型说明

## 奶龙追猎者

追猎者视觉由 `scripts/enemies/hunter.gd` 里的低多边形 3D 网格构成：圆腹、长颈、大头、张嘴、短牙、黑手脚和绿色眼睛。它不是一张始终自发光的平面图，因此会被玩家近光、环境暗部与闪电方向光真实照亮。黑暗时只保留很弱的眼部自发光和眼部反射光，闪电时能看到完整身体。碰撞、AI、声音调查仍由 `CharacterBody3D` 与追猎者脚本管理。

旧的透明像素图 `assets/nailong/nailong_pixel.png` 仍保留为美术参考；它不再是运行时怪物模型。想换成完整角色模型时，将 `.glb` 导入后替换 `_build_model()`，保持根节点结构与碰撞体、AI 分离。

## 森林素材

`assets/forest/` 收录 Kenney Nature Kit 的 6 个 COLLADA 低模树模型，在运行时随机散布，并由深色材质覆盖以适配夜间场景。源素材和许可记录见 `assets/forest/ASSET_LICENSE.txt`。

- 来源：[Kenney Nature Kit](https://kenney.nl/assets/nature-kit)
- 许可：CC0 1.0
- 树群避开出生点和主要地标；加入的碰撞体阻止玩家直接穿过树干。

## 雨声

`assets/audio/rain_loop.ogg` 和 `canopy_rain_loop.ogg` 是两条不同的实录雨声循环，分别作为远处雨幕底噪与近处树冠雨声，音量和空间距离不同。来源及许可记录见 `assets/audio/ASSET_LICENSE.txt`。

- 来源：[OpenGameArt — Rain (loopable)](https://opengameart.org/content/rain-loopable)，Ylmir
- 许可：CC0

## 雨滴效果

雨线由 GPU 粒子生成，摄像机附近保持高密度。落地时通过 Godot 的 `GPUParticlesCollisionBox3D` 碰撞与粒子子发射器生成短暂飞溅；湿地使用低粗糙度材质，在光线掠过时出现反射。雨粒、飞溅和地面反光均通过程序材质/网格完成，不依赖外部插件。

Godot 官方实现资料：[GPU 粒子](https://docs.godotengine.org/en/4.7/classes/class_gpuparticles3d.html)、[粒子子发射器](https://docs.godotengine.org/en/4.7/tutorials/3d/particles/subemitters.html)。

## 2026-10-11 模型细化

- `scripts/art/organic_mesh.gd`：项目自制连续扫掠曲面，控制点间使用 Catmull–Rom 插值（利用相邻四点生成平滑弯曲）。统一用于肢体、树干、树枝、树根。
- 奶龙：连续躯干和颈部、唇缘、双排牙、眼窝、鼻孔、四指弯曲手掌、三趾脚掌；皮肤使用空间固定的程序斑纹。没有骨骼动画或写实雕刻。
- 森林：95 棵自制细节树，包含根、弯枝、分叉、针叶片及沟槽/苔藓材质；另外 90 棵保留 Kenney 素材原有表面材质。中央和地标之间预留路径。
- 1400 片落叶使用 MultiMesh（同一模型批量绘制，减少绘制调用），另有倒地枯枝。
- 以下来源用于研究和制作参考，本次没有下载或集成 Poly Haven 素材：
  - https://polyhaven.com/collections/pine_forest
  - https://dev.epicgames.com/community/learning/tutorials/XYeP/unreal-engine-5-forest-path-tutorial-full-workflow-breakdown
- 当前程序模型仍属于风格化制作，针叶片和皮肤细节不等同于摄影扫描资产。

2026-10-12：奶龙模型代码拆到 `scripts/enemies/hunter_visual.gd`；冲刺预警声音由 `hunter_voice.gd` 程序合成，无外部录音授权依赖。
