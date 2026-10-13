# 四阶段交付证据缺口核对

只读核对当前 `docs/implementation/GOAL.md`、`work/implementation-state.json` 与现有具体回执；未运行新合同、图形程序、输入或导出。完整目标仍为 active。下述“已证明”只覆盖各回执实际范围。

## 已证明

- **UI／三槽**：`work/validation/stage1-ui-capture.json` 明确九张真实 Metal/Forward+ 1920×1080 受控界面图。历史七帧 CUA 操作记录证明三槽及拒绝第四项、死亡／重开、Esc 暂停、Tab 手册、36秒暂停冻结与回主菜单清理；它不是整局逃生。
- **九能力／成长／档案逻辑**：谱灯＋八项可选技能的已知合同，包括真实 World 科研模态24项、当前谱灯37项及核心成长／档案156项；跨进程档案 write/read 4＋3 项属于单独持久性证据。技能175项 fake 分发不替代所有能力的实际 World 施放。三报告、三个自主升级、三级上限及出口逻辑有合同证据。
- **手部／器具局部**：冻结06e36f74源/e7834dfc主GLB，651项手部契约、37项谱灯契约、静态检查及236张原生1080动作帧有身份一致的回执。左右手／姿态自然度不能由数量自动升级为商业美术接受；盐包局部0.632mm焊缝、0.072mm袋体微重叠已如实留证。
- **环境与静态当前事实**：树冠用户已认可，近中远10080/5040/1680叶、九母版和185株布局、4K PBR及LOD/暂停细节有合同与历史原生图。最新塔/报告源审计读到619860/1520636源polygon三角、83268/125512运行独立primitive三角，真实UV及2K/4K图像存在；CPU诊断图不算Godot画面。报告manifest身份已刷新而模型未变。
- **奶龙隔离技术与正式兼容补丁**：c3候选三档881467/254964/87277，24骨六clip，100063接口＋7878全顶点语义检查、185姿态40551840顶点评估通过，五实例资源共享/姿态独立、暂停/LOD/接地和保守盒有隔离证据。正式actor仅最小兼容已合入，hunter_rules/audit_regressions/smoke三项定向回归PASS；正式模型仍为旧版。
- **受控性能**：`outputs/performance-natural-hand-far-shadow/validation.json` valid、输入未变、无runtime errors；34.65/61.96/45.85 FPS是受控工作负载，不是普通整局，也不恢复已取消的60FPS硬要求。
- **旧资源包**：`work/export-audit/receipt.json` 只证明2026-10-12T16:16Z的ZIP/PCK快照导出、21个GLB/9贴图和隔离World加载46项通过；明确没有standalone `.app` 验收。资源包身份与最新手／报告／奶龙改动不同。

## 未完成

- **最终 UI 与能力输入**：最后角色／手部占屏后的九界面布局、真实焦点/失焦/滚动/输入恢复；九能力在正常玩家/World的实际施放、拒绝、反馈、逐级收益与科学边界逐项复核仍缺整合操作证据。
- **静态全场景美术／通行**：树、地表／积水／道路、塔、枯树、车、报告及器具须在最终同一雨夜场景核对暗场／谱灯／闪电、近远LOD、材质受光、碰撞和三地标可达。现有GLB/源/合同/CPU图证明制作或功能，未证明用户新商业精度门槛。
- **动态与生命周期**：最新手部局部通过后，最终所有工具、技能、状态动作、死亡/重开/场景释放及普通输入要在最终资产组合重新核对；13场景套件尚未全通过。
- **奶龙最终美术及正式三档接入**：闭眼C形眼周与v5共边原型仍在修；UV/PBR R22未完成，当前Body/lids/oral主要为VCOL＋PBR因子，whole-body xatlas仍live，不能记真UV已完成。新三档尚未替换正式旧模型；需要最终美术、多视角/六动作图形、五实例真实场景与视野边界验收。
- **真正三报告逃生**：`native-escape-input-interim` 实际仍reports=0、game_clock≈5.41、死亡/暂停；第二次因Mac锁屏没有输入，1021行observer时间线不代表路线执行。静态15段路线是可通行推导；progression_world直接禁hunter/移动player的合同不是普通输入逃生。仍缺三个正常E、三个正常强化模态、出口E以及reports=3/pending_upgrade=false/game_over=true/outcome=胜利的连续真实事件/画面链。
- **最终回归／打包**：最后正式资产及材质接入后，完整13场景与档案进程重启须重新跑通，再生成新的可运行macOS应用及ZIP/PCK，并以实际包内资源、独立启动/普通输入/档案重开核对；旧快照不能称最新完整交付。本次只读范围没有可用的最终 `.app` 验收证据。

## 旧记录矛盾与需合并的表述

- GOAL开头仍写“目标为稳定60 FPS”，后面的用户修订与R20已经取消硬门槛。应统一开头，不能把性能未达60继续列为阻塞。
- GOAL阶段2及“被质量否定的当前批次源文件”仍泛称现有四源/四GLB为中面数旧批；实际已有新高精手部和塔/报告母版审计，不能将它们回退描述成早期四文件。当前制作事实和最终美术未验收应分开表达。
- implementation-state 的 `last_verified_integration.native_performance` 仍说未测量，而 `current_art_revision_20261013.valid_measured_performance` 已有有效受控实测。旧34项谱灯/147项成长应作为历史；当前37/156记录已明确。
- `last_goal_turn_classification` 仍写早期手掌前向候选、LBS/DQ比较，最新goal-turn审计已转正式actor适配＋v5/UV工作。旧单条不应代表当前状态。
- R18“最终奶龙与动画边界未验收”应注明**隔离技术边界已证明、正式新资产与最终图形/Director整局仍未验收**；不能从headless PASS跳成美术/整局PASS。
- 最近完整套件是明确 **12/13，exit1**，失败为旧正式奶龙的四项口腔/中远morph要求；不是13/13。后来正式actor的三个定向回归及新资产隔离PASS没有替代该完整套件。
- 旧13张World图首两帧被focus pause/HUD刷新污染，记录已声明diagnostic和需复捕；不能当最后场景图形验收。旧ZIP/PCK约773/777MB、46加载检查只对应旧快照，原资源清单中报告4744面/塔28616面与当前125512/83268不一致就是版本差异，不应误称资源丢失。

关键回执：`work/validation/stage1-ui-capture.json`；`outputs/left-hand-clean-repair/native-final/validation.json`；`outputs/left-hand-clean-repair/integration-suite/validation.json`及suite.log；`outputs/static-quality-review/README.md`；`outputs/nailong-runtime-isolated/PATCHED_RESULT.json`和production-adapter-checks/validation.json；`outputs/native-escape-input-second/validation.json`；`outputs/native-escape-route-research/README.md`；`work/export-audit/receipt.json`及native-load-receipt.json。未追加代码、测试、导出或GUI进程。
