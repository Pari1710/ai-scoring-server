from fastapi import FastAPI
from dotenv import load_dotenv
from app.services.kafka_service import KafkaService

# Load environment variables from .env file at the very start
load_dotenv()

# --- Application Setup ---
app = FastAPI(
    title="DeFi Reputation Scoring Server",
    description="A Kafka-based microservice to calculate wallet reputation scores.",
    version="1.0.0"
)

# --- Global Services ---
# Create a single instance of the KafkaService that the app will manage
kafka_service = KafkaService()

# --- Application Lifecycle Events ---

@app.on_event("startup")
async def startup_event():
    """
    This function is called when the FastAPI application starts.
    It starts the Kafka consumer in the background.
    """
    print("Application startup...")
    kafka_service.start_consumer()

@app.on_event("shutdown")
async def shutdown_event():
    """
    This function is called when the FastAPI application is shutting down.
    It ensures the Kafka consumer is stopped gracefully.
    """
    print("Application shutdown...")
    kafka_service.stop_consumer()

# --- API Endpoints ---

@app.get("/", tags=["General"])
def read_root():
    """
    Root endpoint providing basic service information.
    """
    return {"service": "AI Scoring Service", "status": "running"}

@app.get("/api/v1/health", tags=["Monitoring"])
def health_check():
    """
    Health check endpoint for monitoring systems.
    """
    # In a real app, you might check DB connection, Kafka connection, etc.
    return {"status": "ok"}

@app.get("/api/v1/stats", tags=["Monitoring"])
def get_stats():
    """
    Returns real-time processing statistics from the Kafka service.
    """
    return kafka_service.get_stats()
