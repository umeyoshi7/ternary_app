from thermo import ChemicalConstantsPackage, GibbsExcessLiquid, FlashVLN, CEOSGas, PRMIX
from thermo.unifac import UNIFAC, DOUFSG, DOUFIP2016
import streamlit as st


def density_water(T_C):
    """Kell (1975) polynomial, g/mL, valid 10-100°C"""
    t = T_C
    return (999.842594 + 6.793952e-2*t - 9.095290e-3*t**2
            + 1.001685e-4*t**3 - 1.120083e-6*t**4 + 6.536332e-9*t**5) / 1000.0


def density_solvent(solvent: dict, T_C: float) -> float:
    return solvent["density_a"] + solvent["density_b"] * T_C


@st.cache_resource
def build_flasher(T: float, thermo_id_1: str, thermo_id_2: str,
                  surrogate_1: str = None, surrogate_2: str = None,
                  unifac_override_1: tuple = None, unifac_override_2: tuple = None):
    P = 101325
    ids = ['water',
           surrogate_1 if surrogate_1 else thermo_id_1,
           surrogate_2 if surrogate_2 else thermo_id_2]
    constants, correlations = ChemicalConstantsPackage.from_IDs(ids)
    if unifac_override_1 or unifac_override_2:
        new_groups = list(constants.UNIFAC_Dortmund_groups)
        if unifac_override_1:
            new_groups[1] = dict(unifac_override_1)
        if unifac_override_2:
            new_groups[2] = dict(unifac_override_2)
        constants = constants.with_new_constants(UNIFAC_Dortmund_groups=new_groups)
    GE = UNIFAC.from_subgroups(
        chemgroups=constants.UNIFAC_Dortmund_groups,
        version=1,
        T=T, xs=[1/3]*3,
        interaction_data=DOUFIP2016,
        subgroups=DOUFSG,
    )
    liquid = GibbsExcessLiquid(
        VaporPressures=correlations.VaporPressures,
        VolumeLiquids=correlations.VolumeLiquids,
        HeatCapacityGases=correlations.HeatCapacityGases,
        GibbsExcessModel=GE,
        T=T, P=P, zs=[1/3]*3,
    )
    eos_kwargs = dict(Tcs=constants.Tcs, Pcs=constants.Pcs, omegas=constants.omegas)
    gas = CEOSGas(PRMIX, eos_kwargs=eos_kwargs,
                  HeatCapacityGases=correlations.HeatCapacityGases,
                  T=T, P=P, zs=[1/3]*3)
    return FlashVLN(constants, correlations,
                    liquids=[liquid, liquid], gas=gas)


def calc_lle_diagram(T_C, solvent1: dict, solvent2: dict, n_grid=25):
    """
    三角図上を格子スキャン → FlashVLN で2液相分離点を検出

    Returns:
        tie_lines: list of (L1_zs, L2_zs)
        binodal_pts: 各液相の組成点リスト
    """
    T = T_C + 273.15
    P = 101325
    flasher = build_flasher(
        T, solvent1["thermo_id"], solvent2["thermo_id"],
        surrogate_1=solvent1.get("thermo_surrogate"),
        surrogate_2=solvent2.get("thermo_surrogate"),
        unifac_override_1=tuple(sorted(solvent1["unifac_groups"].items())) if "unifac_groups" in solvent1 else None,
        unifac_override_2=tuple(sorted(solvent2["unifac_groups"].items())) if "unifac_groups" in solvent2 else None,
    )

    tie_lines = []
    binodal_pts = []
    seen = set()

    for i in range(n_grid + 1):
        for j in range(n_grid + 1 - i):
            k = n_grid - i - j
            if k < 0:
                continue
            z = [i / n_grid, j / n_grid, k / n_grid]
            try:
                res = flasher.flash(T=T, P=P, zs=z)
                if res.phase_count == 2 and res.liquid_count == 2:
                    L1 = tuple(round(x, 6) for x in res.liquids[0].zs)
                    L2 = tuple(round(x, 6) for x in res.liquids[1].zs)
                    key = (min(L1, L2), max(L1, L2))
                    if key not in seen:
                        seen.add(key)
                        tie_lines.append((list(L1), list(L2)))
                        binodal_pts.append(list(L1))
                        binodal_pts.append(list(L2))
            except Exception:
                continue

    return tie_lines, binodal_pts


def calc_layer_composition(T_C, amounts, unit, solvent1: dict, solvent2: dict):
    """
    Parameters
    ----------
    amounts : [water, solvent1, solvent2] in unit
    unit    : 'g' | 'mol' | 'mL'

    Returns
    -------
    dict with keys: phase_count, water_layer, organic_layer, input_zs,
                    beta_water, beta_organic, error
    """
    MW = [18.015, solvent1["mw"], solvent2["mw"]]
    rho = [density_water(T_C), density_solvent(solvent1, T_C), density_solvent(solvent2, T_C)]

    # 単位変換 → グラム
    if unit == 'g':
        grams = list(amounts)
    elif unit == 'mol':
        grams = [a * mw for a, mw in zip(amounts, MW)]
    else:  # mL
        grams = [a * r for a, r in zip(amounts, rho)]

    total_grams = sum(grams)
    if total_grams == 0:
        return {'error': '投入量がすべてゼロです', 'phase_count': 0,
                'input_zs': None, 'water_layer': None, 'organic_layer': None,
                'beta_water': None, 'beta_organic': None}

    moles = [g / mw for g, mw in zip(grams, MW)]
    total_moles = sum(moles)
    z = [m / total_moles for m in moles]

    T = T_C + 273.15
    P = 101325
    try:
        flasher = build_flasher(
            T, solvent1["thermo_id"], solvent2["thermo_id"],
            surrogate_1=solvent1.get("thermo_surrogate"),
            surrogate_2=solvent2.get("thermo_surrogate"),
            unifac_override_1=tuple(sorted(solvent1["unifac_groups"].items())) if "unifac_groups" in solvent1 else None,
            unifac_override_2=tuple(sorted(solvent2["unifac_groups"].items())) if "unifac_groups" in solvent2 else None,
        )
        res = flasher.flash(T=T, P=P, zs=z)
    except Exception as e:
        return {'error': str(e), 'phase_count': 0,
                'input_zs': z, 'water_layer': None, 'organic_layer': None,
                'beta_water': None, 'beta_organic': None}

    if not (res.phase_count == 2 and res.liquid_count == 2):
        return {'phase_count': 1, 'input_zs': z, 'error': None,
                'water_layer': None, 'organic_layer': None,
                'beta_water': None, 'beta_organic': None}

    # 水層 = Water mole fraction が高い方
    if res.liquids[0].zs[0] >= res.liquids[1].zs[0]:
        wl_idx, ol_idx = 0, 1
    else:
        wl_idx, ol_idx = 1, 0

    def phase_metrics(xs, beta):
        phase_moles_i = [xs[i] * beta * total_moles for i in range(3)]
        phase_grams_i = [phase_moles_i[i] * MW[i] for i in range(3)]
        total_pg = sum(phase_grams_i)
        return {
            'zs': list(xs),
            'mol_pct': [x * 100 for x in xs],
            'ww_pct': [g / total_pg * 100 for g in phase_grams_i],
            'vw_pct': [(phase_grams_i[i] / rho[i]) / total_pg * 100 for i in range(3)],
            'beta': beta,
        }

    return {
        'phase_count': 2,
        'input_zs': z,
        'water_layer': phase_metrics(res.liquids[wl_idx].zs, res.betas[wl_idx]),
        'organic_layer': phase_metrics(res.liquids[ol_idx].zs, res.betas[ol_idx]),
        'beta_water': res.betas[wl_idx],
        'beta_organic': res.betas[ol_idx],
        'error': None,
    }
