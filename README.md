# Can Diminishing Returns Restrain an AI Race?

Economics working paper by Diego González-González. The project tests whether declining commercial returns can prevent dangerous AI development, explicitly separating developers' incentives from autonomous resource choices after loss of control.

The results are conditional theory and scenario analysis. The project **does not estimate humanity's extinction probability**. Consumer preference scores do not identify profits, and control-failure and resource-conflict parameters remain assumptions.

## Paper and replication

- [Compiled paper](output/pdf/paper.pdf)
- [LaTeX source](paper/main.tex)
- [Parameter assumptions](replication/parameters.json)
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

The numerical game uses finite-horizon backward induction. Pure equilibria are selected by lower extinction probability, then joint developer payoff, then action order. If no pure equilibrium exists, support feasibility programs return verified mixed equilibria. Mixed equilibria coexisting with pure ones are not enumerated. Alternative selection is a sensitivity exercise, not an exhaustive equilibrium bound.

## Research boundaries

One developer per jurisdiction; no cross-border relocation; perfect local enforcement; the first loss of control ends human developer competition. Subsequent autonomous acquisition and human subsistence are stylized. Capability ceilings are computational and expanded until initial-state clipping probability is below 1e-9. Commercial curvature, research feedback, and social risk valuations are distinct objects.

The manuscript and code were developed with substantial AI assistance. Formal proofs, data limitations, and the single requested external ChatGPT review are documented for inspection. This repository is a working paper, not a claim of journal acceptance or independent peer review. No journal submission is included.

No repository-wide license is imposed on the manuscript. Third-party data retain their original terms and attribution.
