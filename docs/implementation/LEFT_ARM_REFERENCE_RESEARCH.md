# 左臂与举灯：公开资源核查及当前实施

核查日期：2026-10-13。用户要求左臂弯曲和举灯动作重做，并规定后续建模先找开源源文件与指导教程。

## 结论

本轮有针对性的资源已经取得并核查。成熟生产骨架与官方求解器共同提示：手掌与道具接触、肘的弯向、前臂绕长轴旋转、肩肘动作轨迹须分别组织。细分网格与缓动曲线本身不能修复这几项关系。

| 资料 | 实际核查 | 用途 |
| --- | --- | --- |
| [Rain 官方角色源文件](https://studio.blender.org/characters/rain/v3/) | 67,579,177 字节公开包已下载；Blender 4.5.14 禁止自动执行后打开成功；官方 CC BY 4.0，保留署名要求 | 已看到独立手目标、肘 pole、肩／锁骨控制、两段前臂变形骨。作为结构参考；没有举灯动画，不整套搬入游戏。 |
| [Godot 4.7.2 二骨 IK 源码](https://github.com/godotengine/godot/blob/ed1daf0bf001b61586d9930840f2f1394092c079/scene/3d/two_bone_ik_3d.cpp#L780) | 固定 tag/commit 已下载完整源码并检查；引擎 MIT | 核对可达范围、固定骨长、pole 和 roll，发现现自定义 solver 的越界条件风险。 |
| [Godot 官方 IK 演示](https://godotengine.org/article/inverse-kinematics-returns-to-godot-4-6/) | adjusted-ik ZIP 实际下载、解包检查 scene/script/GLB；未声称运行演示 | 范例是 Aim→FABRIK→手掌旋转→TwistDisperser；借鉴职责和顺序，没有直接使用示例模型。 |
| [CloudRig 官方组件指南](https://studio.blender.org/tools/addons/cloudrig/cloudrig-types) | 核对 Chain IK、肘轴和 bone roll 指导 | 统一肘弯曲平面与骨轴，避免长轴旋转任意漂移。 |
| [Shawn Kelly 持物动画教程](https://www.animationmentor.com/blog/how-to-animate-your-character-when-hes-holding-a-prop/) | 已读作者正文，仅参考方法 | 即使 IK 手被道具控制，画面仍应呈现肩带臂、臂带腕；抬入和回落需要有意设计。 |
| [动作重叠与收势教程](https://www.animationmentor.com/blog/tutorial-animate-overlap-and-follow-through/) | 已读作者网页，未声称逐帧观看完整视频 | 主轨迹与从属部位安排有限错时，避免所有部位同一插值值机械同步。 |

许可边界：公开教程与可商用源资产区别记录；未把教程图片、演示枪模型或完整 Rain 导入游戏。其源码/素材版本与校验记录保留于任务 work/。

## 已经实施和实测的部分

左袖源形体改为腕—肘、肘—肩两段近直轴，只在肘附近保留短圆角；腕与肘混权局限于局部，避免整条袖管变成 S 曲线。源检查在肘3厘米之外测得袖环中心到骨轴最大误差约2.84e-8米；右手皮肤、右袖与右袖口源顶点与上一版相同。

举灯表现改为抬入、稳托、回落，再在退场后隐藏；总1.10秒和24/44/32分段是项目候选，来自本次实现选择，不是教程规定的标准。未改立即耗能、命中和冷却。

已在实际 Godot 4.7.2 / Metal 4 / M4 Pro 窗口捕获158帧1920×1080完整动作，包含flash结束后的idle，进程退出0且无运行错误。逐帧检查的上、前臂长度偏差均小于0.000001米；当前已测动作未触发源码审查指出的越界拉伸。该风险仍适用于其他不可达目标，不能称solver对任意输入都正确。

视觉检查已看到旧的整臂S弧消失、肘部位置明确。当前中途弯肘的布料转角仍偏硬；肩肘主动感、前臂roll分配和最终托灯造型仍须以连续实帧判断，不能由长度数字或测试数量替代外观验收。

完整158帧与逐帧关节回执位于任务 outputs/left-arm-articulation/motion-initial/；视频 left-arm-motion.mp4。该预览为受控原生动画，关闭了诊断场景TAA，不是普通游玩录屏；正式渲染配置未改。

## 后续工作约束

按 MODELING_RESOURCE_FIRST.md 执行：先公开资源与教程，核对并实开源文件，决定复用或改造，再做最小可见样例和原生验证。本次研究完成不等于用户已接受左臂，整个四阶段目标继续保持 active；强制60FPS已按用户要求取消。
