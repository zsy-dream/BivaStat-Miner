import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Upload, FileText, CheckCircle, AlertCircle, BarChart2, Filter } from 'lucide-react';
import { API_ENDPOINTS } from '../utils/api';

const API_BASE = API_ENDPOINTS.DATA;

const DataManagement: React.FC = () => {
    const [file, setFile] = useState<File | null>(null);
    const [dataInfo, setDataInfo] = useState<any>(null);
    const [loading, setLoading] = useState(false);
    const [qualityReport, setQualityReport] = useState<any>(null);

    const fetchCurrent = async () => {
        try {
            const resp = await axios.get(`${API_BASE}/current`);
            if (resp.data.success) {
                setDataInfo(resp.data);
                fetchQuality(resp.data.path);
            }
        } catch (e) { }
    };

    const fetchQuality = async (path: string) => {
        try {
            const resp = await axios.post(`${API_BASE}/quality_report`, { file_path: path });
            if (resp.data.success) setQualityReport(resp.data);
        } catch (e) { }
    };

    useEffect(() => {
        fetchCurrent();
    }, []);

    const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const f = e.target.files?.[0];
        if (!f) return;
        setFile(f);
        setLoading(true);

        const formData = new FormData();
        formData.append('file', f);

        try {
            const resp = await axios.post(`${API_BASE}/upload_data`, formData);
            if (resp.data.success) {
                setDataInfo(resp.data);
                fetchQuality(resp.data.path);
            }
        } catch (err) {
            alert("上传失败");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="max-w-6xl mx-auto flex flex-col gap-8">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold tracking-tight mb-1">数据管理与质量中心</h1>
                    <p className="text-[#8e8e8e] text-sm italic">通过自动化评估与清洗管道，确保挖掘结果的科学一致性。</p>
                </div>
                <label className="notion-btn-primary cursor-pointer flex items-center gap-2">
                    <Upload size={16} />
                    <span>上传数据集</span>
                    <input type="file" className="hidden" onChange={handleUpload} />
                </label>
            </div>

            {loading && <div className="text-center py-12">正在努力解析您的数据，请稍候...</div>}

            {dataInfo && !loading && (
                <div className="grid grid-cols-3 gap-6">
                    {/* Summary Card */}
                    <div className="col-span-1 notion-card p-6 flex flex-col gap-4">
                        <h3 className="font-bold flex items-center gap-2">
                            <FileText size={18} className="text-primary-500" />
                            数据集概览
                        </h3>
                        <div className="space-y-3">
                            <div className="flex justify-between text-sm py-2 border-b border-[#f0f0f0]">
                                <span className="text-[#8e8e8e]">文件名</span>
                                <span className="font-medium truncate w-32 text-right">{dataInfo.filename}</span>
                            </div>
                            <div className="flex justify-between text-sm py-2 border-b border-[#f0f0f0]">
                                <span className="text-[#8e8e8e]">总记录数</span>
                                <span className="font-bold">{dataInfo.shape[0]}</span>
                            </div>
                            <div className="flex justify-between text-sm py-2">
                                <span className="text-[#8e8e8e]">变量数量</span>
                                <span className="font-bold">{dataInfo.shape[1]}</span>
                            </div>
                        </div>
                    </div>

                    {/* Quality Report Card */}
                    {qualityReport && (
                        <div className="col-span-2 notion-card p-6">
                            <h3 className="font-bold flex items-center gap-2 mb-6">
                                <CheckCircle size={18} className="text-emerald-500" />
                                数据质量诊断报告
                            </h3>
                            <div className="grid grid-cols-2 gap-8">
                                <div>
                                    <div className="mb-4">
                                        <span className="text-xs font-bold text-[#8e8e8e] uppercase mb-1 block">整体缺失率</span>
                                        <div className="flex items-end gap-2">
                                            <span className="text-3xl font-black text-rose-500">{(qualityReport.summary.missing_rate * 100).toFixed(2)}%</span>
                                            <span className="text-xs text-[#8e8e8e] mb-1">({qualityReport.summary.total_missing} 单元格)</span>
                                        </div>
                                    </div>
                                    <div className="space-y-2">
                                        {qualityReport.summary.warnings.map((w: string, i: number) => (
                                            <div key={i} className="flex gap-2 text-xs bg-amber-50 text-amber-700 p-2 rounded border border-amber-100 items-start">
                                                <AlertCircle size={14} className="shrink-0 mt-0.5" />
                                                <span>{w}</span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                                <div>
                                    <h4 className="text-[11px] font-bold text-[#8e8e8e] uppercase mb-3">最严峻缺失变量 (Top 12)</h4>
                                    <div className="space-y-1.5">
                                        {qualityReport.missing_chart.labels.map((l: string, i: number) => (
                                            <div key={i} className="flex flex-col gap-0.5">
                                                <div className="flex justify-between text-[10px] text-[#37352f]">
                                                    <span>{l}</span>
                                                    <span>{qualityReport.missing_chart.values[i]} vals</span>
                                                </div>
                                                <div className="h-1 bg-[#efefee] rounded-full overflow-hidden">
                                                    <div
                                                        className="h-full bg-rose-400"
                                                        style={{ width: `${Math.min(100, (qualityReport.missing_chart.values[i] / qualityReport.summary.rows) * 100)}%` }}
                                                    />
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Preview Section */}
                    <div className="col-span-3 notion-card p-6 overflow-hidden">
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="font-bold flex items-center gap-2">数据预览 (Top 10)</h3>
                            <div className="flex gap-2">
                                <button className="notion-btn-ghost flex items-center gap-1 text-xs">
                                    <Filter size={14} />
                                    筛选
                                </button>
                                <button className="notion-btn-ghost flex items-center gap-1 text-xs">
                                    <BarChart2 size={14} />
                                    统计图表
                                </button>
                            </div>
                        </div>
                        <div className="overflow-x-auto border rounded-lg">
                            <table className="w-full text-sm text-left">
                                <thead className="bg-[#f7f6f3] border-b text-xs font-bold text-[#8e8e8e]">
                                    <tr>
                                        {dataInfo.columns.map((c: string) => (
                                            <th key={c} className="px-4 py-2 border-r last:border-r-0 min-w-[120px]">{c}</th>
                                        ))}
                                    </tr>
                                </thead>
                                <tbody>
                                    {dataInfo.preview.map((row: any, i: number) => (
                                        <tr key={i} className="border-b last:border-0 hover:bg-[#fbfbfa]">
                                            {dataInfo.columns.map((c: string) => (
                                                <td key={c} className="px-4 py-2 border-r last:border-r-0 truncate max-w-[200px]">{row[c]?.toString() || ''}</td>
                                            ))}
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            )}

            {!dataInfo && !loading && (
                <div className="flex flex-col items-center justify-center py-24 bg-white border border-dashed rounded-2xl border-[#e9e9e8]">
                    <Upload size={48} className="text-[#8e8e8e] mb-4" />
                    <p className="text-[#8e8e8e] text-lg font-medium">尚未载入数据</p>
                    <p className="text-[#8e8e8e] text-sm mb-6">上传之后您将在这里查看数据全貌</p>
                    <label className="notion-btn-primary cursor-pointer">
                        立即导入
                        <input type="file" className="hidden" onChange={handleUpload} />
                    </label>
                    {file && <p className="mt-2 text-sm text-slate-600">Selected: {file.name}</p>}
                </div>
            )}
        </div>
    );
};

export default DataManagement;
