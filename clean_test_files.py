"""
清理测试文件脚本
运行前会询问确认，避免误删
"""

import os
import shutil
from pathlib import Path

def print_colored(text, color):
    """打印彩色文字"""
    colors = {
        'red': '\033[91m',
        'green': '\033[92m',
        'yellow': '\033[93m',
        'blue': '\033[94m',
        'end': '\033[0m'
    }
    print(f"{colors.get(color, '')}{text}{colors['end']}")

def get_file_size(size_bytes):
    """获取文件大小（友好格式）"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} GB"

def main():
    print_colored("="*60, "blue")
    print_colored("🧹 DeepSeek 测试文件清理工具", "blue")
    print_colored("="*60, "blue")
    
    # 当前目录
    current_dir = Path.cwd()
    print_colored(f"\n当前目录: {current_dir}", "yellow")
    
    # 定义要清理的文件类型和目录
    clean_patterns = [
        "test_*.py",
        "debug_*.py",
        "check_*.py",
        "find_*.py",
        "*_test.py",
        "temp_*.py",
        "*.log",
        "*.tmp",
        "*.temp",
        "debug_*.png",
        "*.screenshot.png",
        "*.html",
        "temp_results.json",
        "batch_results_*.json",
        "batch_results_*.txt",
    ]
    
    clean_dirs = [
        "__pycache__",
        ".pytest_cache",
        ".coverage",
    ]
    
    # 收集要清理的文件
    files_to_delete = []
    total_size = 0
    
    print_colored("\n🔍 扫描可清理的文件...", "yellow")
    
    # 扫描文件
    for pattern in clean_patterns:
        for file_path in current_dir.glob(pattern):
            if file_path.is_file():
                size = file_path.stat().st_size
                files_to_delete.append(file_path)
                total_size += size
                print_colored(f"  📄 {file_path.name} ({get_file_size(size)})", "yellow")
    
    # 扫描目录
    dirs_to_delete = []
    for dir_name in clean_dirs:
        dir_path = current_dir / dir_name
        if dir_path.exists() and dir_path.is_dir():
            # 计算目录大小
            dir_size = sum(f.stat().st_size for f in dir_path.rglob('*') if f.is_file())
            dirs_to_delete.append(dir_path)
            total_size += dir_size
            print_colored(f"  📁 {dir_name}/ ({get_file_size(dir_size)})", "yellow")
    
    if not files_to_delete and not dirs_to_delete:
        print_colored("\n✨ 没有找到可清理的文件！", "green")
        return
    
    print_colored(f"\n📊 总计: {len(files_to_delete)} 个文件, {len(dirs_to_delete)} 个目录, 总大小: {get_file_size(total_size)}", "yellow")
    
    # 确认删除
    print_colored("\n⚠️  以上文件将被删除！", "red")
    confirm = input("是否继续？(y/N): ").lower()
    
    if confirm == 'y':
        deleted_count = 0
        deleted_size = 0
        
        # 删除文件
        for file_path in files_to_delete:
            try:
                file_size = file_path.stat().st_size
                file_path.unlink()
                print_colored(f"  ✅ 删除文件: {file_path.name}", "green")
                deleted_count += 1
                deleted_size += file_size
            except Exception as e:
                print_colored(f"  ❌ 删除失败 {file_path.name}: {e}", "red")
        
        # 删除目录
        for dir_path in dirs_to_delete:
            try:
                dir_size = sum(f.stat().st_size for f in dir_path.rglob('*') if f.is_file())
                shutil.rmtree(dir_path)
                print_colored(f"  ✅ 删除目录: {dir_path.name}/", "green")
                deleted_size += dir_size
            except Exception as e:
                print_colored(f"  ❌ 删除失败 {dir_path.name}/: {e}", "red")
        
        print_colored(f"\n🎉 清理完成！释放 {get_file_size(deleted_size)} 空间", "green")
    else:
        print_colored("\n❌ 操作已取消", "red")

if __name__ == "__main__":
    main()
