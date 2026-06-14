from backend.services.config_services import attach_uploads_to_config, latest_config_path, read_config, write_config
from backend.services.utils.detect_metric_schema import detect_all_result_schemas
from backend.core.settings import BASE_DIR, STORAGE_DIR, UPLOAD_DIR, CONFIG_DIR, RESULTS_DIR, RUN_DIR, REGISTRY_DIR
from fastapi import APIRouter, HTTPException, Query, Body, UploadFile, File, Form
from backend.services.result_services import render_report_to_pdf, load_plugin_registry
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
import shutil
import math

ACTIVE_RUN_ID = None

def clean_nans(obj):
    if isinstance(obj, dict):
        return {k: clean_nans(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_nans(v) for v in obj]
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
    return obj

def calculate_fria_risk(likelihood, gravity, is_reversible):
    if likelihood is None: return None
    try: l_val = float(likelihood)
    except (ValueError, TypeError): return None
    g_val = float(gravity) if gravity is not None else 0.0
    risk = l_val * g_val
    if is_reversible is False:
        risk = risk * 1.5 
    return round(risk, 3)


def strip_report_fields(d):
    """Rimuove le vecchie modifiche dai file pre-compilati per partire da zero."""
    if isinstance(d, dict):
        # Elenco delle chiavi "vitali" da NON cancellare mai
        keep_keys = [
            "metric_description_report", 
            "metric_right_report", 
            "right_report", 
            "schema_type_report",
            "context_report",
            "summary_report"
        ]
        
        # Cancella solo le cose che finiscono in _report MA che non sono nella lista qui sopra
        keys_to_delete = [
            k for k in d.keys() 
            if (k.endswith("_report") and k not in keep_keys) or k in ["gravity", "reversibility", "user_weight"]
        ]
        
        for k in keys_to_delete:
            del d[k]
        for v in d.values():
            strip_report_fields(v)
    elif isinstance(d, list):
        for item in d:
            strip_report_fields(item)
    return d


logger = logging.getLogger("uvicorn.error")
router = APIRouter(tags=["results"])

@router.get("/results/plugins")
def get_plugins():
    path = latest_config_path()
    if not path:
        return {"config_file": None, "plugins": []}
    cfg = json.loads(path.read_text(encoding="utf-8"))
    return {"config_file": path.name, "plugins": cfg.get("plugins", [])}

@router.get("/results/values_to_display")
def values_to_display(run_id: Optional[str] = Query(None), session_id: Optional[str] = Query(None)): # <-- AGGIUNTO SESSION_ID QUI
    global ACTIVE_RUN_ID
    if run_id and run_id.strip(): ACTIVE_RUN_ID = run_id.strip()
    current_id = ACTIVE_RUN_ID

    if not current_id:
        cfg = latest_config_path()
        if not cfg: raise HTTPException(status_code=404, detail="Nessun dataset trovato.")
        current_id = cfg.stem
        ACTIVE_RUN_ID = current_id

    dataset_names_map = {
        "Bank_case2": "Algoritmo credit score 2",
    }
    fallback_name = current_id.replace("_", " ").title()
    dataset_name = dataset_names_map.get(current_id, f"Dataset: {fallback_name}")
    evaluation_date = datetime.now().strftime("%B %d, %Y")
    
    # ---> FIX FONDAMENTALE: Legge il file del tuo utente, non quello vuoto! <---
    if session_id:
        report_path = RESULTS_DIR / f"{current_id}_report_{session_id}.json"
    else:
        report_path = RESULTS_DIR / f"{current_id}_report.json"
        
    res_path = RESULTS_DIR / f"{current_id}.json"

    if report_path.exists():
        data = json.loads(report_path.read_text(encoding="utf-8"))
        results = data.get("results", data)
    elif res_path.exists():
        results = json.loads(res_path.read_text(encoding="utf-8"))
    else:
        raise HTTPException(status_code=404, detail=f"File {current_id}.json non trovato!")

    return {
        "run_id": current_id, 
        "results": clean_nans(results), 
        "evaluation_date": evaluation_date, 
        "dataset_name": dataset_name, 
    }

@router.get("/results/result_schemas")
def get_result_schemas(run_id: Optional[str] = Query(None)):
    global ACTIVE_RUN_ID
    if run_id and run_id.strip(): ACTIVE_RUN_ID = run_id.strip()
    current_id = ACTIVE_RUN_ID

    if not current_id:
        cfg = latest_config_path()
        if not cfg: raise HTTPException(status_code=404)
        current_id = cfg.stem
        ACTIVE_RUN_ID = current_id

    schemas_path = RESULTS_DIR / f"{current_id}_schemas.json"
    if not schemas_path.exists():
        raise HTTPException(status_code=404, detail=f"File degli schemi non trovato per {current_id}")
    return json.loads(schemas_path.read_text(encoding="utf-8"))

class WeightsSavePayload(BaseModel):
    run_id: str
    session_id:str 
    group: Optional[str] = None 
    metric: str 
    user_weight: Optional[float] = None
    user_justification: Optional[str] = ""
    weights: Dict[str, float] = Field(default_factory=dict)           
    justifications: Dict[str, str] = Field(default_factory=dict)    
    schema_type_report: Optional[str] = None
    context_report: Optional[Dict[str, Any]] = None
    summary_report: Optional[Dict[str, Any]] = None
    gravity: Optional[float] = 0.0
    reversibility: Optional[bool] = False
    reversibilityByLabel: Dict[str, bool] = Field(default_factory=dict)
    executiveData: Optional[Dict[str, Any]] = Field(default_factory=dict)

@router.post("/results/save_weights")
def save_weights(payload: WeightsSavePayload):
    from backend.services.result_services import load_plugin_registry
    run_id = payload.run_id
    metric = payload.metric
    group = payload.group

    plugin_registry = load_plugin_registry(REGISTRY_DIR)
    metric_meta = plugin_registry.get(metric, {})
    metric_description = metric_meta.get("description") 
    metric_right = metric_meta.get("right")

    source_path = RESULTS_DIR / f"{run_id}.json"
    report_path = RESULTS_DIR / f"{payload.run_id}_report_{payload.session_id}.json"

    if not source_path.exists():
        raise HTTPException(status_code=404, detail=f"Results file not found")

    if report_path.exists():
        report_raw = json.loads(report_path.read_text(encoding="utf-8"))
    else:
        report_raw = json.loads(source_path.read_text(encoding="utf-8"))
        #funzione di pulizia
        report_raw = strip_report_fields(report_raw)

    report_results = report_raw.get("results") if isinstance(report_raw, dict) and "results" in report_raw else report_raw
    if metric not in report_results:
        raise HTTPException(status_code=400, detail=f"Metric not found")

    metric_obj = report_results[metric] 

    if payload.user_weight is not None and "(global)" in metric_obj:
        w = payload.user_weight
        if not isinstance(metric_obj["(global)"], dict):
            metric_obj["(global)"] = {"value": metric_obj["(global)"]}
        metric_value = (payload.context_report or {}).get("final_score")
        final_score = calculate_fria_risk(metric_value, payload.gravity, payload.reversibility)
        
        if final_score is not None: metric_obj["(global)"]["total_score_report"] = final_score
        
        metric_obj["(global)"]["metric_report"] = metric
        metric_obj["(global)"]["user_weight_report"] = w
        metric_obj["(global)"]["user_weight"] = w  # Sicurezza per l'interfaccia
        metric_obj["(global)"]["gravity_report"] = payload.gravity
        metric_obj["(global)"]["gravity"] = payload.gravity # Sicurezza per l'interfaccia
        metric_obj["(global)"]["reversibility_report"] = payload.reversibility
        metric_obj["(global)"]["user_justification_report"] = payload.user_justification

        report_path.write_text(json.dumps(report_raw, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok": True, "mode": "global"}

    if payload.user_weight is not None:
        w = payload.user_weight
        metric_value = (payload.context_report or {}).get("final_score")
        final_score = calculate_fria_risk(metric_value, payload.gravity, payload.reversibility)
        
        if final_score is not None: metric_obj["total_score_report"] = final_score

        metric_obj["user_weight_report"] = w
        metric_obj["user_weight"] = w
        metric_obj["gravity_report"] = payload.gravity
        metric_obj["gravity"] = payload.gravity
        metric_obj["reversibility_report"] = payload.reversibility
        metric_obj["user_justification_report"] = payload.user_justification

        report_path.write_text(json.dumps(report_raw, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok": True, "mode": "metric"}

    if payload.weights:
        for feature, w_raw in payload.weights.items():
            w = w_raw
            feat_rev = payload.reversibilityByLabel.get(feature, payload.reversibility)
            if feature not in metric_obj or not isinstance(metric_obj[feature], dict):
                metric_obj[feature] = {}
            metric_obj[feature]["user_weight_report"] = w
            metric_obj[feature]["user_weight"] = w
            metric_obj[feature]["gravity_report"] = w
            metric_obj[feature]["gravity"] = w
            metric_obj[feature]["reversibility_report"] = feat_rev
            metric_obj[feature]["user_justification_report"] = payload.justifications.get(feature, "")
        report_path.write_text(json.dumps(report_raw, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok": True, "mode": "feature"}

    raise HTTPException(status_code=400, detail="No weights provided.")

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
        raise HTTPException(status_code=404)

    if "domain_configs" not in report_raw: report_raw["domain_configs"] = {}
    report_raw["domain_configs"][payload.domain] = {"reversibility": payload.reversibility}
    report_path.write_text(json.dumps(report_raw, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"status": "success"}


from fastapi import Query, HTTPException

@router.get("/results/{run_id}_report")
def get_report_json(run_id: str, session_id: str = Query(None)):
    # 1. Determina quale file cercare (con o senza session_id)
    if session_id:
        report_path = RESULTS_DIR / f"{run_id}_report_{session_id}.json"
    else:
        report_path = RESULTS_DIR / f"{run_id}_report.json"

    # 2. SE IL REPORT NON ESISTE ANCORA (Nuova sessione o file cancellato)
    if not report_path.exists(): 
        # Cerca il file base originale!
        base_path = RESULTS_DIR / f"{run_id}.json"
        if not base_path.exists():
            raise HTTPException(status_code=404, detail=f"File base {run_id}.json non trovato!")
        
        # Legge il file base e lo "pulisce" al volo usando la funzione che abbiamo sistemato prima
        report_data = json.loads(base_path.read_text(encoding="utf-8"))
        report_data = strip_report_fields(report_data)
    else:
        # Se il report della sessione esiste, legge quello
        report_data = json.loads(report_path.read_text(encoding="utf-8"))

    results = report_data.get("results", report_data)

    privacy_list = ["anonymity_set_size", "k_anonymity", "l_diversity", "mutual_information_metric", "t_closeness"]
    fairness_list = ["conditional_statistical_parity", "conditional_use_accuracy_equality", "demographic_parity", "disparate_impact", "equal_opportunity", "equalized_odds_difference", "overall_accuracy_equality", "predictive_parity"]

    # Funzione helper che calcola il punteggio al volo
    def fix_node(node, metric_name):
        if not isinstance(node, dict): return
        
        # 1. Assegna Dominio
        if not node.get("metric_right_report"):
            node["metric_right_report"] = "Privacy" if metric_name in privacy_list else "Non Discrimination" if metric_name in fairness_list else "Other"

        # 2. Normalizzazione Reversibilità
        rev_val = node.get("reversibility_report")
        is_rev = False
        if isinstance(rev_val, bool): is_rev = rev_val
        elif isinstance(rev_val, str): is_rev = rev_val.lower() == "yes"
        node["reversibility"] = is_rev
        node["reversibility_report"] = is_rev

        # 3. Calcolo rischio
        likelihood = node.get("final_score")
        if likelihood is None and "context_report" in node:
            likelihood = node["context_report"].get("final_score")
        
        gravity = node.get("gravity_report", 0)
        
        if likelihood is not None:
            node["total_score_report"] = calculate_fria_risk(likelihood, gravity, is_rev)

    if isinstance(results, dict):
        for metric_key, metric_data in results.items():
            if not isinstance(metric_data, dict): continue
            
            is_nested = False
            for sub_key, sub_val in metric_data.items():
                if isinstance(sub_val, dict) and ("metric" in sub_val or "status" in sub_val):
                    fix_node(sub_val, metric_key)
                    is_nested = True
            
            if not is_nested:
                fix_node(metric_data, metric_key)
            else:
                fix_node(metric_data, metric_key)

    return clean_nans(report_data)

'''
@router.get("/results/{run_id}_report")
def get_report_json(run_id: str):
    report_path = RESULTS_DIR / f"{run_id}_report.json"
    if not report_path.exists(): 
        raise HTTPException(status_code=404, detail="Report non trovato")

    report_data = json.loads(report_path.read_text(encoding="utf-8"))
    results = report_data.get("results", report_data)

    privacy_list = ["anonymity_set_size", "k_anonymity", "l_diversity", "mutual_information_metric", "t_closeness"]
    fairness_list = ["conditional_statistical_parity", "conditional_use_accuracy_equality", "demographic_parity", "disparate_impact", "equal_opportunity", "equalized_odds_difference", "overall_accuracy_equality", "predictive_parity"]

    # Funzione helper per sistemare un "nodo" (principale o nidificato)
    def fix_node(node, metric_name):
        if not isinstance(node, dict): return
        
        # 1. Assegna il Dominio Corretto
        if not node.get("metric_right_report"):
            node["metric_right_report"] = "Privacy" if metric_name in privacy_list else "Non Discrimination" if metric_name in fairness_list else "Other"

        # 2. Descrizione di Default
        if not node.get("metric_description_report"):
            node["metric_description_report"] = "Detailed analysis of the metric results for the specific feature identified."

        # 3. Correzione testo giustificazione di default
        old_text = "Since no weight has been assigned, the default weight 5 has been used"
        new_text = "Since no weight has been assigned, the gravity is set to low"
        if node.get("justification_report") == old_text:
            node["justification_report"] = new_text
        if node.get("user_justification_report") == old_text:
            node["user_justification_report"] = new_text

        # 4. Normalizzazione Reversibilità
        rev_val = node.get("reversibility_report")
        is_rev = False
        if isinstance(rev_val, bool): is_rev = rev_val
        elif isinstance(rev_val, str): is_rev = rev_val.lower() == "yes"
        node["reversibility"] = is_rev
        node["reversibility_report"] = is_rev

        # 5. FIX RIGUARDANTE DISPARATE IMPACT (Calcolo dinamico se manca total_score_report)
        if not node.get("total_score_report") or node.get("total_score_report") == "-":
            # Recuperiamo la Likelihood (final_score)
            likelihood = node.get("final_score")
            if likelihood is None and "context_report" in node:
                likelihood = node["context_report"].get("final_score")
            
            # Recuperiamo la Gravity
            gravity_val = node.get("gravity_report") if node.get("gravity_report") is not None else node.get("gravity")
            
            if likelihood is not None and gravity_val is not None:
                # Calcola il rischio totale sfruttando la funzione già presente nel file
                node["total_score_report"] = calculate_fria_risk(likelihood, gravity_val, is_rev)

    if isinstance(results, dict):
        for metric_key, metric_data in results.items():
            if not isinstance(metric_data, dict): continue
            
            # Scansione dei sotto-nodi (es. gender, age_range)
            is_nested = False
            for sub_key, sub_val in metric_data.items():
                if isinstance(sub_val, dict) and ("metric" in sub_val or "status" in sub_val):
                    fix_node(sub_val, metric_key)
                    is_nested = True
            
            # Se la metrica è a livello globale (es. k-anonymity)
            if not is_nested:
                fix_node(metric_data, metric_key)
            else:
                fix_node(metric_data, metric_key)

    return clean_nans(report_data)
'''
'''
@router.get("/results/{run_id}_report")
def get_report_json(run_id: str):
    report_path = RESULTS_DIR / f"{run_id}_report.json"
    if not report_path.exists(): 
        raise HTTPException(status_code=404, detail="Report non trovato")

    report_data = json.loads(report_path.read_text(encoding="utf-8"))
    results = report_data.get("results", report_data)

    privacy_list = ["anonymity_set_size", "k_anonymity", "l_diversity", "mutual_information_metric", "t_closeness"]
    fairness_list = ["conditional_statistical_parity", "conditional_use_accuracy_equality", "demographic_parity", "disparate_impact", "equal_opportunity", "equalized_odds_difference", "overall_accuracy_equality", "predictive_parity"]

    # Funzione helper per sistemare un "nodo" (sia principale che nidificato)
    def fix_node(node, metric_name):
        if not isinstance(node, dict): return
        
        # 1. Assegna il Dominio Corretto
        if not node.get("metric_right_report"):
            node["metric_right_report"] = "Privacy" if metric_name in privacy_list else "Non Discrimination" if metric_name in fairness_list else "Other"

        # 2. Descrizione di Default (se manca)
        if not node.get("metric_description_report"):
            node["metric_description_report"] = "Detailed analysis of the metric results for the specific feature identified."

        # 3. CORREZIONE TESTO GIUSTIFICAZIONE
        old_text = "Since no weight has been assigned, the default weight 5 has been used"
        new_text = "Since no weight has been assigned, the gravity is set to low"
        
        if node.get("justification_report") == old_text:
            node["justification_report"] = new_text
        if node.get("user_justification_report") == old_text:
            node["user_justification_report"] = new_text

        # 4. Normalizzazione Reversibilità
        rev_val = node.get("reversibility_report")
        is_rev = False
        if isinstance(rev_val, bool): is_rev = rev_val
        elif isinstance(rev_val, str): is_rev = rev_val.lower() == "yes"
        node["reversibility"] = is_rev
        node["reversibility_report"] = is_rev

    if isinstance(results, dict):
        for metric_key, metric_data in results.items():
            if not isinstance(metric_data, dict): continue
            
            # Controlliamo se è una metrica nidificata (ha sotto-chiavi come "gender" o "age_range")
            # Un modo semplice è vedere se le sotto-chiavi contengono dizionari con il campo "metric" o "status"
            is_nested = False
            for sub_key, sub_val in metric_data.items():
                if isinstance(sub_val, dict) and ("metric" in sub_val or "status" in sub_val):
                    fix_node(sub_val, metric_key)
                    is_nested = True
            
            # Se non era nidificata (es. Anonymity Set Size), applichiamo la correzione al primo livello
            if not is_nested:
                fix_node(metric_data, metric_key)
            else:
                # Per sicurezza, diamo il dominio anche al nodo padre
                fix_node(metric_data, metric_key)

    return clean_nans(report_data)
'''

''''
@router.get("/results/{run_id}_report")
def get_report_json(run_id: str):
    report_path = RESULTS_DIR / f"{run_id}_report.json"
    if not report_path.exists(): 
        raise HTTPException(status_code=404, detail="Report non trovato")

    report_data = json.loads(report_path.read_text(encoding="utf-8"))
    domain_configs = report_data.get("domain_configs", {})
    results = report_data.get("results", report_data)

    privacy_list = ["anonymity_set_size", "k_anonymity", "l_diversity", "mutual_information_metric", "t_closeness"]
    fairness_list = ["conditional_statistical_parity", "conditional_use_accuracy_equality", "demographic_parity", "disparate_impact", "equal_opportunity", "equalized_odds_difference", "overall_accuracy_equality", "predictive_parity"]

    if isinstance(results, dict):
        for metric_key, metric_data in results.items():
            if not isinstance(metric_data, dict): continue
            
            # Dominio
            if not metric_data.get("metric_right_report"):
                metric_data["metric_right_report"] = "Privacy" if metric_key in privacy_list else "Non Discrimination" if metric_key in fairness_list else "Other"

            # Descrizione
            if not metric_data.get("metric_description_report"):
                metric_data["metric_description_report"] = "Detailed analysis of the metric results for the specific feature identified."

            # Reversibilità: Normalizzazione Forzata (Yes/No -> True/False)
            rev_val = metric_data.get("reversibility_report")
            is_rev = False
            if isinstance(rev_val, bool): is_rev = rev_val
            elif isinstance(rev_val, str): is_rev = rev_val.lower() == "yes"
            
            metric_data["reversibility"] = is_rev
            metric_data["reversibility_report"] = is_rev

    return clean_nans(report_data)
'''
class GeneratePDFRequest(BaseModel):
    run_id: str
    session_id: str

@router.post("/results/generate_pdf")
def generate_pdf(req: GeneratePDFRequest):
    run_id = (req.run_id or "").strip()
    session_id = (req.session_id or "").strip()
    if not run_id: raise HTTPException(status_code=400)
    out_dir = Path("backend/storage/reports")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{run_id}_report_{session_id}.pdf"
    try:
        render_report_to_pdf(run_id=run_id, frontend_base_url=os.getenv("FRONTEND_BASE_URL", "http://localhost:5173"), out_path=out_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {e}")
    return FileResponse(path=str(out_path), media_type="application/pdf", filename=f"final_evaluation_report_{run_id}.pdf")

@router.post("/results/purge_run")
def purge_run(payload: Dict[str, Any] = Body(...)):
    run_id = payload.get("run_id")
    if not run_id:
        raise HTTPException(status_code=400, detail="run_id is required")

    # TRUCCO ESPERIMENTO: Eliminiamo SOLO il file del report.
    # I file originali (dati e schemi) NON devono essere toccati!
    report_file = RESULTS_DIR / f"{run_id}_report.json"
    
    deleted_count = 0
    if report_file.exists():
        try:
            report_file.unlink()
            deleted_count += 1
        except Exception as e:
            logger.error(f"Impossibile cancellare il file {report_file}: {e}")
                
    return {"status": "success", "files_deleted": deleted_count}