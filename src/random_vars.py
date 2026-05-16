import math
import time

_state = int(time.time() * 1000) & 0xFFFFFFFF


def _lcg() -> float:
    """Linear congruential generator — returns U(0,1)."""
    global _state
    _state = (1664525 * _state + 1013904223) & 0xFFFFFFFF
    return _state / 0xFFFFFFFF


def seed(s: int) -> None:
    global _state
    _state = s & 0xFFFFFFFF


def uniform() -> float:
    """U(0,1)."""
    return _lcg()


def exponential(lam: float) -> float:
    """Exp(lambda) via inverse transform: -1/lambda * ln(U)."""
    u = _lcg()
    while u == 0.0:
        u = _lcg()
    return -1.0 / lam * math.log(u)


def normal(mu: float, sigma2: float) -> float:
    """N(mu, sigma^2) via Box-Muller transform."""
    sigma = math.sqrt(sigma2)
    u1 = _lcg()
    u2 = _lcg()
    while u1 == 0.0:
        u1 = _lcg()
    z = math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)
    return mu + sigma * z


def bernoulli(p: float) -> bool:
    """Returns True with probability p."""
    return _lcg() < p
