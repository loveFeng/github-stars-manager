# Windows 环境配置指南

本指南帮助 Windows 开发者配置 GitHub Stars Manager 开发环境。

## 前置要求

### 1. Node.js 安装

- 下载并安装 Node.js 18.x LTS: https://nodejs.org/
- 验证安装: `node --version` (应显示 v18.x.x)
- 验证 npm: `npm --version`

### 2. Python 安装

- 下载并安装 Python 3.9+: https://www.python.org/downloads/
- ⚠️ **重要**: 勾选 "Add Python to PATH"
- 验证安装: `python --version` (应显示 Python 3.9+)
- 验证 pip: `pip --version`

### 3. pnpm 安装

```powershell
npm install -g pnpm
```

### 4. Visual Studio Build Tools (用于 native 模块)

better-sqlite3 需要编译，需要安装构建工具：

**选项 1: Visual Studio 2022 Community**
- 下载: https://visualstudio.microsoft.com/downloads/
- 安装时选择 "Desktop development with C++"

**选项 2: Build Tools (更轻量)**
```powershell
npm install -g windows-build-tools
```

或访问: https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2022

### 5. Git (可选但推荐)

- 下载: https://git-scm.com/download/win
- 配置行尾符自动转换:
  ```bash
  git config --global core.autocrlf input
  ```

## 快速开始

### 方法 1: 使用自动化脚本

```cmd
cd scripts
setup.bat
```

### 方法 2: 手动安装

#### 安装前端依赖
```cmd
cd github-stars-manager-frontend
pnpm install --prefer-offline
```

#### 安装后端依赖
```cmd
cd backend
pnpm install --prefer-offline
```

#### 安装 Python 依赖
```cmd
cd services
pip install -r requirements.txt
```

## 常见问题

### 问题 1: better-sqlite3 安装失败

**症状**: 
```
gyp ERR! find VS
gyp ERR! find VS msvs_version not set from command line or npm config
```

**解决方案**: 
1. 安装 Visual Studio Build Tools (见上文)
2. 或使用预编译版本:
   ```cmd
   npm install --build-from-source better-sqlite3
   ```

### 问题 2: PowerShell 执行策略错误

**症状**:
```
无法加载文件 xxx.ps1，因为在此系统上禁止运行脚本
```

**解决方案**:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 问题 3: Python 命令未找到

**症状**:
```
'python' 不是内部或外部命令
```

**解决方案**:
1. 检查 Python 是否已添加到 PATH
2. 或使用 `py` 命令替代 `python`
3. 重新安装 Python 并勾选 "Add to PATH"

### 问题 4: 路径过长错误

**症状**:
```
ENAMETOOLONG: name too long
```

**解决方案**:
1. 启用 Windows 长路径支持:
   - 运行 `gpedit.msc`
   - 计算机配置 > 管理模板 > 系统 > 文件系统
   - 启用 "启用 Win32 长路径"
   
2. 或修改注册表:
   ```reg
   HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\FileSystem
   LongPathsEnabled (DWORD) = 1
   ```

## Docker 环境 (推荐)

如果遇到配置问题，推荐使用 Docker:

### 安装 Docker Desktop for Windows

1. 下载: https://www.docker.com/products/docker-desktop
2. 安装并启用 WSL2 backend
3. 启动 Docker Desktop

### 使用 Docker Compose 运行

```cmd
cd Docker
docker-compose up --build
```

## 开发工具推荐

- **IDE**: Visual Studio Code
  - 安装扩展: Python, ESLint, Prettier
- **终端**: Windows Terminal
- **包管理**: pnpm (比 npm 更快)

## 性能优化建议

1. **使用 WSL2**: 在 WSL2 中运行项目可获得接近 Linux 的性能
2. **关闭实时防病毒扫描**: 对 node_modules 文件夹排除扫描
3. **使用 pnpm**: 比 npm/yarn 更快且节省磁盘空间

## 获取帮助

如果遇到问题:
1. 检查本文档的常见问题部分
2. 查看项目 Issues: [GitHub Issues]
3. 查看详细日志输出

---

**注意**: 本文档由跨平台兼容性修复工具自动生成
**更新时间**: 2025-10-31
