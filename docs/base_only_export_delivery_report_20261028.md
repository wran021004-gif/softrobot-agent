# Base-only Benchmark：MuJoCo 实验资料包交付报告

交付日期：2026-10-28。

本报告可单独转发。接收方使用数据时，请同时取得 `base_only_accepted_20261028.zip`，解压到任意目录。下文所有文件名和运行命令均相对于解压后的资料包根目录，不依赖导出机器的盘符、用户名、Python 环境或原始私有 Store。

本次交付六项历史独立 accepted 任务的可移植实验资料，共六个原始 MuJoCo XML、十条完整成功轨迹、30 个 CSV。M1、M2 各含三个独立条件，M3–M6 各含一个条件。M3 保留 development draft 身份，尚不是已批准的正式 Benchmark。

| 任务 | 条件 | 每条状态／参考 CSV 行数 | 每条控制 CSV 行数 | 物理 timestep |
|---|---|---:|---:|---:|
| M1 | central_high、positive_high、negative_low | 601 | 30 | 0.001 s |
| M2 | zero、positive、negative | 701 | 35 | 0.0005 s |
| M3 | default | 1001 | 50 | 0.0005 s |
| M4 | default | 601 | 30 | 0.001 s |
| M5 | default | 601 | 30 | 0.001 s |
| M6 | default | 601 | 30 | 0.001 s |

行数不含表头。状态与参考 CSV 均包含 t=0；累计真实物理状态为 6,710 行。轨迹记录覆盖每个实际积分步，没有插值、补帧或用规划轨迹替代物理状态。

验证结论：模型加载、文件 SHA-256、关节地址与通道顺序、时间网格、有限数值、六根腱的 fixed_base 起点、M1/M2 共享物理结构、M2 世界系 COM 外力和 M6 刚性负载及接触记录全部通过。十条轨迹与原控制周期记录的 qpos、qvel、末端位置／速度、张力及适用工具轴最大比较差值均为 0；逐步位姿和速度与保存状态一致。六项均通过离线渲染和标准 MuJoCo viewer 动画启动检查。

M2 positive 原速度裕量为 `5.1176539919012276e-08 m/s`，保留原双精度数据，没有舍入重判。M6 保留实际 20 g 刚性工具、COM 与完整惯量，零环境接触检查通过。历史 accepted 与本次导出一致性分别记录，原任务、结构、控制源和历史科学结果未改写。

本次只执行十条确定性导出重放，共 6,700 次实际 `mj_step`，捕获耗时约 6.61 秒；验证及动画检查没有增加物理积分，也没有优化或新一轮 Benchmark 搜索。

资料包内，各 M1–M6 目录包含 `robot.xml`、`structure.json`、`structure.md`、`joint_map.json` 和 README。各条件目录包含中文任务说明、原任务与初态、逐步轨迹、原张力控制序列、可视化参考、来源身份和独立验证记录。全部采用 SI 单位，坐标系与采样语义详见根 README。

精确模型 XML SHA、candidate、控制源、任务身份、raw/evaluation/profile/result 绑定见 `delivery_report.json` 的 `source_identities` 及各条件的 `provenance.json`。完整验证见 `validation.json`；文件完整性清单见 `manifest.json`。这些资料在包内即可读取，无须访问导出机器。

使用 Python 3.11 创建接收方自己的环境，进入资料包根目录后安装依赖：

```powershell
python -m venv .viewer-env
. ./.viewer-env/Scripts/Activate.ps1
python -m pip install -r requirements.txt
```

播放已保存的状态，不重新积分：

```powershell
python ./scripts/view_trajectory.py --benchmark M1 --condition central_high --speed 0.5 --loop
```

空格暂停／继续，R 重播，L 切换循环。标准 viewer 需要桌面和 OpenGL。

校验完整资料包，不执行物理积分：

```powershell
python ./scripts/validate_package.py
```

可按需显式重新积分原控制序列；此命令会产生新的积分计算及输出：

```powershell
python ./scripts/simulate_controls.py --benchmark M2 --condition positive --output ../replay_M2_positive
```

验证环境为 Python 3.11.16、MuJoCo 3.13.0、NumPy 2.4.6，Windows 已验证；Linux 命令见根 README，尚未验证。

该模型是每段 12-cell、理想张力驱动的离散仿真模型，不是制造 CAD。成功张力序列尚不是已验证可直接下发真机的驱动命令；本次不涉及电机、电控、通信、制造公差或硬件安全认证。

原研究版本：`314f75a4971e0a9e4521fe79ddf744ff71de61e2`，分支 `research/base-only-benchmark-feasibility`。导出实现版本：`1ad5e527ffbdb28054e090682186c699ef43a69f`，分支 `feat/base-only-benchmark-export`。新增／修改文件清单见包内 `code_provenance.json`。本次报告修订仅调整交付说明及包装，不改变上述科学数据和导出实现版本。

完整 XML、获胜控制、原始证据及 ZIP 没有上传远端；本报告与工具代码不包含完整成功结构或控制序列。

30 个 CSV 的逐文件明细：

| CSV（资料包内相对路径） | 数据行（不含表头） | 网格 s |
|---|---:|---:|
| M1/central_high/control_schedule.csv | 30 | 0.02 |
| M1/central_high/reference.csv | 601 | 0.001 |
| M1/central_high/trajectory_timestep.csv | 601 | 0.001 |
| M1/positive_high/control_schedule.csv | 30 | 0.02 |
| M1/positive_high/reference.csv | 601 | 0.001 |
| M1/positive_high/trajectory_timestep.csv | 601 | 0.001 |
| M1/negative_low/control_schedule.csv | 30 | 0.02 |
| M1/negative_low/reference.csv | 601 | 0.001 |
| M1/negative_low/trajectory_timestep.csv | 601 | 0.001 |
| M2/zero/control_schedule.csv | 35 | 0.01 |
| M2/zero/reference.csv | 701 | 0.0005 |
| M2/zero/trajectory_timestep.csv | 701 | 0.0005 |
| M2/positive/control_schedule.csv | 35 | 0.01 |
| M2/positive/reference.csv | 701 | 0.0005 |
| M2/positive/trajectory_timestep.csv | 701 | 0.0005 |
| M2/negative/control_schedule.csv | 35 | 0.01 |
| M2/negative/reference.csv | 701 | 0.0005 |
| M2/negative/trajectory_timestep.csv | 701 | 0.0005 |
| M3/default/control_schedule.csv | 50 | 0.01 |
| M3/default/reference.csv | 1001 | 0.0005 |
| M3/default/trajectory_timestep.csv | 1001 | 0.0005 |
| M4/default/control_schedule.csv | 30 | 0.02 |
| M4/default/reference.csv | 601 | 0.001 |
| M4/default/trajectory_timestep.csv | 601 | 0.001 |
| M5/default/control_schedule.csv | 30 | 0.02 |
| M5/default/reference.csv | 601 | 0.001 |
| M5/default/trajectory_timestep.csv | 601 | 0.001 |
| M6/default/control_schedule.csv | 30 | 0.02 |
| M6/default/reference.csv | 601 | 0.001 |
| M6/default/trajectory_timestep.csv | 601 | 0.001 |
