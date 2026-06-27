"""SafeCall RabbitMQ worker — consumes tasks, runs inference, posts results.

Pattern from example/ml_worker/rmq/rmqworker.py.
"""
from rmq.rmqconf import RabbitMQConfig
from predictor import SafeCallPredictor
import pika
import time
import requests
import logging
import json

logger = logging.getLogger(__name__)

# Load model ONCE at module level — shared across all messages
predictor = SafeCallPredictor()


class SafeCallWorker:
    MAX_RETRIES = 3
    RETRY_DELAY = 0.5
    RESULT_ENDPOINT = "http://app:8080/api/predict/send_task_result"
    FAILURE_ENDPOINT = "http://app:8080/api/predict/send_task_failure"

    def __init__(self, config: RabbitMQConfig):
        self.config = config
        self.connection = None
        self.channel = None
        self.retry_count = 0

    def connect(self):
        while True:
            try:
                self.connection = pika.BlockingConnection(
                    self.config.get_connection_params()
                )
                self.channel = self.connection.channel()
                self.channel.queue_declare(queue=self.config.queue_name)
                # Fair dispatch — don't send more than 1 task at a time
                self.channel.basic_qos(prefetch_count=1)
                logger.info(
                    f"Connected to RabbitMQ. Queue: {self.config.queue_name}"
                )
                break
            except Exception as e:
                logger.error(f"Connection failed: {e}")
                time.sleep(self.RETRY_DELAY)

    def send_result(self, task_id, result: str) -> bool:
        """POST result back to FastAPI app."""
        try:
            r = requests.post(
                self.RESULT_ENDPOINT,
                params={"task_id": task_id, "result": result},
            )
            r.raise_for_status()
            logger.info(f"Result sent for task {task_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to send result for task {task_id}: {e}")
            return False

    def send_failure(self, task_id, error: str) -> bool:
        try:
            r = requests.post(
                self.FAILURE_ENDPOINT,
                params={"task_id": task_id, "error": error[:500]},
            )
            r.raise_for_status()
            logger.info(f"Failure reported for task {task_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to report failure for task {task_id}: {e}")
            return False

    def process_message(self, ch, method, properties, body):
        """Process a single prediction task from the queue."""
        try:
            data = json.loads(body.decode("utf-8"))
            task_id = data["task_id"]
            audio_path = data["audio_filename"]
            logger.info(f"Processing task {task_id}: {audio_path}")

            result = predictor.predict(audio_path)
            result_json = json.dumps(result)

            if self.send_result(task_id, result_json):
                ch.basic_ack(delivery_tag=method.delivery_tag)
                self.retry_count = 0
                logger.info(
                    f"Task {task_id} completed: {result['verdict']} "
                    f"(p={result['spoof_probability']:.3f}, "
                    f"t={result['processing_time_ms']:.0f}ms)"
                )
            else:
                raise Exception("Failed to send result to API")
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            task_id = None
            try:
                task_id = json.loads(body.decode("utf-8")).get("task_id")
            except Exception:
                pass
            self.retry_count += 1
            if self.retry_count >= self.MAX_RETRIES:
                if task_id:
                    self.send_failure(task_id, str(e))
                ch.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
                self.retry_count = 0
                logger.warning(f"Message rejected after {self.MAX_RETRIES} retries")
            else:
                time.sleep(self.RETRY_DELAY)
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

    def start_consuming(self):
        self.channel.basic_consume(
            queue=self.config.queue_name,
            on_message_callback=self.process_message,
            auto_ack=False,
        )
        logger.info("Started consuming. Press Ctrl+C to exit.")
        self.channel.start_consuming()

    def cleanup(self):
        if self.channel and self.channel.is_open:
            self.channel.close()
        if self.connection and self.connection.is_open:
            self.connection.close()
        logger.info("Worker cleaned up.")
