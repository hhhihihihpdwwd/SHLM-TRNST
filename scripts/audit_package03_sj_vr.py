#!/usr/bin/env python3
"""Package 3: independent, source-aware SJ/VR completeness report.
Read-only. An archive mismatch is a finding, not permission to fabricate trains.
"""
import collections, json, sys
from pathlib import Path

def main():
    dataset=json.loads(Path(sys.argv[1]).read_text())
    sj=json.loads(Path(sys.argv[2]).read_text())
    vr=json.loads(Path(sys.argv[3]).read_text())
    trips=dataset["trips"]
    assert len(trips)==len({t["id"] for t in trips}), "Duplicate template IDs"
    assert len(dataset["shapes"])>=107 and len(trips)>=10787, "stable/17 regression"
    assert all(t["shapeId"] in dataset["shapes"] for t in trips)
    by_agency=collections.Counter(t["agency"] for t in trips)
    published_sj={str(t.get("sourceTripId")) for t in trips
                  if t["agency"]=="SJ" and t.get("sourceTripId")}
    # Historical SJ source can include several dates. Do not equate distinct
    # weekday services with the one repeated reference-day timetable.
    sj_ref={t["id"]:t for t in sj["trips"] if "2026-11-06" in t["sourceDays"]}
    legacy_sj={(tuple(s[2] for s in t["stops"]),t["stops"][0][4],t["stops"][-1][3])
               for t in trips if t["agency"]=="SJ" and not t.get("sourceTripId")}
    missing_sj=[t for sid,t in sj_ref.items() if sid not in published_sj and
                (tuple(s[2] for s in t["stops"]),t["firstDeparture"],t["lastArrival"]) not in legacy_sj]
    published_vr={str(t["id"]).split(":")[1] for t in trips
                  if t["agency"]=="VR Snabbtåg" and str(t["id"]).startswith("VR-ARCHIVE:")}
    vr_ref={str(t["id"]).split(":")[1]:t for t in vr["trips"]}
    missing_vr=[t for sid,t in vr_ref.items() if sid not in published_vr]
    def compact(items):
        groups=collections.Counter((x["origin"],x["destination"]) for x in items if "origin" in x)
        if not groups:
            groups=collections.Counter((x["stops"][0][2],x["stops"][-1][2]) for x in items)
        return [{"from":a,"to":b,"trips":n} for (a,b),n in groups.most_common()]
    night=[t for t in trips if t["agency"]=="SJ" and
           (t.get("serviceCategory")=="night" or
            (t["end"]-t["start"])>=8*3600)]
    # Inventory endpoint families without assuming a specific route exists.
    sj_pairs=compact([{"origin":t["stops"][0][2],"destination":t["stops"][-1][2]}
                      for t in trips if t["agency"]=="SJ"])
    vr_pairs=compact([{"origin":t["stops"][0][2],"destination":t["stops"][-1][2]}
                      for t in trips if t["agency"]=="VR Snabbtåg"])
    errors=[]
    for t in trips:
        if t["agency"] not in ("SJ","VR Snabbtåg"):continue
        stops=t.get("stops") or []
        if len(stops)<2 or t["end"]<=t["start"]:errors.append({"id":t["id"],"reason":"invalid-times-or-stops"});continue
        if any(stops[i][3]<stops[i-1][4] for i in range(1,len(stops))):
            errors.append({"id":t["id"],"reason":"nonmonotonic-stop-times"})
        if t.get("isLiveGPS") is not False:errors.append({"id":t["id"],"reason":"false-live-label"})
    output={
        "referenceDay":"2026-11-06",
        "datasetScope":dataset.get("scope"),"totalTrips":len(trips),
        "tracks":len(dataset["shapes"]),"operatorTemplateCounts":dict(by_agency),
        "sjSourceReferenceFriday":len(sj_ref),"sjPublishedSourceIds":len(published_sj),
        "sjUnmatchedSourceTrips":len(missing_sj),
        "sjLegacyEndpointTimeFingerprints":len(legacy_sj),
        "sjUnmatchedEndpointFamilies":compact(missing_sj),
        "sjUnmatchedExamples":[{"id":t["id"],"origin":t["origin"],"destination":t["destination"]}
                                for t in missing_sj[:30]],
        "vrSourceReferenceFriday":len(vr_ref),"vrPublishedSourceIds":len(published_vr),
        "vrUnmatchedSourceTrips":len(missing_vr),
        "vrUnmatchedEndpointFamilies":compact(missing_vr),
        "sjNightOrLongTemplates":len(night),
        "sjEndpointFamilies":sj_pairs,"vrEndpointFamilies":vr_pairs,
        "structuralErrors":errors[:100],
        "limitations":["All services are historical repeating simulations, not live positions.",
                       "A Friday snapshot cannot establish seven-day timetable completeness.",
                       "Missing source journeys need verified connected OSM geometry before release.",
                       "Original timetable may have multiple GTFS variants of the same physical run."]
    }
    Path(sys.argv[4]).parent.mkdir(parents=True,exist_ok=True)
    Path(sys.argv[4]).write_text(json.dumps(output,ensure_ascii=False,indent=2))
    print(json.dumps(output,ensure_ascii=False,indent=2))
    if errors:raise SystemExit("SJ/VR structural errors: fail closed")

if __name__=="__main__":main()
