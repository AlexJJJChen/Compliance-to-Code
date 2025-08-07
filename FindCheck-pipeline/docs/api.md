# API接口文档

本文档详细说明了Compliance-to-Code后端服务提供的所有API端点。

## 1. 获取可用法规列表

此端点用于获取所有可供检查的法规列表，以便在前端界面中动态展示。

- **URL**: `/api/regulations`
- **Method**: `GET`
- **描述**: 扫描后端`data/graphs/`目录，解析所有`.json`文件，并返回一个包含每个法规ID和名称的列表。
- **参数**: 无
- **成功响应 (Code 200)**:

  ```json
  {
    "regulations": [
      {
        "id": "regulation_04",
        "name": "北京证券交易所上市公司持续监管指引第4号——股份回购"
      },
      {
        "id": "regulation_08",
        "name": "北京证券交易所上市公司持续监管指引第8号——股份减持和持股管理"
      }
    ]
  }
  ```
- **错误响应**:
  - `404 Not Found`: 如果服务器上`data/graphs/`目录不存在。
  - `500 Internal Server Error`: 如果在扫描或解析文件时发生未知错误。

## 2. 执行合规检查

这是系统的核心功能端点。它接收一个包含法规、公司和日期范围的请求，运行合规检查引擎，并返回详细的检查结果和用于可视化的图谱数据。

- **URL**: `/api/check`
- **Method**: `POST`
- **描述**: 接收合规检查请求，调用`ExecutionEngine`执行检查，并返回结果。
- **请求体 (Request Body)**:
  - **Content-Type**: `application/json`

  ```json
  {
    "regulation_id": "regulation_04",
    "company_name": "祎煜环保",
    "start_date": "2023-01-01",
    "end_date": "2023-12-31"
  }
  ```
  - `regulation_id` (string, **required**): 法规的唯一标识符。
  - `company_name` (string, **required**): 要检查的公司的名称。
  - `start_date` (string, *optional*): 检查的时间范围开始日期，格式为 `YYYY-MM-DD`。
  - `end_date` (string, *optional*): 检查的时间范围结束日期，格式为 `YYYY-MM-DD`。

- **成功响应 (Code 200)**:

  响应体是一个JSON对象，包含两个主要部分：`results` 和 `graph`。

  - `results`: 一个对象，其中包含执行跟踪、违规详情和执行摘要。
  - `graph`: 一个符合ECharts格式的对象，用于在前端渲染知识图谱。

  ```json
  {
    "results": {
      "execution_trace": [
        "...",
        "..."
      ],
      "violations": [
        {
          "rule_id": "R4.5.2",
          "details": "在回购期间，公司于2023-05-15发布了业绩预告，违反了R4.5.2规则。",
          "timestamp": "2023-05-15"
        }
      ],
      "summary": {
        "total_rules_checked": 15,
        "violations_found": 1,
        "execution_duration": "0.12s"
      }
    },
    "graph": {
      "nodes": [
        {"id": "CU1", "name": "回购预案", "category": 0},
        {"id": "R4.5.2", "name": "敏感期限制", "category": 1, "value": "违规"}
      ],
      "links": [
        {"source": "CU1", "target": "R4.5.2"}
      ],
      "categories": [
        {"name": "合规单元"},
        {"name": "规则"}
      ]
    }
  }
  ```

- **错误响应**:
  - `404 Not Found`: 如果请求的公司在指定法规下没有找到数据。
  - `500 Internal Server Error`: 如果在执行检查过程中发生未捕获的内部错误。
  - `422 Unprocessable Entity`: 如果请求体不符合预期的格式（例如，缺少必填字段）。 