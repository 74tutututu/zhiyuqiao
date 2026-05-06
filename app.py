from __future__ import annotations

import os

import uvicorn


if __name__ == "__main__":
    server_name = (
        os.getenv("APP_SERVER_NAME")
        or os.getenv("GRADIO_SERVER_NAME")
        or "0.0.0.0"
    ).strip() or "0.0.0.0"
    server_port = int(
        (os.getenv("APP_SERVER_PORT") or os.getenv("GRADIO_SERVER_PORT") or "7860").strip()
    )
    root_path = (
        os.getenv("APP_ROOT_PATH")
        or os.getenv("GRADIO_ROOT_PATH")
        or ""
    ).strip()

    uvicorn.run(
        "main:app",
        host=server_name,
        port=server_port,
        reload=False,
        root_path=root_path,
    )
