"""定时计划模块 - 基于 schedule 库"""

import threading
import time
import uuid
from datetime import datetime
from typing import Callable

import schedule as _sch_lib


class ScheduledTask:
    def __init__(self, description: str, time_spec: str, callback: Callable):
        self.task_id: str = str(uuid.uuid4())[:8]
        self.description: str = description
        self.time_spec: str = time_spec  # "18:00" | "30s" | "5m" | "2h"
        self.callback: Callable = callback
        self.enabled: bool = True
        self.last_run: str = "从未"
        self.run_count: int = 0


class Scheduler:
    """
    支持以下时间规格：
      HH:MM  — 每天指定时刻执行
      Ns     — 每 N 秒执行
      Nm     — 每 N 分钟执行
      Nh     — 每 N 小时执行
    """

    def __init__(self):
        self._tasks: dict[str, ScheduledTask] = {}
        self._scheduler = _sch_lib.Scheduler()
        self._running = False
        self._thread: threading.Thread | None = None

    # ── 任务管理 ─────────────────────────────────────────────

    def add_task(self, task: ScheduledTask) -> str:
        self._tasks[task.task_id] = task
        self._register(task)
        return task.task_id

    def remove_task(self, task_id: str):
        self._tasks.pop(task_id, None)
        self._scheduler.clear(task_id)

    def toggle_task(self, task_id: str, enabled: bool):
        if task_id in self._tasks:
            self._tasks[task_id].enabled = enabled

    def get_tasks(self) -> list[ScheduledTask]:
        return list(self._tasks.values())

    # ── 运行控制 ─────────────────────────────────────────────

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        self._scheduler.clear()

    def is_running(self) -> bool:
        return self._running

    # ── 内部 ─────────────────────────────────────────────────

    def _loop(self):
        while self._running:
            self._scheduler.run_pending()
            time.sleep(0.5)

    def _register(self, task: ScheduledTask):
        def _run():
            if task.enabled:
                task.last_run = datetime.now().strftime("%H:%M:%S")
                task.run_count += 1
                task.callback()

        spec = task.time_spec.strip()
        try:
            if len(spec) == 5 and spec[2] == ":":
                self._scheduler.every().day.at(spec).do(_run).tag(task.task_id)
            elif spec.endswith("s") and spec[:-1].isdigit():
                self._scheduler.every(int(spec[:-1])).seconds.do(_run).tag(task.task_id)
            elif spec.endswith("m") and spec[:-1].isdigit():
                self._scheduler.every(int(spec[:-1])).minutes.do(_run).tag(task.task_id)
            elif spec.endswith("h") and spec[:-1].isdigit():
                self._scheduler.every(int(spec[:-1])).hours.do(_run).tag(task.task_id)
            elif spec.isdigit():
                self._scheduler.every(int(spec)).seconds.do(_run).tag(task.task_id)
            else:
                raise ValueError(
                    f"不支持的时间规格 {spec!r}，" "支持格式：HH:MM / 30s / 5m / 2h"
                )
        except Exception:
            raise
