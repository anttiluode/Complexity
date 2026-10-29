"""Headless numerical core of phi-world-theory/best.py (MiniWoW.step), pinned commit 17e86f1.

State is (phi, phi_prev, step_index, rng_state). The update is the source recurrence, in the
source's operation order and float32 by default:

    lap  = 6-point lattice Laplacian (scipy.ndimage.convolve, mode wrap|nearest)
    Vp   = -pot_lin*phi + pot_cub*phi**3
    c2   = 1 / (1 + tension*phi**2 + 1e-6)
    acc  = c2*lap - Vp
    next = phi + (1 - damping*dt)*(phi - phi_prev) + dt**2*acc

Equal phi with unequal phi_prev gives unequal futures: phi alone is not the state.
"""
from __future__ import annotations

import dataclasses
import json
from dataclasses import dataclass, field

import numpy as np
from scipy.ndimage import convolve

BOUNDARIES = ("wrap", "nearest")
KINDS = ("box", "sphere", "torus")

KERN = np.zeros((3, 3, 3), np.float32)
KERN[1, 1, 1] = -6
for _d in [(1, 1, 0), (1, 1, 2), (1, 0, 1), (1, 2, 1), (0, 1, 1), (2, 1, 1)]:
    KERN[_d] = 1


@dataclass(frozen=True)
class Config:
    n: int
    dt: float = 0.1
    damping: float = 0.001
    tension: float = 5.0
    pot_lin: float = 1.0
    pot_cub: float = 0.2
    boundary: str = "nearest"
    dtype: str = "float32"
    seed: int = 0

    def __post_init__(self):
        if not isinstance(self.n, int) or self.n < 3:
            raise ValueError("n must be an int >= 3")
        if not self.dt > 0:
            raise ValueError("dt must be > 0")
        if self.boundary not in BOUNDARIES:
            raise ValueError(f"boundary must be one of {BOUNDARIES}")
        if self.dtype not in ("float32", "float64"):
            raise ValueError("dtype must be float32 or float64")

    def to_dict(self):
        return dataclasses.asdict(self)

    def hash(self):
        import hashlib
        return hashlib.sha256(json.dumps(self.to_dict(), sort_keys=True).encode()).hexdigest()[:16]


@dataclass
class State:
    phi: np.ndarray
    phi_prev: np.ndarray
    step_index: int = 0
    rng_state: dict = field(default_factory=dict)

    def copy(self):
        return State(self.phi.copy(), self.phi_prev.copy(), self.step_index, json.loads(json.dumps(self.rng_state)))


def source_boundary(kind):
    """best.py: mode = 'wrap' if topology in ['torus', 'sphere'] else 'nearest'."""
    return "wrap" if kind in ("torus", "sphere") else "nearest"


def initial_state(config: Config, kind: str) -> State:
    """Source init_field() followed by change_topology()'s phi_o = phi.copy() (zero velocity)."""
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {KINDS}")
    N = config.n
    x = np.arange(N)
    X, Y, Z = np.meshgrid(x, x, x, indexing="ij")
    c = N // 2
    r = N // 6
    phi = np.zeros((N, N, N), np.dtype(config.dtype))
    if kind == "box":
        phi[:] = 2 * np.exp(-((X - c) ** 2 + (Y - c) ** 2 + (Z - c) ** 2) / (2 * r**2))
    elif kind == "sphere":
        r_shell, thickness = N / 3, N / 10
        R2 = (X - c) ** 2 + (Y - c) ** 2 + (Z - c) ** 2
        phi[:] = 2 * np.exp(-(np.sqrt(R2) - r_shell) ** 2 / (2 * thickness**2))
    else:
        R_major, R_minor = N / 3, N / 8
        d = np.sqrt((np.sqrt((X - c) ** 2 + (Y - c) ** 2) - R_major) ** 2 + (Z - c) ** 2)
        phi[:] = 2 * np.exp(-(d**2) / (2 * R_minor**2))
    rng = np.random.default_rng(config.seed)
    return State(phi=phi, phi_prev=phi.copy(), step_index=0, rng_state=rng.bit_generator.state)


def _check(state, config):
    if state.phi.shape != (config.n,) * 3 or state.phi_prev.shape != (config.n,) * 3:
        raise ValueError("state shape does not match config.n")
    if not (np.isfinite(state.phi).all() and np.isfinite(state.phi_prev).all()):
        raise FloatingPointError("non-finite state")


def step(state: State, config: Config) -> State:
    _check(state, config)
    phi, phi_o = state.phi, state.phi_prev
    lap = convolve(phi, KERN.astype(phi.dtype), mode=config.boundary)
    Vp = -config.pot_lin * phi + config.pot_cub * phi**3
    c2 = 1.0 / (1.0 + config.tension * phi**2 + 1e-6)
    acc = c2 * lap - Vp
    vel = phi - phi_o
    new = phi + (1 - config.damping * config.dt) * vel + config.dt**2 * acc
    return State(phi=new, phi_prev=phi.copy(), step_index=state.step_index + 1, rng_state=state.rng_state)


def run(state: State, config: Config, n_steps: int) -> State:
    for _ in range(n_steps):
        state = step(state, config)
    return state


def kick(state: State, config: Config, profile: np.ndarray, amplitude: float, channel: str) -> State:
    """velocity: v=(phi-phi_prev)/dt increases by amplitude*profile, phi unchanged.
    position: phi and phi_prev both shift by amplitude*profile, v unchanged."""
    if profile.shape != state.phi.shape:
        raise ValueError("profile shape mismatch")
    out = state.copy()
    d = (amplitude * profile).astype(out.phi.dtype)
    if channel == "velocity":
        out.phi_prev = (out.phi_prev - config.dt * d).astype(out.phi.dtype)
    elif channel == "position":
        out.phi = out.phi + d
        out.phi_prev = out.phi_prev + d
    else:
        raise ValueError("channel must be velocity or position")
    return out


def save_state(path: str, state: State, config: Config) -> None:
    np.savez_compressed(path, phi=state.phi, phi_prev=state.phi_prev,
                        step_index=np.int64(state.step_index),
                        rng_state=np.array(json.dumps(state.rng_state)),
                        config=np.array(json.dumps(config.to_dict())))


def load_state(path: str):
    d = np.load(path, allow_pickle=False)
    cfg = Config(**json.loads(str(d["config"])))
    st = State(phi=d["phi"].copy(), phi_prev=d["phi_prev"].copy(), step_index=int(d["step_index"]),
               rng_state=json.loads(str(d["rng_state"])))
    return st, cfg
