"""Trace the existing TimeTrack throughput peak; no model inference."""
import pandas as pd
from audit_synthesis import ROOT,OUT,read,write,sha

def main():
    checks=pd.read_csv(OUT/"timetrack_throughput_prediction_checks.csv")
    top=checks.loc[checks.prediction_max.idxmax()]
    path=ROOT/f"review_revision/experiments/ar_arx_baseline/predictions/TimeTrack/{top.run_id}.parquet"
    frame=pd.read_parquet(path);peak=frame.loc[frame.y_pred.idxmax()]
    per_lead=frame.assign(error=(frame.y_true-frame.y_pred).abs()).groupby("lead").agg(mae=("error","mean"),max_prediction=("y_pred","max")).reset_index()
    write(OUT/"timetrack_throughput_peak.json",{"source_path":str(path.relative_to(ROOT)),"source_sha256":sha(path),"machine":str(top.machine),"fold":int(top.fold),"formulation":str(top.formulation),"origin_index":int(peak.origin_index),"lead":int(peak.lead),"target_value":float(peak.y_true),"prediction":float(peak.y_pred),"scaled_prediction":float(peak.y_pred_scaled),"origin_timestamp_as_stored":str(peak.origin_timestamp),"target_timestamp_as_stored":str(peak.target_timestamp),"per_lead":per_lead.to_dict("records"),"training":0,"model_inference":0})

if __name__=="__main__":main()
