# 引擎分析笔记

基于 `call_to_arms.exe` 文件版本 1.0.6.7（游戏 1.067，Steam build 25492057）的静态反汇编。地址为 RVA，游戏更新后会变，只作定位参考。

## C / V 高亮

- 按键：`interface/stuff_highlight`（C）、`interface/corpses_highlight`（V），状态类 `eStateHighlightStuff/Corpses@PanelControl`。切换只改场景管理器上的字节（+0x2b0 / +0x2b2）并刷新 UI，脚本读不到。
- 渲染入口 `0xa2d2d0`：C 只点亮**非 `eActor`**、带 `eStuffExtender` 且有物品的实体；V 只点亮生命组件处于死亡/昏迷的 `eActor`。载具是 `eActor`，两条都进不去，数据层面无解。
- `collectable` 属性与 C 高亮无关，只用于鼠标悬停拾取（`0xb69ed0`）。
- 悬停文字取本地化键 `desc/stuff/<item 名>`；载具名在 `desc/entity/<实体名>`。

## 小地图过滤（`0xb215df`，配置 `interface/scene.pak: scene/minimap/minimap.set`）

`able minimap`、无 tag `destroyed`（`0x984430`）、无 prop `no_minimap_view`。本模组用同样三条判断“毁坏”。

## 交互脚本（`set/interaction_entity/*.inc`）

- 顶层块 key 按 prop 组合或实体名匹配（原版 `{"gaz67"}` 即按实体名），同一事件跨多个块会依次执行。
- `{spawn "<实体>" "<骨骼>" [x|y|z] ... {子指令}}`：参数解析 `0x7544a0`，轴参数 `0x7560e0`。子指令块在新生成的实体上执行（原版降落伞用它延时自删）。
- **不写轴时朝向是常量世界 +X**（`0x146e140`），写了轴才取骨骼矩阵方向（执行 `0x705cfa`，`game_entity` 姿态 `0x6fe160`），所以替身必须写 `"basis" x`。只对齐方向向量，侧倾不复制。

## 没走通的路

- 让替身平时不渲染、只在高亮时渲染：高亮使用 `eHighlightMaterial` 覆盖材质，但没找到“仅高亮层”开关；透明贴图对 `blend none` 材质无效；`{hide}` 的不透明度会被高亮读取。当前依赖替身与载具完全重合来掩盖。
- 透明替身实测（替身用自己的 `.mdl`，材质按 `.mdl` 所在目录解析，所以可以给替身单独换材质）：
  - 原版 `$/_building/transparent` 贴图其实是不透明的灰色，用它的替身是白模，能红显。
  - alpha 0 + `blend test`、黑色 + `blend add`、alpha 0 + `blend blend`（`alpharef 0`）：平时看不见，按 C 也没有轮廓。
  - alpha 50% + `blend blend`：能红显，但平时看得出发暗。
  - 结论：轮廓只出现在替身实际画出像素的地方，可见程度和轮廓强度绑定，做不到“平时完全不可见、按 C 有轮廓”。
- 现行做法：替身用原版材质，生成器把活动部件（`revolute` 骨骼、姿态动画会挪动的骨骼，车轮/履带/悬挂除外）的 `VolumeView`/`LODView` 从替身 `.mdl` 中去掉，剩下的部分与真车重合。`.anm` 格式：`EANM` 头，`BMAP` 后是骨骼名表（u32 个数 + 每项 u32 长度 + 名字），之后是 `FRM2` 帧：u16 帧号、u8 记录数，每条记录 u8 骨骼、u8 标志、u8 保留，标志 1 后跟位置 3×f32，标志 2 后跟旋转 3×f32。
- `panel_control` / `keys.set` 只能给已有动作换键，不能新增全局开关。
