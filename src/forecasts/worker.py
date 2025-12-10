from redis import Redis
from rq import Worker, Queue

from src.config import settings
from src.forecasts import tasks


def run():
    redis_conn = Redis.from_url(settings.REDIS_URL)
    queues = [Queue("forecasts", connection=redis_conn)]
    worker = Worker(queues, connection=redis_conn)
    worker.work()


if __name__ == "__main__":
    run()
