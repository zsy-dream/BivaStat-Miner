/**
 * 增强功能模块 - 示例数据集和UI优化
 */

// =======================================================
// 示例数据集功能
// =======================================================

// 显示示例数据选择模态框
window.showSampleDataModal = function showSampleDataModal() {
    let modal = document.getElementById('sample-data-modal');
    if (modal) {
        modal.style.display = 'flex';
        loadSampleDatasets();
        return;
    }
    
    modal = document.createElement('div');
    modal.id = 'sample-data-modal';
    modal.className = 'modal';
    modal.innerHTML = `
        <div class="modal-content" style="max-width: 700px; max-height: 80vh; overflow-y: auto;">
            <div class="modal-header" style="display: flex; justify-content: space-between; align-items: center; padding: 20px; border-bottom: 1px solid #e5e7eb;">
                <h2 style="margin: 0; color: #1f2937;">📊 选择示例数据集</h2>
                <span class="close-btn" onclick="closeSampleDataModal()" style="font-size: 28px; cursor: pointer; color: #9ca3af;">&times;</span>
            </div>
            <div class="modal-body" style="padding: 20px;">
                <p style="color: #6b7280; margin-bottom: 20px;">选择一个预设数据集快速体验平台功能，无需上传文件</p>
                <div id="sample-datasets-grid" class="datasets-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px;">
                    <div style="text-align: center; padding: 40px; color: #9ca3af;">加载中...</div>
                </div>
            </div>
        </div>
    `;
    
    modal.style.cssText = `
        display: flex;
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0,0,0,0.5);
        z-index: 1000;
        justify-content: center;
        align-items: center;
    `;
    
    document.body.appendChild(modal);
    loadSampleDatasets();
}

window.closeSampleDataModal = function closeSampleDataModal() {
    const modal = document.getElementById('sample-data-modal');
    if (modal) {
        modal.style.display = 'none';
    }
}

function loadSampleDatasets() {
    const grid = document.getElementById('sample-datasets-grid');
    grid.innerHTML = '<div style="text-align: center; padding: 40px; color: #9ca3af;">加载中...</div>';
    
    fetch('/api/data/sample_datasets')
        .then(r => r.json())
        .then(res => {
            if (res.success && res.data && res.data.datasets) {
                renderSampleDatasets(res.data.datasets);
            } else {
                grid.innerHTML = '<p style="color: #ef4444; text-align: center;">加载失败，请重试</p>';
            }
        })
        .catch(err => {
            console.error('加载示例数据集失败:', err);
            grid.innerHTML = '<p style="color: #ef4444; text-align: center;">网络错误，请重试</p>';
        });
}

function renderSampleDatasets(datasets) {
    const grid = document.getElementById('sample-datasets-grid');
    
    const icons = {
        retail: '🛒', medical: '🏥', financial: '💰',
        education: '📚', marketing: '📢', iris_extended: '🌸'
    };
    
    const colors = {
        retail: '#3b82f6', medical: '#ef4444', financial: '#10b981',
        education: '#f59e0b', marketing: '#8b5cf6', iris_extended: '#ec4899'
    };
    
    grid.innerHTML = Object.entries(datasets).map(([key, dataset]) => `
        <div onclick="loadSampleDataset('${key}')" style="
            border: 2px solid ${colors[key] || '#e5e7eb'};
            border-radius: 12px;
            padding: 20px;
            cursor: pointer;
            transition: all 0.3s ease;
            background: white;
        " onmouseover="this.style.transform='translateY(-4px)';this.style.boxShadow='0 10px 25px rgba(0,0,0,0.1)'" 
           onmouseout="this.style.transform='translateY(0)';this.style.boxShadow='none'">
            <div style="font-size: 40px; margin-bottom: 12px;">${icons[key] || '📊'}</div>
            <h3 style="margin: 0 0 8px 0; font-size: 18px; color: #1f2937;">${dataset.name}</h3>
            <p style="margin: 0 0 12px 0; font-size: 14px; color: #6b7280; line-height: 1.5;">${dataset.description}</p>
            <div style="display: flex; gap: 15px; font-size: 13px; color: #6b7280; margin-bottom: 10px;">
                <span>📋 ${dataset.rows} 行</span>
                <span>📊 ${dataset.columns} 列</span>
            </div>
            <div style="display: flex; flex-wrap: wrap; gap: 6px;">
                ${dataset.features.slice(0, 4).map(f => `
                    <span style="background: ${colors[key]}15; color: ${colors[key]}; padding: 3px 10px; border-radius: 20px; font-size: 12px;">${f}</span>
                `).join('')}
            </div>
        </div>
    `).join('');
}

window.loadSampleDataset = function loadSampleDataset(datasetType) {
    closeSampleDataModal();
    showLoadingOverlay('正在生成示例数据...');
    
    fetch('/api/data/load_sample_dataset', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ dataset_type: datasetType })
    })
    .then(r => r.json())
    .then(res => {
        hideLoadingOverlay();
        if (res.success) {
            showToast(`✅ ${res.message}`, 'success');
            setTimeout(() => {
                if (window.location.pathname === '/data') {
                    window.location.reload();
                } else {
                    window.location.href = '/data';
                }
            }, 1000);
        } else {
            showToast(res.error || '加载失败', 'error');
        }
    })
    .catch(err => {
        hideLoadingOverlay();
        console.error('加载失败:', err);
        showToast('网络错误，请重试', 'error');
    });
}

// =======================================================
// 加载动画功能
// =======================================================

window.showLoadingOverlay = function showLoadingOverlay(message = '处理中...') {
    let overlay = document.getElementById('loading-overlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.id = 'loading-overlay';
        overlay.innerHTML = `
            <div style="text-align: center;">
                <div class="spinner" style="
                    width: 50px;
                    height: 50px;
                    border: 4px solid #e5e7eb;
                    border-top-color: #3b82f6;
                    border-radius: 50%;
                    animation: spin 1s linear infinite;
                    margin: 0 auto;
                "></div>
                <p id="loading-message" style="margin-top: 15px; color: #6b7280; font-size: 14px;">${message}</p>
            </div>
        `;
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(255,255,255,0.9);
            z-index: 9999;
            display: flex;
            justify-content: center;
            align-items: center;
        `;
        
        const style = document.createElement('style');
        style.textContent = `@keyframes spin { to { transform: rotate(360deg); } }`;
        document.head.appendChild(style);
        document.body.appendChild(overlay);
    } else {
        document.getElementById('loading-message').textContent = message;
        overlay.style.display = 'flex';
    }
}

window.hideLoadingOverlay = function hideLoadingOverlay() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.style.display = 'none';
    }
}

// =======================================================
// 工具函数
// =======================================================

window.debounce = function debounce(func, wait) {
    let timeout;
    return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}

window.throttle = function throttle(func, limit) {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

window.runAnalysis = function runAnalysis() {
    fetch('/api/data/current')
        .then(r => r.json())
        .then(res => {
            if (res.success) {
                window.location.href = '/algorithm';
            } else {
                showToast('请先上传数据或选择示例数据集', 'warning');
                setTimeout(() => {
                    if (confirm('是否打开示例数据集选择界面？')) {
                        showSampleDataModal();
                    }
                }, 500);
            }
        })
        .catch(() => {
            showToast('无法检查数据状态', 'error');
        });
}

window.handleUpload = function handleUpload(input) {
    const file = input.files[0];
    if (!file) return;
    
    const formData = new FormData();
    formData.append('file', file);
    
    showLoadingOverlay('正在上传文件...');
    
    fetch('/api/data/upload_data', {
        method: 'POST',
        body: formData
    })
    .then(r => r.json())
    .then(res => {
        hideLoadingOverlay();
        if (res.success) {
            showToast('✅ 文件上传成功', 'success');
            setTimeout(() => window.location.href = '/data', 1000);
        } else {
            showToast(res.error || '上传失败', 'error');
        }
    })
    .catch(err => {
        hideLoadingOverlay();
        showToast('网络错误，请重试', 'error');
    });
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    // 添加示例数据按钮到首页
    const quickActions = document.querySelector('.action-buttons');
    if (quickActions && !document.getElementById('btn-sample-data')) {
        const sampleBtn = document.createElement('button');
        sampleBtn.id = 'btn-sample-data';
        sampleBtn.className = 'action-btn btn-orange';
        sampleBtn.innerHTML = '<span>📊 示例数据</span>';
        sampleBtn.onclick = showSampleDataModal;
        sampleBtn.style.cssText = `
            background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 16px;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            gap: 8px;
        `;
        quickActions.appendChild(sampleBtn);
    }
});
