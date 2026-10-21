# Response to the single referee report

The report concerns frozen commit `5a1d9a436f29e3a69ef434aa1966c0bcf87b3b7e`, not this revision. The [17-page report](referee-report.pdf) is preserved unchanged. Exactly one request was submitted through the prepared ChatGPT Pro browser session. The added results and revisions below received local proof and numerical checks, without a second external review. Numbered results in the report refer to the original draft; inserting the recursive benchmark changes later proposition numbers.

The recommendation was rejection at the requested serious general-interest journal standard, principally because the constructive contribution was insufficient. We accept that assessment as a limitation of the reviewed draft. The revision strengthens the economic characterization and repairs the verified issues; it does not claim that an AI referee has established novelty, journal readiness, or acceptance.

## 1. Formal assumptions and outcome-dependent risk

**Implemented.** The environment now states positive capabilities, positive initial autonomous capacity, total capacity exceeding initial capacity, and initially adequate human subsistence. The unbounded-progress illustration explicitly requires positive initial capability. The no-delegation theorem explicitly refers to a time-dependent Markov-perfect/subgame-perfect equilibrium, avoiding confusion with initial-state Nash optimality.

The local delegation discussion now gives the outcome-dependent identity `N - beta E[q(X) H(X)]`, including its covariance term. The simple probability threshold continues to hold its continuation values fixed and retains its independence assumption. See [theory](../paper/theory.tex).

## 2. Contribution and the stopping characterization

**Strengthened, with limits retained.** A new recursive stopping benchmark compares bounded commercial benefits `R_infinity - b a^(-r)` with research-step costs `c0 a^(-xi)`. It derives complete discounted payoff differences for arbitrary stopping times and explicit eventual stopping or perpetual-improvement regions. Commercial saturation dominates when `xi < r`; recursive cost reduction dominates at sufficiently high capability when `xi > r`. Equality has an exact coefficient comparison. A divisible-input technology maps the comparison into research assistance, difficulty, input prices, and effort elasticity.

The result includes a complete proof and boundary cases. Numerical checks independently compare the gain decomposition with complete discounted flow paths. It is a controlled benchmark, not a theorem that perpetual research in the full strategic model causes extinction. The main race still requires a separate delegation comparison.

**Implemented:** the restricted no-delegation game is now solved and original delegated deviations are explicitly evaluated. [Certificate outputs](../output/tables/certificates.tex) report full-grid and action-reachable maxima and binding states/times; [model results](../output/model_results.json) also record `N`, `H`, risk, and financing slack for the full-grid binding deviations. The reference fails the certificate. The empirical bridge has no feasible delegated deviations in its initial-state action-reachable tree, although its additional, unreachable grid states can have positive margins. This distinction prevents interpreting arbitrary off-path states as evidence of initial-state danger.

The certificate remains an equilibrium-existence statement, not a guarantee covering every equilibrium. Partial enforceability after delegation is a worthwhile further research problem, but the revision does not promise an unproved general comparative-static theorem. Its stated results remain conditional.

## 3. Artificial ceilings and profitable deviations

**Repaired.** Selected-path zero clipping was an inadequate optimization certificate. `reachable_bounds` now constructs an analytic envelope covering every feasible finite-horizon action history from the initial state, including deviations and all autonomous alternatives. A bounded-revenue financing cutoff, when applicable, bounds starting states for positive projects; the final research jump may overshoot that cutoff. Separate upward rounding and full-horizon autonomous bounds cover both grids. `solve_verified_domain` expands the requested domains before solving, rather than consulting the selected path to choose them. The derivation is in the numerical appendix.

The checks include both a small-grid false-stopping example and the report's explicit one-period counterexample. They verify that the old truncated computation holds while the enlarged, certified problem undertakes profitable research.

Recomputed headline reference results are very close to the original values, but not every sensitivity was unaffected. In particular, the long-terminal-value case changes materially, from about 4.108 percent to 4.725 percent extinction within the scenario. All revised tables come from the repaired domains. The bound applies to the finite initial-state game; it is not a continuous-state convergence theorem, an infinite-horizon bound, or a certification of arbitrary unbounded initial-state subgames.

## 4. Support search, transitions, and planning horizons

**Implemented the referee's narrower-description option.** The manuscript and docstrings now specify the fast search exactly: equal-size nonsingular supports at the smallest successful size, with full LP support-pair enumeration only as fallback. The risk rule applies to returned candidates. Government games use the full support-pair routine. Neither mode exhausts degenerate equilibrium continua, and mixed equilibria coexisting with pure equilibria remain unenumerated. We retain the faster developer selection because all returned candidates are checked for profitable unilateral deviations; we withdraw any suggestion that it obtains global equilibrium risk bounds. The report's explicit omitted-support example is now a regression check.

**Reconciled:** the formal Bellman game now uses conditional regime-specific kernels. The no-failure branch projects onto the controlled grid. The failure branch projects the same unrounded research target directly onto the autonomous grid. Both are explicitly numerical approximations; the text no longer claims one shared rounded realization followed by a state map. The code and model now agree.

**Implemented:** existing rows are labeled planning-horizon comparisons, with decisions re-optimized at each horizon. A separate recursion now measures cumulative risk at years 5, 10, and 25 while following the same policies optimized for 25 years. The [fixed-policy table](../output/tables/fixed_horizon_risk.tex) differs from separately solved short-horizon economies. Probability monotonicity, conservation, extinction/first-loss ordering, and agreement at the terminal date are checked. Human and AI terminal coefficients are varied separately as well as jointly. No infinite-horizon safety claim is made.

## 5. Financing, indivisibility, and autonomous effort

**Implemented.** The bridge discussion now shows its actual budget mechanism. At the first unrounded target, another unit project costs about 7.353 normalized units against funding of about 2.055. Delegation is unavailable before the first supervised jump. Thus stopping is imposed by eligibility and financing under indivisible unit projects; it is not an identified finding that feasible dangerous research is unprofitable.

Quarter-size project sensitivities permit delegation; at 25 years the corresponding bridge has positive modeled extinction probability. The text also explains why arbitrarily small supervised input can defeat exact stopping in a clean final-period comparison with positive marginal benefits and effort elasticity below one. The finite action game is retained as an explicit economic restriction; capability-mesh refinement alone is not presented as action-space robustness.

An autonomous sensitivity adds the affordable research boundary `k - acquisition_cost * y`, exposing the extra opportunity cost of the coarse baseline menu. Controlled safety infrastructure now has its own parameter, `safety_resource`, instead of borrowing autonomous acquisition cost. See [parameter definitions](../replication/PARAMETERS.md).

## 6. Survival, production, recovery, and welfare

**Implemented.** Productive resources are interpreted as persistent capacity yielding renewed services, rather than an undepleted consumable flow. Private baseline utility is explicitly a composite of life and consumption: it falls with resource diversion before death. The revision does not interpret increasing `private_life` as changing only the pure value of survival.

The solver separately propagates discounted survival and production annuities, surviving task surplus, and development costs. [Welfare components](../output/tables/welfare_components.tex) reconcile baseline utility plus task surplus, minus research/safety costs, mortality losses, and nonfatal resource losses. The accounting identity is checked. A recovery sensitivity restores pre-failure commercial/task flows, frozen at pre-failure capabilities, only after successful containment. This exposes the baseline assumption of permanent loss of those flows even after containment.

These are welfare comparisons under specified utility and recovery assumptions. They do not estimate willingness to pay for extinction-risk reduction or establish a general risk ordering of regulatory policies.

## 7. Empirical population, uncertainty, and fitted shape

**Implemented.** The manuscript now reports the sample flow: 135,634 raw observations; 108,315 first-round votes; 37,799 primary matches before outcome exclusions; 5,847 ties and 4,481 both-bad outcomes excluded; 27,471 decisive comparisons retained. [Model-support counts](../output/tables/model_support.csv) make model concentration inspectable. Qualified mappings remain separate and alter the estimand as well as sample size. Reasoning-budget differences unresolved by model-level ECI are explicitly retained as a limitation.

The dyadic score sandwich now permits dependence whenever observations share a model. Self-model comparisons are included once per distinct endpoint, with overlap subtraction only for distinct model pairs. The resulting primary linear and quadratic standard errors are approximately 0.14454 and 0.15836, reproducing the referee's sensitivity. The quadratic interval widens to approximately [-0.411, 0.210]. Finite-model and capability-score uncertainty remain unresolved; eigenvalue diagnostics are exposed, and this is not described as definitive inference.

The appendix now plots fitted latent levels and slopes on actual support. It identifies the common-sample ECI turning point near 140.39 and distinguishes its nonmonotonicity from the primary fit. ECI and GPQA can reorder models; their contrast is not attributed solely to an arbitrary monotone change of units.

We did not impose a monotonicity-constrained utility function: the descriptive unconstrained fits and their failure to establish uniformly increasing value are relevant evidence, while imposing the desired shape would not identify financial returns. The paper continues to avoid causal capability, willingness-to-pay, revenue, or profit claims.

## 8. Separate bridges and provenance

**Implemented.** Cost and progress bridges are each run alone. The text anchors the mapping at `ECI_reference = 168.83`, states its implied delegation/acquisition scores, and discloses extrapolation beyond the cost sample. Alternative scaling formulas show that choosing another capability mapping while retaining other primitives changes the assumed economy. A status table separates estimates, observed moments, imposed bridges, normalizations, and unidentified assumptions. Neither commercial curvature nor catastrophe parameters are estimated.

`acquire_data.arena` now reuses original revision/retrieval metadata only after verifying the cached hash. It rejects cached data without matching original provenance and no longer labels old bytes using a fresh remote revision. Acquisition errors preserve existing manifest entries. Normal replication remains offline.

## 9. Numerical policy statements and negligible probabilities

**Implemented and rechecked.** Risk-region labels now distinguish exact computed zero from a positive value below the reporting tolerance. Display rounding is not treated as a safety proof. The government prisoner's-dilemma inequalities and planner welfare comparisons receive explicit checks in the experiments. The result remains conditional on selected continuations, policies, enforceability, planning horizon, and welfare assumptions. Eliminating acquisition excludes the stipulated channel and changes upstream incentives; it does not rule out other real-world dangers.

## 10. Validation and remaining scope

The documented command `python replication/run.py` verifies all frozen source hashes, behavioral and counterexample checks, restricted and unrestricted incentives, probability and welfare identities, estimates, scenario tables, and the PDF build. It renders every page for visual inspection. A fresh source snapshot is used for the final clean replication; its record is in [clean replication](../output/clean_replication.json).

No second referee request, journal submission, model of several uncontrolled systems, relocation extension, or identified real-world extinction probability has been added. We retain the report's central editorial warning: a correct, reproducible working paper and a sharper conditional benchmark do not establish a general-interest-journal contribution. Human theoretical and empirical scrutiny remains necessary.
