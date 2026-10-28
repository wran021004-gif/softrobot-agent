"""Assemble a portable delivery report from actual checks and frozen metadata."""
import argparse
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from phs2d_io import TASK_DIR,RESEARCH_SHA,read,write,sha,require


def generate(package,validation_path):
    validation=read(validation_path)
    require(validation['status']=='passed' and len(validation['active']['results'])==10 and
            len(validation['passive']['results'])==11 and validation['physics_steps']==0, 'ALL_21_CHECKS_REQUIRED')
    base=package/TASK_DIR;dataset=read(base/'dataset.json');structure=read(base/'structure.json')
    viewer=read(package/'viewer_validation.json')['phs2d']
    require(viewer['status']=='passed' and viewer['gui_smoke_executed'],'ACTUAL_VIEWER_CHECKS_REQUIRED')
    code_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip()
    suites=['tests.research.test_phs2d_package','tests.research.test_base_only_export']
    test_run=subprocess.run([sys.executable,'-B','-m','unittest',*suites],cwd=ROOT,capture_output=True,text=True)
    require(test_run.returncode==0,'FOCUSED_TEST_FAILURE:'+test_run.stderr)
    test_count=int(re.search(r'Ran (\d+) tests?',test_run.stderr).group(1))
    baseline=read(base/'evidence/legacy_hash_snapshot.json')
    immutable={name:identity for name,identity in baseline['files'].items() if name not in baseline['mutable_root_files']}
    require(all(sha(package/name)==identity for name,identity in immutable.items()),'LEGACY_PRESERVATION')
    report=dict(version='phs2d_package_delivery_v1',status='validated_for_publication',
        package_directory='.',phs_directory=TASK_DIR,source_research_commit=RESEARCH_SHA,
        code_commit=code_commit,code_branch='feat/phs2d-benchmark-package-export',
        source_export_commit='c8085b8faa4d802d529d4bc8468f7c3c907662c4',
        xml_sha256=structure['xml_sha256'],source_design_sha256=structure['source_design_sha256'],
        physics_identity=structure['physics']['identity'],source_assembly=structure['source_assembly'],
        fixed_payout_lengths=read(base/'payout_lengths.json'),trajectories=dataset['trajectories'],
        total_csv_rows=sum(e['rows'] for e in dataset['trajectories']),
        total_csv_bytes=sum(e['csv_bytes'] for e in dataset['trajectories']),
        total_npz_bytes=sum(e['npz_bytes'] for e in dataset['trajectories']),
        validation=validation,viewer_validation=viewer,all_legacy_immutable_hashes_preserved=True,
        original_files_snapshotted=len(baseline['files']),immutable_original_files_preserved=len(immutable),
        tests=dict(focused_tests_passed=test_count,physical_integration_executed=False,suites=suites,
                   runner_output=test_run.stderr.strip()),
        actual_new_physics_steps=0,scientific_store_access='SQLite mode=ro&immutable=1, readonly blob reads only',
        zip_publication_record='../base_only_accepted_20261028.phs2d-publication.json',
        zip_policy='Build new ZIP64 archive, CRC-test and verify every member SHA-256; keep byte-identical old ZIP backup; atomic replace.',
        validity='Development independent numerical PHS witness; not registered TaskAdapter/SELECT, hardware or cross-platform performance.')
    write(package/'phs2d_delivery_report.json',report)
    write(package/'validation.json',validation)
    old_report=read(package/'delivery_report.json')
    legacy=old_report.get('legacy',old_report)
    write(package/'delivery_report.json',dict(version='base_only_delivery_v2',legacy=legacy,
        phs2d_report='phs2d_delivery_report.json',new_physics_steps=0,code_commit=code_commit,
        all_legacy_immutable_hashes_preserved=True,active_trajectories_passed=10,passive_trajectories_passed=11))
    old_audit=read(package/'export_audit.json')
    write(package/'export_audit.json',dict(version='base_only_audit_v2',legacy=old_audit.get('legacy',old_audit),
        phs2d=dict(status='passed',original_physical_timestep_arrays_preserved=True,true_t0_snapshots=True,
            maximum_csv_npz_shared_error=0.,maximum_forward_pose_error=max(r['max_forward_pose_error'] for r in validation['passive']['results']),
            original_xml_hash_verified=True,new_physics_steps=0,private_store_copied=False,
            all_legacy_immutable_hashes_preserved=True,source_commit=RESEARCH_SHA)))
    provenance=read(package/'code_provenance.json');provenance['code_commit']=code_commit
    write(package/'code_provenance.json',provenance)
    rows=['| 目录 | CSV 数据行 | CSV 列 | CSV bytes | NPZ bytes |','|---|---:|---:|---:|---:|']
    for e in dataset['trajectories']:
        rows.append(f"| {e['directory']}/ | {e['rows']} | {e['csv_columns']} | {e['csv_bytes']} | {e['npz_bytes']} |")
    text=f'''# PHS-2D 增量导出交付报告

原资料包目录为本文件所在目录，新任务目录为 [{TASK_DIR}/]({TASK_DIR}/README.md)。
原 M1–M6 的模型、控制、轨迹、证据和旧脚本字节全部保留。
本次新增物理积分 **0 次**，没有重优化结构、改写成功解或修改原验收。

## 数据文件和真实规模

以下每个目录均在 {TASK_DIR}/ 下；CSV 行数不含表头：

{chr(10).join(rows)}

每条目录包含 trajectory_timestep.csv、states_timestep.npz、external_force_schedule.csv、initial_state.json、replay_spec.json、validation.json。
十个加载目录另有 original_evaluation.json。全部 11 条共 {report['total_csv_rows']} 行，
CSV 总大小 {report['total_csv_bytes']} bytes，NPZ 总大小 {report['total_npz_bytes']} bytes。
每条 NPZ 含真实 t=0 和 32,000 个原积分后状态；float64 和完整 qacc 均保留。

## 身份与精度

- 科研来源提交：`{RESEARCH_SHA}`。
- 导出代码提交：`{code_commit}`，远端代码分支 `feat/phs2d-benchmark-package-export`，仓库 wran021004-gif/softrobot-agent。
- XML SHA-256：`{structure['xml_sha256']}`，与冻结 solution/model.xml 字节完全一致。
- 源设计文件 SHA-256：`{structure['source_design_sha256']}`；物理身份：`{structure['physics']['identity']}`。
- 九段、72 cells、144 DOF、四根 Base-only 被动腱、八块实体导向板、原连接件与偏心 payload；无 actuator 或额外世界/Tip 约束。
- 固定 payout 顺序和值见 [{TASK_DIR}/payout_lengths.json]({TASK_DIR}/payout_lengths.json)，四个值均为 0.39274245978073885 m。
- 封存原 NPZ 的 SHA 已核验；原 32,000×442 float64 数组与交付 NPZ 后 32,000 行的数组 SHA 完全相同。
- CSV/NPZ 所有共享字段逐行完全一致，最大绝对误差 0；全部 352,011 帧独立 forward 位姿误差 0。
- t=0 均来自各原始 snapshot，未复制首个 post-step 帧，也未插值。
- qacc、原张力/腱长与独立重建位姿相位分开记录，绝不以 forward 重算反力替代原张力。
- payload 的原 XML 完整惯量张量精确保留；MuJoCo 主轴表示重构约有 2e-15 kg·m² 舍入，单列为编译表示诊断，不改变物理或验收。

## 实际验证

原 M1–M6 的 10 条轨迹通过原 validate_package.py 完整校验；PHS 11 条通过新增逐帧校验。
原 {len(baseline['files'])} 个文件有导出前哈希快照；其中 {len(immutable)} 个不可变文件逐字节保留。
根 README、清单、来源索引和验证/交付报告按增量 v2 更新，原根报告内容在 JSON 的 legacy 中保留。
原 manifest.trajectories 仍只有十条主动任务；PHS 以 passive_benchmarks 单独类型化组织。

已实际测试：无 GUI 下全帧位姿检查、原九段 XML 加载、MuJoCo 离线 PNG 渲染、3 秒 GUI 动画、
动力学复现 --check-only；全部物理积分入口在只读工具中禁止。
GUI 实际帧数、环境、完整相对命令和脚本 SHA 见 [viewer_validation.json](viewer_validation.json)。
暂停/继续、循环、重播、速度调整逻辑与原主动导出回归共 {test_count} 项测试通过。
真正 dynamics 重放未自动运行；接收方以后须明确指定新包外输出目录主动执行。
Linux 启动命令已提供但未验证。

## ZIP 与边界

最终 ZIP 为包外相邻的 ../base_only_accepted_20261028.zip；旧 ZIP 逐字节备份为 ../base_only_accepted_20261028.before_phs2d.zip。
ZIP 使用临时文件构建，逐成员 SHA-256 和 CRC 检查通过后原子替换；最终大小、ZIP SHA、备份身份及校验状态
记录在包外同名发布记录文件 ../base_only_accepted_20261028.phs2d-publication.json，避免 ZIP 对自身哈希的循环依赖。
该记录可随 ZIP 另行转发，不是查看、校验和运行模型所需的包内依赖。
ZIP64 支持大文件；清单全部使用包内相对路径。代码分支不包含 CSV、NPZ、私有 Store 或 ZIP。

PHS 结论仅是原开发性独立数值见证，尚未注册正式 TaskAdapter/SELECT，不代表真机或跨平台性能验证。
模型省略真实腱摩擦/弹性、轴向伸长、剪切、扭转及自碰撞；材料黏性未真材标定，几何检查仅覆盖保存姿态。
没有电机、电控、通信或真实张力控制器。查看/校验只需 MuJoCo 和 NumPy，不需科研 Agent、Provider、Store 或 Harness。
'''
    (package/'phs2d_delivery_report.md').write_text(text,encoding='utf8')
    old_md=(package/'delivery_report.md').read_text(encoding='utf8')
    marker='<!-- PHS2D_REPORT_INCREMENT -->'
    if marker in old_md:old_md=old_md.split(marker,1)[0].rstrip()
    (package/'delivery_report.md').write_text(old_md+'\n\n'+marker+'\n\n## PHS-2D 增量 v2\n\n'
        '原 M1–M6 十条记录保持不变；新增十条被动力工况和一条无力基准，新增物理积分为零。\n'
        '完整增量报告见 [phs2d_delivery_report.md](phs2d_delivery_report.md)。\n',encoding='utf8')
    (package/'VERSION.md').write_text('''# base_only_package_v2_with_passive_phs2d

在原 base_only_package_v1 上增量加入 PHS2D_passive_head_stabilization。
M1–M6 的文件身份、十条轨迹与历史验收不变；旧主动导出 6,700 步为历史成本。
本次 PHS 导出与校验新增积分 0。主动 trajectories 字段保持原语义，新增 passive_benchmarks。
所有旧脚本保留，新根入口 scripts/validate_all.py 采用类型化分派。
ZIP 发布完整性与大小见包外同名 phs2d-publication.json。
''',encoding='utf8')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--package',type=Path,required=True);p.add_argument('--validation',type=Path,required=True)
    args=p.parse_args();generate(args.package.resolve(),args.validation)


if __name__=='__main__':main()
