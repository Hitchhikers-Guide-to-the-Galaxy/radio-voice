#!/usr/bin/env python3
"""index_city.py — the city media index from every manifest on disk (the truth is the manifests, not a run's log)."""
import json, os, glob, time, collections, sys
C = os.path.expanduser('~/Nextcloud/fedwiki/constitution.legalcommons.org/assets/pages')
AS = os.path.expanduser('~/Nextcloud/fedwiki/atlas.anarchive.earth/assets/hear-crowds-demo')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); from validate import validate_file
d = json.load(open(AS + '/districts.json')); dist = {}
for site, v in d['sites'].items():
    for x in v['districts']:
        for s in x['slugs']: dist[(site, s)] = x['id']
street = json.load(open(os.path.join(HERE, 'street-media.json')))
houses, extras, bad = [], [], []
for mp in sorted(glob.glob(C + '/*/hear/wiki-city-media.json')):
    r = validate_file(mp, 'wiki-city-media', files=os.path.dirname(mp))
    if not r['ok']:
        bad.append((mp.split('/')[-3], [e['code'] for e in r['errors']])); continue
    m = json.load(open(mp)); a = m['assets'][0]; slug = m['semantic_target']['wiki_city_id'].split('/', 1)[1]
    base = f"https://constitution.legalcommons.org/assets/pages/{slug}/hear/"; stem = a['delivery'][0]['uri'].rsplit('.', 1)[0]
    e = dict(slug=slug, title=m['semantic_target']['title'], fragment_id=a['source_text'].get('fragment_id'), heading=a['source_text'].get('heading'),
             words=a['source_text'].get('words'), voice=(a['provenance'].get('voice_id') or 'human:' + a['provenance'].get('reader', '')),
             district=dist.get(('constitution.legalcommons.org', slug)), role=a['role'], seconds=a['duration_seconds'], loudness=a['loudness'],
             rights=a['rights'].get('source_rights_class'), manifest=base + 'wiki-city-media.json', audio=base + stem + '.m4a', opus=base + stem + '.opus')
    (extras if a['role'] == 'human_reading' else houses).append(e)
out = dict(street=street['street'], edition=street.get('edition'), built=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
           scope='every voiced house on constitution.legalcommons.org whose manifest validates', houses=houses, extras=extras)
for p in (os.path.join(HERE, 'city-media.json'), AS + '/city-media.json'): json.dump(out, open(p, 'w'), indent=1)
L = [h['loudness']['integrated_lufs'] for h in houses]
print(f"city index: {len(houses)} houses + {len(extras)} extras; loudness {min(L)}..{max(L)}; invalid left out: {bad}")
