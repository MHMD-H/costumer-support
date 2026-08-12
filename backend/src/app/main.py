"""FastAPI app entry point."""

from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title="AI Commerce Copilot API")
    return app


app = create_app()
