from backend.core.settings import BASE_DIR, STORAGE_DIR, UPLOAD_DIR, CONFIG_DIR, RESULTS_DIR, RUN_DIR #all the dir to be imported
from backend.services.dataset_services import save_upload, delete_existing_uploads
from backend.services.config_services import latest_upload_for_type, get_config_id
from backend.services.utils.get_file_columns import get_file_columns
from backend.services.utils.csv_tools import read_columns_from_file
from fastapi import APIRouter, HTTPException, Query, Body, UploadFile, File, Form
from pathlib import Path
import json
import uuid
import csv
import pandas as pd

import shutil
from pydantic import BaseModel

router = APIRouter(tags=["datasets"])

#Save datasets in UPLOADS with following path: {dataset_type}__{cfg_id}__{safe_name}
@router.post("/datasets")
async def upload_dataset(
    file: UploadFile = File(...),
    dataset_type: str = Form(...),):
    cfg_id = get_config_id() 
    safe_name = file.filename.replace("/", "_").replace("\\", "_")

    # keep only one file for each dataset_type
    delete_existing_uploads(dataset_type)

    path = UPLOAD_DIR / f"{dataset_type}__{cfg_id}__{safe_name}"

    save_upload(file, path)

    return {
        "filename": safe_name,
        "dataset_type": dataset_type,
        "path": str(path.resolve()),
    }

#GET: if files already uploaded, keep them (when go Back), else if upload new ones, overwrite them
@router.get("/datasets/latest-status")
def latest_status():
    cfg = get_config_id()

    dataset_types = ["X_test", "y_true", "y_pred", "train", "model"]
    result = {}

    for ds_type in dataset_types:
        files = sorted(
            UPLOAD_DIR.glob(f"{ds_type}__{cfg}__*"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

        if files:
            file_name = files[0].name.split("__")[-1]

            if ds_type == "X_test":
                result[ds_type] = {
                    "ok": True,
                    "filename": file_name,
                }
            else:
                result[ds_type] = {
                    "filename": file_name,
                }

        else:
            if ds_type == "X_test":
                result[ds_type] = {
                    "ok": False,
                    "filename": "",
                }
            else:
                result[ds_type] = {
                    "filename": "",
                }

    return result

#GET: headers for sensitive features
@router.get("/headers")
def latest_columns():
    # 1. Prova a usare il metodo originale del tesista
    try:
        result = get_file_columns()
        if "columns" in result and result["columns"]:
            return {"columns": result["columns"]}
    except Exception as e:
        print(f"Metodo originale fallito: {e}")
        pass # Se fallisce, usiamo il nostro fallback
        
    # 2. FALLBACK: Cerca l'ultimo file X_test caricato
    cfg = get_config_id()
    files = sorted(
        UPLOAD_DIR.glob(f"X_test__{cfg}__*"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )
    
    if not files:
        raise HTTPException(status_code=404, detail="Nessun dataset trovato per la configurazione attuale")
        
    latest_file = files[0]
    
    # 3. Leggi le colonne usando pandas (metodo infallibile)
    try:
        df = pd.read_csv(latest_file, nrows=0) # Legge solo le intestazioni per velocità
        columns = df.columns.tolist()
        return {"columns": columns}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore nella lettura del CSV: {e}")

class ExperimentDataset(BaseModel):
    filename: str

@router.post("/upload-experiment-dataset")
def upload_experiment_dataset(payload: ExperimentDataset):
    cfg_id = get_config_id()
    filename = payload.filename
    
    # Cerca il file nella cartella 'data'
    source_path = BASE_DIR.parent / "data" / filename 

    if not source_path.exists():
        raise HTTPException(status_code=404, detail=f"File {filename} non trovato in {source_path}")

    # Invece di simulare solo X_test, simuliamo l'upload di tutti e 3 i requisiti base
    dataset_types_to_mock = ["X_test", "y_true", "y_pred"]
    
    for dtype in dataset_types_to_mock:
        # 1. Pulisce eventuali vecchi file di questo tipo
        for old_file in UPLOAD_DIR.glob(f"{dtype}__*"):
            try:
                old_file.unlink()
            except Exception as e:
                pass
        
        # 2. Crea il nuovo percorso simulando che l'utente abbia caricato y_true e y_pred
        dest_path = UPLOAD_DIR / f"{dtype}__{cfg_id}__{filename}"
        
        # 3. Copia il file
        shutil.copy2(source_path, dest_path)
    
    return {
        "status": "ok", 
        "config_id": cfg_id,
        "message": "Dataset X_test, y_true e y_pred caricati silenziosamente."
    }

class SlicePayload(BaseModel):
    target_column: str
    prediction_column: str

@router.post("/slice-target-files")
def slice_target_files(payload: SlicePayload):
    cfg_id = get_config_id()

    # 1. Trova e taglia il file y_true
    y_true_files = list(UPLOAD_DIR.glob(f"y_true__{cfg_id}__*"))
    if y_true_files:
        file_path = y_true_files[0]
        df = pd.read_csv(file_path)
        if payload.target_column in df.columns:
            # Salva sovrascrivendo il file, ma tenendo SOLO quella colonna
            df[[payload.target_column]].to_csv(file_path, index=False)

    # 2. Trova e taglia il file y_pred
    y_pred_files = list(UPLOAD_DIR.glob(f"y_pred__{cfg_id}__*"))
    if y_pred_files:
        file_path = y_pred_files[0]
        df = pd.read_csv(file_path)
        if payload.prediction_column in df.columns:
            # Salva sovrascrivendo il file, ma tenendo SOLO quella colonna
            df[[payload.prediction_column]].to_csv(file_path, index=False)

    return {"message": "File tagliati con successo a 1 colonna!"}




