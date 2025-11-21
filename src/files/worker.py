from rq import Worker, Queue
from redis import Redis

from src.config import settings
from src.files import tasks  # noqa: F401  # ensure tasks are imported


def run():
    redis_conn = Redis.from_url(settings.REDIS_URL)
    listen = ["files", "datasets", "forecasts"]
    queues = [Queue(name, connection=redis_conn) for name in listen]
    worker = Worker(queues, connection=redis_conn)
    worker.work()


if __name__ == "__main__":
    run()
