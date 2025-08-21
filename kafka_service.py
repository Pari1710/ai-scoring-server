import os
import json
import time
import threading
from confluent_kafka import Consumer, Producer, KafkaError
from app.models.dex_model import DexModel
from app.utils.types import WalletTransactionInput

class KafkaService:
    """
    Manages Kafka consumer and producer to process wallet transactions.
    """
    def __init__(self):
        # --- Configuration ---
        self.kafka_bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
        self.input_topic = os.getenv("KAFKA_INPUT_TOPIC")
        self.success_topic = os.getenv("KAFKA_SUCCESS_TOPIC")
        self.failure_topic = os.getenv("KAFKA_FAILURE_TOPIC")
        self.consumer_group = os.getenv("KAFKA_CONSUMER_GROUP")

        # --- Kafka Clients ---
        self.consumer = Consumer({
            'bootstrap.servers': self.kafka_bootstrap_servers,
            'group.id': self.consumer_group,
            'auto.offset.reset': 'earliest'
        })
        self.producer = Producer({'bootstrap.servers': self.kafka_bootstrap_servers})

        # --- AI Model ---
        self.dex_model = DexModel()

        # --- State and Control ---
        self.is_running = False
        self.consumer_thread = None
        self.processed_count = 0
        self.success_count = 0
        self.failure_count = 0

    def _produce_message(self, topic: str, message: dict):
        """Helper to produce a JSON message to a specific topic."""
        self.producer.produce(topic, json.dumps(message).encode('utf-8'))
        self.producer.flush()

    def _processing_loop(self):
        """The main loop that consumes, processes, and produces messages."""
        self.consumer.subscribe([self.input_topic])
        print(f"🚀 Consumer started. Listening to topic: {self.input_topic}")

        while self.is_running:
            msg = self.consumer.poll(1.0) # Poll for messages with a 1-second timeout

            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                else:
                    print(f"❌ Kafka Consumer error: {msg.error()}")
                    break

            start_time = time.time()
            wallet_address = "unknown"
            try:
                # 1. Deserialize and Validate
                raw_data = json.loads(msg.value().decode('utf-8'))
                validated_data = WalletTransactionInput(**raw_data)
                wallet_address = validated_data.wallet_address

                # 2. Process with AI Model
                score, features = self.dex_model.process_wallet(validated_data.dict())
                
                # 3. Build and Send Success Message
                processing_time_ms = int((time.time() - start_time) * 1000)
                success_payload = {
                    "wallet_address": wallet_address,
                    "zscore": f"{score:.18f}",
                    "timestamp": int(time.time()),
                    "processing_time_ms": processing_time_ms,
                    "categories": [{
                        "category": "dexes",
                        "score": score,
                        "transaction_count": features.pop('transaction_count'),
                        "features": features
                    }]
                }
                self._produce_message(self.success_topic, success_payload)
                self.success_count += 1

            except Exception as e:
                # 4. Handle Any Errors and Send Failure Message
                print(f"🔥 Processing failed for wallet {wallet_address}: {e}")
                processing_time_ms = int((time.time() - start_time) * 1000)
                failure_payload = {
                    "wallet_address": wallet_address,
                    "error": str(e),
                    "timestamp": int(time.time()),
                    "processing_time_ms": processing_time_ms,
                }
                self._produce_message(self.failure_topic, failure_payload)
                self.failure_count += 1
            
            finally:
                self.processed_count += 1

        self.consumer.close()
        print("🛑 Consumer closed.")

    def start_consumer(self):
        """Starts the consumer loop in a background thread."""
        if not self.is_running:
            self.is_running = True
            self.consumer_thread = threading.Thread(target=self._processing_loop)
            self.consumer_thread.start()
            print("✅ Kafka consumer thread started.")

    def stop_consumer(self):
        """Stops the consumer loop gracefully."""
        if self.is_running:
            self.is_running = False
            self.consumer_thread.join() # Wait for the thread to finish
            print("✅ Kafka consumer thread stopped.")

    def get_stats(self):
        """Returns processing statistics."""
        return {
            "processed_messages": self.processed_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "is_running": self.is_running
        }
