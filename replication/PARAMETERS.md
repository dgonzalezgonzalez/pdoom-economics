# Parameters and units

`parameters.json` contains the complete reference inputs. `experiments.py` records every scenario override. Currency, capability, life value, and resources are normalized model units; they are not dollar or energy measurements. A period is one year. The scenario probabilities are not real-world risk estimates.

| Inputs | Interpretation and status |
|---|---|
| `horizon` | Years reported; reference 10, sensitivities 5 and 25. |
| `beta`, `beta_ai` | Annual human and autonomous discount factors; assumptions. |
| `terminal_years`, `terminal_ai` | Frozen human-flow years and terminal AI capability multiplier; assumptions, varied in sensitivity. |
| `sigma`, `commercial_scale` | Commercial marginal benefit is `commercial_scale * a^(-sigma)`; neither is identified by preference data. |
| `capture_share` | Developer's share of human task surplus; unidentified assumption. |
| `prize`, `government_prize`, `contest_power` | Relative competitive reward scales and contest exponent; assumptions. Equal scales give zero-sum positional rewards. |
| `private_life`, `social_life` | Private annual baseline human value and aggregate annual baseline welfare; unidentified normalized assumptions. |
| `research_cost`, `cost_exponent` | Research project cost scale and capability exponent. Reference assumptions; bridge substitutes the estimated log-cost association for the exponent, subject to a strong mapping. |
| `project_size` | Common positive research input for the three active actions. Normalized to one; quarter-size sensitivities vary this indivisibility. It is not a continuous action space. |
| `safety_cost`, `external_finance`, `infrastructure` | Safety resource cost, per-period outside financing, and fixed jurisdiction-specific research capacities; assumptions. Finance does not accumulate. |
| `safety_resource` | Controlled safety's infrastructure coefficient, separate from autonomous acquisition cost. |
| `recovery_share` | Fraction of frozen pre-failure commercial/task flows restored after successful containment. Zero at baseline, one in the recovery sensitivity. This affects developers' incentives; the autonomous objective stays fixed. |
| `acquisition_boundary` | Numerical action-menu sensitivity: include maximum budget-feasible research alongside acquisition, avoiding the extra sacrifice implied by the coarse baseline menu. |
| `research_eta`, `effort_elasticity` | Research rate and input elasticity; assumptions. Bridge replaces the rate using retrospective frontier growth. |
| `research_feedback`, `research_difficulty`, `bottleneck` | AI assistance exponent, research difficulty exponent, and saturation scale; motivated by research-productivity literature but not estimated from it. |
| `delegation_multiplier`, `launch_capability` | Delegation's productivity multiplier and minimum capability; unidentified engineering assumptions. |
| `q0`, `safety_effect`, `loss_correlation` | Per-cycle baseline loss probability, exponential safety effectiveness, and mixture weight between independent failures and a maximally common shock. Unidentified assumptions. Loss risk applies only to delegated actions. |
| `resource_total`, `resource_initial`, `human_subsistence` | Total normalized resources, initial autonomous stock, and minimum human stock. Extinction occurs strictly below the minimum. |
| `seizure_capability`, `seizure_cost`, `resource_enabled` | Acquisition capability requirement, resource cost per acquisition, and whether acquisition is feasible. Assumptions, not physical estimates. |
| `containment`, `containment_decay` | Baseline containment probability per acquisition and its capability-related decay. No containment attempt without acquisition; containment stops AI and restores human baseline resources. |
| `human_resource_elasticity` | Human production's elasticity in remaining resources; assumption. |
| `capability_max`, `ai_max` | Requested computational grid endpoints. Analytic all-path envelopes override endpoints that are too small, including for deviations. No economic conclusion relies on these requested ceilings. |
| `capability_step`, `ai_step` | Capability meshes. Interior targets are projected onto adjacent grid points. They induce numerical randomization, distinct from technical control risk. |
| `selection` | Risk preference among the candidate equilibria returned by the stated solver, with payoff/action-order tie breaks. It does not optimize over the complete equilibrium correspondence. |
| `seed` | Reserved reproducibility label; current algorithms are deterministic and use no stochastic simulation. |

`output/tables/identification.tex` distinguishes estimated coefficients, observed changes, imposed bridges, normalizations, and unidentified assumptions. No monetary benefit curvature, autonomous productivity, loss risk, containment probability, or human-extinction resource threshold is estimated from the public consumer data.

The empirical bridge posits `a = exp((ECI - ECI_reference)/10)`, sets `cost_exponent` equal to the cross-sectional log-cost slope per ten ECI points, and maps one year's retrospective ECI frontier change into a unit-input research increment. These are transparent scenario bridges, not structural identification or a forecast.
