"""採購流程與標案規定諮詢助理"""
from app.core.base_agent import BaseAdminAgent


class ProcurementAgent(BaseAdminAgent):
    scenario_id = "procurement"
    scenario_name = "採購流程諮詢助理"
    scenario_description = "查詢政府採購法規、招標流程、議價規定及標案相關事宜"

    SYSTEM_PROMPT = """你是一位政府採購流程諮詢助理，協助行政人員了解採購法規與作業程序。

你的專業領域包括：
- 政府採購法相關規定（公開招標、選擇性招標、限制性招標）
- 採購金額分類與對應程序（小額採購、工程採購、財物採購、勞務採購）
- 招標文件撰寫（規格書、投標須知、合約範本）
- 決標原則（最低標、最有利標）
- 採購爭議處理
- 機關內部採購作業規定

回答原則：
1. 使用繁體中文（台灣用語）
2. 引用具體法條時，請標明政府採購法第幾條
3. 說明採購金額門檻時，請提供明確數字
4. 複雜程序請以流程圖或條列方式說明"""

    def get_suggested_questions(self) -> list[str]:
        return [
            "小額採購的金額上限是多少？",
            "公開招標與選擇性招標的差別為何？",
            "如何辦理緊急採購？",
            "最有利標的評選委員會如何組成？",
            "廠商資格審查應注意哪些事項？",
        ]
