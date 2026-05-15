"""經費報支流程助理"""
from app.core.base_agent import BaseAdminAgent


class BudgetAgent(BaseAdminAgent):
    scenario_id = "budget"
    scenario_name = "經費報支流程助理"
    scenario_description = "協助查詢各類經費報支規定、憑證要求與核銷作業流程"

    SYSTEM_PROMPT = """你是一位經費報支作業助理，協助同仁了解各類費用申請與核銷規定。

你的專業領域包括：
- 差旅費報支（交通費、住宿費、日支費）
- 業務費、材料費、設備費的核銷規定
- 統一發票、收據等憑證的規格要求
- 預算科目的正確選用
- 零用金撥補作業
- 跨年度經費處理
- 機關內部財務規章

回答原則：
1. 使用繁體中文（台灣用語）
2. 說明憑證要求時，請明確列出所需文件清單
3. 引用相關法規（如會計法、審計法、各項費用報支要點）
4. 提醒常見的核銷錯誤以供注意"""

    def get_suggested_questions(self) -> list[str]:
        return [
            "出差的交通費如何報支？需要哪些憑證？",
            "購買辦公用品應使用哪個預算科目？",
            "統一發票的抬頭應該填寫什麼？",
            "差旅費的住宿費上限是多少？",
            "如何申請零用金撥補？",
        ]
