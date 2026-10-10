"""Python mirror of the ProductionLimits config parser + profile expansion in BP_MapLoad (same string steps).
Run: python tools/profiles_sim.py   (runs the tests)"""

OFF_WORDS = ('off', '-', '--', 'none', '')


def strip_comment(line):
    for ch in (';', '#'):
        i = line.find(ch)
        if i >= 0:
            line = line[:i]
    return line


def parse(defaults_text, user_text):
    """Both texts '|'-joined (the BP turns the file's newlines into '|'). Returns [(name, items)]
    items = 'key=val,key=val,' (keys/values trimmed + lower case)."""
    names, keys, items = [], [], []
    cur = -1
    for raw in (defaults_text + '|' + user_text.replace('\n', '|')).split('|'):
        if raw == '':
            continue
        line = strip_comment(raw)
        L = line.strip().lower()
        if L == '':
            continue
        if L.startswith('['):
            body = line.strip()[1:]
            if ']' in body:
                body = body.split(']', 1)[0]
            name = body.strip()
            key = name.lower()
            if key in keys:                      # same name as an earlier section: start it over (replace)
                cur = keys.index(key)
                items[cur] = ''
            else:
                names.append(name); keys.append(key); items.append('')
                cur = len(names) - 1
            continue
        if '=' not in line or cur < 0:
            continue
        k, v = line.split('=', 1)
        k, v = k.strip().lower(), v.strip().lower()
        if k == '':
            continue
        items[cur] = items[cur] + k + '=' + v + ','
    return [(n, it) for n, it in zip(names, items) if it != '']


def expand(items, item_names, item_cats):
    """-> [(resource, value)] in window spelling; later lines win. value 'off'-words -> clear."""
    want_n, want_v = [], []

    def put(res, val):
        if res in want_n:
            want_v[want_n.index(res)] = val
        else:
            want_n.append(res); want_v.append(val)

    lower_names = [n.lower() for n in item_names]
    for tok in [t for t in items.split(',') if t != '']:
        k, v = tok.split('=', 1)
        if k == '*':
            for n in item_names:
                put(n, v)
        elif k.startswith('@'):
            c = k[1:]
            for n, ic in zip(item_names, item_cats):
                if ic.lower() == c:
                    put(n, v)
        elif k in lower_names:                      # Name compare is case-insensitive in UE
            put(item_names[lower_names.index(k)], v)
    return list(zip(want_n, want_v))


def actions(pairs):
    out = []
    for res, v in pairs:
        if v in OFF_WORDS:
            out.append(('clearProductionLimit', res, 0))
        elif v.isdigit():
            out.append(('setProductionLimit', res, int(v)))
        else:
            out.append(('bad', res, v))
    return out


if __name__ == '__main__':
    D = '[Initial]|wood = 50|stone = 100|[Midgame]|* = off|@ore = 20|[Advanced]|wood = 500|[No limits]|* = off'
    U = ('; my file\n[initial]   ; replaces\n berries = 30 ; c\nWood = 80\n\n[Advanced]\n# empty: removes\n'
         '[My farm]\nwheat = 200\nflax=\n[Midgame]\n@ore = 40\ncopperore = off\n')
    p = parse(D, U)
    print(p)
    assert [n for n, _ in p] == ['Initial', 'Midgame', 'No limits', 'My farm'], p
    assert p[0][1] == 'berries=30,wood=80,'
    assert p[3][1] == 'wheat=200,flax=,'
    names = ['wood', 'stone', 'berries', 'copperOre', 'tinore', 'wheat', 'flax']
    cats = ['raw', 'raw', 'rawFood', 'ore', 'ore', 'raw', 'raw']
    e = expand(p[1][1], names, cats)
    assert e == [('copperOre', 'off'), ('tinore', '40')], e
    a = actions(expand(p[3][1], names, cats))
    assert a == [('setProductionLimit', 'wheat', 200), ('clearProductionLimit', 'flax', 0)], a
    a = actions(expand('*=off,wood=10,', names, cats))
    assert a[0] == ('setProductionLimit', 'wood', 10) and len(a) == 7
    assert parse('', '[X]\nfoo\n') == []
    assert parse('', 'wood = 1\n[Y] trailing\nwood=2') == [('Y', 'wood=2,')]
    print('all tests ok')
