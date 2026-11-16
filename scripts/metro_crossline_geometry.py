"""Verified OSM relation splicing for historical RED-LINE cross-branch metro trains.

A few genuine GTFS trips operate between terminal branches normally associated
with T13 and T14. Joining existing *verified* red-line relation geometry is
permitted only where the two OSM geometries physically coincide (<= 12 metres).
The finished route must satisfy the same strict monotonic stop projection as
every direct OSM route. No stop-to-stop straight lines are ever generated.
"""
from __future__ import annotations
import math
from refine_osm_routes import project_stops

def meters(a,b):
    k=math.pi/180; x=(a[1]-b[1])*111100*math.cos((a[0]+b[0])*k/2)
    y=(a[0]-b[0])*111100
    return math.hypot(x,y)

def stitch_red_line(stops,shape_by_line,max_stop_error=350):
    start_name=stops[0][2].casefold()
    end_name=stops[-1][2].casefold()
    if ('tekniska högskolan' in start_name and 'sätra' in end_name):
        first_line,second_line='14','13'
    elif ('sätra' in start_name and 'tekniska högskolan' in end_name):
        first_line,second_line='13','14'
    else:
        return None
    p_start=[stops[0][0],stops[0][1]]
    p_end=[stops[-1][0],stops[-1][1]]
    solutions=[]
    joint_center=[59.331,18.060] # T-Centralen, existing common railway area
    for key_a,raw_a in shape_by_line[first_line]:
        for key_b,raw_b in shape_by_line[second_line]:
            for orient_a,a in [('f',raw_a),('r',list(reversed(raw_a)))]:
                for orient_b,b in [('f',raw_b),('r',list(reversed(raw_b)))]:
                    # Ignore shapes travelling away from the relevant initial
                    # and final stations (use proximity, not guessed itinerary).
                    if min(meters(p_start,p) for p in a)>max_stop_error: continue
                    if min(meters(p_end,p) for p in b)>max_stop_error: continue
                    joints=[]
                    # 12 m is a strict OSM intersection tolerance, not
                    # permission to draw a fabricated interstation track.
                    for i,p in enumerate(a):
                        for j,q in enumerate(b):
                            gap=meters(p,q)
                            if gap<=12:
                                joints.append((meters(p,joint_center),gap,i,j))
                    # Most central intersections first, deduplicate repeated
                    # OSM nodes and cap pathological geometric intersections.
                    joints.sort()
                    for _,gap,i,j in joints[:40]:
                        joined=a[:i+1]+b[j:]
                        if len(joined)<2:continue
                        if project_stops(stops,joined,max_stop_error):
                            sid='metro-osm:cross-red:'+key_a.replace('metro-osm:','')+'+'+key_b.replace('metro-osm:','')+':'+orient_a+orient_b+':'+str(i)+':'+str(j)
                            solutions.append((len(joined),gap,sid,joined,(key_a,key_b)))
    if not solutions:return None
    solutions.sort(key=lambda item:(item[0],item[1],item[2]))
    _,_,sid,shape,parents=solutions[0]
    return sid,shape,parents
