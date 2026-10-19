# Personal Calendar

独立计算节日、传统民俗、二十四节气与季节生活节点。公开订阅，前后三年共七个完整公历年滚动，中文全天、无提醒、不占用忙碌时间。

放假、补班及原生班休角标由用户另订 [Apple 官方源](https://calendars.icloud.com/holidays/cn_zh.ics)。本项目不复制、代理或按 Apple 数据删减内容；同时显示时可能重叠。旧 r1/B1 角标测试已冻结，请退订，实机未通过记录保留。

## 订阅方式

[打开订阅与检索页面](https://shiki1255.github.io/personal-calendar/)

- **整合订阅**：[calendar.ics](https://shiki1255.github.io/personal-calendar/calendar.ics) 包含全部已启用内容，推荐使用。
- **分类订阅**：从下面八组中按需选择，可在手机上分别隐藏、显示及设色。
- **旧地址兼容**：[festivals.ics](https://shiki1255.github.io/personal-calendar/festivals.ics) 继续汇总前六组节日，不包含节气、季节节点。已有订阅可继续使用，并按需搭配后两组。

不要同时订阅整合版与分类版；不要将 festivals.ics 与前六组分类重复订阅。切换时先退订旧源再添加新源，不依赖 Apple 跨日历去重。节气的旧地址保持不变。

| 管理分类 | 配置标识 | 独立订阅 | 规则数 |
|---|---|---|---|
| 传统节日 | traditional | [traditional.ics](https://shiki1255.github.io/personal-calendar/traditional.ics) | 8 |
| 传统民俗 | folk | [folk.ics](https://shiki1255.github.io/personal-calendar/folk.ics) | 8 |
| 公共节日与纪念日 | public | [public.ics](https://shiki1255.github.io/personal-calendar/public.ics) | 10 |
| 亲情与情感 | family | [family.ics](https://shiki1255.github.io/personal-calendar/family.ics) | 3 |
| 文化与商业 | culture | [culture.ics](https://shiki1255.github.io/personal-calendar/culture.ics) | 5 |
| 基督宗教节日 | christian | [christian.ics](https://shiki1255.github.io/personal-calendar/christian.ics) | 8 |
| 二十四节气 | solar_terms | [solar_terms.ics](https://shiki1255.github.io/personal-calendar/solar_terms.ics) | 24 |
| 季节生活节点 | seasonal | [seasonal.ics](https://shiki1255.github.io/personal-calendar/seasonal.ics) | 14 |

分类用于个人管理，不宣称是唯一的文化或宗教分类。42 条节日规则、24 个节气、14 类季节节点不等于每个公历年固定生成80条事件；整合版合并清明，农历年初边界也可能影响年度数量。

iPhone 日历中使用“添加日历 → 添加订阅日历”并粘贴 HTTPS 地址，或使用网页 webcal 按钮。不要一次性导入。订阅 URL 不变，客户端自动刷新时间由 Apple 控制；GitHub Pages 实测曾为 max-age=600，不保证即时更新。实际手机验收见 [记录](docs/acceptance.md)，其他客户端未实测。

## 规则、目录与批量管理

规则由分类登记、节日定义、节气定义和季节节点定义统一生成网页与 [机器可读目录](https://shiki1255.github.io/personal-calendar/catalog.json)。网页可按中文名、稳定 ID、分类和 sanfu/shujiu 子组检索，显示真实启用状态、配置位置与归属订阅；筛选只影响目录显示，不修改订阅。

[config.toml](config.toml) 是正式开关入口：

| 操作 | 修改位置 | 影响 |
|---|---|---|
| 批量关闭某一分类 | `[categories]` 中对应值设为 `false` | 从整合版、对应分类及兼容合集中一致隐藏，其他分类不变 |
| 单独关闭某节日 | `[festivals].disabled_ids` 加入目录列出的 ID | 只隐藏该节日，保留规则与历史 |
| 单独关闭某节气 | `[solar_terms].disabled_ids` 加入其 ID | 不阻止依赖该节气的节日和季节节点计算 |
| 关闭三伏或数九 | `[seasonal].sanfu` 或 `shujiu` 设为 `false` | 仅关闭该子组 |
| 关闭某个季节节点 | `[seasonal].disabled_ids` 加入其 ID | 仅关闭该节点 |
| 选择小年口径 | `[festivals].little_new_year` | both / north / south / none，默认 both |
| 复活节星期一 | `[festivals].easter_monday` | 已开启，仍可单独关闭 |

分类关闭优先于单项开启。分类关掉后仍发布有效空日历，地址不会404。日常删减用停用配置，不物理删除定义。未知 ID 和不合法配置阻止生成，避免拼错后静默失效。

清明节与清明节气在两个配置段中各自独立，目录使用 `festivals:qingming` / `solar_terms:qingming` 区分；整合版按稳定身份合并。关闭感恩节显示仍可计算黑色星期五，关闭节气显示仍可计算清明、三伏和数九。

只读查询示例（不修改配置或写文件）：

```powershell
python -B scripts/catalog.py --category folk
python -B scripts/catalog.py --search 小年
python -B scripts/catalog.py --category seasonal --search shujiu --json
```

分类、规则 ID 和独立订阅文件在登记信息中一一对应，后续增删清单不需要修改日期算法。名称和分类不是 UID 的组成部分。

## 日期计算约定

- 固定月日仅用于定义本身固定的公历节日；母亲节、父亲节和美国感恩节采用原有星期规则，黑色星期五为感恩节后一天。
- 农历节日逐年转换，不在闰月重复；除夕是下一次春节前一天。新增上巳节采用三月初三、寒衣节十月初一、下元节十月十五口径，地域习俗可能不同。
- 复活节使用 USNO 公布的 Oudin 西方公历算法；圣枝主日、圣周四、受难日、圣周六、复活节星期一分别偏移 -7、-3、-2、-1、+1 天。
- 二十四节气由本地算法计算，取北京时间所属日期，不展示未经独立验证的分钟。清明节本体跟随当年的清明节气。
- 三伏从夏至当天起计第三个庚日为初伏，第四个庚日为中伏，立秋当天起第一个庚日为末伏；节气当天为庚日时计入。初伏和末伏各10天，中伏10或20天，出伏是末伏开始后第10天。
- 数九从冬至当天开始，每九天一个阶段；一九至九九分别偏移0、9……72天，出九偏移81天。以起始冬至年度保持稳定身份，补算前一年周期后按公历窗口过滤。
- 季节节点只显示每阶段的开始日，并在说明中标出阶段长度；初伏/入伏、一九/入九各合为一条。冬至与一九含义不同，允许同日分别显示。这些节点不表示实际天气变化或放假。

依据：[USNO](https://aa.usno.navy.mil/faq/easter)、[HKO 节气](https://www.hko.gov.hk/tc/gts/time/24solarterms.htm)、[民俗年历](https://www.ihchina.cn/project_details/18325)、[下元节](https://www.ihchina.cn/project_details/10176/)、[紫金山天文台历书说明](https://www.pmo.cas.cn/xwdt2019/kpdt2019/202203/t20220317_6399980.html)。三伏测试另保存政府公开历史样本和干支纪日锚点的来源；不使用算法自身生成测试预期。

2026-10-19 本次扩充保留此前39条节日，新增上巳、寒衣、下元，重排八组分类并加入三伏和数九。复活节星期一继续启用。

## 本地生成与修订

Python 3.12，锁定 `lunar_python==1.4.8`，只使用农历、节气和基础干支纪日，不使用预置节日、调休、三伏或数九清单。离线生成，不依赖日历 API、数据库、常驻服务或在线 AI。[第三方许可](THIRD_PARTY_NOTICES.md)

```powershell
python -m pip install --require-hashes -r requirements.txt -r requirements-test.txt
python -B scripts/preflight.py
python -B -m unittest discover -s tests -v
python -B scripts/calendar_cli.py --output D:/CodexProjects/codex_workbench/projects/personal-calendar/outputs/release-candidate/site --state-output D:/CodexProjects/codex_workbench/projects/personal-calendar/outputs/release-candidate/events.json
python -B scripts/automation.py verify --site D:/CodexProjects/codex_workbench/projects/personal-calendar/outputs/release-candidate/site
```

候选必须在源码仓库外的全新目录中生成，不覆盖上一成功版本。CI 使用 RUNNER_TEMP。`--as-of` 可传带时区的 ISO 时间，`--config` 和 `--state` 可指定输入。verify 必须在部署相同候选后运行。

现有事件保持 UID 和日期规则，分类元数据变化正常增加 SEQUENCE；内容不变的事件保持时间戳和版本。新分类文件与整合版使用同一事件身份，但客户端不会自动跨订阅去重。历史修订条目保留，按字节折行、UTF-8、CRLF、全天排他结束日期均验证。

## 自动维护与发布

- 每天北京时间 06:17 轻量判断。每周一、当年/当月尚无成功记录、上次失败时运行完整检查；代码配置变化与手动触发立即运行。平台可能延迟或丢失调度。
- 正常日期完全本地计算，不抓政府或 Apple 数据。无维护任务时不安装依赖、不构建、不访问外部日期站点。
- 测试 → 候选十份 ICS → 与线上版本比较 → 显式 Pages 部署 → 匿名 HTTP/MIME/全部内容哈希回读 → 持久化修订与真实健康记录。
- 十份 ICS 同版部署；内容无变化时跳过部署，不重写事件。月度首个完整成功检查保存健康记录；普通周检只留 Actions 日志，不提交无意义日历变化。
- 验证失败不发布；部署或回读失败不记成功，次日重试。维护失败复用一个 Issue，恢复后关闭；正常运行不主动发消息。请在 GitHub 订阅此仓库 Issue/失败 Actions 通知。
- 最小 job 权限、Actions 固定提交 SHA、依赖锁版本与哈希，不需要长期私人访问令牌。Dependabot 月度归组更新，安全更新不并入普通版本组；任何依赖/算法/工作流更新都不自动合并。
- PR 检查实际上传、下载候选及 Pages 打包文件，逐文件核对内容；PR 不部署、不写发布状态。升级部署组件后，可手动选择 force_deploy，使用相同日历字节验证完整部署及线上回读；默认仍只在内容变化时发布。

月度健康提交降低公开仓库 60 天无活动导致定时工作流停用的风险，但不保证平台永不停调度。没有外部监控，完全停跑无法靠自身告警。每年查看一次 Actions、覆盖范围和通知状态，集中审阅非紧急依赖更新。[GitHub 调度限制](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)

## 回滚

每次线上核验成功保存 last-good-site artifact，保留 90 天。到 Actions → Update calendar → Run workflow，将之前**成功的 main 运行 ID**填入 rollback_run_id；留空则正常生成。恢复完整静态版本并重新回读，不倒退事件修订历史。此恢复只改变发布内容，后续常规更新仍按当前源码生成；需要长期停留旧版本时先修正或回退引入问题的代码。

~~~powershell
gh workflow run update-calendar.yml --repo SHIKI1255/personal-calendar -f rollback_run_id=RUN_ID
~~~

超过 artifact 保留期仍可从 Git 历史中的代码、规则和修订状态重建，但必须重新测试；不要通过强制推送抹去历史。

## 验证范围

首版逐日核对 2023—2029 年 2,557 个公历日的农历转换、168 个节气以及全部生成的农历节日；2022 年 HKO 原文提供跨年月份上下文和2023年初数九周期的冬至基准。测试预期来自 HKO 快照，不由被测算法生成。HKO 不作为自动生成上游。算法与权威基准冲突阻止发布。

另外覆盖复活节独立算法对照、闰年/闰月、除夕、星期规则、圣周、配置、同日不同节日、UID、折行与结束日期、修订和字节稳定、失败保护、线上校验、告警去重及回滚验证。手机订阅和刷新仍需真实用户验收，不以这些测试代替。
