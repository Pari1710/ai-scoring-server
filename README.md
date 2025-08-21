AI Engineer Challenge: DeFi Reputation Scoring Server
This project is a production-ready AI microservice that calculates reputation scores for DeFi wallet addresses based on their transaction history. It consumes transaction data from a Kafka stream, processes it using a Pandas-based scoring model, and publishes the resulting scores back to Kafka.

The entire application and its dependencies (Kafka, Zookeeper, MongoDB) are containerized using Docker and managed with Docker Compose for easy setup and deployment.

🚀 Technology Stack
Language: Python 3.11

Web Framework: FastAPI

Data Streaming: Confluent Kafka

Database: MongoDB

Containerization: Docker & Docker Compose

Core Libraries: Pandas, Pydantic, python-dotenv

✅ Prerequisites
Docker installed and running on your machine.

Docker Compose (typically included with Docker Desktop).

⚙️ Setup and Execution
1. Configure Environment Variables
The application is configured using environment variables.

Copy the example environment file:

cp .env.example .env

Update the .env file with your specific Kafka and MongoDB configurations. For the default Docker Compose setup, the provided values should work out of the box:

# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
KAFKA_INPUT_TOPIC=wallet-transactions
KAFKA_SUCCESS_TOPIC=wallet-scores-success
KAFKA_FAILURE_TOPIC=wallet-scores-failure
KAFKA_CONSUMER_GROUP=ai-scoring-service

# MongoDB Configuration
MONGODB_URL=mongodb://mongo:27017
MONGODB_DATABASE=ai_scoring
MONGODB_TOKENS_COLLECTION=tokens
MONGODB_THRESHOLDS_COLLECTION=protocol-thresholds-percentiles

2. Build and Run the Application
This project uses Docker Compose to build and run all services with a single command.

From the project's root directory, run:

docker-compose up --build -d

--build: Forces a rebuild of the ai-scoring-service image if you've made code changes.

-d: Runs the containers in detached mode (in the background).

This command will:

Pull the required images for Kafka, Zookeeper, and MongoDB.

Build the Docker image for the Python application.

Start all four services on a shared Docker network.

3. Create Kafka Topics
After the services have started, you need to create the necessary Kafka topics.

Wait about 20-30 seconds for Kafka to initialize fully.

Run the following commands one by one:

docker-compose exec kafka kafka-topics --create --topic wallet-transactions --bootstrap-server kafka:9092
docker-compose exec kafka kafka-topics --create --topic wallet-scores-success --bootstrap-server kafka:9092
docker-compose exec kafka kafka-topics --create --topic wallet-scores-failure --bootstrap-server kafka:9092

4. Restart the Service
Restart the ai-scoring-service to ensure it connects to the newly created topics.

docker-compose restart ai-scoring-service

The application is now running and ready to process messages.

🧪 Testing the Service
Automated Health Check
Run the provided test script to verify that the API endpoints are live and responsive. The script is executed inside the running service container.

docker-compose exec ai-scoring-service python test_challenge.py

You should see a summary indicating that all 4 tests have passed.

Manual End-to-End Test
This test validates the entire Kafka pipeline.

Start a Consumer:
Open a new terminal and run the following command to listen for successful results. The terminal will wait for messages.

docker-compose exec kafka kafka-console-consumer --bootstrap-server kafka:9092 --topic wallet-scores-success --from-beginning

Start a Producer:
Open a second new terminal to send a message.

docker-compose exec kafka kafka-console-producer --bootstrap-server kafka:9092 --topic wallet-transactions

Send a Message:
Copy the sample JSON from test_challenge.py and paste it into the producer terminal, then press Enter.

Verify the Output:
Switch back to your consumer terminal. You will see the final, scored JSON output from the service.

🌐 API Endpoints
The service exposes the following endpoints for monitoring:

GET /: Basic service information.

URL: http://localhost:8000/

GET /api/v1/health: Health check endpoint.

URL: http://localhost:8000/api/v1/health

GET /api/v1/stats: Real-time processing statistics.

URL: http://localhost:8000/api/v1/stats

📂 Project Structure
.
├── app/                  # Main application source code
│   ├── main.py           # FastAPI application entry point
│   ├── models/
│   │   └── dex_model.py  # AI scoring model logic
│   ├── services/
│   │   └── kafka_service.py # Kafka consumer/producer service
│   └── utils/
│       └── types.py      # Pydantic data models
├── .env                  # Environment variables (local)
├── .env.example          # Example environment variables
├── docker-compose.yml    # Docker Compose configuration
├── Dockerfile            # Docker configuration for the app
├── requirements.txt      # Python dependencies
└── test_challenge.py     # Health check script
