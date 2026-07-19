import uvicorn

def run(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Start the development server using Uvicorn and FastAPI."""
    print(f"Starting AuditData AI on FastAPI/Uvicorn at http://{host}:{port}")
    uvicorn.run("backend.app.main:app", host=host, port=port, reload=False)

if __name__ == "__main__":
    run()
