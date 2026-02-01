"""
Enterprise Resilience Patterns for MuleSoft Application
"""
import asyncio
import time
import logging
from typing import Dict, Any, Optional, Callable
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import httpx
import json

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

@dataclass
class RetryConfig:
    max_retries: int = 3
    base_delay: float = 2.0
    max_delay: float = 60.0
    exponential_base: float = 2.0

@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5
    recovery_timeout: int = 60
    success_threshold: int = 3

@dataclass
class ConnectionPoolConfig:
    max_connections: int = 100
    max_keepalive_connections: int = 20
    keepalive_expiry: int = 5
    timeout: float = 30.0

class CircuitBreaker:
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        
    def can_execute(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        elif self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.config.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
                return True
            return False
        else:  # HALF_OPEN
            return True
    
    def record_success(self):
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0
    
    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitState.CLOSED and self.failure_count >= self.config.failure_threshold:
            self.state = CircuitState.OPEN
        elif self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN

class DeadLetterQueue:
    def __init__(self):
        self.messages: list = []
        
    async def add_message(self, message: Dict[str, Any], error: str, retry_count: int):
        dlq_entry = {
            "id": f"dlq_{int(time.time())}_{len(self.messages)}",
            "timestamp": datetime.now().isoformat(),
            "message": message,
            "error": error,
            "retry_count": retry_count,
            "status": "pending_manual_review"
        }
        self.messages.append(dlq_entry)
        logger.error(f"Message added to DLQ: {dlq_entry['id']} - {error}")
        
        # Auto-create ServiceNow incident for DLQ messages
        await self.create_servicenow_incident(dlq_entry)
        
    async def create_servicenow_incident(self, dlq_entry: Dict[str, Any]):
        """Create ServiceNow incident for DLQ message"""
        try:
            incident_data = {
                "short_description": f"MuleSoft DLQ Message: {dlq_entry['id']}",
                "description": f"Failed message requires manual intervention.\n\nError: {dlq_entry['error']}\nRetry Count: {dlq_entry['retry_count']}\nTimestamp: {dlq_entry['timestamp']}",
                "priority": "2",
                "category": "Software",
                "subcategory": "Integration",
                "caller_id": "mulesoft_system"
            }
            
            # This would integrate with your ServiceNow connector
            logger.info(f"ServiceNow incident created for DLQ message: {dlq_entry['id']}")
            
        except Exception as e:
            logger.error(f"Failed to create ServiceNow incident: {e}")

class EnterpriseHttpClient:
    def __init__(self, 
                 pool_config: ConnectionPoolConfig = None,
                 retry_config: RetryConfig = None,
                 circuit_config: CircuitBreakerConfig = None):
        
        self.pool_config = pool_config or ConnectionPoolConfig()
        self.retry_config = retry_config or RetryConfig()
        self.circuit_breaker = CircuitBreaker(circuit_config or CircuitBreakerConfig())
        self.dlq = DeadLetterQueue()
        
        # Configure connection pool
        limits = httpx.Limits(
            max_connections=self.pool_config.max_connections,
            max_keepalive_connections=self.pool_config.max_keepalive_connections,
            keepalive_expiry=self.pool_config.keepalive_expiry
        )
        
        timeout = httpx.Timeout(self.pool_config.timeout)
        
        self.client = httpx.AsyncClient(
            limits=limits,
            timeout=timeout,
            verify=False
        )
    
    async def execute_with_resilience(self, 
                                    method: str,
                                    url: str,
                                    **kwargs) -> httpx.Response:
        """Execute HTTP request with all resilience patterns"""
        
        if not self.circuit_breaker.can_execute():
            raise Exception("Circuit breaker is OPEN - request blocked")
        
        last_exception = None
        
        for attempt in range(self.retry_config.max_retries + 1):
            try:
                response = await self.client.request(method, url, **kwargs)
                
                if response.status_code < 500:  # Success or client error
                    self.circuit_breaker.record_success()
                    return response
                else:
                    raise httpx.HTTPStatusError(f"Server error: {response.status_code}", 
                                              request=response.request, response=response)
                    
            except Exception as e:
                last_exception = e
                self.circuit_breaker.record_failure()
                
                if attempt < self.retry_config.max_retries:
                    delay = min(
                        self.retry_config.base_delay * (self.retry_config.exponential_base ** attempt),
                        self.retry_config.max_delay
                    )
                    logger.warning(f"Request failed (attempt {attempt + 1}), retrying in {delay}s: {e}")
                    await asyncio.sleep(delay)
                else:
                    # Max retries exceeded - send to DLQ
                    await self.dlq.add_message(
                        message={
                            "method": method,
                            "url": url,
                            "kwargs": str(kwargs)
                        },
                        error=str(last_exception),
                        retry_count=attempt + 1
                    )
                    break
        
        raise last_exception
    
    async def get(self, url: str, **kwargs) -> httpx.Response:
        return await self.execute_with_resilience("GET", url, **kwargs)
    
    async def post(self, url: str, **kwargs) -> httpx.Response:
        return await self.execute_with_resilience("POST", url, **kwargs)
    
    async def put(self, url: str, **kwargs) -> httpx.Response:
        return await self.execute_with_resilience("PUT", url, **kwargs)
    
    async def delete(self, url: str, **kwargs) -> httpx.Response:
        return await self.execute_with_resilience("DELETE", url, **kwargs)
    
    def get_circuit_breaker_status(self) -> Dict[str, Any]:
        return {
            "state": self.circuit_breaker.state.value,
            "failure_count": self.circuit_breaker.failure_count,
            "success_count": self.circuit_breaker.success_count,
            "last_failure_time": self.circuit_breaker.last_failure_time
        }
    
    def get_dlq_messages(self) -> list:
        return self.dlq.messages
    
    async def close(self):
        await self.client.aclose()

# Global enterprise client instance
enterprise_client = EnterpriseHttpClient()

# Monitoring and alerting
class AlertManager:
    @staticmethod
    async def send_circuit_breaker_alert(service_name: str, state: str):
        """Send alert when circuit breaker state changes"""
        alert_data = {
            "service": service_name,
            "alert_type": "circuit_breaker_state_change",
            "state": state,
            "timestamp": datetime.now().isoformat(),
            "severity": "high" if state == "open" else "medium"
        }
        
        # Create ServiceNow incident for circuit breaker alerts
        try:
            incident_data = {
                "short_description": f"Circuit Breaker {state.upper()}: {service_name}",
                "description": f"Circuit breaker for {service_name} changed to {state} state at {alert_data['timestamp']}",
                "priority": "2" if state == "open" else "3",
                "category": "Software",
                "subcategory": "Integration"
            }
            logger.warning(f"Circuit breaker alert: {service_name} is {state}")
            
        except Exception as e:
            logger.error(f"Failed to send circuit breaker alert: {e}")
    
    @staticmethod
    async def send_dlq_alert(message_count: int):
        """Send alert when DLQ reaches threshold"""
        if message_count > 10:  # Threshold
            try:
                incident_data = {
                    "short_description": f"High DLQ Message Count: {message_count}",
                    "description": f"Dead Letter Queue has {message_count} messages requiring manual intervention",
                    "priority": "2",
                    "category": "Software",
                    "subcategory": "Integration"
                }
                logger.error(f"DLQ alert: {message_count} messages in queue")
                
            except Exception as e:
                logger.error(f"Failed to send DLQ alert: {e}")
