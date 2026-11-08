#!/usr/bin/env python3
"""Diagnostic only: identify why OSM route relation 27/28 rejects GTFS stops."""
import datetime as dt
import sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from build_roslags_candidates import build_candidates
from build_rail_keyless import ZONE,fetch_archive
from append_roslagsbanan import osm_shapes, direction, RELATIONS, MAX_STOP_ERROR
from refine_osm_routes import project_stops,total_length,distance

def inspect():
    now=dt.datetime.now(ZONE).date()
    with fetch_archive() as z:
        ds=build_candidates(z,now)
    groups={}
    for trip in ds["trips"]:
        line=trip["line"]
        stops=trip["stops"]
        if direction(line,stops[0][2],stops[-1][2]) is None:continue
        groups.setdefault((line,stops[0][2],stops[-1][2]),trip)
    for line in RELATIONS:
        routes=osm_shapes(line)
        print("DIAG OSM",line,"ROUTES",len(routes),flush=True)
        for rid,geom in routes:
            print("DIAG ROUTE",line,rid,"VERTICES",len(geom),"KM",round(total_length(geom)/1000,2),"FIRST",geom[0],"LAST",geom[-1],flush=True)
        for (ln,first,last),trip in groups.items():
            if ln!=line:continue
            stops=trip["stops"]
            print("DIAG TRIP",line,first,"TO",last,"STOPS",len(stops),"COORDS",stops[0][:2],stops[-1][:2],flush=True)
            for rid,geom in routes:
                for suffix,shape in (("",geom),(":reverse",list(reversed(geom)))):
                    match=project_stops(stops,shape,MAX_STOP_ERROR)
                    sampled=[(st[2],round(min(distance(st[:2],point) for point in shape))) for st in stops[::max(1,len(stops)//8)]]
                    detailed=[(st[2],round(min(distance(st[:2],point) for point in shape))) for st in stops]
                    print("DIAG TRY",line,rid+suffix,"MATCH",bool(match),"STATION DISTANCES",sampled,flush=True)
                    print("DIAG FULL STATION ERRORS",line,rid+suffix,detailed,flush=True)
if __name__=="__main__":inspect()
