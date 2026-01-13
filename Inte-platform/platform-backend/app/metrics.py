from prometheus_client import Counter, Histogram, Gauge, Info
import time

# Integration Execution Metrics
integration_executions_total = Counter(
    'integration_executions_total',
    'Total number of integration executions',
    ['integration_name', 'status']  # status: success, failure
)

integration_execution_duration = Histogram(
    'integration_execution_duration_seconds',
    'Time spent executing integration',
    ['integration_name'],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

integration_records_processed = Counter(
    'integration_records_processed_total',
    'Total records processed by integration',
    ['integration_name', 'direction']  # direction: inbound, outbound
)

integration_errors_total = Counter(
    'integration_errors_total',
    'Total errors by integration',
    ['integration_name', 'error_type']
)

# Integration Status Gauge (1=deployed, 0=stopped, -1=error)
integration_status = Gauge(
    'integration_status',
    'Current status of integration',
    ['integration_name']
)

# Active Integrations Count
active_integrations = Gauge(
    'active_integrations_count',
    'Number of currently active integrations'
)

# API Call Metrics (for integrations calling external APIs)
api_calls_total = Counter(
    'integration_api_calls_total',
    'API calls made by integrations',
    ['integration_name', 'target_service', 'method', 'status_code']
)

api_call_duration = Histogram(
    'integration_api_call_duration_seconds',
    'Duration of API calls made by integrations',
    ['integration_name', 'target_service'],
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
)

# Helper functions
def record_execution(integration_name: str, success: bool, duration: float, records: int = 0):
    """Record an integration execution"""
    status = 'success' if success else 'failure'
    integration_executions_total.labels(integration_name=integration_name, status=status).inc()
    integration_execution_duration.labels(integration_name=integration_name).observe(duration)
    if records > 0:
        integration_records_processed.labels(integration_name=integration_name, direction='processed').inc(records)

def record_api_call(integration_name: str, target: str, method: str, status_code: int, duration: float):
    """Record an API call made by an integration"""
    api_calls_total.labels(
        integration_name=integration_name,
        target_service=target,
        method=method,
        status_code=str(status_code)
    ).inc()
    api_call_duration.labels(integration_name=integration_name, target_service=target).observe(duration)

def record_error(integration_name: str, error_type: str):
    """Record an integration error"""
    integration_errors_total.labels(integration_name=integration_name, error_type=error_type).inc()

def update_integration_status(integration_name: str, status: str):
    """Update integration status gauge"""
    status_map = {'deployed': 1, 'stopped': 0, 'error': -1, 'draft': 0}
    integration_status.labels(integration_name=integration_name).set(status_map.get(status, 0))

def update_active_count(count: int):
    """Update active integrations count"""
    active_integrations.set(count)
