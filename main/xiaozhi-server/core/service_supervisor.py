"""Supervise long-running services: ready means bound, task failure stops the process."""
import asyncio

async def run_services(services, stop, startup_timeout=120, on_ready=None):
    tasks = {asyncio.create_task(start(), name=name): name for name, start, _ in services}
    async def all_ready():
        await asyncio.gather(*(event.wait() for _, _, event in services))
    ready = asyncio.create_task(all_ready(), name="readiness")
    async def wait_stop():
        await stop()
    stopping = asyncio.create_task(wait_stop(), name="shutdown")
    try:
        done, _ = await asyncio.wait([*tasks, ready, stopping], timeout=startup_timeout,
                                     return_when=asyncio.FIRST_COMPLETED)
        for task in tasks:
            if task in done:
                if task.cancelled():
                    raise RuntimeError(f"Dịch vụ {tasks[task]} đã bị hủy")
                error = task.exception()
                raise RuntimeError(f"Dịch vụ {tasks[task]} đã dừng ngoài dự kiến") from error
        if stopping in done:
            return
        if ready not in done:
            pending = [name for name, _, event in services if not event.is_set()]
            raise TimeoutError("Hết thời gian khởi động: " + ", ".join(pending))
        if on_ready:
            on_ready()
        done, _ = await asyncio.wait([*tasks, stopping], return_when=asyncio.FIRST_COMPLETED)
        for task in tasks:
            if task in done:
                if task.cancelled():
                    raise RuntimeError(f"Dịch vụ {tasks[task]} đã bị hủy")
                error = task.exception()
                raise RuntimeError(f"Dịch vụ {tasks[task]} đã dừng ngoài dự kiến") from error
    finally:
        for task in [*tasks, ready, stopping]:
            task.cancel()
        await asyncio.gather(*tasks, ready, stopping, return_exceptions=True)
