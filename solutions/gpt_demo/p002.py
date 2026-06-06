"""Cascade Log 查询引擎 参考实现。"""
import sys


def parse_log(line):
    ts, level, module, rest = line[1:-1].split('|', 3)
    payload = {}
    if '{' in rest:
        _, payload_str = rest.split('{', 1)
        payload_str = payload_str.rstrip('}')
        if payload_str:
            for kv in payload_str.split(','):
                k, v = kv.split('=', 1)
                payload[k] = v
    return {'ts': int(ts), 'level': level, 'module': module, 'payload': payload}


def matches(e, filters):
    for f in filters:
        k, v = f.split('=', 1)
        if k == 'level' and e['level'] != v:
            return False
        if k == 'module' and e['module'] != v:
            return False
    return True


def main():
    entries, out = [], []
    for line in sys.stdin:
        line = line.rstrip('\n')
        if not line.strip():
            continue
        if line.startswith('QUERY'):
            toks = line.split()
            qtype, rest = toks[1], toks[2:]
            if qtype == 'SUM':
                sum_key, filters = None, []
                for t in rest:
                    k, v = t.split('=', 1)
                    if k == 'key':
                        sum_key = v
                    else:
                        filters.append(t)
                total = 0
                for e in entries:
                    if matches(e, filters) and sum_key in e['payload']:
                        try:
                            total += int(e['payload'][sum_key])
                        except ValueError:
                            pass
                out.append(str(total))
            else:
                matched = [e for e in entries if matches(e, rest)]
                if qtype == 'COUNT':
                    out.append(str(len(matched)))
                elif qtype == 'LATEST':
                    out.append(str(max((e['ts'] for e in matched), default=-1)))
                elif qtype == 'KEYS':
                    keys = set()
                    for e in matched:
                        keys.update(e['payload'].keys())
                    out.append(','.join(sorted(keys)))
        else:
            entries.append(parse_log(line))
    print('\n'.join(out))


main()
