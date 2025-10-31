#!/usr/bin/env python3
"""
跨平台兼容性修复脚本
GitHub Stars Manager Project
生成时间: 2025-10-31 12:03:45

此脚本自动修复项目中的跨平台兼容性问题，包括：
1. 路径处理修复
2. Shell 命令跨平台化
3. 配置文件修正
4. 文件权限处理
5. 换行符统一
"""

import os
import sys
import json
import platform
import subprocess
import shutil
from pathlib import Path
from typing import List, Dict, Tuple


class CompatibilityFixer:
    """跨平台兼容性修复器"""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root).resolve()
        self.platform = platform.system()  # Windows, Darwin, Linux
        self.fixes_applied = []
        self.errors = []
        
    def log(self, message: str, level: str = "INFO"):
        """日志输出"""
        prefix = {
            "INFO": "ℹ️",
            "SUCCESS": "✅",
            "WARNING": "⚠️",
            "ERROR": "❌"
        }.get(level, "•")
        print(f"{prefix} {message}")
    
    def run_all_fixes(self):
        """运行所有修复"""
        self.log("开始跨平台兼容性修复...", "INFO")
        self.log(f"当前平台: {self.platform}", "INFO")
        self.log(f"项目根目录: {self.project_root}", "INFO")
        print("-" * 60)
        
        # 执行各项修复
        self.fix_package_json_scripts()
        self.create_gitattributes()
        self.fix_python_paths()
        self.create_cross_platform_scripts()
        self.check_node_modules()
        self.create_windows_setup_guide()
        
        # 总结
        print("-" * 60)
        self.log(f"修复完成! 共应用 {len(self.fixes_applied)} 项修复", "SUCCESS")
        if self.errors:
            self.log(f"发现 {len(self.errors)} 个错误", "WARNING")
            for error in self.errors:
                self.log(f"  {error}", "ERROR")
    
    def fix_package_json_scripts(self):
        """修复 package.json 中的跨平台兼容性问题"""
        self.log("修复 package.json 脚本命令...", "INFO")
        
        package_json_paths = [
            self.project_root / "github-stars-manager-frontend" / "package.json",
            self.project_root / "backend" / "package.json"
        ]
        
        for package_path in package_json_paths:
            if not package_path.exists():
                continue
            
            try:
                with open(package_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                modified = False
                
                if 'scripts' in data:
                    scripts = data['scripts']
                    
                    # 替换 rm -rf 为 rimraf
                    for key, value in scripts.items():
                        if 'rm -rf' in value:
                            new_value = value.replace('rm -rf', 'rimraf')
                            scripts[key] = new_value
                            modified = True
                            self.log(f"  修复脚本: {key}", "SUCCESS")
                    
                    # 检查是否需要添加 rimraf 依赖
                    if modified:
                        if 'devDependencies' not in data:
                            data['devDependencies'] = {}
                        
                        if 'rimraf' not in data.get('devDependencies', {}):
                            data['devDependencies']['rimraf'] = '^5.0.0'
                            self.log(f"  添加 rimraf 依赖", "SUCCESS")
                
                if modified:
                    # 备份原文件
                    backup_path = package_path.with_suffix('.json.backup')
                    shutil.copy2(package_path, backup_path)
                    
                    # 写入修改
                    with open(package_path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                        f.write('\n')
                    
                    self.fixes_applied.append(f"修复 {package_path.name}")
                    self.log(f"  已修复: {package_path.relative_to(self.project_root)}", "SUCCESS")
            
            except Exception as e:
                self.errors.append(f"修复 {package_path} 失败: {str(e)}")
                self.log(f"  修复失败: {str(e)}", "ERROR")
    
    def create_gitattributes(self):
        """创建 .gitattributes 文件统一换行符"""
        self.log("创建 .gitattributes 配置...", "INFO")
        
        gitattributes_path = self.project_root / ".gitattributes"
        
        content = """# 跨平台换行符配置
# 自动检测文本文件并规范化换行符
* text=auto

# 源代码文件使用 LF
*.py text eol=lf
*.js text eol=lf
*.ts text eol=lf
*.jsx text eol=lf
*.tsx text eol=lf
*.json text eol=lf
*.md text eol=lf
*.yml text eol=lf
*.yaml text eol=lf
*.sh text eol=lf
*.bash text eol=lf

# 配置文件
.env* text eol=lf
.gitignore text eol=lf
.gitattributes text eol=lf
Dockerfile text eol=lf
docker-compose.yml text eol=lf

# Windows 批处理文件使用 CRLF
*.bat text eol=crlf
*.cmd text eol=crlf

# 二进制文件
*.png binary
*.jpg binary
*.jpeg binary
*.gif binary
*.ico binary
*.pdf binary
*.zip binary
*.tar.gz binary
*.woff binary
*.woff2 binary
*.ttf binary
*.eot binary
"""
        
        try:
            with open(gitattributes_path, 'w', encoding='utf-8', newline='\n') as f:
                f.write(content)
            
            self.fixes_applied.append("创建 .gitattributes")
            self.log("  .gitattributes 已创建", "SUCCESS")
        except Exception as e:
            self.errors.append(f"创建 .gitattributes 失败: {str(e)}")
            self.log(f"  创建失败: {str(e)}", "ERROR")
    
    def fix_python_paths(self):
        """修复 Python 文件中的路径处理"""
        self.log("检查 Python 文件路径处理...", "INFO")
        
        # 查找所有 Python 文件
        python_files = list(self.project_root.glob("**/*.py"))
        
        issues_found = 0
        files_with_issues = []
        
        for py_file in python_files:
            # 跳过虚拟环境和 node_modules
            if 'venv' in str(py_file) or 'node_modules' in str(py_file):
                continue
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 检查潜在的路径问题
                issues = []
                
                # 检查硬编码的路径分隔符
                if '\\\\' in content or '"\\\\"' in content:
                    issues.append("包含硬编码的 Windows 路径分隔符")
                
                # 检查是否使用了 os.path 或 pathlib
                if 'os.path.join' not in content and 'Path(' not in content:
                    if '/' in content and 'http' not in content:
                        # 可能有路径拼接问题
                        if any(x in content for x in ['" + "', '+ "/', '"/']):
                            issues.append("可能存在不跨平台的路径拼接")
                
                if issues:
                    issues_found += len(issues)
                    files_with_issues.append(py_file.relative_to(self.project_root))
            
            except Exception as e:
                pass
        
        if files_with_issues:
            self.log(f"  发现 {issues_found} 个潜在路径问题", "WARNING")
            self.log(f"  涉及 {len(files_with_issues)} 个文件", "WARNING")
            self.log("  建议手动检查以下文件:", "INFO")
            for f in files_with_issues[:10]:  # 只显示前10个
                self.log(f"    - {f}", "INFO")
        else:
            self.log("  未发现明显的路径问题", "SUCCESS")
    
    def create_cross_platform_scripts(self):
        """创建跨平台的辅助脚本"""
        self.log("创建跨平台辅助脚本...", "INFO")
        
        # 创建 setup 脚本
        scripts_dir = self.project_root / "scripts"
        scripts_dir.mkdir(exist_ok=True)
        
        # Windows 批处理脚本
        if self.platform == "Windows" or True:  # 总是创建
            setup_bat = scripts_dir / "setup.bat"
            setup_content = """@echo off
REM GitHub Stars Manager - Windows Setup Script
echo Setting up GitHub Stars Manager...

REM Check Node.js
where node >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Node.js not found. Please install Node.js 18+
    exit /b 1
)

REM Check Python
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python not found. Please install Python 3.9+
    exit /b 1
)

echo Installing frontend dependencies...
cd github-stars-manager-frontend
call pnpm install --prefer-offline
cd ..

echo Installing backend dependencies...
cd backend
call pnpm install --prefer-offline
cd ..

echo Installing Python dependencies...
cd services
pip install -r requirements.txt
cd ..

echo Setup complete!
pause
"""
            try:
                with open(setup_bat, 'w', encoding='utf-8', newline='\r\n') as f:
                    f.write(setup_content)
                self.log("  创建 setup.bat", "SUCCESS")
                self.fixes_applied.append("创建 Windows setup 脚本")
            except Exception as e:
                self.errors.append(f"创建 setup.bat 失败: {str(e)}")
        
        # Unix shell 脚本
        setup_sh = scripts_dir / "setup.sh"
        setup_content_sh = """#!/bin/bash
# GitHub Stars Manager - Unix Setup Script
echo "Setting up GitHub Stars Manager..."

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "ERROR: Node.js not found. Please install Node.js 18+"
    exit 1
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python not found. Please install Python 3.9+"
    exit 1
fi

echo "Installing frontend dependencies..."
cd github-stars-manager-frontend
pnpm install --prefer-offline
cd ..

echo "Installing backend dependencies..."
cd backend
pnpm install --prefer-offline
cd ..

echo "Installing Python dependencies..."
cd services
pip3 install -r requirements.txt
cd ..

echo "Setup complete!"
"""
        try:
            with open(setup_sh, 'w', encoding='utf-8', newline='\n') as f:
                f.write(setup_content_sh)
            
            # 在 Unix 系统上设置执行权限
            if self.platform in ["Linux", "Darwin"]:
                os.chmod(setup_sh, 0o755)
            
            self.log("  创建 setup.sh", "SUCCESS")
            self.fixes_applied.append("创建 Unix setup 脚本")
        except Exception as e:
            self.errors.append(f"创建 setup.sh 失败: {str(e)}")
    
    def check_node_modules(self):
        """检查 Node.js 模块兼容性"""
        self.log("检查 Node.js 模块兼容性...", "INFO")
        
        # 检查 better-sqlite3
        backend_package = self.project_root / "backend" / "package.json"
        if backend_package.exists():
            try:
                with open(backend_package, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if 'better-sqlite3' in data.get('dependencies', {}):
                    self.log("  检测到 better-sqlite3 依赖", "INFO")
                    if self.platform == "Windows":
                        self.log("  Windows 平台需要 Visual Studio Build Tools", "WARNING")
                        self.log("  参考: https://github.com/nodejs/node-gyp#installation", "INFO")
            except Exception as e:
                pass
    
    def create_windows_setup_guide(self):
        """创建 Windows 环境配置指南"""
        self.log("创建 Windows 配置指南...", "INFO")
        
        guide_path = self.project_root / "WINDOWS_SETUP.md"
        
        guide_content = """# Windows 环境配置指南

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
   HKEY_LOCAL_MACHINE\\SYSTEM\\CurrentControlSet\\Control\\FileSystem
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
"""
        
        try:
            with open(guide_path, 'w', encoding='utf-8', newline='\n') as f:
                f.write(guide_content)
            
            self.fixes_applied.append("创建 Windows 配置指南")
            self.log("  WINDOWS_SETUP.md 已创建", "SUCCESS")
        except Exception as e:
            self.errors.append(f"创建 Windows 配置指南失败: {str(e)}")
            self.log(f"  创建失败: {str(e)}", "ERROR")


def main():
    """主函数"""
    print("=" * 60)
    print("GitHub Stars Manager - 跨平台兼容性修复工具")
    print("=" * 60)
    print()
    
    # 查找项目根目录
    current_dir = Path.cwd()
    project_root = current_dir
    
    # 如果当前目录有 package.json 或特征文件，认为是项目根目录
    if not (project_root / "github-stars-manager-frontend").exists():
        # 尝试上级目录
        if (current_dir.parent / "github-stars-manager-frontend").exists():
            project_root = current_dir.parent
    
    # 创建修复器实例
    fixer = CompatibilityFixer(project_root=project_root)
    
    # 运行所有修复
    fixer.run_all_fixes()
    
    print()
    print("=" * 60)
    print("后续步骤:")
    print("1. 在 frontend 目录运行: pnpm install (安装 rimraf)")
    print("2. 提交 .gitattributes 文件到版本控制")
    print("3. Windows 用户查看 WINDOWS_SETUP.md")
    print("4. 运行: git add --renormalize . (重新规范化换行符)")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n用户中断操作")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
