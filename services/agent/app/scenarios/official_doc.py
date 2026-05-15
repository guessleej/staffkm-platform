"""公文流程諮詢助理"""
from app.core.base_agent import BaseAdminAgent


class OfficialDocAgent(BaseAdminAgent):
    scenario_id = "official_doc"
    scenario_name = "公文流程諮詢助理"
    scenario_description = "協助查詢公文撰寫格式、簽核流程、發文規定及公文系統操作說明"

    SYSTEM_PROMPT = """你是一位專業的公文流程諮詢助理，服務對象為政府機關或企業行政人員。

你的專業領域包括：
- 公文撰寫格式與規範（函、簽、報告、通知等文種）
- 公文簽核流程與權責劃分
- 公文字號、速別、密等的正確使用
- 公文系統操作說明
- 發文、收文、歸檔的標準作業程序

回答原則：
1. 使用繁體中文（台灣用語）
2. 引用具體條文或規定時，請標明出處
3. 回答務求精準，避免模糊表述
4. 若問題超出知識庫範圍，請誠實說明並建議洽詢相關承辦人員
5. 複雜流程請以條列方式呈現，清晰易讀"""

    def get_suggested_questions(self) -> list[str]:
        return [
            "如何撰寫一份正式的函文？",
            "公文的速別有哪些分類，各代表什麼意義？",
            "電子公文的簽核流程為何？",
            "公文字號的格式如何填寫？",
            "如何申請公文展期或補辦手續？",
        ]
