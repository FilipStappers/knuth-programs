"""Small independent native-CNF model checker for encoder regressions."""
def satisfiable(clauses):
    names = {}
    encoded = []
    for clause in clauses:
        encoded.append(tuple((-1 if lit.startswith('~') else 1) *
                             names.setdefault(lit.lstrip('~'), len(names)+1)
                             for lit in clause))

    def solve(cs, assigned):
        while True:
            residual, units = [], {}
            for c in cs:
                if any(abs(x) in assigned and assigned[abs(x)] == (x > 0) for x in c):
                    continue
                r = tuple(x for x in c if abs(x) not in assigned)
                if not r:
                    return False
                if len(r) == 1:
                    k, value = abs(r[0]), r[0] > 0
                    if k in units and units[k] != value:
                        return False
                    units[k] = value
                residual.append(r)
            if not residual:
                return True
            if not units:
                break
            assigned.update(units)
            cs = residual
        x = min(residual, key=len)[0]
        return any(solve(residual, assigned | {abs(x): value})
                   for value in [x > 0, x < 0])

    return solve(encoded, {})
