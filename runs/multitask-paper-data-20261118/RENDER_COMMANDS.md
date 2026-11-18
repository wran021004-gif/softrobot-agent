# 重现渲染

PowerShell，工作目录D:\softrobot-agent：

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONDONTWRITEBYTECODE='1'
$py='C:/Users/gugugaga/miniconda3/envs/softagent/python.exe'
& $py -u runs/multitask-paper-data-20261118/scripts/extract_render_inputs.py
& $py -u runs/multitask-paper-data-20261118/scripts/add_phs_reference_motion.py
& $py -u runs/multitask-paper-data-20261118/scripts/render_native_assets.py --mode all
& $py -u runs/multitask-paper-data-20261118/scripts/render_intermediate_stills.py
& $py -u runs/multitask-paper-data-20261118/scripts/build_delivery.py
```

MuJoCo3.13.0，1600×1200，25fps，原生Renderer、4samples、4096阴影；8MiB编译线程栈用于Windows模型编译。既有视觉模板、原模型、相机参数见每任务VISUAL_XML/*.check.json和CAMERA_SETTINGS.json。所有新视觉geom为mass=0、contype=0、conaffinity=0，编译后质量/惯量、骨架、关节、腱路、原碰撞geom和积分设置与对应原模型比较通过。

视频使用本机已有FFmpeg：D:/Program Files (x86)/英雄联盟(26)/Cross/icreate/recorder-release/ffmpeg.exe，h264_nvenc、QP18、yuv420p、faststart。仅编码原生帧，不叠字、不裁切、不重画。没有重新积分或构造新轨迹。每帧选择最近的原保存状态，不插值姿态；精确播放倍率与来源见VIDEO_MANIFEST及frame_sources.csv。

定量图复现脚本分别为T01/make_quantitative_figures.py（八任务）、T07/plot_t07_paper.py、T10/make_paper_figures.py。分Study资源与补充索引的复现脚本为scripts/consolidate_resources.py、scripts/consolidate_supplement.py。
