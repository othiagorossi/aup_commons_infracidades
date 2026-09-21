# -*- coding: utf-8 -*-
"""
Agent-Based Model: Long-Term Urban Agriculture Dynamics with Real Estate Pressure
==================================================================================
This model simulates second-order effects of successful urban agriculture,
including gentrification, land value dynamics, and farmer displacement.

It integrates outputs from Rossi et al. (2026)(short-term market dynamics) as initial conditions.

Author: Thiago Rossi
Version: 2.0
Date: August 2026
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from dataclasses import dataclass
from typing import List, Dict
from enum import Enum
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

class SuccessRegime(Enum):
    """Success regimes from ABM 1"""
    LOW = "low"           # Market share < 10%
    MODERATE = "moderate" # Market share 10-25%
    HIGH = "high"         # Market share > 25%

@dataclass
class ABM1Results:
    market_share: float
    active_producers: int
    mean_producer_profit: float
    mean_consumer_knowledge: float
    land_productivity: float  # units/m²/week
    food_security_index: float

    @property
    def regime(self) -> SuccessRegime:
        """Classify success regime"""
        if self.market_share < 0.10:
            return SuccessRegime.LOW
        elif self.market_share < 0.25:
            return SuccessRegime.MODERATE
        else:
            return SuccessRegime.HIGH

@dataclass
class PolicyConfig:
    """Policy intervention configuration"""
    tenure_protection: float  # 0-1, proportion of farmers with secure tenure
    subsidy_rate: float       # 0-1, cost reduction for protected farmers
    zoning_enforcement: float # 0-1, strength of agricultural zoning
    land_trust_coverage: float # 0-1, proportion under community land trust

    @property
    def total_protection_index(self) -> float:
        """Composite protection score"""
        return (0.4 * self.tenure_protection +
                0.3 * self.zoning_enforcement +
                0.3 * self.land_trust_coverage)

class UrbanFarmer:
    """Agent representing an urban farmer facing displacement pressure"""

    def __init__(self, farmer_id: int, x: float, y: float,
                 initial_wealth: float, plot_size: float):
        self.id = farmer_id
        self.x = x
        self.y = y
        self.plot_size = plot_size  # m²

        # Economic variables
        self.wealth = initial_wealth
        self.monthly_profit = 0.0
        self.production_value = 0.0

        # Vulnerability and protection
        self.has_tenure_security = False
        self.has_subsidy = False
        self.in_land_trust = False
        self.vulnerability_index = np.random.uniform(0.3, 0.9)

        # State
        self.active = True
        self.months_active = 0
        self.displacement_risk = 0.0

        # History
        self.wealth_history = []
        self.risk_history = []

    def calculate_displacement_risk(self, land_value: float,
                                   rent_pressure: float,
                                   policy: PolicyConfig) -> float:
        """Calculate monthly displacement risk"""
        # Base risk from land value appreciation
        base_risk = min(land_value / 10000, 1.0) * 0.15

        # Rent pressure component
        rent_risk = rent_pressure * 0.10

        # Personal vulnerability
        vulnerability_risk = self.vulnerability_index * 0.08

        # Protection factors
        protection = 0.0
        if self.has_tenure_security:
            protection += 0.60  # Major protection
        if self.in_land_trust:
            protection += 0.30  # Strong protection
        if self.has_subsidy:
            protection += 0.15  # Economic buffer

        # Zoning protection (applies to all)
        protection += policy.zoning_enforcement * 0.25

        # Final risk
        risk = max(0, (base_risk + rent_risk + vulnerability_risk) * (1 - protection))

        return risk

    def update_wealth(self, base_productivity: float, land_value_multiplier: float):
        """Update farmer wealth based on production and costs"""
        # Production revenue (scales with plot size)
        production = base_productivity * self.plot_size * 4.33  # weekly to monthly
        self.production_value = production

        # Land costs (increases with land value)
        if not self.has_tenure_security:
            land_cost = self.plot_size * 0.05 * land_value_multiplier
        else:
            land_cost = self.plot_size * 0.05  # Fixed cost

        # Operating costs
        operating_cost = production * 0.35
        if self.has_subsidy:
            operating_cost *= 0.80  # 20% reduction

        # Net profit
        self.monthly_profit = production - land_cost - operating_cost
        self.wealth += self.monthly_profit

        # Record history
        self.wealth_history.append(self.wealth)

    def check_displacement(self) -> bool:
        """Check if farmer is displaced this month"""
        if not self.active:
            return False

        # Stochastic displacement based on risk
        if np.random.random() < self.displacement_risk:
            self.active = False
            return True

        # Deterministic displacement if wealth depleted
        if self.wealth < -5000:
            self.active = False
            return True

        return False

    def step(self, land_value: float, rent_pressure: float,
             base_productivity: float, land_value_multiplier: float,
             policy: PolicyConfig):
        """Monthly update step"""
        if not self.active:
            return

        self.months_active += 1

        # Calculate displacement risk
        self.displacement_risk = self.calculate_displacement_risk(
            land_value, rent_pressure, policy
        )
        self.risk_history.append(self.displacement_risk)

        # Update economic state
        self.update_wealth(base_productivity, land_value_multiplier)

        # Check for displacement
        self.check_displacement()


class LandParcel:
    """Represents a land parcel that can appreciate in value"""

    def __init__(self, parcel_id: int, x: float, y: float,
                 initial_value: float, size: float):
        self.id = parcel_id
        self.x = x
        self.y = y
        self.size = size  # m²
        self.base_value = initial_value
        self.current_value = initial_value

        # Appreciation factors
        self.green_amenity_bonus = 0.0
        self.neighborhood_effect = 0.0
        self.speculation_pressure = 0.0

        # Protection
        self.has_zoning_protection = False
        self.in_land_trust = False

        # History
        self.value_history = [initial_value]

    def calculate_appreciation(self, nearby_farmers: int,
                              mean_neighborhood_value: float,
                              market_attractiveness: float,
                              policy: PolicyConfig) -> float:
        """Calculate land value appreciation"""
        # Base appreciation (inflation + urban growth)
        base_rate = 0.003  # 0.3% monthly = ~3.6% annual

        # Green amenity effect (more nearby farmers = higher value)
        self.green_amenity_bonus = (nearby_farmers / 20) * 0.008

        # Neighborhood spillover
        if mean_neighborhood_value > self.current_value:
            self.neighborhood_effect = 0.005
        else:
            self.neighborhood_effect = 0.0

        # Market attractiveness (from ABM 1 success)
        self.speculation_pressure = market_attractiveness * 0.010

        # Protection dampening
        if self.has_zoning_protection:
            protection_factor = 1 - (policy.zoning_enforcement * 0.60)
        elif self.in_land_trust:
            protection_factor = 0.10  # Strong dampening
        else:
            protection_factor = 1.0

        # Total appreciation rate
        total_rate = (base_rate +
                     self.green_amenity_bonus +
                     self.neighborhood_effect +
                     self.speculation_pressure) * protection_factor

        return total_rate

    def step(self, nearby_farmers: int, mean_neighborhood_value: float,
             market_attractiveness: float, policy: PolicyConfig):
        """Monthly land value update"""
        appreciation_rate = self.calculate_appreciation(
            nearby_farmers, mean_neighborhood_value,
            market_attractiveness, policy
        )

        self.current_value *= (1 + appreciation_rate)
        self.value_history.append(self.current_value)

class LongTermUrbanAgricultureModel:
    """ABM 2: Long-term dynamics with gentrification pressure"""

    def __init__(self, abm1_results: ABM1Results, policy: PolicyConfig,
                 n_farmers: int = 50, n_parcels: int = 100,
                 world_size: float = 5000.0):
        """
        Initialize the long-term model.

        Parameters:
        -----------
        abm1_results : Results from ABM 1 (short-term dynamics)
        policy : Policy configuration for protection measures
        n_farmers : Number of initial farmers
        n_parcels : Number of land parcels
        world_size : Size of simulation area (meters)
        """
        self.abm1_results = abm1_results
        self.policy = policy
        self.world_size = world_size

        # Initialize agents
        self.farmers = self._initialize_farmers(n_farmers)
        self.parcels = self._initialize_parcels(n_parcels)

        # Apply policy protections
        self._apply_policy_protections()

        # Global state
        self.month = 0
        self.market_attractiveness = self._calculate_market_attractiveness()

        # Metrics tracking
        self.metrics = {
            'month': [],
            'active_farmers': [],
            'mean_land_value': [],
            'displacement_rate': [],
            'total_production': [],
            'mean_farmer_wealth': [],
            'gini_coefficient': [],
            'displacement_events': [],
            'mean_displacement_risk': [],
            'land_value_volatility': []
        }

    def _initialize_farmers(self, n: int) -> List[UrbanFarmer]:
        """Initialize farmer agents"""
        farmers = []
        for i in range(n):
            x = np.random.uniform(0, self.world_size)
            y = np.random.uniform(0, self.world_size)

            # Initial wealth based on ABM 1 results
            base_wealth = self.abm1_results.mean_producer_profit * 12
            wealth = np.random.normal(base_wealth, base_wealth * 0.3)

            # Plot size distribution
            plot_size = np.random.gamma(shape=2, scale=250)  # ~500 m² mean

            farmer = UrbanFarmer(i, x, y, wealth, plot_size)
            farmers.append(farmer)

        return farmers

    def _initialize_parcels(self, n: int) -> List[LandParcel]:
        """Initialize land parcels"""
        parcels = []

        # Base land value from ABM 1 success
        regime_multipliers = {
            SuccessRegime.LOW: 1.0,
            SuccessRegime.MODERATE: 1.3,
            SuccessRegime.HIGH: 1.8
        }
        base_value = 100 * regime_multipliers[self.abm1_results.regime]

        for i in range(n):
            x = np.random.uniform(0, self.world_size)
            y = np.random.uniform(0, self.world_size)

            value = np.random.normal(base_value, base_value * 0.2)
            size = np.random.uniform(400, 800)

            parcel = LandParcel(i, x, y, value, size)
            parcels.append(parcel)

        return parcels

    def _apply_policy_protections(self):
        """Apply policy protections to farmers and parcels"""
        n_protected = int(len(self.farmers) * self.policy.tenure_protection)
        n_subsidy = int(len(self.farmers) * self.policy.tenure_protection * 0.7)
        n_land_trust = int(len(self.farmers) * self.policy.land_trust_coverage)
        n_zoned = int(len(self.parcels) * self.policy.zoning_enforcement)

        # Prioritize most vulnerable farmers for protection
        farmers_by_vulnerability = sorted(
            self.farmers,
            key=lambda f: f.vulnerability_index,
            reverse=True
        )

        for i, farmer in enumerate(farmers_by_vulnerability):
            if i < n_protected:
                farmer.has_tenure_security = True
            if i < n_subsidy:
                farmer.has_subsidy = True
            if i < n_land_trust:
                farmer.in_land_trust = True

        # Apply zoning protection to parcels
        for i, parcel in enumerate(self.parcels):
            if i < n_zoned:
                parcel.has_zoning_protection = True
            if i < n_land_trust:
                parcel.in_land_trust = True

    def _calculate_market_attractiveness(self) -> float:
        """Calculate market attractiveness from ABM 1 results"""
        # Combination of market share, knowledge, and food security
        attractiveness = (
            0.4 * self.abm1_results.market_share * 4 +  # Scale to 0-1.6
            0.3 * self.abm1_results.mean_consumer_knowledge +
            0.3 * self.abm1_results.food_security_index
        )
        return min(attractiveness, 1.0)

    def _get_nearby_farmers(self, x: float, y: float, radius: float = 1000) -> int:
        """Count active farmers within radius"""
        count = 0
        for farmer in self.farmers:
            if not farmer.active:
                continue
            distance = np.sqrt((farmer.x - x)**2 + (farmer.y - y)**2)
            if distance < radius:
                count += 1
        return count

    def _calculate_rent_pressure(self) -> float:
        """Calculate overall rent pressure in the system"""
        active_farmers = sum(1 for f in self.farmers if f.active)
        if active_farmers == 0:
            return 1.0

        # Pressure increases as land values rise and farmers struggle
        mean_land_value = np.mean([p.current_value for p in self.parcels])
        initial_mean = np.mean([p.base_value for p in self.parcels])

        appreciation_ratio = mean_land_value / initial_mean

        # Pressure also from market attractiveness
        pressure = (0.6 * (appreciation_ratio - 1) +
                   0.4 * self.market_attractiveness)

        return max(0, min(pressure, 1.0))

    def _calculate_gini(self, values: List[float]) -> float:
        """Calculate Gini coefficient"""
        if not values or all(v == 0 for v in values):
            return 0.0

        sorted_values = sorted([v for v in values if v > 0])
        n = len(sorted_values)
        if n == 0:
            return 0.0

        cumsum = np.cumsum(sorted_values)
        return (2 * sum((i+1) * v for i, v in enumerate(sorted_values)) /
                (n * cumsum[-1]) - (n + 1) / n)

    def step(self):
        """Execute one month of simulation"""
        self.month += 1

        # Calculate global conditions
        rent_pressure = self._calculate_rent_pressure()
        mean_land_value = np.mean([p.current_value for p in self.parcels])

        # Land value multiplier for costs
        initial_mean = np.mean([p.base_value for p in self.parcels])
        land_value_multiplier = mean_land_value / initial_mean

        # Update land parcels
        for parcel in self.parcels:
            nearby_farmers = self._get_nearby_farmers(parcel.x, parcel.y)
            mean_neighborhood = np.mean([
                p.current_value for p in self.parcels
                if np.sqrt((p.x - parcel.x)**2 + (p.y - parcel.y)**2) < 1000
            ])

            parcel.step(nearby_farmers, mean_neighborhood,
                       self.market_attractiveness, self.policy)

        # Update farmers
        displacement_events = 0
        for farmer in self.farmers:
            # Get local land value
            nearby_parcels = [
                p for p in self.parcels
                if np.sqrt((p.x - farmer.x)**2 + (p.y - farmer.y)**2) < 500
            ]
            if nearby_parcels:
                local_land_value = np.mean([p.current_value for p in nearby_parcels])
            else:
                local_land_value = mean_land_value

            was_active = farmer.active
            farmer.step(local_land_value, rent_pressure,
                       self.abm1_results.land_productivity,
                       land_value_multiplier, self.policy)

            if was_active and not farmer.active:
                displacement_events += 1

        # Record metrics
        self._record_metrics(displacement_events)

    def _record_metrics(self, displacement_events: int):
        """Record system-level metrics"""
        active_farmers = [f for f in self.farmers if f.active]

        self.metrics['month'].append(self.month)
        self.metrics['active_farmers'].append(len(active_farmers))
        self.metrics['displacement_events'].append(displacement_events)

        if active_farmers:
            self.metrics['mean_farmer_wealth'].append(
                np.mean([f.wealth for f in active_farmers])
            )
            self.metrics['total_production'].append(
                sum(f.production_value for f in active_farmers)
            )
            self.metrics['mean_displacement_risk'].append(
                np.mean([f.displacement_risk for f in active_farmers])
            )

            # Calculate Gini for wealth inequality
            wealth_values = [f.wealth for f in active_farmers]
            self.metrics['gini_coefficient'].append(
                self._calculate_gini(wealth_values)
            )
        else:
            self.metrics['mean_farmer_wealth'].append(0)
            self.metrics['total_production'].append(0)
            self.metrics['mean_displacement_risk'].append(0)
            self.metrics['gini_coefficient'].append(0)

        # Land value metrics
        land_values = [p.current_value for p in self.parcels]
        self.metrics['mean_land_value'].append(np.mean(land_values))

        # Calculate volatility (rolling 12-month std if enough data)
        if len(self.metrics['mean_land_value']) >= 12:
            recent_values = self.metrics['mean_land_value'][-12:]
            volatility = np.std(recent_values) / np.mean(recent_values)
        else:
            volatility = 0.0
        self.metrics['land_value_volatility'].append(volatility)

        # Displacement rate (rolling 12-month)
        if self.month >= 12:
            recent_displacements = sum(self.metrics['displacement_events'][-12:])
            initial_farmers = len(self.farmers)
            displacement_rate = recent_displacements / initial_farmers
        else:
            displacement_rate = 0.0
        self.metrics['displacement_rate'].append(displacement_rate)

    def run(self, months: int = 240):
        """Run simulation for specified months (default 20 years)"""
        print(f"Running ABM 2 for {months} months...")
        print(f"ABM 1 Regime: {self.abm1_results.regime.value}")
        print(f"Policy Protection Index: {self.policy.total_protection_index:.2f}")
        print()

        for month in range(months):
            self.step()

            if (month + 1) % 24 == 0:  # Report every 2 years
                active = len([f for f in self.farmers if f.active])
                mean_value = self.metrics['mean_land_value'][-1]
                print(f"Year {(month+1)//12}: "
                      f"{active} farmers active, "
                      f"Mean land value: R${mean_value:.0f}/m²")

        print("\nSimulation complete!")
        return self.get_results_dataframe()

    def get_results_dataframe(self) -> pd.DataFrame:
        """Export results as DataFrame"""
        return pd.DataFrame(self.metrics)

    def calculate_sustainability_score(self) -> Dict[str, float]:
        """Calculate composite sustainability indicators"""
        df = self.get_results_dataframe()

        # Final state metrics
        final_farmers_pct = df['active_farmers'].iloc[-1] / len(self.farmers)
        mean_displacement_rate = df['displacement_rate'].mean()
        final_land_value = df['mean_land_value'].iloc[-1]
        initial_land_value = df['mean_land_value'].iloc[0]
        land_appreciation = (final_land_value / initial_land_value - 1) * 100

        # Stability metrics
        mean_volatility = df['land_value_volatility'].mean()
        final_gini = df['gini_coefficient'].iloc[-1]

        # Production resilience
        initial_production = df['total_production'].iloc[0]
        final_production = df['total_production'].iloc[-1]
        if initial_production > 0:
            production_retention = (final_production / initial_production) * 100
        else:
            production_retention = 0

        # Composite scores
        social_sustainability = (
            0.5 * final_farmers_pct * 100 +
            0.3 * (1 - mean_displacement_rate) * 100 +
            0.2 * (1 - final_gini) * 100
        )

        economic_sustainability = (
            0.4 * production_retention +
            0.4 * final_farmers_pct * 100 +
            0.2 * (1 - mean_volatility) * 100
        )

        # Penalize excessive appreciation (gentrification indicator)
        if land_appreciation > 150:  # >150% appreciation is problematic
            gentrification_penalty = min((land_appreciation - 150) / 100, 0.5)
        else:
            gentrification_penalty = 0

        overall_sustainability = (
            0.5 * social_sustainability +
            0.5 * economic_sustainability -
            gentrification_penalty * 30
        )

        return {
            'social_sustainability': social_sustainability,
            'economic_sustainability': economic_sustainability,
            'overall_sustainability': max(overall_sustainability, 0),
            'final_farmers_pct': final_farmers_pct * 100,
            'mean_displacement_rate': mean_displacement_rate * 100,
            'land_appreciation_pct': land_appreciation,
            'final_gini': final_gini,
            'production_retention_pct': production_retention,
            'mean_volatility': mean_volatility,
            'regime': self.abm1_results.regime.value,
            'protection_index': self.policy.total_protection_index
        }


class ModelAnalyzer:
    """Analysis and visualization tools for ABM 2"""

    @staticmethod
    def plot_time_series(df: pd.DataFrame, title: str = "Long-Term Dynamics"):
        """Plot key time series"""
        fig, axes = plt.subplots(2, 3, figsize=(18, 10))
        fig.suptitle(title, fontsize=16, fontweight='bold')

        # Active farmers
        axes[0, 0].plot(df['month'], df['active_farmers'], linewidth=2)
        axes[0, 0].set_title('Active Farmers Over Time')
        axes[0, 0].set_xlabel('Month')
        axes[0, 0].set_ylabel('Number of Farmers')
        axes[0, 0].grid(True, alpha=0.3)

        # Land value
        axes[0, 1].plot(df['month'], df['mean_land_value'],
                       linewidth=2, color='green')
        axes[0, 1].set_title('Mean Land Value')
        axes[0, 1].set_xlabel('Month')
        axes[0, 1].set_ylabel('R$/m²')
        axes[0, 1].grid(True, alpha=0.3)

        # Displacement risk
        axes[0, 2].plot(df['month'], df['mean_displacement_risk'],
                       linewidth=2, color='red')
        axes[0, 2].set_title('Mean Displacement Risk')
        axes[0, 2].set_xlabel('Month')
        axes[0, 2].set_ylabel('Risk (0-1)')
        axes[0, 2].grid(True, alpha=0.3)

        # Total production
        axes[1, 0].plot(df['month'], df['total_production'],
                       linewidth=2, color='orange')
        axes[1, 0].set_title('Total Production')
        axes[1, 0].set_xlabel('Month')
        axes[1, 0].set_ylabel('Production Value (R$)')
        axes[1, 0].grid(True, alpha=0.3)

        # Gini coefficient
        axes[1, 1].plot(df['month'], df['gini_coefficient'],
                       linewidth=2, color='purple')
        axes[1, 1].set_title('Wealth Inequality (Gini)')
        axes[1, 1].set_xlabel('Month')
        axes[1, 1].set_ylabel('Gini Coefficient')
        axes[1, 1].grid(True, alpha=0.3)

        # Cumulative displacements
        cumulative_displacements = np.cumsum(df['displacement_events'])
        axes[1, 2].plot(df['month'], cumulative_displacements,
                       linewidth=2, color='darkred')
        axes[1, 2].set_title('Cumulative Displacements')
        axes[1, 2].set_xlabel('Month')
        axes[1, 2].set_ylabel('Number of Farmers')
        axes[1, 2].grid(True, alpha=0.3)

        plt.tight_layout()
        return fig

    @staticmethod
    def plot_sustainability_comparison(results: List[Dict],
                                      labels: List[str]):
        """Compare sustainability scores across scenarios"""
        fig, axes = plt.subplots(1, 3, figsize=(18, 5))

        metrics = ['social_sustainability', 'economic_sustainability',
                  'overall_sustainability']
        titles = ['Social Sustainability', 'Economic Sustainability',
                 'Overall Sustainability']
        colors = ['#3498db', '#2ecc71', '#e74c3c']

        for ax, metric, title, color in zip(axes, metrics, titles, colors):
            values = [r[metric] for r in results]
            bars = ax.bar(labels, values, color=color, alpha=0.7,
                         edgecolor='black', linewidth=1.5)
            ax.set_title(title, fontsize=12, fontweight='bold')
            ax.set_ylabel('Score (0-100)')
            ax.set_ylim(0, 100)
            ax.axhline(y=70, color='green', linestyle='--',
                      label='Target (70)', linewidth=2)
            ax.grid(axis='y', alpha=0.3)
            ax.legend()

            # Add value labels on bars
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{height:.1f}',
                       ha='center', va='bottom', fontweight='bold')

        plt.tight_layout()
        return fig

    @staticmethod
    def export_results(results: Dict, filename: str):
        """Export results to JSON"""
        with open(filename, 'w') as f:
            # Convert numpy types to native Python types
            serializable_results = {}
            for key, value in results.items():
                if isinstance(value, (np.integer, np.floating)):
                    serializable_results[key] = float(value)
                else:
                    serializable_results[key] = value

            json.dump(serializable_results, f, indent=2)
        print(f"Results exported to {filename}")


class ScenarioRunner:
    """Run multiple scenarios linking ABM 1 and ABM 2"""

    @staticmethod
    def create_abm1_scenarios() -> Dict[str, ABM1Results]:
        """Create representative ABM 1 result scenarios"""
        return {
            'low_success': ABM1Results(
                market_share=0.08,
                active_producers=6,
                mean_producer_profit=380,
                mean_consumer_knowledge=0.52,
                land_productivity=4.5,
                food_security_index=0.88
            ),
            'moderate_success': ABM1Results(
                market_share=0.18,
                active_producers=12,
                mean_producer_profit=520,
                mean_consumer_knowledge=0.72,
                land_productivity=6.8,
                food_security_index=0.94
            ),
            'high_success': ABM1Results(
                market_share=0.32,
                active_producers=18,
                mean_producer_profit=680,
                mean_consumer_knowledge=0.85,
                land_productivity=9.2,
                food_security_index=0.97
            )
        }

    @staticmethod
    def create_policy_scenarios() -> Dict[str, PolicyConfig]:
        """Create policy protection scenarios"""
        return {
            'no_protection': PolicyConfig(
                tenure_protection=0.0,
                subsidy_rate=0.0,
                zoning_enforcement=0.0,
                land_trust_coverage=0.0
            ),
            'weak_protection': PolicyConfig(
                tenure_protection=0.30,
                subsidy_rate=0.15,
                zoning_enforcement=0.30,
                land_trust_coverage=0.20
            ),
            'moderate_protection': PolicyConfig(
                tenure_protection=0.60,
                subsidy_rate=0.20,
                zoning_enforcement=0.60,
                land_trust_coverage=0.40
            ),
            'strong_protection': PolicyConfig(
                tenure_protection=0.70,
                subsidy_rate=0.25,
                zoning_enforcement=0.70,
                land_trust_coverage=0.50
            ),
            'maximum_protection': PolicyConfig(
                tenure_protection=0.90,
                subsidy_rate=0.30,
                zoning_enforcement=0.90,
                land_trust_coverage=0.80
            )
        }

    @staticmethod
    def run_full_experiment(months: int = 240, n_farmers: int = 50,
                           output_dir: str = './results'):
        """Run full factorial experiment"""
        Path(output_dir).mkdir(exist_ok=True)

        abm1_scenarios = ScenarioRunner.create_abm1_scenarios()
        policy_scenarios = ScenarioRunner.create_policy_scenarios()

        all_results = []

        print("=" * 70)
        print("RUNNING FULL ABM 1 → ABM 2 INTEGRATION EXPERIMENT")
        print("=" * 70)
        print()

        for abm1_name, abm1_result in abm1_scenarios.items():
            print(f"\n{'='*70}")
            print(f"ABM 1 SCENARIO: {abm1_name.upper()}")
            print(f"Market Share: {abm1_result.market_share:.1%}")
            print(f"Regime: {abm1_result.regime.value}")
            print(f"{'='*70}\n")

            for policy_name, policy in policy_scenarios.items():
                print(f"\n  Testing policy: {policy_name}")
                print(f"  Protection index: {policy.total_protection_index:.2f}")

                # Run model
                model = LongTermUrbanAgricultureModel(
                    abm1_results=abm1_result,
                    policy=policy,
                    n_farmers=n_farmers
                )

                df = model.run(months=months)
                sustainability = model.calculate_sustainability_score()

                # Add scenario identifiers
                sustainability['abm1_scenario'] = abm1_name
                sustainability['policy_scenario'] = policy_name

                all_results.append(sustainability)

                # Save individual run
                scenario_name = f"{abm1_name}_{policy_name}"
                df.to_csv(f"{output_dir}/timeseries_{scenario_name}.csv",
                         index=False)

                # Plot and save
                fig = ModelAnalyzer.plot_time_series(
                    df,
                    title=f"{abm1_name.replace('_', ' ').title()} + "
                          f"{policy_name.replace('_', ' ').title()}"
                )
                fig.savefig(f"{output_dir}/plot_{scenario_name}.png",
                           dpi=300, bbox_inches='tight')
                plt.close()

                print(f"  → Overall Sustainability: "
                      f"{sustainability['overall_sustainability']:.1f}")
                print(f"  → Final Farmers: "
                      f"{sustainability['final_farmers_pct']:.1f}%")

        # Create summary DataFrame
        results_df = pd.DataFrame(all_results)
        results_df.to_csv(f"{output_dir}/summary_all_scenarios.csv",
                         index=False)

        # Create comparison visualizations
        print("\n" + "="*70)
        print("CREATING COMPARATIVE VISUALIZATIONS")
        print("="*70)

        # Plot by regime
        for regime in ['low_success', 'moderate_success', 'high_success']:
            regime_results = [r for r in all_results
                            if r['abm1_scenario'] == regime]
            labels = [r['policy_scenario'].replace('_', '\n')
                     for r in regime_results]

            fig = ModelAnalyzer.plot_sustainability_comparison(
                regime_results, labels
            )
            fig.suptitle(f"Policy Comparison: {regime.replace('_', ' ').title()}",
                        fontsize=14, fontweight='bold')
            fig.savefig(f"{output_dir}/comparison_{regime}.png",
                       dpi=300, bbox_inches='tight')
            plt.close()

        # Heatmap of overall sustainability
        pivot = results_df.pivot(
            index='abm1_scenario',
            columns='policy_scenario',
            values='overall_sustainability'
        )

        fig, ax = plt.subplots(figsize=(12, 6))
        sns.heatmap(pivot, annot=True, fmt='.1f', cmap='RdYlGn',
                   vmin=0, vmax=100, ax=ax, cbar_kws={'label': 'Score'})
        ax.set_title('Overall Sustainability Scores: ABM 1 × Policy Scenarios',
                    fontsize=14, fontweight='bold')
        ax.set_xlabel('Policy Scenario', fontsize=12)
        ax.set_ylabel('ABM 1 Success Level', fontsize=12)
        plt.tight_layout()
        fig.savefig(f"{output_dir}/heatmap_sustainability.png",
                   dpi=300, bbox_inches='tight')
        plt.close()

        print(f"\nAll results saved to {output_dir}/")
        print("Experiment complete!")

        return results_df


if __name__ == "__main__":
    import warnings
    warnings.filterwarnings('ignore')

    print("\n" + "="*70)
    print("ABM 2: LONG-TERM URBAN AGRICULTURE DYNAMICS")
    print("Integrating Results from ABM 1 (Short-Term Market Dynamics)")
    print("="*70 + "\n")

    # Run full experiment
    results = ScenarioRunner.run_full_experiment(
        months=240,  # 20 years
        n_farmers=50,
        output_dir='./abm2_results'
    )

    print("\n" + "="*70)
    print("KEY FINDINGS")
    print("="*70)
    print(results.groupby('regime')[
        ['overall_sustainability', 'final_farmers_pct', 'land_appreciation_pct']
    ].mean().round(1))

    print("\n" + "="*70)
    print("BEST CONFIGURATIONS BY REGIME")
    print("="*70)
    for regime in results['regime'].unique():
        best = results[results['regime'] == regime].nlargest(
            1, 'overall_sustainability'
        ).iloc[0]
        print(f"\n{regime.upper()}:")
        print(f"  Best policy: {best['policy_scenario']}")
        print(f"  Sustainability: {best['overall_sustainability']:.1f}")
        print(f"  Farmers retained: {best['final_farmers_pct']:.1f}%")
        print(f"  Land appreciation: {best['land_appreciation_pct']:.1f}%")