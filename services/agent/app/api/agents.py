"""代理人管理 API — 列出所有場景、取得建議問題"""
from fastapi import APIRouter
from pydantic import BaseModel

from app.scenarios import SCENARIO_REGISTRY
from core.schemas.response import ApiResponse

router = APIRouter()


class ScenarioInfo(BaseModel):
    scenario_id: str
    name: str
    description: str
    suggested_questions: list[str]


@router.get("", response_model=ApiResponse[list[ScenarioInfo]], summary="列出所有代理人場景")
async def list_agents():
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
async def get_agent(scenario_id: str):
    from fastapi import HTTPException
    if scenario_id not in SCENARIO_REGISTRY:
        raise HTTPException(status_code=404, detail=f"代理人場景 '{scenario_id}' 不存在")
    agent = SCENARIO_REGISTRY[scenario_id]()
    return ApiResponse(data=ScenarioInfo(
        scenario_id=scenario_id,
        name=agent.scenario_name,
        description=agent.scenario_description,
        suggested_questions=agent.get_suggested_questions(),
    ))
