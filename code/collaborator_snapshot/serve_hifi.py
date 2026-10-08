"""启动 OpenMDBench V2 仿真服务器（绑定 MD-AD-002-EASY 场景）。

用法：
    python serve_hifi.py --port 8000
远程调用：
    POST /v2/sessions               创建会话（body: {session_id, seed}）
    POST /v2/sessions/{id}/control  控制（body: {operation: "start"}）
    GET  /v2/sessions/{id}/observation?faction_id=...  拿观测
    POST /v2/sessions/{id}/step     推进一步（body: {operation_id, expected_tick}）
    GET  /v2/sessions/{id}/result   拿结果
"""
import argparse

import uvicorn

from openmdbench.api.gateway_v2 import create_gateway_app_v2
from openmdbench.sessions.formal_v2 import create_formal_gateway_v2


# 注意：AgentGatewayV2 绑定单个场景，这里以 MD-AD-002-EASY 为例
SCENARIO_ID = "MD-AD-002-EASY"


def build_app():
    gateway = create_formal_gateway_v2(SCENARIO_ID)
    return create_gateway_app_v2(gateway)


app = build_app()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    uvicorn.run(app, host=args.host, port=args.port)
