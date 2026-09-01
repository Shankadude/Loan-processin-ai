from fastapi import FastAPI

from api.routes import router


app = FastAPI(
    title="Loan Processing Decision API",
    description=(
        "Automated loan document comparison, "
        "risk assessment and decision API."
    ),
    version="1.0.0",
)


app.include_router(
    router,
    prefix="/api"
)


@app.get("/")
def root():

    return {
        "service": "Loan Processing Decision Engine",
        "status": "running"
    }