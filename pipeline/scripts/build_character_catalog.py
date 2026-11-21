#!/usr/bin/env python3
"""Stream a deterministic 100K procedural preset catalogue and queue manifests.

This indexes combinations only; it does not claim 100K hand-authored or
individually rendered production models. Jobs are chunked for bounded memory.
"""
from __future__ import annotations
import argparse, hashlib, itertools, json
from pathlib import Path

def load_dimensions(path: Path):
    data=json.loads(path.read_text(encoding="utf-8"))
    dims=data.get("dimensions")
    if not isinstance(dims,dict) or not dims: raise ValueError("dimensions must be a non-empty object")
    keys=list(dims)
    values=[]
    for key in keys:
        arr=dims[key]
        if not isinstance(arr,list) or not arr or any(not isinstance(v,str) or not v for v in arr):
            raise ValueError(f"invalid dimension: {key}")
        if len(set(arr))!=len(arr): raise ValueError(f"duplicate values in dimension: {key}")
        values.append(arr)
    return data,keys,values

def total_count(values):
    n=1
    for group in values: n*=len(group)
    return n

def make_record(index, keys, values):
    sizes=[len(v) for v in values]
    rem=index; chosen=[None]*len(keys)
    for pos in range(len(keys)-1,-1,-1):
        rem, digit=divmod(rem,sizes[pos]); chosen[pos]=values[pos][digit]
    dimensions=dict(zip(keys,chosen))
    canonical=json.dumps(dimensions,sort_keys=True,separators=(",",":"))
    digest=hashlib.sha256(canonical.encode()).hexdigest()
    return {"catalog_index":index,"asset_id":f"FG-HUM-{index+1:06d}","seed":int(digest[:8],16),"dimensions":dimensions,"preset_sha256":digest,"quality_tier":"preset","generation_status":"not_generated"}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--dimensions",default="pipeline/catalog/character-dimensions.json")
    p.add_argument("--output",default="artifacts/catalog")
    p.add_argument("--offset",type=int,default=0)
    p.add_argument("--limit",type=int,default=None)
    p.add_argument("--batch-size",type=int,default=500)
    a=p.parse_args()
    if a.offset<0 or (a.limit is not None and a.limit<0) or a.batch_size<1: raise ValueError("offset/limit/batch-size out of range")
    config,keys,values=load_dimensions(Path(a.dimensions))
    total=total_count(values)
    if total!=config.get("catalog_size"): raise ValueError(f"configured catalog_size {config.get('catalog_size')} != computed {total}")
    if a.offset>total: raise ValueError("offset exceeds catalog size")
    stop=min(total,a.offset+(a.limit if a.limit is not None else total-a.offset))
    root=Path(a.output); root.mkdir(parents=True,exist_ok=True)
    manifest_dir=root/"queue"; manifest_dir.mkdir(exist_ok=True)
    batch=[]; batch_no=a.offset//a.batch_size; written=0; jsonl=root/"presets.jsonl"
    with jsonl.open("w",encoding="utf-8") as stream:
        for index in range(a.offset,stop):
            record=make_record(index,keys,values)
            stream.write(json.dumps(record,separators=(",",":"))+"\n")
            batch.append(record); written+=1
            if len(batch)==a.batch_size or index==stop-1:
                payload={"schema_version":"forge.queue-batch.v1","batch_id":f"forge-{batch_no:06d}","offset":index-len(batch)+1,"count":len(batch),"job_type":"character_preset","jobs":batch,"execution_policy":{"max_concurrency":4,"retry_limit":3,"idempotency":"asset_id+preset_sha256"}}
                (manifest_dir/f"batch-{batch_no:06d}.json").write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
                batch=[]; batch_no+=1
    summary={"schema":"forge.catalog-build.v1","catalog_size":total,"offset":a.offset,"written":written,"batch_size":a.batch_size,"batch_count":(written+a.batch_size-1)//a.batch_size,"unique_id_range":[f"FG-HUM-{a.offset+1:06d}",f"FG-HUM-{stop:06d}"] if written else [],"dimensions":{k:len(v) for k,v in zip(keys,values)},"storage_layout":"presets.jsonl + queue/batch-*.json","status":"preset_catalog_created_not_generated_assets"}
    (root/"catalog-report.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary,indent=2))
if __name__=="__main__": main()
