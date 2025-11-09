import uvicorn
from app.web_server import GraphWebServer

server = GraphWebServer()

if __name__ == "__main__":
    uvicorn.run(server.app, host="0.0.0.0", port=8000)
