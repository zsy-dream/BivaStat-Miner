import axios, { AxiosError } from 'axios';
import { API_ENDPOINTS } from '../utils/api';
import type {
    ApiResponse, DataInfo, QualityReport,
    Task, TaskHistoryItem, DataProfile, AssociationRule, ProcessingResult, ProfileRecommendations,
    DataQualityAssessment, MiningDiagnostics, MiningFallbackAttempt, MiningExcludedColumn, MiningTopItem, MiningTransactionSummary,
} from '../types';

// ======================== 通用请求封装 ========================

const http = axios.create({ timeout: 120_000 });

/** 创建可取消的请求控制器 */
export function createAbortController(): AbortController {
    return new AbortController();
}

/** 提取后端错误信息 */
function extractErrorMessage(error: unknown, fallback: string): string {
    if (error instanceof AxiosError) {
        if (error.response?.data?.error) return error.response.data.error;
        if (error.response?.data?.detail) return error.response.data.detail;
        if (!error.response) return '网络通信失败：请确认后端服务已启动';
    }
    return fallback;
}

function unwrapData<T>(payload: { data?: T } & Record<string, unknown>): T | undefined {
    return payload.data as T | undefined;
}

function toStringArray(value: unknown): string[] {
    return Array.isArray(value) ? value.map((item) => String(item)) : [];
}

function toNumber(value: unknown, fallback = 0): number {
    return typeof value === 'number' && Number.isFinite(value) ? value : fallback;
}

function toRecord(value: unknown): Record<string, unknown> {
    return value && typeof value === 'object' && !Array.isArray(value)
        ? value as Record<string, unknown>
        : {};
}

function normalizeExcludedColumn(value: unknown): MiningExcludedColumn {
    const raw = toRecord(value);
    return {
        name: String(raw.name ?? ''),
        reason: String(raw.reason ?? ''),
        unique_count: typeof raw.unique_count === 'number' ? raw.unique_count : undefined,
        unique_ratio: typeof raw.unique_ratio === 'number' ? raw.unique_ratio : undefined,
        dtype: typeof raw.dtype === 'string' ? raw.dtype : undefined,
    };
}

function normalizeTopItem(value: unknown): MiningTopItem {
    const raw = toRecord(value);
    return {
        item: String(raw.item ?? ''),
        count: toNumber(raw.count),
        support: toNumber(raw.support),
    };
}

function normalizeTransactionSummary(value: unknown): MiningTransactionSummary | undefined {
    const raw = toRecord(value);
    if (!Object.keys(raw).length) return undefined;
    return {
        transaction_count: toNumber(raw.transaction_count),
        avg_items_per_transaction: toNumber(raw.avg_items_per_transaction),
        min_items_per_transaction: toNumber(raw.min_items_per_transaction),
        max_items_per_transaction: toNumber(raw.max_items_per_transaction),
        empty_transactions: toNumber(raw.empty_transactions),
        frequent_single_items_at_threshold: toNumber(raw.frequent_single_items_at_threshold),
    };
}

function normalizeMiningDiagnostics(value: unknown): MiningDiagnostics | undefined {
    const raw = toRecord(value);
    if (!Object.keys(raw).length) return undefined;

    const candidateOverview = toRecord(raw.candidate_overview);
    const datasetShape = toRecord(raw.dataset_shape);
    const recommendedParams = toRecord(raw.recommended_params);
    const effectiveParams = toRecord(raw.effective_params);

    return {
        readiness_score: toNumber(raw.readiness_score),
        readiness_level: String(raw.readiness_level ?? 'poor') as MiningDiagnostics['readiness_level'],
        summary: typeof raw.summary === 'string' ? raw.summary : '',
        dataset_shape: Object.keys(datasetShape).length
            ? {
                rows: toNumber(datasetShape.rows),
                cols: toNumber(datasetShape.cols),
            }
            : undefined,
        candidate_columns: toStringArray(raw.candidate_columns),
        selected_columns: toStringArray(raw.selected_columns),
        preferred_columns: toStringArray(raw.preferred_columns),
        excluded_columns: Array.isArray(raw.excluded_columns)
            ? raw.excluded_columns.map(normalizeExcludedColumn).filter((item) => item.name && item.reason)
            : [],
        warnings: toStringArray(raw.warnings),
        suggestions: toStringArray(raw.suggestions),
        recommended_params: Object.keys(recommendedParams).length
            ? recommendedParams as MiningDiagnostics['recommended_params']
            : undefined,
        candidate_overview: Object.keys(candidateOverview).length
            ? {
                candidate_count: toNumber(candidateOverview.candidate_count),
                selected_count: toNumber(candidateOverview.selected_count),
                excluded_count: toNumber(candidateOverview.excluded_count),
                categorical_candidate_count: toNumber(candidateOverview.categorical_candidate_count),
                numeric_candidate_count: toNumber(candidateOverview.numeric_candidate_count),
                average_unique_ratio: typeof candidateOverview.average_unique_ratio === 'number'
                    ? candidateOverview.average_unique_ratio
                    : undefined,
            }
            : undefined,
        transaction_summary: normalizeTransactionSummary(raw.transaction_summary),
        top_items: Array.isArray(raw.top_items)
            ? raw.top_items.map(normalizeTopItem).filter((item) => item.item)
            : undefined,
        effective_params: Object.keys(effectiveParams).length ? effectiveParams : undefined,
        attempts_run: typeof raw.attempts_run === 'number' ? raw.attempts_run : undefined,
    };
}

function normalizeFallbackAttempt(value: unknown): MiningFallbackAttempt {
    const raw = toRecord(value);
    const params = toRecord(raw.params);
    return {
        name: String(raw.name ?? '未命名策略'),
        strategy: String(raw.strategy ?? 'unknown'),
        reason: typeof raw.reason === 'string' ? raw.reason : undefined,
        params: Object.keys(params).length ? params : undefined,
        rules_found: toNumber(raw.rules_found),
        selected_for_output: typeof raw.selected_for_output === 'boolean' ? raw.selected_for_output : undefined,
        selected_columns: toStringArray(raw.selected_columns),
        excluded_columns_count: typeof raw.excluded_columns_count === 'number' ? raw.excluded_columns_count : undefined,
        excluded_columns_preview: Array.isArray(raw.excluded_columns_preview)
            ? raw.excluded_columns_preview.map(normalizeExcludedColumn).filter((item) => item.name && item.reason)
            : undefined,
        transaction_count: typeof raw.transaction_count === 'number' ? raw.transaction_count : undefined,
        avg_items_per_transaction: typeof raw.avg_items_per_transaction === 'number' ? raw.avg_items_per_transaction : undefined,
        min_items_per_transaction: typeof raw.min_items_per_transaction === 'number' ? raw.min_items_per_transaction : undefined,
        max_items_per_transaction: typeof raw.max_items_per_transaction === 'number' ? raw.max_items_per_transaction : undefined,
        empty_transactions: typeof raw.empty_transactions === 'number' ? raw.empty_transactions : undefined,
        frequent_single_items_at_threshold: typeof raw.frequent_single_items_at_threshold === 'number'
            ? raw.frequent_single_items_at_threshold
            : undefined,
        top_items: Array.isArray(raw.top_items)
            ? raw.top_items.map(normalizeTopItem).filter((item) => item.item)
            : undefined,
        top_lift: typeof raw.top_lift === 'number' ? raw.top_lift : undefined,
        top_confidence: typeof raw.top_confidence === 'number' ? raw.top_confidence : undefined,
        warnings: toStringArray(raw.warnings),
    };
}

function normalizeDataQualityAssessment(value: unknown): DataQualityAssessment | undefined {
    const raw = toRecord(value);
    if (!Object.keys(raw).length) return undefined;

    const missing = toRecord(raw.missing_values);
    const duplicates = toRecord(raw.duplicates);
    const consistency = toRecord(raw.data_consistency);

    return {
        overall_score: typeof raw.overall_score === 'number' ? raw.overall_score : undefined,
        missing_values: Object.keys(missing).length
            ? {
                total_missing: typeof missing.total_missing === 'number' ? missing.total_missing : undefined,
                high_missing_columns: toStringArray(missing.high_missing_columns),
            }
            : undefined,
        duplicates: Object.keys(duplicates).length
            ? {
                total_duplicates: typeof duplicates.total_duplicates === 'number' ? duplicates.total_duplicates : undefined,
                duplicate_percentage: typeof duplicates.duplicate_percentage === 'number' ? duplicates.duplicate_percentage : undefined,
            }
            : undefined,
        data_consistency: Object.keys(consistency).length
            ? {
                issue_count: typeof consistency.issue_count === 'number' ? consistency.issue_count : undefined,
            }
            : undefined,
    };
}

function normalizeRule(rule: Record<string, unknown>, pValueThreshold = 0.05): AssociationRule {
    const antecedents = toStringArray(rule.antecedents ?? rule.antecedent);
    const consequents = toStringArray(rule.consequents ?? rule.consequent);
    const pValue = typeof rule.p_value === 'number' ? rule.p_value : undefined;

    return {
        antecedents,
        consequents,
        support: toNumber(rule.support),
        confidence: toNumber(rule.confidence),
        lift: toNumber(rule.lift),
        conviction: typeof rule.conviction === 'number' ? rule.conviction : undefined,
        length: typeof rule.length === 'number' ? rule.length : undefined,
        p_value: pValue,
        test_method: typeof rule.test_method === 'string' ? rule.test_method : undefined,
        significant: typeof rule.significant === 'boolean'
            ? rule.significant
            : (pValue !== undefined ? pValue <= pValueThreshold : false),
    };
}

function normalizeTask(rawTask: Record<string, unknown> | null | undefined): Task | null {
    if (!rawTask) return null;

    const metrics = (rawTask.metrics ?? {}) as Record<string, unknown>;
    const rawResult = ((rawTask.result ?? {}) as Record<string, unknown>);
    const summary = (rawResult.summary ?? {}) as Record<string, unknown>;
    const pValueThreshold = toNumber(summary.p_value_threshold, 0.05);
    const rawRules = (rawResult.association_rules ?? rawResult.rules ?? []) as Record<string, unknown>[];
    const rules = rawRules.map((rule) => normalizeRule(rule, pValueThreshold));
    const miningDiagnostics = normalizeMiningDiagnostics(rawResult.mining_diagnostics ?? rawResult.diagnostics);
    const warnings = toStringArray(rawResult.warnings);
    const fallbackAttempts = Array.isArray(rawResult.fallback_attempts)
        ? rawResult.fallback_attempts.map(normalizeFallbackAttempt)
        : [];
    const selectedAttempt = rawResult.selected_attempt
        ? normalizeFallbackAttempt(rawResult.selected_attempt)
        : undefined;
    const rawMemoryMetric = typeof metrics.memory_usage_mb === 'number'
        ? metrics.memory_usage_mb
        : (typeof metrics.memory_usage === 'number' ? metrics.memory_usage : undefined);
    const normalizedMemoryMb = rawMemoryMetric !== undefined
        ? (
            // 兼容旧版本：旧后端 memory_usage 是 GB（通常 < 64），新后端已改成 MB
            rawMemoryMetric <= 64
                ? Number((rawMemoryMetric * 1024).toFixed(1))
                : Number(rawMemoryMetric.toFixed(1))
        )
        : undefined;
    const hasResultPayload = Boolean(
        rules.length
        || Object.keys(summary).length
        || miningDiagnostics
        || warnings.length
        || fallbackAttempts.length
        || selectedAttempt
    );

    return {
        task_id: String(rawTask.task_id ?? rawTask.id ?? ''),
        status: String(rawTask.status ?? 'pending') as Task['status'],
        progress: toNumber(rawTask.progress),
        eta_seconds: typeof metrics.estimated_time_remaining === 'number' ? metrics.estimated_time_remaining : undefined,
        memory_usage: normalizedMemoryMb,
        message: typeof rawTask.error === 'string'
            ? rawTask.error
            : (typeof rawTask.message === 'string' ? rawTask.message : undefined),
        start_time: typeof rawTask.start_time === 'string' ? rawTask.start_time : undefined,
        type: typeof rawTask.type === 'string' ? rawTask.type : undefined,
        rules_found: rules.length,
        records: toNumber(metrics.total_count),
        logs: Array.isArray(rawTask.logs) ? rawTask.logs.map((item) => String(item)) : [],
        has_result: Boolean(rawTask.has_result ?? rawTask.result),
        steps: Array.isArray(rawTask.steps)
            ? rawTask.steps.map((step) => ({
                name: String((step as Record<string, unknown>).name ?? ''),
                status: String((step as Record<string, unknown>).status ?? 'pending'),
            }))
            : undefined,
        result: hasResultPayload
            ? {
                rules,
                heatmap_data: (rawResult.heatmap_data ?? undefined) as Record<string, unknown> | undefined,
                summary: summary,
                mining_diagnostics: miningDiagnostics,
                warnings,
                fallback_attempts: fallbackAttempts,
                selected_attempt: selectedAttempt,
                ai_analysis: typeof rawResult.ai_analysis === 'string' ? rawResult.ai_analysis : undefined,
                ai_analysis_updated_at: typeof rawResult.ai_analysis_updated_at === 'string' ? rawResult.ai_analysis_updated_at : undefined,
            }
            : undefined,
    };
}

// ======================== 数据管理服务 ========================

export const dataService = {
    /** 获取当前已加载的数据集 */
    async getCurrent(signal?: AbortSignal): Promise<ApiResponse<DataInfo>> {
        const res = await http.get(`${API_ENDPOINTS.DATA}/current`, { signal });
        return res.data;
    },

    /** 获取质量报告 */
    async getQualityReport(filePath: string, signal?: AbortSignal): Promise<QualityReport> {
        const res = await http.post(`${API_ENDPOINTS.DATA}/quality_report`, { file_path: filePath }, { signal });
        const payload = unwrapData<Record<string, unknown>>(res.data) ?? {};
        return {
            success: Boolean(res.data.success),
            summary: payload.summary as QualityReport['summary'],
            missing_chart: payload.missing_chart as QualityReport['missing_chart'],
            assessment: payload.assessment as Record<string, unknown> | undefined,
        };
    },

    /** 上传数据文件 */
    async uploadData(file: File, signal?: AbortSignal): Promise<ApiResponse<DataInfo>> {
        const formData = new FormData();
        formData.append('file', file);
        const res = await http.post(`${API_ENDPOINTS.DATA}/upload_data`, formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
            signal,
        });
        return res.data;
    },

    /** 加载示例数据集 */
    async loadSampleDataset(type: string, nSamples = 1000, signal?: AbortSignal): Promise<ApiResponse<DataInfo> & { path?: string }> {
        const res = await http.post(`${API_ENDPOINTS.DATA}/load_sample_dataset`, {
            dataset_type: type, n_samples: nSamples,
        }, { signal });
        const payload = unwrapData<DataInfo & { path?: string }>(res.data);
        return { ...res.data, path: payload?.path, data: payload };
    },

    /** 执行增强预处理 */
    async enhancedPreprocessing(
        filePath: string,
        config: Record<string, unknown>,
        signal?: AbortSignal
    ): Promise<ApiResponse<{ preprocessing_result?: ProcessingResult }> & { preprocessing_result?: ProcessingResult }> {
        const res = await http.post(`${API_ENDPOINTS.DATA}/enhanced_preprocessing`, {
            file_path: filePath, config,
        }, { signal });
        const payload = unwrapData<{ preprocessing_result?: ProcessingResult }>(res.data);
        return {
            ...res.data,
            data: payload,
            preprocessing_result: payload?.preprocessing_result,
        };
    },

    /** 获取数据画像与推荐参数 */
    async getProfile(taskId?: string | null, signal?: AbortSignal): Promise<ApiResponse & {
        profile?: DataProfile;
        recommendations?: ProfileRecommendations;
        assessment?: DataQualityAssessment;
        miningReadiness?: MiningDiagnostics;
    }> {
        const res = await http.get(`${API_ENDPOINTS.DATA}/profile`, {
            params: taskId ? { task_id: taskId } : {},
            signal
        });

        const payload = unwrapData<Record<string, unknown>>(res.data) ?? {};
        const rawProfile = (payload.profile ?? {}) as Record<string, unknown>;
        const assessment = normalizeDataQualityAssessment(payload.assessment);
        const miningReadiness = normalizeMiningDiagnostics(payload.mining_readiness);
        const profile: DataProfile | undefined = Object.keys(rawProfile).length
            ? {
                rows: toNumber(rawProfile.rows),
                cols: toNumber(rawProfile.cols, Array.isArray(rawProfile.columns) ? rawProfile.columns.length : 0),
                columns: toStringArray(rawProfile.columns),
                numeric_cols: toStringArray(rawProfile.numeric_cols),
                categorical_cols: toStringArray(rawProfile.categorical_cols),
            }
            : undefined;

        return {
            ...res.data,
            data: payload,
            profile,
            recommendations: payload.recommendations as ProfileRecommendations | undefined,
            assessment,
            miningReadiness,
        };
    },

    /** 清除当前数据集 */
    async clearCurrent(signal?: AbortSignal) {
        const res = await http.post(`${API_ENDPOINTS.DATA}/clear_current`, undefined, { signal });
        return res.data;
    },

    /** 导出数据集 URL */
    getExportUrl(format = 'csv'): string {
        return `${API_ENDPOINTS.DATA}/export_current?format=${format}`;
    },

    /** 导出质量报告 URL */
    getQualityReportDownloadUrl(format = 'html'): string {
        return `${API_ENDPOINTS.DATA}/quality_report/download?format=${format}`;
    },
};

// ======================== 算法服务 ========================

const API_ALGO = API_ENDPOINTS.ALGORITHM;

export const algorithmService = {
    /** 启动挖掘任务 */
    async startTask(params: Record<string, unknown>, signal?: AbortSignal) {
        const res = await http.post(`${API_ALGO}/start_task`, { params }, { signal });
        return res.data;
    },

    /** 获取任务状态 */
    async getTaskStatus(taskId: string, signal?: AbortSignal): Promise<Task> {
        const res = await http.get(`${API_ALGO}/task_status/${taskId}`, {
            signal,
            params: { _ts: Date.now() },
            headers: { 'Cache-Control': 'no-cache' },
        });
        return normalizeTask((res.data.task ?? res.data) as Record<string, unknown>) ?? {
            task_id: taskId,
            status: 'failed',
            progress: 0,
            rules_found: 0,
            records: 0,
            logs: [],
        };
    },

    /** 获取最近一次任务 */
    async getLastTask(signal?: AbortSignal) {
        const res = await http.get(`${API_ALGO}/last_task`, {
            signal,
            params: { _ts: Date.now() },
            headers: { 'Cache-Control': 'no-cache' },
        });
        return {
            ...res.data,
            task: normalizeTask(res.data.task as Record<string, unknown> | undefined),
        };
    },

    /** 获取历史列表 */
    async getHistory(signal?: AbortSignal): Promise<{ tasks: TaskHistoryItem[] }> {
        const res = await http.get(`${API_ALGO}/get_history`, {
            signal,
            params: { _ts: Date.now() },
            headers: { 'Cache-Control': 'no-cache' },
        });
        return res.data;
    },

    /** 删除任务 */
    async deleteTask(taskId: string, signal?: AbortSignal) {
        const res = await http.delete(`${API_ALGO}/delete_task/${taskId}`, { signal });
        return res.data;
    },

    /** 任务控制 */
    async controlTask(action: 'stop' | 'pause' | 'resume', taskId: string, signal?: AbortSignal) {
        const res = await http.post(`${API_ALGO}/${action}_task/${taskId}`, undefined, { signal });
        return res.data;
    },
};

// ======================== 可视化服务 ========================

export const visualizationService = {
    /** 生成图表 */
    async createChart(payload: Record<string, unknown>, signal?: AbortSignal) {
        const res = await http.post(`${API_ENDPOINTS.VISUALIZATION}/create_chart`, payload, { signal });
        const responsePayload = unwrapData<Record<string, unknown>>(res.data) ?? {};
        return {
            ...res.data,
            data: responsePayload,
        };
    },
    /** 导出图表 */
    async exportChart(payload: Record<string, unknown>, signal?: AbortSignal): Promise<Blob> {
        const res = await http.post(`${API_ENDPOINTS.VISUALIZATION}/export_chart`, payload, { signal, responseType: 'blob' });
        return res.data;
    },
};

// ======================== 报告服务 ========================

export const reportService = {
    /** 生成报告 */
    async generateReport(payload: Record<string, unknown>, signal?: AbortSignal) {
        const res = await http.post(`${API_ENDPOINTS.REPORT}/generate_report`, payload, { signal });
        return res.data;
    },

    /** 下载报告 (Blob) */
    async downloadReport(reportId: string, signal?: AbortSignal): Promise<Blob> {
        const res = await http.get(`${API_ENDPOINTS.REPORT}/download_report/${reportId}`, {
            responseType: 'blob',
            signal,
        });
        return res.data;
    },
};

// ======================== AI 服务 ========================

export const aiService = {
    /** 检查 AI 可用性 */
    async checkStatus(signal?: AbortSignal): Promise<{ available: boolean }> {
        const res = await http.get(`${API_ENDPOINTS.AI}/status`, {
            signal,
            params: { _ts: Date.now() },
            headers: { 'Cache-Control': 'no-cache' },
        });
        return res.data;
    },

    /** AI 深度解读 */
    async analyzeRules(payload: Record<string, unknown>, signal?: AbortSignal) {
        const res = await http.post(`${API_ENDPOINTS.AI}/analyze_rules`, payload, { signal });
        return res.data;
    },
};

export { extractErrorMessage };
