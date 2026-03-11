# 📊 BivaStat-Miner / 双变量关联挖掘与非参数统计分析平台

[![Backend](https://img.shields.io/badge/Backend-Flask-black?style=flat-square&logo=flask)](https://flask.palletsprojects.com/)
[![Frontend](https://img.shields.io/badge/Frontend-React%20%2B%20Vite-61DAFB?style=flat-square&logo=react)](https://react.dev/)
[![License](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](LICENSE)
一个面向**科研分析、业务洞察与行业报告生成**的一体化分析平台，覆盖：

- 数据导入与预处理
- 启发式关联规则挖掘
- 非参数统计检验
- 联动可视化探索
- 模板化 HTML 报告生成
- 可选 AI 摘要与任务级 AI 解读

本文档是当前仓库的**唯一主 README**，已按现有代码结构、运行入口和部署方式整理完成。

## 快速导航

- **本地开发**：见 [本地开发启动](#本地开发启动)
- **生产部署**：见 [生产部署推荐方案](#生产部署推荐方案)
- **Vercel + Render 更新部署**：见 [Vercel + Render 更新部署步骤](#vercel--render-更新部署步骤)
- **上线前核对**：见 [上线前检查清单](#上线前检查清单)
- 自定义域名配置前的核对清单

---

## 目录

- [项目简介](#项目简介)
- [核心能力](#核心能力)
- [当前技术架构](#当前技术架构)
- [项目结构](#项目结构)
- [环境要求](#环境要求)
- [本地开发启动](#本地开发启动)
- [关键环境变量](#关键环境变量)
- [生产部署推荐方案](#生产部署推荐方案)
- [Vercel + Render 更新部署步骤](#vercel--render-更新部署步骤)
- [更新发布 SOP](#更新发布-sop)
- [上线前检查清单](#上线前检查清单)
- [部署注意事项](#部署注意事项)
- [常见问题](#常见问题)

---

## 项目简介

**BivaStat-Miner** 是一个面向科研分析、业务洞察和行业报告输出的智能分析平台。  
它围绕“**数据导入 → 预处理 → 启发式关联规则挖掘 → 非参数统计检验 → 可视化探索 → 报告生成 → AI 解读**”这条主链路，提供一体化工作台。

当前版本重点支持：

- 双变量/关联规则挖掘
- 显著性统计检验
- 分析结果页交互浏览
- 规则网络和联动可视化
- 模板化 HTML 报告生成
- 可选的 AI 执行摘要与 AI 深度解读

---

## 核心能力

### 1. 数据导入与预处理

- 支持 CSV / Excel / JSON 等文件导入
- 自动质量评估、缺失值处理、异常值处理
- 数据管理页支持滚动浏览和编码处理

### 2. 异步算法任务

- 后端异步执行关联规则挖掘
- 前端轮询任务进度、日志和结果
- 支持任务历史查看与回溯

### 3. 统计显著性校验

- 结合非参数统计分析结果解释规则可信度
- 结果页展示显著性标签、统计摘要和风险提示

### 4. 可视化探索

- 关系图、规则网络图、散点图、分布图等
- 分析结果页支持从规则直接联动跳转到可视化页

### 5. 报告生成

- 多模板：综合分析 / 金融风控 / 医学研究 / 市场分析
- 支持图表开关：可导出“带图版”或“纯文字表格版”
- AI 执行摘要是**本次导出报告的可选项**

### 6. AI 能力

- 分析结果页可生成并保存 AI 深度解读
- 历史记录页可复看任务级 AI 内容
- 报告生成页的 AI 开关**只影响本次导出报告**

---

## 当前技术架构

### 后端

- Python 3.10
- Flask
- Pandas / NumPy / SciPy / scikit-learn
- Plotly / Jinja2 / Markdown
- Gunicorn（Linux / Render 生产推荐）
- Waitress（Windows 部署推荐）

### 前端

- React + TypeScript + Vite
- Axios
- Tailwind CSS
- Framer Motion
- Recharts

### 当前运行结构

```text
React + Vite Frontend
        │
        ▼
Flask API Server
        │
        ├── 数据导入 / 预处理
        ├── 异步任务管理
        ├── 统计与规则挖掘
        ├── 可视化服务
        ├── 报告生成服务
        └── AI 服务
```

---

## 项目结构

```text
.
├── app.py                  # Flask 应用入口（本地运行）
├── wsgi.py                 # Gunicorn / Render 推荐入口
├── serve.py                # 跨平台生产启动入口（Windows / Linux）
├── requirements.txt        # 后端依赖
├── config.json             # 系统配置
├── Dockerfile              # 当前可用的容器部署入口
├── routes/                 # 后端路由
├── services/               # 核心业务逻辑
├── models/                 # 数据模型
├── utils/                  # 配置、缓存、任务管理等
├── static/
│   ├── reports/            # 生成的 HTML 报告
│   └── templates/          # 报告模板
├── uploads/                # 上传文件
└── frontend/
    ├── package.json
    ├── .env.development
    ├── .env.production.example
    └── src/
```

---

## 环境要求

### 最低要求

- Python 3.10+
- Node.js 18+
- npm 9+

### 推荐要求

- Python 3.10 / 3.11
- Node.js 20+
- 8GB+ 内存

---

## 本地开发启动

## 1. 安装后端依赖

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

macOS / Linux:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 2. 启动后端

```bash
python app.py
```

当前代码默认本地端口是：

- `http://127.0.0.1:8001`

> 注意：当前项目真实默认端口是 **8001**，不是旧文档中的 5000。

如需用更接近生产的方式在本机启动（尤其是 Windows）：

```bash
python serve.py
```

## 3. 启动前端

```bash
cd frontend
npm install
npm run dev
```

前端开发环境默认读取：

- `frontend/.env.development`

当前内容应指向本地后端：

```bash
VITE_API_URL=http://localhost:8001
```

## 4. 构建前端

```bash
cd frontend
npm run build
```

构建产物目录：

- `frontend/dist`

---

## 关键环境变量

### 后端

建议在部署环境中显式配置：

- `PORT`  
  后端监听端口。Render 会自动注入。

- `SECRET_KEY`  
  Flask 密钥。生产环境务必自己设置。

- `ALLOWED_ORIGINS`  
  跨域白名单。  
  例如：
  ```bash
  ALLOWED_ORIGINS=https://your-frontend-domain.com
  ```

- `HUAWEI_MAAS_API_KEY`  
  AI 功能所需密钥。未配置时 AI 功能不可用。

### 前端

- `VITE_API_URL`  
  前端请求后端 API 的根地址。  
  例如：
  ```bash
  VITE_API_URL=https://api.yourdomain.com
  ```

---

## 生产部署推荐方案

## 推荐架构

继续采用你当前已经在使用的分离式部署：

- **前端：Vercel**
- **后端：Render**
- **域名：前后端分别绑定自定义域名**

这是当前项目最稳妥、最省改动的方案。

---

## Vercel + Render 更新部署步骤

## 一、Render 部署后端

### 方案 A：Render Python Web Service（推荐）

**Build Command**

```bash
pip install -r requirements.txt
```

**Start Command**

```bash
gunicorn wsgi:app --workers 2 --threads 4 --timeout 120 --bind 0.0.0.0:$PORT
```

> 当前仓库已经补齐了 `wsgi.py`，可直接作为 Gunicorn 入口。

### 方案 A-补充：Windows 服务器 / 本机生产模式启动

如果你的后台是部署在 **Windows** 环境，不要使用 `gunicorn`，推荐直接执行：

```bash
python serve.py
```

`serve.py` 会自动：

- 在 Windows 上使用 `waitress`
- 在 Linux / Render 上提示继续使用 `gunicorn wsgi:app`

### 方案 B：Render Docker 部署

当前根目录 `Dockerfile` 已修正为可运行当前 Flask 项目的版本：

- 基于 `python:3.10-slim`
- 使用 `gunicorn wsgi:app`
- 兼容 Render 注入的 `PORT`

如果你在 Render 上选 Docker 部署，直接使用当前仓库根目录 `Dockerfile` 即可。

### Render 环境变量建议

至少配置：

```bash
SECRET_KEY=your-secret-key
ALLOWED_ORIGINS=https://your-frontend-domain.com
HUAWEI_MAAS_API_KEY=your-ai-key
```

### Render 持久化建议

当前项目运行时会写入本地文件：

- `uploads/`
- `static/reports/`

如果你希望这些内容在 Render 重启或重新部署后保留，建议：

- 为 Render 服务挂载 persistent disk  
或
- 后续改造为对象存储

---

## 二、Vercel 部署前端

### 推荐设置

- **Framework Preset**：Vite
- **Root Directory**：`frontend`
- **Build Command**：`npm run build`
- **Output Directory**：`dist`

### Vercel 环境变量

在 Vercel 项目中设置：

```bash
VITE_API_URL=https://api.yourdomain.com
```

> 修改 `VITE_API_URL` 后，必须重新部署前端，新的环境变量才会生效。

---

## 三、自定义域名

你当前这套架构推荐：

- 前端域名：`https://yourdomain.com`
- 后端域名：`https://api.yourdomain.com`

然后：

- Vercel 绑定前端域名
- Render 绑定后端 API 子域名
- 后端 `ALLOWED_ORIGINS` 填前端正式域名
- 前端 `VITE_API_URL` 填后端正式域名

---

## 四、更新部署建议顺序

每次更新推荐按这个顺序：

1. 推送最新代码到 Git 仓库
2. 先部署 Render 后端
3. 检查后端健康接口是否正常
4. 再部署 Vercel 前端
5. 前端联调以下关键功能：
   - 数据上传
   - 算法任务启动
   - 分析结果页
   - 可视化页
   - AI 状态检测
   - 报告生成与下载

---

## 更新发布 SOP

下面这套流程适合你当前这类 **Vercel 前端 + Render 后端 + 自定义域名** 的日常更新发布。

### 标准发布顺序

#### 1. 本地确认

发布前先在本地至少做一次最小确认：

- 前端能正常构建
- 后端关键模块能正常导入
- 本次修改涉及的核心页面能打开
- 如果改了报告、AI、可视化或任务状态逻辑，至少手动走一次对应流程

#### 2. 提交代码

建议保持一次发布对应一组清晰提交：

```bash
git status
git add .
git commit -m "feat: your change summary"
git push origin main
```

#### 3. 先更新 Render 后端

原因：

- 前端最终要依赖新的 API
- 如果先发前端而后端没更新，最容易出现页面新逻辑打旧接口的问题

后端发布后先检查：

- 根路径健康检查是否正常
- 关键 API 是否可访问
- 环境变量是否仍完整

#### 4. 再更新 Vercel 前端

后端正常后，再触发前端部署。

前端发布前重点确认：

- `VITE_API_URL` 没写错
- 如果改过环境变量，已经重新部署而不是只保存设置

#### 5. 最后做线上验收

建议至少验收下面这些页面或流程：

- 首页是否能正常打开
- 数据上传是否正常
- 算法任务是否能启动
- 分析结果页是否正常显示
- 可视化页是否能打开
- AI 状态是否正常
- 报告是否能生成和下载

### 推荐的发布节奏

如果这次修改比较大，建议按下面节奏发：

1. 先推代码
2. 先看 Render 构建与启动日志
3. 后端健康后再发 Vercel
4. 发布完成后马上做一次关键链路回归

### 不建议的发布顺序

尽量避免：

- 先发前端，后发后端
- 改了环境变量但没重新部署
- Render 还没启动成功就去验前端页面

### 一次完整发布的最短检查路径

如果你每次只想走最短路径，可以按这 6 步：

1. `git push`
2. Render redeploy
3. 检查 Render 健康接口
4. Vercel redeploy
5. 打开正式前端首页
6. 手动走一遍“上传 → 分析 → 报告”

---

## 上线前检查清单

正式切流量前，建议至少确认下面这些项：

### Render 后端

- 代码已拉到最新提交
- Build Command 正确
- Start Command 为 `gunicorn wsgi:app --workers 2 --threads 4 --timeout 120 --bind 0.0.0.0:$PORT`
- `SECRET_KEY` 已配置
- `ALLOWED_ORIGINS` 已配置为前端正式域名
- `HUAWEI_MAAS_API_KEY` 已配置
- 如需保留上传文件和报告文件，已处理持久化存储

### Vercel 前端

- Root Directory 为 `frontend`
- Build Command 为 `npm run build`
- Output Directory 为 `dist`
- `VITE_API_URL` 已指向 Render 后端正式域名
- 环境变量改动后已重新部署

### 自定义域名

- 前端域名已绑定到 Vercel 项目
- 后端 API 子域名已绑定到 Render 服务
- 前后端域名填写没有写反
- HTTPS 已正常生效

### 功能联调

- 能正常打开首页
- 数据上传正常
- 算法任务能启动并返回结果
- 分析结果页正常展示
- 可视化页能正常打开
- AI 状态检测正常
- 报告生成与下载正常

---

## 部署注意事项

### 1. 当前项目不是 FastAPI / Uvicorn 结构

旧版 Dockerfile 曾使用：

```bash
uvicorn main:app
```

这**不适用于当前项目**。  
当前项目实际后端入口是：

- 本地：`python app.py`
- Linux / Render 生产：`gunicorn wsgi:app`
- Windows 生产：`python serve.py`

> `gunicorn` 主要面向类 Unix 环境，Windows 部署不要直接用它。

### 2. 当前默认本地端口是 8001

请以当前代码为准，不要再按旧文档的 5000 来。

### 3. AI 功能依赖后端密钥

没有 `HUAWEI_MAAS_API_KEY` 时：

- 分析结果页 AI 功能不可用
- 报告页 AI 执行摘要不可用

### 4. 报告页 AI 开关只影响本次导出

报告生成页中的 **AI 智能执行摘要** 开关：

- 只控制“**这次导出的最终报告是否附带 AI 执行摘要**”
- 不代表该任务历史里是否已有 AI 解读记录

### 5. 图表开关已接通

报告页中的“包含预构建的静态雷达与关系图斑序列”现在行为为：

- 勾选：报告带图
- 不勾：报告不带图，只保留文字和表格

---

## 常见问题

### Q1：部署后前端能打开，但接口报错 / 跨域失败

检查：

- `VITE_API_URL` 是否指向正确的 Render 后端域名
- `ALLOWED_ORIGINS` 是否包含你的 Vercel 前端域名

### Q2：AI 开关显示不可用

检查：

- Render 是否配置了 `HUAWEI_MAAS_API_KEY`
- 后端 `/api/ai/status` 是否返回 `available: true`
- 前端是否已经重新部署到最新版本

### Q3：报告能生成，但历史报告或上传文件部署后丢失

这是因为这些内容当前写在本地文件系统。  
请考虑：

- Render 持久化磁盘
或
- 后续把上传和报告改到对象存储

### Q4：更新部署后页面还是旧版本

检查：

- Vercel 是否完成了新的 Production Deployment
- 浏览器是否仍在使用旧缓存
- `VITE_API_URL` 是否确实更新

### Q5：Windows 上执行 `gunicorn wsgi:app` 启动失败

这是部署方式不匹配，不是当前 Flask 项目入口写错。

处理方式：

- 先执行 `pip install -r requirements.txt`
- Windows 上改用 `python serve.py`
- 如果部署在 Render / Linux，继续使用 `gunicorn wsgi:app --bind 0.0.0.0:$PORT`

---

## 许可证

本项目基于 **MIT License** 开源。

---

## 维护说明

如果后续再调整部署结构，请优先更新本文件，不要再新增第二份并行 README。  
当前仓库以根目录 `README.md` 作为唯一主文档。
