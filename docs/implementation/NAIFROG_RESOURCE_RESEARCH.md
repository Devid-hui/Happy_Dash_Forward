归档说明：以下为实际研究时的报告；公开证据和源文件现已复制到 `source_assets/naifrog/reference_research/`，历史复现命令需要改为该目录及本机 Blender 路径。源文件没有被修改，转换后的研究 GLB 仍未作为游戏成品接入。

# 新奶蛙公开资源与建模教程研究

核验日期：2026-10-13。此次只做公开来源、许可、下载源文件、Blender 数据及导出样本检查；没有制作新奶蛙，没有改动生产仓库，也没有 stage、commit 或 push。

**结论：本次未核到与用户新照片同款、许可清楚、带可编辑绑定源文件的高精游戏奶蛙。** 已实际下载的 CC0 通用蛙可用于研究骨骼、UV 与 Actions；外形和精度不足以成为最终角色。推荐按新照片专门制作角色网格、材质与变形，参考已核教程的工作方法，并在接入时遵守主任务核查的现有游戏接口。

## 新参考的造型边界

已实际查看[用户参考图](../previews/naifrog/PRIMARY_REFERENCE.png)。它表现为小头与短颈过渡、宽梨形黄色躯干、面积很大的浅米白肚皮、站立的双腿、深橄榄色手掌与脚，以及位于头部上方的双眼。参考里没有可见尾巴。原奶龙的大头、短腿与圆尾轮廓已失去参考依据。

原图分辨率只有 144×257，能决定主要轮廓与色块，不能证明背部、脚趾数量、手指构造和精细嘴部结构。后续侧面与背面设计须明确作为创作补全，并逐视角核对；不能把补全结果说成原图已显示的细节。

## 中文“奶蛙”资源：已核范围与缺口

搜索覆盖“奶蛙 3D 模型 blender 源文件 开源”“奶蛙 模型 3D”“奶蛙 blender 下载”“奶蛙 开源 模型”和 `filetype:blend`。以下均是作者或平台作品页。检索结果只能支持“本次未确认”，不能证明互联网不存在其他资产。

| 页面 | 实際核到什么 | 对本任务的结论 |
| --- | --- | --- |
| [Nexprint：奶蛙豆包月饼伸缩剑](https://www.nexprint.cn/zh/models/G6209717) | 作者页面列 3MF 打印文件，标 CC BY-NC-SA；实际页面 HTTP 200 已保存。 | 属同人打印浮雕与玩具，不是独立绑定角色；未下载，不作为游戏源资产。 |
| [Makeronline：奶蛙×豆包中秋浮雕](https://www.makeronline.com/zh/model/%E5%A5%B6%E8%9B%99%C3%97%E8%B1%86%E5%8C%85%E8%BF%87%E4%B8%AD%E7%A7%8B%EF%BD%9C%E8%B1%86%E5%A5%B6CP%E6%9C%88%E9%A5%BC%E6%B5%AE%E9%9B%95%E6%91%86%E4%BB%B6/332624.html) | 页面对原始模型文件计数为 0，列打印配置；Standard Digital File License 禁止文件及衍生作品分发。实际页面 HTTP 200 已保存。 | 不符合开放源模型条件；未下载，不导入本项目。 |
| [Tripo：生成一只奶蛙](https://studio.tripo3d.ai/3d-model/%E7%94%9F%E6%88%90%E4%B8%80%E5%8F%AA%E5%A5%B6%E8%9B%99-a1ddba2d-6b81-4f48-a718-6c1b2ce8ff68) | 网页检索能读取展示标题与提示词；直接 HTTP 请求返回 403。未确认可下载源文件、绑定或许可。 | 只能记为展示线索，不能声称找到可用同款模型。 |

表情包、像素重排应用或桌宠代码的开源声明并不证明其中存在三维源角色，因此没有把它们列成模型候选。

## 通用蛙模型候选

| 资源与作者 | 许可与获取核验 | 可复用部分及限制 |
| --- | --- | --- |
| [OpenGameArt：Frog low poly animated 3d model，methodical pixel](https://opengameart.org/content/frog-low-poly-animated-3d-model) | 上传页面标 CC0；无登录即可下载 tar.gz。本次已下载 `.blend`、PNG 与 XCF，实际在 Blender 4.5.14 LTS 打开检查。压缩包未内置单独 LICENSE 文本，许可证据来自上传页及其 CC0 链接。 | 最适合当最小导出研究样本。它是四足、600 三角面的低模，不能满足直立高精奶蛙。 |
| [BlendSwap：2 Realistic Frogs (Rigged)，RubenCUR](https://blendswap.com/blend/29791) | 侧栏虽标 CC0，但作者正文明确原模型来自 ffish.asia / floraZia.com，原许可 CC-BY；作者修改包括清理、低分辨率烘焙与 Rigify。下载页要求登录。 | 许可信息存在冲突，本次不按 CC0 导入。可阅读其处理思路；尚未取得源文件，未实测。 |
| [Motion Miracles：Frog Toy Rig (From Klaus)](https://sketchfab.com/3d-models/frog-toy-rig-from-klaus-c0440af002ab4cddaad0096ae3437d51) | 作者 Sketchfab 页面实际链接 CC BY 4.0，显示约 258.4k 三角面；[作者站](https://motionmiracles.com/assets)称免费。旧 Sellfy 源文件链接当前返回 404；未取得绑定 `.blend`。 | 可借风格与跳跃展示方法，来源明确指向电影 Klaus 的青蛙玩具，比例不同。没有实际文件就不能确认游戏骨架、UV 或 Godot 适配。 |
| [Blender Studio：Yule Frog 源文件](https://studio.blender.org/training/3d-printing/yule-frog-blend-file/) | 官方页标 CC BY 4.0、作者 Hjalti Hjalmarsson、Blender 5.1 File，当前显示 Login to Download。 | [教程](https://studio.blender.org/training/3d-printing/chapter/yule-frog/)面向 3D 打印摆件，可借形体、脚与嘴雕刻方法。没有实际源文件，不能认定有游戏绑定；页面版本也高于本机 4.5.14。 |

[CC0 官方说明](https://creativecommons.org/publicdomain/zero/1.0/)与[CC BY 4.0 官方说明](https://creativecommons.org/licenses/by/4.0/)已直接核对。后者要求署名、提供许可链接并说明改动。这里记录资产页面的声明，不把页面许可标签当成第三方权利已经全部解决的证明。

额外核查了 Quaternius 的[Ultimate Animated Animals 官方包](https://quaternius.com/packs/ultimateanimatedanimals.html)：作者页面 CC0、包含 `.blend`，公开 Blends 文件夹里列的是 Alpaca、Bull、Cow、Deer、Donkey、Fox、Horse、Horse_White、Husky、ShibaInu、Stag、Wolf，没有 Frog。Poly Pizza 的 Quaternius Frog 页面可作另一条资源线索，但本次未追溯到作者同款源文件，未下载或列为已检查候选。

## 已下载模型的实测结果

[原始压缩包](../../source_assets/naifrog/reference_research/downloads/opengameart-frog.tar.gz)为 191,703 bytes，SHA-256 `4b72b3f4eceb0b15fa8d4f464007a059fc0c2ab6f22b5965230762db614655e8`。包含 `.blend`、128×128 PNG 和可编辑 XCF。

所有 Blender 调用均使用 `--background --disable-autoexec`；本次运行的是自己编写的数据检查、CPU 预览与导出脚本，没有执行下载文件中的脚本。检查只读取源文件；预览和导出调整仅存在于当前 Blender 进程，未保存覆盖源 `.blend`。

| 项目 | 实测数据 | 对高精奶蛙的影响 |
| --- | --- | --- |
| 网格 | 1 个 mesh；330 vertices、348 polygons、600 triangles；128 三角面、208 四边面、8 六边面、4 八边面 | 面数与轮廓是低模标准，不能靠数量标签称高精。 |
| 拓扑 | boundary edges 0、non-manifold edges 0、loose vertices 0 | 本次拓扑库存检查没有发现上述缺口；不等于所有动画变形已验收。 |
| UV/贴图 | 1 个 UVMap；1 张 128×128 PNG；路径存在；Principled BSDF 与 image texture | 能研究 UV 与嵌入贴图；缺少高精表面、法线/粗糙度细节。 |
| 骨骼/权重 | 1 个 armature、15 根 deform bones；无未权重顶点；权重和为 1；每顶点仅 1 根骨骼影响 | 硬权重适合原低模，不能据此保证宽肚皮、肩、膝与手腕的平滑变形。 |
| 动作 | `idle`、`walk`：1–24；`jump`、`land`：1–12；另外 4 项是单帧 pose | 共 8 个 Actions，但不能把单帧 pose 统计成 8 套完整动作；无本项目六动作兼容性证明。 |
| 表情 | 无 Shape Keys；无 drivers、无 text blocks | 未提供高精嘴眼表情系统。 |

已在 Cycles **CPU** 渲染并实际查看[源模型预览](../../source_assets/naifrog/reference_research/inspections/opengameart-frog-source-preview.png)：宽眼、四足、绿色低模表面，与新照片的直立黄色梨形奶蛙明显不同。

![已下载 CC0 蛙的 CPU 源模型预览](../../source_assets/naifrog/reference_research/inspections/opengameart-frog-source-preview.png)

## glTF 样本：导出成功与需要修整的真实问题

首次按选中物体导出时，原文件将 armature 隐藏，导出结果只有静态 mesh，没有 skins 或 animations。显式显示 armature 后，原文件重复 NLA 引用及 mesh 上的骨骼 Action 数据又使部分动画出现重复 target/path 通道。本次保留了这两份原始失败样本与各自机器检查。

研究导出脚本在内存中显示 mesh/armature、清掉 mesh 的冗余动画数据与重复 NLA 轨，再保留 8 个 Actions 导出；未保存源文件。最终[研究 GLB](../../source_assets/naifrog/reference_research/inspections/opengameart-frog-research.glb)为 132,820 bytes，SHA-256 `8cbe3338c07907c7d808804d5599915763fa7ede0894e2d9e327bc0b1cea0c76`。

机器检查确认 GLB 头与长度一致，包含 15 joints、8 animations、嵌入 PNG、600 triangles，以及 `POSITION/NORMAL/TEXCOORD_0/JOINTS_0/WEIGHTS_0`。每段动画均 45 个唯一 target/path 通道，未再发现重复通道。导出后 478 个 vertices 是法线/UV 等拆分后的数据，不能拿它与源网格 330 vertices 混算。

这是 GLB 数据库存及指定结构检查通过，**没有执行完整 Khronos Validator，也没有在 Godot 实际导入运行**。研究 GLB 不能当作已经接入游戏的最终奶蛙。该案例说明验收应读取导出数据，而不能凭 `.blend` 看见骨骼就假设交付文件带骨骼。

## 推荐教程与后续制作依据

优先参考 [Crowfriend Games：Blender to Godot from Scratch](https://www.youtube.com/watch?v=0aLCOJWvuc4)，作者页明确覆盖从参考、建模、绑定、动画到 Godot 与 AnimationTree。定位点为 29:48 骨骼、37:30 权重、1:15:40 动画、1:17:38 Godot、1:23:45 AnimationTree、1:34:45 UV。来源发现链是聚合页嵌入 ID → 作者 YouTube 页；实际结论来自作者页面。

[Blender Study](https://www.youtube.com/watch?v=t6uP7VKiIgI)仅核到建模和渲染承诺；[SouthernShotty](https://www.youtube.com/watch?v=NN4xM3dQKtg)可补形状键与低模表情方法。后者的网页章节是 YouTube 自动章节，不标成作者章节。Yule Frog 用于形体与雕刻学习，不推定是现成游戏角色。

教程仅核对标题、作者描述和章节，未播放或声称看完。详细作者证据、版本固定的 Godot 4.5/Blender 4.5 官方导入原则见[教程研究文档](../../source_assets/naifrog/reference_research/tutorial-primary-research.md)。

后续制作的实际验收应包括：新照片的正面轮廓与色块、补全侧背视角；肩、膝、肚皮与手腕在动作中的变形；双眼与嘴部表情；glTF 的骨骼、权重、动作名称与数量；Godot 中尺寸、朝向、材质、阴影、脚部接地、循环与过渡。精度由这些成片与运行结果决定，不能由一个“高模”标签或教程成功示范代替。

## 本地证据与复现

- [下载收据](../../source_assets/naifrog/reference_research/downloads/opengameart-frog-download-receipt.json)：源 URL、完整包清单、大小与 SHA-256。
- [Blender 数据检查](../../source_assets/naifrog/reference_research/inspections/opengameart-frog-inspection.json)：完整 object、UV、bone、weight、Action、material、image 库存。
- [最终 GLB 检查](../../source_assets/naifrog/reference_research/inspections/opengameart-frog-glb-inspection.json)与[指定结构检查](../../source_assets/naifrog/reference_research/inspections/opengameart-frog-export-checks.json)。
- [检查脚本](../../source_assets/naifrog/reference_research/scripts/inspect_blend.py)、[CPU 预览脚本](../../source_assets/naifrog/reference_research/scripts/render_source_preview.py)、[研究导出脚本](../../source_assets/naifrog/reference_research/scripts/export_source_sample.py)、[GLB 读取脚本](../../source_assets/naifrog/reference_research/scripts/inspect_glb.py)。
- 原始采集目录位于本 chat 的 `work/naifrog/resource-research/`；已核验的页面、下载源文件、许可、检查结果、失败样本和制作脚本另外按原件保存到仓库的 `source_assets/naifrog/reference_research/`，随 `17b34a5` 发布。仓库档案用于来源与复现，不作为正式游戏运行资产。

复现检查命令（从本 chat 根目录执行）：

```sh
work/runtime/blender/Blender.app/Contents/MacOS/Blender --background --disable-autoexec work/naifrog/resource-research/downloads/opengameart-frog/frog/frog.blend --python work/naifrog/resource-research/scripts/inspect_blend.py -- work/naifrog/resource-research/inspections/opengameart-frog-inspection.json
work/runtime/blender/Blender.app/Contents/MacOS/Blender --background --disable-autoexec work/naifrog/resource-research/downloads/opengameart-frog/frog/frog.blend --python work/naifrog/resource-research/scripts/export_source_sample.py -- work/naifrog/resource-research/inspections/opengameart-frog-research.glb
python3 work/naifrog/resource-research/scripts/inspect_glb.py work/naifrog/resource-research/inspections/opengameart-frog-research.glb work/naifrog/resource-research/inspections/opengameart-frog-glb-inspection.json
```
