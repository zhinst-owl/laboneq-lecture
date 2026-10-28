"""Generate the synthetic chip and measurement results used by Lecture 4.

No instrument and no emulator is involved: every result file is computed from a
small physical model of each qubit (a Rabi cosine, a damped Ramsey fringe, the two
DRAG lines, an RB decay), sampled with 1024-shot binomial noise and placed in the
IQ plane between a |g> and an |e> calibration point with readout noise on top.

The qubit parameters stored in the QPU file are the *starting calibration* — a
little off from the model's truth, so the automated tune-up has something to
correct. Run this file from the ``automation_helpers`` folder to regenerate
everything:

    python generate_synthetic_data.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import yaml
from laboneq import serializers
from laboneq.dsl.result import AcquiredResult, Results
from laboneq_applications.qpu_types.tunable_transmon.demo_qpus import demo_platform

HERE = Path(__file__).parent
OUT = HERE / "saved_results"
OUT.mkdir(exist_ok=True)

rng = np.random.default_rng(2026)

N_QUBITS = 6
COUNT = 1024
RB_LENGTHS = [1, 2, 4, 8, 16, 32, 64, 128, 256]
RB_VARIATIONS = 4
RAMSEY_DETUNING = 1.6e6

# ---------------------------------------------------------------------------
# 1. The chip: a 6-qubit demo platform (SHFQC + HDAWG + PQSC), with the
#    starting calibration written into the qubit parameters.
# ---------------------------------------------------------------------------
platform = demo_platform(n_qubits=N_QUBITS)
setup, qpu = platform.setup, platform.qpu

for i, q in enumerate(qpu.quantum_elements):
    q.update(
        resonance_frequency_ge=6.12e9 + 0.085e9 * i,
        drive_lo_frequency=6.0e9,
        readout_resonator_frequency=7.05e9 + 0.04e9 * i,
        readout_lo_frequency=7.0e9,
        ge_drive_amplitude_pi=0.62 + 0.03 * i,
        ge_drive_amplitude_pi2=(0.62 + 0.03 * i) / 2,
        ge_drive_length=32e-9,
        ge_drive_pulse={"function": "drag", "beta": 0.0, "sigma": 0.25},
        readout_length=1.5e-6,
        readout_integration_length=1.5e-6,
        reset_delay_length=100e-6,
    )

serializers.save(setup, HERE / "setup_synthetic_6q.json")
serializers.save(qpu, HERE / "qpu_synthetic_6q.json")

# ---------------------------------------------------------------------------
# 2. The truth: what the "real" qubits do, as seen by each experiment.
# ---------------------------------------------------------------------------
qubit_ids = [q.uid for q in qpu.quantum_elements]
truth = {}
for q in qpu.quantum_elements:
    p = q.parameters
    truth[q.uid] = {
        "pi_amp": p.ge_drive_amplitude_pi * (1 + rng.uniform(-0.05, 0.05)),
        "freq_offset": rng.uniform(-0.35e6, 0.35e6),  # true f_ge - calibrated f_ge
        "t2_star": rng.uniform(1.2e-6, 2.5e-6),
        "beta": rng.uniform(-0.015, 0.03),
        "drag_slope": rng.uniform(3.0, 5.0),
        "rb_p": rng.uniform(0.996, 0.9985),  # Clifford survival per gate
        "g_point": (rng.uniform(-1.5, 1.5) + 1j * rng.uniform(-1.5, 1.5)) * 1e-3,
        "e_point": None,
    }
    angle = rng.uniform(0, 2 * np.pi)
    truth[q.uid]["e_point"] = truth[q.uid]["g_point"] + 2.4e-3 * np.exp(1j * angle)


def iq(q: str, population: np.ndarray | float) -> np.ndarray | complex:
    """Place a population on the g-e line in the IQ plane, with shot and readout noise."""
    population = np.clip(np.asarray(population, dtype=float), 0, 1)
    measured = np.asarray(rng.binomial(COUNT, population) / COUNT, dtype=float)
    g, e = truth[q]["g_point"], truth[q]["e_point"]
    readout_noise = 0.012 * abs(e - g) * (rng.normal(size=measured.shape) + 1j * rng.normal(size=measured.shape))
    return g + measured * (e - g) + readout_noise


def cal_traces(q: str) -> dict[str, AcquiredResult]:
    return {
        f"{q}/cal_trace/g": AcquiredResult(data=np.complex128(iq(q, 0.02)), axis_name=[], axis=[]),
        f"{q}/cal_trace/e": AcquiredResult(data=np.complex128(iq(q, 0.96)), axis_name=[], axis=[]),
    }


def save(name: str, acquired: dict[str, AcquiredResult]) -> None:
    serializers.save(Results(acquired_results=acquired), OUT / f"{name}.json")
    print(f"{name}.json: {len(acquired)} handles")


# ---------------------------------------------------------------------------
# 3. One file per calibration step.
# ---------------------------------------------------------------------------
def rabi_file(name: str, amplitudes: np.ndarray) -> None:
    acquired = {}
    for q in qubit_ids:
        population = 0.5 * (1 - np.cos(np.pi * amplitudes / truth[q]["pi_amp"]))
        acquired[f"{q}/result"] = AcquiredResult(data=iq(q, population), axis_name=[q], axis=[amplitudes])
        acquired.update(cal_traces(q))
    save(name, acquired)


def ramsey_file(name: str, delays: np.ndarray) -> None:
    acquired = {}
    for q in qubit_ids:
        f_osc = RAMSEY_DETUNING - truth[q]["freq_offset"]
        population = 0.5 + 0.5 * np.cos(2 * np.pi * f_osc * delays) * np.exp(-delays / truth[q]["t2_star"])
        acquired[f"{q}/result"] = AcquiredResult(
            data=iq(q, population), axis_name=[["wait_time_" + q, "x90_phases_" + q]],
            axis=[[delays, 2 * np.pi * RAMSEY_DETUNING * delays]],
        )
        acquired.update(cal_traces(q))
    save(name, acquired)


def drag_file(name: str, q_scalings: np.ndarray) -> None:
    acquired = {}
    for q in qubit_ids:
        k, b0 = truth[q]["drag_slope"], truth[q]["beta"]
        lines = {"xx": 0.5 + 0 * q_scalings, "xy": 0.5 + k * (q_scalings - b0), "xmy": 0.5 - k * (q_scalings - b0)}
        for pulse_id, population in lines.items():
            acquired[f"{q}/result/{pulse_id}"] = AcquiredResult(data=iq(q, population), axis_name=[q], axis=[q_scalings])
        acquired.update(cal_traces(q))
    save(name, acquired)


def rb_file(name: str, lengths: list[int], variations: int) -> None:
    acquired = {}
    m = np.array(lengths * variations, dtype=float)
    for q in qubit_ids:
        population = 0.5 - 0.5 * truth[q]["rb_p"] ** m
        acquired[f"{q}/result"] = AcquiredResult(data=iq(q, population), axis_name=["index_" + q], axis=[np.arange(len(m))])
        acquired.update(cal_traces(q))
    save(name, acquired)


rabi_amplitudes = np.linspace(0, 1, 31)
fine_amplitudes = np.linspace(0, 1, 51)
ramsey_delays = np.linspace(0, 800e-9, 31)
q_scalings = np.linspace(-0.05, 0.05, 21)

rabi_file("rabi_results", rabi_amplitudes)
ramsey_file("ramsey_results", ramsey_delays)
rabi_file("rabi_fine_results", fine_amplitudes)
drag_file("drag_results", q_scalings)
rabi_file("rabi_fine_2_results", fine_amplitudes)
rb_file("sqrb_results", RB_LENGTHS, RB_VARIATIONS)

# ---------------------------------------------------------------------------
# 4. The automation parameters the lecture loads, for every qubit on the chip.
# ---------------------------------------------------------------------------
def layer(workflow_parameters, options, evaluation=None, inject=None):
    entry = {
        "workflow_parameters": {q: dict(workflow_parameters) for q in qubit_ids},
        "options": {**options, "inject_results": {"paths": [f"automation_helpers/saved_results/{inject}.json"], "use": "emulation", "check_shapes": False}},
    }
    if evaluation:
        entry["evaluation_parameters"] = {k: {q: v for q in qubit_ids} for k, v in evaluation.items()}
    return entry


common = {"evaluate": True, "update": True, "count": COUNT, "active_reset": False, "do_raw_data_plotting": False}
params = {
    "rabi": layer({"amplitudes": rabi_amplitudes.tolist()}, common, {"fit_r2_thresholds": 0.85, "parameter_thresholds": 1e-4}, "rabi_results"),
    "ramsey": layer({"delays": ramsey_delays.tolist(), "detunings": RAMSEY_DETUNING}, common, {"fit_r2_thresholds": 0.85, "parameter_thresholds": 1e-7}, "ramsey_results"),
    "rabi_fine": layer({"amplitudes": fine_amplitudes.tolist()}, common, {"fit_r2_thresholds": 0.85, "parameter_thresholds": 1e-4}, "rabi_fine_results"),
    "drag": layer({"q_scalings": q_scalings.tolist()}, {**common, "evaluate": False}, None, "drag_results"),
    "rabi_fine_2": layer({"amplitudes": fine_amplitudes.tolist()}, common, {"fit_r2_thresholds": 0.85, "parameter_thresholds": 1e-4}, "rabi_fine_2_results"),
    "sqrb": layer({"length_cliffords": RB_LENGTHS, "variations": RB_VARIATIONS}, {"update": True, "count": 512, "transition": "ge", "do_raw_data_plotting": False}, None, "sqrb_results"),
}
with open(HERE / "automation_params.yml", "w") as f:
    yaml.safe_dump(params, f, sort_keys=False)
print("automation_params.yml written for", qubit_ids)
print("truth:", {q: {k: round(v, 4) if isinstance(v, float) else None for k, v in t.items() if k in ("pi_amp", "freq_offset", "beta", "rb_p")} for q, t in truth.items()})
