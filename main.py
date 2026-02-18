from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from routers import tickets
import resources

app = FastAPI(title="GLPI Ticket Dashboard")

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files and Templates
app.mount("/static", StaticFiles(directory=resources.get_path("static")), name="static")
templates = Jinja2Templates(directory=resources.get_path("templates"))

# Routers
app.include_router(tickets.router)

@app.get("/")
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
