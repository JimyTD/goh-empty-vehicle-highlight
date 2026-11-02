# Workshop 发布材料

已发布：https://steamcommunity.com/sharedfiles/filedetails/?id=3831496369 （Id 3831496369，2026-11-01）

上传工具 Description 栏只接受 `A-Z a-z 0-9 , ; . - _ ( ) '` 和空格，不能有中文、BBCode、换行；完整描述发布后在网页 Edit title & description 里粘贴。

上传工具：`<游戏目录>\binaries\x64\call_to_arms_workshop.exe`（先启动 Steam）

| 字段 | 填写 |
|---|---|
| Upload Directory | 本仓库的 `mod\empty_vehicle_highlight`（上传工具若回写 `mod.info`，改动会留在仓库里，提交即可） |
| Preview Image | 本仓库的 `docs\workshop_preview.jpg`（512×512） |
| Title | `Empty Vehicle Highlight` |
| Tags | 选与界面 / 游戏性相关的标签 |
| Visibility | 先 Private，自己订阅测试后再改 Public |

## Description（复制下面整段，Steam 支持 BBCode）

```
[h1]Empty Vehicle Highlight[/h1]
Press the vanilla [b]"highlight items"[/b] key (default [b]C[/b]) to also outline [b]every crewless vehicle[/b] on the map - tanks, cars, APCs, guns, mortars, planes, boats. Hover over the outline to see the vehicle name.

[list]
[*]Works for all 822 vehicles in the base game and DLCs.
[*]Only vehicles that the minimap still shows are marked - destroyed wrecks are ignored.
[*]The outline disappears within ~3 s after someone climbs in.
[*]No new keys, no UI changes: it simply rides on the vanilla C highlight.
[/list]

[h2]Known limitations[/h2]
[list]
[*]Turrets/hatches in the outline use the default pose.
[*]On side slopes the outline may be slightly off (roll is not copied).
[*]Only appends two include lines to the small vanilla [i]set/interaction_entity/debug.inc[/i]; it no longer overrides [i]entity.set[/i], so it works alongside most big mods. Vehicles added by other mods are not highlighted.
[*]Multiplayer not tested.
[/list]

Source code & generator: https://github.com/JimyTD/goh-empty-vehicle-highlight

[hr][/hr]

[h1]空载具高亮[/h1]
按原版“高亮地面物品”键（默认 [b]C[/b]）时，同时描出地图上[b]所有无人载具[/b]的轮廓：坦克、汽车、装甲车、火炮、迫击炮、飞机、船只。鼠标悬停显示载具名称。

[list]
[*]覆盖本体及 DLC 的全部 822 种载具。
[*]只标小地图上仍显示的载具，已被摧毁的残骸不标。
[*]有人上车后约 3 秒内轮廓消失。
[*]不新增按键、不改界面，直接沿用原版 C 键高亮。
[/list]

[h2]已知限制[/h2]
[list]
[*]轮廓中的炮塔、舱门为默认姿态。
[*]横向斜坡上轮廓可能略有偏差（不复制侧倾）。
[*]只在原版很小的 [i]set/interaction_entity/debug.inc[/i] 末尾追加两行引用，不再覆盖 [i]entity.set[/i]，可与大多数大型模组同时使用。其他模组新增的载具不会高亮。
[*]未测试联机。
[/list]

源码与生成器：https://github.com/JimyTD/goh-empty-vehicle-highlight
```

## 发布后

1. 订阅自己的 Workshop 版本前，先把游戏 `mods\empty_vehicle_highlight` 本地副本移走，否则游戏会报重复模组并只用其中一份。
2. 把 Workshop 链接补到 README，若 `mod.info` 被上传工具改过一并提交。
3. 游戏更新后：`python tools/gen_proxies.py` → 视情况改 `mod.info` 版本号 → 用上传工具的更新功能重新上传。
