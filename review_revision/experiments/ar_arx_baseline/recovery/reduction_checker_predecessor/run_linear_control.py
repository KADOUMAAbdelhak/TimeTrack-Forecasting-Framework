#!/usr/bin/env python3
"""Stage18B3. Frozen readers only; every writer is confined to this namespace."""
from __future__ import annotations
import argparse
import fcntl
import importlib
import json
import multiprocessing as mp
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

# Limit BLAS threads before numpy/sklearn imports, without changing Ridge math.
for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[name] = "1"
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PRIOR = ROOT / "review_revision/experiments/s2_common_context"
B2 = ROOT / "review_revision/experiments/m1_capacity_matched"
sys.path.insert(0, str(PRIOR))
sys.path.insert(0, str(ROOT))
import run_control as frozen
sha, canonical, read, now, require = frozen.sha, frozen.canonical, frozen.read, frozen.now, frozen.require
CONFIG = HERE / "control_config.json"
LABEL = "POST-HOC SENSITIVITY CONTROL"
RESULT_LABEL = "POST-HOC SENSITIVITY RESULT"
PROTECTED = (*frozen.PROTECTED, str(PRIOR.relative_to(ROOT)),
             "review_revision/experiments/s2_common_context_predecessor_stage18b1r",
             str(B2.relative_to(ROOT)), "benchmark/src")
ENGINE = None

def output(path):
    path = Path(path).resolve()
    require(path.is_relative_to(HERE), f"Forbidden write {path}", "WRITE_SCOPE_CONFLICT")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path

def write(path, value):
    path = output(path); tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n")
    os.replace(tmp, path)

def parquet(path, frame):
    path = output(path); tmp = path.with_suffix(path.suffix + ".tmp")
    frame.to_parquet(tmp, index=False, compression="zstd"); os.replace(tmp, path)

def verify_refs():
    c = read(CONFIG)
    require(frozen.git("branch", "--show-current") == c["branch"], "Branch differs")
    require(frozen.git("rev-parse", "HEAD") == c["parent_manuscript_checkpoint"], "HEAD differs")
    require(frozen.git("rev-parse", "HEAD^") == c["parent_scientific_checkpoint"], "Parent differs")
    require(frozen.refs()["scientific_tag_target"] == c["parent_scientific_checkpoint"], "Tag differs")
    require(not frozen.git("diff", "--name-only") and not frozen.git("diff", "--cached", "--name-only"), "Tracked modifications exist")

def protected_inventory():
    for rel in PROTECTED:
        for p in sorted((ROOT / rel).rglob("*")):
            if p.is_file(): yield {"path":str(p.relative_to(ROOT)), "bytes":p.stat().st_size, "sha256":sha(p)}

def preserve(capture=False):
    path = output(HERE / "provenance/preservation_before.jsonl")
    if capture:
        require(not path.exists(), "Baseline already exists")
        previous = B2 / "provenance/preservation_before.jsonl"
        require(sha(previous) == read(B2 / "provenance/preservation_baseline.json")["inventory_sha256"], "Previous baseline altered")
        with previous.open() as s: old = {r["path"]:r for r in map(json.loads,s)}
        count = 0
        with path.open("x") as stream:
            for row in protected_inventory():
                if row["path"] in old:
                    require(old.pop(row["path"]) == row, f"Pre-existing protected artifact differs {row['path']}")
                stream.write(json.dumps(row, sort_keys=True)+"\n"); count += 1
        require(not old, "Previously protected artifacts missing")
        write(HERE / "provenance/preservation_baseline.json", {"files":count,"refs":frozen.refs(),"inventory_sha256":sha(path),"timestamp":now()})
    else:
        meta = read(HERE / "provenance/preservation_baseline.json")
        require(sha(path) == meta["inventory_sha256"] and frozen.refs() == meta["refs"], "Baseline/refs differ")
        with path.open() as s: expected = {r["path"]:r for r in map(json.loads,s)}
        count = 0
        for row in protected_inventory():
            require(expected.get(row["path"]) == row, f"Protected file changed/added {row['path']}")
            count += 1
        require(count == len(expected), "Protected file missing")
        write(HERE / "provenance/preservation_after.json", {"status":"PASS","files":count,"modified":0,"refs":frozen.refs(),"timestamp":now()})

def source_hashes():
    paths = list(HERE.glob("*.py")) + [CONFIG, PRIOR / "run_control.py"]
    for rel in frozen.PROTECTED[:3]:
        base = ROOT / rel
        paths += list(base.glob("*.py")) + list((base / "src").rglob("*.py"))
    paths += list((ROOT / "benchmark/src").rglob("*.py"))
    return {str(p.relative_to(ROOT)):sha(p) for p in sorted(set(paths))}

def verify_seal():
    successor = HERE / "recovery/successor_audit_fix.json"
    if not successor.exists(): successor = HERE / "recovery/successor.json"
    seal = read(successor if successor.exists() else HERE / "provenance/experiment.json")
    if successor.exists():
        require(sha(HERE/"provenance/experiment.json") == seal["predecessor_seal_sha256"], "Original seal changed")
        require(sha(HERE/"recovery/authorisation.json") == seal["authorisation_sha256"], "Recovery authority changed")
        require(sha(HERE/"recovery/predecessor_snapshot.json") == seal["snapshot_manifest_sha256"], "Snapshot manifest changed")
        require(sha(HERE/"recovery/tests.json") == seal["tests_sha256"], "Recovery tests changed")
        require(sha(HERE/"recovery/exact_adapter_diff.patch") == seal["exact_diff_sha256"], "Adapter diff changed")
        if "prior_successor_sha256" in seal:
            require(sha(HERE/"recovery/successor.json") == seal["prior_successor_sha256"], "Prior recovery seal changed")
            require(sha(HERE/"recovery/STOP.json") == seal["resolved_audit_stop_sha256"], "Historical audit STOP changed")
    require(sha(CONFIG) == seal["configuration_sha256"], "Config changed", "PROVENANCE_CONFLICT")
    for rel,h in seal["source_hashes"].items(): require(sha(ROOT/rel) == h, f"Source changed {rel}", "PROVENANCE_CONFLICT")
    for b,h in seal["plan_hashes"].items(): require(sha(HERE/f"plans/{b}.json") == h, f"Plan changed {b}", "PROVENANCE_CONFLICT")

def ridge_class():
    return importlib.import_module("benchmark.src.models.ridge").RidgeForecaster

def selector():
    return importlib.import_module("benchmark.src.selection").select_from_inner_validation

def init_worker(block):
    global ENGINE
    ENGINE = frozen.Engine(block)
    from threadpoolctl import threadpool_limits
    ENGINE.thread_limit = threadpool_limits(limits=1)

def plan_block(block):
    e = frozen.Engine(block); tasks = []
    expected = e.core.FROZEN_CONFIG_HASH if e.tt else e.materna.CONFIG_SHA256 if block.startswith("Materna") else e.core.CONFIG_HASH
    require(sha(e.config_path) == expected, "Frozen config differs")
    entities = e.entities(); require(len(entities) == (7 if e.tt else 35), "Cohort count differs")
    contexts = e.contexts[e.contexts.formulation.eq("M1")]
    require(set(contexts[e.entity_key]) == set(entities) and len(contexts) == 5*len(entities), "Frozen M1 cohort differs")
    sources = {str(p.relative_to(ROOT)):sha(p) for p in [e.config_path,e.support_path,*e.cohort_paths,e.root/"selected_contexts.csv",e.root/"run_registry.csv",e.root/"inner_run_registry.csv"]}
    for entity in entities:
        for k in range(1,6):
            row = e.unique(contexts, **{e.entity_key:entity,"fold":k})
            L = int(row.selected_L); require(L in ([32,64,128] if e.tt else [4,9,18]), "Context outside frozen grid")
            frame,folds = e.data(entity,L); fold = folds[k-1]
            support = e.support
            if "environment" in support:
                env = block if block.startswith("Materna") else e.core.ENVIRONMENTS[block]
                support = support[support.environment.eq(env)]
            sr = e.unique(support, **{e.entity_key:entity,"fold":k,"context_length" if e.tt else "L":L})
            require(all(sr[f"{name}_hash"] == v for name,v in fold.hashes.items()), "Frozen support manifest differs", "SCIENTIFIC_SUPPORT_CONFLICT")
            scalers = {}
            for phase in ("inner","final"):
                scalers[phase] = e.scaler_payload(e.scaler(frame,entity,getattr(fold,"inner_train" if phase=="inner" else "outer_train"),L))
                frozen.finite_primary(scalers[phase])
            original = e.unique(e.registry, **{e.entity_key:entity,"fold":k,"formulation":"M1","seed":0})
            record_path, record = e.record(original,"final")
            require(int(record["identity"]["L"]) == L, "Frozen M1 context/record differs")
            require(e.scaler_from_record(record) == scalers["final"], "Frozen outer scaler differs")
            pred_path = e.artifact(record,"prediction")
            require(sha(pred_path) == record["prediction_sha256"], "Frozen prediction hash differs")
            inner = e.unique(e.inner_registry, **{e.entity_key:entity,"fold":k,"formulation":"M1","seed":0,"L":L})
            _, ir = e.record(inner,"inner")
            require(e.scaler_from_record(ir) == scalers["inner"], "Frozen inner scaler differs")
            require(all(record[f"{name}_hash"] == fold.hashes[name] for name in ("outer_train","outer_test")), "Frozen outer origins differ")
            spec = {"namespace":read(CONFIG)["namespace"],"configuration_sha256":sha(CONFIG),"block":block,"entity":entity,"fold":k,"L":L,"split_hashes":fold.hashes,"scalers":scalers,"inner_support":e.support_hash(fold,"inner"),"final_support":e.support_hash(fold,"final"),"reference_record":str(record_path),"reference_record_sha256":sha(record_path),"reference_prediction":str(pred_path),"reference_prediction_sha256":sha(pred_path)}
            spec["group_id"] = canonical(spec); tasks.append(spec)
        print(f"PLAN {block} entity={entity} groups={len(tasks)}",flush=True)
    write(HERE/f"plans/{block}.json", {"block":block,"entities":entities,"groups":tasks,"source_hashes":sources,"inner":40*len(tasks),"final":8*len(tasks),"metric_rows":8*len(tasks)*len(e.leads)})

def ident(spec, phase, form, resource, alpha, selection_hash=None):
    value = {k:spec[k] for k in ("namespace","configuration_sha256","group_id","block","entity","fold","L")}
    value.update(phase=phase,formulation=form,resource=resource,alpha=float(alpha),support=spec[f"{phase}_support"],scaler_sha256=canonical(spec["scalers"][phase]))
    if phase == "final":
        require(selection_hash is not None, "Selection required before final")
        value["selection_sha256"] = selection_hash
    value["run_id"] = canonical(value)
    return value

def completion_path(identity):
    return HERE/f"completions/{identity['phase']}/{identity['block']}/{identity['run_id']}.json"

def begin(identity):
    path = HERE/f"attempts/{identity['phase']}/{identity['block']}/{identity['run_id']}.json"
    if path.exists() and identity["run_id"] in authorised_recoveries():
        approved = authorised_recoveries()[identity["run_id"]]
        require(identity == approved["identity"] and read(path)["identity"] == identity, "Recovery identity changed")
        path = HERE/f"recovery/attempts/{identity['run_id']}.json"
    require(not path.exists(), f"Unresolved attempt {identity}", "UNRESOLVED_ATTEMPT_CONFLICT")
    write(path,{"identity":identity,"started":now()})

def authorised_recoveries():
    path = HERE/"recovery/authorisation.json"
    return read(path)["units"] if path.exists() else {}

def unresolved_failures(allow_authorised_pending=False):
    approved = authorised_recoveries(); unresolved = []
    for p in (HERE/"failures").rglob("*.json"):
        if p.stem not in approved or sha(p) != approved[p.stem]["failure_sha256"]:
            unresolved.append(str(p)); continue
        identity = approved[p.stem]["identity"]; completion = completion_path(identity)
        if completion.exists(): validate_completion(identity,read(completion))
        elif not allow_authorised_pending: unresolved.append(str(p))
    unresolved += [str(p) for p in (HERE/"recovery/failures").rglob("*.json")]
    return unresolved

def verify_predecessor():
    manifest = read(HERE/"recovery/predecessor_snapshot.json")
    snapshot = Path(manifest["snapshot_path"])
    expected = {r["path"]:r for r in manifest["files"]}
    actual = {str(p.relative_to(snapshot)) for p in snapshot.rglob("*") if p.is_file()}
    require(actual == set(expected), "Predecessor snapshot membership changed")
    retained = 0
    for rel,row in expected.items():
        require(sha(snapshot/rel) == row["sha256"], f"Snapshot changed {rel}")
        if rel.startswith(("completions/","attempts/","failures/","selections/","plans/")) or rel in ("control_config.json","provenance/experiment.json","STOP.json","STAGE18B3_AR_ARX_BASELINE_REPORT.md"):
            require(sha(HERE/rel) == row["sha256"], f"Pre-existing evidence changed {rel}")
            retained += 1
    write(HERE/"recovery/predecessor_preservation.json", {"status":"PASS","snapshot_files":len(expected),"retained_evidence_files":retained,"pre_existing_valid_inner_completions":1400,"timestamp":now()})

def persistence_reference_mae(np, truth, persistence, timetrack):
    # Frozen TT baseline metric promotes operands to float64 before subtracting.
    # External raw windows already use float64: retain their original path.
    if timetrack:
        truth, persistence = truth.astype(float), persistence.astype(float)
    return np.mean(np.abs(truth-persistence),axis=0)

def verify_persistence_reference(np, record, resource, leads, pmae):
    for j,lead in enumerate(leads):
        previous = [m for m in record["persistence_metrics"] if m["resource"] == resource and m["lead"] == lead]
        require(len(previous) == 1 and np.isclose(previous[0]["mae"],pmae[j],rtol=1e-12,atol=0), "Frozen persistence MAE differs", "PERSISTENCE_REFERENCE_CONFLICT")

def transport_error(code, error):
    return RuntimeError(f"{code}: {error}")

def validate_completion(identity, value):
    require(value["identity"] == identity and value["status"] == "complete", "Completion identity differs")
    require(value["test_evaluations"] == int(identity["phase"] == "final"), "Test evaluation count differs")
    frozen.finite_primary(value["validation_score"] if identity["phase"] == "inner" else [m["mae"] for m in value["metrics"]])
    if identity["phase"] == "final":
        for kind in ("model","prediction"):
            p = Path(value[f"{kind}_path"])
            require(p.resolve().is_relative_to(HERE) and sha(p) == value[f"{kind}_sha256"], "Final artifact integrity differs")

def checked_data(e,spec,phase):
    frame,folds = e.data(spec["entity"],spec["L"]); fold = folds[spec["fold"]-1]
    require(fold.hashes == spec["split_hashes"], "Split differs", "SCIENTIFIC_SUPPORT_CONFLICT")
    scaler = e.scaler(frame,spec["entity"],getattr(fold,"inner_train" if phase=="inner" else "outer_train"),spec["L"])
    require(e.scaler_payload(scaler) == spec["scalers"][phase], "Scaler differs", "SCIENTIFIC_SUPPORT_CONFLICT")
    return frame,fold,scaler

def arrays(e,frame,spec,origins,scaler):
    X,y,raw = e.windows(frame,spec["entity"],spec["L"],origins)
    xs,ys = e.core.scale_windows(X,y,scaler)
    require(all(e.np.isfinite(a).all() for a in (X,y,xs,ys)), "Nonfinite data", "PRIMARY_NONFINITE_RESULT_CONFLICT")
    return X,y,xs,ys,raw

def inverse(e,pred,scaler,resource):
    require(e.np.isfinite(pred).all(), "Nonfinite scaled prediction", "PRIMARY_NONFINITE_RESULT_CONFLICT")
    native,_,unclipped = e.core.inverse_one(pred,scaler,resource,project=True) if e.tt else scaler.inverse_one(pred,resource,project=True)
    require(e.np.isfinite(native).all() and e.np.isfinite(unclipped).all(), "Nonfinite native prediction", "PRIMARY_NONFINITE_RESULT_CONFLICT")
    return native,unclipped

def inputs(xs, form, index):
    require(form in ("AR","ARX"), "Unknown formulation")
    return xs[:,:,index:index+1] if form == "AR" else xs

def choose(e,spec,form,resource,candidates):
    rows = [{"context_length":spec["L"],"alpha":c["identity"]["alpha"],"inner_validation_mae":c["validation_score"]} for c in candidates]
    require(len(rows) == 5 and {r["alpha"] for r in rows} == set(read(CONFIG)["alphas"]), "Alpha coverage differs")
    selected = selector()(e.pd.DataFrame(rows),"Ridge")
    return {"group_id":spec["group_id"],"formulation":form,"resource":resource,"L":spec["L"],"alpha":float(selected.alpha),"inner_validation_mae":float(selected.inner_validation_mae),"candidate_sources":[{"path":str(completion_path(c["identity"])),"sha256":sha(completion_path(c["identity"]))} for c in candidates],"test_accessed":False}

def selection_path(spec,form,resource):
    return HERE/f"selections/{spec['block']}/{spec['group_id']}_{form}_{resource}.json"

def model_state(e,model):
    state = {"coef":model.model.coef_,"intercept":e.np.asarray(model.model.intercept_),"feature_mean":model.scaler.mean_,"feature_scale":model.scaler.scale_,"feature_var":model.scaler.var_,"feature_samples":e.np.asarray(model.scaler.n_samples_seen_)}
    require(all(e.np.isfinite(v).all() for v in state.values()), "Nonfinite Ridge state", "PRIMARY_NONFINITE_RESULT_CONFLICT")
    return state

def reference_frame(e,spec,r,y,origins):
    require(sha(spec["reference_record"]) == spec["reference_record_sha256"] and sha(spec["reference_prediction"]) == spec["reference_prediction_sha256"], "Reference changed")
    old = e.pd.read_parquet(spec["reference_prediction"])
    old = old[old.resource.eq(r)].sort_values(["origin_index","lead"]).reset_index(drop=True)
    require(not old.duplicated(["origin_index","lead"]).any() and len(old) == y.size, "Duplicate/missing frozen prediction support")
    require(e.np.array_equal(old.y_true.to_numpy(),y.ravel()), "Native target differs", "SCIENTIFIC_SUPPORT_CONFLICT")
    require(e.np.array_equal(old.origin_index.to_numpy(),e.np.repeat(origins,len(e.leads))) and e.np.array_equal(old.lead.to_numpy(),e.np.tile(e.leads,len(origins))), "Origins/leads differ", "SCIENTIFIC_SUPPORT_CONFLICT")
    require(old.selected_L.eq(spec["L"]).all(), "Reference context differs")
    return old

def run_group(spec):
    e = ENGINE; np = e.np; current = None; tick = time.perf_counter()
    try:
        frame,fold,scaler = checked_data(e,spec,"inner")
        _,_,xt,yt,_ = arrays(e,frame,spec,fold.inner_train,scaler)
        _,yv,xv,_,_ = arrays(e,frame,spec,fold.inner_validation,scaler)
        selections = {}
        for i,r in enumerate(e.resources):
            for form in ("AR","ARX"):
                candidates = []
                for alpha in read(CONFIG)["alphas"]:
                    current = ident(spec,"inner",form,r,alpha); path = completion_path(current)
                    if path.exists():
                        value = read(path); validate_completion(current,value)
                    else:
                        begin(current); started = time.perf_counter()
                        model = ridge_class()(alpha).fit(inputs(xt,form,i),yt[:,i,:])
                        model_state(e,model)
                        native,_ = inverse(e,model.predict(inputs(xv,form,i)),scaler,r)
                        score = float(np.mean(np.abs(yv[:,i,:]-native)))
                        frozen.finite_primary(score)
                        value = {"status":"complete","identity":current,"validation_score":score,"test_evaluations":0,"elapsed_seconds":time.perf_counter()-started,"completed":now(),"feature_scaler_sha256":canonical({k:v.tolist() for k,v in model_state(e,model).items() if k.startswith("feature_")})}
                        write(path,value)
                    candidates.append(value)
                selected = choose(e,spec,form,r,candidates); path = selection_path(spec,form,r)
                if path.exists(): require(read(path) == selected, "Selection differs")
                else: write(path,selected)
                selections[form,r] = selected
        # Outer-test arrays are never constructed until all alpha selections are fixed.
        frame,fold,scaler = checked_data(e,spec,"final")
        _,_,xt,yt,_ = arrays(e,frame,spec,fold.outer_train,scaler)
        test = None
        for i,r in enumerate(e.resources):
            for form in ("AR","ARX"):
                selected = selections[form,r]
                current = ident(spec,"final",form,r,selected["alpha"],sha(selection_path(spec,form,r)))
                path = completion_path(current)
                if path.exists(): validate_completion(current,read(path)); continue
                begin(current); started = time.perf_counter()
                model = ridge_class()(selected["alpha"]).fit(inputs(xt,form,i),yt[:,i,:])
                state = model_state(e,model)
                if test is None: test = arrays(e,frame,spec,fold.outer_test,scaler)
                X,y,xs,_,_ = test
                scaled = model.predict(inputs(xs,form,i))  # one outer-test predict call
                native,unclipped = inverse(e,scaled,scaler,r)
                persistence = np.repeat(X[:,-1,i,None],len(e.leads),axis=1)
                mae = np.mean(np.abs(y[:,i,:]-native),axis=0)
                skill_denominator = np.mean(np.abs(y[:,i,:]-persistence),axis=0)
                pmae = persistence_reference_mae(np,y[:,i,:],persistence,e.tt)
                require(np.isfinite(mae).all() and np.isfinite(pmae).all(), "Nonfinite MAE", "PRIMARY_NONFINITE_RESULT_CONFLICT")
                old = reference_frame(e,spec,r,y[:,i,:],fold.outer_test)
                # Retain authenticated support/time columns only; no inherited stochastic identity.
                drop = [c for c in old if c in ("run_id","formulation","seed","selected_epoch","y_pred","y_pred_scaled","y_pred_unclipped")]
                pred = old.drop(columns=drop).copy()
                pred["run_id"] = current["run_id"]; pred["formulation"] = form; pred["alpha"] = selected["alpha"]
                pred["y_pred_scaled"] = scaled.ravel(); pred["y_pred"] = native.ravel(); pred["y_pred_unclipped"] = unclipped.ravel(); pred["persistence_prediction"] = persistence.ravel(); pred["label"] = RESULT_LABEL
                record = read(spec["reference_record"])
                verify_persistence_reference(np,record,r,e.leads,pmae)
                # Preserve the original skill metric arithmetic; TT's frozen helper
                # uses raw-window precision for its relative-skill denominator.
                metrics = [{"resource":r,"lead":int(lead),"n":len(y),"mae":float(mae[j]),"persistence_mae":float(pmae[j]),"persistence_skill":float(1-mae[j]/skill_denominator[j]) if skill_denominator[j]>0 else None,"persistence_skill_undefined_reason":None if skill_denominator[j]>0 else "zero persistence MAE denominator; raw division undefined/nonfinite"} for j,lead in enumerate(e.leads)]
                mpth = output(HERE/f"models/{e.block}/{current['run_id']}.npz")
                with mpth.with_suffix(".tmp").open("wb") as stream: np.savez_compressed(stream,**state)
                os.replace(mpth.with_suffix(".tmp"),mpth)
                ppth = HERE/f"predictions/{e.block}/{current['run_id']}.parquet"; parquet(ppth,pred)
                write(path,{"status":"complete","identity":current,"test_evaluations":1,"completed":now(),"elapsed_seconds":time.perf_counter()-started,"metrics":metrics,"source_scaler":spec["scalers"]["final"],"model_path":str(mpth),"model_sha256":sha(mpth),"prediction_path":str(ppth),"prediction_sha256":sha(ppth)})
        return {"group_id":spec["group_id"],"elapsed_seconds":time.perf_counter()-tick}
    except BaseException as exc:
        code = getattr(exc,"code","STAGE_18B3R_EXECUTION_FAILURE")
        write(HERE/f"recovery/failures/{spec['block']}/{current['run_id'] if current else spec['group_id']}.json", {"identity":current,"timestamp":now(),"code":code,"error":repr(exc),"traceback":traceback.format_exc()})
        # A built-in exception survives multiprocessing transport. Never mutate
        # the imported frozen two-argument Conflict class or its source file.
        raise transport_error(code,exc) from None

def run_block(block,workers):
    verify_seal(); plan = read(HERE/f"plans/{block}.json")
    for rel,h in plan["source_hashes"].items(): require(sha(ROOT/rel) == h, "Plan source differs")
    done = 0
    with mp.get_context("spawn").Pool(workers,initializer=init_worker,initargs=(block,)) as pool:
        for result in pool.imap_unordered(run_group,plan["groups"],chunksize=1):
            done += 1
            write(HERE/f"progress/{block}.json", {"completed_groups":done,"required_groups":len(plan["groups"]),"timestamp":now(),"last_group":result})
            print(f"PROGRESS {block} groups={done}/{len(plan['groups'])} seconds={result['elapsed_seconds']:.2f}",flush=True)

def audit_block(block):
    e = frozen.Engine(block); plan = read(HERE/f"plans/{block}.json")
    expected = {"inner":set(),"final":set()}; count = 0; undefined = 0
    for spec in plan["groups"]:
        checked_data(e,spec,"inner"); frame,fold,scaler = checked_data(e,spec,"final")
        X,y,_,_,_ = arrays(e,frame,spec,fold.outer_test,scaler)
        for i,r in enumerate(e.resources):
            for form in ("AR","ARX"):
                candidates = []
                for a in read(CONFIG)["alphas"]:
                    identity = ident(spec,"inner",form,r,a); value = read(completion_path(identity)); validate_completion(identity,value)
                    candidates.append(value); expected["inner"].add(identity["run_id"])
                sel = choose(e,spec,form,r,candidates); sp = selection_path(spec,form,r)
                require(read(sp) == sel, "Independent selection differs")
                identity = ident(spec,"final",form,r,sel["alpha"],sha(sp)); value = read(completion_path(identity)); validate_completion(identity,value)
                pred = e.pd.read_parquet(value["prediction_path"]).sort_values(["origin_index","lead"]).reset_index(drop=True)
                reference = reference_frame(e,spec,r,y[:,i,:],fold.outer_test)
                for c in ("resource",e.entity_key,"fold","origin_index","lead","target_index","support_hash","y_true","selected_L") + (("sample_id","origin_timestamp","target_timestamp") if e.tt else ("origin_timestamp_seconds","target_timestamp_seconds")):
                    require(np_equal(e,pred[c],reference[c]), f"Persisted support differs {c}")
                require("seed" not in pred and "selected_epoch" not in pred, "Artificial seed/epoch present")
                require(pred.formulation.eq(form).all() and pred.alpha.eq(sel["alpha"]).all() and pred.run_id.eq(identity["run_id"]).all(), "Prediction identity differs")
                require(e.np.isfinite(pred[["y_true","y_pred","y_pred_scaled","y_pred_unclipped","persistence_prediction"]].to_numpy()).all(), "Nonfinite persisted predictions")
                with e.np.load(value["model_path"],allow_pickle=False) as state:
                    require(all(e.np.isfinite(state[k]).all() for k in state.files), "Nonfinite model file")
                    require(state["coef"].shape == (len(e.leads),spec["L"]*(1 if form=="AR" else 4)), "Coefficient dimensions differ")
                require(len(value["metrics"]) == len(e.leads), "Metric coverage differs")
                persistence = e.np.repeat(X[:,-1,i,None],len(e.leads),axis=1)
                reference_pm = persistence_reference_mae(e.np,y[:,i,:],persistence,e.tt)
                skill_pm = e.np.mean(e.np.abs(y[:,i,:]-persistence),axis=0)
                verify_persistence_reference(e.np,read(spec["reference_record"]),r,e.leads,reference_pm)
                require(e.np.array_equal(pred.persistence_prediction.to_numpy(),persistence.ravel()), "Persisted persistence differs")
                for m in value["metrics"]:
                    p = pred[pred.lead.eq(m["lead"])]
                    j = list(e.leads).index(m["lead"])
                    mae = float(e.np.mean(e.np.abs(p.y_true-p.y_pred))); pm = float(reference_pm[j])
                    require(len(p) == m["n"] and e.np.isclose(mae,m["mae"],rtol=1e-12,atol=0) and e.np.isclose(pm,m["persistence_mae"],rtol=1e-12,atol=0), "Recomputed MAE differs")
                    if skill_pm[j] > 0: require(e.np.isclose(1-e.np.float64(mae)/skill_pm[j],m["persistence_skill"],rtol=1e-12,atol=1e-14), "Skill differs")
                    else:
                        require(m["persistence_skill"] is None and m["persistence_skill_undefined_reason"], "Undefined skill not explicit"); undefined += 1
                expected["final"].add(identity["run_id"]); count += len(value["metrics"])
    for phase in expected:
        paths = list((HERE/f"completions/{phase}/{block}").glob("*.json"))
        require({p.stem for p in paths} == expected[phase] and len(paths) == len(expected[phase]), "Duplicate/missing completion", "CONTROL_COMPLETION_DUPLICATION_CONFLICT")
        require({p.stem for p in (HERE/f"attempts/{phase}/{block}").glob("*.json")} == expected[phase], "Attempt coverage differs")
    require(len(expected["inner"]) == plan["inner"] and len(expected["final"]) == plan["final"] and count == plan["metric_rows"], "Plan coverage differs")
    write(HERE/f"validation/full_audit_{block}.json", {"status":"PASS","inner":len(expected["inner"]),"final":len(expected["final"]),"metric_rows":count,"duplicates":0,"undefined_persistence_skills":undefined,"support_cohort_context_scaler":"PASS","finite_predictions_primary_MAE":"PASS","timestamp":now()})

def np_equal(e,a,b): return e.np.array_equal(a.to_numpy(),b.to_numpy())

def child(action,block=None,workers=4):
    args = [sys.executable,"-B",str(Path(__file__)),action]
    if block: args += ["--block",block]
    if action == "run-block": args += ["--workers",str(workers)]
    subprocess.run(args,cwd=ROOT,check=True)

def prepare():
    verify_refs(); require(not (HERE/"provenance/experiment.json").exists(), "Already sealed")
    require(read(HERE/"validation/tests.json")["status"] == "PASS", "Tests required")
    require(read(B2/"validation/final_handoff.json")["status"] == "STAGE_18B2_PASS", "B2 not terminal")
    preserve(capture=True)
    for block in read(CONFIG)["blocks"]: child("plan-block",block)
    plans = [read(HERE/f"plans/{b}.json") for b in read(CONFIG)["blocks"]]
    require(sum(p["inner"] for p in plans) == 36400 and sum(p["final"] for p in plans) == 7280 and sum(p["metric_rows"] for p in plans) == 37240, "Expected counts differ")
    import numpy, pandas, sklearn, scipy
    write(HERE/"provenance/experiment.json", {"label":LABEL,"timestamp":now(),"configuration_sha256":sha(CONFIG),"source_hashes":source_hashes(),"plan_hashes":{p["block"]:sha(HERE/f"plans/{p['block']}.json") for p in plans},"refs":frozen.refs(),"versions":{m.__name__:m.__version__ for m in (numpy,pandas,sklearn,scipy)},"seed_repetitions":0})
    write(HERE/"validation/preflight.json", {"status":"PASS","groups":sum(len(p["groups"]) for p in plans),"inner":36400,"final":7280,"metric_rows":37240,"timestamp":now()})
    print("STAGE18B3_PREFLIGHT_PASS",flush=True)

def run_all(workers):
    verify_refs(); verify_seal()
    verify_predecessor()
    approved = authorised_recoveries()
    historical_audit_stop = (HERE/"recovery/successor_audit_fix.json").exists() and sha(HERE/"recovery/STOP.json") == read(HERE/"recovery/successor_audit_fix.json")["resolved_audit_stop_sha256"]
    require((not (HERE/"recovery/STOP.json").exists() or historical_audit_stop) and not (HERE/"recovery/current_STOP.json").exists() and not unresolved_failures(True), "Unresolved failure; no silent retry", "UNRESOLVED_FAILURE_CONFLICT")
    for phase in ("inner","final"):
        for p in (HERE/f"attempts/{phase}").rglob("*.json"):
            require((HERE/f"completions/{phase}/{p.parent.name}/{p.name}").exists() or p.stem in approved, f"Unresolved interrupted attempt {p}", "UNRESOLVED_ATTEMPT_CONFLICT")
    for p in (HERE/"recovery/attempts").glob("*.json"):
        require(completion_path(read(p)["identity"]).exists(), f"Interrupted recovery attempt {p}", "UNRESOLVED_ATTEMPT_CONFLICT")
    for b in read(CONFIG)["blocks"]:
        child("run-block",b,workers); child("audit-block",b)
    require(not unresolved_failures(), "Recovery unresolved")
    verify_predecessor(); preserve(); verify_refs(); verify_seal()
    subprocess.run([sys.executable,"-B",str(HERE/"analyse_linear_control.py")],cwd=ROOT,check=True)

def main():
    parser = argparse.ArgumentParser(); parser.add_argument("action",choices=["prepare","run","plan-block","run-block","audit-block","verify"])
    parser.add_argument("--block",choices=list(frozen.FROZEN)); parser.add_argument("--workers",type=int,default=4)
    a = parser.parse_args(); lock = None
    if a.action in ("prepare","run"):
        lock = output(HERE/"runtime.lock").open("a")
        try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError: raise frozen.Conflict("ACTIVE_PROCESS_CONFLICT","Do not duplicate runner")
    try:
        if a.action == "prepare": prepare()
        elif a.action == "run": run_all(a.workers)
        elif a.action == "plan-block": plan_block(a.block)
        elif a.action == "run-block": run_block(a.block,a.workers)
        elif a.action == "audit-block": audit_block(a.block)
        else: verify_refs(); verify_seal(); preserve()
    except BaseException as exc:
        if a.action in ("prepare","run"):
            stop = HERE/"recovery/STOP.json"
            if stop.exists(): stop = HERE/"recovery/current_STOP.json"
            write(stop, {"status":getattr(exc,"code","STAGE_18B3R_BLOCKED"),"timestamp":now(),"error":repr(exc),"traceback":traceback.format_exc()})
        raise

if __name__ == "__main__": main()
