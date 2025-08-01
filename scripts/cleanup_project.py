#!/usr/bin/env python3
"""
專案清理工具

清理不必要的文件和目錄
"""

import os
import shutil
from pathlib import Path
import argparse

# 定義要清理的模式
CLEANUP_PATTERNS = {
    "python_cache": {
        "patterns": ["__pycache__", "*.pyc", "*.pyo", "*.pyd", ".Python"],
        "description": "Python 編譯文件"
    },
    "ide_files": {
        "patterns": [".vscode", ".idea", "*.swp", "*.swo", "*~"],
        "description": "IDE 配置文件"
    },
    "os_files": {
        "patterns": [".DS_Store", "Thumbs.db", "desktop.ini"],
        "description": "系統文件"
    },
    "logs": {
        "patterns": ["*.log", "logs/"],
        "description": "日誌文件"
    },
    "temp_files": {
        "patterns": ["*.tmp", "*.temp", "*.bak", "~*"],
        "description": "臨時文件"
    },
    "test_files": {
        "patterns": [".pytest_cache", ".coverage", "htmlcov/", ".tox/"],
        "description": "測試相關文件"
    },
    "empty_dirs": {
        "patterns": [],
        "description": "空目錄"
    }
}

# 需要確認的文件
CONFIRM_PATTERNS = {
    "database": {
        "patterns": ["*.db", "*.sqlite", "*.sqlite3"],
        "description": "資料庫文件"
    },
    "node_modules": {
        "patterns": ["node_modules/"],
        "description": "Node.js 依賴"
    }
}


def find_files_to_clean(root_path: Path, patterns: list) -> list:
    """找出符合模式的文件"""
    files_to_clean = []
    
    for pattern in patterns:
        if pattern.endswith("/"):
            # 目錄模式
            for path in root_path.rglob(pattern.rstrip("/")):
                if path.is_dir():
                    files_to_clean.append(path)
        else:
            # 文件模式
            for path in root_path.rglob(pattern):
                if path.is_file():
                    files_to_clean.append(path)
    
    return files_to_clean


def find_empty_dirs(root_path: Path) -> list:
    """找出空目錄"""
    empty_dirs = []
    
    for root, dirs, files in os.walk(root_path):
        # 跳過 .git 目錄
        if ".git" in root:
            continue
            
        # 檢查目錄是否為空
        if not dirs and not files:
            empty_dirs.append(Path(root))
    
    return empty_dirs


def format_size(size_bytes: int) -> str:
    """格式化文件大小"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


def get_size(path: Path) -> int:
    """獲取文件或目錄大小"""
    if path.is_file():
        return path.stat().st_size
    elif path.is_dir():
        total = 0
        for item in path.rglob("*"):
            if item.is_file():
                total += item.stat().st_size
        return total
    return 0


def clean_files(files: list, dry_run: bool = True) -> tuple:
    """清理文件"""
    total_size = 0
    cleaned_count = 0
    
    for file_path in files:
        try:
            size = get_size(file_path)
            total_size += size
            
            if not dry_run:
                if file_path.is_dir():
                    shutil.rmtree(file_path)
                else:
                    file_path.unlink()
                cleaned_count += 1
                print(f"  [v] 已刪除: {file_path}")
            else:
                print(f"  [-] 將刪除: {file_path} ({format_size(size)})")
                
        except Exception as e:
            print(f"  [x] 錯誤: {file_path} - {e}")
    
    return cleaned_count, total_size


def main():
    parser = argparse.ArgumentParser(description="清理 GA+ 專案中的不必要文件")
    parser.add_argument("--dry-run", action="store_true", default=True,
                        help="僅顯示將要刪除的文件，不實際刪除")
    parser.add_argument("--execute", action="store_true",
                        help="實際執行刪除操作")
    parser.add_argument("--include-db", action="store_true",
                        help="包含資料庫文件")
    parser.add_argument("--include-node", action="store_true",
                        help="包含 node_modules 目錄")
    
    args = parser.parse_args()
    
    # 設置執行模式
    dry_run = not args.execute
    
    # 獲取專案根目錄
    project_root = Path(__file__).parent.parent
    
    print(f"[CLEANUP] GA+ 專案清理工具")
    print(f"專案路徑: {project_root}")
    print(f"模式: {'預覽' if dry_run else '執行'}")
    print("-" * 60)
    
    total_cleaned = 0
    total_size = 0
    
    # 清理標準模式
    for category, info in CLEANUP_PATTERNS.items():
        print(f"\n[{category.upper()}] {info['description']}:")
        
        if category == "empty_dirs":
            files = find_empty_dirs(project_root)
        else:
            files = find_files_to_clean(project_root, info['patterns'])
        
        if files:
            count, size = clean_files(files, dry_run)
            total_cleaned += count
            total_size += size
        else:
            print("  沒有找到需要清理的文件")
    
    # 處理需要確認的文件
    if args.include_db:
        print(f"\n[DATABASE] {CONFIRM_PATTERNS['database']['description']}:")
        files = find_files_to_clean(project_root, CONFIRM_PATTERNS['database']['patterns'])
        if files:
            count, size = clean_files(files, dry_run)
            total_cleaned += count
            total_size += size
    
    if args.include_node:
        print(f"\n[NODE_MODULES] {CONFIRM_PATTERNS['node_modules']['description']}:")
        files = find_files_to_clean(project_root, CONFIRM_PATTERNS['node_modules']['patterns'])
        if files:
            count, size = clean_files(files, dry_run)
            total_cleaned += count
            total_size += size
    
    # 顯示總結
    print("\n" + "=" * 60)
    if dry_run:
        print(f"[SUMMARY] 預覽總結:")
        print(f"   將清理文件數量: {len(files) if 'files' in locals() else 0}")
        print(f"   將釋放空間: {format_size(total_size)}")
        print(f"\n[TIP] 提示: 使用 --execute 參數來實際執行清理")
        print(f"   可選: --include-db 包含資料庫文件")
        print(f"   可選: --include-node 包含 node_modules")
    else:
        print(f"[SUCCESS] 清理完成:")
        print(f"   已清理文件數量: {total_cleaned}")
        print(f"   已釋放空間: {format_size(total_size)}")


if __name__ == "__main__":
    main()