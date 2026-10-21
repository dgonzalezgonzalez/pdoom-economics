# Can Diminishing Returns Restrain an AI Race?

Economics working paper by Diego González-González. The project tests whether declining commercial returns can prevent dangerous AI development, explicitly separating developers' incentives from autonomous resource choices after loss of control.

The results are conditional theory and scenario analysis. The project **does not estimate humanity's extinction probability**. Consumer preference scores do not identify profits, and control-failure and resource-conflict parameters remain assumptions.

## Paper and replication

- [Compiled paper](output/pdf/paper.pdf)
- [LaTeX source](paper/main.tex)
- [Parameter assumptions](replication/parameters.json)
- [Parameter definitions and identification status](replication/PARAMETERS.md)
- [Empirical estimates](output/empirical.json)
- [Model results and equilibrium diagnostics](output/model_results.json)
- [Source provenance and licensing](data/README.md)
- [External referee request, report, and response](review/README.md)

Use Python 3.12 or later, with MiKTeX or TeX Live providing `pdflatex` and `bibtex` on PATH:

```sh
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python replication/run.py
```

The normal run is offline and verifies frozen input hashes. It runs accounting and equilibrium checks, reproduces estimates and numerical scenarios, writes tables and figures, compiles the PDF, and renders every page into ignored `output/qa/` for visual inspection. `--paper-only` recompiles from existing verified outputs; `--no-pdf` runs analysis without TeX. Numerical runtime depends on grid expansion and mixed-equilibrium state games.

The numerical game uses finite-horizon backward induction. Pure equilibria are selected by lower extinction probability, then joint developer payoff, then action order. Without pure equilibria, the solver first checks equal-size nonsingular supports at the smallest successful size; otherwise LP support enumeration returns verified representatives. Mixed equilibria coexisting with pure ones are not enumerated, nor are continua within degenerate supports. Alternative selection is a sensitivity exercise, not an exhaustive equilibrium bound.

The revision includes an explicit recursive stopping benchmark, evaluated no-delegation margins, a welfare decomposition, dyadic preference-uncertainty sensitivity, smaller research projects, separate calibration bridges, and cumulative risk under one fixed long-horizon equilibrium. Each scenario records an analytic domain certificate covering feasible deviations.

## Research boundaries

One developer per jurisdiction; no cross-border relocation; perfect local enforcement; the first loss of control ends human developer competition. Subsequent autonomous acquisition and human subsistence are stylized. Analytic capability bounds cover every feasible finite-horizon path from the initial state, including deviations; grids are expanded before solving. Selected-path zero clipping alone is not a safety certificate. Commercial curvature, research feedback, and social risk valuations are distinct objects. The empirical bridge's stopping result depends on financing and indivisible projects, not an identified commercial-curvature estimate.

The manuscript and code were developed with substantial AI assistance. Exactly one ChatGPT Pro referee request reviewed frozen commit `5a1d9a4`. Its [unaltered report](review/referee-report.pdf) reproduced the draft and found no invalid named proof, but recommended rejection at the requested general-interest journal standard because the contribution was insufficient. The [response](review/response.md) records implemented repairs and remaining limits. Added results and revisions were checked locally without a second external review. This is a working paper, not a claim of journal acceptance or independent human peer review. No journal submission is included.

No repository-wide license is imposed on the manuscript. Third-party data retain their original terms and attribution.
