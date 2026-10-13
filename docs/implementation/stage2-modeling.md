# 第二阶段资产与器具动态交接

> 状态修正：用户实际查看后明确认为这一批仍粗糙、未达到新的商业近景与高面数要求。本文件记录的是被否定的中面数批及当时的独立合同；REFINED_* 与合同 PASS 均不能作为当前建模完成或商业品质验收证据。新母版/原生候选由 tools/build_high_fidelity_assets.py 生成，仍需逐图与整合游玩核对。

静态模型由原始程序形体制作、可编辑 Blender 源和原生 Godot 导入组成。未使用外部模型、纹理或全球 Blender 安装。模型交互与碰撞位置沿用既有 World；新增地面细节无碰撞。这里的独立素材验收不能代替整合后的雨夜游玩与性能验收。

| 资产 | 现已实现的结构 | 文件 |
| --- | --- | --- |
| 森林 | 连续扫掠根干、弯曲主枝与分叉、带中脊的叶片与枝梗、终梢叶簇；六变体和活/枯差异；共享网格与材质，近景树皮/叶两批，远景两批。保留树干圆柱碰撞。 | `scripts/art/forest_detail.gd` |
| 地面 | 程序湿泥、随机细颗粒/粗糙度、贴地落叶、弯草、灌木、石块与不规则积水；16 m 空间分区，避免全地图一个叶批。路线附近排除石块/灌木；总目标数量与实际生成数量分别记 metadata。 | `scripts/art/terrain_detail.gd` |
| 输电塔 | 斜格构、支承横担、连接板与紧固件、瓷碟绝缘子、基础与爬梯、真实下垂八线缆。适当同材质组已合并。 | `assets/refined/power_tower.glb` |
| 枯树 | 连续根干、分叉、独立深裂缝、碎裂断梢与风化材质，保留 `BleachedTrunk` 节点。 | `scripts/props/landmark_models.gd` |
| 废车 | 连续截面车身、真实轮拱开口、倾斜车窗、四胎/轮毂、门缝、弯曲引擎盖、散热格栅、锈蚀与破裂挡风玻璃。 | `assets/refined/abandoned_car.glb` |
| 报告 | 封面、页块、圆书脊、24 纸页侧线、研究烫金/图记、标签与弹力带，中文封面与交互为原生 Label3D。`highlight(duration=7.0)` 到时恢复材质。 | `assets/refined/research_report.glb`、`scripts/props/research_book.gd` |
| 科研谱灯与器具 | 连续旋转光学壳与凸透镜、金属压圈/散热、真实连接的储能壳、握柄肩/扳机保护、服务侧板及紧固件、拇指可及模式控制、显示模块、试剂瓶、封口盐包和泥罐。 | `assets/refined/field_equipment.glb` |
| 手部与动作 | 两手各 17 骨骼与加权掌/指/指甲；袖口接连续雨衣前臂。常态右手握持，爆发另一手支撑；点射反冲、食指按扳机、拇指切换/模块操作，三种器具的掌骨倾斜及手指释放。 | `scripts/player/field_equipment.gd` |

`source_assets/*.blend` 保留独立形体、UV、材质、权重和骨骼；`.gdignore` 防止 Godot 自动转入 Blender 源，正式游戏只用 GLB。`tools/build_field_assets.py` 为可重复制作配方，`assets/refined/ASSET_MANIFEST.json` 记录最终网格统计与来源。

森林 39 m 左右采用近/远表现，四米边缘范围用 Forward+ 的 `VISIBILITY_RANGE_FADE_SELF` 做渐变。Godot 官方说明此模式比硬切换慢，并只在 Forward+ 有渐变效果，最终采用成本必须由整合后的 1080p 性能测量核对。[GeometryInstance3D 官方文档](https://docs.godotengine.org/en/stable/classes/class_geometryinstance3d.html#class-geometryinstance3d-property-visibility-range-fade-mode)

## 精确接入

```gdscript
var details := preload("res://scripts/art/terrain_detail.gd").build(731)
add_child(details)
# 原地面保留碰撞，仅换外观：
floor.material_override = preload("res://scripts/art/terrain_detail.gd").ground_material()
# World 用实际 gameplay elapsed 驱动；暂停/失焦/强化时不要继续此时间。
preload("res://scripts/art/terrain_detail.gd").set_motion_time(elapsed)
preload("res://scripts/art/forest_detail.gd").set_motion_time(elapsed)
```

FieldEquipment 不控制电量、冷却、命中或技能成功。Player 在真实成功/切换后传 `trigger(kind)`，正常运行时传 `tick(delta, movement, sprinting, boost, noise)`。支持 `flash/shot/mode/light/capture/boost/afterimage/echo/luminol/salt/mud/filter`，`filter` 归一为 `infer`。`set_mode(bool)` 更新模式并播切换，`set_level(int)` 更新实际谱灯等级。`beam_socket` 给出真实透镜前的光源连接点，随模型和动作移动。它位于谱灯本地 `(0, 0, -0.269)`，供真实 Spotlight 连接。第一人称设备基位为相机下 `(0.33,-0.13,-0.85)`，资产比例 0.84；世界资源逻辑由 Player/World 保持。

支持动作被新动作打断时立即清理旧器具/支撑姿态；手指和掌骨在动作结束恢复中立。谱灯状态的发射核心与感知/模式显示材质在各实例内独立。植被 shader 已去掉内置 `TIME`，只读 `motion_time`，因此不会在 CPU 暂停后继续风摆。

## 实际验证证据

- Blender 4.5.14 LTS `62c1db4208e8` 运行时 RNA 已核对 glTF 参数；四份 `.blend` 保存和四个 GLB 导出实际完成。
- Godot 4.7.2 原生导入成功。`tests/static_assets_contract.tscn` 通过且无 warning/error；覆盖近远共享资源、树碰撞、局部分批边界与无碰撞、四轮/八缆/页书脊保留、标亮恢复、双手骨骼、真实关节按动/恢复、动作打断清理和器具可见/隐藏。
- `tests/static_assets_preview.tscn` 用 Apple M4 Pro、Metal 4.0、Forward+ 原生生成 11 个 1920×1080 固定视角，正常退出。逐图检查了车、塔、活树、枯树、报告、单手谱灯、爆发支撑、试剂、光学前视、盐布设和泥投放。
- 原第一版发现近景谱灯裁掉右手、紧固件浮空、梢部稀缺、盐动作把前臂端抬入视野。实际修正后复查：右握/袖口可见且保持路线空间，紧固件/铭牌贴壳，终梢覆叶，布设只倾斜掌骨并限制前臂角度。第一版证据留在任务 `work/stage2/preview_iteration1`，最终图为 `docs/previews/REFINED_*.png`。

独立素材预览证明形体/连接和器具动作可被原生渲染观察。暗处路线、实际谱灯光束、闪电、雨幕、完整技能成功/拒绝、重开、五奶龙及 60 FPS 验收仍需根代理在正式 World 中核对。本交接不将独立图或三角数当作整个第二/第三阶段验收已完成。
