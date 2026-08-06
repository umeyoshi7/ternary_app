"""timetable_agent のユニットテスト（モックLLM → スキーマ → applier）

実行: .venv/Scripts/python tests/test_timetable_agent.py
Azure OpenAI キー不要（モックモードで検証する）。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from timetable_agent.agent import run_agent
from timetable_agent.applier import apply_proposals
from timetable_agent.client import MockLLMClient, get_client
from timetable_agent.schemas import AgentReply, FilterParams, HeatParams, StepProposal

# ─ テスト用ダミーデータ ─
EQUIPMENT = [
    {"tag_no": "R-101", "type": "反応槽", "display": "R-101 (100L 反応槽)"},
    {"tag_no": "R-102", "type": "反応槽", "display": "R-102 (200L 反応槽)"},
    {"tag_no": "F-201", "type": "フィルター", "display": "F-201 (1.5m² 加圧ろ過)"},
]

STEPS = [
    {"step_no": 1, "name": "原料仕込み", "op_type": "CHARGE", "prev_steps": [],
     "current": {"equipment_display": "（未選択）", "time_method": "手動", "duration_min": 0.0}},
    {"step_no": 2, "name": "80℃まで昇温", "op_type": "HEAT", "prev_steps": [1],
     "current": {"equipment_display": "（未選択）", "time_method": "計算", "duration_min": 0.0}},
    {"step_no": 3, "name": "反応", "op_type": "REACTION", "prev_steps": [2],
     "current": {"equipment_display": "（未選択）", "time_method": "手動", "duration_min": 0.0}},
    {"step_no": 4, "name": "30℃に冷却", "op_type": "COOL", "prev_steps": [3],
     "current": {"equipment_display": "（未選択）", "time_method": "計算", "duration_min": 0.0}},
    {"step_no": 5, "name": "ろ過", "op_type": "FILTER", "prev_steps": [4],
     "current": {"equipment_display": "（未選択）", "time_method": "計算", "duration_min": 0.0}},
]

ROWS = [
    {"step_no": s["step_no"], "name": s["name"], "prev_steps": s["prev_steps"],
     "op_type": s["op_type"], "time_method": s["current"]["time_method"]}
    for s in STEPS
]


def test_mock_client_selected_without_key():
    """キー未設定時はモッククライアントが選択される。"""
    import os
    for k in ("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_DEPLOYMENT"):
        os.environ.pop(k, None)
    client = get_client()
    assert isinstance(client, MockLLMClient), f"expected mock, got {type(client)}"


def test_agent_autofill():
    """モックで全工程補完: 温度抽出・温度引き継ぎ・機器/時間の提案を確認。"""
    reply = run_agent(STEPS, EQUIPMENT)
    assert isinstance(reply, AgentReply)
    assert len(reply.proposals) == 5
    by_no = {p.step_no: p for p in reply.proposals}

    # CHARGE: 手動 + 目安時間 + 反応槽
    assert by_no[1].time_method == "手動"
    assert by_no[1].duration_min == 30.0
    assert by_no[1].equipment_tag == "R-101"

    # HEAT: 計算 + 操作名から目標温度80℃を抽出、初期温度は室温20℃
    assert by_no[2].time_method == "計算"
    assert by_no[2].heat.target_temp_C == 80.0
    assert by_no[2].heat.initial_temp_C == 20.0
    assert by_no[2].heat.dT_offset_K > 0

    # COOL: 目標30℃、初期温度は前のHEATの80℃を引き継ぎ、オフセット負
    assert by_no[4].heat.target_temp_C == 30.0
    assert by_no[4].heat.initial_temp_C == 80.0
    assert by_no[4].heat.dT_offset_K < 0

    # FILTER: フィルター機器 + ろ過パラメータ
    assert by_no[5].equipment_tag == "F-201"
    assert by_no[5].filter.pressure_MPa == 0.2


def test_apply_proposals():
    """提案が正しい session_state キーに書き込まれる。"""
    reply = run_agent(STEPS, EQUIPMENT)
    state: dict = {}
    applied, warnings = apply_proposals(reply.proposals, ROWS, EQUIPMENT, state)

    assert applied > 0
    assert warnings == [], f"unexpected warnings: {warnings}"
    assert state["eq_1"] == "R-101 (100L 反応槽)"   # display 文字列で保持
    assert state["dur_1"] == 30.0
    assert state["edit_method_2"] == "計算"
    assert state["ht_tt_2"] == 80.0
    assert state["ht_t0_4"] == 80.0
    assert state["ht_dto_4"] == -20.0
    assert state["eq_5"] == "F-201 (1.5m² 加圧ろ過)"
    assert state["fi_dP_5"] == 0.2


def test_apply_validation():
    """不正な提案は書き込まれず警告になる（既存値が守られる）。"""
    bad = [
        StepProposal(step_no=99, duration_min=10.0),                      # 存在しない操作
        StepProposal(step_no=1, equipment_tag="R-999"),                   # DBにないTag
        StepProposal(step_no=5, equipment_tag="R-101"),                   # FILTERに反応槽
        StepProposal(step_no=1, duration_min=-5.0),                       # 負の時間
        StepProposal(step_no=2, heat=HeatParams(liquid_volume_L=0.01)),   # 下限未満
        StepProposal(step_no=5, filter=FilterParams(cake_resistance_m_per_kg=-1.0)),  # 負値
    ]
    state: dict = {}
    applied, warnings = apply_proposals(bad, ROWS, EQUIPMENT, state)
    assert applied == 0, f"applied={applied}, state={state}"
    assert state == {}
    assert len(warnings) == 6, f"warnings: {warnings}"


def test_chat_instruction():
    """チャット指示（モック対応形式）で差分提案が返り、適用される。"""
    reply = run_agent(STEPS, EQUIPMENT, instruction="操作3 を 45分 にして")
    assert len(reply.proposals) == 1
    p = reply.proposals[0]
    assert p.step_no == 3 and p.duration_min == 45.0

    state: dict = {"dur_3": 180.0}
    apply_proposals(reply.proposals, ROWS, EQUIPMENT, state)
    assert state["dur_3"] == 45.0


def test_chat_unknown_instruction():
    """モックが解釈できない指示は提案ゼロ + 案内メッセージ（クラッシュしない）。"""
    reply = run_agent(STEPS, EQUIPMENT, instruction="いい感じにして")
    assert reply.proposals == []
    assert "解釈できません" in reply.message


def test_schema_roundtrip():
    """AgentReply が JSON との相互変換に耐える（Azure Structured Outputs の前提確認）。"""
    reply = run_agent(STEPS, EQUIPMENT)
    dumped = reply.model_dump_json()
    restored = AgentReply.model_validate_json(dumped)
    assert restored == reply


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in tests:
        fn()
        print(f"PASS: {fn.__name__}")
    print(f"\n{len(tests)} tests passed.")
