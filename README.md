# Empty Vehicle Highlight（空载具高亮）

Call to Arms – Gates of Hell: Ostfront 模组。按原版“高亮地面物品”键（默认 **C**）时，同时描出所有**无人载具**的轮廓（坦克、汽车、装甲车、火炮、飞机、船只……），鼠标悬停显示载具名称。

A mod for *Call to Arms – Gates of Hell: Ostfront*. Pressing the vanilla "highlight items" key (**C**) also outlines every crewless vehicle; hovering shows the vehicle name.

**Steam Workshop: https://steamcommunity.com/sharedfiles/filedetails/?id=3831496369**

![preview](docs/workshop_preview.jpg)

## 原理

引擎的 C 键高亮只对非 `actor` 的物品实体生效，载具是 `actor`，无法直接被点亮。本模组：

1. 在所有基于 `/properties/vehicle.ext` 的实体上挂脚本：载具无人（`not operatable`）、在小地图上显示（`able minimap`、无 `destroyed` 标签、无 `no_minimap_view` 属性）且没有被牵引（`not linked`）时，每 3 秒在载具 `basis` 骨骼处生成一个**替身**，替身存活 3.3 秒后自删；有人上车后最多 3 秒消失。
2. 每种载具一个替身：带 stuff extender 和专属物品，所有碰撞体关闭，因此能被 C 点亮、悬停显示名称，但不可拾取、不可选中、不挡子弹。
   替身用的是载具完整模型的副本：网格、动画仍指回原版文件，但所有材质换成一个**平时不画、只在 C 键高亮时画**的标记材质（见下）。因此平时看不到替身，按 C 时整车（含炮塔、炮管、火炮大架、机枪）都有轮廓。
3. 替身、物品、名称、标记贴图和脚本块由 `tools/gen_proxies.py` 从当前安装的游戏数据生成（当前 822 种载具）。

### 隐形替身

标记材质是 `blend test` + `{alpharef 255}`，贴图 `texture/common/evh/evh_marker.dds` 的透明度统一为 0.6：

- 普通渲染的 alpha test 丢弃透明度 < `alpharef`/255（= 1.0）的像素，0.6 被丢弃，替身既不画颜色也不写深度。
- C 键高亮用的 `silhouette_ps` 固定丢弃透明度 < 0.5 的像素，不读 `alpharef`，0.6 保留，所以轮廓照常出现。

早期“透明替身没有轮廓”的测试用的是透明度 0，两条渲染路径都会丢弃，所以失败。

### 兼容性约定

- 替身实体放在 `/entity/evh/`，物品放在 `/set/stuff/evh/`。单位资料库会扫描 `/entity/-vehicle/` 和 `/set/stuff/special/`，替身放在那里会被当成载具/物品读入，导致进资料库闪退。
- 不覆盖 `entity.set`（大型模组常改它），而是在原版很小的 `debug.inc` 末尾追加两行 include；各模组的 `entity.set` 通常都保留对它的引用。
- 每种载具的脚本块 key 写成 `"<载具名> obstacle_ignore_height"`，不与原版或其他模组的同名载具块重名。

详细的引擎分析见 [docs/NOTES.md](docs/NOTES.md)，Workshop 发布材料见 [docs/WORKSHOP.md](docs/WORKSHOP.md)。

## 目录

```
mod/empty_vehicle_highlight/     模组本体（即上传 Workshop 的目录）
  mod.info
  resource/set/interaction_entity/
    debug.inc                          原版文件 + 两行 include（生成）
    empty_vehicle_highlight.inc        核心逻辑（手写）
    empty_vehicle_highlight_proxies.inc 每种载具的生成块（生成）
  resource/set/stuff/evh/evh_*         替身物品（生成）
  resource/entity/evh/**/evh_*.def     替身实体（生成）
  resource/entity/evh/**/*.mdl, *.mtl  替身模型（完整几何，网格/动画用相对路径指回原版）和同名标记材质（生成）
  resource/texture/common/evh/         标记贴图（生成）
  localizations/{default,ch}/...       替身悬停名称（生成）
tools/
  gen_proxies.py   重新生成所有生成文件
  install.py       复制到游戏 mods 目录
  check_log.py     扫描 game.log 中与本模组相关的报错
```

只有 `mod.info` 和 `empty_vehicle_highlight.inc` 是手写的，其余文件都由脚本生成，不要手改。

## 维护流程

需要 Python 3.9+，无第三方依赖。游戏不在默认路径时先设置环境变量 `GOH_DIR`。

```bash
# 游戏更新或新增载具后
python tools/gen_proxies.py     # 重新生成
python tools/install.py         # 装到游戏 mods 目录
# 进游戏测试后
python tools/check_log.py
```

游戏版本超出 `mod.info` 中 `maxGameVersion` 后，模组会被判定不兼容，需要修改版本号并重新上传。

## 已知限制

- 按 C 时轮廓是替身的姿态，不一定与真车一致：炮塔、炮管、车门、火炮大架等是默认姿态；车头朝某些方向停在坡上时轮廓会带一个不该有的侧倾（引擎 `spawn` 的朝向算法所致，见 NOTES）。平时替身不可见，这些偏差只在按住 C 时看得到。
- 有人上车后轮廓最多还留 3 秒左右。
- 覆盖了原版 `set/interaction_entity/debug.inc`（只追加两行 include），与同样覆盖该文件、或自带的 `entity.set` 不再引用 `debug.inc` 的模组冲突。
- 其他模组新增的载具没有替身，不会高亮。
- 未测试联机。

## License

[MIT](LICENSE)。本仓库只包含模组脚本和生成器；游戏本体及其资源版权归 Barbedwire Studios / Digitalmindsoft 所有。
