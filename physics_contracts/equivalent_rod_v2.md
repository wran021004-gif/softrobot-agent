# Round 9 等效离散杆 V2（未标定）

授权来源：本轮用户提示；仅 reach_free。legacy_v1_surrogate 文件和默认路径不变。
全部使用 SI；世界基座原点、初始骨架 +x，qpos=qvel=0，无松弛阶段。
MuJoCo 每段保留 y/z 两个 hinge；MATLAB 保留 y hinge，正角使骨架向 -z 弯曲。
平面外 y 运动、z hinge 和自碰撞未建模；MATLAB 不是物理真值。

8 段等长 ds=L/8，每个关节代表一个 ds 控制体，包括根部；弯曲能
0.5 integral EI*kappa^2 ds 近似为 0.5(EI/ds)(q-q0)^2。
k_theta=EI/ds [N m/rad]；c_theta=粘性系数/ds [N m s/rad]。
EI 从根部到末端按关节索引线性变化，自然 y 角=-自然总弯曲角/8，z 自然角为零。
自然角改变弹簧预载，不改变初始 qpos。无关节限位。

等效代理质量模式：每段质量=lambda*ds，重心 ds/2，惯性为均匀圆柱
Ixx=mr²/2，Iyy=Izz=m(3r²+ds²)/12；碰撞外形仍是现有胶囊。
这是明确的等效质量/惯性模型，不声称是实心胶囊或真实材料关系；EI 独立。
V1 基线从已编译 MuJoCo 模型读取真实质量/惯性，不能直接用 V2 替代旧质量。

腱编号与旧版一致，偏置 (r cos(angle), r sin(angle))，angle=2pi*i/nt。
每根路线连接固定 base site 与各段末端 site；MATLAB 使用旋转后的实际折线路径及其 Jacobian。
参考长度 L_ref=L。gear=1，无额外腱动态，原始驱动力=-T，T=clip(kp*(路径长-命令长),0,Fmax)。
kp 是长度伺服增益，不是腱材料刚度；没有另加弹性腱，弹性腱刚度不可选。
C1 固定命令；C2 复用 PCC Jacobian-transpose 反馈，离散更新并保持指令。
命令=L-r*(bend_y*cos(angle)+bend_z*sin(angle))+bias*L，主动项限于 ±0.25L，
bias 在 [-0.02,0.05]L；最终命令裁剪至 [0.73,1.30]L，始终为正。
C2 命令变化率为 (0,2]L/s，更新间隔为 1..100 个冻结 0.002s 步长；
反馈 gain 为 [0,100] rad²/m²，单次 bend 变化最大 0.2rad。C1 从 t=0 固定施加，无额外 ramp。

任务 floor=-0.02m，接触开关不变。MATLAB 接触仅为胶囊中心线端点最低处的
两端各半权重的单边法向罚力 max(0,5000*penetration-5*w*vnormal)，只在 penetration>0 时生效；
w=min(1,penetration/1e-4) 平滑接触阻尼的启用。两点求积避免近水平段的最低端切换导致整段力矩跳变。
首次正式基线用最低端接触导致 ode15s 207959 次 RHS 后 120s 超时；该版本保留，修复后的源哈希产生新缓存身份。
不模拟摩擦/扭转接触及 MuJoCo soft constraint。记录 gap 和法向近似力，
接触显著时标记 CONTACT_APPROXIMATION；模型排序必须由 MuJoCo 对照。
根部外形半径>0.02m 时初始地面相交无法由固定基座消除，明确标记而不改初始姿态。

MATLAB 用拉格朗日质量矩阵、COM Jacobian、解析 centripetal bias，ode15s，
输出间隔 0.002s、RelTol=1e-5、AbsTol=1e-7、MaxStep=0.02s。
输出采样/求解器内部网格/RHS 次数分别记录。极值仅指保存采样极值。
优化目标唯一为 t=2s 末端欧氏误差，辅助项权重全部 0；无效或未到终点不可获胜。
有界坐标模式搜索使用对数 EI/粘性/密度/增益空间；仅局部搜索，无全局最优声明。
