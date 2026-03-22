import streamlit as st

from ui_lle import render_lle_tab
from ui_vp import render_vp_tab
from ui_vle import render_vle_tab
from ui_conc import render_conc_tab
from ui_logic import render_logic_tab
from ui_timetable import render as render_timetable
from ui_reaction import render as render_reaction

st.set_page_config(page_title="バッチ製造支援ツール", layout="wide")


def _coming_soon(name: str):
    st.title(name)
    st.info("このページは現在準備中です。")


def _page_timetable():    render_timetable()
def _page_lle():          render_lle_tab()
def _page_vle():          render_vle_tab()
def _page_vp():           render_vp_tab()
def _page_conc():         render_conc_tab()
def _page_reaction():     render_reaction()
def _page_conc_time():    _coming_soon("濃縮時間推算")
def _page_heat():         _coming_soon("伝熱計算")
def _page_filter():       _coming_soon("ろ過時間推算")
def _page_logic():        render_logic_tab()

pg = st.navigation({
    "生産管理": [
        st.Page(_page_timetable, title="タイムテーブル作成"),
    ],
    "化学工学計算": [
        st.Page(_page_lle,       title="LLE線図"),
        st.Page(_page_vle,       title="VLE線図"),
        st.Page(_page_vp,        title="蒸気圧曲線"),
        st.Page(_page_conc,      title="濃縮シミュレーション"),
        st.Page(_page_reaction,  title="反応速度解析"),
        st.Page(_page_conc_time, title="[濃縮時間推算]"),
        st.Page(_page_heat,      title="[伝熱計算]"),
        st.Page(_page_filter,    title="[ろ過時間推算]"),
    ],
    "ロジック説明": [
        st.Page(_page_logic,     title="ロジック説明"),
    ],
})
pg.run()
