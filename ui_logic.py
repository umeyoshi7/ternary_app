import streamlit as st


def render_logic_tab(tab):
    with tab:
        st.header("計算ロジック・数式説明")

        with st.expander("1. UNIFAC Dortmund モデル（活量係数）", expanded=True):
            st.markdown(r"""
**活量係数の分解：**

$$
\ln \gamma_i = \ln \gamma_i^C + \ln \gamma_i^R
$$

**組み合わせ項（Combinatorial term）：**

$$
\ln \gamma_i^C = 1 - V_i' + \ln V_i' - 5q_i \left(1 - \frac{V_i}{F_i} + \ln \frac{V_i}{F_i}\right)
$$

$$
V_i' = \frac{r_i^{3/4}}{\sum_j x_j r_j^{3/4}}, \quad V_i = \frac{r_i}{\sum_j x_j r_j}, \quad F_i = \frac{q_i}{\sum_j x_j q_j}
$$

ここで $r_i$ はvan der Waals体積パラメータ, $q_i$ は表面積パラメータ。

**残差項（Residual term）：**

$$
\ln \gamma_i^R = \sum_k \nu_k^{(i)} \left(\ln \Gamma_k - \ln \Gamma_k^{(i)}\right)
$$

$$
\ln \Gamma_k = Q_k \left[1 - \ln\left(\sum_m \Theta_m \Psi_{mk}\right) - \sum_m \frac{\Theta_m \Psi_{km}}{\sum_n \Theta_n \Psi_{nm}}\right]
$$

**温度依存相互作用パラメータ（Dortmund修正）：**

$$
\Psi_{mn} = \exp\left(-\frac{a_{mn} + b_{mn}T + c_{mn}T^2}{T}\right)
$$
""")

        with st.expander("2. 液液平衡（LLE）条件"):
            st.markdown(r"""
**等フガシティー条件：**

$$
f_i^{L1} = f_i^{L2} \quad (i = 1, 2, \ldots, N)
$$

液相では $f_i^L = x_i \gamma_i P_i^{sat}$ なので：

$$
x_i^{L1} \gamma_i^{L1} = x_i^{L2} \gamma_i^{L2}
$$

**物質収支：**

$$
z_i = \beta^{L1} x_i^{L1} + \beta^{L2} x_i^{L2}, \quad \beta^{L1} + \beta^{L2} = 1
$$

**Rachford-Rice方程式（2液相）：**

$$
\sum_i \frac{z_i (K_i - 1)}{1 + \beta (K_i - 1)} = 0, \quad K_i = \frac{x_i^{L2}}{x_i^{L1}}
$$
""")

        with st.expander("3. フラッシュアルゴリズム"):
            st.markdown(r"""
**ステップ 1 — 安定性テスト（Tangent Plane Distance, TPD）：**

$$
\text{TPD}(\mathbf{y}) = \sum_i y_i \left[\ln y_i + \ln \gamma_i(\mathbf{y}) - \ln z_i - \ln \gamma_i(\mathbf{z})\right]
$$

$\text{TPD} < 0$ となる試験組成 $\mathbf{y}$ が存在する場合、相分離が起こる。

**ステップ 2 — 逐次代入法（Successive Substitution）：**

1. 初期 $K_i$ を推定（Wilson式など）
2. Rachford-Rice方程式を解いて $\beta$, $x_i^{L1}$, $x_i^{L2}$ を計算
3. 活量係数 $\gamma_i^{L1}$, $\gamma_i^{L2}$ を更新
4. $K_i \leftarrow \gamma_i^{L1} / \gamma_i^{L2}$
5. 収束まで繰り返す（$|\Delta K_i| < \varepsilon$）

本アプリでは **thermo ライブラリ**（`FlashVLN`）が上記を自動実行します。
""")

        with st.expander("4. 密度・単位変換"):
            st.markdown(r"""
**水の密度 — Kell (1975) 多項式（g/mL）：**

$$
\rho_{\text{water}}(T) = \frac{999.842594 + 6.793952\times10^{-2}T - 9.095290\times10^{-3}T^2 + \cdots}{1000}
$$

（$T$ は摂氏、有効範囲：10〜100 °C）

**有機溶媒の密度 — 線形近似（g/mL）：**

$$
\rho_{\text{solvent}}(T) = a + b \cdot T
$$

| パラメータ | 意味 |
|---|---|
| $a$ | 0°C外挿密度 (g/mL) |
| $b$ | 温度係数 (g/mL/°C)、通常負値 |

**単位変換（g / mol / mL → mol）：**

| 入力単位 | 変換式 |
|---|---|
| g | $n_i = m_i / M_i$ |
| mol | $n_i = $ 入力値そのまま |
| mL | $n_i = (V_i \cdot \rho_i) / M_i$ |
""")

        with st.expander("5. scipy の使用箇所"):
            st.markdown(r"""
**Rachford-Rice 方程式の数値解法：**

thermo ライブラリは内部で `scipy.optimize` を使用してRachford-Rice方程式を解いています。

具体的には：
- `scipy.optimize.brentq` または `scipy.optimize.ridder` などのブラケット法
- 解の存在区間 $[\beta_{\min}, \beta_{\max}]$ を解析的に求めた後、数値的に根を求める

**安定性テスト（TPD最小化）：**

`scipy.optimize.minimize` を用いて接平面距離関数を最小化し、相分離の判定を行います。

これらの計算はすべて `FlashVLN.flash()` 呼び出し内で自動的に処理されます。
""")
