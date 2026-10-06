# Personal Calendar

独立计算的常规节日、圣周与二十四节气。公开订阅，七个完整公历年滚动，默认中文全天、无提醒、不占用忙碌时间。代码 MIT，政府历史记录与 HKO 资料另行注明来源。

**放假、补班及原生班休角标已取消自建，改为用户另订 Apple 官方源。**本项目不复制或合并 Apple 日历日期。原 r1/B1 角标实机测试均未通过，记录保留，旧角标关卡已撤销。

## 订阅

[订阅页面](https://shiki1255.github.io/personal-calendar/)

| 方式 | 固定地址 | 内容 |
|---|---|---|
| 整合 | [calendar.ics](https://shiki1255.github.io/personal-calendar/calendar.ics) | 全部节日、圣周、节气，内部去重 |
| 分开 | [festivals.ics](https://shiki1255.github.io/personal-calendar/festivals.ics) | 传统与常见节日、圣周 |
| 分开 | [solar_terms.ics](https://shiki1255.github.io/personal-calendar/solar_terms.ics) | 二十四节气 |

选择整合版，或选择一个/两个分类，**不要同时添加整合版与分类版**。切换先退订旧源再添加新源。分类版不为综合去重而删减。放假与补班另订 [Apple 官方源](https://calendars.icloud.com/holidays/cn_zh.ics)；官方也包含节日和节气，同时显示时可能重复。本项目按用户选择保留完整内容，可用配置关闭指定节日。

Apple 日历中使用“添加日历 → 添加订阅日历”并粘贴 HTTPS URL，或点网页上的 webcal 按钮；系统版本不同入口可能不同。不要以一次性导入代替订阅。旧的 compatibility/apple-badges.ics 与 compatibility/apple-badges-b1.ics 已冻结，请退订。

GitHub Pages 的 Cache-Control 由平台控制，实测曾为 max-age=600；iOS 另有刷新策略，不保证即时同步，不使用随机查询参数变换订阅身份。当前真实验收状态见 [验收记录](docs/acceptance.md)。其他客户端未实测。

## 内容与计算方式

完整规则在 [节日定义](data/festivals.json) 和订阅页面，日期按所选地域口径计算，不把某一年结果当作固定规律。

| 类型 | 默认内容及规则 |
|---|---|
| 农历 | 春节正月初一、元宵正月十五、龙抬头二月初二、端午五月初五、七夕七月初七、中元七月十五、中秋八月十五、重阳九月初九、腊八十二月初八 |
| 小年 | 北方十二月二十三、南方十二月二十四各一条；可选 north/south/both/none，不宣称所有地区统一 |
| 除夕 | 下一次春节前一天，不能固定为十二月三十；闰月不重复过节 |
| 固定公历 | 元旦 1/1、情人节 2/14、妇女节 3/8、植树节 3/12、愚人节 4/1、劳动节 5/1、青年节 5/4、儿童节 6/1、建党纪念日 7/1、建军节 8/1、教师节 9/10、国庆节 10/1、万圣夜 10/31、平安夜 12/24、圣诞节 12/25、跨年夜 12/31 |
| 星期规则 | 母亲节五月第二个星期日、父亲节六月第三个星期日、美国感恩节十一月第四个星期四、黑色星期五为感恩节后一天 |
| 复活节 | 自行实现 USNO 公布的 Oudin 公历算法，使用教会历规则，不用实际天文满月替代；可能在三月或四月 |
| 圣周 | 圣枝主日 -7、圣周四 -3、耶稣受难日 -2、圣周六 -1，相对复活节偏移；复活节仅一条，星期一 +1 默认关闭 |
| 清明 | 计算当年清明节气的北京时间日期；综合版与清明节合并，不固定在 4/4 或 4/5 |
| 节气 | 全部 24 个，按太阳黄经计算取北京时间日期，只展示日期，不宣称交节分钟已验证 |

不同节日同日仍分别保留，例如某年清明与复活节相遇。劳动节、国庆节等仅表示节日本体，不表示放假。

2026-10-06 补入龙抬头、植树节、青年节、儿童节、建党纪念日、建军节、教师节，共启用 38 条节日规则（小年南北分别计入；复活节星期一仍默认关闭）。新增固定公历节日采用中国大陆口径；龙抬头由农历二月初二逐年转换，闰月不重复。各新增规则的权威来源 URL 保存在定义文件中，网页规则目录由同一份定义自动生成。

计算使用 Python 3.12 与锁定的 lunar_python==1.4.8；只调用农历转换/节气算法，不调用其节日清单与调休表。算法完全离线，不以他人 ICS、Apple 日期、私人 API 为上游。

参考：[USNO 复活节算法](https://aa.usno.navy.mil/faq/easter)、[HKO 二十四节气](https://www.hko.gov.hk/tc/gts/time/24solarterms.htm)、[HKO 公农历对照](https://www.hko.gov.hk/tc/gts/time/conversion.htm)、[算法库与许可证](https://pypi.org/project/lunar_python/1.4.8/)。第三方许可见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

## 配置与本地命令

[config.toml](config.toml) 使用 Python 标准库读取，无需另装 YAML 解析器。默认前后各三年，以 Asia/Shanghai 当前年份判断；2026 年导出 2023—2029，2027 年导出 2024—2030。保留历史修订状态和校验资料。

类别开关控制传统、常见、圣周、节气；festivals.disabled_ids 按规则文件中的固定 ID 关闭节日；solar_terms.disabled_ids 可关闭指定节气。小年地域和复活节星期一各有开关。关闭感恩节显示不会妨碍计算黑色星期五；关闭清明节本体与关闭清明节气是两个独立选项。

所有本机命令由 PowerShell 7 发起，在专用 Python 3.12 环境中运行：

~~~powershell
python -m pip install --require-hashes -r requirements.txt -r requirements-test.txt
python -B scripts/preflight.py
python -B -m unittest discover -s tests -v
python -B scripts/calendar_cli.py --output D:/CodexProjects/codex_workbench/projects/personal-calendar/outputs/release-candidate --state-output D:/CodexProjects/codex_workbench/projects/personal-calendar/outputs/candidate-events.json
python -B scripts/automation.py verify --site D:/CodexProjects/codex_workbench/projects/personal-calendar/outputs/release-candidate
~~~

生成必须使用全新、位于源码仓库外的空目录；不覆盖上一成功候选。可加 --as-of 2026-12-31T16:00:00+00:00 测跨年，--config 指定配置，--state 指定历史修订输入。verify 是线上回读命令，需要已经部署同一候选。本地构建不主动提交修订状态，由发布成功步骤维护。

主要模块：calendar_core.py 负责规则、身份与 ICS；calendar_cli.py 生成候选；validate_calendar.py 独立解析验证；automation.py 负责调度判断、发布回读、健康及告警；tests/fixtures/hko 保存带来源和哈希的独立权威对照。

UID 来自稳定节日 ID 与所属公历/农历年度，与标题和计算出的日期无关。跨年窗口移出后保留修订条目；内容变化才提高 SEQUENCE 并更新时间戳。CRLF、UTF-8 75 字节折行、TEXT 转义、全天排他结束日期均自动验证。

## 自动维护与发布

- 每天北京时间 06:17 轻量判断。每周一、当年/当月尚无成功记录、上次失败时运行完整检查；代码配置变化与手动触发立即运行。平台可能延迟或丢失调度。
- 正常日期完全本地计算，不抓政府或 Apple 数据。无维护任务时不安装依赖、不构建、不访问外部日期站点。
- 测试 → 候选三份 ICS → 与线上版本比较 → 显式 Pages 部署 → 匿名 HTTP/MIME/全部内容哈希回读 → 持久化修订与真实健康记录。
- 三份 ICS 同版部署；内容无变化时跳过部署，不重写事件。月度首个完整成功检查保存健康记录；普通周检只留 Actions 日志，不提交无意义日历变化。
- 验证失败不发布；部署或回读失败不记成功，次日重试。维护失败复用一个 Issue，恢复后关闭；正常运行不主动发消息。请在 GitHub 订阅此仓库 Issue/失败 Actions 通知。
- 最小 job 权限、Actions 固定提交 SHA、依赖锁版本与哈希，不需要长期私人访问令牌。Dependabot 月度归组更新，安全更新不并入普通版本组；任何依赖/算法/工作流更新都不自动合并。

月度健康提交降低公开仓库 60 天无活动导致定时工作流停用的风险，但不保证平台永不停调度。没有外部监控，完全停跑无法靠自身告警。每年查看一次 Actions、覆盖范围和通知状态，集中审阅非紧急依赖更新。[GitHub 调度限制](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)

## 回滚

每次线上核验成功保存 last-good-site artifact，保留 90 天。到 Actions → Update calendar → Run workflow，将之前**成功的 main 运行 ID**填入 rollback_run_id；留空则正常生成。恢复完整静态版本并重新回读，不倒退事件修订历史。此恢复只改变发布内容，后续常规更新仍按当前源码生成；需要长期停留旧版本时先修正或回退引入问题的代码。

~~~powershell
gh workflow run update-calendar.yml --repo SHIKI1255/personal-calendar -f rollback_run_id=RUN_ID
~~~

超过 artifact 保留期仍可从 Git 历史中的代码、规则和修订状态重建，但必须重新测试；不要通过强制推送抹去历史。

## 验证范围

首版逐日核对 2023—2029 年 2,557 个公历日的农历转换、168 个节气以及全部生成的农历节日；2022 年 HKO 原文只提供跨年月份上下文。测试预期来自 HKO 快照，不由被测算法生成。HKO 不作为自动生成上游。算法与权威基准冲突阻止发布。

另外覆盖复活节独立算法对照、闰年/闰月、除夕、星期规则、圣周、配置、同日不同节日、UID、折行与结束日期、修订和字节稳定、失败保护、线上校验、告警去重及回滚验证。手机订阅和刷新仍需真实用户验收，不以这些测试代替。
