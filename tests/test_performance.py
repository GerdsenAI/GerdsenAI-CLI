"""
Tests for performance monitoring module.

Covers performance tracking, metrics collection, target checking,
and reporting functionality.
"""

import asyncio
import time
from unittest.mock import MagicMock, patch

import pytest

from gerdsenai_cli.utils.performance import (
    PerformanceMetric,
    PerformanceTracker,
    measure_performance,
    performance_tracker,
)


class TestPerformanceMetric:
    """Test suite for PerformanceMetric data structure."""

    def test_initialization(self):
        """Test metric initialization."""
        metric = PerformanceMetric(
            operation="test_op",
            start_time=1000.0,
            end_time=1001.5,
            duration=1.5,
            memory_before=50.0,
            memory_after=55.0,
            memory_delta=5.0,
            success=True,
            metadata={"key": "value"},
        )

        assert metric.operation == "test_op"
        assert metric.duration == 1.5
        assert metric.memory_delta == 5.0
        assert metric.success is True
        assert metric.metadata["key"] == "value"
        assert metric.timestamp is not None


class TestPerformanceTracker:
    """Test suite for PerformanceTracker functionality."""

    def setup_method(self):
        """Set up test tracker instance."""
        self.tracker = PerformanceTracker()

    def test_initialization(self):
        """Test tracker initialization."""
        assert len(self.tracker.metrics) == 0
        assert self.tracker.startup_time is None
        assert self.tracker.max_metrics == 1000
        assert "startup_time" in self.tracker.targets
        assert self.tracker.targets["startup_time"] == 2.0

    @patch("psutil.Process")
    def test_memory_usage_tracking(self, mock_process):
        """Test memory usage measurement."""
        # Mock psutil memory info
        mock_memory_info = MagicMock()
        mock_memory_info.rss = 104857600  # 100MB in bytes
        mock_process.return_value.memory_info.return_value = mock_memory_info

        tracker = PerformanceTracker()
        memory_mb = tracker.get_memory_usage()
        assert memory_mb == 100.0

    def test_startup_tracking(self):
        """Test startup time tracking."""
        self.tracker.mark_startup()
        assert self.tracker.startup_time is not None

        # Small delay to test duration calculation
        time.sleep(0.01)
        duration = self.tracker.get_startup_duration()
        assert duration is not None
        assert duration > 0

    @patch("psutil.Process")
    def test_sync_measurement(self, mock_process):
        """Test synchronous operation measurement."""
        mock_memory_info = MagicMock()
        mock_memory_info.rss = 104857600
        mock_process.return_value.memory_info.return_value = mock_memory_info

        with self.tracker.measure_sync("test_operation", test_param="value"):
            time.sleep(0.01)  # Simulate work

        assert len(self.tracker.metrics) == 1
        metric = self.tracker.metrics[0]
        assert metric.operation == "test_operation"
        assert metric.duration > 0
        assert metric.success is True
        assert metric.metadata["test_param"] == "value"

    @patch("psutil.Process")
    @pytest.mark.asyncio
    async def test_async_measurement(self, mock_process):
        """Test asynchronous operation measurement."""
        mock_memory_info = MagicMock()
        mock_memory_info.rss = 104857600
        mock_process.return_value.memory_info.return_value = mock_memory_info

        async with self.tracker.measure_async("async_operation"):
            await asyncio.sleep(0.01)  # Simulate async work

        assert len(self.tracker.metrics) == 1
        metric = self.tracker.metrics[0]
        assert metric.operation == "async_operation"
        assert metric.success is True

    @patch("psutil.Process")
    def test_error_handling_in_measurement(self, mock_process):
        """Test error handling during measurement."""
        mock_memory_info = MagicMock()
        mock_memory_info.rss = 104857600
        mock_process.return_value.memory_info.return_value = mock_memory_info

        with pytest.raises(ValueError):
            with self.tracker.measure_sync("error_operation"):
                raise ValueError("Test error")

        assert len(self.tracker.metrics) == 1
        metric = self.tracker.metrics[0]
        assert metric.success is False
        assert "Test error" in metric.metadata["error"]

    def test_metrics_filtering(self):
        """Test metrics filtering functionality."""
        # Add test metrics
        for i in range(5):
            metric = PerformanceMetric(
                operation=f"operation_{i % 2}",  # alternates between operation_0 and operation_1
                start_time=time.time(),
                end_time=time.time(),
                duration=0.1,
                memory_before=50.0,
                memory_after=50.0,
                memory_delta=0.0,
            )
            self.tracker._add_metric(metric)

        # Filter by operation
        op0_metrics = self.tracker.get_metrics(operation="operation_0")
        assert len(op0_metrics) == 3

        # Filter by count
        last_2_metrics = self.tracker.get_metrics(last_n=2)
        assert len(last_2_metrics) == 2

    def test_operation_statistics(self):
        """Test operation statistics calculation."""
        # Add test metrics for same operation
        for i in range(3):
            metric = PerformanceMetric(
                operation="test_op",
                start_time=time.time(),
                end_time=time.time(),
                duration=0.1 * (i + 1),  # 0.1, 0.2, 0.3
                memory_before=50.0,
                memory_after=50.0,
                memory_delta=1.0,
                success=True,
            )
            self.tracker._add_metric(metric)

        stats = self.tracker.get_operation_stats("test_op")
        assert stats["count"] == 3
        assert stats["success_rate"] == 1.0
        assert abs(stats["avg_duration"] - 0.2) < 1e-10  # (0.1 + 0.2 + 0.3) / 3
        assert stats["min_duration"] == 0.1
        assert abs(stats["max_duration"] - 0.3) < 1e-10

    def test_performance_targets_checking(self):
        """Test performance target validation."""
        # Add metric that meets target
        metric = PerformanceMetric(
            operation="startup_time",
            start_time=time.time(),
            end_time=time.time(),
            duration=1.0,  # Under 2.0s target
            memory_before=50.0,
            memory_after=50.0,
            memory_delta=0.0,
            success=True,
        )
        self.tracker._add_metric(metric)

        targets_met = self.tracker.check_performance_targets()
        assert "startup_time" in targets_met
        assert targets_met["startup_time"] is True

    def test_metrics_size_limit(self):
        """Test metrics collection size limit."""
        self.tracker.max_metrics = 3

        # Add more metrics than the limit
        for i in range(5):
            metric = PerformanceMetric(
                operation=f"op_{i}",
                start_time=time.time(),
                end_time=time.time(),
                duration=0.1,
                memory_before=50.0,
                memory_after=50.0,
                memory_delta=0.0,
            )
            self.tracker._add_metric(metric)

        # Should only keep the last 3
        assert len(self.tracker.metrics) == 3
        assert self.tracker.metrics[-1].operation == "op_4"

    @patch("rich.console.Console.print")
    def test_performance_report_display(self, mock_print):
        """Test performance report generation."""
        # Add test metric
        metric = PerformanceMetric(
            operation="test_op",
            start_time=time.time(),
            end_time=time.time(),
            duration=0.5,
            memory_before=50.0,
            memory_after=55.0,
            memory_delta=5.0,
            success=True,
        )
        self.tracker._add_metric(metric)

        self.tracker.display_performance_report()

        # Verify that print was called (report was generated)
        assert mock_print.called


class TestPerformanceDecorator:
    """Test suite for performance measurement decorator."""

    @patch("psutil.Process")
    def test_sync_function_decoration(self, mock_process):
        """Test decorator on synchronous functions."""
        mock_memory_info = MagicMock()
        mock_memory_info.rss = 104857600
        mock_process.return_value.memory_info.return_value = mock_memory_info

        @measure_performance("decorated_sync_op")
        def test_function(x, y):
            time.sleep(0.01)
            return x + y

        result = test_function(1, 2)
        assert result == 3

        # Check that metric was recorded
        metrics = performance_tracker.get_metrics(operation="decorated_sync_op")
        assert len(metrics) >= 1

    @patch("psutil.Process")
    @pytest.mark.asyncio
    async def test_async_function_decoration(self, mock_process):
        """Test decorator on asynchronous functions."""
        import asyncio

        mock_memory_info = MagicMock()
        mock_memory_info.rss = 104857600
        mock_process.return_value.memory_info.return_value = mock_memory_info

        @measure_performance("decorated_async_op")
        async def async_test_function(x, y):
            await asyncio.sleep(0.01)
            return x * y

        result = await async_test_function(3, 4)
        assert result == 12

        # Check that metric was recorded
        metrics = performance_tracker.get_metrics(operation="decorated_async_op")
        assert len(metrics) >= 1

    @patch("psutil.Process")
    def test_decorator_with_metadata(self, mock_process):
        """Test decorator with additional metadata."""
        mock_memory_info = MagicMock()
        mock_memory_info.rss = 104857600
        mock_process.return_value.memory_info.return_value = mock_memory_info

        @measure_performance("metadata_op", component="test", version="1.0")
        def test_function_with_metadata():
            return "success"

        result = test_function_with_metadata()
        assert result == "success"

        metrics = performance_tracker.get_metrics(operation="metadata_op")
        assert len(metrics) >= 1
        metric = metrics[-1]
        assert metric.metadata["component"] == "test"
        assert metric.metadata["version"] == "1.0"

    @patch("psutil.Process")
    def test_decorator_error_handling(self, mock_process):
        """Test decorator behavior when decorated function raises error."""
        mock_memory_info = MagicMock()
        mock_memory_info.rss = 104857600
        mock_process.return_value.memory_info.return_value = mock_memory_info

        @measure_performance("error_op")
        def failing_function():
            raise RuntimeError("Test error")

        with pytest.raises(RuntimeError):
            failing_function()

        # Should still record the metric with success=False
        metrics = performance_tracker.get_metrics(operation="error_op")
        assert len(metrics) >= 1
        metric = metrics[-1]
        assert metric.success is False
        assert "Test error" in metric.metadata["error"]
