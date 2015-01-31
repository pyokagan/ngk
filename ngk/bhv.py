import time
import itertools


def iter_until(it, predicate=bool):
    """Iterates over `it` until predicate is True"""
    while True:
        ret = next(it)
        if predicate(ret):
            return ret
        yield


def call_until(f, predicate=bool):
    """Calls `f` until `predicate` returns True"""
    while True:
        ret = f()
        if predicate(ret):
            return ret
        yield


def parallel(*iterators):
    """Runs `iterators` in parallel until they all have values (or timeout)"""
    total = len(iterators)
    complete = [False for i in range(total)]
    rets = [None for i in range(total)]
    completed = 0
    while True:
        for i, it in enumerate(iterators):
            if complete[i]:
                continue
            try:
                next(it)
            except StopIteration as e:
                rets[i] = e.value
                complete[i] = True
                completed += 1
        if completed >= total:
            return rets
        yield completed


def any(*iterators):
    """Runs `iterators` in parallel until one of them returns"""
    while True:
        for it in iterators:
            next(it)
        yield


def sleep(t):
    return itertools.repeat(None, int(t))


def interval(it, interval=1.0/60):
    """Iterates `it` at `interval`"""
    last_step_time = time.monotonic()
    while True:
        now = time.monotonic()
        while last_step_time + interval < now:
            next(it)
            last_step_time += interval
        yield
