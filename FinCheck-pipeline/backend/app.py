"""
Compliance-to-Code 后端主应用

提供API接口服务，用于与前端交互。
"""

import os
import sys
import json
import uvicorn
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date

# 将项目根目录添加到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

# 核心模块导入
from tools.execution_engine import ExecutionEngine
from tools.compliance_report import get_report_for_result
from tools.data_fetcher import DataFetcher  # 添加DataFetcher导入

# FastAPI 应用初始化
app = FastAPI(
    title="Compliance-to-Code API",
    description="一个用于执行金融合规自动化检查的API服务。",
    version="2.0.0",
)

# 中间件配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局实例
# 注意: 现在引擎是所有操作的唯一入口点
execution_engine = ExecutionEngine()
data_fetcher = DataFetcher()  # 添加DataFetcher实例

# API 数据模型
class CheckRequest(BaseModel):
    regulation_id: str
    company_name: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    shareholder: Optional[str] = None  # 添加股东参数，可选

class RegulationInfo(BaseModel):
    id: str
    name: str

class RegulationsResponse(BaseModel):
    regulations: List[RegulationInfo]

class ResultRequest(BaseModel):
    result_path: str

class CompaniesResponse(BaseModel):
    companies: List[str]


# API 端点定义

@app.get("/api/regulations", response_model=RegulationsResponse)
async def get_regulations():
    """
    获取所有可用的法规列表。
    """
    graphs_dir = os.path.join(project_root, "data", "graphs")
    regulation_list = []
    try:
        for filename in os.listdir(graphs_dir):
            if filename.endswith(".json"):
                regulation_id = filename.replace('.json', '')
                file_path = os.path.join(graphs_dir, filename)
                with open(file_path, 'r', encoding='utf-8') as f:
                    graph_data = json.load(f)
                    regulation_name = graph_data.get("regulation_name", "未命名法规")
                    regulation_list.append(RegulationInfo(id=regulation_id, name=regulation_name))
        return RegulationsResponse(regulations=regulation_list)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取法规列表时出错: {str(e)}")

# 新增API端点：获取指定法规下的可用公司列表
@app.get("/api/companies/{regulation_id}", response_model=CompaniesResponse)
async def get_companies_for_regulation(regulation_id: str):
    """
    获取指定法规下的可用公司列表。
    
    参数:
        regulation_id: 法规ID
    
    返回:
        可用公司名称列表
    """
    try:
        companies = data_fetcher.get_available_companies(regulation_id)
        return CompaniesResponse(companies=companies)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取公司列表时出错: {str(e)}")

# 新增API端点：获取指定法规下的可用股东列表
@app.get("/api/shareholders/{regulation_id}/{company_name}")
async def get_shareholders_for_regulation(regulation_id: str, company_name: str):
    """
    获取指定法规和公司下的可用股东列表。
    目前仅支持regulation_08法规。
    
    参数:
        regulation_id: 法规ID
        company_name: 公司名称
    
    返回:
        可用股东名称列表
    """
    if regulation_id != "regulation_08":
        return {"shareholders": []}
    
    try:
        shareholders = data_fetcher.get_available_shareholders(regulation_id, company_name)
        return {"shareholders": shareholders}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取股东列表时出错: {str(e)}")

@app.post("/api/check")
async def run_compliance_check(request: CheckRequest):
    """
    执行合规检查。
    此端点现在是 ExecutionEngine.run_and_save 方法的一个简单封装。
    """
    try:
        # 准备参数字典
        params = {
            "company_name": request.company_name,
            "regulation_id": request.regulation_id,
            "start_date": str(request.start_date) if request.start_date else None,
            "end_date": str(request.end_date) if request.end_date else None,
        }
        
        # 如果是regulation_08并且提供了股东参数，则添加到参数列表
        if request.regulation_id == "regulation_08" and request.shareholder:
            params["shareholder"] = request.shareholder
        
        # 直接调用统一的引擎入口
        response_data = execution_engine.run_and_save(**params)
        
        # 检查引擎是否返回了错误
        if "error" in response_data:
            # 根据错误类型返回不同的HTTP状态码
            if "未找到" in response_data["error"]:
                raise HTTPException(status_code=404, detail=response_data["error"])
            else:
                raise HTTPException(status_code=500, detail=response_data["error"])

        return response_data

    except HTTPException as http_exc:
        # 重新抛出已知的HTTP异常
        raise http_exc
    except Exception as e:
        # 捕获其他所有异常
        import traceback
        error_detail = f"执行合规检查时出错: {str(e)}\n{traceback.format_exc()}"
        print(error_detail)
        raise HTTPException(status_code=500, detail=error_detail)

@app.get("/api/results")
async def get_results_list():
    """
    获取所有可用的结果列表。
    """
    results_dir = os.path.join(project_root, "results")
    results_list = []
    try:
        for dirname in os.listdir(results_dir):
            dir_path = os.path.join(results_dir, dirname)
            if os.path.isdir(dir_path):
                metadata_path = os.path.join(dir_path, "request_metadata.json")
                if os.path.exists(metadata_path):
                    with open(metadata_path, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                        results_list.append({
                            "path": dirname,
                            "company_name": metadata.get("company_name", "未知公司"),
                            "regulation_id": metadata.get("regulation_id", "未知法规"),
                            "date": dirname.split("_")[0] + "_" + dirname.split("_")[1]
                        })
        return {"results": sorted(results_list, key=lambda x: x["date"], reverse=True)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取结果列表时出错: {str(e)}")

@app.get("/api/result/{result_path}")
async def get_result(result_path: str):
    """
    获取指定路径的结果文件。
    优先使用后处理后的结果文件（processed_result.json）。
    """
    try:
        # 安全检查，防止路径遍历攻击
        if ".." in result_path or result_path.startswith("/"):
            raise HTTPException(status_code=400, detail="非法的结果路径")
            
        # 首先尝试查找processed_result.json（优先使用后处理后的结果）
        processed_result_path = os.path.join(project_root, "results", result_path, "processed_result.json")
        if os.path.exists(processed_result_path):
            result_file_path = processed_result_path
        else:
            # 如果没有后处理结果，则使用原始结果
            result_file_path = os.path.join(project_root, "results", result_path, "result.json")
            if not os.path.exists(result_file_path):
                raise HTTPException(status_code=404, detail=f"结果文件不存在: {result_path}")
        
        with open(result_file_path, 'r', encoding='utf-8') as f:
            result_data = json.load(f)
            
        return result_data
        
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取结果文件时出错: {str(e)}")


@app.get("/api/report/{result_path}")
async def get_compliance_report(result_path: str):
    """
    获取指定结果的合规报告
    """
    try:
        # 安全检查，防止路径遍历攻击
        if ".." in result_path or result_path.startswith("/"):
            raise HTTPException(status_code=400, detail="非法的结果路径")
        
        # 使用compliance_report模块获取报告
        report_content = get_report_for_result(result_path)
        
        if not report_content:
            raise HTTPException(status_code=404, detail="无法生成合规报告")
        
        return {"report": report_content}
        
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取合规报告时出错: {str(e)}")


@app.get("/api/download/report/{result_path}")
async def download_report(result_path: str):
    """
    下载指定结果的合规报告文件
    """
    try:
        # 安全检查，防止路径遍历攻击
        if ".." in result_path or result_path.startswith("/"):
            raise HTTPException(status_code=400, detail="非法的结果路径")
        
        # 构建报告文件路径
        report_path = os.path.join(project_root, "results", result_path, "compliance_report.md")
        
        # 检查报告是否存在
        if not os.path.exists(report_path):
            # 尝试生成报告
            report_content = get_report_for_result(result_path)
            if not report_content:
                raise HTTPException(status_code=404, detail="无法生成合规报告")
        
        # 设置下载文件名
        filename = f"{result_path}_compliance_report.md"
        
        # 返回文件响应
        return FileResponse(
            path=report_path, 
            filename=filename, 
            media_type='text/markdown'
        )
        
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"下载合规报告时出错: {str(e)}")


@app.get("/api/download/json/{result_path}")
async def download_json(result_path: str):
    """
    下载指定结果的JSON文件
    """
    try:
        # 安全检查，防止路径遍历攻击
        if ".." in result_path or result_path.startswith("/"):
            raise HTTPException(status_code=400, detail="非法的结果路径")
        
        # 首先尝试查找processed_result.json
        json_path = os.path.join(project_root, "results", result_path, "processed_result.json")
        if not os.path.exists(json_path):
            # 如果没有processed_result.json，则尝试使用result.json
            json_path = os.path.join(project_root, "results", result_path, "result.json")
            if not os.path.exists(json_path):
                raise HTTPException(status_code=404, detail="结果文件不存在")
        
        # 设置下载文件名
        filename = f"{result_path}_result.json"
        
        # 返回文件响应
        return FileResponse(
            path=json_path, 
            filename=filename, 
            media_type='application/json'
        )
        
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"下载JSON文件时出错: {str(e)}")

# 将前端目录挂载为静态文件服务
app.mount("/", StaticFiles(directory=os.path.join(project_root, "frontend"), html=True), name="frontend")

if __name__ == "__main__":
    uvicorn.run("backend.app:app", host="0.0.0.0", port=8008, reload=True) 