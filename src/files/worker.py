from rq import Connection, Worker, Queue
from redis import Redis

from src.config import settings
from src.files import tasks  # noqa: F401  # ensure tasks are imported


def run():
    redis_conn = Redis.from_url(settings.REDIS_URL)
    listen = ["files"]
    worker = Worker(list(map(Queue, listen)), connection=redis_conn)
    worker.work()


if __name__ == "__main__":
    run()
