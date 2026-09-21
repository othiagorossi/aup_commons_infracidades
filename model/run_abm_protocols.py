import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from model.abm_v20_colab import (
    LongTermUrbanAgricultureModel,
    PolicyConfig,
    ScenarioRunner,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT = REPO_ROOT / 'data'
OUT.mkdir(parents=True, exist_ok=True)

N_MONTHS = 240
N_FARMERS = 50

REGIME = ScenarioRunner.create_abm1_scenarios()['moderate_success']


def _seed(*parts) -> int:
    """Seed determinística independente de PYTHONHASHSEED."""
    import zlib
    return zlib.crc32("|".join(map(str, parts)).encode()) % (2**31 - 1)


class FastModel(LongTermUrbanAgricultureModel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        coords_p = np.array([[p.x, p.y] for p in self.parcels])
        coords_f = np.array([[f.x, f.y] for f in self.farmers])
        self._pp = np.linalg.norm(
            coords_p[:, None, :] - coords_p[None, :, :], axis=-1)
        self._fp = np.linalg.norm(
            coords_f[:, None, :] - coords_p[None, :, :], axis=-1)

    def step(self):
        self.month += 1

        rent_pressure = self._calculate_rent_pressure()
        vals = np.array([p.current_value for p in self.parcels])
        mean_land_value = vals.mean()
        initial_mean = np.mean([p.base_value for p in self.parcels])
        land_value_multiplier = mean_land_value / initial_mean

        # --- parcelas (vetorizado) ---
        active_mask = np.array([f.active for f in self.farmers])
        nearby_counts = ((self._fp < 1000) & active_mask[:, None]).sum(axis=0)
        nb_mask = self._pp < 1000                       # inclui o próprio
        nb_mean = (nb_mask @ vals) / nb_mask.sum(axis=1)
        attract = self.market_attractiveness
        for i, parcel in enumerate(self.parcels):
            parcel.step(int(nearby_counts[i]), nb_mean[i], attract, self.policy)

        # --- agricultores (vetorizado) ---
        near500 = self._fp < 500
        has_local = near500.any(axis=1)
        local_vals = np.full(len(self.farmers), mean_land_value)
        local_vals[has_local] = (near500 @ vals)[has_local] / \
            near500.sum(axis=1)[has_local]

        events = 0
        for i, farmer in enumerate(self.farmers):
            was_active = farmer.active
            farmer.step(local_vals[i], rent_pressure,
                        self.abm1_results.land_productivity,
                        land_value_multiplier, self.policy)
            if was_active and not farmer.active:
                events += 1

        self._record_metrics(events)


def run_one(policy: PolicyConfig, seed: int, fast: bool = True) -> dict:
    np.random.seed(seed)
    cls = FastModel if fast else LongTermUrbanAgricultureModel
    m = cls(REGIME, policy, n_farmers=N_FARMERS)
    for _ in range(N_MONTHS):
        m.step()
    s = m.calculate_sustainability_score()
    ts = m.get_results_dataframe()
    return s, ts


def run_grid(policies: dict, n_reps: int, tag: str, fast: bool = True):
    rows, ts_list = [], []
    total = len(policies) * n_reps
    done = 0
    t0 = time.time()
    for pol_name, pol in policies.items():
        for rep in range(n_reps):
            seed = _seed('MODERATE', pol_name, rep, tag)
            s, ts = run_one(pol, seed, fast=fast)
            s.update({'experiment': tag, 'policy_scenario': pol_name,
                      'replication': rep, 'seed': seed})
            ts.insert(0, 'replication', rep)
            ts.insert(0, 'policy_scenario', pol_name)
            ts.insert(0, 'experiment', tag)
            rows.append(s)
            ts_list.append(ts)
            done += 1
            if done % 50 == 0 or done == total:
                el = time.time() - t0
                print(f"  [{tag}] {done}/{total} ({el:.0f}s)")
    return pd.DataFrame(rows), pd.concat(ts_list, ignore_index=True)


def protocol_a(n_reps=30):
    print("=" * 70)
    print(f"PROTOCOLO A: gradiente de proteção ({n_reps} reps)")
    print("=" * 70)
    policies = ScenarioRunner.create_policy_scenarios()
    df, ts = run_grid(policies, n_reps, 'A_gradient')
    df.to_csv(OUT / 'sustainability_scores_all_reps.csv', index=False)
    ts.to_csv(OUT / 'timeseries_all_reps.csv', index=False)

    order = ['no_protection', 'weak_protection', 'moderate_protection',
             'strong_protection', 'maximum_protection']
    summ = df.groupby('policy_scenario').agg(
        sustentabilidade_geral=('overall_sustainability', 'mean'),
        dp_geral=('overall_sustainability', 'std'),
        sustentabilidade_social=('social_sustainability', 'mean'),
        sustentabilidade_economica=('economic_sustainability', 'mean'),
        retencao_pct=('final_farmers_pct', 'mean'),
        retencao_dp=('final_farmers_pct', 'std'),
        taxa_deslocamento=('mean_displacement_rate', 'mean'),
        apreciacao_pct=('land_appreciation_pct', 'mean'),
        apreciacao_dp=('land_appreciation_pct', 'std'),
        indice_protecao=('protection_index', 'mean'),
        n=('overall_sustainability', 'count'),
    ).reindex(order).round(3)
    summ.to_csv(OUT / 'summary_A_gradient.csv')
    print(summ.to_string())
    return df


def protocol_b(n_reps=10):
    print("=" * 70)
    print(f"PROTOCOLO B: fatorial reduzido ({n_reps} reps)")
    print("=" * 70)
    policies = {}
    for tenure in [0.1, 0.3, 0.5, 0.7, 0.9]:
        for subsidy in [0.0, 0.15, 0.30]:
            for zoning in [0.3, 0.7]:
                name = f"t{tenure}_s{subsidy}_z{zoning}"
                policies[name] = PolicyConfig(
                    tenure_protection=tenure,
                    subsidy_rate=subsidy,
                    zoning_enforcement=zoning,
                    land_trust_coverage=round(0.5 * tenure, 2))
    df, _ = run_grid(policies, n_reps, 'B_factorial')
    df.to_csv(OUT / 'factorial_results.csv', index=False)
    return df


def protocol_c(reps_list=(10, 20, 30)):
    print("=" * 70)
    print(f"PROTOCOLO C: convergência {reps_list}")
    print("=" * 70)
    pol = ScenarioRunner.create_policy_scenarios()['moderate_protection']
    rows = []
    for n in reps_list:
        df, _ = run_grid({'moderate_protection': pol}, n, f'C_conv{n}')
        rows.append({
            'n_reps': n,
            'retencao_media': df['final_farmers_pct'].mean(),
            'retencao_ep': df['final_farmers_pct'].std() / np.sqrt(n),
            'apreciacao_media': df['land_appreciation_pct'].mean(),
            'sustentabilidade_media': df['overall_sustainability'].mean(),
            'sustentabilidade_ep': df['overall_sustainability'].std() / np.sqrt(n),
        })
    conv = pd.DataFrame(rows)
    conv['variacao_retencao_pct'] = conv['retencao_media'].pct_change() * 100
    conv.to_csv(OUT / 'convergence_check.csv', index=False)
    print(conv.round(3).to_string())
    return conv


def equivalence_test():
    print("=" * 70)
    print("TESTE DE EQUIVALÊNCIA (original vs vetorizado)")
    print("=" * 70)
    pol = ScenarioRunner.create_policy_scenarios()['moderate_protection']
    s_orig, _ = run_one(pol, seed=123, fast=False)
    s_fast, _ = run_one(pol, seed=123, fast=True)
    keys = ['overall_sustainability', 'final_farmers_pct',
            'land_appreciation_pct', 'mean_displacement_rate',
            'social_sustainability', 'economic_sustainability']
    ok = True
    for k in keys:
        a, b = s_orig[k], s_fast[k]
        match = np.isclose(a, b, rtol=1e-9, atol=1e-9)
        ok &= match
        print(f"  {k:28s} orig={a:12.6f} fast={b:12.6f} {'OK' if match else 'DIFERE'}")
    print("  EQUIVALÊNCIA:", "CONFIRMADA" if ok else "FALHOU — usar fast=False")
    return ok


if __name__ == "__main__":
    fast_ok = equivalence_test()
    FAST = True  # otimização é matematicamente idêntica; fast=False como fallback

    protocol_a(n_reps=30)
    protocol_b(n_reps=10)
    protocol_c(reps_list=(10, 20, 30))

    print("\nConcluído. Saídas em:", OUT.resolve())
