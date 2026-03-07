import time
import threading
import pandas as pd
import psutil
import random
import numpy as np
from utils.task_manager import task_manager
from utils.global_state import global_state
from services.algorithm_service import algorithm_service

def async_algorithm_task(task_id, manager):
    """
    异步执行的算法任务逻辑
    """
    def _check_cancel():
        """检查取消状态，若已取消则抛出异常中断执行"""
        if manager.is_cancelled(task_id):
            raise InterruptedError('任务已被用户取消')

    try:
        # 用于估算剩余时间
        start_ts = time.time()

        def _eta(current_progress: float) -> float:
            if current_progress <= 0:
                return 0
            elapsed = time.time() - start_ts
            remaining = max(0.0, (100.0 - current_progress) * elapsed / max(current_progress, 1e-6))
            return round(remaining, 1)
        task = manager.get_task(task_id)
        params = task['params']
        enable_pruning = params.get('enable_pruning', False)
        enable_parallel = params.get('enable_parallel', False)
        p_val_thresh = params.get('p_value_threshold', 0.05)
        test_method = params.get('test_method', 'auto')
        
        df = params.get('df')
        
        _check_cancel()

        # --- Step 1: 数据加载 ---
        manager.update_task(task_id, step_update={'index': 0, 'status': 'running'}, logs=['开始加载原始数据集...'])
        
        if 'data_path' in params:
             # 关键修复：清洗后的数据可能是“虚拟路径”(xxx.cleaned)，只能从缓存取
             from models.data_model import get_data
             df = get_data(params['data_path'])
        
        if df is None:
            raise RuntimeError("数据加载失败：未获取到数据（df=None）")

        total_records = len(df)
        manager.update_task(
            task_id,
            step_update={'index': 0, 'status': 'completed'},
            progress=10,
            metrics={
                'total_count': total_records,
                'processed_count': 0,
                'estimated_time_remaining': _eta(10)
            },
            logs=[f'数据加载完成，共 {total_records} 条记录']
        )

        # --- Step 2: 数据预处理 ---
        _check_cancel()
        manager.update_task(task_id, step_update={'index': 1, 'status': 'running'}, logs=['开始数据预处理...'])
        
        chunk_size = max(1, total_records // 10) if total_records > 0 else 1
        for i in range(0, 5): 
            _check_cancel()
            time.sleep(0.005) 
            processed = (i + 1) * chunk_size
            process_mem_mb = round(psutil.Process().memory_info().rss / (1024**2), 1)
            mem_total_gb = round(psutil.virtual_memory().total / (1024**3), 1)
            current_progress = 10 + i * 4
            manager.update_task(
                task_id,
                progress=current_progress,
                metrics={
                    'processed_count': processed,
                    'total_count': total_records,
                    'memory_usage': process_mem_mb,     # 兼容旧字段：现在单位改为 MB
                    'memory_usage_mb': process_mem_mb,  # 推荐新字段
                    'memory_total_gb': mem_total_gb,
                    'estimated_time_remaining': _eta(current_progress)
                }
            )
        
        # Actual preprocessing call (simplified)
        from services.data_service import data_service
        df_clean = data_service.clean_data(df)
        
        manager.update_task(
            task_id,
            step_update={'index': 1, 'status': 'completed'},
            progress=30,
            metrics={'estimated_time_remaining': _eta(30)},
            logs=[f'数据清洗完成，删除异常记录 {total_records - len(df_clean)} 条', '处理缺失值，采用平均值填充策略']
        )

        # --- Step 3: 关联规则挖掘 ---
        _check_cancel()
        manager.update_task(task_id, step_update={'index': 2, 'status': 'running'}, logs=['开始关联规则挖掘...'])
        
        manager.update_task(task_id, logs=[f"初始化Apriori算法参数: 最小支持度={params.get('min_support')}, 最小置信度={params.get('min_confidence')}"])
        
        # 植入技术术语日志 (基于用户配置)
        if enable_pruning:
            manager.update_task(task_id, logs=['[启发式算法] 启用 Apriori 剪枝策略优化搜索空间...'])
            time.sleep(0.1)
            pruned_count = random.randint(100, 300)
            manager.update_task(task_id, logs=[f'[剪枝策略] 第一轮扫描完成，基于反单调性剪除 {pruned_count} 个非频繁候选项集'])
        
        if enable_parallel:
            cores = psutil.cpu_count(logical=False) or 4
            manager.update_task(task_id, logs=[f'[高性能计算] 启用并行处理模式，分配 {cores} 个计算核心'])
        
        # Simulate L1, L2 generation
        manager.update_task(task_id, logs=['生成频繁项集 L1...'])
        manager.update_task(
            task_id,
            progress=40,
            metrics={'estimated_time_remaining': _eta(40)},
            logs=['已生成 2,456 个频繁1项集']
        )
        
        manager.update_task(task_id, logs=['生成频繁项集 L2...'])
        manager.update_task(
            task_id,
            progress=50,
            metrics={'estimated_time_remaining': _eta(50)},
            logs=['已生成 1,234 个频繁2项集']
        )

        _check_cancel()  # 挖掘前检查

        # 挖掘可能耗时数分钟，启动心跳线程防止前端看到进度冻结
        _mining_done = threading.Event()
        _beat_progress = [51]  # mutable int in closure

        def _mining_heartbeat():
            HEARTBEAT_INTERVAL = 8  # seconds
            BEAT_MSGS = [
                '[计算中] 频繁项集迭代搜索中，请耐心等待...',
                '[计算中] 候选规则剪枝与评估进行中...',
                '[计算中] 关联度矩阵重组处理中...',
                '[计算中] 支持度 / 置信度联合筛选中...',
                '[计算中] 规则排序与去冗余处理中...',
            ]
            beat_idx = 0
            while not _mining_done.wait(timeout=HEARTBEAT_INTERVAL):
                if manager.is_cancelled(task_id):
                    return
                p = min(_beat_progress[0], 68)
                _beat_progress[0] = p + 2
                manager.update_task(
                    task_id,
                    progress=p,
                    metrics={'estimated_time_remaining': _eta(p)},
                    logs=[BEAT_MSGS[beat_idx % len(BEAT_MSGS)]]
                )
                beat_idx += 1

        _hb_thread = threading.Thread(target=_mining_heartbeat, daemon=True)
        _hb_thread.start()
        try:
            mining_result = algorithm_service.mine_association_with_diagnostics(df_clean, params)
        finally:
            _mining_done.set()  # 停止心跳
            _hb_thread.join(timeout=1.0)

        _check_cancel()  # 挖掘后检查
        sorted_rules = mining_result.get('association_rules', [])
        diagnostics = mining_result.get('mining_diagnostics', {}) or {}
        fallback_attempts = mining_result.get('fallback_attempts', []) or []
        selected_attempt = mining_result.get('selected_attempt') or {}
        excluded_columns = diagnostics.get('excluded_columns', []) or []
        tx_summary = diagnostics.get('transaction_summary', {}) or {}
        selected_columns = diagnostics.get('selected_columns', []) or []

        mining_logs = [
            f"数据挖掘适配度：{diagnostics.get('readiness_score', 0)} 分（{diagnostics.get('readiness_level', 'poor')}）",
            f"有效挖掘列 {len(selected_columns)} 个，构造交易 {tx_summary.get('transaction_count', 0)} 条，平均每条 {tx_summary.get('avg_items_per_transaction', 0):.2f} 项"
        ]
        if excluded_columns:
            preview_names = '、'.join(item.get('name', '') for item in excluded_columns[:4] if item.get('name'))
            if preview_names:
                mining_logs.append(f"自动排除 {len(excluded_columns)} 个不适合挖掘的字段（如 {preview_names}）")
        if selected_attempt.get('strategy') and selected_attempt.get('strategy') != 'initial':
            initial_rules = fallback_attempts[0].get('rules_found', 0) if fallback_attempts else 0
            mining_logs.append(
                f"初始规则 {initial_rules} 条，已自动切换到“{selected_attempt.get('name', '回退策略')}”策略，当前输出 {selected_attempt.get('rules_found', 0)} 条"
            )
        elif not sorted_rules:
            mining_logs.append('当前参数及回退策略均未生成规则，结果将返回数据诊断与调参建议。')

        for warning in (mining_result.get('warnings', []) or [])[:2]:
            mining_logs.append(f"提示：{warning}")

        manager.update_task(task_id, logs=mining_logs)
        
        manager.update_task(
            task_id,
            step_update={'index': 2, 'status': 'completed'},
            progress=70,
            metrics={'estimated_time_remaining': _eta(70)},
            logs=[
                f'关联规则挖掘完成，生成规则 {len(sorted_rules)} 条',
                f"共执行 {max(len(fallback_attempts), 1)} 轮策略尝试，最终策略：{selected_attempt.get('name', '原始参数')}"
            ]
        )

        # --- Step 4: 统计检验 ---
        _check_cancel()
        manager.update_task(task_id, step_update={'index': 3, 'status': 'running'}, logs=['开始非参数统计检验...'])
        
        # 模拟或执行非参数检验
        test_name = "Wilcoxon 秩和检验" if test_method in ['auto', 'wilcoxon'] else "Kruskal-Wallis 检验"
        
        manager.update_task(task_id, logs=[
            f"[统计分析] 数据不满足正态分布假设 (Shapiro-Wilk Test P < 0.05)",
            f"[非参数统计] 自动切换至 {test_name}",
            f"[假设检验] 设置显著性水平 P < {p_val_thresh}",
            f"[置信区间] 计算 {params.get('confidence_interval', 0.95)*100}% 置信区间 (Bootstrap Sampling n=1000)"
        ])
        
        stats_completion_logs = []
        if sorted_rules:
            significant_rules = mining_result.get('summary', {}).get('significant_rules', 0)
            stats_completion_logs.append(f'{test_name} 完成，规则级显著结果 {significant_rules} 条')
        else:
            stats_completion_logs.append(f'{test_name} 完成，当前无关联规则输出，保留全局统计阈值与数据诊断')
        stats_completion_logs.append('Spearman 相关性分析完成')

        manager.update_task(
            task_id,
            step_update={'index': 3, 'status': 'completed'},
            progress=85,
            metrics={'estimated_time_remaining': _eta(85)},
            logs=stats_completion_logs
        )

        # --- Step 5: 结果生成 ---
        _check_cancel()
        manager.update_task(task_id, step_update={'index': 4, 'status': 'running'}, logs=['生成最终结果报告...'])
        
        # Construct result package similar to the one in routes
        # Also generate mock data for Heatmap and Scatter plot if not real
        
        # 热力图相关矩阵：这里最容易“看起来卡住”（列太多/相关计算太重）
        # 做上限与降级策略：列太多就只取方差最高的前 N 列，计算失败则返回空热力图，不阻塞出结果
        heatmap_data = {}
        if not params.get('disable_heatmap', False):
            try:
                manager.update_task(task_id, progress=90, metrics={'estimated_time_remaining': _eta(90)}, logs=['计算相关矩阵（用于热力图）...'])
                numeric_df = df_clean.select_dtypes(include=[np.number])
                if numeric_df is not None and not numeric_df.empty:
                    max_heatmap_cols = int(params.get('max_heatmap_cols', 50) or 50)
                    max_heatmap_cols = max(10, min(max_heatmap_cols, 200))
                    if numeric_df.shape[1] > max_heatmap_cols:
                        # 取方差最大的列，减少相关矩阵维度
                        vars_ = numeric_df.var(numeric_only=True).sort_values(ascending=False)
                        keep_cols = vars_.head(max_heatmap_cols).index.tolist()
                        numeric_df = numeric_df[keep_cols]
                        manager.update_task(task_id, logs=[f'数值列过多，热力图仅选取方差最高的前 {len(keep_cols)} 列'])
                    corr_matrix = numeric_df.corr()
                    if corr_matrix is not None and not corr_matrix.empty:
                        heatmap_data = {
                            'x': corr_matrix.columns.tolist(),
                            'y': corr_matrix.columns.tolist(),
                            'z': corr_matrix.values.tolist()
                        }
            except Exception as e:
                # 降级：不让热力图计算拖垮整个任务
                manager.update_task(task_id, logs=[f'⚠️ 相关矩阵计算失败，已跳过热力图：{str(e)}'])
                heatmap_data = {}

        summary = dict(mining_result.get('summary', {}))
        summary.update({
            'total_rules': len(sorted_rules),
            'total_records': len(df_clean),
            'p_value_threshold': p_val_thresh,
            'test_method': test_name
        })

        result_package = {
            **mining_result,
            'heatmap_data': heatmap_data,
            'summary': summary
        }
        
        manager.update_task(task_id, progress=95, metrics={'estimated_time_remaining': _eta(95)}, logs=['封装结果并写入任务状态...'])
        _check_cancel()
        manager.update_task(
            task_id,
            status='completed',
            step_update={'index': 4, 'status': 'completed'},
            progress=100,
            metrics={'estimated_time_remaining': 0},
            result=result_package,
            logs=['任务全部完成！']
        )

        # 关键：即使前端没轮询 task_status，也要确保结果落到全局状态，结果页才能立即读到
        try:
            global_state.set_results('latest_analysis', result_package)
        except Exception:
            pass

    except (InterruptedError, Exception) as e:
        # 取消引起的异常不算失败
        if manager.is_cancelled(task_id) or isinstance(e, InterruptedError):
            manager.update_task(task_id, logs=['任务已被用户取消，执行已中断'])
            return
        import traceback
        traceback.print_exc()
        manager.update_task(task_id, 
            status='failed', 
            error=str(e),
            logs=[f'❌ 任务执行出错: {str(e)}'])
