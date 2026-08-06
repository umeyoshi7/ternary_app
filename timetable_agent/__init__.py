"""タイムテーブル AI パラメータ補完エージェント

既存の timetable パイプラインは一切変更せず、
アップロード済みフローのパラメータ（機器 Tag No.・所要時間・計算パラメータ）を
LLM で推定し、既存編集 UI の session_state に書き込むことで補完する。

構成:
    config.py  : Azure OpenAI 接続設定（.env / 環境変数）
    schemas.py : LLM 出力の Pydantic スキーマ
    client.py  : LLM クライアント（Azure OpenAI / モック自動切替）
    agent.py   : プロンプト組立 → LLM 呼び出し → AgentReply 返却
    applier.py : 提案の検証と session_state への適用
"""
