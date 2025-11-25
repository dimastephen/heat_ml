from redis import Redis
from rq import Worker, Queue

from src.config import settings
from src.files import tasks  # noqa: F401  # ensure tasks are imported


def run():
    redis_conn = Redis.from_url(settings.REDIS_URL)
    queues = [Queue(name, connection=redis_conn) for name in ["files", "datasets"]]
    worker = Worker(queues, connection=redis_conn)
    worker.work()


if __name__ == "__main__":
    run()
