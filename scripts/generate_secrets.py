#!/usr/bin/env python3
"""
生成安全密鑰的工具腳本

使用方法:
    python scripts/generate_secrets.py
"""

import secrets
import string
import sys
from pathlib import Path

def generate_secret_key(length: int = 32) -> str:
    """生成安全的密鑰"""
    return secrets.token_urlsafe(length)

def generate_password(length: int = 20) -> str:
    """生成強密碼"""
    alphabet = string.ascii_letters + string.digits + string.punctuation
    # 移除可能造成問題的字符
    alphabet = alphabet.replace('"', '').replace("'", '').replace('\\', '')
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def update_env_file():
    """更新 .env 文件中的密鑰"""
    env_path = Path(".env")
    if not env_path.exists():
        print("❌ .env 文件不存在。請先複製 .env.example 為 .env")
        return False
    
    # 讀取現有內容
    with open(env_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 生成新密鑰
    new_secret_key = generate_secret_key(32)
    new_encryption_key = generate_secret_key(32)[:32]  # 確保是32字符
    new_db_password = generate_password(20)
    
    # 更新內容
    updated_lines = []
    for line in lines:
        if line.startswith("SECRET_KEY="):
            updated_lines.append(f"SECRET_KEY={new_secret_key}\n")
            print(f"✅ 更新 SECRET_KEY")
        elif line.startswith("ENCRYPTION_KEY="):
            updated_lines.append(f"ENCRYPTION_KEY={new_encryption_key}\n")
            print(f"✅ 更新 ENCRYPTION_KEY")
        elif line.startswith("DB_PASSWORD=") and ("password" in line or line.strip().endswith("=")):
            updated_lines.append(f"DB_PASSWORD={new_db_password}\n")
            print(f"✅ 更新 DB_PASSWORD")
        else:
            updated_lines.append(line)
    
    # 寫回文件
    with open(env_path, 'w', encoding='utf-8') as f:
        f.writelines(updated_lines)
    
    return True

def main():
    """主函數"""
    print("🔐 GA+ 安全密鑰生成工具")
    print("-" * 40)
    
    if len(sys.argv) > 1 and sys.argv[1] == "--show":
        # 只顯示生成的密鑰，不更新文件
        print(f"SECRET_KEY={generate_secret_key(32)}")
        print(f"ENCRYPTION_KEY={generate_secret_key(32)[:32]}")
        print(f"DB_PASSWORD={generate_password(20)}")
    else:
        # 更新 .env 文件
        if update_env_file():
            print("\n✅ 密鑰已成功更新到 .env 文件")
            print("⚠️  請妥善保管這些密鑰，特別是在生產環境中")
        else:
            print("\n❌ 更新失敗")
            print("您可以手動生成密鑰：")
            print(f"SECRET_KEY={generate_secret_key(32)}")
            print(f"ENCRYPTION_KEY={generate_secret_key(32)[:32]}")
            print(f"DB_PASSWORD={generate_password(20)}")

if __name__ == "__main__":
    main()