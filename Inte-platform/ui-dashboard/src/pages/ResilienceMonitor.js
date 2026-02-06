import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Statistic, Table, Button, Tag, Space, Modal, message, Progress } from 'antd';
import { 
  ThunderboltOutlined, 
  ExclamationCircleOutlined, 
  CheckCircleOutlined, 
  CloseCircleOutlined,
  ReloadOutlined,
  WarningOutlined
} from '@ant-design/icons';
import { backendApi as api } from '../api';

const ResilienceMonitor = () => {
  const [status, setStatus] = useState(null);
  const [dlqMessages, setDlqMessages] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000); // Refresh every 5 seconds
    return () => clearInterval(interval);
  }, []);

  const fetchData = async () => {
    try {
      const [statusRes, dlqRes, metricsRes] = await Promise.all([
        api.get('/resilience/status'),
        api.get('/resilience/dlq/messages'),
        api.get('/resilience/metrics')
      ]);
      
      setStatus(statusRes.data);
      setDlqMessages(dlqRes.data);
      setMetrics(metricsRes.data);
    } catch (error) {
      console.error('Failed to fetch resilience data:', error);
    } finally {
      setLoading(false);
    }
  };

  const resetCircuitBreaker = async () => {
    try {
      await api.post('/resilience/circuit-breaker/reset');
      message.success('Circuit breaker reset successfully');
      fetchData();
    } catch (error) {
      message.error('Failed to reset circuit breaker');
    }
  };

  const retryDlqMessage = async (messageId) => {
    try {
      await api.post(`/resilience/dlq/messages/${messageId}/retry`);
      message.success('Message marked for retry');
      fetchData();
    } catch (error) {
      message.error('Failed to retry message');
    }
  };

  const resolveDlqMessage = async (messageId) => {
    try {
      await api.post(`/resilience/dlq/messages/${messageId}/resolve`);
      message.success('Message resolved');
      fetchData();
    } catch (error) {
      message.error('Failed to resolve message');
    }
  };

  const testFailure = async () => {
    try {
      const response = await api.post('/resilience/test/failure');
      message.info('Failure scenario tested - check circuit breaker status');
      fetchData();
    } catch (error) {
      message.info('Failure scenario executed');
      fetchData();
    }
  };

  const getCircuitBreakerColor = (state) => {
    switch (state) {
      case 'closed': return 'green';
      case 'open': return 'red';
      case 'half_open': return 'orange';
      default: return 'gray';
    }
  };

  const dlqColumns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 200,
    },
    {
      title: 'Timestamp',
      dataIndex: 'timestamp',
      key: 'timestamp',
      render: (timestamp) => new Date(timestamp).toLocaleString(),
    },
    {
      title: 'Error',
      dataIndex: 'error',
      key: 'error',
      ellipsis: true,
    },
    {
      title: 'Retry Count',
      dataIndex: 'retry_count',
      key: 'retry_count',
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status) => (
        <Tag color={status === 'resolved' ? 'green' : status === 'retrying' ? 'blue' : 'red'}>
          {status.toUpperCase()}
        </Tag>
      ),
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button 
            size="small" 
            onClick={() => retryDlqMessage(record.id)}
            disabled={record.status === 'resolved'}
          >
            Retry
          </Button>
          <Button 
            size="small" 
            type="primary"
            onClick={() => resolveDlqMessage(record.id)}
            disabled={record.status === 'resolved'}
          >
            Resolve
          </Button>
        </Space>
      ),
    },
  ];

  if (loading) {
    return <div>Loading resilience monitor...</div>;
  }

  return (
    <div style={{ padding: '24px' }}>
      <Row gutter={[16, 16]}>
        <Col span={24}>
          <h2>Enterprise Resilience Monitor</h2>
        </Col>
        
        {/* Status Cards */}
        <Col span={6}>
          <Card>
            <Statistic
              title="Circuit Breaker"
              value={status?.circuit_breaker?.state?.toUpperCase() || 'UNKNOWN'}
              valueStyle={{ color: getCircuitBreakerColor(status?.circuit_breaker?.state) }}
              prefix={<ThunderboltOutlined />}
            />
            <div style={{ marginTop: 8 }}>
              <Button 
                size="small" 
                onClick={resetCircuitBreaker}
                disabled={status?.circuit_breaker?.state === 'closed'}
              >
                Reset
              </Button>
            </div>
          </Card>
        </Col>
        
        <Col span={6}>
          <Card>
            <Statistic
              title="DLQ Messages"
              value={status?.dead_letter_queue?.message_count || 0}
              valueStyle={{ color: (status?.dead_letter_queue?.message_count || 0) > 10 ? '#cf1322' : '#3f8600' }}
              prefix={<ExclamationCircleOutlined />}
            />
            <div style={{ marginTop: 8, fontSize: '12px', color: '#666' }}>
              {status?.dead_letter_queue?.pending_messages || 0} pending
            </div>
          </Card>
        </Col>
        
        <Col span={6}>
          <Card>
            <Statistic
              title="Connection Pool"
              value="Healthy"
              valueStyle={{ color: '#3f8600' }}
              prefix={<CheckCircleOutlined />}
            />
            <div style={{ marginTop: 8, fontSize: '12px', color: '#666' }}>
              Max: 100 connections
            </div>
          </Card>
        </Col>
        
        <Col span={6}>
          <Card>
            <Statistic
              title="Failure Count"
              value={status?.circuit_breaker?.failure_count || 0}
              valueStyle={{ color: (status?.circuit_breaker?.failure_count || 0) > 0 ? '#cf1322' : '#3f8600' }}
              prefix={<WarningOutlined />}
            />
            <div style={{ marginTop: 8 }}>
              <Button size="small" onClick={testFailure}>
                Test Failure
              </Button>
            </div>
          </Card>
        </Col>
      </Row>

      {/* Configuration Details */}
      <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
        <Col span={8}>
          <Card title="Retry Policy" size="small">
            <p><strong>Max Retries:</strong> 3</p>
            <p><strong>Base Delay:</strong> 2s</p>
            <p><strong>Max Delay:</strong> 60s</p>
            <p><strong>Backoff:</strong> Exponential (2x)</p>
          </Card>
        </Col>
        
        <Col span={8}>
          <Card title="Circuit Breaker" size="small">
            <p><strong>Failure Threshold:</strong> 5</p>
            <p><strong>Recovery Timeout:</strong> 60s</p>
            <p><strong>Success Threshold:</strong> 3</p>
            <p><strong>Current Failures:</strong> {status?.circuit_breaker?.failure_count || 0}</p>
          </Card>
        </Col>
        
        <Col span={8}>
          <Card title="Connection Pool" size="small">
            <p><strong>Max Connections:</strong> 100</p>
            <p><strong>Keep-Alive:</strong> 20</p>
            <p><strong>Keep-Alive Expiry:</strong> 5s</p>
            <p><strong>Timeout:</strong> 30s</p>
          </Card>
        </Col>
      </Row>

      {/* Dead Letter Queue */}
      <Row style={{ marginTop: 24 }}>
        <Col span={24}>
          <Card 
            title="Dead Letter Queue Messages" 
            extra={
              <Button icon={<ReloadOutlined />} onClick={fetchData}>
                Refresh
              </Button>
            }
          >
            <Table
              columns={dlqColumns}
              dataSource={dlqMessages}
              rowKey="id"
              pagination={{ pageSize: 10 }}
              size="small"
            />
          </Card>
        </Col>
      </Row>

      {/* Alerts */}
      {metrics?.alerts && (
        <Row style={{ marginTop: 24 }}>
          <Col span={24}>
            <Card title="Active Alerts">
              {metrics.alerts.circuit_breaker_open && (
                <Tag color="red" style={{ marginBottom: 8 }}>
                  <ExclamationCircleOutlined /> Circuit Breaker OPEN
                </Tag>
              )}
              {metrics.alerts.high_dlq_count && (
                <Tag color="orange" style={{ marginBottom: 8 }}>
                  <WarningOutlined /> High DLQ Message Count
                </Tag>
              )}
              {metrics.alerts.recent_failures && (
                <Tag color="yellow" style={{ marginBottom: 8 }}>
                  <WarningOutlined /> Recent Failures Detected
                </Tag>
              )}
              {!metrics.alerts.circuit_breaker_open && !metrics.alerts.high_dlq_count && !metrics.alerts.recent_failures && (
                <Tag color="green">
                  <CheckCircleOutlined /> All Systems Healthy
                </Tag>
              )}
            </Card>
          </Col>
        </Row>
      )}
    </div>
  );
};

export default ResilienceMonitor;
