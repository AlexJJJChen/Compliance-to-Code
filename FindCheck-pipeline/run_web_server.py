import uvicorn
import sys
import os

# 将项目根目录添加到Python路径
# 这样我们就可以从任何地方运行这个脚本
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 显式地从 backend.app 模块导入 app 对象
from backend.app import app

if __name__ == "__main__":
    # 直接将导入的 app 对象传递给 uvicorn
    # 禁用 reload 功能，因为直接传递 app 对象与 reload=True 不兼容
    uvicorn.run(app, host="0.0.0.0", port=8008, reload=False) 