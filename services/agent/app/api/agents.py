"""代理人管理 API — 列出所有場景、取得建議問題（workspace-scoped 唯讀）。

NOTE: 場景目錄目前是 hard-coded 在 SCENARIO_REGISTRY，所有 workspace 共用同一份。
未來若要支援 workspace 自訂場景，再把場景定義落地到 DB 並加 workspace_id 過濾。
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.scenarios import SCENARIO_REGISTRY
from staffkm_core.schemas.response import ApiResponse
from staffkm_tenant import TenantContext, require_member

router = APIRouter()


class ScenarioInfo(BaseModel):
    scenario_id: str
    name: str
    description: str
    suggested_questions: list[str]


@router.get("", response_model=ApiResponse[list[ScenarioInfo]], summary="列出所有代理人場景")
async def list_agents(_: TenantContext = Depends(require_member)):
    result = []
    for scenario_id, agent_cls in SCENARIO_REGISTRY.items():
        agent = agent_cls()
        result.append(ScenarioInfo(
            scenario_id=scenario_id,
            name=agent.scenario_name,
            description=agent.scenario_description,
            suggested_questions=agent.get_suggested_questions(),
        ))
    return ApiResponse(data=result)


@router.get("/{scenario_id}", response_model=ApiResponse[ScenarioInfo], summary="取得特定代理人資訊")
async def get_agent(scenario_id: str, _: TenantContext = Depends(require_member)):
    if scenario_id not in SCENARIO_REGISTRY:
        raise HTTPException(status_code=404, detail=f"代理人場景 '{scenario_id}' 不存在")
    agent = SCENARIO_REGISTRY[scenario_id]()
    return ApiResponse(data=ScenarioInfo(
        scenario_id=scenario_id,
        name=agent.scenario_name,
        description=agent.scenario_description,
        suggested_questions=agent.get_suggested_questions(),
    ))
