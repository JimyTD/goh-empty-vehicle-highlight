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
- 写了轴时姿态是“从世界 +X 转到骨骼 X 方向的最短旋转”（转轴 = +X × 方向，转角 = acos(方向.x)），不是“没有侧倾”：会额外带一个约为 俯仰角 × tan(偏航/2) 的侧倾。车头接近世界 -X 时可以很大（3° 坡、偏航 170° 约 33°），这就是替身“半翻车”的原因。
- `spawn` 的其他参数：`no_normal`、`inv_normal`、`dir_velocity`、`no_position`、`random_position`、`random_orientation`、`terrain_texmod`、`offset`、`local_offset`、`local`、`constrain_after_dir`、`scale`、`volume`、`texmod`。脚本没有把生成的实体挂到另一个实体骨骼上的命令（只有 `unlink`、`with_linked_entity`）。
- `cannon_state` 取值：`fire` 0、`move` 1、`trailing` 2（`0x10eb7a0`）。

## 隐形替身（现行做法）

普通渲染和 C 键高亮的 alpha 丢弃规则不同，中间有一段空档：

- 普通渲染：`blend test` 材质用 `ALPHA_TEST` shader，丢弃 alpha < `cb1[10].w`（材质的 `alpharef`）的像素。
- C 键高亮：`eHighlightMaterial`（`0x6ea440`）用 `silhouette_ps`，丢弃 alpha < 0.5，写死在 shader 里，不读 `alpharef`。
- 贴图 alpha 0.6（153）+ `{alpharef 255}` + `{blend test}`：普通渲染丢弃，高亮保留。已在游戏里确认：平时看不到替身，按 C 有轮廓，悬停能显示名称。
- `{alphatocoverage}` 不能开：抖动变体 `ALPHA_TEST_DITHER` 不读 `alpharef`。

高亮渲染层是 21（`highlight`，`0xa2d59e`）。ply 内嵌的材质名都不带路径，所以在替身 `.mdl` 目录放同名 `.mtl` 就能全部替换。

## 没走通的路

- 早期透明替身实测（替身用自己的 `.mdl`，材质按 `.mdl` 所在目录解析，所以可以给替身单独换材质）：
  - 原版 `$/_building/transparent` 贴图其实是不透明的灰色，用它的替身是白模，能红显。
  - alpha 0 + `blend test`、黑色 + `blend add`、alpha 0 + `blend blend`（`alpharef 0`）：平时看不见，按 C 也没有轮廓。alpha 0 低于两条路径的阈值，都被丢弃。
  - alpha 50% + `blend blend`：能红显，但平时看得出发暗。
- 删掉活动部件（`revolute` 骨骼、姿态动画会挪动的骨骼）让替身和真车重合：平时没有重影，但火炮和机枪只剩约 1/4 能亮，且侧倾错位去不掉。隐形替身后不再需要，生成器里保留为 `HIDE_MOVING = False`。`.anm` 格式：`EANM` 头，`BMAP` 后是骨骼名表（u32 个数 + 每项 u32 长度 + 名字），之后是 `FRM2` 帧：u16 帧号、u8 记录数，每条记录 u8 骨骼、u8 标志、u8 保留，标志 1 后跟位置 3×f32，标志 2 后跟旋转 3×f32。
- 替身贴地（`constrain_after_dir` + `{constrain surface}`）：只取一点的地形高度和法线，桥上、弹坑边会错位。
- 埋到地下或缩小藏进车内：形状对不上，敞篷车和火炮藏不住，凸起地形会露出。
- 中立描边（`camera.reg` 的 `active_outlines/neutral`）：只在鼠标悬停（`0xaf1720`）和战斗事件时把实体加入描边列表，不能批量显示，脚本也触发不了。
- 同步火炮 `close` 动画姿态：约 4 成骨骼的默认姿态不在动画两端，摆不准。
- `panel_control` / `keys.set` 只能给已有动作换键，不能新增全局开关。
