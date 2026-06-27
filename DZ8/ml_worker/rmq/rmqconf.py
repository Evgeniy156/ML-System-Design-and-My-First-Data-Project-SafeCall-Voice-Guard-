"""RabbitMQ configuration for ml_worker — copy of app/services/rm/rmqconf.py."""
import os
from dataclasses import dataclass, field
import pika


@dataclass
class RabbitMQConfig:
    host: str = field(default_factory=lambda: os.environ.get("RABBITMQ_HOST", "rabbitmq"))
    port: int = field(default_factory=lambda: int(os.environ.get("RABBITMQ_PORT", "5672")))
    user: str = field(default_factory=lambda: os.environ.get("RABBITMQ_USER", "rmuser"))
    password: str = field(default_factory=lambda: os.environ.get("RABBITMQ_PASS", "rmpassword"))
    queue_name: str = field(default_factory=lambda: os.environ.get("RABBITMQ_QUEUE", "safecall_tasks"))

    def get_connection_params(self) -> pika.ConnectionParameters:
        credentials = pika.PlainCredentials(self.user, self.password)
        return pika.ConnectionParameters(
            host=self.host,
            port=self.port,
            credentials=credentials,
        )
