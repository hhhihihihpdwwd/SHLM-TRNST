#!/usr/bin/env python3
"""STABLE30: restore ONLY commuter and SL local rail seven-day GTFS from archived STABLE24.

GTFS Sverige 2 historic week is already independently route matched against OSM.
Leave the current STABLE29 Tunnelbana, all national rail services, all existing
OSM route vertices, photos, icons and UI untouched. Fail hard on any collision.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

PATCH_MODES={'commuter','tram','localrail','saltsjo'}
WEEK_METADATA=(
 'commuterWeekdaySimulation','commuterWeekdaySourceDays','commuterWeeklyCoverage','commuterSourceDisclaimer',
 'localWeekdaySimulation','localWeekdaySourceDays','localWeeklyCoverage','localSourceDisclaimer',
)
LINE_METADATA=('tramLines','roslagsLines','saltsjoLines')
def ident(data):
    return hashlib.sha256(json.dumps(data,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def merge(old,reference):
    assert old.get('metroWeekdaySimulation') is True
    assert old.get('commuterWeekdaySimulation') is not True
    assert old.get('localWeekdaySimulation') is not True
    assert reference.get('metroWeekdaySimulation') is True
    assert reference.get('commuterWeekdaySimulation') is True
    assert reference.get('localWeekdaySimulation') is True
    assert old.get('type')==reference.get('type')=='historical-daily-repeating-simulation'
    assert old['simulationTemplateDay']==reference['simulationTemplateDay']
    assert old['scope']==reference['scope']
    original_untouched=[t for t in old['trips'] if t['mode'] not in PATCH_MODES]
    reference_untouched=[t for t in reference['trips'] if t['mode'] not in PATCH_MODES]
    assert original_untouched==reference_untouched,'Archived source changed a Metro or national train'
    original_patch=[t for t in old['trips'] if t['mode'] in PATCH_MODES]
    fresh=[t for t in reference['trips'] if t['mode'] in PATCH_MODES]
    assert len(fresh)>len(original_patch)>0
    assert len({t['id'] for t in fresh})==len(fresh)
    assert all(t.get('sourceTripId') and t.get('geometryQuality')=='verified-osm-relation'
               and len(t.get('stops',[]))>=2 for t in fresh)
    assert len({t['serviceDay'] for t in fresh})==7
    assert {'2026-11-04','2026-11-05','2026-11-06','2026-11-07','2026-11-08',
            '2026-11-09','2026-11-10'}=={t['serviceDay'] for t in fresh}
    shapes={**old['shapes']}
    used={t['shapeId'] for t in fresh}
    for key in used:
        assert key in reference['shapes'],('Missing source OSM geometry',key)
        if key in shapes:
            assert shapes[key]==reference['shapes'][key],('Original OSM route vertex changed',key)
        else:
            shapes[key]=reference['shapes'][key]
    for t in original_untouched:
        assert t['shapeId'] in shapes
    counts=Counter(t['mode'] for t in fresh)
    assert set(counts)==PATCH_MODES
    result={**old,'trips':original_untouched+fresh,'shapes':shapes}
    result['counts']={**old['counts'],**{mode:counts[mode] for mode in PATCH_MODES}}
    for key in WEEK_METADATA+LINE_METADATA:
        assert key in reference,('Missing independent GTFS source metadata',key)
        result[key]=reference[key]
    assert all(result['shapes'][key]==shape for key,shape in old['shapes'].items())
    assert [t for t in result['trips'] if t['mode'] not in PATCH_MODES]==original_untouched
    assert result['counts']['metro']==13372
    assert sum(result['counts'].values())==len(result['trips'])
    assert len(result['trips'])==len(reference['trips'])
    assert len(result['shapes'])==len(reference['shapes'])
    # Every source line's exact weekly source rows must survive; zero drops.
    groups=Counter((t['serviceDay'],t['mode'],str(t['line'])) for t in fresh)
    for day in sorted({t['serviceDay'] for t in fresh}):
        print('STABLE30 VERIFIED WEEK',day,dict(sorted(
          ((f'{mode}:{line}',n) for (d,mode,line),n in groups.items() if d==day))),flush=True)
    print('STABLE30 PATCHED GTFS COUNTS',dict(counts),flush=True)
    print('STABLE30 UNCHANGED METRO+NATIONAL',len(original_untouched),ident(original_untouched),flush=True)
    print('STABLE30 PRESERVED PREEXISTING TRACKS',len(old['shapes']),
          'TOTAL VERIFIED OSM GEOMETRIES',len(shapes),flush=True)
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--current',type=Path,required=True)
    p.add_argument('--complete-week',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    current=json.loads(a.current.read_text(encoding='utf-8'))
    week=json.loads(a.complete_week.read_text(encoding='utf-8'))
    output=merge(current,week)
    raw=json.dumps(output,ensure_ascii=False,separators=(',',':'))
    assert len(raw.encode())<100_000_000,'Oversized dataset; refuse unsafe publish'
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(raw,encoding='utf-8')
    assert json.loads(a.output.read_text(encoding='utf-8'))['localWeekdaySimulation'] is True
    print('STABLE30 COMPLETE GTFS DATA CREATED',len(raw.encode()),'bytes',flush=True)
if __name__=='__main__':main()
