import streamlit as st
import plotly.graph_objects as go

from engine import calc_vapor_pressure_curve
from solvents import ALL_SOLVENTS, get_solvent_by_name


def render_vp_tab(tab):
    with tab:
        st.header("蒸気圧曲線")
        col_vp1, col_vp2 = st.columns([1, 3])
        with col_vp1:
            vp_name = st.selectbox("成分", [s["name"] for s in ALL_SOLVENTS], key="vp_name")
            vp_T_range = st.slider("温度範囲 (°C)", -50, 250, (0, 150), key="vp_T_range")
            vp_sol = get_solvent_by_name(vp_name, ALL_SOLVENTS)
            vp_tid = vp_sol.get("thermo_surrogate", vp_sol["thermo_id"])

        with st.spinner("計算中..."):
            try:
                vp_data = calc_vapor_pressure_curve(vp_tid, vp_T_range[0], vp_T_range[1])
            except Exception as e:
                vp_data = None
                with col_vp2:
                    st.error(f"計算エラー: {e}")

        if vp_data:
            with col_vp2:
                if vp_data["T_bp_C"] is not None:
                    st.info(f"沸点 = **{vp_data['T_bp_C']:.1f} °C** @ 101.325 kPa")
                else:
                    st.warning("沸点が指定温度範囲内にありません")
                fig_vp = go.Figure()
                fig_vp.add_trace(go.Scatter(
                    x=vp_data["T_C"], y=vp_data["P_kPa"],
                    name=vp_name, line=dict(color="royalblue", width=2),
                ))
                fig_vp.add_hline(y=101.325, line_dash="dash", line_color="red",
                                 annotation_text="101.325 kPa",
                                 annotation_position="bottom right")
                if vp_data["T_bp_C"] is not None:
                    fig_vp.add_vline(x=vp_data["T_bp_C"], line_dash="dot",
                                     line_color="orange",
                                     annotation_text=f"{vp_data['T_bp_C']:.1f}°C")
                fig_vp.update_layout(
                    xaxis_title="温度 (°C)", yaxis_title="蒸気圧 (kPa)",
                    title=f"{vp_name} 蒸気圧曲線",
                    height=450, plot_bgcolor="white",
                )
                st.plotly_chart(fig_vp, use_container_width=True)
