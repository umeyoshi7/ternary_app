import streamlit as st

from ui_lle import render_lle_tab
from ui_vp import render_vp_tab
from ui_vle import render_vle_tab
from ui_conc import render_conc_tab
from ui_logic import render_logic_tab

st.set_page_config(page_title="LLE/VLE calculator", layout="wide")
st.title("LLE/VLE calculator")

tab_lle, tab_vp, tab_vle, tab_conc, tab_logic = st.tabs([
    "LLE線図", "蒸気圧曲線", "VLE線図", "濃縮シミュレーション", "ロジック"
])

render_lle_tab(tab_lle)
render_vp_tab(tab_vp)
render_vle_tab(tab_vle)
render_conc_tab(tab_conc)
render_logic_tab(tab_logic)
