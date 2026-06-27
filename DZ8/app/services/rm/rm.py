"""RabbitMQ client (producer) — pattern from example/app/services/rm/rm.py.

Global singleton: safecall_rmq_client.send_task(prediction)
"""
import json
import logging
import pika
from services.rm.rmqconf import RabbitMQConfig

logger = logging.getLogger(__name__)


class RabbitMQClient:
    def __init__(self):
        self.config = RabbitMQConfig()
        self.connection = None
        self.channel = None

    def _connect(self):
        if self.connection and self.connection.is_open:
            return
        self.connection = pika.BlockingConnection(
            self.config.get_connection_params()
        )
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue=self.config.queue_name)
        logger.info("RabbitMQ producer connected.")

    def send_task(self, task) -> bool:
        """Publish task.to_queue_message() to the queue."""
        try:
            self._connect()
            message = json.dumps(task.to_queue_message())
            self.channel.basic_publish(
                exchange="",
                routing_key=self.config.queue_name,
                body=message.encode("utf-8"),
                properties=pika.BasicProperties(delivery_mode=2),
            )
            logger.info(f"Task {task.id} sent to queue '{self.config.queue_name}'")
            return True
        except Exception as e:
            logger.error(f"Failed to send task: {e}")
            # Reset connection for next attempt
            self.connection = None
            self.channel = None
            return False

    def close(self):
        if self.channel and self.channel.is_open:
            self.channel.close()
        if self.connection and self.connection.is_open:
            self.connection.close()


# Global singleton — like example's rabbit_client
safecall_rmq_client = RabbitMQClient()
