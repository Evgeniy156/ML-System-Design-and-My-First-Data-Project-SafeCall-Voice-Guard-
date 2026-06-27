"""SafeCall ML Worker — entry point with reconnect loop.

Pattern from example/ml_worker/main.py.
"""
from rmq.rmqconf import RabbitMQConfig
import sys
import pika
import time
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def run_worker(worker):
    """Run worker with automatic reconnect on connection loss."""
    while True:
        try:
            if not worker.connection or not worker.connection.is_open:
                worker.connect()
            worker.start_consuming()
        except pika.exceptions.AMQPConnectionError as e:
            logger.error(f"Connection error: {e}, retrying in 5s...")
            time.sleep(5)
        except KeyboardInterrupt:
            logger.info("Shutdown requested.")
            worker.cleanup()
            break
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise
        time.sleep(1)


def main():
    try:
        # Import after logging setup so model-loading messages are visible.
        from rmq.rmqworker import SafeCallWorker

        config = RabbitMQConfig()
        logger.info(f"Worker starting. Queue: {config.queue_name}, Host: {config.host}")
        worker = SafeCallWorker(config)
        run_worker(worker)
    except Exception as e:
        logger.error(f"Application error: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
