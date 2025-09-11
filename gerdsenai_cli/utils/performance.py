"""
Performance monitoring and instrumentation for GerdsenAI CLI.

This module provides utilities for tracking execution time, memory usage,
and performance metrics across all components.
"""

import asyncio
import functools
import time
from collections.abc import Callable
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import psutil
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


@dataclass
class PerformanceMetric:
    """A single performance measurement."""

    operation: str
    start_time: float
    end_time: float
    duration: float
    memory_before: float
    memory_after: float
    memory_delta: float
    success: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def timestamp(self) -> datetime:
        """Get the timestamp of when this metric was recorded."""
        return datetime.fromtimestamp(self.start_time)


class PerformanceTracker:
    """Global performance tracking and monitoring."""

    def __init__(self):
        self.metrics: list[PerformanceMetric] = []
        self.operation_stack: list[dict[str, Any]] = []
        self.process = psutil.Process()
        self.startup_time: float | None = None
        self.max_metrics = 1000  # Limit stored metrics

        # Performance targets from clinerules.md
        self.targets = {
            "startup_time": 2.0,  # < 2 seconds to interactive prompt
            "response_time": 0.5,  # < 500ms for local operations
            "memory_baseline": 100.0,  # < 100MB baseline memory footprint
            "model_loading": 5.0,  # < 5 seconds to load model list
            "file_scanning": 1.0,  # < 1 second for typical project directories
            "context_building": 2.0,  # < 2 seconds for project analysis
            "file_editing": 0.5,  # < 500ms for diff generation and validation
        }

    def get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            return self.process.memory_info().rss / 1024 / 1024
        except Exception:
            return 0.0

    def mark_startup(self) -> None:
        """Mark the application startup time."""
        self.startup_time = time.time()

    def get_startup_duration(self) -> float | None:
        """Get the time since startup in seconds."""
        if self.startup_time:
            return time.time() - self.startup_time
        return None

    @contextmanager
    def measure_sync(self, operation: str, **metadata):
        """Context manager for measuring synchronous operations."""
        start_time = time.time()
        memory_before = self.get_memory_usage()
        success = True

        try:
            yield
        except Exception as e:
            success = False
            metadata["error"] = str(e)
            raise
        finally:
            end_time = time.time()
            memory_after = self.get_memory_usage()
            duration = end_time - start_time
            memory_delta = memory_after - memory_before

            metric = PerformanceMetric(
                operation=operation,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                memory_before=memory_before,
                memory_after=memory_after,
                memory_delta=memory_delta,
                success=success,
                metadata=metadata,
            )

            self._add_metric(metric)

    @asynccontextmanager
    async def measure_async(self, operation: str, **metadata):
        """Context manager for measuring asynchronous operations."""
        start_time = time.time()
        memory_before = self.get_memory_usage()
        success = True

        try:
            yield
        except Exception as e:
            success = False
            metadata["error"] = str(e)
            raise
        finally:
            end_time = time.time()
            memory_after = self.get_memory_usage()
            duration = end_time - start_time
            memory_delta = memory_after - memory_before

            metric = PerformanceMetric(
                operation=operation,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                memory_before=memory_before,
                memory_after=memory_after,
                memory_delta=memory_delta,
                success=success,
                metadata=metadata,
            )

            self._add_metric(metric)

    def _add_metric(self, metric: PerformanceMetric) -> None:
        """Add a metric to the collection."""
        self.metrics.append(metric)

        # Limit the number of stored metrics
        if len(self.metrics) > self.max_metrics:
            self.metrics = self.metrics[-self.max_metrics :]

    def get_metrics(
        self,
        operation: str | None = None,
        last_n: int | None = None,
        since: datetime | None = None,
    ) -> list[PerformanceMetric]:
        """Get metrics with optional filtering."""
        filtered_metrics = self.metrics

        if operation:
            filtered_metrics = [m for m in filtered_metrics if m.operation == operation]

        if since:
            since_timestamp = since.timestamp()
            filtered_metrics = [
                m for m in filtered_metrics if m.start_time >= since_timestamp
            ]

        if last_n:
            filtered_metrics = filtered_metrics[-last_n:]

        return filtered_metrics

    def get_operation_stats(self, operation: str) -> dict[str, Any]:
        """Get statistical summary for a specific operation."""
        metrics = self.get_metrics(operation=operation)

        if not metrics:
            return {"count": 0}

        durations = [m.duration for m in metrics if m.success]
        memory_deltas = [m.memory_delta for m in metrics if m.success]

        if not durations:
            return {"count": len(metrics), "success_rate": 0.0}

        return {
            "count": len(metrics),
            "success_count": len(durations),
            "success_rate": len(durations) / len(metrics),
            "avg_duration": sum(durations) / len(durations),
            "min_duration": min(durations),
            "max_duration": max(durations),
            "avg_memory_delta": sum(memory_deltas) / len(memory_deltas)
            if memory_deltas
            else 0.0,
            "target": self.targets.get(operation),
            "target_met": all(
                d <= self.targets.get(operation, float("inf")) for d in durations
            ),
        }

    def check_performance_targets(self) -> dict[str, bool]:
        """Check if performance targets are being met."""
        results = {}

        for operation, _target in self.targets.items():
            stats = self.get_operation_stats(operation)
            if stats.get("count", 0) > 0:
                results[operation] = stats.get("target_met", False)

        # Check startup time separately
        if self.startup_time:
            startup_duration = self.get_startup_duration()
            if startup_duration:
                results["startup_time"] = (
                    startup_duration <= self.targets["startup_time"]
                )

        return results

    def display_performance_report(self, show_details: bool = False) -> None:
        """Display a performance report in the console."""
        if not self.metrics:
            console.print(
                Panel("No performance metrics available", title="Performance Report")
            )
            return

        # Summary table
        table = Table(title="Performance Summary")
        table.add_column("Operation", style="cyan")
        table.add_column("Count", justify="right")
        table.add_column("Success Rate", justify="right")
        table.add_column("Avg Duration", justify="right")
        table.add_column("Target", justify="right")
        table.add_column("Status", justify="center")

        # Group metrics by operation
        operations = {m.operation for m in self.metrics}

        for operation in sorted(operations):
            stats = self.get_operation_stats(operation)

            if stats["count"] == 0:
                continue

            success_rate = f"{stats['success_rate']:.1%}"
            avg_duration = f"{stats['avg_duration']:.3f}s"
            target = f"{stats.get('target', 'N/A')}"
            if target != "N/A":
                target += "s"

            # Status indicator
            if stats.get("target_met"):
                status = "✓"
                status_style = "green"
            elif stats.get("target"):
                status = "✗"
                status_style = "red"
            else:
                status = "-"
                status_style = "dim"

            table.add_row(
                operation,
                str(stats["count"]),
                success_rate,
                avg_duration,
                target,
                f"[{status_style}]{status}[/{status_style}]",
            )

        console.print(table)

        # Memory usage
        current_memory = self.get_memory_usage()
        memory_status = (
            "✓" if current_memory <= self.targets["memory_baseline"] else "✗"
        )
        memory_color = (
            "green" if current_memory <= self.targets["memory_baseline"] else "red"
        )

        console.print(
            f"\nCurrent Memory Usage: [{memory_color}]{current_memory:.1f}MB[/{memory_color}] "
            f"(Target: {self.targets['memory_baseline']}MB) [{memory_color}]{memory_status}[/{memory_color}]"
        )

        # Startup time
        if self.startup_time:
            startup_duration = self.get_startup_duration()
            if startup_duration:
                startup_status = (
                    "✓" if startup_duration <= self.targets["startup_time"] else "✗"
                )
                startup_color = (
                    "green"
                    if startup_duration <= self.targets["startup_time"]
                    else "red"
                )
                console.print(
                    f"Startup Time: [{startup_color}]{startup_duration:.3f}s[/{startup_color}] "
                    f"(Target: {self.targets['startup_time']}s) [{startup_color}]{startup_status}[/{startup_color}]"
                )

        if show_details:
            console.print("\n" + "=" * 50)
            console.print("Recent Operations (Last 10):")
            recent_metrics = self.metrics[-10:]
            for metric in recent_metrics:
                status_icon = "✓" if metric.success else "✗"
                status_color = "green" if metric.success else "red"
                console.print(
                    f"[{status_color}]{status_icon}[/{status_color}] "
                    f"{metric.operation}: {metric.duration:.3f}s "
                    f"(Memory: {metric.memory_delta:+.1f}MB)"
                )


# Global performance tracker instance
performance_tracker = PerformanceTracker()


def measure_performance(operation: str, **metadata):
    """Decorator for measuring function performance."""

    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                async with performance_tracker.measure_async(operation, **metadata):
                    return await func(*args, **kwargs)

            return async_wrapper
        else:

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                with performance_tracker.measure_sync(operation, **metadata):
                    return func(*args, **kwargs)

            return sync_wrapper

    return decorator


def log_slow_operation(operation: str, duration: float, threshold: float = 1.0) -> None:
    """Log operations that exceed performance thresholds."""
    if duration > threshold:
        target = performance_tracker.targets.get(operation)
        if target and duration > target:
            console.print(
                f"[yellow]Warning: {operation} took {duration:.3f}s "
                f"(target: {target}s)[/yellow]"
            )
