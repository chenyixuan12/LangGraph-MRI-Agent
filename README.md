# MRI Agent

面向 MRI 医学图像超分辨率的 Agent 系统骨架。当前版本提供可运行的 FastAPI 后端、MongoDB 元数据存储、本地影像文件存储、超分辨率处理占位管线、Agent 编排接口，以及一个轻量的 Vue 3 前端。

> 免责声明：项目中的超分辨率实现是工程占位（Lanczos/Bicubic），不用于临床诊断。接入真实模型前，请完成数据脱敏、验证集评估、DICOM/NIfTI 元数据保护、审计和临床合规流程。

## 快速开始

```bash
docker compose up --build
```

- API 文档：http://localhost:8000/docs
- 前端：http://localhost:5173

默认会启动 MongoDB 7，数据库名为 `mri_agent`。MongoDB 保存 `studies` 和 `jobs` 元数据；MRI 原始文件与处理结果仍保存在 `data/uploads`、`data/processed`，避免把大体积影像作为普通 MongoDB 文档存储。开发环境数据库端口仅绑定到本机 `127.0.0.1:27017`。

MongoDB 数据保存在 Docker 命名卷 `mongodb_data` 中。停止容器不会删除数据；如需清空数据库，需显式删除该卷（这会永久删除数据库数据）。

查看数据库和集合：

```bash
docker compose exec mongo mongosh mri_agent
```

进入 `mongosh` 后执行 `show collections`，可看到 `studies` 与 `jobs`；例如 `db.studies.findOne()` 查看一条研究记录。上传 MRI 后元数据进入 MongoDB，影像本体仍在 `data/uploads/`。

本地启动后端：

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1  # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

本地运行后端时，先在项目根目录单独启动 MongoDB：

```bash
docker compose up -d mongo
```

`backend/.env.example` 中有本地连接配置；需要本机启动时可复制为 `backend/.env`。Compose 启动时会自动使用容器网络地址 `mongodb://mongo:27017`。

### 后端启动层是怎么工作的

后端入口故意只负责“启动服务”，不在 `app/main.py` 中执行 MRI 分析：

1. `app/config.py` 读取 `MRI_` 前缀的环境变量，例如端口无关的 CORS、数据目录和模型目录配置。
2. `app/main.py` 创建 FastAPI、配置日志和 CORS，并把 `/api/v1` 下的路由集中注册。
3. FastAPI lifespan 在服务启动时调用 `app/startup.py`：创建影像目录，检查 MongoDB、ChromaDB 是否可用，并检查模型目录是否存在；结果保存到应用状态。
4. `GET /api/v1/health` 是存活检查，`GET /api/v1/ready` 返回启动依赖状态。MRI 处理仍由 `imaging`、`agents`、`rag` 等模块负责。

安装依赖并运行后，可以用下面的地址确认启动层：

```text
http://localhost:8000/api/v1/health
http://localhost:8000/api/v1/ready
```

MongoDB 是业务元数据依赖；未启动时服务会保持进程运行，但 `/api/v1/ready` 会标记为 `degraded`，上传和任务接口无法正常写入。ChromaDB 当前是可选依赖：未安装时服务仍可启动，但健康结果会标记为 `not_configured`，方便以后接入真正的向量库。

本地启动前端：

```bash
cd frontend
npm install
npm run dev
```

## API 概览

- `GET /api/v1/health`：健康检查
- `GET /api/v1/ready`：就绪检查和依赖状态
- `POST /api/v1/studies`：上传 MRI 文件（PNG/JPEG/TIFF/BMP/DICOM/NIfTI 扩展名）
- `GET /api/v1/studies?limit=50&offset=0`：分页查询研究列表
- `GET /api/v1/studies/{study_id}`：查询单个研究元数据
- `GET /api/v1/studies/{study_id}/file`：下载原始 MRI 文件
- `DELETE /api/v1/studies/{study_id}`：删除原始文件和对应元数据
- `POST /api/v1/studies/{study_id}/super-resolution`：创建超分任务
- `GET /api/v1/jobs/{job_id}`：查询任务状态
- `POST /api/v1/agent/chat`：向 MRI Agent 提问，返回任务建议和安全提示

## 目录说明

`backend/app/imaging` 负责图像读写和模型适配；`backend/app/agents` 负责规划和任务编排；`backend/app/rag` 与 `backend/app/llm` 是可替换接口；`backend/app/storage/repository.py` 将研究和任务元数据读写到 MongoDB。影像文件暂存本地 `data/`，生产部署可迁移到加密对象存储。`GET /api/v1/ready` 会报告 MongoDB 连通状态。

### 文件管理的数据流

上传时，服务先校验文件名、扩展名、MIME 类型和大小，然后先写入隐藏临时文件；写入成功后通过原子重命名放到
`data/uploads/{study_id}{extension}`，最后才把研究元数据写入 MongoDB。这样上传中断不会留下可被误用的半文件。
MongoDB 只保存原始显示名、文件类型、大小、创建时间和内部存储名，不保存大体积影像二进制内容。

下载和删除都只根据 MongoDB 中的内部存储名定位文件，并验证路径仍位于 `data/uploads` 内，避免客户端传入路径造成路径穿越。
删除成功后同时移除磁盘文件和 `studies` 元数据；历史任务记录不会被自动删除，便于审计，但其关联研究文件将不再可用。

生产环境请使用 MongoDB 用户认证、TLS、网络访问控制和备份，并将连接 URI 通过密钥管理系统注入；当前 Compose 配置用于本地开发，不应直接作为公网部署配置。
