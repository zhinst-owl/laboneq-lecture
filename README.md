# LabOne Q Lecture

A hands-on course on [LabOne Q](https://github.com/zhinst/laboneq), Zurich Instruments' software framework
for quantum computing, and its [Applications Library](https://github.com/zhinst/laboneq-applications).
Six notebooks take you from the first `DeviceSetup` to a fully automated multi-qubit calibration pipeline.

Everything runs **without hardware**: every notebook compiles against a real instrument description in
LabOne Q's emulation mode, so you see the real compiler, the real pulse sheets and the real analysis code —
just no rack. Nothing here needs a LabOne installation or a licence.

## Setup

You need Python 3.10 or newer. Create an environment, install the two packages the course is about, and
start Jupyter from the repository root (the notebooks read their helper files via relative paths):

```bash
git clone https://github.com/zhinst-owl/laboneq-lecture.git
cd laboneq-lecture
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
jupyter lab
```

That is the whole environment: `laboneq`, `laboneq-applications`, JupyterLab, and `xarray` for the
result logbook used in the last lecture. The versions are pinned in `requirements.txt` to the release the
course was verified against; a GitHub Action re-runs every notebook on each push and once a week.

## The course

Work through the notebooks in order. Each one is self-contained and builds its own setup.

| # | Notebook | What you learn |
|---|----------|----------------|
| 1 | `01_Basic_Concepts.ipynb` | `DeviceSetup` and the descriptor, logical signal lines, `Session`, `Calibration`, sections and pulses, sweeps and averaging, the pulse sheet viewer and the output simulator, custom pulse shapes with `register_pulse_functional`, and switching between pulses in real time with `match` / `case`. |
| 2 | `02_Case_Study_ef_Rabi.ipynb` | A worked example in the plain DSL: an e-f Rabi experiment on an SHFQC where the g-e and e-f drives share one physical port — and the timing rule that makes the oscillator switch work. |
| 3 | `03_Operations_QPU_Topology.ipynb` | Quantum operations, qubits and the `QPU`: what an operation builds, inspecting one before running it, qubit parameters and the calibration they generate, topology edges, and a two-qubit gate defined on top of the topology. |
| 4 | `04_Workflows.ipynb` | The workflow DSL: tasks, workflows, `compile_experiment` / `run_experiment`, and a shipped Amplitude Rabi workflow — its task tree, pulling one task's output, `temporary_parameters`, and the pulse sheet straight from a workflow result. |
| 5 | `05_Workflow_Exercise.ipynb` | **Exercise.** Rewrite the e-f Rabi of the case study the way every experiment in the Applications Library is written: `@dsl.qubit_experiment`, quantum operations, the standard workflow signature, and a conditional analysis branch. Two cells to fill in; `05_Workflow_Exercise_Solution.ipynb` has the answer. |
| 6 | `06_Automation.ipynb` | The automation framework: layers, nodes, dependencies and retry logic on a toy example, `WorkflowAutomation` for experiment workflows, result injection, and a six-layer single-qubit tune-up (Rabi → Ramsey → Rabi → DRAG → Rabi → RB) for three qubits of a six-qubit chip — including a qubit that fails evaluation and the logic that recovers it automatically. |

## The chip in Lecture 6

`automation_helpers/` holds a six-qubit `DeviceSetup` and `QPU` (an SHFQC, an HDAWG and a PQSC) and one
recorded `Results` file per calibration step. No instrument and no emulator produced those results: they
are computed from a small physical model of each qubit — a Rabi cosine, a damped Ramsey fringe, the two
DRAG lines, an RB decay — sampled with 1024-shot statistics and readout noise, and placed in the IQ plane
between a |g⟩ and an |e⟩ calibration point. The calibration stored in the QPU is deliberately a few percent
off from that model, so the pipeline has real corrections to make. `generate_synthetic_data.py` in the
same folder regenerates all of it; change the seed or the model and the lecture follows.

## Going further

- [LabOne Q User Manual](https://docs.zhinst.com/labone_q_user_manual/) — the reference this course follows
- [Applications Library docs](https://docs.zhinst.com/labone_q_user_manual/applications_library/) — every experiment used in Lectures 4–6
- [laboneq on GitHub](https://github.com/zhinst/laboneq), [laboneq-applications on GitHub](https://github.com/zhinst/laboneq-applications)

## License

Apache License 2.0 — see `LICENSE`. Copyright 2026 Zurich Instruments AG.
