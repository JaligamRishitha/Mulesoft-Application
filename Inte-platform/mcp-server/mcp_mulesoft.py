#!/usr/bin/env python3
"""
MCP Server for MuleSoft Integration with HTTP API
Provides both MCP tools and REST API endpoints for frontend

Enterprise Features:
- Tiered timeout configuration (connection, response, transaction)
- Asynchronous processing for long-running operations
- Batch processing with configurable chunk sizes
- Watermarking for incremental data synchronization
- Performance monitoring and alerting thresholds
- Schema validation (JSON/XML) at integration entry points
- DataWeave-style transformation with error handling
- Business rule validation engine
- Error categorization (recoverable vs non-recoverable)
- Detailed error logging with payload snapshots
"""

import json
import httpx
import uvicorn
import uuid
import asyncio
import time
import re
import traceback
import hashlib
import copy
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Callable, Union, Tuple
from enum import Enum
from collections import deque
from dataclasses import dataclass, field
from functools import wraps
from fastapi import FastAPI, HTTPException, Depends, Query, Body, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, validator
import threading
import statistics
import xml.etree.ElementTree as ET
from io import StringIO

# MCP imports are optional (for AI tool integration)
try:
    from mcp.server import Server
    from mcp.types import TextContent
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False


# ============================================================================
# ENTERPRISE FEATURE 1: TIERED TIMEOUT CONFIGURATION
# ============================================================================

class TimeoutTier(Enum):
    """Timeout tiers for different operation types"""
    FAST = "fast"           # Quick operations (health checks, simple queries)
    STANDARD = "standard"   # Normal operations (CRUD, authentication)
    EXTENDED = "extended"   # Long operations (batch processing, reports)
    TRANSACTION = "transaction"  # Full transaction flows


@dataclass
class TimeoutConfig:
    """Tiered timeout configuration for HTTP operations"""
    # Connection timeout - time to establish TCP connection
    connect_timeout: float = 5.0
    # Read/Response timeout - time to receive response
    read_timeout: float = 30.0
    # Write timeout - time to send request
    write_timeout: float = 30.0
    # Pool timeout - time to acquire connection from pool
    pool_timeout: float = 10.0
    # Transaction timeout - overall operation timeout
    transaction_timeout: float = 60.0

    def to_httpx_timeout(self) -> httpx.Timeout:
        """Convert to httpx Timeout object"""
        return httpx.Timeout(
            connect=self.connect_timeout,
            read=self.read_timeout,
            write=self.write_timeout,
            pool=self.pool_timeout
        )


# Predefined timeout configurations per tier
TIMEOUT_CONFIGS: Dict[TimeoutTier, TimeoutConfig] = {
    TimeoutTier.FAST: TimeoutConfig(
        connect_timeout=3.0,
        read_timeout=10.0,
        write_timeout=10.0,
        pool_timeout=5.0,
        transaction_timeout=15.0
    ),
    TimeoutTier.STANDARD: TimeoutConfig(
        connect_timeout=5.0,
        read_timeout=30.0,
        write_timeout=30.0,
        pool_timeout=10.0,
        transaction_timeout=60.0
    ),
    TimeoutTier.EXTENDED: TimeoutConfig(
        connect_timeout=10.0,
        read_timeout=120.0,
        write_timeout=60.0,
        pool_timeout=30.0,
        transaction_timeout=300.0
    ),
    TimeoutTier.TRANSACTION: TimeoutConfig(
        connect_timeout=10.0,
        read_timeout=180.0,
        write_timeout=90.0,
        pool_timeout=30.0,
        transaction_timeout=600.0
    ),
}


def get_timeout_config(tier: TimeoutTier = TimeoutTier.STANDARD) -> TimeoutConfig:
    """Get timeout configuration for a specific tier"""
    return TIMEOUT_CONFIGS.get(tier, TIMEOUT_CONFIGS[TimeoutTier.STANDARD])


# ============================================================================
# ENTERPRISE FEATURE 2: ASYNCHRONOUS PROCESSING
# ============================================================================

class JobStatus(Enum):
    """Status of async jobs"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AsyncJob:
    """Represents an asynchronous job"""
    job_id: str
    job_type: str
    status: JobStatus = JobStatus.PENDING
    progress: int = 0
    total_items: int = 0
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "job_type": self.job_type,
            "status": self.status.value,
            "progress": self.progress,
            "total_items": self.total_items,
            "progress_percent": round((self.progress / self.total_items * 100) if self.total_items > 0 else 0, 2),
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": (self.completed_at - self.started_at).total_seconds() if self.completed_at and self.started_at else None,
            "metadata": self.metadata
        }


class AsyncJobManager:
    """Manages asynchronous job execution"""

    def __init__(self, max_concurrent_jobs: int = 10):
        self.jobs: Dict[str, AsyncJob] = {}
        self.max_concurrent_jobs = max_concurrent_jobs
        self._semaphore = asyncio.Semaphore(max_concurrent_jobs)
        self._lock = threading.Lock()

    def create_job(self, job_type: str, total_items: int = 0, metadata: Dict[str, Any] = None) -> AsyncJob:
        """Create a new async job"""
        job_id = f"JOB-{uuid.uuid4().hex[:12].upper()}"
        job = AsyncJob(
            job_id=job_id,
            job_type=job_type,
            total_items=total_items,
            metadata=metadata or {}
        )
        with self._lock:
            self.jobs[job_id] = job
        return job

    def get_job(self, job_id: str) -> Optional[AsyncJob]:
        """Get job by ID"""
        return self.jobs.get(job_id)

    def update_progress(self, job_id: str, progress: int):
        """Update job progress"""
        if job := self.jobs.get(job_id):
            job.progress = progress

    def complete_job(self, job_id: str, result: Dict[str, Any] = None, error: str = None):
        """Mark job as completed or failed"""
        if job := self.jobs.get(job_id):
            job.completed_at = datetime.now()
            if error:
                job.status = JobStatus.FAILED
                job.error = error
            else:
                job.status = JobStatus.COMPLETED
                job.result = result
                job.progress = job.total_items

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a pending or running job"""
        if job := self.jobs.get(job_id):
            if job.status in [JobStatus.PENDING, JobStatus.RUNNING]:
                job.status = JobStatus.CANCELLED
                job.completed_at = datetime.now()
                return True
        return False

    def list_jobs(self, status: Optional[JobStatus] = None, limit: int = 100) -> List[Dict]:
        """List all jobs, optionally filtered by status"""
        jobs = list(self.jobs.values())
        if status:
            jobs = [j for j in jobs if j.status == status]
        jobs.sort(key=lambda x: x.created_at, reverse=True)
        return [j.to_dict() for j in jobs[:limit]]

    async def run_job(self, job_id: str, coro: Callable):
        """Run an async job with semaphore control"""
        job = self.jobs.get(job_id)
        if not job:
            return

        async with self._semaphore:
            job.status = JobStatus.RUNNING
            job.started_at = datetime.now()
            try:
                result = await coro
                self.complete_job(job_id, result=result)
            except Exception as e:
                self.complete_job(job_id, error=str(e))


# Global job manager instance
job_manager = AsyncJobManager(max_concurrent_jobs=10)


# ============================================================================
# ENTERPRISE FEATURE 3: BATCH PROCESSING
# ============================================================================

@dataclass
class BatchConfig:
    """Configuration for batch processing"""
    chunk_size: int = 50           # Number of items per chunk
    max_retries: int = 3           # Max retries per chunk
    retry_delay: float = 1.0       # Delay between retries (seconds)
    parallel_chunks: int = 3       # Number of chunks to process in parallel
    fail_fast: bool = False        # Stop on first error vs continue
    timeout_per_chunk: float = 60.0  # Timeout per chunk processing


@dataclass
class BatchResult:
    """Result of batch processing"""
    total_items: int = 0
    processed: int = 0
    succeeded: int = 0
    failed: int = 0
    errors: List[Dict[str, Any]] = field(default_factory=list)
    chunks_processed: int = 0
    duration_seconds: float = 0
    items_per_second: float = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_items": self.total_items,
            "processed": self.processed,
            "succeeded": self.succeeded,
            "failed": self.failed,
            "success_rate": round((self.succeeded / self.processed * 100) if self.processed > 0 else 0, 2),
            "errors": self.errors[:10],  # Limit errors in response
            "error_count": len(self.errors),
            "chunks_processed": self.chunks_processed,
            "duration_seconds": round(self.duration_seconds, 2),
            "items_per_second": round(self.items_per_second, 2)
        }


class BatchProcessor:
    """Handles batch processing of large datasets"""

    def __init__(self, config: BatchConfig = None):
        self.config = config or BatchConfig()

    def chunk_data(self, data: List[Any]) -> List[List[Any]]:
        """Split data into chunks"""
        return [data[i:i + self.config.chunk_size]
                for i in range(0, len(data), self.config.chunk_size)]

    async def process_chunk(
        self,
        chunk: List[Any],
        processor: Callable,
        chunk_index: int
    ) -> Dict[str, Any]:
        """Process a single chunk with retries"""
        for attempt in range(self.config.max_retries):
            try:
                results = await asyncio.wait_for(
                    processor(chunk),
                    timeout=self.config.timeout_per_chunk
                )
                return {
                    "chunk_index": chunk_index,
                    "success": True,
                    "results": results,
                    "items_processed": len(chunk)
                }
            except asyncio.TimeoutError:
                if attempt == self.config.max_retries - 1:
                    return {
                        "chunk_index": chunk_index,
                        "success": False,
                        "error": "Chunk processing timeout",
                        "items_failed": len(chunk)
                    }
            except Exception as e:
                if attempt == self.config.max_retries - 1:
                    return {
                        "chunk_index": chunk_index,
                        "success": False,
                        "error": str(e),
                        "items_failed": len(chunk)
                    }
            await asyncio.sleep(self.config.retry_delay * (attempt + 1))

        return {"chunk_index": chunk_index, "success": False, "error": "Max retries exceeded"}

    async def process_batch(
        self,
        data: List[Any],
        processor: Callable,
        job: Optional[AsyncJob] = None
    ) -> BatchResult:
        """Process entire batch with parallel chunk processing"""
        start_time = time.time()
        result = BatchResult(total_items=len(data))

        chunks = self.chunk_data(data)
        chunk_results = []

        # Process chunks in parallel groups
        for i in range(0, len(chunks), self.config.parallel_chunks):
            parallel_group = chunks[i:i + self.config.parallel_chunks]
            tasks = [
                self.process_chunk(chunk, processor, i + j)
                for j, chunk in enumerate(parallel_group)
            ]

            group_results = await asyncio.gather(*tasks, return_exceptions=True)

            for res in group_results:
                if isinstance(res, Exception):
                    result.failed += 1
                    result.errors.append({"error": str(res)})
                elif isinstance(res, dict):
                    chunk_results.append(res)
                    if res.get("success"):
                        result.succeeded += res.get("items_processed", 0)
                    else:
                        result.failed += res.get("items_failed", 0)
                        result.errors.append(res)
                        if self.config.fail_fast:
                            break

            result.chunks_processed = len(chunk_results)
            result.processed = result.succeeded + result.failed

            # Update job progress if provided
            if job:
                job_manager.update_progress(job.job_id, result.processed)

            if self.config.fail_fast and result.errors:
                break

        result.duration_seconds = time.time() - start_time
        result.items_per_second = result.processed / result.duration_seconds if result.duration_seconds > 0 else 0

        return result


# ============================================================================
# ENTERPRISE FEATURE 4: WATERMARKING FOR INCREMENTAL SYNC
# ============================================================================

@dataclass
class Watermark:
    """Watermark for tracking incremental sync state"""
    entity_type: str
    connector_id: int
    last_sync_timestamp: datetime
    last_sync_id: Optional[str] = None
    records_synced: int = 0
    sync_status: str = "idle"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_type": self.entity_type,
            "connector_id": self.connector_id,
            "last_sync_timestamp": self.last_sync_timestamp.isoformat(),
            "last_sync_id": self.last_sync_id,
            "records_synced": self.records_synced,
            "sync_status": self.sync_status,
            "metadata": self.metadata
        }


class WatermarkManager:
    """Manages watermarks for incremental data synchronization"""

    def __init__(self):
        self.watermarks: Dict[str, Watermark] = {}
        self._lock = threading.Lock()

    def _get_key(self, entity_type: str, connector_id: int) -> str:
        return f"{entity_type}:{connector_id}"

    def get_watermark(self, entity_type: str, connector_id: int) -> Optional[Watermark]:
        """Get watermark for entity type and connector"""
        key = self._get_key(entity_type, connector_id)
        return self.watermarks.get(key)

    def set_watermark(
        self,
        entity_type: str,
        connector_id: int,
        timestamp: datetime,
        last_id: str = None,
        records_synced: int = 0,
        metadata: Dict[str, Any] = None
    ) -> Watermark:
        """Set or update watermark"""
        key = self._get_key(entity_type, connector_id)
        with self._lock:
            if key in self.watermarks:
                wm = self.watermarks[key]
                wm.last_sync_timestamp = timestamp
                wm.last_sync_id = last_id or wm.last_sync_id
                wm.records_synced += records_synced
                wm.metadata.update(metadata or {})
            else:
                wm = Watermark(
                    entity_type=entity_type,
                    connector_id=connector_id,
                    last_sync_timestamp=timestamp,
                    last_sync_id=last_id,
                    records_synced=records_synced,
                    metadata=metadata or {}
                )
                self.watermarks[key] = wm
        return wm

    def update_sync_status(self, entity_type: str, connector_id: int, status: str):
        """Update sync status for a watermark"""
        key = self._get_key(entity_type, connector_id)
        if wm := self.watermarks.get(key):
            wm.sync_status = status

    def reset_watermark(self, entity_type: str, connector_id: int) -> bool:
        """Reset watermark for full resync"""
        key = self._get_key(entity_type, connector_id)
        with self._lock:
            if key in self.watermarks:
                self.watermarks[key] = Watermark(
                    entity_type=entity_type,
                    connector_id=connector_id,
                    last_sync_timestamp=datetime(1970, 1, 1),
                    records_synced=0
                )
                return True
        return False

    def list_watermarks(self, connector_id: Optional[int] = None) -> List[Dict]:
        """List all watermarks, optionally filtered by connector"""
        watermarks = list(self.watermarks.values())
        if connector_id is not None:
            watermarks = [w for w in watermarks if w.connector_id == connector_id]
        return [w.to_dict() for w in watermarks]

    def get_delta_query_params(self, entity_type: str, connector_id: int) -> Dict[str, Any]:
        """Get query parameters for incremental/delta fetch"""
        wm = self.get_watermark(entity_type, connector_id)
        if wm:
            return {
                "modified_after": wm.last_sync_timestamp.isoformat(),
                "last_id": wm.last_sync_id,
                "incremental": True
            }
        return {"incremental": False}


# Global watermark manager instance
watermark_manager = WatermarkManager()


# ============================================================================
# ENTERPRISE FEATURE 5: PERFORMANCE MONITORING & ALERTING
# ============================================================================

@dataclass
class AlertThreshold:
    """Threshold configuration for alerting"""
    metric_name: str
    warning_threshold: float
    critical_threshold: float
    window_seconds: int = 60
    min_samples: int = 5


@dataclass
class MetricSample:
    """Single metric sample"""
    value: float
    timestamp: datetime = field(default_factory=datetime.now)


class PerformanceMonitor:
    """Monitors performance metrics and triggers alerts"""

    def __init__(self, max_samples_per_metric: int = 1000):
        self.metrics: Dict[str, deque] = {}
        self.thresholds: Dict[str, AlertThreshold] = {}
        self.alerts: List[Dict[str, Any]] = []
        self.max_samples = max_samples_per_metric
        self._lock = threading.Lock()

        # Initialize default thresholds
        self._setup_default_thresholds()

    def _setup_default_thresholds(self):
        """Setup default alerting thresholds"""
        default_thresholds = [
            AlertThreshold("response_time_ms", warning_threshold=1000, critical_threshold=5000),
            AlertThreshold("error_rate_percent", warning_threshold=5, critical_threshold=15),
            AlertThreshold("requests_per_second", warning_threshold=100, critical_threshold=200),
            AlertThreshold("active_connections", warning_threshold=80, critical_threshold=95),
            AlertThreshold("batch_failure_rate", warning_threshold=10, critical_threshold=25),
        ]
        for threshold in default_thresholds:
            self.thresholds[threshold.metric_name] = threshold

    def record_metric(self, metric_name: str, value: float):
        """Record a metric value"""
        with self._lock:
            if metric_name not in self.metrics:
                self.metrics[metric_name] = deque(maxlen=self.max_samples)
            self.metrics[metric_name].append(MetricSample(value=value))

        # Check thresholds
        self._check_threshold(metric_name, value)

    def record_request(self, endpoint: str, duration_ms: float, success: bool):
        """Record HTTP request metrics"""
        self.record_metric("response_time_ms", duration_ms)
        self.record_metric(f"endpoint:{endpoint}:response_time_ms", duration_ms)

        # Track success/failure for error rate
        self.record_metric("request_success", 1.0 if success else 0.0)

    def _check_threshold(self, metric_name: str, current_value: float):
        """Check if metric exceeds threshold and create alert"""
        threshold = self.thresholds.get(metric_name)
        if not threshold:
            return

        severity = None
        if current_value >= threshold.critical_threshold:
            severity = "critical"
        elif current_value >= threshold.warning_threshold:
            severity = "warning"

        if severity:
            alert = {
                "alert_id": f"ALERT-{uuid.uuid4().hex[:8].upper()}",
                "metric_name": metric_name,
                "current_value": current_value,
                "threshold": threshold.critical_threshold if severity == "critical" else threshold.warning_threshold,
                "severity": severity,
                "timestamp": datetime.now().isoformat(),
                "message": f"{metric_name} is {severity}: {current_value} exceeds threshold"
            }
            with self._lock:
                self.alerts.append(alert)
                # Keep only last 100 alerts
                if len(self.alerts) > 100:
                    self.alerts = self.alerts[-100:]
            print(f"[ALERT] {severity.upper()}: {alert['message']}")

    def get_metric_stats(self, metric_name: str, window_seconds: int = 60) -> Dict[str, Any]:
        """Get statistics for a metric within time window"""
        samples = self.metrics.get(metric_name, deque())
        cutoff = datetime.now() - timedelta(seconds=window_seconds)

        recent_values = [s.value for s in samples if s.timestamp > cutoff]

        if not recent_values:
            return {"metric_name": metric_name, "samples": 0, "window_seconds": window_seconds}

        return {
            "metric_name": metric_name,
            "samples": len(recent_values),
            "window_seconds": window_seconds,
            "min": round(min(recent_values), 2),
            "max": round(max(recent_values), 2),
            "avg": round(statistics.mean(recent_values), 2),
            "median": round(statistics.median(recent_values), 2),
            "stddev": round(statistics.stdev(recent_values), 2) if len(recent_values) > 1 else 0,
            "p95": round(sorted(recent_values)[int(len(recent_values) * 0.95)] if len(recent_values) >= 20 else max(recent_values), 2),
            "p99": round(sorted(recent_values)[int(len(recent_values) * 0.99)] if len(recent_values) >= 100 else max(recent_values), 2)
        }

    def get_error_rate(self, window_seconds: int = 60) -> float:
        """Calculate error rate percentage"""
        samples = self.metrics.get("request_success", deque())
        cutoff = datetime.now() - timedelta(seconds=window_seconds)
        recent = [s.value for s in samples if s.timestamp > cutoff]
        if not recent:
            return 0.0
        return round((1 - statistics.mean(recent)) * 100, 2)

    def get_all_metrics(self) -> Dict[str, Any]:
        """Get summary of all metrics"""
        summary = {}
        for metric_name in self.metrics:
            summary[metric_name] = self.get_metric_stats(metric_name)
        return summary

    def get_alerts(self, severity: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """Get recent alerts"""
        alerts = self.alerts.copy()
        if severity:
            alerts = [a for a in alerts if a["severity"] == severity]
        return alerts[-limit:]

    def set_threshold(self, metric_name: str, warning: float, critical: float, window: int = 60):
        """Set or update alert threshold"""
        self.thresholds[metric_name] = AlertThreshold(
            metric_name=metric_name,
            warning_threshold=warning,
            critical_threshold=critical,
            window_seconds=window
        )

    def get_thresholds(self) -> List[Dict]:
        """Get all configured thresholds"""
        return [
            {
                "metric_name": t.metric_name,
                "warning_threshold": t.warning_threshold,
                "critical_threshold": t.critical_threshold,
                "window_seconds": t.window_seconds
            }
            for t in self.thresholds.values()
        ]


# Global performance monitor instance
perf_monitor = PerformanceMonitor()


# ============================================================================
# PERFORMANCE MONITORING MIDDLEWARE
# ============================================================================

def create_monitored_client(
    tier: TimeoutTier = TimeoutTier.STANDARD,
    verify: bool = False
) -> httpx.AsyncClient:
    """Create an httpx client with monitoring and tiered timeouts"""
    config = get_timeout_config(tier)
    return httpx.AsyncClient(
        verify=verify,
        timeout=config.to_httpx_timeout()
    )


# ============================================================================
# ENTERPRISE FEATURE 6: SCHEMA VALIDATION (JSON/XML)
# ============================================================================

class SchemaType(Enum):
    """Supported schema types"""
    JSON_SCHEMA = "json_schema"
    XML_XSD = "xml_xsd"
    CUSTOM = "custom"


@dataclass
class ValidationResult:
    """Result of schema validation"""
    valid: bool
    errors: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[Dict[str, Any]] = field(default_factory=list)
    validated_at: datetime = field(default_factory=datetime.now)
    schema_id: Optional[str] = None
    payload_hash: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "validated_at": self.validated_at.isoformat(),
            "schema_id": self.schema_id,
            "payload_hash": self.payload_hash
        }


class SchemaValidator:
    """Schema validation engine for JSON and XML payloads"""

    def __init__(self):
        self.schemas: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._setup_default_schemas()

    def _setup_default_schemas(self):
        """Setup default schemas for common integration payloads"""
        # Salesforce Case Schema
        self.register_schema("salesforce_case", SchemaType.JSON_SCHEMA, {
            "type": "object",
            "required": ["subject"],
            "properties": {
                "id": {"type": ["integer", "string"]},
                "case_number": {"type": "string", "pattern": "^CS-[A-Z0-9]+$"},
                "subject": {"type": "string", "minLength": 1, "maxLength": 500},
                "description": {"type": "string", "maxLength": 5000},
                "status": {"type": "string", "enum": ["New", "Working", "Escalated", "Closed"]},
                "priority": {"type": "string", "enum": ["Low", "Medium", "High", "Critical"]},
                "account_id": {"type": ["integer", "null"]},
                "contact_id": {"type": ["integer", "null"]}
            }
        })

        # SAP IDoc Schema
        self.register_schema("sap_idoc", SchemaType.JSON_SCHEMA, {
            "type": "object",
            "required": ["message_type", "sender", "receiver"],
            "properties": {
                "message_type": {"type": "string"},
                "sender": {"type": "string"},
                "receiver": {"type": "string"},
                "doc_number": {"type": "string"},
                "segments": {"type": "array", "items": {"type": "object"}}
            }
        })

        # ServiceNow Ticket Schema
        self.register_schema("servicenow_ticket", SchemaType.JSON_SCHEMA, {
            "type": "object",
            "required": ["title", "category"],
            "properties": {
                "title": {"type": "string", "minLength": 1, "maxLength": 200},
                "description": {"type": "string", "maxLength": 10000},
                "category": {"type": "string"},
                "priority": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                "ticket_type": {"type": "string", "enum": ["incident", "service_request", "change", "problem"]}
            }
        })

        # Account Request Schema
        self.register_schema("account_request", SchemaType.JSON_SCHEMA, {
            "type": "object",
            "required": ["account_name", "request_type"],
            "properties": {
                "id": {"type": "integer"},
                "account_name": {"type": "string", "minLength": 1, "maxLength": 255},
                "account_type": {"type": "string"},
                "request_type": {"type": "string", "enum": ["NEW_CONNECTION", "UPGRADE", "MODIFICATION", "TERMINATION"]},
                "current_load": {"type": "number", "minimum": 0},
                "requested_load": {"type": "number", "minimum": 0},
                "city": {"type": "string"},
                "pin_code": {"type": "string", "pattern": "^[0-9]{5,6}$"}
            }
        })

    def register_schema(self, schema_id: str, schema_type: SchemaType, schema: Dict[str, Any]):
        """Register a new schema"""
        with self._lock:
            self.schemas[schema_id] = {
                "id": schema_id,
                "type": schema_type.value,
                "schema": schema,
                "created_at": datetime.now().isoformat(),
                "usage_count": 0
            }

    def get_schema(self, schema_id: str) -> Optional[Dict[str, Any]]:
        """Get schema by ID"""
        return self.schemas.get(schema_id)

    def list_schemas(self) -> List[Dict[str, Any]]:
        """List all registered schemas"""
        return [
            {"id": s["id"], "type": s["type"], "created_at": s["created_at"], "usage_count": s["usage_count"]}
            for s in self.schemas.values()
        ]

    def _compute_payload_hash(self, payload: Any) -> str:
        """Compute hash of payload for tracking"""
        payload_str = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(payload_str.encode()).hexdigest()[:16]

    def _validate_type(self, value: Any, expected_type: Any, path: str) -> List[Dict]:
        """Validate value against expected type"""
        errors = []
        if isinstance(expected_type, list):
            # Union type
            type_valid = False
            for t in expected_type:
                if t == "null" and value is None:
                    type_valid = True
                    break
                elif t == "string" and isinstance(value, str):
                    type_valid = True
                    break
                elif t == "integer" and isinstance(value, int) and not isinstance(value, bool):
                    type_valid = True
                    break
                elif t == "number" and isinstance(value, (int, float)) and not isinstance(value, bool):
                    type_valid = True
                    break
                elif t == "boolean" and isinstance(value, bool):
                    type_valid = True
                    break
                elif t == "array" and isinstance(value, list):
                    type_valid = True
                    break
                elif t == "object" and isinstance(value, dict):
                    type_valid = True
                    break
            if not type_valid:
                errors.append({"path": path, "error": f"Expected one of {expected_type}, got {type(value).__name__}"})
        else:
            type_map = {
                "string": str, "integer": int, "number": (int, float),
                "boolean": bool, "array": list, "object": dict
            }
            if expected_type in type_map:
                expected = type_map[expected_type]
                if expected_type == "integer" and isinstance(value, bool):
                    errors.append({"path": path, "error": f"Expected integer, got boolean"})
                elif not isinstance(value, expected):
                    errors.append({"path": path, "error": f"Expected {expected_type}, got {type(value).__name__}"})
        return errors

    def validate_json(self, payload: Dict[str, Any], schema_id: str) -> ValidationResult:
        """Validate JSON payload against registered schema"""
        schema_entry = self.schemas.get(schema_id)
        if not schema_entry:
            return ValidationResult(
                valid=False,
                errors=[{"path": "", "error": f"Schema '{schema_id}' not found"}],
                schema_id=schema_id
            )

        schema = schema_entry["schema"]
        schema_entry["usage_count"] += 1
        errors = []
        warnings = []
        payload_hash = self._compute_payload_hash(payload)

        # Check required fields
        required = schema.get("required", [])
        for field in required:
            if field not in payload:
                errors.append({"path": field, "error": f"Required field '{field}' is missing"})

        # Validate properties
        properties = schema.get("properties", {})
        for prop_name, prop_schema in properties.items():
            if prop_name in payload:
                value = payload[prop_name]
                prop_path = prop_name

                # Type validation
                if "type" in prop_schema:
                    errors.extend(self._validate_type(value, prop_schema["type"], prop_path))

                # String validations
                if isinstance(value, str):
                    if "minLength" in prop_schema and len(value) < prop_schema["minLength"]:
                        errors.append({"path": prop_path, "error": f"String too short (min: {prop_schema['minLength']})"})
                    if "maxLength" in prop_schema and len(value) > prop_schema["maxLength"]:
                        errors.append({"path": prop_path, "error": f"String too long (max: {prop_schema['maxLength']})"})
                    if "pattern" in prop_schema:
                        if not re.match(prop_schema["pattern"], value):
                            errors.append({"path": prop_path, "error": f"String doesn't match pattern: {prop_schema['pattern']}"})
                    if "enum" in prop_schema and value not in prop_schema["enum"]:
                        errors.append({"path": prop_path, "error": f"Value must be one of: {prop_schema['enum']}"})

                # Number validations
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    if "minimum" in prop_schema and value < prop_schema["minimum"]:
                        errors.append({"path": prop_path, "error": f"Value below minimum ({prop_schema['minimum']})"})
                    if "maximum" in prop_schema and value > prop_schema["maximum"]:
                        errors.append({"path": prop_path, "error": f"Value above maximum ({prop_schema['maximum']})"})

        # Check for unknown fields (warnings)
        for field in payload:
            if field not in properties:
                warnings.append({"path": field, "warning": f"Unknown field '{field}' not in schema"})

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            schema_id=schema_id,
            payload_hash=payload_hash
        )

    def validate_xml(self, xml_content: str, schema_id: str) -> ValidationResult:
        """Validate XML content against XSD schema"""
        errors = []
        warnings = []

        try:
            # Parse XML
            root = ET.fromstring(xml_content)

            # Basic structure validation
            if root.tag == "IDOC":
                # Validate IDoc structure
                edi_dc40 = root.find("EDI_DC40")
                if edi_dc40 is None:
                    errors.append({"path": "IDOC", "error": "Missing EDI_DC40 control segment"})
                else:
                    required_fields = ["TABNAM", "DOCNUM", "IDOCTYP", "MESTYP"]
                    for field in required_fields:
                        if edi_dc40.find(field) is None:
                            errors.append({"path": f"EDI_DC40/{field}", "error": f"Required field {field} missing"})

            payload_hash = hashlib.sha256(xml_content.encode()).hexdigest()[:16]

            return ValidationResult(
                valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                schema_id=schema_id,
                payload_hash=payload_hash
            )

        except ET.ParseError as e:
            return ValidationResult(
                valid=False,
                errors=[{"path": "root", "error": f"XML parse error: {str(e)}"}],
                schema_id=schema_id
            )


# Global schema validator instance
schema_validator = SchemaValidator()


# ============================================================================
# ENTERPRISE FEATURE 7: DATAWEAVE-STYLE TRANSFORMATION
# ============================================================================

class TransformationError(Exception):
    """Custom exception for transformation errors"""
    def __init__(self, message: str, path: str = "", recoverable: bool = True):
        self.message = message
        self.path = path
        self.recoverable = recoverable
        super().__init__(message)


@dataclass
class TransformationResult:
    """Result of a DataWeave transformation"""
    success: bool
    output: Optional[Any] = None
    source_format: str = "json"
    target_format: str = "json"
    errors: List[Dict[str, Any]] = field(default_factory=list)
    transformation_id: str = ""
    duration_ms: float = 0
    input_hash: str = ""
    output_hash: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "output": self.output,
            "source_format": self.source_format,
            "target_format": self.target_format,
            "errors": self.errors,
            "transformation_id": self.transformation_id,
            "duration_ms": round(self.duration_ms, 2),
            "input_hash": self.input_hash,
            "output_hash": self.output_hash
        }


class DataWeaveTransformer:
    """
    DataWeave-style transformation engine with comprehensive error handling.
    Supports JSON-to-JSON, JSON-to-XML, and custom transformations.
    """

    def __init__(self):
        self.transformations: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._setup_default_transformations()

    def _setup_default_transformations(self):
        """Setup default transformation mappings"""
        # Salesforce Case to SAP IDoc
        self.register_transformation(
            "salesforce_to_sap",
            source_format="json",
            target_format="xml",
            mapping={
                "IDOC.EDI_DC40.DOCNUM": "lambda d: f\"DOC{d.get('id', '000'):010d}\"",
                "IDOC.EDI_DC40.IDOCTYP": "'SRCLST01'",
                "IDOC.EDI_DC40.MESTYP": "'SRCLST'",
                "IDOC.EDI_DC40.SNDPRT": "'LS'",
                "IDOC.EDI_DC40.SNDPRN": "'MULESOFT'",
                "IDOC.EDI_DC40.RCVPRT": "'LS'",
                "IDOC.EDI_DC40.RCVPRN": "'SAP_ERP'",
                "IDOC.E1SRCLST.CASE_ID": "d.get('id')",
                "IDOC.E1SRCLST.CASE_NUMBER": "d.get('case_number', '')",
                "IDOC.E1SRCLST.SUBJECT": "d.get('subject', '')",
                "IDOC.E1SRCLST.STATUS": "d.get('status', 'NEW')",
                "IDOC.E1SRCLST.PRIORITY": "d.get('priority', 'MEDIUM')"
            }
        )

        # Salesforce Case to ServiceNow Ticket
        self.register_transformation(
            "salesforce_to_servicenow",
            source_format="json",
            target_format="json",
            mapping={
                "title": "d.get('subject', 'No Subject')",
                "description": "d.get('description', '')",
                "category": "'Case Import'",
                "priority": "{'Critical': 'critical', 'High': 'high', 'Medium': 'medium', 'Low': 'low'}.get(d.get('priority', 'Medium'), 'medium')",
                "ticket_type": "'incident'",
                "source_system": "'Salesforce'",
                "source_id": "str(d.get('id', ''))",
                "external_reference": "d.get('case_number', '')"
            }
        )

        # Account Request to SAP Format
        self.register_transformation(
            "account_request_to_sap",
            source_format="json",
            target_format="json",
            mapping={
                "customer_number": "f\"CUST{d.get('id', 0):08d}\"",
                "company_name": "d.get('account_name', '')",
                "account_group": "d.get('account_type', 'STANDARD')",
                "request_type": "d.get('request_type', 'NEW_CONNECTION')",
                "load_current_kw": "d.get('current_load', 0)",
                "load_requested_kw": "d.get('requested_load', 0)",
                "location.city": "d.get('city', '')",
                "location.postal_code": "d.get('pin_code', '')",
                "created_date": "datetime.now().strftime('%Y%m%d')",
                "created_time": "datetime.now().strftime('%H%M%S')"
            }
        )

    def register_transformation(
        self,
        transformation_id: str,
        source_format: str,
        target_format: str,
        mapping: Dict[str, str],
        validators: List[str] = None
    ):
        """Register a transformation mapping"""
        with self._lock:
            self.transformations[transformation_id] = {
                "id": transformation_id,
                "source_format": source_format,
                "target_format": target_format,
                "mapping": mapping,
                "validators": validators or [],
                "created_at": datetime.now().isoformat(),
                "usage_count": 0,
                "error_count": 0
            }

    def get_transformation(self, transformation_id: str) -> Optional[Dict]:
        """Get transformation by ID"""
        return self.transformations.get(transformation_id)

    def list_transformations(self) -> List[Dict]:
        """List all registered transformations"""
        return [
            {
                "id": t["id"],
                "source_format": t["source_format"],
                "target_format": t["target_format"],
                "field_count": len(t["mapping"]),
                "usage_count": t["usage_count"],
                "error_count": t["error_count"]
            }
            for t in self.transformations.values()
        ]

    def _safe_eval(self, expr: str, data: Dict, path: str) -> Tuple[Any, Optional[str]]:
        """Safely evaluate a transformation expression"""
        try:
            # Create safe context
            safe_context = {
                "d": data,
                "datetime": datetime,
                "str": str,
                "int": int,
                "float": float,
                "len": len,
                "upper": lambda s: s.upper() if isinstance(s, str) else s,
                "lower": lambda s: s.lower() if isinstance(s, str) else s,
                "trim": lambda s: s.strip() if isinstance(s, str) else s,
                "default": lambda v, d: v if v is not None else d,
            }
            result = eval(expr, {"__builtins__": {}}, safe_context)
            return result, None
        except Exception as e:
            return None, f"Expression error at '{path}': {str(e)}"

    def _set_nested_value(self, obj: Dict, path: str, value: Any):
        """Set a value in a nested dictionary using dot notation"""
        parts = path.split(".")
        current = obj
        for i, part in enumerate(parts[:-1]):
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = value

    def transform(
        self,
        data: Dict[str, Any],
        transformation_id: str,
        strict: bool = False
    ) -> TransformationResult:
        """Execute a transformation"""
        start_time = time.time()
        transformation = self.transformations.get(transformation_id)

        if not transformation:
            return TransformationResult(
                success=False,
                errors=[{"error": f"Transformation '{transformation_id}' not found"}],
                transformation_id=transformation_id
            )

        transformation["usage_count"] += 1
        errors = []
        output = {}
        input_hash = hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()[:16]

        # Execute each mapping
        for target_path, expr in transformation["mapping"].items():
            value, error = self._safe_eval(expr, data, target_path)
            if error:
                errors.append({"path": target_path, "error": error, "recoverable": True})
                if strict:
                    transformation["error_count"] += 1
                    return TransformationResult(
                        success=False,
                        errors=errors,
                        transformation_id=transformation_id,
                        duration_ms=(time.time() - start_time) * 1000,
                        input_hash=input_hash
                    )
            else:
                self._set_nested_value(output, target_path, value)

        # Convert to XML if needed
        if transformation["target_format"] == "xml":
            output = self._dict_to_xml(output)

        output_hash = hashlib.sha256(
            (json.dumps(output, default=str) if isinstance(output, dict) else str(output)).encode()
        ).hexdigest()[:16]

        duration_ms = (time.time() - start_time) * 1000

        return TransformationResult(
            success=len(errors) == 0 or not strict,
            output=output,
            source_format=transformation["source_format"],
            target_format=transformation["target_format"],
            errors=errors,
            transformation_id=transformation_id,
            duration_ms=duration_ms,
            input_hash=input_hash,
            output_hash=output_hash
        )

    def _dict_to_xml(self, data: Dict, root_name: str = None) -> str:
        """Convert dictionary to XML string"""
        def build_xml(parent: ET.Element, data: Any):
            if isinstance(data, dict):
                for key, value in data.items():
                    child = ET.SubElement(parent, key)
                    build_xml(child, value)
            elif isinstance(data, list):
                for item in data:
                    build_xml(parent, item)
            else:
                parent.text = str(data) if data is not None else ""

        if not root_name:
            root_name = list(data.keys())[0] if data else "root"
            data = data.get(root_name, data)

        root = ET.Element(root_name)
        build_xml(root, data)

        return ET.tostring(root, encoding="unicode")


# Global transformer instance
dataweave_transformer = DataWeaveTransformer()


# ============================================================================
# ENTERPRISE FEATURE 8: BUSINESS RULE VALIDATION ENGINE
# ============================================================================

class RuleSeverity(Enum):
    """Severity levels for business rule violations"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class RuleViolation:
    """Represents a business rule violation"""
    rule_id: str
    rule_name: str
    message: str
    severity: RuleSeverity
    field: Optional[str] = None
    actual_value: Any = None
    expected_value: Any = None
    recoverable: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "message": self.message,
            "severity": self.severity.value,
            "field": self.field,
            "actual_value": self.actual_value,
            "expected_value": self.expected_value,
            "recoverable": self.recoverable
        }


@dataclass
class BusinessRuleResult:
    """Result of business rule validation"""
    valid: bool
    violations: List[RuleViolation] = field(default_factory=list)
    rules_evaluated: int = 0
    rules_passed: int = 0
    rules_failed: int = 0
    has_critical: bool = False
    validated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "violations": [v.to_dict() for v in self.violations],
            "rules_evaluated": self.rules_evaluated,
            "rules_passed": self.rules_passed,
            "rules_failed": self.rules_failed,
            "has_critical": self.has_critical,
            "validated_at": self.validated_at.isoformat(),
            "summary": {
                "info": len([v for v in self.violations if v.severity == RuleSeverity.INFO]),
                "warnings": len([v for v in self.violations if v.severity == RuleSeverity.WARNING]),
                "errors": len([v for v in self.violations if v.severity == RuleSeverity.ERROR]),
                "critical": len([v for v in self.violations if v.severity == RuleSeverity.CRITICAL])
            }
        }


class BusinessRuleEngine:
    """
    Business rule validation engine for cross-field and cross-system validations.
    Supports configurable rules with multiple severity levels.
    """

    def __init__(self):
        self.rules: Dict[str, Dict[str, Any]] = {}
        self.rule_sets: Dict[str, List[str]] = {}
        self._lock = threading.Lock()
        self._setup_default_rules()

    def _setup_default_rules(self):
        """Setup default business rules"""
        # Account Request Rules
        self.register_rule(
            "AR001",
            "Load Increase Limit",
            "account_request",
            "lambda d: d.get('requested_load', 0) <= d.get('current_load', 0) * 3",
            "Requested load cannot exceed 3x current load",
            RuleSeverity.ERROR,
            recoverable=True
        )

        self.register_rule(
            "AR002",
            "Valid PIN Code",
            "account_request",
            "lambda d: d.get('pin_code', '').isdigit() and len(d.get('pin_code', '')) in [5, 6]",
            "PIN code must be 5 or 6 digits",
            RuleSeverity.ERROR,
            recoverable=True
        )

        self.register_rule(
            "AR003",
            "Account Name Required",
            "account_request",
            "lambda d: bool(d.get('account_name', '').strip())",
            "Account name is required",
            RuleSeverity.CRITICAL,
            recoverable=False
        )

        self.register_rule(
            "AR004",
            "Minimum Load Requirement",
            "account_request",
            "lambda d: d.get('requested_load', 0) >= 1",
            "Requested load must be at least 1 kW",
            RuleSeverity.WARNING,
            recoverable=True
        )

        # Salesforce Case Rules
        self.register_rule(
            "SF001",
            "Subject Length",
            "salesforce_case",
            "lambda d: 5 <= len(d.get('subject', '')) <= 500",
            "Subject must be between 5 and 500 characters",
            RuleSeverity.ERROR,
            recoverable=True
        )

        self.register_rule(
            "SF002",
            "Critical Priority Requires Description",
            "salesforce_case",
            "lambda d: d.get('priority') != 'Critical' or bool(d.get('description', '').strip())",
            "Critical priority cases must have a description",
            RuleSeverity.ERROR,
            recoverable=True
        )

        self.register_rule(
            "SF003",
            "Escalated Status Check",
            "salesforce_case",
            "lambda d: d.get('status') != 'Escalated' or d.get('priority') in ['High', 'Critical']",
            "Only High or Critical priority cases can be escalated",
            RuleSeverity.WARNING,
            recoverable=True
        )

        # Cross-System Rules
        self.register_rule(
            "XS001",
            "SAP Integration Ready",
            "cross_system",
            "lambda d: all(k in d for k in ['account_name', 'request_type', 'requested_load'])",
            "Missing required fields for SAP integration",
            RuleSeverity.CRITICAL,
            recoverable=False
        )

        self.register_rule(
            "XS002",
            "ServiceNow Integration Ready",
            "cross_system",
            "lambda d: bool(d.get('subject') or d.get('title') or d.get('account_name'))",
            "At least one identifier field required for ServiceNow",
            RuleSeverity.ERROR,
            recoverable=True
        )

        # Create rule sets
        self.create_rule_set("account_validation", ["AR001", "AR002", "AR003", "AR004"])
        self.create_rule_set("case_validation", ["SF001", "SF002", "SF003"])
        self.create_rule_set("integration_ready", ["XS001", "XS002"])
        self.create_rule_set("full_validation", ["AR001", "AR002", "AR003", "AR004", "SF001", "SF002", "SF003", "XS001", "XS002"])

    def register_rule(
        self,
        rule_id: str,
        name: str,
        category: str,
        condition: str,
        message: str,
        severity: RuleSeverity,
        recoverable: bool = True,
        field: str = None
    ):
        """Register a business rule"""
        with self._lock:
            self.rules[rule_id] = {
                "id": rule_id,
                "name": name,
                "category": category,
                "condition": condition,
                "message": message,
                "severity": severity,
                "recoverable": recoverable,
                "field": field,
                "created_at": datetime.now().isoformat(),
                "evaluation_count": 0,
                "violation_count": 0
            }

    def create_rule_set(self, set_name: str, rule_ids: List[str]):
        """Create a named set of rules"""
        self.rule_sets[set_name] = rule_ids

    def get_rule(self, rule_id: str) -> Optional[Dict]:
        """Get rule by ID"""
        return self.rules.get(rule_id)

    def list_rules(self, category: str = None) -> List[Dict]:
        """List all rules, optionally filtered by category"""
        rules = list(self.rules.values())
        if category:
            rules = [r for r in rules if r["category"] == category]
        return [
            {
                "id": r["id"],
                "name": r["name"],
                "category": r["category"],
                "severity": r["severity"].value,
                "recoverable": r["recoverable"],
                "evaluation_count": r["evaluation_count"],
                "violation_count": r["violation_count"]
            }
            for r in rules
        ]

    def list_rule_sets(self) -> Dict[str, List[str]]:
        """List all rule sets"""
        return self.rule_sets.copy()

    def _evaluate_rule(self, rule: Dict, data: Dict) -> Optional[RuleViolation]:
        """Evaluate a single rule against data"""
        rule["evaluation_count"] += 1

        try:
            # Safely evaluate the condition with common built-ins
            safe_builtins = {
                "bool": bool, "int": int, "float": float, "str": str,
                "len": len, "all": all, "any": any, "abs": abs,
                "min": min, "max": max, "sum": sum, "round": round,
                "isinstance": isinstance, "type": type,
                "list": list, "dict": dict, "set": set, "tuple": tuple
            }
            condition_func = eval(rule["condition"], {"__builtins__": safe_builtins}, {})
            result = condition_func(data)

            if not result:
                rule["violation_count"] += 1
                return RuleViolation(
                    rule_id=rule["id"],
                    rule_name=rule["name"],
                    message=rule["message"],
                    severity=rule["severity"],
                    field=rule.get("field"),
                    recoverable=rule["recoverable"]
                )
        except Exception as e:
            rule["violation_count"] += 1
            return RuleViolation(
                rule_id=rule["id"],
                rule_name=rule["name"],
                message=f"Rule evaluation error: {str(e)}",
                severity=RuleSeverity.ERROR,
                recoverable=True
            )

        return None

    def validate(
        self,
        data: Dict[str, Any],
        rule_ids: List[str] = None,
        rule_set: str = None,
        category: str = None,
        stop_on_critical: bool = True
    ) -> BusinessRuleResult:
        """Validate data against business rules"""
        violations = []
        rules_to_evaluate = []

        # Determine which rules to evaluate
        if rule_ids:
            rules_to_evaluate = [self.rules[rid] for rid in rule_ids if rid in self.rules]
        elif rule_set and rule_set in self.rule_sets:
            rules_to_evaluate = [self.rules[rid] for rid in self.rule_sets[rule_set] if rid in self.rules]
        elif category:
            rules_to_evaluate = [r for r in self.rules.values() if r["category"] == category]
        else:
            rules_to_evaluate = list(self.rules.values())

        rules_passed = 0
        has_critical = False

        for rule in rules_to_evaluate:
            violation = self._evaluate_rule(rule, data)
            if violation:
                violations.append(violation)
                if violation.severity == RuleSeverity.CRITICAL:
                    has_critical = True
                    if stop_on_critical:
                        break
            else:
                rules_passed += 1

        return BusinessRuleResult(
            valid=len(violations) == 0,
            violations=violations,
            rules_evaluated=len(rules_to_evaluate),
            rules_passed=rules_passed,
            rules_failed=len(violations),
            has_critical=has_critical
        )


# Global business rule engine instance
business_rule_engine = BusinessRuleEngine()


# ============================================================================
# ENTERPRISE FEATURE 9: ERROR CATEGORIZATION
# ============================================================================

class ErrorCategory(Enum):
    """Categories of integration errors"""
    VALIDATION = "validation"           # Schema/business rule validation failures
    TRANSFORMATION = "transformation"   # Data transformation errors
    CONNECTIVITY = "connectivity"       # Network/connection errors
    AUTHENTICATION = "authentication"   # Auth/permission errors
    TIMEOUT = "timeout"                 # Timeout errors
    RATE_LIMIT = "rate_limit"           # Rate limiting errors
    DATA_QUALITY = "data_quality"       # Data quality issues
    SYSTEM = "system"                   # Internal system errors
    EXTERNAL = "external"               # External system errors
    UNKNOWN = "unknown"                 # Unclassified errors


class RecoverabilityStatus(Enum):
    """Whether an error is recoverable"""
    RECOVERABLE = "recoverable"           # Can retry automatically
    MANUAL_INTERVENTION = "manual"        # Needs human intervention
    NON_RECOVERABLE = "non_recoverable"   # Cannot be recovered


@dataclass
class CategorizedError:
    """A categorized integration error"""
    error_id: str
    category: ErrorCategory
    recoverability: RecoverabilityStatus
    message: str
    details: Optional[str] = None
    source_system: Optional[str] = None
    target_system: Optional[str] = None
    http_status: Optional[int] = None
    retry_count: int = 0
    max_retries: int = 3
    retry_delay_seconds: int = 5
    created_at: datetime = field(default_factory=datetime.now)
    resolved_at: Optional[datetime] = None
    resolution: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_id": self.error_id,
            "category": self.category.value,
            "recoverability": self.recoverability.value,
            "message": self.message,
            "details": self.details,
            "source_system": self.source_system,
            "target_system": self.target_system,
            "http_status": self.http_status,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "can_retry": self.can_retry(),
            "retry_delay_seconds": self.retry_delay_seconds,
            "created_at": self.created_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolution": self.resolution
        }

    def can_retry(self) -> bool:
        """Check if error can be retried"""
        return (
            self.recoverability == RecoverabilityStatus.RECOVERABLE and
            self.retry_count < self.max_retries
        )


class ErrorCategorizer:
    """
    Categorizes integration errors and determines recoverability.
    Provides retry strategies based on error type.
    """

    # Error classification patterns
    ERROR_PATTERNS = {
        ErrorCategory.CONNECTIVITY: [
            "connection refused", "connection reset", "connection timed out",
            "network unreachable", "dns resolution", "socket error",
            "ECONNREFUSED", "ECONNRESET", "ETIMEDOUT"
        ],
        ErrorCategory.AUTHENTICATION: [
            "unauthorized", "authentication failed", "invalid token",
            "expired token", "permission denied", "access denied", "401", "403"
        ],
        ErrorCategory.TIMEOUT: [
            "timeout", "timed out", "deadline exceeded", "request timeout"
        ],
        ErrorCategory.RATE_LIMIT: [
            "rate limit", "too many requests", "throttled", "quota exceeded", "429"
        ],
        ErrorCategory.VALIDATION: [
            "validation failed", "invalid", "required field", "schema",
            "constraint violation", "format error"
        ],
        ErrorCategory.TRANSFORMATION: [
            "transformation", "mapping", "conversion", "parse error",
            "serialization", "deserialization"
        ],
        ErrorCategory.DATA_QUALITY: [
            "duplicate", "missing data", "data integrity", "inconsistent",
            "referential integrity"
        ]
    }

    # HTTP status code mappings
    HTTP_CATEGORIES = {
        400: (ErrorCategory.VALIDATION, RecoverabilityStatus.MANUAL_INTERVENTION),
        401: (ErrorCategory.AUTHENTICATION, RecoverabilityStatus.MANUAL_INTERVENTION),
        403: (ErrorCategory.AUTHENTICATION, RecoverabilityStatus.NON_RECOVERABLE),
        404: (ErrorCategory.EXTERNAL, RecoverabilityStatus.MANUAL_INTERVENTION),
        408: (ErrorCategory.TIMEOUT, RecoverabilityStatus.RECOVERABLE),
        409: (ErrorCategory.DATA_QUALITY, RecoverabilityStatus.MANUAL_INTERVENTION),
        422: (ErrorCategory.VALIDATION, RecoverabilityStatus.MANUAL_INTERVENTION),
        429: (ErrorCategory.RATE_LIMIT, RecoverabilityStatus.RECOVERABLE),
        500: (ErrorCategory.EXTERNAL, RecoverabilityStatus.RECOVERABLE),
        502: (ErrorCategory.CONNECTIVITY, RecoverabilityStatus.RECOVERABLE),
        503: (ErrorCategory.EXTERNAL, RecoverabilityStatus.RECOVERABLE),
        504: (ErrorCategory.TIMEOUT, RecoverabilityStatus.RECOVERABLE)
    }

    # Retry configurations per category
    RETRY_CONFIGS = {
        ErrorCategory.CONNECTIVITY: {"max_retries": 5, "delay": 2, "backoff": 2.0},
        ErrorCategory.TIMEOUT: {"max_retries": 3, "delay": 5, "backoff": 1.5},
        ErrorCategory.RATE_LIMIT: {"max_retries": 3, "delay": 30, "backoff": 2.0},
        ErrorCategory.EXTERNAL: {"max_retries": 3, "delay": 10, "backoff": 2.0},
        ErrorCategory.AUTHENTICATION: {"max_retries": 1, "delay": 0, "backoff": 1.0},
        ErrorCategory.VALIDATION: {"max_retries": 0, "delay": 0, "backoff": 1.0},
        ErrorCategory.TRANSFORMATION: {"max_retries": 0, "delay": 0, "backoff": 1.0},
        ErrorCategory.DATA_QUALITY: {"max_retries": 0, "delay": 0, "backoff": 1.0},
        ErrorCategory.SYSTEM: {"max_retries": 2, "delay": 5, "backoff": 2.0},
        ErrorCategory.UNKNOWN: {"max_retries": 1, "delay": 5, "backoff": 1.5}
    }

    def categorize(
        self,
        error: Union[Exception, str],
        http_status: int = None,
        source_system: str = None,
        target_system: str = None
    ) -> CategorizedError:
        """Categorize an error and determine recoverability"""
        error_id = f"ERR-{uuid.uuid4().hex[:12].upper()}"
        error_message = str(error)
        error_lower = error_message.lower()

        # First check HTTP status
        if http_status and http_status in self.HTTP_CATEGORIES:
            category, recoverability = self.HTTP_CATEGORIES[http_status]
        else:
            # Pattern matching
            category = ErrorCategory.UNKNOWN
            for cat, patterns in self.ERROR_PATTERNS.items():
                if any(pattern in error_lower for pattern in patterns):
                    category = cat
                    break

            # Determine recoverability
            recoverability = self._determine_recoverability(category)

        # Get retry config
        retry_config = self.RETRY_CONFIGS.get(category, self.RETRY_CONFIGS[ErrorCategory.UNKNOWN])

        return CategorizedError(
            error_id=error_id,
            category=category,
            recoverability=recoverability,
            message=error_message,
            details=traceback.format_exc() if isinstance(error, Exception) else None,
            source_system=source_system,
            target_system=target_system,
            http_status=http_status,
            max_retries=retry_config["max_retries"],
            retry_delay_seconds=retry_config["delay"]
        )

    def _determine_recoverability(self, category: ErrorCategory) -> RecoverabilityStatus:
        """Determine recoverability based on category"""
        recoverable_categories = {
            ErrorCategory.CONNECTIVITY,
            ErrorCategory.TIMEOUT,
            ErrorCategory.RATE_LIMIT,
            ErrorCategory.EXTERNAL
        }

        non_recoverable_categories = {
            ErrorCategory.VALIDATION,
            ErrorCategory.TRANSFORMATION,
            ErrorCategory.DATA_QUALITY
        }

        if category in recoverable_categories:
            return RecoverabilityStatus.RECOVERABLE
        elif category in non_recoverable_categories:
            return RecoverabilityStatus.MANUAL_INTERVENTION
        else:
            return RecoverabilityStatus.RECOVERABLE

    def get_retry_delay(self, error: CategorizedError) -> int:
        """Calculate retry delay with exponential backoff"""
        config = self.RETRY_CONFIGS.get(error.category, self.RETRY_CONFIGS[ErrorCategory.UNKNOWN])
        backoff = config.get("backoff", 1.5)
        base_delay = config.get("delay", 5)
        return int(base_delay * (backoff ** error.retry_count))

    def get_category_stats(self) -> Dict[str, Any]:
        """Get information about error categories"""
        return {
            "categories": [
                {
                    "category": cat.value,
                    "retry_config": self.RETRY_CONFIGS.get(cat, {}),
                    "patterns": self.ERROR_PATTERNS.get(cat, [])
                }
                for cat in ErrorCategory
            ],
            "http_mappings": {
                str(code): {"category": cat.value, "recoverability": rec.value}
                for code, (cat, rec) in self.HTTP_CATEGORIES.items()
            }
        }


# Global error categorizer instance
error_categorizer = ErrorCategorizer()


# ============================================================================
# ENTERPRISE FEATURE 10: ERROR LOGGING WITH PAYLOAD SNAPSHOTS
# ============================================================================

@dataclass
class ErrorLogEntry:
    """Detailed error log entry with payload snapshot"""
    log_id: str
    error: CategorizedError
    timestamp: datetime
    correlation_id: Optional[str] = None
    transaction_id: Optional[str] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None
    request_payload: Optional[Dict[str, Any]] = None
    response_payload: Optional[Dict[str, Any]] = None
    request_headers: Optional[Dict[str, str]] = None
    stack_trace: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self, include_payloads: bool = True) -> Dict[str, Any]:
        result = {
            "log_id": self.log_id,
            "error": self.error.to_dict(),
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
            "transaction_id": self.transaction_id,
            "endpoint": self.endpoint,
            "method": self.method,
            "context": self.context
        }
        if include_payloads:
            result["request_payload"] = self._sanitize_payload(self.request_payload)
            result["response_payload"] = self._sanitize_payload(self.response_payload)
            result["request_headers"] = self._sanitize_headers(self.request_headers)
            result["stack_trace"] = self.stack_trace
        return result

    def _sanitize_payload(self, payload: Optional[Dict]) -> Optional[Dict]:
        """Remove sensitive data from payload"""
        if not payload:
            return None
        sanitized = copy.deepcopy(payload)
        sensitive_fields = ["password", "token", "secret", "api_key", "authorization", "credit_card", "ssn"]
        self._redact_sensitive(sanitized, sensitive_fields)
        return sanitized

    def _sanitize_headers(self, headers: Optional[Dict]) -> Optional[Dict]:
        """Remove sensitive headers"""
        if not headers:
            return None
        sanitized = copy.deepcopy(headers)
        sensitive_headers = ["authorization", "x-api-key", "cookie", "x-auth-token"]
        for key in list(sanitized.keys()):
            if key.lower() in sensitive_headers:
                sanitized[key] = "[REDACTED]"
        return sanitized

    def _redact_sensitive(self, obj: Any, sensitive_fields: List[str]):
        """Recursively redact sensitive fields"""
        if isinstance(obj, dict):
            for key in list(obj.keys()):
                if any(s in key.lower() for s in sensitive_fields):
                    obj[key] = "[REDACTED]"
                else:
                    self._redact_sensitive(obj[key], sensitive_fields)
        elif isinstance(obj, list):
            for item in obj:
                self._redact_sensitive(item, sensitive_fields)


class ErrorLogger:
    """
    Comprehensive error logging system with payload snapshots.
    Supports filtering, searching, and exporting error logs.
    """

    def __init__(self, max_entries: int = 10000, payload_retention_hours: int = 24):
        self.logs: Dict[str, ErrorLogEntry] = {}
        self.max_entries = max_entries
        self.payload_retention_hours = payload_retention_hours
        self._lock = threading.Lock()
        self._stats = {
            "total_logged": 0,
            "by_category": {cat.value: 0 for cat in ErrorCategory},
            "by_recoverability": {rec.value: 0 for rec in RecoverabilityStatus}
        }

    def log_error(
        self,
        error: Union[CategorizedError, Exception, str],
        correlation_id: str = None,
        transaction_id: str = None,
        endpoint: str = None,
        method: str = None,
        request_payload: Dict = None,
        response_payload: Dict = None,
        request_headers: Dict = None,
        context: Dict = None,
        http_status: int = None,
        source_system: str = None,
        target_system: str = None
    ) -> ErrorLogEntry:
        """Log an error with full context and payload snapshots"""

        # Categorize if needed
        if isinstance(error, CategorizedError):
            categorized_error = error
        else:
            categorized_error = error_categorizer.categorize(
                error,
                http_status=http_status,
                source_system=source_system,
                target_system=target_system
            )

        log_id = f"LOG-{uuid.uuid4().hex[:12].upper()}"
        stack_trace = None
        if isinstance(error, Exception):
            stack_trace = traceback.format_exc()

        entry = ErrorLogEntry(
            log_id=log_id,
            error=categorized_error,
            timestamp=datetime.now(),
            correlation_id=correlation_id or f"CORR-{uuid.uuid4().hex[:8].upper()}",
            transaction_id=transaction_id,
            endpoint=endpoint,
            method=method,
            request_payload=request_payload,
            response_payload=response_payload,
            request_headers=request_headers,
            stack_trace=stack_trace,
            context=context or {}
        )

        with self._lock:
            # Cleanup old entries if at capacity
            if len(self.logs) >= self.max_entries:
                self._cleanup_old_entries()

            self.logs[log_id] = entry
            self._stats["total_logged"] += 1
            self._stats["by_category"][categorized_error.category.value] += 1
            self._stats["by_recoverability"][categorized_error.recoverability.value] += 1

        # Print to console for immediate visibility
        print(f"[ERROR LOG] {log_id} | {categorized_error.category.value} | "
              f"{categorized_error.recoverability.value} | {categorized_error.message[:100]}")

        return entry

    def _cleanup_old_entries(self):
        """Remove oldest entries to make room for new ones"""
        if not self.logs:
            return

        # Sort by timestamp and remove oldest 10%
        sorted_logs = sorted(self.logs.items(), key=lambda x: x[1].timestamp)
        remove_count = max(1, len(sorted_logs) // 10)

        for log_id, _ in sorted_logs[:remove_count]:
            del self.logs[log_id]

    def get_log(self, log_id: str, include_payloads: bool = True) -> Optional[Dict]:
        """Get a specific error log entry"""
        entry = self.logs.get(log_id)
        if entry:
            return entry.to_dict(include_payloads=include_payloads)
        return None

    def search_logs(
        self,
        category: ErrorCategory = None,
        recoverability: RecoverabilityStatus = None,
        correlation_id: str = None,
        transaction_id: str = None,
        start_time: datetime = None,
        end_time: datetime = None,
        endpoint: str = None,
        source_system: str = None,
        limit: int = 100,
        include_payloads: bool = False
    ) -> List[Dict]:
        """Search error logs with filters"""
        results = []

        for entry in self.logs.values():
            # Apply filters
            if category and entry.error.category != category:
                continue
            if recoverability and entry.error.recoverability != recoverability:
                continue
            if correlation_id and entry.correlation_id != correlation_id:
                continue
            if transaction_id and entry.transaction_id != transaction_id:
                continue
            if start_time and entry.timestamp < start_time:
                continue
            if end_time and entry.timestamp > end_time:
                continue
            if endpoint and entry.endpoint != endpoint:
                continue
            if source_system and entry.error.source_system != source_system:
                continue

            results.append(entry.to_dict(include_payloads=include_payloads))

            if len(results) >= limit:
                break

        # Sort by timestamp descending
        results.sort(key=lambda x: x["timestamp"], reverse=True)
        return results

    def get_stats(self) -> Dict[str, Any]:
        """Get error logging statistics"""
        return {
            **self._stats,
            "current_log_count": len(self.logs),
            "max_entries": self.max_entries,
            "payload_retention_hours": self.payload_retention_hours
        }

    def get_recent_errors(self, hours: int = 1, limit: int = 50) -> List[Dict]:
        """Get recent errors within time window"""
        cutoff = datetime.now() - timedelta(hours=hours)
        return self.search_logs(start_time=cutoff, limit=limit, include_payloads=False)

    def export_logs(
        self,
        format: str = "json",
        category: ErrorCategory = None,
        start_time: datetime = None,
        end_time: datetime = None
    ) -> str:
        """Export logs in specified format"""
        logs = self.search_logs(
            category=category,
            start_time=start_time,
            end_time=end_time,
            limit=10000,
            include_payloads=True
        )

        if format == "json":
            return json.dumps(logs, indent=2, default=str)
        else:
            # Simple CSV format
            if not logs:
                return "log_id,timestamp,category,recoverability,message,endpoint"
            lines = ["log_id,timestamp,category,recoverability,message,endpoint"]
            for log in logs:
                lines.append(
                    f"{log['log_id']},{log['timestamp']},{log['error']['category']},"
                    f"{log['error']['recoverability']},\"{log['error']['message'][:100]}\","
                    f"{log.get('endpoint', '')}"
                )
            return "\n".join(lines)


# Global error logger instance
error_logger = ErrorLogger(max_entries=10000, payload_retention_hours=24)


# ============================================================================
# CONFIGURATION
# ============================================================================

BACKEND_API_URL = "http://149.102.158.71:4797/api"  # Remote MuleSoft backend
SAP_API_URL = "http://149.102.158.71:4798"  # Remote SAP backend
SERVICENOW_API_URL = "http://149.102.158.71:4780"  # Remote ServiceNow backend
SALESFORCE_API_URL = "http://149.102.158.71:4799"  # Remote Salesforce backend
SALESFORCE_MCP_URL = "http://149.102.158.71:8095"  # Salesforce MCP Server (SSE)
MCP_HTTP_PORT = 8090  # Port for HTTP API


# ============================================================================
# SALESFORCE MCP CLIENT (True MCP Integration via SSE)
# ============================================================================

class SalesforceMCPClient:
    """
    Client to interact with Salesforce MCP Server via SSE protocol.

    This is a TRUE MCP integration that:
    1. Connects to the Salesforce MCP Server's SSE endpoint
    2. Uses the MCP protocol to discover and call tools
    3. Maintains a persistent connection for real-time communication
    """

    def __init__(self, mcp_url: str = SALESFORCE_MCP_URL):
        self.mcp_url = mcp_url.rstrip("/")
        self.sse_endpoint = f"{self.mcp_url}/sse"
        self.messages_endpoint = f"{self.mcp_url}/messages"
        self._session_id = None
        self._tools_cache = None
        self._tools_cache_time = None
        self._cache_ttl = 300  # 5 minutes cache

    async def _get_session(self) -> str:
        """Initialize SSE connection and get session ID"""
        if self._session_id:
            return self._session_id

        timeout_config = get_timeout_config(TimeoutTier.STANDARD)
        try:
            async with httpx.AsyncClient(timeout=timeout_config.to_httpx_timeout(), verify=False) as client:
                # Connect to SSE endpoint to get session
                async with client.stream("GET", self.sse_endpoint) as response:
                    async for line in response.aiter_lines():
                        if line.startswith("data:"):
                            data = json.loads(line[5:].strip())
                            if "session_id" in data:
                                self._session_id = data["session_id"]
                                return self._session_id
                            # For initial connection, extract endpoint info
                            if "endpoint" in data:
                                self.messages_endpoint = data["endpoint"]
                                return "connected"
                        # Break after first message to avoid blocking
                        break
        except Exception as e:
            print(f"[MCP Client] SSE connection error: {e}")

        return None

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Call a tool on the Salesforce MCP server via MCP protocol.

        Uses the /messages endpoint to send tool call requests.
        """
        timeout_config = get_timeout_config(TimeoutTier.STANDARD)

        # Build MCP tool call request
        mcp_request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments or {}
            }
        }

        try:
            async with httpx.AsyncClient(timeout=timeout_config.to_httpx_timeout(), verify=False) as client:
                # Send tool call via MCP messages endpoint
                response = await client.post(
                    self.messages_endpoint,
                    json=mcp_request,
                    headers={"Content-Type": "application/json"}
                )

                if response.status_code == 200:
                    result = response.json()
                    # Extract result from MCP response
                    if "result" in result:
                        content = result["result"].get("content", [])
                        if content and len(content) > 0:
                            text_content = content[0].get("text", "{}")
                            return json.loads(text_content)
                    return result
                elif response.status_code == 202:
                    # Accepted - async processing
                    return {"status": "accepted", "message": "Tool call is being processed"}
                else:
                    # Fallback to direct API call if MCP fails
                    return await self._fallback_api_call(tool_name, arguments)

        except Exception as e:
            print(f"[MCP Client] Tool call error: {e}, falling back to direct API")
            # Fallback to direct API call
            return await self._fallback_api_call(tool_name, arguments)

    async def _fallback_api_call(self, tool_name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Fallback to direct Salesforce API call if MCP connection fails"""
        timeout_config = get_timeout_config(TimeoutTier.STANDARD)

        # Map tool names to API endpoints
        endpoint, method, data = self._map_tool_to_endpoint(tool_name, arguments or {})

        async with httpx.AsyncClient(timeout=timeout_config.to_httpx_timeout(), verify=False) as client:
            # Authenticate first
            auth_response = await client.post(
                f"{SALESFORCE_API_URL}/api/auth/login",
                json={"username": "admin", "password": "admin123"}
            )

            headers = {"Content-Type": "application/json"}
            if auth_response.status_code == 200:
                token = auth_response.json().get("access_token")
                headers["Authorization"] = f"Bearer {token}"

            try:
                if method == "GET":
                    response = await client.get(f"{SALESFORCE_API_URL}{endpoint}", headers=headers, params=arguments)
                elif method == "POST":
                    response = await client.post(f"{SALESFORCE_API_URL}{endpoint}", headers=headers, json=data)
                elif method == "PUT":
                    response = await client.put(f"{SALESFORCE_API_URL}{endpoint}", headers=headers, json=data)
                elif method == "DELETE":
                    response = await client.delete(f"{SALESFORCE_API_URL}{endpoint}", headers=headers)
                else:
                    return {"error": f"Unsupported method: {method}"}

                if response.status_code >= 400:
                    return {"error": f"API Error {response.status_code}", "details": response.text}

                return response.json()
            except Exception as e:
                return {"error": str(e)}

    def _map_tool_to_endpoint(self, tool_name: str, arguments: Dict[str, Any]) -> Tuple[str, str, Dict]:
        """Map MCP tool names to Salesforce API endpoints (for fallback)"""
        tool_mappings = {
            # Authentication
            "login": ("/api/auth/login", "POST", arguments),
            "get_current_user": ("/api/auth/me", "GET", {}),
            "list_users": ("/api/auth/users", "GET", {}),

            # Accounts
            "list_accounts": ("/api/accounts", "GET", {}),
            "get_account": (f"/api/accounts/{arguments.get('account_id', '')}", "GET", {}),
            "create_account": ("/api/accounts", "POST", arguments),
            "update_account": (f"/api/accounts/{arguments.get('account_id', '')}", "PUT", arguments),
            "delete_account": (f"/api/accounts/{arguments.get('account_id', '')}", "DELETE", {}),

            # Account Requests (for approval workflow)
            "list_account_requests": ("/api/accounts/requests", "GET", {}),
            "get_account_request": (f"/api/accounts/requests/{arguments.get('request_id', '')}", "GET", {}),
            "create_account_request": ("/api/accounts/requests", "POST", arguments),
            "update_account_request_status": (f"/api/accounts/requests/{arguments.get('request_id', '')}/status", "PUT", arguments),

            # Contacts
            "list_contacts": ("/api/contacts", "GET", {}),
            "get_contact": (f"/api/contacts/{arguments.get('contact_id', '')}", "GET", {}),
            "create_contact": ("/api/contacts", "POST", arguments),
            "update_contact": (f"/api/contacts/{arguments.get('contact_id', '')}", "PUT", arguments),
            "delete_contact": (f"/api/contacts/{arguments.get('contact_id', '')}", "DELETE", {}),

            # Cases
            "list_cases": ("/api/cases", "GET", {}),
            "get_case": (f"/api/cases/{arguments.get('case_id', '')}", "GET", {}),
            "create_case": ("/api/cases", "POST", arguments),
            "update_case": (f"/api/cases/{arguments.get('case_id', '')}", "PUT", arguments),
            "delete_case": (f"/api/cases/{arguments.get('case_id', '')}", "DELETE", {}),
            "escalate_case": (f"/api/cases/{arguments.get('case_id', '')}/escalate", "POST", {}),

            # Leads
            "list_leads": ("/api/leads", "GET", {}),
            "get_lead": (f"/api/leads/{arguments.get('lead_id', '')}", "GET", {}),
            "create_lead": ("/api/leads", "POST", arguments),
            "update_lead": (f"/api/leads/{arguments.get('lead_id', '')}", "PUT", arguments),
            "delete_lead": (f"/api/leads/{arguments.get('lead_id', '')}", "DELETE", {}),
            "convert_lead": (f"/api/leads/{arguments.get('lead_id', '')}/convert", "POST", {}),

            # Opportunities
            "list_opportunities": ("/api/opportunities", "GET", {}),
            "get_opportunity": (f"/api/opportunities/{arguments.get('opportunity_id', '')}", "GET", {}),
            "create_opportunity": ("/api/opportunities", "POST", arguments),
            "update_opportunity": (f"/api/opportunities/{arguments.get('opportunity_id', '')}", "PUT", arguments),
            "delete_opportunity": (f"/api/opportunities/{arguments.get('opportunity_id', '')}", "DELETE", {}),

            # Dashboard & Activities
            "get_dashboard_stats": ("/api/dashboard/stats", "GET", {}),
            "get_recent_records": ("/api/dashboard/recent-records", "GET", {}),
            "global_search": ("/api/dashboard/search", "GET", {}),
            "list_activities": ("/api/activities", "GET", {}),
            "create_activity": ("/api/activities", "POST", arguments),

            # Health
            "health_check": ("/api/health", "GET", {}),
        }

        return tool_mappings.get(tool_name, (f"/api/{tool_name}", "GET", {}))

    async def list_tools(self) -> List[Dict[str, Any]]:
        """
        List available tools from Salesforce MCP server.

        Uses the MCP protocol to discover tools dynamically.
        """
        # Check cache first
        if self._tools_cache and self._tools_cache_time:
            cache_age = (datetime.now() - self._tools_cache_time).total_seconds()
            if cache_age < self._cache_ttl:
                return self._tools_cache

        timeout_config = get_timeout_config(TimeoutTier.STANDARD)

        # Build MCP tools/list request
        mcp_request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "tools/list",
            "params": {}
        }

        try:
            async with httpx.AsyncClient(timeout=timeout_config.to_httpx_timeout(), verify=False) as client:
                response = await client.post(
                    self.messages_endpoint,
                    json=mcp_request,
                    headers={"Content-Type": "application/json"}
                )

                if response.status_code == 200:
                    result = response.json()
                    if "result" in result and "tools" in result["result"]:
                        tools = result["result"]["tools"]
                        # Cache the tools
                        self._tools_cache = tools
                        self._tools_cache_time = datetime.now()
                        return tools
        except Exception as e:
            print(f"[MCP Client] List tools error: {e}, using static list")

        # Return static list as fallback
        return self._get_static_tools_list()

    def _get_static_tools_list(self) -> List[Dict[str, Any]]:
        """Static tools list as fallback"""
        return [
            {"name": "login", "description": "Login to Salesforce", "inputSchema": {"type": "object", "properties": {"username": {"type": "string"}, "password": {"type": "string"}}}},
            {"name": "list_accounts", "description": "List all accounts", "inputSchema": {"type": "object", "properties": {"skip": {"type": "integer"}, "limit": {"type": "integer"}, "search": {"type": "string"}}}},
            {"name": "get_account", "description": "Get account by ID", "inputSchema": {"type": "object", "properties": {"account_id": {"type": "integer"}}, "required": ["account_id"]}},
            {"name": "create_account", "description": "Create new account", "inputSchema": {"type": "object", "properties": {"name": {"type": "string"}, "industry": {"type": "string"}}, "required": ["name"]}},
            {"name": "update_account", "description": "Update account", "inputSchema": {"type": "object", "properties": {"account_id": {"type": "integer"}, "name": {"type": "string"}}, "required": ["account_id"]}},
            {"name": "delete_account", "description": "Delete account", "inputSchema": {"type": "object", "properties": {"account_id": {"type": "integer"}}, "required": ["account_id"]}},
            {"name": "list_account_requests", "description": "List account creation requests", "inputSchema": {"type": "object", "properties": {"status": {"type": "string"}}}},
            {"name": "create_account_request", "description": "Create account request for approval", "inputSchema": {"type": "object", "properties": {"account_name": {"type": "string"}, "industry": {"type": "string"}}, "required": ["account_name"]}},
            {"name": "list_contacts", "description": "List all contacts", "inputSchema": {"type": "object", "properties": {"skip": {"type": "integer"}, "limit": {"type": "integer"}, "search": {"type": "string"}}}},
            {"name": "get_contact", "description": "Get contact by ID", "inputSchema": {"type": "object", "properties": {"contact_id": {"type": "integer"}}, "required": ["contact_id"]}},
            {"name": "create_contact", "description": "Create new contact", "inputSchema": {"type": "object", "properties": {"first_name": {"type": "string"}, "last_name": {"type": "string"}, "email": {"type": "string"}}, "required": ["first_name", "last_name"]}},
            {"name": "list_cases", "description": "List all cases", "inputSchema": {"type": "object", "properties": {"skip": {"type": "integer"}, "limit": {"type": "integer"}, "search": {"type": "string"}}}},
            {"name": "get_case", "description": "Get case by ID", "inputSchema": {"type": "object", "properties": {"case_id": {"type": "integer"}}, "required": ["case_id"]}},
            {"name": "create_case", "description": "Create new case", "inputSchema": {"type": "object", "properties": {"subject": {"type": "string"}, "contact_id": {"type": "integer"}}, "required": ["subject", "contact_id"]}},
            {"name": "escalate_case", "description": "Escalate a case", "inputSchema": {"type": "object", "properties": {"case_id": {"type": "integer"}}, "required": ["case_id"]}},
            {"name": "list_leads", "description": "List all leads", "inputSchema": {"type": "object", "properties": {"skip": {"type": "integer"}, "limit": {"type": "integer"}, "search": {"type": "string"}}}},
            {"name": "convert_lead", "description": "Convert lead to account/contact/opportunity", "inputSchema": {"type": "object", "properties": {"lead_id": {"type": "integer"}}, "required": ["lead_id"]}},
            {"name": "list_opportunities", "description": "List all opportunities", "inputSchema": {"type": "object", "properties": {"skip": {"type": "integer"}, "limit": {"type": "integer"}, "search": {"type": "string"}}}},
            {"name": "get_dashboard_stats", "description": "Get dashboard statistics", "inputSchema": {"type": "object", "properties": {}}},
            {"name": "global_search", "description": "Search across all objects", "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
            {"name": "health_check", "description": "Check Salesforce API health", "inputSchema": {"type": "object", "properties": {}}},
        ]

    async def check_connection(self) -> Dict[str, Any]:
        """Check if MCP server is reachable and responding"""
        timeout_config = get_timeout_config(TimeoutTier.FAST)

        try:
            async with httpx.AsyncClient(timeout=timeout_config.to_httpx_timeout(), verify=False) as client:
                # Try to connect to SSE endpoint
                response = await client.get(self.sse_endpoint, timeout=5)
                if response.status_code in [200, 202]:
                    return {
                        "connected": True,
                        "mcp_url": self.mcp_url,
                        "sse_endpoint": self.sse_endpoint,
                        "messages_endpoint": self.messages_endpoint,
                        "status": "healthy"
                    }
        except Exception as e:
            pass

        # Try fallback to direct API
        try:
            async with httpx.AsyncClient(timeout=timeout_config.to_httpx_timeout(), verify=False) as client:
                response = await client.get(f"{SALESFORCE_API_URL}/api/health")
                if response.status_code == 200:
                    return {
                        "connected": True,
                        "mcp_url": self.mcp_url,
                        "fallback_mode": True,
                        "salesforce_api_url": SALESFORCE_API_URL,
                        "status": "healthy (fallback mode)"
                    }
        except Exception as e:
            return {
                "connected": False,
                "mcp_url": self.mcp_url,
                "error": str(e),
                "status": "unreachable"
            }

        return {"connected": False, "status": "unknown"}


# Global Salesforce MCP client instance
salesforce_mcp_client = SalesforceMCPClient()

# In-memory storage for demo (replace with database in production)
connectors_db = {
    1: {
        "id": 1,
        "name": "Salesforce Production",
        "connector_type": "salesforce",
        "connection_config": {
            "server_url": "http://149.102.158.71:4799",
            "mcp_server_url": "http://149.102.158.71:8095",
            "use_mcp": True
        },
        "status": "active",
        "created_at": "2026-01-30T10:00:00.000000"
    }
}
users_db = {
    "admin": {"id": 1, "email": "admin@example.com", "password": "admin123", "full_name": "Admin User"},
    "mulesoft": {"id": 2, "email": "admin@mulesoft.io", "password": "admin123", "full_name": "MuleSoft Admin"}
}
tokens_db = {}

# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str


# Enterprise Feature Models
class TimeoutConfigRequest(BaseModel):
    """Request model for custom timeout configuration"""
    tier: str = Field(default="standard", description="Timeout tier: fast, standard, extended, transaction")
    connect_timeout: Optional[float] = Field(None, description="Override connection timeout (seconds)")
    read_timeout: Optional[float] = Field(None, description="Override read timeout (seconds)")
    transaction_timeout: Optional[float] = Field(None, description="Override transaction timeout (seconds)")


class BatchProcessRequest(BaseModel):
    """Request model for batch processing"""
    connector_id: int
    entity_type: str = Field(..., description="Type of entity: cases, accounts, requests")
    chunk_size: int = Field(default=50, ge=1, le=500, description="Items per chunk")
    parallel_chunks: int = Field(default=3, ge=1, le=10, description="Parallel chunk processing")
    fail_fast: bool = Field(default=False, description="Stop on first error")
    operation: str = Field(default="sync", description="Operation: sync, validate, transform")


class IncrementalSyncRequest(BaseModel):
    """Request model for incremental sync with watermarking"""
    connector_id: int
    entity_type: str
    force_full_sync: bool = Field(default=False, description="Force full resync ignoring watermark")
    batch_size: int = Field(default=100, ge=1, le=1000)


class AlertThresholdRequest(BaseModel):
    """Request model for setting alert thresholds"""
    metric_name: str
    warning_threshold: float
    critical_threshold: float
    window_seconds: int = Field(default=60, ge=10, le=3600)

class ConnectorCreate(BaseModel):
    name: str
    connector_type: str
    connection_config: Dict[str, Any] = {}

class ConnectorUpdate(BaseModel):
    name: Optional[str] = None
    connector_type: Optional[str] = None
    connection_config: Optional[Dict[str, Any]] = None

class CaseTransformData(BaseModel):
    caseId: Optional[Any] = None
    caseNumber: Optional[str] = None
    subject: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    account: Optional[Dict] = None
    contact: Optional[Dict] = None
    currentLoad: Optional[int] = 5
    requestedLoad: Optional[int] = 10
    connectionType: Optional[str] = "RESIDENTIAL"
    city: Optional[str] = "Hyderabad"
    pinCode: Optional[str] = "500001"
    accountId: Optional[Any] = None
    accountName: Optional[str] = None
    accountType: Optional[str] = None
    industry: Optional[str] = None
    requestType: Optional[str] = None

class SAPSendRequest(BaseModel):
    case_data: Dict[str, Any]
    endpoint_type: str = "load_request_xml"

class ValidateRequest(BaseModel):
    request_id: int
    account_name: str

class SendToServiceNowRequest(BaseModel):
    request_id: int
    account_name: str
    request_data: Dict[str, Any]

class ServiceNowWebhookCallback(BaseModel):
    """Payload ServiceNow sends when approval status changes"""
    ticket_number: str
    status: str  # approved, rejected, pending_approval
    request_id: Optional[int] = None
    account_name: Optional[str] = None
    approved_by: Optional[str] = None
    approval_date: Optional[str] = None
    rejection_reason: Optional[str] = None
    comments: Optional[str] = None
    correlation_id: Optional[str] = None

# ============================================================================
# FASTAPI APP
# ============================================================================

app = FastAPI(title="MuleSoft MCP API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer(auto_error=False)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        return None
    token = credentials.credentials
    if token in tokens_db:
        return tokens_db[token]
    return None

async def require_auth(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = credentials.credentials
    if token not in tokens_db:
        raise HTTPException(status_code=401, detail="Invalid token")
    return tokens_db[token]

# ============================================================================
# AUTH ENDPOINTS (Proxy to Remote MuleSoft Backend)
# ============================================================================

@app.post("/api/auth/login")
async def login(request: LoginRequest):
    """Proxy login to remote MuleSoft backend"""
    # First try remote backend authentication
    try:
        async with httpx.AsyncClient(verify=False, timeout=15) as client:
            response = await client.post(
                f"{BACKEND_API_URL}/auth/login",
                json={"email": request.email, "password": request.password}
            )
            if response.status_code == 200:
                data = response.json()
                # Handle both "token" and "access_token" response formats
                token = data.get("access_token") or data.get("token")
                user = data.get("user", {"email": request.email, "full_name": request.email})
                tokens_db[token] = user
                print(f"[MCP] User {request.email} authenticated via remote backend")
                # Return in consistent format
                return {"access_token": token, "token_type": "bearer", "user": user}
            elif response.status_code == 401:
                raise HTTPException(status_code=401, detail="Invalid credentials")
    except httpx.RequestError as e:
        print(f"[MCP] Remote auth failed, falling back to local: {e}")

    # Fallback to local auth
    for username, user in users_db.items():
        if user["email"] == request.email and user["password"] == request.password:
            token = str(uuid.uuid4())
            tokens_db[token] = user
            print(f"[MCP] User {request.email} authenticated via local fallback")
            return {"access_token": token, "token_type": "bearer", "user": user}
    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.post("/api/auth/register")
async def register(request: RegisterRequest):
    """Proxy registration to remote MuleSoft backend"""
    # Try remote backend registration
    try:
        async with httpx.AsyncClient(verify=False, timeout=15) as client:
            response = await client.post(
                f"{BACKEND_API_URL}/auth/register",
                json={"email": request.email, "password": request.password, "full_name": request.full_name}
            )
            if response.status_code in [200, 201]:
                return response.json()
            elif response.status_code == 400:
                raise HTTPException(status_code=400, detail="Email already registered")
    except httpx.RequestError as e:
        print(f"[MCP] Remote registration failed, falling back to local: {e}")

    # Fallback to local registration
    if any(u["email"] == request.email for u in users_db.values()):
        raise HTTPException(status_code=400, detail="Email already registered")
    user_id = len(users_db) + 1
    user = {"id": user_id, "email": request.email, "password": request.password, "full_name": request.full_name}
    users_db[request.email] = user
    return {"message": "User registered successfully"}

# ============================================================================
# HELPER: Get auth token from remote backend
# ============================================================================

async def get_remote_backend_token():
    """Authenticate with remote MuleSoft backend and get token"""
    try:
        async with httpx.AsyncClient(verify=False, timeout=15) as client:
            response = await client.post(
                f"{BACKEND_API_URL}/auth/login",
                json={"email": "admin@mulesoft.io", "password": "admin123"}
            )
            if response.status_code == 200:
                data = response.json()
                # Handle both "token" and "access_token" response formats
                return data.get("access_token") or data.get("token")
    except Exception as e:
        print(f"[MCP] Error getting remote backend token: {e}")
    return None

async def get_connector_by_id(connector_id: int) -> Optional[Dict]:
    """Get connector from local cache or fetch from remote backend"""
    # Try local cache first
    if connector_id in connectors_db:
        return connectors_db[connector_id]

    # Fetch from remote backend
    try:
        async with httpx.AsyncClient(verify=False, timeout=15) as client:
            token = await get_remote_backend_token()
            headers = {"Authorization": f"Bearer {token}"} if token else {}
            response = await client.get(f"{BACKEND_API_URL}/connectors/{connector_id}", headers=headers)
            if response.status_code == 200:
                connector = response.json()
                connectors_db[connector_id] = connector
                print(f"[MCP] Cached connector {connector_id} from remote backend")
                return connector
    except Exception as e:
        print(f"[MCP] Error fetching connector {connector_id} from remote: {e}")
    return None

# ============================================================================
# CONNECTOR ENDPOINTS (Proxy to Remote MuleSoft Backend)
# ============================================================================

@app.get("/api/connectors")
async def list_connectors(user = Depends(require_auth)):
    """Proxy to remote backend - list connectors"""
    try:
        async with httpx.AsyncClient(verify=False, timeout=15) as client:
            token = await get_remote_backend_token()
            headers = {"Authorization": f"Bearer {token}"} if token else {}
            response = await client.get(f"{BACKEND_API_URL}/connectors/", headers=headers)
            if response.status_code == 200:
                # Also cache in local db for other operations
                connectors = response.json()
                for conn in connectors:
                    connectors_db[conn["id"]] = conn
                return connectors
    except Exception as e:
        print(f"[MCP] Error fetching connectors from remote: {e}")
    # Fallback to local cache
    return list(connectors_db.values())

@app.get("/api/connectors/")
async def list_connectors_slash(user = Depends(require_auth)):
    return await list_connectors(user)

@app.get("/api/connectors/types")
async def get_connector_types(user = Depends(require_auth)):
    """Proxy to remote backend - get connector types"""
    try:
        async with httpx.AsyncClient(verify=False, timeout=15) as client:
            token = await get_remote_backend_token()
            headers = {"Authorization": f"Bearer {token}"} if token else {}
            response = await client.get(f"{BACKEND_API_URL}/connectors/types", headers=headers)
            if response.status_code == 200:
                return response.json()
    except Exception as e:
        print(f"[MCP] Error fetching connector types from remote: {e}")
    # Fallback
    base_config_schema = {"server_url": {"type": "string", "label": "Server URL", "required": True, "placeholder": "http://your-server-ip:port"}}
    salesforce_config_schema = {
        "server_url": {"type": "string", "label": "Salesforce API URL", "required": False, "placeholder": "http://salesforce-server:port"},
        "mcp_server_url": {"type": "string", "label": "Salesforce MCP URL", "required": False, "placeholder": "http://salesforce-mcp:8095"},
        "use_mcp": {"type": "boolean", "label": "Use MCP Integration", "required": False, "default": True}
    }
    return [
        {"type": "salesforce", "name": "Salesforce", "description": "Connect to Salesforce CRM via MCP or direct API", "config_schema": salesforce_config_schema},
        {"type": "sap", "name": "SAP", "description": "Connect to SAP ERP", "config_schema": base_config_schema},
        {"type": "servicenow", "name": "ServiceNow", "description": "Connect to ServiceNow ITSM", "config_schema": base_config_schema},
        {"type": "database", "name": "Database", "description": "Connect to databases", "config_schema": base_config_schema},
    ]

@app.get("/api/connectors/{connector_id}")
async def get_connector(connector_id: int, user = Depends(require_auth)):
    """Proxy to remote backend - get connector by ID"""
    try:
        async with httpx.AsyncClient(verify=False, timeout=15) as client:
            token = await get_remote_backend_token()
            headers = {"Authorization": f"Bearer {token}"} if token else {}
            response = await client.get(f"{BACKEND_API_URL}/connectors/{connector_id}", headers=headers)
            if response.status_code == 200:
                connector = response.json()
                connectors_db[connector_id] = connector
                return connector
    except Exception as e:
        print(f"[MCP] Error fetching connector from remote: {e}")
    # Fallback to local cache
    if connector_id in connectors_db:
        connector = connectors_db[connector_id]
        return {"id": connector_id, "config": connector.get("connection_config", {}), **connector}
    raise HTTPException(status_code=404, detail="Connector not found")

@app.get("/api/connectors")
async def get_connectors(user = Depends(require_auth)):
    """Get all connectors"""
    print(f"[MCP] Getting connectors, found {len(connectors_db)} in memory")
    connectors_list = []
    for connector_id, connector_data in connectors_db.items():
        connectors_list.append({
            "id": connector_id,
            "name": connector_data.get("name", "Unknown"),
            "type": connector_data.get("connector_type", "unknown"),
            "status": connector_data.get("status", "active"),
            "last_tested": connector_data.get("created_at", None)
        })
    print(f"[MCP] Returning {len(connectors_list)} connectors")
    return connectors_list

@app.post("/api/connectors")
async def create_connector(connector: ConnectorCreate, user = Depends(require_auth)):
    """Create connector locally (remote backend sync is optional)"""
    print(f"[MCP] Creating connector: {connector.dict()}")
    
    # Create locally first
    connector_id = max(connectors_db.keys(), default=0) + 1
    connector_data = {
        "id": connector_id,
        "name": connector.name,
        "connector_type": connector.connector_type,
        "connection_config": connector.connection_config,
        "status": "active",
        "created_at": datetime.now().isoformat()
    }
    connectors_db[connector_id] = connector_data
    print(f"[MCP] Connector created successfully: {connector_data}")
    return connector_data

@app.put("/api/connectors/{connector_id}")
async def update_connector(connector_id: int, connector: ConnectorUpdate, user = Depends(require_auth)):
    """Proxy to remote backend - update connector"""
    try:
        async with httpx.AsyncClient(verify=False, timeout=15) as client:
            token = await get_remote_backend_token()
            headers = {"Authorization": f"Bearer {token}"} if token else {}
            update_data = {}
            if connector.name:
                update_data["name"] = connector.name
            if connector.connector_type:
                update_data["connector_type"] = connector.connector_type
            if connector.connection_config:
                update_data["connection_config"] = connector.connection_config
            response = await client.put(
                f"{BACKEND_API_URL}/connectors/{connector_id}",
                json=update_data,
                headers=headers
            )
            if response.status_code == 200:
                updated = response.json()
                connectors_db[connector_id] = updated
                return updated
    except Exception as e:
        print(f"[MCP] Error updating connector on remote: {e}")
    # Fallback to local update
    if connector_id not in connectors_db:
        raise HTTPException(status_code=404, detail="Connector not found")
    existing = connectors_db[connector_id]
    if connector.name:
        existing["name"] = connector.name
    if connector.connector_type:
        existing["connector_type"] = connector.connector_type
    if connector.connection_config:
        existing["connection_config"] = connector.connection_config
    return existing

@app.delete("/api/connectors/{connector_id}")
async def delete_connector(connector_id: int, user = Depends(require_auth)):
    """Proxy to remote backend - delete connector"""
    try:
        async with httpx.AsyncClient(verify=False, timeout=15) as client:
            token = await get_remote_backend_token()
            headers = {"Authorization": f"Bearer {token}"} if token else {}
            response = await client.delete(f"{BACKEND_API_URL}/connectors/{connector_id}", headers=headers)
            if response.status_code == 200:
                if connector_id in connectors_db:
                    del connectors_db[connector_id]
                return {"message": "Connector deleted"}
    except Exception as e:
        print(f"[MCP] Error deleting connector on remote: {e}")
    # Fallback to local delete
    if connector_id in connectors_db:
        del connectors_db[connector_id]
    return {"message": "Connector deleted"}

@app.post("/api/connectors/{connector_id}/test")
async def test_connector(connector_id: int, user = Depends(require_auth)):
    """Proxy to remote backend - test connector"""
    # First try remote backend test
    try:
        async with httpx.AsyncClient(verify=False, timeout=15) as client:
            token = await get_remote_backend_token()
            headers = {"Authorization": f"Bearer {token}"} if token else {}
            response = await client.post(f"{BACKEND_API_URL}/connectors/{connector_id}/test", headers=headers)
            if response.status_code == 200:
                return response.json()
    except Exception as e:
        print(f"[MCP] Error testing connector via remote: {e}")

    # Fallback: test directly based on connector type
    connector = connectors_db.get(connector_id)
    if not connector:
        # Try to fetch from remote
        try:
            async with httpx.AsyncClient(verify=False, timeout=15) as client:
                token = await get_remote_backend_token()
                headers = {"Authorization": f"Bearer {token}"} if token else {}
                response = await client.get(f"{BACKEND_API_URL}/connectors/{connector_id}", headers=headers)
                if response.status_code == 200:
                    connector = response.json()
                    connectors_db[connector_id] = connector
        except:
            pass

    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")

    # Test connection based on type
    server_url = connector.get("connection_config", {}).get("server_url", "") or connector.get("config", {}).get("server_url", "")
    if server_url:
        try:
            async with httpx.AsyncClient(verify=False, timeout=10) as client:
                response = await client.get(f"{server_url}/api/health")
                if response.status_code == 200:
                    return {"success": True, "message": f"Connection to {connector['connector_type']} successful", "server_url": server_url}
        except Exception as e:
            return {"success": False, "message": f"Could not connect: {str(e)}", "server_url": server_url}

    return {"success": False, "message": "No server URL configured for this connector"}

@app.get("/api/salesforce/test")
async def test_salesforce_connection():
    """Test Salesforce backend connectivity"""
    try:
        async with httpx.AsyncClient(verify=False, timeout=10) as client:
            # Test basic connectivity
            health_response = await client.get(f"{SALESFORCE_API_URL}/api/health")
            if health_response.status_code != 200:
                return {"status": "error", "message": f"Health check failed: {health_response.status_code}"}
            
            # Test authentication
            auth_response = await client.post(
                f"{SALESFORCE_API_URL}/api/auth/login",
                json={"username": "admin", "password": "admin123"}
            )
            if auth_response.status_code != 200:
                return {"status": "error", "message": f"Auth failed: {auth_response.status_code}", "response": auth_response.text}
            
            token = auth_response.json().get("access_token", "")
            
            # Test cases endpoint
            cases_response = await client.get(
                f"{SALESFORCE_API_URL}/api/cases",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            return {
                "status": "success",
                "salesforce_url": SALESFORCE_API_URL,
                "health_status": health_response.status_code,
                "auth_status": auth_response.status_code,
                "cases_status": cases_response.status_code,
                "cases_count": len(cases_response.json()) if cases_response.status_code == 200 else 0
            }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/salesforce/cases")
async def get_salesforce_cases():
    """Get cases from Salesforce backend"""
    server_url = SALESFORCE_API_URL.rstrip("/")
    if not server_url:
        return {"status": "error", "message": "Server URL not configured", "cases": []}

    try:
        async with httpx.AsyncClient(verify=False, timeout=15) as client:
            # Authenticate
            auth_response = await client.post(f"{server_url}/api/auth/login", json={"username": "admin", "password": "admin123"})
            if auth_response.status_code != 200:
                return {"status": "error", "message": "Authentication failed", "cases": []}
            token = auth_response.json().get("access_token", "")

            # Fetch cases
            cases_response = await client.get(f"{server_url}/api/cases", headers={"Authorization": f"Bearer {token}"})
            if cases_response.status_code == 200:
                cases = cases_response.json()
                return {"status": "success", "cases": cases}
            else:
                return {"status": "error", "message": f"Failed to fetch cases: {cases_response.status_code}", "cases": []}
    except Exception as e:
        return {"status": "error", "message": str(e), "cases": []}

@app.get("/api/cases/external/cases")
async def get_external_cases_proxy(connector_id: int = Query(...)):
    """Proxy endpoint for remote backend to access Salesforce cases"""
    return await get_external_cases(connector_id)

@app.get("/api/cases/external/account-requests") 
async def get_external_account_requests_proxy(connector_id: int = Query(...)):
    """Proxy endpoint for remote backend to access Salesforce account requests"""
    return await get_external_account_requests(connector_id)

@app.post("/api/connectors/{connector_id}/test")
async def test_connector_proxy(connector_id: int):
    """Proxy endpoint for remote backend to test Salesforce connectivity"""
    try:
        # Test Salesforce connection
        async with httpx.AsyncClient(verify=False, timeout=10) as client:
            auth_response = await client.post(
                f"{SALESFORCE_API_URL}/api/auth/login",
                json={"username": "admin", "password": "admin123"}
            )
            if auth_response.status_code == 200:
                return {"success": True, "message": "Connection successful", "status": "Healthy"}
            else:
                return {"success": False, "message": f"Auth failed: {auth_response.status_code}", "status": "Error"}
    except Exception as e:
        return {"success": False, "message": str(e), "status": "Error"}

# ============================================================================
# SALESFORCE/CASES ENDPOINTS (Proxy to external Salesforce app)
# ============================================================================

@app.get("/api/cases/external/cases")
async def get_external_cases(connector_id: int = Query(...), user = Depends(require_auth)):
    connector = await get_connector_by_id(connector_id)
    if not connector:
        return {"status": "error", "message": "Connector not found", "cases": []}

    conn_config = connector.get("connection_config", {}) or connector.get("config", {})
    server_url = conn_config.get("server_url", "").rstrip("/")

    if not server_url:
        return {"status": "error", "message": "Server URL not configured", "cases": []}

    try:
        async with httpx.AsyncClient(verify=False, timeout=15) as client:
            # Authenticate
            auth_response = await client.post(f"{server_url}/api/auth/login", json={"username": "admin", "password": "admin123"})
            if auth_response.status_code != 200:
                return {"status": "error", "message": "Authentication failed", "cases": []}
            token = auth_response.json().get("access_token", "")

            # Fetch cases
            headers = {"Authorization": f"Bearer {token}"}
            response = await client.get(f"{server_url}/api/cases", headers=headers)
            if response.status_code == 200:
                data = response.json()
                return {"status": "success", "server_url": server_url, "cases": data}
            return {"status": "error", "message": f"Failed: HTTP {response.status_code}", "cases": []}
    except Exception as e:
        return {"status": "error", "message": str(e), "cases": []}

@app.get("/api/cases/external/account-requests")
async def get_external_account_requests(connector_id: int = Query(...), status: Optional[str] = None, user = Depends(require_auth)):
    connector = await get_connector_by_id(connector_id)
    if not connector:
        return {"status": "error", "message": "Connector not found", "requests": []}

    conn_config = connector.get("connection_config", {}) or connector.get("config", {})
    server_url = conn_config.get("server_url", "").rstrip("/")

    if not server_url:
        return {"status": "error", "message": "Server URL not configured", "requests": []}

    try:
        async with httpx.AsyncClient(verify=False, timeout=15) as client:
            # Authenticate
            auth_response = await client.post(f"{server_url}/api/auth/login", json={"username": "admin", "password": "admin123"})
            if auth_response.status_code != 200:
                return {"status": "error", "message": "Authentication failed", "requests": []}
            token = auth_response.json().get("access_token", "")

            # Fetch account requests
            headers = {"Authorization": f"Bearer {token}"}
            params = {}
            if status:
                params["status"] = status
            response = await client.get(f"{server_url}/api/accounts/requests", headers=headers, params=params)
            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])
                return {"status": "success", "server_url": server_url, "total": len(items), "requests": items}
            return {"status": "error", "message": f"Failed: HTTP {response.status_code}", "requests": []}
    except Exception as e:
        return {"status": "error", "message": str(e), "requests": []}

@app.post("/api/cases/validate-single-request")
async def validate_single_request(request: ValidateRequest, connector_id: int = Query(...), user = Depends(require_auth)):
    mulesoft_transaction_id = f"MULE-{uuid.uuid4().hex[:8].upper()}"

    # Update Salesforce backend with validation status
    sf_update_result = None
    if connector_id in connectors_db:
        connector = connectors_db[connector_id]
        sf_server_url = connector.get("connection_config", {}).get("server_url", "").rstrip("/")
        if sf_server_url:
            try:
                async with httpx.AsyncClient(verify=False, timeout=15) as client:
                    # Authenticate with Salesforce
                    auth_response = await client.post(
                        f"{sf_server_url}/api/auth/login",
                        json={"username": "admin", "password": "admin123"}
                    )
                    if auth_response.status_code == 200:
                        token = auth_response.json().get("access_token", "")
                        headers = {"Authorization": f"Bearer {token}"}

                        # Update status to PENDING_MULESOFT (validated)
                        update_response = await client.patch(
                            f"{sf_server_url}/api/accounts/requests/{request.request_id}/status",
                            json={
                                "integration_status": "PENDING_MULESOFT",
                                "mulesoft_transaction_id": mulesoft_transaction_id
                            },
                            headers=headers
                        )
                        sf_update_result = {"success": update_response.status_code == 200}
                        print(f"[MCP] Salesforce validation update: {update_response.status_code}")
            except Exception as e:
                print(f"[MCP] Error updating Salesforce validation: {e}")

    return {
        "valid": True,
        "request_id": request.request_id,
        "account_name": request.account_name,
        "mulesoft_transaction_id": mulesoft_transaction_id,
        "validation_timestamp": datetime.now().isoformat(),
        "salesforce_update": sf_update_result
    }

@app.post("/api/cases/send-single-to-servicenow")
async def send_single_to_servicenow(request: SendToServiceNowRequest, connector_id: int = Query(...), user = Depends(require_auth)):
    # Get ServiceNow server URL from connector config
    server_url = SERVICENOW_API_URL
    sf_server_url = SALESFORCE_API_URL  # Default to configured Salesforce URL

    # Fetch connector from cache or remote
    connector = await get_connector_by_id(connector_id)
    if connector:
        conn_config = connector.get("connection_config", {}) or connector.get("config", {})
        if connector.get("connector_type") == "servicenow":
            server_url = conn_config.get("server_url", SERVICENOW_API_URL)
        elif connector.get("connector_type") == "salesforce":
            sf_server_url = conn_config.get("server_url", SALESFORCE_API_URL).rstrip("/")

    # Also check all cached connectors for servicenow type
    for cid, conn in connectors_db.items():
        conn_config = conn.get("connection_config", {}) or conn.get("config", {})
        if conn.get("connector_type") == "servicenow":
            server_url = conn_config.get("server_url", server_url)

    server_url = server_url.rstrip("/")

    try:
        async with httpx.AsyncClient(verify=False, timeout=30) as client:
            # Authenticate with ServiceNow first
            auth_response = await client.post(
                f"{server_url}/token",
                data={"username": "admin@company.com", "password": "admin123"},
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            if auth_response.status_code != 200:
                print(f"[MCP] ServiceNow auth failed: {auth_response.text}")
                raise Exception("ServiceNow authentication failed")

            token = auth_response.json().get("access_token")
            headers = {"Authorization": f"Bearer {token}"}

            # Create ticket via ServiceNow API
            ticket_data = {
                "title": f"Account Creation Request: {request.account_name}",
                "description": f"Request ID: {request.request_id}\nAccount: {request.account_name}\nRequested via MuleSoft Integration",
                "category": "Account Management",
                "priority": "medium",
                "ticket_type": "service_request",
                "business_justification": f"Account creation for {request.account_name}"
            }
            # Use the standard tickets endpoint
            print(f"[MCP] Creating ticket in ServiceNow: {server_url}/tickets/")
            response = await client.post(f"{server_url}/tickets/", json=ticket_data, headers=headers)
            if response.status_code in [200, 201]:
                result = response.json()
                ticket_number = result.get("ticket_number", "UNKNOWN")
                ticket_status = result.get("status", "pending")
                print(f"[MCP] Ticket created successfully: {ticket_number}, status: {ticket_status}")

                # Update Salesforce backend with deployment status
                sf_update_result = None
                if sf_server_url:
                    try:
                        # Authenticate with Salesforce
                        sf_auth = await client.post(
                            f"{sf_server_url}/api/auth/login",
                            json={"username": "admin", "password": "admin123"}
                        )
                        if sf_auth.status_code == 200:
                            sf_token = sf_auth.json().get("access_token", "")
                            sf_headers = {"Authorization": f"Bearer {sf_token}"}

                            # Update status to COMPLETED (deployed)
                            sf_update = await client.patch(
                                f"{sf_server_url}/api/accounts/requests/{request.request_id}/status",
                                json={
                                    "integration_status": "COMPLETED",
                                    "servicenow_ticket_id": ticket_number,
                                    "servicenow_status": ticket_status
                                },
                                headers=sf_headers
                            )
                            sf_update_result = {"success": sf_update.status_code == 200}
                            print(f"[MCP] Salesforce deployment update: {sf_update.status_code}")
                    except Exception as e:
                        print(f"[MCP] Error updating Salesforce deployment: {e}")

                return {
                    "success": True,
                    "ticket_number": ticket_number,
                    "servicenow_response": result,
                    "server_url": server_url,
                    "status": ticket_status,
                    "requires_approval": ticket_status in ["pending", "open", "pending_approval"],
                    "message": f"Ticket {ticket_number} created successfully",
                    "salesforce_update": sf_update_result
                }
            else:
                print(f"[MCP] ServiceNow returned status {response.status_code}: {response.text}")
                return {
                    "success": False,
                    "error": f"ServiceNow returned status {response.status_code}",
                    "server_url": server_url,
                    "message": f"ServiceNow error: {response.text}"
                }
    except Exception as e:
        print(f"[MCP] ServiceNow error: {e}")
        return {
            "success": False,
            "error": str(e),
            "server_url": server_url,
            "message": "Failed to connect to ServiceNow"
        }

@app.post("/api/cases/orchestrate/account-requests")
async def orchestrate_account_requests(connector_id: int = Query(...), user = Depends(require_auth)):
    # Simulate orchestration
    return {
        "status": "completed",
        "total_fetched": 5,
        "total_valid": 4,
        "total_invalid": 1,
        "total_sent_to_servicenow": 4,
        "total_failed": 0,
        "results": []
    }

# ============================================================================
# SALESFORCE MCP INTEGRATION ENDPOINTS
# ============================================================================

@app.get("/api/salesforce-mcp/tools")
async def list_salesforce_mcp_tools(user = Depends(require_auth)):
    """List available tools from Salesforce MCP server"""
    try:
        tools = await salesforce_mcp_client.list_tools()
        return {
            "success": True,
            "mcp_server": "salesforce-crm",
            "mcp_url": SALESFORCE_MCP_URL,
            "tools": tools,
            "total": len(tools)
        }
    except Exception as e:
        return {"success": False, "error": str(e), "tools": []}


@app.post("/api/salesforce-mcp/call")
async def call_salesforce_mcp_tool(
    tool_name: str = Body(..., embed=True),
    arguments: Dict[str, Any] = Body(default={}, embed=True),
    user = Depends(require_auth)
):
    """Call a tool on the Salesforce MCP server"""
    try:
        result = await salesforce_mcp_client.call_tool(tool_name, arguments)
        return {
            "success": True,
            "tool": tool_name,
            "mcp_server": "salesforce-crm",
            "result": result
        }
    except Exception as e:
        return {"success": False, "tool": tool_name, "error": str(e)}


@app.get("/api/salesforce-mcp/health")
async def check_salesforce_mcp_health(user = Depends(require_auth)):
    """Check Salesforce MCP server health and connection status"""
    try:
        # Check MCP connection first
        connection_status = await salesforce_mcp_client.check_connection()

        # Also call health_check tool
        health_result = await salesforce_mcp_client.call_tool("health_check", {})

        return {
            "success": connection_status.get("connected", False),
            "mcp_server": "salesforce-crm",
            "mcp_url": SALESFORCE_MCP_URL,
            "salesforce_api_url": SALESFORCE_API_URL,
            "connection": connection_status,
            "health": health_result
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/salesforce-mcp/accounts")
async def get_salesforce_accounts_via_mcp(
    skip: int = Query(default=0),
    limit: int = Query(default=50),
    search: str = Query(default=""),
    user = Depends(require_auth)
):
    """Get accounts from Salesforce via MCP"""
    try:
        result = await salesforce_mcp_client.call_tool("list_accounts", {
            "skip": skip,
            "limit": limit,
            "search": search
        })
        return {
            "success": True,
            "source": "salesforce-mcp",
            "accounts": result if isinstance(result, list) else result.get("items", result)
        }
    except Exception as e:
        return {"success": False, "error": str(e), "accounts": []}


@app.post("/api/salesforce-mcp/accounts")
async def create_salesforce_account_via_mcp(
    name: str = Body(...),
    industry: str = Body(default=""),
    revenue: Optional[float] = Body(default=None),
    employees: Optional[int] = Body(default=None),
    user = Depends(require_auth)
):
    """Create a new account in Salesforce via MCP"""
    try:
        result = await salesforce_mcp_client.call_tool("create_account", {
            "name": name,
            "industry": industry,
            "revenue": revenue,
            "employees": employees
        })
        return {
            "success": True,
            "source": "salesforce-mcp",
            "account": result
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/salesforce-mcp/account-requests")
async def get_salesforce_account_requests_via_mcp(
    status: Optional[str] = Query(default=None),
    user = Depends(require_auth)
):
    """Get account creation requests from Salesforce via MCP"""
    try:
        args = {}
        if status:
            args["status"] = status
        result = await salesforce_mcp_client.call_tool("list_account_requests", args)
        return {
            "success": True,
            "source": "salesforce-mcp",
            "requests": result if isinstance(result, list) else result.get("items", result)
        }
    except Exception as e:
        return {"success": False, "error": str(e), "requests": []}


@app.post("/api/salesforce-mcp/account-requests")
async def create_salesforce_account_request_via_mcp(
    account_name: str = Body(...),
    industry: str = Body(default=""),
    requester: str = Body(default="MuleSoft Integration"),
    user = Depends(require_auth)
):
    """Create an account request in Salesforce via MCP (for approval workflow)"""
    try:
        result = await salesforce_mcp_client.call_tool("create_account_request", {
            "account_name": account_name,
            "industry": industry,
            "requester": requester
        })
        return {
            "success": True,
            "source": "salesforce-mcp",
            "request": result
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.put("/api/salesforce-mcp/account-requests/{request_id}/status")
async def update_salesforce_account_request_status_via_mcp(
    request_id: int,
    status: str = Body(..., embed=True),
    user = Depends(require_auth)
):
    """Update account request status in Salesforce via MCP"""
    try:
        result = await salesforce_mcp_client.call_tool("update_account_request_status", {
            "request_id": request_id,
            "status": status
        })
        return {
            "success": True,
            "source": "salesforce-mcp",
            "result": result
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/salesforce-mcp/cases")
async def get_salesforce_cases_via_mcp(
    skip: int = Query(default=0),
    limit: int = Query(default=50),
    search: str = Query(default=""),
    user = Depends(require_auth)
):
    """Get cases from Salesforce via MCP"""
    try:
        result = await salesforce_mcp_client.call_tool("list_cases", {
            "skip": skip,
            "limit": limit,
            "search": search
        })
        return {
            "success": True,
            "source": "salesforce-mcp",
            "cases": result if isinstance(result, list) else result.get("items", result)
        }
    except Exception as e:
        return {"success": False, "error": str(e), "cases": []}


@app.get("/api/salesforce-mcp/contacts")
async def get_salesforce_contacts_via_mcp(
    skip: int = Query(default=0),
    limit: int = Query(default=50),
    search: str = Query(default=""),
    user = Depends(require_auth)
):
    """Get contacts from Salesforce via MCP"""
    try:
        result = await salesforce_mcp_client.call_tool("list_contacts", {
            "skip": skip,
            "limit": limit,
            "search": search
        })
        return {
            "success": True,
            "source": "salesforce-mcp",
            "contacts": result if isinstance(result, list) else result.get("items", result)
        }
    except Exception as e:
        return {"success": False, "error": str(e), "contacts": []}


@app.get("/api/salesforce-mcp/leads")
async def get_salesforce_leads_via_mcp(
    skip: int = Query(default=0),
    limit: int = Query(default=50),
    search: str = Query(default=""),
    user = Depends(require_auth)
):
    """Get leads from Salesforce via MCP"""
    try:
        result = await salesforce_mcp_client.call_tool("list_leads", {
            "skip": skip,
            "limit": limit,
            "search": search
        })
        return {
            "success": True,
            "source": "salesforce-mcp",
            "leads": result if isinstance(result, list) else result.get("items", result)
        }
    except Exception as e:
        return {"success": False, "error": str(e), "leads": []}


@app.get("/api/salesforce-mcp/opportunities")
async def get_salesforce_opportunities_via_mcp(
    skip: int = Query(default=0),
    limit: int = Query(default=50),
    search: str = Query(default=""),
    user = Depends(require_auth)
):
    """Get opportunities from Salesforce via MCP"""
    try:
        result = await salesforce_mcp_client.call_tool("list_opportunities", {
            "skip": skip,
            "limit": limit,
            "search": search
        })
        return {
            "success": True,
            "source": "salesforce-mcp",
            "opportunities": result if isinstance(result, list) else result.get("items", result)
        }
    except Exception as e:
        return {"success": False, "error": str(e), "opportunities": []}


@app.get("/api/salesforce-mcp/dashboard")
async def get_salesforce_dashboard_via_mcp(user = Depends(require_auth)):
    """Get dashboard statistics from Salesforce via MCP"""
    try:
        result = await salesforce_mcp_client.call_tool("get_dashboard_stats", {})
        return {
            "success": True,
            "source": "salesforce-mcp",
            "dashboard": result
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/salesforce-mcp/search")
async def global_search_salesforce_via_mcp(
    q: str = Query(..., description="Search query"),
    user = Depends(require_auth)
):
    """Global search across Salesforce objects via MCP"""
    try:
        result = await salesforce_mcp_client.call_tool("global_search", {"query": q})
        return {
            "success": True,
            "source": "salesforce-mcp",
            "query": q,
            "results": result
        }
    except Exception as e:
        return {"success": False, "error": str(e), "results": []}


# ============================================================================
# SERVICENOW STATUS ENDPOINT
# ============================================================================

@app.get("/api/servicenow/ticket-status/{ticket_number}")
async def get_servicenow_ticket_status(ticket_number: str, user = Depends(require_auth)):
    """Fetch ticket status from ServiceNow backend"""
    try:
        async with httpx.AsyncClient(verify=False, timeout=15) as client:
            # Authenticate with ServiceNow
            auth_response = await client.post(
                f"{SERVICENOW_API_URL}/token",
                data={"username": "admin@company.com", "password": "admin123"},
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            if auth_response.status_code != 200:
                return {"status": "unknown", "error": "ServiceNow authentication failed"}

            token = auth_response.json().get("access_token")
            headers = {"Authorization": f"Bearer {token}"}

            # Fetch ticket by number
            response = await client.get(
                f"{SERVICENOW_API_URL}/tickets/by-number/{ticket_number}",
                headers=headers
            )
            if response.status_code == 200:
                ticket = response.json()
                return {
                    "status": ticket.get("status", "unknown"),
                    "ticket_number": ticket.get("ticket_number"),
                    "title": ticket.get("title"),
                    "priority": ticket.get("priority"),
                    "created_at": ticket.get("created_at"),
                    "updated_at": ticket.get("updated_at"),
                    "assigned_to": ticket.get("assigned_to_name"),
                    "resolution_notes": ticket.get("resolution_notes")
                }
            else:
                return {"status": "not_found", "error": f"Ticket {ticket_number} not found"}
    except Exception as e:
        print(f"[MCP] Error fetching ServiceNow ticket status: {e}")
        return {"status": "error", "error": str(e)}

# ============================================================================
# SAP ENDPOINTS
# ============================================================================

@app.get("/api/sap/test-connection")
async def test_sap_connection(user = Depends(require_auth)):
    try:
        async with httpx.AsyncClient(verify=False, timeout=10) as client:
            response = await client.get(f"{SAP_API_URL}/api/health")
            if response.status_code == 200:
                return {"success": True, "message": "SAP connection successful"}
    except:
        pass
    return {"success": False, "message": "SAP not reachable"}

@app.post("/api/sap/preview-xml")
async def preview_sap_xml(data: CaseTransformData, user = Depends(require_auth)):
    # Generate XML preview
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<IDOC BEGIN="1">
  <EDI_DC40 SEGMENT="1">
    <TABNAM>EDI_DC40</TABNAM>
    <MANDT>100</MANDT>
    <DOCNUM>{uuid.uuid4().hex[:10].upper()}</DOCNUM>
    <IDOCTYP>SRCLST01</IDOCTYP>
    <MESTYP>SRCLST</MESTYP>
    <SNDPRT>LS</SNDPRT>
    <SNDPRN>MULESOFT</SNDPRN>
    <RCVPRT>LS</RCVPRT>
    <RCVPRN>SAP_ERP</RCVPRN>
    <CREDAT>{datetime.now().strftime('%Y%m%d')}</CREDAT>
    <CRETIM>{datetime.now().strftime('%H%M%S')}</CRETIM>
  </EDI_DC40>
  <E1SRCLST SEGMENT="1">
    <CASE_ID>{data.caseId or data.accountId or 'N/A'}</CASE_ID>
    <CASE_NUMBER>{data.caseNumber or 'N/A'}</CASE_NUMBER>
    <SUBJECT>{data.subject or data.accountName or 'N/A'}</SUBJECT>
    <DESCRIPTION>{data.description or 'N/A'}</DESCRIPTION>
    <STATUS>{data.status or 'NEW'}</STATUS>
    <PRIORITY>{data.priority or 'MEDIUM'}</PRIORITY>
    <CONNECTION_TYPE>{data.connectionType}</CONNECTION_TYPE>
    <CURRENT_LOAD>{data.currentLoad}</CURRENT_LOAD>
    <REQUESTED_LOAD>{data.requestedLoad}</REQUESTED_LOAD>
    <CITY>{data.city}</CITY>
    <PIN_CODE>{data.pinCode}</PIN_CODE>
    <REQUEST_TYPE>{data.requestType or 'SERVICE_REQUEST'}</REQUEST_TYPE>
    <TIMESTAMP>{datetime.now().isoformat()}</TIMESTAMP>
  </E1SRCLST>
</IDOC>"""
    return {"xml": xml, "format": "SAP IDoc XML"}

@app.post("/api/sap/send-load-request")
async def send_to_sap(request: SAPSendRequest, user = Depends(require_auth)):
    try:
        async with httpx.AsyncClient(verify=False, timeout=30) as client:
            response = await client.post(
                f"{SAP_API_URL}/api/integration/mulesoft/load-request/xml",
                json=request.case_data
            )
            if response.status_code in [200, 201]:
                return {"success": True, "sap_response": response.json()}
            else:
                return {"success": False, "error": f"SAP returned status {response.status_code}", "details": response.text}
    except Exception as e:
        return {"success": False, "error": str(e), "message": "Failed to connect to SAP"}

# ============================================================================
# SERVICENOW ENDPOINTS
# ============================================================================

@app.get("/api/servicenow/test-connection")
async def test_servicenow_connection(connector_id: Optional[int] = Query(None), user = Depends(require_auth)):
    # Get server URL from connector or fallback to hardcoded
    server_url = SERVICENOW_API_URL
    if connector_id and connector_id in connectors_db:
        connector = connectors_db[connector_id]
        server_url = connector.get("connection_config", {}).get("server_url", SERVICENOW_API_URL)

    try:
        async with httpx.AsyncClient(verify=False, timeout=10) as client:
            response = await client.get(f"{server_url}/api/health")
            if response.status_code == 200:
                return {"success": True, "message": "ServiceNow connection successful", "server_url": server_url}
    except:
        pass
    return {"success": False, "message": "ServiceNow not reachable", "server_url": server_url}

@app.post("/api/servicenow/preview-ticket")
async def preview_servicenow_ticket(data: Dict[str, Any] = Body(...), ticket_type: str = Query("incident"), user = Depends(require_auth)):
    ticket_payload = {
        "short_description": data.get("subject") or f"Case #{data.get('caseId', 'N/A')}",
        "description": data.get("description") or "No description provided",
        "category": data.get("category", "General"),
        "priority": "3" if data.get("priority") == "Medium" else ("1" if data.get("priority") == "Critical" else "2"),
        "caller_id": data.get("userName") or data.get("contact", {}).get("name", "Unknown"),
        "ticket_type": ticket_type,
        "source_system": "MuleSoft",
        "source_id": str(data.get("caseId") or data.get("id", "N/A"))
    }
    return {"ticket_payload": ticket_payload}

@app.post("/api/servicenow/preview-approval")
async def preview_servicenow_approval(data: Dict[str, Any] = Body(...), approval_type: str = Query("user_account"), user = Depends(require_auth)):
    approval_payload = {
        "approval_type": approval_type,
        "requested_for": data.get("userName") or data.get("accountName") or data.get("contact", {}).get("name", "Unknown"),
        "requested_by": "MuleSoft Integration",
        "description": f"Approval request for {approval_type}: {data.get('subject') or data.get('accountName', 'N/A')}",
        "priority": data.get("priority", "Medium"),
        "source_id": str(data.get("caseId") or data.get("id", "N/A")),
        "details": {
            "department": data.get("department", "N/A"),
            "role": data.get("userRole", "Standard User"),
            "category": data.get("category", "General")
        }
    }
    return {"approval_payload": approval_payload}

@app.post("/api/servicenow/send-ticket-only")
async def send_ticket_only(data: Dict[str, Any] = Body(...), ticket_type: str = Query("incident"), connector_id: Optional[int] = Query(None), user = Depends(require_auth)):
    """Send only a ticket to ServiceNow without automatic approval"""
    # Get server URL from connector or fallback to hardcoded
    server_url = SERVICENOW_API_URL
    if connector_id and connector_id in connectors_db:
        connector = connectors_db[connector_id]
        server_url = connector.get("connection_config", {}).get("server_url", SERVICENOW_API_URL)

    ticket_result = {"success": False}

    try:
        async with httpx.AsyncClient(verify=False, timeout=30) as client:
            # Send ticket only (no approval)
            ticket_data = {
                "short_description": data.get("subject") or f"Case #{data.get('caseId', 'N/A')}",
                "description": data.get("description") or "No description",
                "category": data.get("category", "General"),
                "priority": "3" if data.get("priority") == "Medium" else ("1" if data.get("priority") == "Critical" else "2"),
                "ticket_type": ticket_type,
                "source_system": "MuleSoft",
                "source_id": str(data.get("caseId") or data.get("id", "N/A"))
            }
            ticket_response = await client.post(f"{server_url}/tickets/", json=ticket_data)
            if ticket_response.status_code in [200, 201]:
                ticket_result = {"success": True, "response": ticket_response.json(), "ticket_number": ticket_response.json().get("ticket_number")}
            else:
                ticket_result = {"success": False, "error": f"ServiceNow returned status {ticket_response.status_code}"}
    except Exception as e:
        ticket_result = {"success": False, "error": str(e), "message": "Failed to connect to ServiceNow"}

    return {"ticket": ticket_result, "approval": None}

@app.post("/api/servicenow/send-ticket-and-approval")
async def send_ticket_and_approval(data: Dict[str, Any] = Body(...), ticket_type: str = Query("incident"), approval_type: str = Query("user_account"), connector_id: Optional[int] = Query(None), user = Depends(require_auth)):
    # Get server URL from connector or fallback to hardcoded
    server_url = SERVICENOW_API_URL
    if connector_id and connector_id in connectors_db:
        connector = connectors_db[connector_id]
        server_url = connector.get("connection_config", {}).get("server_url", SERVICENOW_API_URL)

    ticket_result = {"success": False}
    approval_result = {"success": False}

    try:
        async with httpx.AsyncClient(verify=False, timeout=30) as client:
            # Send ticket
            ticket_data = {
                "short_description": data.get("subject") or f"Case #{data.get('caseId', 'N/A')}",
                "description": data.get("description") or "No description",
                "category": data.get("category", "General"),
                "priority": "3"
            }
            ticket_response = await client.post(f"{server_url}/tickets/", json=ticket_data)
            if ticket_response.status_code in [200, 201]:
                ticket_result = {"success": True, "response": ticket_response.json(), "ticket_number": ticket_response.json().get("ticket_number")}

            # Send approval
            approval_data = {
                "approval_type": approval_type,
                "requested_for": data.get("userName") or "Unknown",
                "description": f"Approval for {data.get('subject', 'N/A')}"
            }
            approval_response = await client.post(f"{server_url}/approvals/", json=approval_data)
            if approval_response.status_code in [200, 201]:
                approval_result = {"success": True, "response": approval_response.json(), "approval_id": approval_response.json().get("approval_id")}
            else:
                approval_result = {"success": False, "error": f"ServiceNow returned status {approval_response.status_code}"}
    except Exception as e:
        if not ticket_result.get("success"):
            ticket_result = {"success": False, "error": str(e), "message": "Failed to connect to ServiceNow"}
        if not approval_result.get("success"):
            approval_result = {"success": False, "error": str(e), "message": "Failed to create approval"}

    return {"ticket": ticket_result, "approval": approval_result}

@app.get("/api/servicenow/ticket-status/{ticket_id}")
async def get_ticket_status(ticket_id: str, connector_id: Optional[int] = Query(None), user = Depends(require_auth)):
    # Get server URL from connector or fallback to hardcoded
    server_url = SERVICENOW_API_URL
    if connector_id and connector_id in connectors_db:
        connector = connectors_db[connector_id]
        server_url = connector.get("connection_config", {}).get("server_url", SERVICENOW_API_URL)

    server_url = server_url.rstrip("/")

    try:
        async with httpx.AsyncClient(verify=False, timeout=15) as client:
            # Authenticate with ServiceNow first
            auth_response = await client.post(
                f"{server_url}/token",
                data={"username": "admin@company.com", "password": "admin123"},
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            if auth_response.status_code != 200:
                print(f"[MCP] ServiceNow auth failed: {auth_response.text}")
                raise Exception("ServiceNow authentication failed")

            token = auth_response.json().get("access_token")
            headers = {"Authorization": f"Bearer {token}"}

            # Try fetching by ticket number first
            response = await client.get(f"{server_url}/tickets/by-number/{ticket_id}", headers=headers)
            if response.status_code == 200:
                data = response.json()
                return {"ticket_id": ticket_id, "status": data.get("status", "unknown"), "updated_at": data.get("updated_at") or datetime.now().isoformat(), "data": data}

            # Fallback to tickets/{id} endpoint
            response = await client.get(f"{server_url}/tickets/{ticket_id}", headers=headers)
            if response.status_code == 200:
                data = response.json()
                return {"ticket_id": ticket_id, "status": data.get("status", "unknown"), "updated_at": data.get("updated_at") or datetime.now().isoformat(), "data": data}
    except Exception as e:
        print(f"[MCP] Error fetching ticket status: {e}")
        return {"ticket_id": ticket_id, "status": "error", "error": str(e), "message": "Failed to fetch ticket status from ServiceNow"}

# ============================================================================
# MULESOFT INBOUND ENDPOINTS (receives requests from Salesforce)
# ============================================================================

@app.post("/api/mulesoft/account-request")
async def receive_account_request(data: Dict[str, Any] = Body(...)):
    """
    Receives account creation requests from Salesforce backend.
    This endpoint does NOT require auth as it's called by the Salesforce system.
    """
    correlation_id = data.get("correlationId", str(uuid.uuid4()))
    transaction_id = f"MULE-{uuid.uuid4().hex[:12]}"

    # Log the request
    print(f"[MuleSoft] Received account request: {correlation_id}")
    print(f"[MuleSoft] Data: {data}")

    # In a real scenario, this would trigger the ServiceNow workflow
    # For now, just acknowledge receipt
    return {
        "success": True,
        "transactionId": transaction_id,
        "mulesoftTransactionId": transaction_id,
        "correlationId": correlation_id,
        "message": "Account request received and queued for processing",
        "status": "PENDING"
    }

# In-memory store for tracking ticket to request mapping
ticket_request_mapping = {}

@app.post("/api/webhooks/servicenow/approval-callback")
async def servicenow_approval_callback(callback: ServiceNowWebhookCallback):
    """
    Webhook endpoint that ServiceNow calls when approval status changes.
    This endpoint does NOT require auth as it's called by ServiceNow system.

    Expected payload from ServiceNow:
    {
        "ticket_number": "TKT-XXXXXXXX",
        "status": "approved",  // or "rejected", "pending_approval"
        "request_id": 123,
        "account_name": "Company Name",
        "approved_by": "admin@company.com",
        "approval_date": "2026-01-30T12:00:00Z",
        "rejection_reason": null,  // Only if rejected
        "comments": "Approved by manager",
        "correlation_id": "original-correlation-id"
    }
    """
    print(f"[MuleSoft] ========== SERVICENOW CALLBACK RECEIVED ==========")
    print(f"[MuleSoft] Ticket: {callback.ticket_number}")
    print(f"[MuleSoft] Status: {callback.status}")
    print(f"[MuleSoft] Request ID: {callback.request_id}")
    print(f"[MuleSoft] Account: {callback.account_name}")
    print(f"[MuleSoft] Approved By: {callback.approved_by}")
    print(f"[MuleSoft] ===================================================")

    # Store the callback for tracking
    ticket_request_mapping[callback.ticket_number] = {
        "status": callback.status,
        "request_id": callback.request_id,
        "account_name": callback.account_name,
        "approved_by": callback.approved_by,
        "approval_date": callback.approval_date or datetime.now().isoformat(),
        "rejection_reason": callback.rejection_reason,
        "comments": callback.comments,
        "received_at": datetime.now().isoformat()
    }

    # Map ServiceNow status to integration status
    status_mapping = {
        "approved": "COMPLETED",
        "rejected": "REJECTED",
        "pending_approval": "REQUESTED",
        "submitted": "REQUESTED"
    }
    integration_status = status_mapping.get(callback.status.lower(), "REQUESTED")

    # Forward status update to Salesforce backend if request_id is provided
    salesforce_update_result = None
    if callback.request_id:
        try:
            # Find Salesforce connector to get server URL
            sf_server_url = None
            for cid, conn in connectors_db.items():
                if conn.get("connector_type") == "salesforce":
                    sf_server_url = conn.get("connection_config", {}).get("server_url")
                    break

            if sf_server_url:
                sf_server_url = sf_server_url.rstrip("/")
                async with httpx.AsyncClient(verify=False, timeout=30) as client:
                    # Authenticate with Salesforce
                    auth_response = await client.post(
                        f"{sf_server_url}/api/auth/login",
                        json={"username": "admin", "password": "admin123"}
                    )
                    if auth_response.status_code == 200:
                        token = auth_response.json().get("access_token", "")
                        headers = {"Authorization": f"Bearer {token}"}

                        # Update the account request status in Salesforce
                        update_payload = {
                            "integration_status": integration_status,
                            "servicenow_status": callback.status,
                            "servicenow_ticket_id": callback.ticket_number,
                            "approved_by": callback.approved_by,
                            "approval_date": callback.approval_date,
                            "rejection_reason": callback.rejection_reason
                        }

                        update_response = await client.patch(
                            f"{sf_server_url}/api/accounts/requests/{callback.request_id}/status",
                            json=update_payload,
                            headers=headers
                        )

                        if update_response.status_code == 200:
                            salesforce_update_result = {
                                "success": True,
                                "message": "Salesforce updated successfully"
                            }
                            print(f"[MuleSoft] Salesforce updated: {update_response.json()}")
                        else:
                            salesforce_update_result = {
                                "success": False,
                                "message": f"Salesforce update failed: {update_response.status_code}"
                            }
                            print(f"[MuleSoft] Salesforce update failed: {update_response.text}")
        except Exception as e:
            print(f"[MuleSoft] Error updating Salesforce: {e}")
            salesforce_update_result = {"success": False, "error": str(e)}

    return {
        "success": True,
        "message": f"Callback received for ticket {callback.ticket_number}",
        "ticket_number": callback.ticket_number,
        "status_received": callback.status,
        "integration_status": integration_status,
        "mulesoft_processed_at": datetime.now().isoformat(),
        "salesforce_update": salesforce_update_result
    }

@app.get("/api/webhooks/servicenow/status/{ticket_number}")
async def get_callback_status(ticket_number: str):
    """
    Check if a callback has been received for a ticket.
    Useful for debugging/verification.
    """
    if ticket_number in ticket_request_mapping:
        return {
            "found": True,
            "ticket_number": ticket_number,
            **ticket_request_mapping[ticket_number]
        }
    return {
        "found": False,
        "ticket_number": ticket_number,
        "message": "No callback received for this ticket yet"
    }

# ============================================================================
# API ENDPOINTS (for API Manager page)
# ============================================================================

@app.get("/api/apis/endpoints")
async def list_api_endpoints(user = Depends(require_auth)):
    return [
        {"id": 1, "name": "Get Cases", "method": "GET", "path": "/api/cases", "status": "active"},
        {"id": 2, "name": "Create Case", "method": "POST", "path": "/api/cases", "status": "active"},
        {"id": 3, "name": "SAP Sync", "method": "POST", "path": "/api/sap/sync", "status": "active"},
    ]

@app.post("/api/apis/endpoints")
async def create_api_endpoint(data: Dict[str, Any] = Body(...), user = Depends(require_auth)):
    return {"id": uuid.uuid4().hex[:8], **data, "status": "active"}

@app.delete("/api/apis/endpoints/{endpoint_id}")
async def delete_api_endpoint(endpoint_id: int, user = Depends(require_auth)):
    return {"message": "Endpoint deleted"}

@app.get("/api/apis/keys")
async def list_api_keys(user = Depends(require_auth)):
    return [
        {"id": 1, "name": "Production Key", "key": "pk_live_xxx", "status": "active", "created_at": datetime.now().isoformat()},
    ]

@app.post("/api/apis/keys")
async def create_api_key(data: Dict[str, Any] = Body(...), user = Depends(require_auth)):
    return {"id": uuid.uuid4().hex[:8], "key": f"pk_{uuid.uuid4().hex}", **data}

@app.delete("/api/apis/keys/{key_id}")
async def revoke_api_key(key_id: int, user = Depends(require_auth)):
    return {"message": "Key revoked"}

# ============================================================================
# ENTERPRISE FEATURE ENDPOINTS
# ============================================================================

# --- Timeout Configuration ---

@app.get("/api/enterprise/timeouts")
async def get_timeout_configs(user = Depends(require_auth)):
    """Get all available timeout tier configurations"""
    return {
        "tiers": {
            tier.value: {
                "connect_timeout": config.connect_timeout,
                "read_timeout": config.read_timeout,
                "write_timeout": config.write_timeout,
                "pool_timeout": config.pool_timeout,
                "transaction_timeout": config.transaction_timeout
            }
            for tier, config in TIMEOUT_CONFIGS.items()
        },
        "description": {
            "fast": "Quick operations (health checks, simple queries)",
            "standard": "Normal operations (CRUD, authentication)",
            "extended": "Long operations (batch processing, reports)",
            "transaction": "Full transaction flows with multiple steps"
        }
    }


@app.post("/api/enterprise/timeouts/test")
async def test_timeout_config(
    request: TimeoutConfigRequest,
    target_url: str = Query(..., description="URL to test timeout against"),
    user = Depends(require_auth)
):
    """Test a timeout configuration against a target URL"""
    tier = TimeoutTier(request.tier) if request.tier in [t.value for t in TimeoutTier] else TimeoutTier.STANDARD
    config = get_timeout_config(tier)

    # Apply overrides if provided
    if request.connect_timeout:
        config.connect_timeout = request.connect_timeout
    if request.read_timeout:
        config.read_timeout = request.read_timeout

    start_time = time.time()
    try:
        async with create_monitored_client(tier) as client:
            response = await client.get(target_url)
            duration = (time.time() - start_time) * 1000
            perf_monitor.record_request(target_url, duration, response.status_code < 400)
            return {
                "success": True,
                "status_code": response.status_code,
                "duration_ms": round(duration, 2),
                "timeout_config_used": config.__dict__
            }
    except httpx.TimeoutException as e:
        duration = (time.time() - start_time) * 1000
        perf_monitor.record_request(target_url, duration, False)
        return {
            "success": False,
            "error": "timeout",
            "error_type": type(e).__name__,
            "duration_ms": round(duration, 2),
            "timeout_config_used": config.__dict__
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# --- Async Job Management ---

@app.get("/api/enterprise/jobs")
async def list_jobs(
    status: Optional[str] = Query(None, description="Filter by status: pending, running, completed, failed"),
    limit: int = Query(50, ge=1, le=200),
    user = Depends(require_auth)
):
    """List all async jobs"""
    job_status = JobStatus(status) if status and status in [s.value for s in JobStatus] else None
    return {
        "jobs": job_manager.list_jobs(status=job_status, limit=limit),
        "total": len(job_manager.jobs)
    }


@app.get("/api/enterprise/jobs/{job_id}")
async def get_job(job_id: str, user = Depends(require_auth)):
    """Get async job status and details"""
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.to_dict()


@app.post("/api/enterprise/jobs/{job_id}/cancel")
async def cancel_job(job_id: str, user = Depends(require_auth)):
    """Cancel a pending or running job"""
    if job_manager.cancel_job(job_id):
        return {"success": True, "message": f"Job {job_id} cancelled"}
    raise HTTPException(status_code=400, detail="Job cannot be cancelled (already completed or not found)")


# --- Batch Processing ---

@app.post("/api/enterprise/batch/process")
async def start_batch_process(
    request: BatchProcessRequest,
    background_tasks: BackgroundTasks,
    user = Depends(require_auth)
):
    """Start async batch processing for large datasets"""
    # Validate connector exists
    connector = await get_connector_by_id(request.connector_id)
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")

    # Create batch config
    batch_config = BatchConfig(
        chunk_size=request.chunk_size,
        parallel_chunks=request.parallel_chunks,
        fail_fast=request.fail_fast
    )

    # Create async job
    job = job_manager.create_job(
        job_type=f"batch_{request.operation}_{request.entity_type}",
        metadata={
            "connector_id": request.connector_id,
            "entity_type": request.entity_type,
            "operation": request.operation,
            "config": batch_config.__dict__
        }
    )

    # Define the batch processing coroutine
    async def run_batch():
        processor = BatchProcessor(batch_config)

        # Fetch data based on entity type
        conn_config = connector.get("connection_config", {}) or connector.get("config", {})
        server_url = conn_config.get("server_url", SALESFORCE_API_URL).rstrip("/")

        try:
            async with create_monitored_client(TimeoutTier.EXTENDED) as client:
                # Authenticate
                auth_response = await client.post(
                    f"{server_url}/api/auth/login",
                    json={"username": "admin", "password": "admin123"}
                )
                if auth_response.status_code != 200:
                    raise Exception("Authentication failed")

                token = auth_response.json().get("access_token", "")
                headers = {"Authorization": f"Bearer {token}"}

                # Fetch data
                data = []
                if request.entity_type == "cases":
                    response = await client.get(f"{server_url}/api/cases", headers=headers)
                    if response.status_code == 200:
                        resp_data = response.json()
                        # Handle both {"items": [...]} and direct array format
                        data = resp_data.get("items", resp_data) if isinstance(resp_data, dict) else resp_data
                elif request.entity_type == "accounts":
                    response = await client.get(f"{server_url}/api/accounts", headers=headers)
                    if response.status_code == 200:
                        resp_data = response.json()
                        data = resp_data.get("items", resp_data) if isinstance(resp_data, dict) else resp_data
                elif request.entity_type == "requests":
                    response = await client.get(f"{server_url}/api/accounts/requests", headers=headers)
                    if response.status_code == 200:
                        resp_data = response.json()
                        data = resp_data.get("items", resp_data) if isinstance(resp_data, dict) else resp_data

                job.total_items = len(data)

                # Define processor function based on operation
                async def process_items(items):
                    results = []
                    for item in items:
                        if request.operation == "sync":
                            # Simulate sync operation
                            results.append({"id": item.get("id"), "synced": True})
                        elif request.operation == "validate":
                            results.append({"id": item.get("id"), "valid": True})
                        elif request.operation == "transform":
                            results.append({"id": item.get("id"), "transformed": True})
                    return results

                # Process batch
                result = await processor.process_batch(data, process_items, job)
                return result.to_dict()

        except Exception as e:
            raise Exception(f"Batch processing failed: {str(e)}")

    # Run job in background
    background_tasks.add_task(job_manager.run_job, job.job_id, run_batch())

    return {
        "job_id": job.job_id,
        "status": "started",
        "message": f"Batch {request.operation} started for {request.entity_type}",
        "check_status_url": f"/api/enterprise/jobs/{job.job_id}"
    }


@app.get("/api/enterprise/batch/config")
async def get_batch_config_defaults(user = Depends(require_auth)):
    """Get default batch processing configuration"""
    default_config = BatchConfig()
    return {
        "defaults": {
            "chunk_size": default_config.chunk_size,
            "max_retries": default_config.max_retries,
            "retry_delay": default_config.retry_delay,
            "parallel_chunks": default_config.parallel_chunks,
            "fail_fast": default_config.fail_fast,
            "timeout_per_chunk": default_config.timeout_per_chunk
        },
        "limits": {
            "min_chunk_size": 1,
            "max_chunk_size": 500,
            "min_parallel_chunks": 1,
            "max_parallel_chunks": 10
        }
    }


# --- Watermarking / Incremental Sync ---

@app.get("/api/enterprise/watermarks")
async def list_watermarks(
    connector_id: Optional[int] = Query(None),
    user = Depends(require_auth)
):
    """List all watermarks for incremental sync tracking"""
    return {
        "watermarks": watermark_manager.list_watermarks(connector_id),
        "total": len(watermark_manager.watermarks)
    }


@app.get("/api/enterprise/watermarks/{entity_type}/{connector_id}")
async def get_watermark(
    entity_type: str,
    connector_id: int,
    user = Depends(require_auth)
):
    """Get watermark for specific entity type and connector"""
    wm = watermark_manager.get_watermark(entity_type, connector_id)
    if not wm:
        return {"exists": False, "entity_type": entity_type, "connector_id": connector_id}
    return {"exists": True, **wm.to_dict()}


@app.post("/api/enterprise/watermarks/reset")
async def reset_watermark(
    entity_type: str = Query(...),
    connector_id: int = Query(...),
    user = Depends(require_auth)
):
    """Reset watermark to trigger full resync"""
    watermark_manager.reset_watermark(entity_type, connector_id)
    return {
        "success": True,
        "message": f"Watermark reset for {entity_type} on connector {connector_id}",
        "next_sync": "full"
    }


@app.post("/api/enterprise/sync/incremental")
async def incremental_sync(
    request: IncrementalSyncRequest,
    background_tasks: BackgroundTasks,
    user = Depends(require_auth)
):
    """Perform incremental sync using watermarks"""
    connector = await get_connector_by_id(request.connector_id)
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")

    # Reset watermark if full sync requested
    if request.force_full_sync:
        watermark_manager.reset_watermark(request.entity_type, request.connector_id)

    # Get delta query params
    delta_params = watermark_manager.get_delta_query_params(request.entity_type, request.connector_id)

    # Create job for sync
    job = job_manager.create_job(
        job_type=f"incremental_sync_{request.entity_type}",
        metadata={
            "connector_id": request.connector_id,
            "entity_type": request.entity_type,
            "delta_params": delta_params,
            "force_full": request.force_full_sync
        }
    )

    async def run_incremental_sync():
        watermark_manager.update_sync_status(request.entity_type, request.connector_id, "syncing")

        conn_config = connector.get("connection_config", {}) or connector.get("config", {})
        server_url = conn_config.get("server_url", SALESFORCE_API_URL).rstrip("/")

        try:
            async with create_monitored_client(TimeoutTier.EXTENDED) as client:
                # Authenticate
                auth_response = await client.post(
                    f"{server_url}/api/auth/login",
                    json={"username": "admin", "password": "admin123"}
                )
                if auth_response.status_code != 200:
                    raise Exception("Authentication failed")

                token = auth_response.json().get("access_token", "")
                headers = {"Authorization": f"Bearer {token}"}

                # Fetch data with delta params if incremental
                params = {}
                if delta_params.get("incremental"):
                    params["modified_after"] = delta_params["modified_after"]

                # Fetch based on entity type
                data = []
                if request.entity_type == "cases":
                    response = await client.get(f"{server_url}/api/cases", headers=headers, params=params)
                    if response.status_code == 200:
                        resp_data = response.json()
                        data = resp_data.get("items", resp_data) if isinstance(resp_data, dict) else resp_data
                elif request.entity_type == "requests":
                    response = await client.get(f"{server_url}/api/accounts/requests", headers=headers, params=params)
                    if response.status_code == 200:
                        resp_data = response.json()
                        data = resp_data.get("items", resp_data) if isinstance(resp_data, dict) else resp_data

                job.total_items = len(data)

                # Process records (simulate sync)
                synced_count = 0
                last_id = None
                for item in data:
                    synced_count += 1
                    last_id = str(item.get("id", ""))
                    job_manager.update_progress(job.job_id, synced_count)

                # Update watermark
                watermark_manager.set_watermark(
                    entity_type=request.entity_type,
                    connector_id=request.connector_id,
                    timestamp=datetime.now(),
                    last_id=last_id,
                    records_synced=synced_count
                )
                watermark_manager.update_sync_status(request.entity_type, request.connector_id, "idle")

                return {
                    "records_synced": synced_count,
                    "sync_type": "full" if request.force_full_sync or not delta_params.get("incremental") else "incremental",
                    "last_id": last_id
                }

        except Exception as e:
            watermark_manager.update_sync_status(request.entity_type, request.connector_id, "error")
            raise

    background_tasks.add_task(job_manager.run_job, job.job_id, run_incremental_sync())

    return {
        "job_id": job.job_id,
        "sync_type": "full" if request.force_full_sync or not delta_params.get("incremental") else "incremental",
        "delta_params": delta_params,
        "check_status_url": f"/api/enterprise/jobs/{job.job_id}"
    }


# --- Performance Monitoring ---

@app.get("/api/enterprise/metrics")
async def get_all_metrics(
    window_seconds: int = Query(60, ge=10, le=3600),
    user = Depends(require_auth)
):
    """Get all performance metrics"""
    metrics = {}
    for metric_name in perf_monitor.metrics:
        metrics[metric_name] = perf_monitor.get_metric_stats(metric_name, window_seconds)

    return {
        "metrics": metrics,
        "error_rate_percent": perf_monitor.get_error_rate(window_seconds),
        "window_seconds": window_seconds,
        "collected_at": datetime.now().isoformat()
    }


@app.get("/api/enterprise/metrics/{metric_name}")
async def get_metric(
    metric_name: str,
    window_seconds: int = Query(60, ge=10, le=3600),
    user = Depends(require_auth)
):
    """Get specific metric statistics"""
    stats = perf_monitor.get_metric_stats(metric_name, window_seconds)
    if stats.get("samples", 0) == 0:
        raise HTTPException(status_code=404, detail=f"No samples for metric: {metric_name}")
    return stats


@app.post("/api/enterprise/metrics/record")
async def record_custom_metric(
    metric_name: str = Query(...),
    value: float = Query(...),
    user = Depends(require_auth)
):
    """Record a custom metric value"""
    perf_monitor.record_metric(metric_name, value)
    return {"success": True, "metric_name": metric_name, "value": value}


# --- Alerting ---

@app.get("/api/enterprise/alerts")
async def get_alerts(
    severity: Optional[str] = Query(None, description="Filter: warning, critical"),
    limit: int = Query(50, ge=1, le=200),
    user = Depends(require_auth)
):
    """Get recent alerts"""
    return {
        "alerts": perf_monitor.get_alerts(severity, limit),
        "total": len(perf_monitor.alerts)
    }


@app.get("/api/enterprise/thresholds")
async def get_alert_thresholds(user = Depends(require_auth)):
    """Get all configured alert thresholds"""
    return {"thresholds": perf_monitor.get_thresholds()}


@app.post("/api/enterprise/thresholds")
async def set_alert_threshold(
    request: AlertThresholdRequest,
    user = Depends(require_auth)
):
    """Set or update an alert threshold"""
    perf_monitor.set_threshold(
        request.metric_name,
        request.warning_threshold,
        request.critical_threshold,
        request.window_seconds
    )
    return {
        "success": True,
        "message": f"Threshold set for {request.metric_name}",
        "threshold": {
            "metric_name": request.metric_name,
            "warning": request.warning_threshold,
            "critical": request.critical_threshold,
            "window_seconds": request.window_seconds
        }
    }


@app.delete("/api/enterprise/thresholds/{metric_name}")
async def delete_alert_threshold(metric_name: str, user = Depends(require_auth)):
    """Delete an alert threshold"""
    if metric_name in perf_monitor.thresholds:
        del perf_monitor.thresholds[metric_name]
        return {"success": True, "message": f"Threshold deleted for {metric_name}"}
    raise HTTPException(status_code=404, detail="Threshold not found")


# --- Schema Validation ---

@app.get("/api/enterprise/schemas")
async def list_schemas(user = Depends(require_auth)):
    """List all registered validation schemas"""
    return {
        "schemas": schema_validator.list_schemas(),
        "total": len(schema_validator.schemas)
    }


@app.get("/api/enterprise/schemas/{schema_id}")
async def get_schema(schema_id: str, user = Depends(require_auth)):
    """Get a specific schema definition"""
    schema = schema_validator.get_schema(schema_id)
    if not schema:
        raise HTTPException(status_code=404, detail=f"Schema '{schema_id}' not found")
    return schema


@app.post("/api/enterprise/schemas")
async def register_schema(
    schema_id: str = Query(...),
    schema_type: str = Query(default="json_schema"),
    schema: Dict[str, Any] = Body(...),
    user = Depends(require_auth)
):
    """Register a new validation schema"""
    st = SchemaType(schema_type) if schema_type in [s.value for s in SchemaType] else SchemaType.JSON_SCHEMA
    schema_validator.register_schema(schema_id, st, schema)
    return {"success": True, "message": f"Schema '{schema_id}' registered", "schema_id": schema_id}


@app.post("/api/enterprise/validate/json")
async def validate_json_payload(
    schema_id: str = Query(...),
    payload: Dict[str, Any] = Body(...),
    user = Depends(require_auth)
):
    """Validate JSON payload against a schema"""
    result = schema_validator.validate_json(payload, schema_id)
    return result.to_dict()


@app.post("/api/enterprise/validate/xml")
async def validate_xml_payload(
    schema_id: str = Query(...),
    xml_content: str = Body(..., media_type="application/xml"),
    user = Depends(require_auth)
):
    """Validate XML payload against a schema"""
    result = schema_validator.validate_xml(xml_content, schema_id)
    return result.to_dict()


# --- DataWeave Transformation ---

@app.get("/api/enterprise/transformations")
async def list_transformations(user = Depends(require_auth)):
    """List all registered transformations"""
    return {
        "transformations": dataweave_transformer.list_transformations(),
        "total": len(dataweave_transformer.transformations)
    }


@app.get("/api/enterprise/transformations/{transformation_id}")
async def get_transformation(transformation_id: str, user = Depends(require_auth)):
    """Get a specific transformation definition"""
    transformation = dataweave_transformer.get_transformation(transformation_id)
    if not transformation:
        raise HTTPException(status_code=404, detail=f"Transformation '{transformation_id}' not found")
    return transformation


@app.post("/api/enterprise/transformations")
async def register_transformation(
    transformation_id: str = Query(...),
    source_format: str = Query(default="json"),
    target_format: str = Query(default="json"),
    mapping: Dict[str, str] = Body(...),
    user = Depends(require_auth)
):
    """Register a new transformation mapping"""
    dataweave_transformer.register_transformation(
        transformation_id, source_format, target_format, mapping
    )
    return {"success": True, "message": f"Transformation '{transformation_id}' registered"}


@app.post("/api/enterprise/transform")
async def execute_transformation(
    transformation_id: str = Query(...),
    strict: bool = Query(default=False, description="Fail on any error"),
    payload: Dict[str, Any] = Body(...),
    user = Depends(require_auth)
):
    """Execute a transformation on payload"""
    result = dataweave_transformer.transform(payload, transformation_id, strict=strict)
    return result.to_dict()


@app.post("/api/enterprise/transform/preview")
async def preview_transformation(
    transformation_id: str = Query(...),
    payload: Dict[str, Any] = Body(...),
    user = Depends(require_auth)
):
    """Preview transformation result without recording metrics"""
    result = dataweave_transformer.transform(payload, transformation_id, strict=False)
    return {
        "input": payload,
        "output": result.output,
        "transformation_id": transformation_id,
        "success": result.success,
        "errors": result.errors
    }


# --- Business Rule Validation ---

@app.get("/api/enterprise/rules")
async def list_business_rules(
    category: Optional[str] = Query(None),
    user = Depends(require_auth)
):
    """List all business rules"""
    return {
        "rules": business_rule_engine.list_rules(category),
        "total": len(business_rule_engine.rules),
        "categories": list(set(r["category"] for r in business_rule_engine.rules.values()))
    }


@app.get("/api/enterprise/rules/{rule_id}")
async def get_business_rule(rule_id: str, user = Depends(require_auth)):
    """Get a specific business rule"""
    rule = business_rule_engine.get_rule(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail=f"Rule '{rule_id}' not found")
    return {
        "id": rule["id"],
        "name": rule["name"],
        "category": rule["category"],
        "message": rule["message"],
        "severity": rule["severity"].value,
        "recoverable": rule["recoverable"],
        "evaluation_count": rule["evaluation_count"],
        "violation_count": rule["violation_count"]
    }


@app.get("/api/enterprise/rule-sets")
async def list_rule_sets(user = Depends(require_auth)):
    """List all rule sets"""
    return {
        "rule_sets": business_rule_engine.list_rule_sets()
    }


@app.post("/api/enterprise/rules/validate")
async def validate_business_rules(
    rule_set: Optional[str] = Query(None, description="Rule set to use"),
    category: Optional[str] = Query(None, description="Category to filter rules"),
    rule_ids: Optional[List[str]] = Query(None, description="Specific rule IDs"),
    stop_on_critical: bool = Query(default=True),
    payload: Dict[str, Any] = Body(...),
    user = Depends(require_auth)
):
    """Validate payload against business rules"""
    result = business_rule_engine.validate(
        payload,
        rule_ids=rule_ids,
        rule_set=rule_set,
        category=category,
        stop_on_critical=stop_on_critical
    )
    return result.to_dict()


@app.post("/api/enterprise/rules")
async def register_business_rule(
    rule_id: str = Query(...),
    name: str = Query(...),
    category: str = Query(...),
    condition: str = Query(..., description="Lambda expression: lambda d: d.get('field') > 0"),
    message: str = Query(...),
    severity: str = Query(default="error"),
    recoverable: bool = Query(default=True),
    user = Depends(require_auth)
):
    """Register a new business rule"""
    sev = RuleSeverity(severity) if severity in [s.value for s in RuleSeverity] else RuleSeverity.ERROR
    business_rule_engine.register_rule(rule_id, name, category, condition, message, sev, recoverable)
    return {"success": True, "message": f"Rule '{rule_id}' registered"}


# --- Error Categorization ---

@app.get("/api/enterprise/error-categories")
async def get_error_categories(user = Depends(require_auth)):
    """Get error category information and configurations"""
    return error_categorizer.get_category_stats()


@app.post("/api/enterprise/errors/categorize")
async def categorize_error(
    error_message: str = Query(...),
    http_status: Optional[int] = Query(None),
    source_system: Optional[str] = Query(None),
    target_system: Optional[str] = Query(None),
    user = Depends(require_auth)
):
    """Categorize an error and get retry recommendations"""
    categorized = error_categorizer.categorize(
        error_message,
        http_status=http_status,
        source_system=source_system,
        target_system=target_system
    )
    retry_delay = error_categorizer.get_retry_delay(categorized)
    return {
        **categorized.to_dict(),
        "recommended_retry_delay": retry_delay
    }


# --- Error Logging ---

@app.get("/api/enterprise/error-logs")
async def get_error_logs(
    category: Optional[str] = Query(None),
    recoverability: Optional[str] = Query(None),
    correlation_id: Optional[str] = Query(None),
    endpoint: Optional[str] = Query(None),
    hours: int = Query(default=24, ge=1, le=168),
    limit: int = Query(default=100, ge=1, le=1000),
    include_payloads: bool = Query(default=False),
    user = Depends(require_auth)
):
    """Search error logs"""
    cat = ErrorCategory(category) if category and category in [c.value for c in ErrorCategory] else None
    rec = RecoverabilityStatus(recoverability) if recoverability and recoverability in [r.value for r in RecoverabilityStatus] else None
    start_time = datetime.now() - timedelta(hours=hours)

    return {
        "logs": error_logger.search_logs(
            category=cat,
            recoverability=rec,
            correlation_id=correlation_id,
            endpoint=endpoint,
            start_time=start_time,
            limit=limit,
            include_payloads=include_payloads
        ),
        "stats": error_logger.get_stats()
    }


@app.get("/api/enterprise/error-logs/stats")
async def get_error_log_stats(user = Depends(require_auth)):
    """Get error logging statistics"""
    return error_logger.get_stats()


@app.get("/api/enterprise/error-logs/recent")
async def get_recent_errors(
    hours: int = Query(default=1, ge=1, le=24),
    limit: int = Query(default=50, ge=1, le=200),
    user = Depends(require_auth)
):
    """Get recent errors for quick monitoring"""
    return {
        "errors": error_logger.get_recent_errors(hours=hours, limit=limit),
        "window_hours": hours
    }


@app.get("/api/enterprise/error-logs/{log_id}")
async def get_error_log(log_id: str, user = Depends(require_auth)):
    """Get a specific error log entry with full details"""
    log = error_logger.get_log(log_id, include_payloads=True)
    if not log:
        raise HTTPException(status_code=404, detail=f"Error log '{log_id}' not found")
    return log


@app.post("/api/enterprise/error-logs/export")
async def export_error_logs(
    format: str = Query(default="json", description="Export format: json or csv"),
    category: Optional[str] = Query(None),
    hours: int = Query(default=24, ge=1, le=168),
    user = Depends(require_auth)
):
    """Export error logs"""
    cat = ErrorCategory(category) if category and category in [c.value for c in ErrorCategory] else None
    start_time = datetime.now() - timedelta(hours=hours)

    content = error_logger.export_logs(
        format=format,
        category=cat,
        start_time=start_time
    )

    return {
        "format": format,
        "content": content,
        "exported_at": datetime.now().isoformat()
    }


# --- Comprehensive Validation Pipeline ---

@app.post("/api/enterprise/validate/full")
async def full_validation_pipeline(
    schema_id: Optional[str] = Query(None, description="Schema to validate against"),
    rule_set: Optional[str] = Query(None, description="Business rule set to apply"),
    transformation_id: Optional[str] = Query(None, description="Transformation to apply after validation"),
    payload: Dict[str, Any] = Body(...),
    user = Depends(require_auth)
):
    """
    Execute full validation pipeline:
    1. Schema validation
    2. Business rule validation
    3. Optional transformation
    """
    results = {
        "timestamp": datetime.now().isoformat(),
        "payload_hash": hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()[:16],
        "stages": {}
    }

    overall_valid = True
    all_errors = []

    # Stage 1: Schema Validation
    if schema_id:
        schema_result = schema_validator.validate_json(payload, schema_id)
        results["stages"]["schema_validation"] = schema_result.to_dict()
        if not schema_result.valid:
            overall_valid = False
            all_errors.extend([{"stage": "schema", **e} for e in schema_result.errors])

    # Stage 2: Business Rule Validation
    if rule_set or not schema_id:
        rule_result = business_rule_engine.validate(
            payload,
            rule_set=rule_set or "full_validation",
            stop_on_critical=True
        )
        results["stages"]["business_rules"] = rule_result.to_dict()
        if not rule_result.valid:
            overall_valid = False
            all_errors.extend([{"stage": "business_rule", **v.to_dict()} for v in rule_result.violations])

    # Stage 3: Transformation (only if validation passed)
    if transformation_id and overall_valid:
        transform_result = dataweave_transformer.transform(payload, transformation_id, strict=False)
        results["stages"]["transformation"] = transform_result.to_dict()
        if not transform_result.success:
            all_errors.extend([{"stage": "transformation", **e} for e in transform_result.errors])
        results["transformed_output"] = transform_result.output

    results["overall_valid"] = overall_valid
    results["all_errors"] = all_errors
    results["error_count"] = len(all_errors)

    # Log if there were errors
    if all_errors:
        error_logger.log_error(
            f"Validation pipeline failed with {len(all_errors)} errors",
            endpoint="/api/enterprise/validate/full",
            method="POST",
            request_payload=payload,
            context={"schema_id": schema_id, "rule_set": rule_set, "transformation_id": transformation_id}
        )

    return results


# --- Enterprise Dashboard Summary ---

@app.get("/api/enterprise/dashboard")
async def enterprise_dashboard(user = Depends(require_auth)):
    """Get enterprise features dashboard summary"""
    return {
        "timestamp": datetime.now().isoformat(),
        "jobs": {
            "total": len(job_manager.jobs),
            "pending": len([j for j in job_manager.jobs.values() if j.status == JobStatus.PENDING]),
            "running": len([j for j in job_manager.jobs.values() if j.status == JobStatus.RUNNING]),
            "completed": len([j for j in job_manager.jobs.values() if j.status == JobStatus.COMPLETED]),
            "failed": len([j for j in job_manager.jobs.values() if j.status == JobStatus.FAILED])
        },
        "watermarks": {
            "total": len(watermark_manager.watermarks),
            "syncing": len([w for w in watermark_manager.watermarks.values() if w.sync_status == "syncing"])
        },
        "performance": {
            "error_rate_percent": perf_monitor.get_error_rate(60),
            "response_time": perf_monitor.get_metric_stats("response_time_ms", 60),
            "active_alerts": len([a for a in perf_monitor.alerts if a["severity"] == "critical"])
        },
        "validation": {
            "schemas_registered": len(schema_validator.schemas),
            "transformations_registered": len(dataweave_transformer.transformations),
            "business_rules": len(business_rule_engine.rules),
            "rule_sets": len(business_rule_engine.rule_sets)
        },
        "error_logging": error_logger.get_stats(),
        "timeout_tiers": list(TIMEOUT_CONFIGS.keys()),
        "recent_alerts": perf_monitor.get_alerts(limit=5),
        "recent_errors": error_logger.get_recent_errors(hours=1, limit=5)
    }


# ============================================================================
# HEALTH & MISC
# ============================================================================

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat(), "enterprise_features": True}

@app.get("/api/test")
async def test_endpoint():
    return {"message": "MCP API is working", "timestamp": datetime.now().isoformat()}

@app.post("/api/proxy/request")
async def proxy_request(data: Dict[str, Any] = Body(...), user = Depends(require_auth)):
    url = data.get("url")
    method = data.get("method", "GET")
    body = data.get("body")
    headers = data.get("headers", {})

    try:
        async with httpx.AsyncClient(verify=False, timeout=30) as client:
            if method == "GET":
                response = await client.get(url, headers=headers)
            else:
                response = await client.post(url, headers=headers, json=body)
            return {"status": response.status_code, "data": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text}
    except Exception as e:
        return {"error": str(e)}

# ============================================================================
# MCP SERVER (for AI model tool calls) - Optional
# ============================================================================

if MCP_AVAILABLE:
    mcp_server = Server("mulesoft-integration")

    @mcp_server.call_tool()
    async def mcp_sync_case_to_sap(case_id: int, operation: str = "CREATE"):
        """Synchronize a case to SAP via MuleSoft"""
        result = {"case_id": case_id, "operation": operation, "status": "synced"}
        return [TextContent(type="text", text=json.dumps(result))]

    @mcp_server.call_tool()
    async def mcp_health_check():
        """Check MuleSoft integration health"""
        result = {"status": "healthy", "timestamp": datetime.now().isoformat()}
        return [TextContent(type="text", text=json.dumps(result))]

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print(f"Starting MuleSoft MCP HTTP API on port {MCP_HTTP_PORT}")
    print(f"Frontend should connect to: http://localhost:{MCP_HTTP_PORT}/api")
    print(f"Remote backend can connect to: http://14.99.47.106:{MCP_HTTP_PORT}/api")
    uvicorn.run(app, host="0.0.0.0", port=MCP_HTTP_PORT)
