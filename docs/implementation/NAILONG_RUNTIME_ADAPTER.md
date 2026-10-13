# 重建奶龙的运行适配

当前正式模型文件仍是旧版。新版c3f08b4b源与三档GLB在隔离项目中完成实际Godot4.7.2导入和185姿态检查；模型替换与图形美术验收尚未完成。

本轮已将两项必要适配加入正式`hunter_visual.gd`，保持既有24骨／六动画、缓存、LOD、暂停恢复和Director接口。

## 联合眼皮权重

旧移动恢复逻辑会为所有带`Focus`的mesh强写`.22`。新眼皮使用`LidBxxxFxxx`及`Blink/Focus`端点声明联合格点；单写Focus使其权重和由约1升到1.22。该已测状态没有角膜穿透，实际问题是作者凸组合语义被改变。

适配按实际ArrayMesh的targetNames识别这种声明，保持新眼皮的作者动画；其余Body／OralBag Focus和头／腹疲态保持原逻辑。旧版只带普通Blink／Focus的mesh不会被此判断跳过。

## 同一个完整边界盒

新版三档185原生姿态的全顶点union为`(-1.193482,.004868,-1.173552)`至`(1.184975,2.758051,1.075285)`。隔离盒加0.10m余量并向外取整到厘米。正式代码又与旧保守盒合并，保留旧盒整个范围，得到：

```gdscript
AABB(Vector3(-1.30, -0.13, -1.28), Vector3(2.59, 3.15, 2.46))
```

它同时用于mesh `custom_aabb`和`get_animation_bounds`。这次不更换物理碰撞、导航或目标选择，也没有给渲染与Director分别建立不同的边界。

## 实际验证与边界

正式源修改后重新导入成功，`hunter_rules`、`audit_regressions`、`smoke`三个既有行为场景全部PASS，零引擎／脚本错误，检查前后脚本和三GLB输入哈希一致。证据位于当前聊天`outputs/nailong-runtime-isolated/production-adapter-checks/`。

隔离新资产已经通过五实例共享资源且姿态独立、24骨六动画、三档LOD、暂停恢复和全顶点形变。这个HEADLESS结果不等于实际图形美术／整局验证；闭眼侧面C形过渡、局部共边原型与实际UV／贴图仍在处理。正式新模型和最终运行包尚未交付，完整goal仍active，60FPS硬要求已由用户取消。
