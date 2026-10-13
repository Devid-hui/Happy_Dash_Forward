# 完整下载与首次运行

当前正式工程在 `codex/four-stage-modeling` 分支，使用 **Godot 4.7.2 Standard / GDScript / Forward+**。运行游戏需要 Git LFS 中的 GLB 模型和纹理，以及 Godot 在本机生成的导入缓存；只有脚本和 HUD 可以显示，不代表模型已经准备完成。无需安装 Blender，也无需下载历史建模报告、预览和可编辑 `.blend` 才能玩。

## 推荐：只下载当前运行资产

先安装 Git、[Git LFS](https://git-lfs.com/)、Python 3.9 或更新版本，以及 Godot 4.7.2 Standard 编辑器。Linux 还需要中文字体 `Noto Sans CJK SC`（Ubuntu 包名 `fonts-noto-cjk`）；macOS 使用系统的苹方字体。导入和运行不需要 C#/.NET SDK。导出应用才需要与引擎版本一致的 Export Templates。

克隆时暂时跳过自动下载所有 LFS 历史素材，再由项目脚本按当前运行清单拉取。

macOS / Linux：

```bash
GIT_LFS_SKIP_SMUDGE=1 git clone --branch codex/four-stage-modeling https://github.com/Devid-hui/Happy_Dash_Forward.git
cd Happy_Dash_Forward
python3 tools/bootstrap_project.py --download --godot "/absolute/path/to/godot"
```

macOS 的引擎参数可以直接传应用包路径，例如 `--godot "/Applications/Godot.app"`；脚本会使用包内的 `Contents/MacOS/Godot`。也可以传这个二进制的完整路径。

Windows PowerShell（保留原有环境变量）：

```powershell
$previousLfsSkip = $env:GIT_LFS_SKIP_SMUDGE
try {
    $env:GIT_LFS_SKIP_SMUDGE = "1"
    git clone --branch codex/four-stage-modeling https://github.com/Devid-hui/Happy_Dash_Forward.git
} finally {
    $env:GIT_LFS_SKIP_SMUDGE = $previousLfsSkip
}
Set-Location Happy_Dash_Forward
py -3 tools/bootstrap_project.py --download --godot "C:\Godot\Godot_v4.7.2-stable_win64.exe"
```

将引擎路径换成你实际安装的位置。脚本不会安装全局软件、切换分支或覆盖本地修改；`--download` 仅在这个仓库执行 `git lfs install --local`。下载范围由 [RUNTIME_ASSET_PATHS.json](../assets/refined/RUNTIME_ASSET_PATHS.json) 的活动资产目录推导，包含当前所需模型与纹理，以及编辑器会扫描的模型附属 PNG、材质源图片；有 `.gdignore` 的旧模型目录、历史报告和可编辑 Blender 源工程不在这个范围内。只下载清单中的直接依赖会留下附属 PNG 指针，首次导入仍会报图片损坏，因此脚本一并处理这些文件。资源若有未提交修改，会先停止，让你保留自己的文件。

脚本会先检查文件是否仍为 LFS 指针、GLB 头部与文件长度是否有效、JSON 是否完整；在 Git 检出中还将实际模型/纹理的 SHA256 和大小与本分支已提交的 LFS 对象核对。随后确认指定的引擎是 4.7.2 编辑器，并显式执行：

```bash
godot --headless --path . --editor --import
```

只有导入进程正常结束、日志没有 `ERROR` / `SCRIPT ERROR`、当前运行资源的缓存存在且源文件校验相符，才输出 `PASS import cache`。完成后，用同一个 Godot 编辑器打开 `project.godot`，按 **F5** 运行整个项目。首次导入期间不要同时启动游戏或另一份编辑器导入。

## 已经下载工程，但地图只有地面、雨和文字

先停止游戏，在项目根目录执行只读诊断：

```bash
python3 tools/bootstrap_project.py --check
```

Windows 将 `python3` 换为 `py -3`。这个模式不下载文件，也不生成或删除任何导入缓存。

| 输出 | 含义 | 处理 |
| --- | --- | --- |
| `LFS POINTER` | 文件只有下载地址和 SHA256，实际模型或纹理尚未到本机 | 在完整 Git 检出中执行 `--download --godot 引擎路径` |
| `MISSING SOURCE` / `INVALID SOURCE` | 运行源文件缺失、截断或与分支的 LFS 对象不符 | 保留本地修改；用完整 Git 检出下载和重新校验。脚本不会强制覆盖文件 |
| `SOURCE OK, IMPORT NOT READY` / `IMPORT REQUIRED` | 二进制已到本机，但 `.godot/imported` 缓存缺失或不对应当前源文件 | 执行 `python3 tools/bootstrap_project.py --godot "引擎路径"`，或在编辑器打开工程，等待导入全部结束再 F5 |
| Git LFS `quota` / `bandwidth` / `billing` 报错 | 服务端下载额度或账单限制 | 保留完整报错，由仓库所有者处理服务端限制；反复 `git pull` 或 Godot 导入不会补回二进制 |
| `PASS source assets` 和 `PASS import cache`，但仍不可见 | 当前运行文件和本机导入检查已经通过，需继续核对图形运行问题 | 提供 Godot 的实际版本、渲染器/显卡信息及运行日志中的完整 `ERROR` / `SCRIPT ERROR` |

返回码 **0** 表示当前源资源、附属图片和导入缓存检查通过；**1** 表示源文件、下载或引擎导入失败；**2** 表示源文件通过但导入尚未准备好。`--check` 和 `--godot` 不能组合，因为后者会生成缓存。

只运行 `godot --path .` 不会替代首次编辑器资源导入。仓库不提交 `.godot/`：该目录由你自己的引擎、系统和导入参数生成，不能从另一台电脑直接复制。仓库中的 `.glb.import` / `.png.import` 是导入设置，单有它们也没有可加载的 `.scn` / `.ctex` 缓存。Godot 的 [`--import` 官方说明](https://docs.godotengine.org/en/stable/tutorials/editor/command_line_tutorial.html)明确说明该命令启动编辑器、等待资源导入完成后退出。

## GitHub 网页 ZIP 与完整源素材

GitHub 的 **Code → Download ZIP** 默认只放入 LFS 指针，不包含实际大文件，除非仓库所有者专门启用了包含 LFS 对象的归档设置。见 [GitHub 官方归档说明](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/managing-git-lfs-objects-in-archives-of-your-repository)。ZIP 还缺少 `.git`，不能在解压目录中使用 `git lfs pull`；请保留原目录，按上面的步骤另建完整 Git 检出，再运行项目脚本。若 ZIP 确实包含全部二进制，`--check` 和 `--godot` 仍可校验与导入，但无法核对 Git 中的 LFS SHA256 身份。

如果需要编辑所有高模 `.blend`、历史候选、研究素材和预览，可在完整 Git 检出中另外执行：

```bash
git lfs pull --include="" --exclude=""
```

这是可选的大体积源素材下载，与当前游戏运行下载分开。它不会替代 Godot 导入，也不保证这些历史素材全部属于当前正式模型。

开发回归入口为 `python3 tests/run_tests.py --godot "引擎路径"`。检查通过能够证明其覆盖范围内的资源、脚本和行为；它不等于同伴电脑上的图形运行验收。
