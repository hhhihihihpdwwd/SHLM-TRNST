"""Strict authentic OSM splice for historical Saltsjöbanan line-26 through trains.

Some real archive trips operate Saltsjö-Järla–Solsidan instead of terminating
at Igelboda. Use only 25 + 26's already-verified OSM rail vertices. Junction
points must coincide within <=10 metres near Igelboda and the entire ordered
GTFS station pattern must validate. Never draw a stop-to-stop connector.
"""
from __future__ import annotations
import math
from refine_osm_routes import project_stops

def metres(a,b):
    p=(a[0]+b[0])*math.pi/360
    return math.hypot((a[0]-b[0])*111100,(a[1]-b[1])*111100*math.cos(p))

def stitch_saltsjo_25_26(stops,inventory):
    if not stops or not inventory.get("25") or not inventory.get("26"):return None
    origin=stops[0][2].casefold()
    destination=stops[-1][2].casefold()
    if "saltsjö-järla" in origin and "solsidan" in destination:
        initial,final="25","26"
    elif "solsidan" in origin and "saltsjö-järla" in destination:
        initial,final="26","25"
    else:return None
    junction=next(([s[0],s[1]] for s in stops if "igelboda" in s[2].casefold()),None)
    if junction is None:return None
    solutions=[]
    for sid_a,source_a in inventory[initial].items():
        for sid_b,source_b in inventory[final].items():
            for dir_a,a in (("f",source_a),("r",list(reversed(source_a)))):
                for dir_b,b in (("f",source_b),("r",list(reversed(source_b)))):
                    candidates_a=[(i,p) for i,p in enumerate(a) if metres(p,junction)<=450]
                    candidates_b=[(j,q) for j,q in enumerate(b) if metres(q,junction)<=450]
                    for i,p in candidates_a:
                        for j,q in candidates_b:
                            gap=metres(p,q)
                            if gap>10:continue
                            shape=a[:i+1]+b[j:]
                            if project_stops(stops,shape,350) is None:continue
                            id="sl-local-cross:saltsjo:"+sid_a+":"+sid_b+":"+dir_a+dir_b+":"+str(i)+":"+str(j)
                            solutions.append((gap,len(shape),id,shape,[sid_a,sid_b]))
    if not solutions:return None
    solutions.sort(key=lambda x:(x[0],x[1],x[2]))
    gap,_,id,shape,parents=solutions[0]
    return id,shape,parents,gap
