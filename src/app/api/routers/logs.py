import os
import json
import shutil
from datetime import datetime, timedelta
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel

# 日志保存API路由
router = APIRouter()

# 日志数据模型
class LogEntry(BaseModel):
    timestamp: str
    level: str
    category: str
    message: str
    data: Dict[str, Any] = None

class LogsRequest(BaseModel):
    logs: List[LogEntry]
    timestamp: str

# 日志目录配置
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# 日志文件最大大小 (MB)
MAX_LOG_FILE_SIZE = 10

# 日志保留天数
LOG_RETENTION_DAYS = 7

@router.post("/save", status_code=status.HTTP_200_OK)
async def save_logs(request: Request):
    """保存前端日志到服务器文件系统"""
    try:
        # 直接从请求体获取原始数据
        request_data = await request.json()
        logs = request_data.get('logs', [])
        timestamp = request_data.get('timestamp', datetime.now().isoformat())
        
        # 记录保存请求
        print(f"收到日志保存请求: {len(logs)} 条日志, 时间: {timestamp}")
        
        # 生成日志文件名
        date_str = datetime.now().strftime("%Y-%m-%d")
        filename = f"frontend-logs-{date_str}.json"
        filepath = os.path.join(LOG_DIR, filename)
        
        # 如果文件已存在，读取现有日志并合并
        existing_logs = []
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    existing_logs = json.load(f)
            except (json.JSONDecodeError, UnicodeDecodeError):
                # 如果文件格式错误，则忽略
                print(f"日志文件 {filepath} 格式错误，将创建新文件")
                existing_logs = []
        
        # 验证并清理日志数据
        valid_logs = []
        for log in logs:
            try:
                # 确保日志条目包含必要的字段
                if isinstance(log, dict) and all(key in log for key in ['timestamp', 'level', 'category', 'message']):
                    valid_logs.append(log)
                else:
                    print(f"无效的日志条目: {log}")
            except Exception as e:
                print(f"处理日志条目失败: {e}")
                # 如果处理失败，跳过该日志条目
                continue
        
        print(f"成功验证 {len(valid_logs)} 条日志，跳过 {len(logs) - len(valid_logs)} 条")
        
        # 合并日志
        combined_logs = existing_logs + valid_logs
        
        # 检查文件大小，如果太大则进行轮转
        if os.path.exists(filepath):
            file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
            if file_size_mb > MAX_LOG_FILE_SIZE:
                # 创建一个带时间戳的新文件名
                timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                rotated_filename = f"frontend-logs-{timestamp_str}.json"
                rotated_filepath = os.path.join(LOG_DIR, rotated_filename)
                
                # 移动旧文件
                shutil.move(filepath, rotated_filepath)
                print(f"日志文件已轮转: {filepath} -> {rotated_filepath}")
        
        # 写入文件
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(combined_logs, f, ensure_ascii=False, indent=2)
            print(f"成功保存 {len(valid_logs)} 条日志到 {filepath}")
        except Exception as e:
            print(f"写入日志文件失败: {e}")
            # 如果写入失败，尝试保存为更简单的格式
            try:
                # 只保存前10条日志，避免过大
                simple_logs = combined_logs[:10]
                simple_filepath = os.path.join(LOG_DIR, f"frontend-logs-{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
                with open(simple_filepath, "w", encoding="utf-8") as f:
                    json.dump(simple_logs, f, ensure_ascii=False, indent=2)
                print(f"使用简化格式保存了 {len(simple_logs)} 条日志到 {simple_filepath}")
            except Exception as e2:
                print(f"简化格式保存也失败: {e2}")
                # 如果所有保存都失败，只记录到控制台
                print(f"无法保存日志，将只记录到控制台: {len(combined_logs)} 条日志")
        
        # 清理旧日志文件
        cleanup_old_logs()
        
        return {
            "status": "success",
            "message": f"成功保存 {len(valid_logs)} 条日志",
            "filepath": filepath
        }
    
    except Exception as e:
        print(f"保存日志时出错: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": f"保存日志失败: {str(e)}"}
        )

@router.get("/list", status_code=status.HTTP_200_OK)
async def list_log_files():
    """获取服务器上所有日志文件列表"""
    try:
        # 获取所有日志文件
        log_files = []
        for filename in os.listdir(LOG_DIR):
            if filename.startswith("frontend-logs-") and filename.endswith(".json"):
                filepath = os.path.join(LOG_DIR, filename)
                stat = os.stat(filepath)
                log_files.append({
                    "filename": filename,
                    "filepath": filepath,
                    "size": os.path.getsize(filepath),
                    "size_mb": round(os.path.getsize(filepath) / (1024 * 1024), 2),
                    "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
        
        # 按修改时间排序
        log_files.sort(key=lambda x: x["modified"], reverse=True)
        
        return {
            "status": "success",
            "count": len(log_files),
            "files": log_files
        }
    
    except Exception as e:
        print(f"获取日志文件列表时出错: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": f"获取日志文件列表失败: {str(e)}"}
        )

@router.get("/download/{filename}", status_code=status.HTTP_200_OK)
async def download_log_file(filename: str):
    """下载指定的日志文件"""
    try:
        # 安全检查：只允许下载前端日志文件
        if not filename.startswith("frontend-logs-") or not filename.endswith(".json"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": "无效的文件名"}
            )
        
        filepath = os.path.join(LOG_DIR, filename)
        
        # 检查文件是否存在
        if not os.path.exists(filepath):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": "日志文件不存在"}
            )
        
        # 读取文件内容
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        
        # 解析JSON内容
        try:
            parsed_content = json.loads(content)
        except json.JSONDecodeError:
            print(f"解析日志文件 {filepath} 失败")
            parsed_content = []
        
        return {
            "status": "success",
            "filename": filename,
            "content": parsed_content,
            "size": os.path.getsize(filepath),
            "modified": datetime.fromtimestamp(os.path.getmtime(filepath)).isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"下载日志文件时出错: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": f"下载日志文件失败: {str(e)}"}
        )

@router.delete("/cleanup", status_code=status.HTTP_200_OK)
async def cleanup_logs():
    """清理旧的日志文件"""
    try:
        deleted_count = cleanup_old_logs()
        
        return {
            "status": "success",
            "message": f"成功清理 {deleted_count} 个旧日志文件",
            "deleted_count": deleted_count
        }
    
    except Exception as e:
        print(f"清理日志文件时出错: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": f"清理日志文件失败: {str(e)}"}
        )

def cleanup_old_logs():
    """删除指定天数之前的日志文件"""
    try:
        cutoff_date = datetime.now() - timedelta(days=LOG_RETENTION_DAYS)
        deleted_count = 0
        
        for filename in os.listdir(LOG_DIR):
            if filename.startswith("frontend-logs-") and filename.endswith(".json"):
                filepath = os.path.join(LOG_DIR, filename)
                file_modified_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                
                if file_modified_time < cutoff_date:
                    os.remove(filepath)
                    print(f"删除旧日志文件: {filepath}")
                    deleted_count += 1
        
        return deleted_count
    
    except Exception as e:
        print(f"清理旧日志文件时出错: {e}")
        return 0