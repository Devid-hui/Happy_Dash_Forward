# 当前界面与真实科研手册内容复核

本轮重新运行现有UI契约，实际Metal4／Forward+／M4 Pro渲染九张1920×1080界面：菜单、选科、设置、档案、HUD、暂停、手册、强化、结局。当前源码哈希在运行前后相同；UI CONTRACT PASS，无SCRIPT ERROR／ERROR。该契约使用FakeWorld资源值和程序信号来检查布局／三槽／重复提交，不能作为普通输入或完整逃生证明。

现有契约手册只有一段短示例，不能覆盖本轮修正的真实科学／效果／代价文字。因此增加聊天目录内的外部渲染审阅脚本：注册autoload后载入既有ReviewWorld，调用实际World.toggle_handbook，让生产代码生成谱灯与八项技能的完整内容。分别设置基础与精修两档，按官方ScrollContainer.ensure_control_visible逐项滚到可见区；18项完整条目均在滚动视口内，无横向截断。同步HUD后重新渲染，真实电池100及当前装备／等级与手册一致。

实际生产内容图及回执位于 `actual-handbook-synced/`，九界面图与契约回执位于 `contract-ui/`、`contract-validation.json`。root实际看过选科、强化，以及泥区基础、蓄昼精修、谱灯基础等具体图；尚未据此宣布普通键鼠／焦点／失焦和最终角色整局通过。

为使受控图片稳定，沿用现有ReviewWorld的窗口焦点覆盖，冻结玩家、追猎者、Director和Storm的物理／更新。程序通过真实手册方法与滚动API进入状态，不注入键盘／鼠标。场景背景仍为当前正式旧奶龙，不是最终新角色图形验收。

两次外部审阅脚本失败已保留：外部--script在compile阶段无法解析项目autoload GameState；预加载依赖也过早。随后按实际启动顺序，先取root的已注册GameState、再运行时载入既有ReviewWorld，源码不需修改。最初18张已正确显示条目，但背景HUD因直接设置等级后未刷新而过时；原图保留在actual-handbook，最终使用显式update_display后的actual-handbook-synced。失败和未选图不冒充最终通过。

API依据：[Godot ScrollContainer](https://docs.godotengine.org/en/stable/classes/class_scrollcontainer.html)、[Godot Script](https://docs.godotengine.org/en/stable/classes/class_script.html)。项目结构使用codebase-memory-mcp CLI Verify代际2026-10-13T01:19:59Z，相关6路径metadata_match；UI查询53／53分页完成。动态图/API关系另读实际源码，外部新审阅脚本明确在图谱项目之外。
