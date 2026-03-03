document.addEventListener('DOMContentLoaded', function() {
    highlightCurrentNav();
});

function highlightCurrentNav() {
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.nav a');

    navLinks.forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
            // 如果样式中有 .active 类定义，这会生效
            link.style.fontWeight = 'bold';
            link.style.borderBottom = '2px solid white';
        }
    });
}

// 通用工具函数：格式化数字
function formatNumber(num, decimals = 2) {
    return parseFloat(num).toFixed(decimals);
}

// 通用工具函数：显示通知
function showToast(message, type = 'info') {
    // 检查页面是否已有 toast 容器
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.style.position = 'fixed';
        container.style.top = '20px';
        container.style.right = '20px';
        container.style.zIndex = '9999';
        document.body.appendChild(container);
    }

    // 创建 toast 元素
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    // 设置样式
    const colors = {
        success: '#28a745',
        error: '#dc3545',
        info: '#17a2b8',
        warning: '#ffc107'
    };
    
    toast.style.backgroundColor = colors[type] || colors.info;
    toast.style.color = 'white';
    toast.style.padding = '12px 24px';
    toast.style.marginBottom = '10px';
    toast.style.borderRadius = '4px';
    toast.style.boxShadow = '0 4px 6px rgba(0,0,0,0.1)';
    toast.style.minWidth = '250px';
    toast.style.opacity = '0';
    toast.style.transition = 'opacity 0.3s ease-in-out, transform 0.3s ease';
    toast.style.transform = 'translateY(-20px)';
    
    toast.textContent = message;
    
    container.appendChild(toast);
    
    // 动画显示
    requestAnimationFrame(() => {
        toast.style.opacity = '1';
        toast.style.transform = 'translateY(0)';
    });

    // 自动消失
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(-20px)';
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 300);
    }, 3000);
}

// 暴露给全局，方便其他模块调用
window.showError = (msg) => showToast(msg, 'error');
window.showSuccess = (msg) => showToast(msg, 'success');

// 统一入口：跳转到“最近一次有结果的任务”对应的结果分析页
// 用于侧边栏“结果分析”菜单和首页快捷卡片
window.goToLatestAnalysis = function goToLatestAnalysis() {
    // 先尝试从后端拿 last_task 信息
    fetch('/api/algorithm/last_task')
        .then(r => r.json())
        .then(res => {
            const t = res && res.task;
            if (t && t.task_id && (t.has_result || t.status === 'completed')) {
                window.location.href = `/analysis_result?task_id=${encodeURIComponent(t.task_id)}`;
            } else {
                // 没有可用任务就退回默认结果页，由后端再做兜底提示
                window.location.href = '/analysis_result';
            }
        })
        .catch(() => {
            window.location.href = '/analysis_result';
        });
}