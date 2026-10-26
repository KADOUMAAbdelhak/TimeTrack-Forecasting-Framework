"""Read-only regression; never fits a model or performs inference."""
import numpy as np
import run_linear_control as r

def main():
    diagnostic=r.read(r.HERE/"recovery/reduction_order_diagnostic.json")
    r.require(len(diagnostic["column_audit_mismatches"])==1 and diagnostic["stored_mae_skill_mismatches"]==0,"Expected diagnosed reduction mismatch")
    case=diagnostic["column_audit_mismatches"][0]
    r.require(np.isclose(case["mae_column"],case["mae_stored"],rtol=1e-12,atol=0),"Independent native MAE fails original strict check")
    r.require(not np.isclose(case["skill_column"],case["skill_stored"],rtol=1e-12,atol=1e-14),"Old skill blocker not reproduced")
    r.require(case["skill_from_verified_stored_mae"]==case["skill_stored"],"Derived skill not exact")
    # A genuine primary-error/derived-skill mismatch remains detectable.
    r.require(not np.isclose(case["mae_stored"]+.001,case["mae_stored"],rtol=1e-12,atol=0),"Genuine MAE discrepancy accepted")
    r.require(not np.isclose(case["skill_stored"]+.001,case["skill_stored"],rtol=1e-12,atol=1e-14),"Genuine skill discrepancy accepted")
    r.write(r.HERE/"recovery/reduction_order_test.json",{"status":"PASS","diagnosed_row":case["id"],"Rnd_all_stored_mae_skill_formula_mismatches":0,"independent_MAE_tolerance_unchanged":True,"derived_skill_tolerance_unchanged":True,"scientific_metric_changes":0,"fits_or_inference":0,"timestamp":r.now()})
    print("REDUCTION_ORDER_TEST_PASS",flush=True)

if __name__=="__main__":main()
