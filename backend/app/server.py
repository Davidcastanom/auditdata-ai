import os
import uvicorn

def run(host: str = None, port: int = None) -> None:
    """Start the development server using Uvicorn and FastAPI."""
    host = host or os.getenv("HOST", "127.0.0.1")
    port = port or int(os.getenv("PORT", "8000"))
    print(f"Starting AuditData AI on FastAPI/Uvicorn at http://{host}:{port}")
    uvicorn.run("backend.app.main:app", host=host, port=port, reload=False)

if __name__ == "__main__":
    run()
