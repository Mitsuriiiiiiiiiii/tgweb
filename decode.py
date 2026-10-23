import json, re, base64, struct, socket, hashlib

DC_IP = {1: '149.154.175.53', 2: '149.154.167.51', 3: '149.154.175.100',
         4: '149.154.167.91', 5: '91.108.56.130'}
API_ID, API_HASH = 2040, 'b18441a1ff607e10a989891a5462e627'


def _key(v):
    if isinstance(v, str):
        s = v.strip()
        if re.fullmatch(r'[0-9a-fA-F]{512}', s):
            return bytes.fromhex(s)
        try:
            b = base64.b64decode(s + '=' * (-len(s) % 4))
            if len(b) == 256:
                return b
        except Exception:
            pass
    if isinstance(v, dict) and 'u8' in v:
        try:
            b = bytes.fromhex(v['u8'])
            if len(b) == 256:
                return b
        except Exception:
            pass
    if isinstance(v, list) and len(v) == 256 and all(isinstance(x, int) for x in v):
        return bytes(v)
    return None


def _walk(o, path=''):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from _walk(v, path + '.' + str(k))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from _walk(v, path + '[' + str(i) + ']')
    else:
        yield path, o


def _pairs(o):
    out = []

    def rec(x):
        if isinstance(x, dict):
            d = None
            for kk in ('dcId', 'dc_id', 'dc'):
                if kk in x and str(x[kk]).isdigit():
                    d = int(x[kk])
            if d:
                for kk in ('authKey', 'auth_key', 'authKeyHex', 'key'):
                    if kk in x:
                        kb = _key(x[kk])
                        if kb:
                            out.append((d, kb))
                            break
            for v in x.values():
                rec(v)
        elif isinstance(x, list):
            for v in x:
                rec(v)

    rec(o)
    return out


def norm_dc(d):
    d = int(d)
    return d if 1 <= d <= 5 else ((d - 1) % 5) + 1


def extract(dump):
    cands = []
    for p, v in _walk(dump):
        kb = _key(v)
        if not kb:
            continue
        dc = None
        m = re.search(r'(?:^|[._\[])dc_?([0-9]+)', p, re.I)
        if m:
            dc = int(m.group(1))
        cands.append({'dc': dc, 'key': kb, 'path': p})

    for d, kb in _pairs(dump):
        cands.append({'dc': d, 'key': kb, 'path': 'pair'})

    gdc = None
    for p, v in _walk(dump):
        if re.search(r'(^|[._])dc(id)?$', p, re.I) and str(v).isdigit():
            gdc = int(v)
            break
    if gdc is None and cands:
        gdc = cands[0]['dc'] or 2

    seen, out = set(), []
    for c in cands:
        if c['key'] in seen:
            continue
        seen.add(c['key'])
        c['dc'] = norm_dc(c['dc'] or gdc or 2)
        out.append(c)
    return out


def user_id(dump):
    for p, v in _walk(dump):
        if 'user_auth' in p and isinstance(v, str):
            try:
                j = json.loads(v)
                if 'id' in j:
                    return int(j['id'])
            except Exception:
                pass
    for p, v in _walk(dump):
        if re.search(r'(userId|user_id)$', p, re.I) and str(v).isdigit():
            return int(v)
    return None


def string_session(dc, key):
    payload = struct.pack('>B', dc) + socket.inet_aton(DC_IP[dc]) + struct.pack('>H', 443) + key
    return '1' + base64.urlsafe_b64encode(payload).decode().rstrip('=')


def main(dump):
    cands = extract(dump)
    if not cands:
        print('aucune cle trouvee')
        return None
    uid = user_id(dump)
    print('url     :', dump.get('url'))
    print('user_id :', uid)
    print('cles    :', len(cands))
    for c in cands:
        print('   dc%s  %s  %s' % (c['dc'], hashlib.sha1(c['key']).hexdigest()[:12], c['path']))
    c = cands[0]
    ss = string_session(c['dc'], c['key'])
    open('session.txt', 'w').write(ss)
    json.dump({'dc_id': c['dc'], 'auth_key_hex': c['key'].hex(), 'user_id': uid,
               'api_id': API_ID, 'api_hash': API_HASH}, open('session.json', 'w'), indent=1)
    print('-> session.txt + session.json')
    return ss


if __name__ == '__main__':
    import sys
    main(json.load(open(sys.argv[1], encoding='utf-8')))
