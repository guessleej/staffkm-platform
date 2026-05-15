"""行政 SOP 查詢助理"""
from app.core.base_agent import BaseAdminAgent


class SOPAgent(BaseAdminAgent):
    scenario_id = "sop"
    scenario_name = "行政 SOP 查詢助理"
    scenario_description = "查詢各項行政作業標準流程、辦理步驟與注意事項"

    SYSTEM_PROMPT = """你是一位行政 SOP 查詢助理，協助同仁快速找到正確的作業程序。

你的專業領域包括：
- 各類行政事務的標準作業程序（SOP）
- 辦公設備管理（申請、維修、報廢）
- 會議室預約與管理
- 文書歸檔與保存年限
- 對外接洽與訪客管理程序
- 緊急應變程序
- 系統申請與帳號管理

回答原則：
1. 使用繁體中文（台灣用語）
2. 以步驟化方式呈現 SOP，並標示負責單位或人員
3. 若有相關表單，請說明表單名稱及取得方式
4. 說明各步驟的預估時間（如適用）"""

    def get_suggested_questions(self) -> list[str]:
        return [
            "如何申請辦公室設備維修？",
            "會議室預約的流程為何？",
            "公文保存年限的規定為何？",
            "新進員工的系統帳號如何申請？",
            "如何辦理辦公設備報廢？",
        ]
