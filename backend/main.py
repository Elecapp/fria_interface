import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

from backend.core.settings import ensure_dirs
from backend.api import datasets, configs, evaluation, postprocessing, results #rights,

def create_app() -> FastAPI:
    ensure_dirs()
    app = FastAPI()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"], 
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def log_requests(request, call_next):
        print("INCOMING:", request.method, request.url.path)
        return await call_next(request)


    app_api = FastAPI()
    app_api.include_router(datasets.router)
    app_api.include_router(configs.configs_router)
    app_api.include_router(configs.rights_router)
    app_api.include_router(postprocessing.router)
    #app.include_router(rights.router)
    app_api.include_router(evaluation.router)
    app_api.include_router(results.router)


    app.mount('/api', app_api)

    # Calculate absolute path to frontend/dist directory
    _script_dir = os.path.dirname(os.path.abspath(__file__))
    _project_root = os.path.dirname(_script_dir)
    _frontend_dist = os.path.join(_project_root, 'frontend', 'dist')
    app.mount('/', StaticFiles(directory=_frontend_dist, html=True), name='static')


    return app

app = create_app()
