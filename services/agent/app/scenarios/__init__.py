"""行政 AI 代理人場景模組"""
from .official_doc import OfficialDocAgent
from .hr_leave import HRLeaveAgent
from .procurement import ProcurementAgent
from .budget import BudgetAgent
from .sop import SOPAgent
from .onboarding import OnboardingAgent

SCENARIO_REGISTRY: dict[str, type] = {
    "official_doc": OfficialDocAgent,
    "hr_leave": HRLeaveAgent,
    "procurement": ProcurementAgent,
    "budget": BudgetAgent,
    "sop": SOPAgent,
    "onboarding": OnboardingAgent,
}

__all__ = [
    "OfficialDocAgent", "HRLeaveAgent", "ProcurementAgent",
    "BudgetAgent", "SOPAgent", "OnboardingAgent", "SCENARIO_REGISTRY",
]
