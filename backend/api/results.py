from backend.services.config_services import attach_uploads_to_config, latest_config_path, read_config, write_config
from backend.services.utils.detect_metric_schema import detect_all_result_schemas
from backend.core.settings import BASE_DIR, STORAGE_DIR, UPLOAD_DIR, CONFIG_DIR, RESULTS_DIR, RUN_DIR, REGISTRY_DIR
from fastapi import APIRouter, HTTPException, Query, Body, UploadFile, File, Form
from backend.services.result_services import render_report_to_pdf, load_plugin_registry, compute_total_score
from fastapi.responses import JSONResponse, FileResponse
from backend.schemas.config import ConfigIn
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from pathlib import Path
import numpy as np
import pandas as pd
from datetime import datetime
import logging
import uuid
import json
import os
import re

logger = logging.getLogger("uvicorn.error")
router = APIRouter(tags=["results"])

#GET: metrics to be displayed in dashboard
@router.get("/results/plugins")
def get_plugins():
    path = latest_config_path()
    if not path:
        return {"config_file": None, "plugins": []}
    cfg = json.loads(path.read_text(encoding="utf-8"))
    return {
        "config_file": path.name,
        "plugins": cfg.get("plugins", [])
    }

#GET: values to be displayed for the dashboard + metadata for report generation
@router.get("/results/values_to_display")
def values_to_display():
    cfg = latest_config_path()
    if not cfg:
        raise HTTPException(status_code=404, detail="No config files found")

    run_id = cfg.stem    
    cfg = json.loads(cfg.read_text(encoding="utf-8"))

    dataset_name = ""
    x_test = (cfg.get("datasets") or {}).get("X_test")
        
    if x_test:
        fname = os.path.basename(str(x_test))
        parts = fname.split("__")
        if len(parts) >= 3:
            dataset_name = parts[-1]
            if dataset_name.lower().endswith(".csv"):
                dataset_name = dataset_name[:-4]  

    evaluation_date = datetime.now().strftime("%B %d, %Y")
    logger.info(f"dataset= {dataset_name}")
    
    res_path = RESULTS_DIR / f"{run_id}.json"

    if res_path.exists():
        results = json.loads(res_path.read_text(encoding="utf-8"))  
        return {
            "run_id": run_id, 
            "results": results, 
            "evaluation_date": evaluation_date, 
            "dataset_name": dataset_name, 
        }

    raise HTTPException(status_code=404, detail="No results found matching any config")

#GET: returns the schema identified for each metric
@router.get("/results/result_schemas")
def get_result_schemas(run_id: str | None = Query(default=None)):
    if run_id is None:
        cfg = latest_config_path()
        if not cfg:
            raise HTTPException(status_code=404, detail="No config files found")
        run_id = cfg.stem

    schemas_path = RESULTS_DIR / f"{run_id}_schemas.json"
    if not schemas_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Schemas file not found for run_id={run_id}. Expected: {schemas_path.name}"
        )

    return json.loads(schemas_path.read_text(encoding="utf-8"))


# --- PAYLOAD AGGIORNATO (Executive Revision) ---
class WeightsSavePayload(BaseModel):
    run_id: str 
    group: Optional[str] = None 
    metric: str 

    user_weight: Optional[float] = None
    user_justification: Optional[str] = ""
    
    weights: Dict[str, float] = Field(default_factory=dict)           
    justifications: Dict[str, str] = Field(default_factory=dict)    

    schema_type_report: Optional[str] = None
    context_report: Optional[Dict[str, Any]] = None
    summary_report: Optional[Dict[str, Any]] = None

    # NUOVI CAMPI EXECUTIVE
    gravity: Optional[int] = 0
    reversibility: Optional[bool] = False
    executiveData: Optional[Dict[str, Any]] = Field(default_factory=dict)

#POST: save weights, justification and report content
@router.post("/results/save_weights")
def save_weights(payload: WeightsSavePayload):
    run_id = payload.run_id
    group = payload.group
    metric = payload.metric

    plugin_registry = load_plugin_registry(REGISTRY_DIR)
    metric_meta = plugin_registry.get(metric, {})
    metric_description = metric_meta.get("description") 
    metric_right = metric_meta.get("right")

    source_path = RESULTS_DIR / f"{run_id}.json"
    report_path = RESULTS_DIR / f"{run_id}_report.json"

    if not source_path.exists():
        raise HTTPException(status_code=404, detail=f"Results file not found for run_id={run_id}")

    if report_path.exists():
        report_raw = json.loads(report_path.read_text(encoding="utf-8"))
    else:
        report_raw = json.loads(source_path.read_text(encoding="utf-8"))

    report_results = report_raw.get("results") if isinstance(report_raw, dict) and "results" in report_raw else report_raw

    if metric not in report_results or not isinstance(report_results[metric], dict):
        raise HTTPException(status_code=400, detail=f"Metric '{metric}' not found in results/report")

    metric_obj = report_results[metric] 

    # --------------------
    # CASE A: GLOBAL METRIC 
    # --------------------
    if payload.user_weight is not None and "(global)" in metric_obj:
        w = payload.user_weight
        just = (payload.user_justification).strip()

        if not isinstance(metric_obj["(global)"], dict):
            if isinstance(metric_obj["(global)"], (int, float)):
                metric_obj["(global)"] = {"value": metric_obj["(global)"]}
            else:
                metric_obj["(global)"] = {}

        metric_value = (payload.context_report or {}).get("final_score")
        final_score = compute_total_score(metric_value, w)
        
        if final_score is not None:
            metric_obj["(global)"]["total_score_report"] = final_score
        
        metric_obj["(global)"]["metric_report"] = metric
        if w is not None: 
            metric_obj["(global)"]["user_weight_report"] = w
        if group:
            metric_obj["(global)"]["group_report"] = group
        if metric_description:
            metric_obj["(global)"]["metric_description_report"] = metric_description
        if metric_right:
            metric_obj["(global)"]["metric_right_report"] = metric_right 
        if just:
            metric_obj["(global)"]["user_justification_report"] = just
        if payload.schema_type_report is not None:
            metric_obj["(global)"]["schema_type_report"] = payload.schema_type_report
        if payload.context_report is not None:
            metric_obj["(global)"]["context_report"] = payload.context_report

        # CAMPI EXECUTIVE
        metric_obj["(global)"]["gravity_report"] = payload.gravity
        metric_obj["(global)"]["reversibility_report"] = payload.reversibility

        report_path.write_text(json.dumps(report_raw, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok": True, "mode": "global", "run_id": run_id}

    # --------------------
    # CASE B: METRIC-LEVEL 
    # --------------------
    if payload.user_weight is not None:
        w = payload.user_weight
        just = (payload.user_justification or "").strip()

        metric_value = (payload.context_report or {}).get("final_score")
        final_score = compute_total_score(metric_value, w)
        
        if final_score is not None:
            metric_obj["total_score_report"] = final_score

        metric_obj["metric_report"] = metric
        if w is not None: 
            metric_obj["user_weight_report"] = w
        if group:
            metric_obj["right_report"] = group
        if metric_description:
            metric_obj["metric_description_report"] = metric_description 
        if metric_right:
            metric_obj["metric_right_report"] = metric_right 
        if just:
            metric_obj["user_justification_report"] = just
        if payload.schema_type_report is not None:
            metric_obj["schema_type_report"] = payload.schema_type_report
        if payload.context_report is not None:
            metric_obj["context_report"] = payload.context_report

        # CAMPI EXECUTIVE
        metric_obj["gravity_report"] = payload.gravity
        metric_obj["reversibility_report"] = payload.reversibility

        report_path.write_text(json.dumps(report_raw, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok": True, "mode": "metric", "run_id": run_id}

    # --------------------
    # CASE C: FEATURE-LEVEL 
    # --------------------
    if payload.weights:
        for feature, w_raw in payload.weights.items():
            w = w_raw
            just = (payload.justifications.get(feature) or "").strip()

            if feature not in metric_obj or not isinstance(metric_obj[feature], dict):
                if isinstance(metric_obj.get(feature), (int, float)):
                    metric_obj[feature] = {"value": metric_obj[feature]}
                else:
                    metric_obj[feature] = {}

            metric_value = ((payload.summary_report or {}).get(feature, {}).get("Final Score")
                            or (payload.context_report or {}).get(feature, {}).get("Final Score")
                            or ((payload.context_report or {}).get(feature, {}).get("value", 0)*10)
            )

            final_score = compute_total_score(metric_value, w)
            if final_score is not None:
                metric_obj[feature]["total_score_report"] = final_score

            metric_obj[feature]["metric_report"] = metric
            metric_obj[feature]["user_weight_report"] = w
            if group:
                metric_obj[feature]["group_report"] = group
            if metric_description:
                metric_obj[feature]["metric_description_report"] = metric_description 
            if metric_right:
                metric_obj[feature]["metric_right_report"] = metric_right 
            if just:
                metric_obj[feature]["user_justification_report"] = just
        
            if payload.schema_type_report is not None:
                metric_obj[feature]["schema_type_report"] = payload.schema_type_report
            
            if payload.context_report is not None:
                if feature in payload.context_report and isinstance(payload.context_report.get(feature), dict):
                    metric_obj[feature]["context_report"] = payload.context_report[feature]
                else:
                    metric_obj[feature]["context_report"] = payload.context_report

            if payload.summary_report is not None:
                if feature in payload.summary_report and isinstance(payload.summary_report.get(feature), dict):
                    metric_obj[feature]["summary_report"] = payload.summary_report[feature]
                else:
                    metric_obj[feature]["summary_report"] = payload.summary_report

            # CAMPI EXECUTIVE FEATURE-LEVEL
            exec_info = payload.executiveData.get(feature, {})
            metric_obj[feature]["gravity_report"] = exec_info.get("gravity", payload.gravity)
            metric_obj[feature]["reversibility_report"] = exec_info.get("reversibility", payload.reversibility)

        report_path.write_text(json.dumps(report_raw, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok": True, "mode": "feature", "run_id": run_id}

    raise HTTPException(status_code=400, detail="No weights provided (metric-level or feature-level).")


# --- NUOVO ENDPOINT: DOMAIN CONFIG (REVERSIBILITY) ---
class DomainConfigPayload(BaseModel):
    run_id: str
    domain: str
    reversibility: bool = False

@router.post("/results/save_domain_config")
def save_domain_config(payload: DomainConfigPayload):
    report_path = RESULTS_DIR / f"{payload.run_id}_report.json"
    source_path = RESULTS_DIR / f"{payload.run_id}.json"
    
    if report_path.exists():
        report_raw = json.loads(report_path.read_text(encoding="utf-8"))
    elif source_path.exists():
        report_raw = json.loads(source_path.read_text(encoding="utf-8"))
    else:
        raise HTTPException(status_code=404, detail="Results not found")

    if "domain_configs" not in report_raw:
        report_raw["domain_configs"] = {}
        
    report_raw["domain_configs"][payload.domain] = {
        "reversibility": payload.reversibility
    }
    
    report_path.write_text(json.dumps(report_raw, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"status": "success", "domain": payload.domain, "reversibility": payload.reversibility}


#GET: take the _report.json to generate the final PDF
#GET: take the _report.json to generate the final PDF
@router.get("/results/{run_id}_report")
def get_report_json(run_id: str):
    report_path = RESULTS_DIR / f"{run_id}_report.json"

    if not report_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Report file not found for run_id={run_id}. Expected: {report_path.name}"
        )

    report_data = json.loads(report_path.read_text(encoding="utf-8"))
    
    # --- LA MAGIA DI INIEZIONE DATI ---
    # Prendiamo le configurazioni dei domini e le iniettiamo in ogni metrica
    domain_configs = report_data.get("domain_configs", {})
    results = report_data.get("results", {})

    for metric_key, metric_data in results.items():
        # Cerchiamo il gruppo (dominio) della metrica. 
        # Di solito è nel campo 'group_report'
        group = metric_data.get("group_report")
        if not group and "(global)" in metric_data:
            group = metric_data["(global)"].get("group_report")
            
        # Se abbiamo trovato il dominio, cerchiamo se ha una reversibilità salvata
        if group and group in domain_configs:
            rev = domain_configs[group].get("reversibility", False)
            # Iniettiamo il dato nella metrica in modo che il frontend/PDF lo veda!
            metric_data["reversibility_report"] = rev
            if "(global)" in metric_data:
                metric_data["(global)"]["reversibility_report"] = rev

    return report_data

#PDF GENERATION
class GeneratePDFRequest(BaseModel):
    run_id: str

@router.post("/results/generate_pdf")
def generate_pdf(req: GeneratePDFRequest):
    run_id = (req.run_id or "").strip()
    if not run_id:
        raise HTTPException(status_code=400, detail="run_id is required")

    frontend_base_url = os.getenv("FRONTEND_BASE_URL", "http://localhost:5173")

    out_dir = Path("backend/storage/reports")
    out_path = out_dir / f"{run_id}_report.pdf"

    try:
        render_report_to_pdf(
            run_id=run_id,
            frontend_base_url=frontend_base_url,
            out_path=out_path,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {e}")

    return FileResponse(
        path=str(out_path),
        media_type="application/pdf",
        filename=f"final_evaluation_report_{run_id}.pdf",
    )