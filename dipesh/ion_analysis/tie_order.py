"""
The order in which equally bright candidates are taken when single ions
are separated (brightest first, each removing its neighbours): with many
pixels of the same value, the order of the ties decides which of two
touching candidates survives, so it is a setting (SinglesParams.ties).

    reading   brightest first; equal ones in reading order (row by row,
              left to right). The default: the same on every computer.
    numpy1    the order NumPy 1.x's argsort gave (its quicksort, reversed),
              which earlier analyses depended on without saying so. NumPy
              2 sorts ties differently, so the same old code gives other
              counts there; this reproduces the old ones anywhere.
"""

import numpy as np

SMALL = 15          # parts of 16 or fewer are insertion-sorted


def reading(values):
    """Brightest first, ties in reading order. -> index array"""
    return np.argsort(-np.asarray(values, np.float64), kind="stable")


def _heapsort(v, a, lo, n):
    """NumPy's aheapsort on a[lo:lo+n] (1-based heap, as in npysort)."""
    def at(i):                       # a[lo + i - 1], 1-based
        return lo + i - 1
    for l in range(n >> 1, 0, -1):
        tmp = a[at(l)]
        i, j = l, l << 1
        while j <= n:
            if j < n and v[a[at(j)]] < v[a[at(j + 1)]]:
                j += 1
            if v[tmp] < v[a[at(j)]]:
                a[at(i)] = a[at(j)]
                i, j = j, j + j
            else:
                break
        a[at(i)] = tmp
    while n > 1:
        tmp = a[at(n)]
        a[at(n)] = a[at(1)]
        n -= 1
        i, j = 1, 2
        while j <= n:
            if j < n and v[a[at(j)]] < v[a[at(j + 1)]]:
                j += 1
            if v[tmp] < v[a[at(j)]]:
                a[at(i)] = a[at(j)]
                i, j = j, j + j
            else:
                break
        a[at(i)] = tmp


def numpy1_argsort(values):
    """np.argsort(values) exactly as NumPy 1.x computed it (introsort:
    median-of-three quicksort, insertion sort for parts of 16 elements or
    fewer, heapsort past the depth limit); checked against NumPy 1.26 on
    hundreds of arrays full of ties. -> list of indices, ascending."""
    v = [float(x) for x in values]
    num = len(v)
    a = list(range(num))
    if num < 2:
        return a
    stack, depths = [], []
    pl, pr = 0, num - 1
    cdepth = (num.bit_length() - 1) * 2
    while True:
        if cdepth < 0:
            _heapsort(v, a, pl, pr - pl + 1)
        else:
            while pr - pl > SMALL:
                pm = pl + ((pr - pl) >> 1)
                if v[a[pm]] < v[a[pl]]:
                    a[pm], a[pl] = a[pl], a[pm]
                if v[a[pr]] < v[a[pm]]:
                    a[pr], a[pm] = a[pm], a[pr]
                if v[a[pm]] < v[a[pl]]:
                    a[pm], a[pl] = a[pl], a[pm]
                vp = v[a[pm]]
                pi, pj = pl, pr - 1
                a[pm], a[pj] = a[pj], a[pm]
                while True:
                    pi += 1
                    while v[a[pi]] < vp:
                        pi += 1
                    pj -= 1
                    while vp < v[a[pj]]:
                        pj -= 1
                    if pi >= pj:
                        break
                    a[pi], a[pj] = a[pj], a[pi]
                pk = pr - 1
                a[pi], a[pk] = a[pk], a[pi]
                # the larger part waits on the stack
                if pi - pl < pr - pi:
                    stack += [pi + 1, pr]
                    pr = pi - 1
                else:
                    stack += [pl, pi - 1]
                    pl = pi + 1
                cdepth -= 1
                depths.append(cdepth)
            for i in range(pl + 1, pr + 1):            # insertion sort
                vi = a[i]
                vv = v[vi]
                j = i
                while j > pl and vv < v[a[j - 1]]:
                    a[j] = a[j - 1]
                    j -= 1
                a[j] = vi
        if not stack:
            break
        pr = stack.pop()
        pl = stack.pop()
        cdepth = depths.pop()
    return a


def numpy1(values):
    """Brightest first in NumPy 1.x's order. -> index array"""
    return np.array(numpy1_argsort(values)[::-1], dtype=np.intp)


ORDERS = {"reading": reading, "numpy1": numpy1}
