"""Lokale Stimm-Schicht für K-Creative: Segmentierung, Engines, Persona-/Kanal-Registry."""


def synthesize(*a, **k):
    from .synth import synthesize as _s
    return _s(*a, **k)
