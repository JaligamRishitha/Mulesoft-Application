import React, { useState, useEffect } from 'react';
import { Row, Col, Card, Statistic, Spin, Table, Tag, Progress } from 'antd';
import { ApiOutlined, CloudServerOutlined, WarningOutlined, ThunderboltOutlined, ArrowUpOutlined, ArrowDownOutlined } from '@ant-design/icons';
import api from '../api';

// Simple SVG Line Chart Component
const SimpleLineChart = ({ data, color = '#1890ff', height = 60 }) => {
  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min || 1;
  const points = data.map((v, i) => `${(i / (data.length - 1)) * 100},${100 - ((v - min) / range) * 80 - 10}`).join(' ');
  return (
    <svg width="100%" height={height} viewBox="0 0 100 100" preserveAspectRatio="none">
      <polyline fill="none" stroke={color} strokeWidth="2" points={points} />
    </svg>
  );
};

// Simple Bar Chart Component
const SimpleBarChart = ({ data, color = '#1890ff', height = 120 }) => {
  const max = Math.max(...data.map(d => d.value));
  return (
    <div style={{ display: 'flex', alignItems: 'flex-end', height, gap: 4 }}>
      {data.map((d, i) => (
        <div key={i} style={{ flex: 1, textAlign: 'center' }}>
          <div style={{ background: color, height: `${(d.value / max) * 100}%`, minHeight: 4, borderRadius: 2 }} />
          <div style={{ fontSize: 10, color: '#999', marginTop: 4 }}>{d.label}</div>
        </div>
      ))}
    </div>
  );
};

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/dashboard/stats')
      .then(({ data }) => setStats(data))
      .catch(() => setStats({ apiCount: 7, activeIntegrations: 3, errorRate: 20, throughput: 1250 }))
      .finally(() => setLoading(false));
  }, []);

  // Mock data
  const trafficData = [120, 85, 45, 78, 320, 580, 720, 650, 890, 560, 340, 180];
  const responseTimeData = [45, 42, 38, 52, 78, 95, 120, 88, 145, 92, 65, 48];
  const errorData = [
    { label: '8am', value: 2 }, { label: '10am', value: 5 }, { label: '12pm', value: 12 },
    { label: '2pm', value: 4 }, { label: '4pm', value: 15 }, { label: '6pm', value: 7 }
  ];

  const integrationStatus = [
    { name: 'SAP to Salesforce Sync', status: 'deployed', requests: 1250, latency: 45 },
    { name: 'Order Processing Pipeline', status: 'deployed', requests: 890, latency: 62 },
    { name: 'Inventory Alert System', status: 'stopped', requests: 0, latency: 0 },
    { name: 'Payment Gateway', status: 'deployed', requests: 2100, latency: 38 },
    { name: 'Customer 360 Aggregator', status: 'error', requests: 45, latency: 250 },
  ];

  const recentLogs = [
    { time: '16:45:23', level: 'ERROR', message: 'Connection refused: CRM API unavailable', integration: 'Customer 360' },
    { time: '16:42:15', level: 'WARN', message: 'Slow response from SAP endpoint (2.3s)', integration: 'SAP Sync' },
    { time: '16:38:02', level: 'INFO', message: 'Processed 45 orders successfully', integration: 'Order Pipeline' },
    { time: '16:35:18', level: 'INFO', message: 'Synced 150 customer records', integration: 'SAP Sync' },
  ];

  const serviceHealth = [
    { service: 'ERP API', status: 'healthy', latency: 120, uptime: 99.9 },
    { service: 'CRM API', status: 'healthy', latency: 85, uptime: 99.7 },
    { service: 'ITSM API', status: 'healthy', latency: 65, uptime: 99.8 },
    { service: 'Kong Gateway', status: 'healthy', latency: 12, uptime: 100 },
  ];

  if (loading) return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />;

  return (
    <div>
      <h2>Dashboard</h2>
      
      {/* Stats Cards */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic title="API Endpoints" value={stats.apiCount} prefix={<ApiOutlined />} />
           
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="Active Integrations" value={stats.activeIntegrations} prefix={<CloudServerOutlined />} valueStyle={{ color: '#3f8600' }} suffix={<ArrowUpOutlined style={{ fontSize: 14 }} />} />
          
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="Error Rate" value={stats.errorRate} suffix="%" prefix={<WarningOutlined />} valueStyle={{ color: stats.errorRate > 5 ? '#cf1322' : '#3f8600' }} />
           
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="Throughput" value={stats.throughput} suffix="req/min" prefix={<ThunderboltOutlined />} />
           
          </Card>
        </Col>
      </Row>

      {/* Charts Row */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={12}>
          <Card title="API Traffic (24h)" extra={<Tag color="blue">Kong</Tag>}>
            <div style={{ padding: '20px 0' }}>
              <SimpleLineChart data={trafficData} color="#1890ff" height={120} />
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: '#999', marginTop: 8 }}>
                <span>00:00</span><span>06:00</span><span>12:00</span><span>18:00</span><span>24:00</span>
              </div>
            </div>
            <Row gutter={16}>
              <Col span={8}><Statistic title="Peak" value={890} suffix="req/min" valueStyle={{ fontSize: 16 }} /></Col>
              <Col span={8}><Statistic title="Average" value={385} suffix="req/min" valueStyle={{ fontSize: 16 }} /></Col>
              <Col span={8}><Statistic title="Total" value="46.2K" valueStyle={{ fontSize: 16 }} /></Col>
            </Row>
          </Card>
        </Col>
        <Col span={12}>
          <Card title="Response Time (ms)" extra={<Tag color="green">Camel</Tag>}>
            <div style={{ padding: '20px 0' }}>
              <SimpleLineChart data={responseTimeData} color="#52c41a" height={120} />
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: '#999', marginTop: 8 }}>
                <span>00:00</span><span>06:00</span><span>12:00</span><span>18:00</span><span>24:00</span>
              </div>
            </div>
            <Row gutter={16}>
              <Col span={8}><Statistic title="P50" value={65} suffix="ms" valueStyle={{ fontSize: 16, color: '#52c41a' }} /></Col>
              <Col span={8}><Statistic title="P95" value={120} suffix="ms" valueStyle={{ fontSize: 16, color: '#faad14' }} /></Col>
              <Col span={8}><Statistic title="P99" value={145} suffix="ms" valueStyle={{ fontSize: 16, color: '#ff4d4f' }} /></Col>
            </Row>
          </Card>
        </Col>
      </Row>

      {/* Errors and Status */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={8}>
          <Card title="Errors Today" extra={<Tag color="red">Kong + Camel</Tag>}>
            <SimpleBarChart data={errorData} color="#ff4d4f" height={140} />
            <div style={{ marginTop: 16, textAlign: 'center' }}>
              <Statistic title="Total Errors" value={45} valueStyle={{ color: '#ff4d4f' }} />
            </div>
          </Card>
        </Col>
        <Col span={8}>
          <Card title="Integration Status" extra={<Tag color="purple">Platform</Tag>}>
            <div style={{ padding: '10px 0' }}>
              <div style={{ marginBottom: 16 }}>
                <span>Deployed</span>
                <Progress percent={60} strokeColor="#52c41a" format={() => '3'} />
              </div>
              <div style={{ marginBottom: 16 }}>
                <span>Stopped</span>
                <Progress percent={20} strokeColor="#faad14" format={() => '1'} />
              </div>
              <div>
                <span>Error</span>
                <Progress percent={20} strokeColor="#ff4d4f" format={() => '1'} />
              </div>
            </div>
          </Card>
        </Col>
        <Col span={8}>
          <Card title="Security Metrics" extra={<Tag color="cyan">Kong</Tag>}>
            <div style={{ padding: '10px 0' }}>
              <div style={{ marginBottom: 16 }}>
                <span>Authenticated</span>
                <Progress percent={85} strokeColor="#1890ff" />
              </div>
              <div style={{ marginBottom: 16 }}>
                <span>Rate Limited</span>
                <Progress percent={8} strokeColor="#faad14" />
              </div>
              <div style={{ marginBottom: 16 }}>
                <span>Blocked (IP)</span>
                <Progress percent={5} strokeColor="#ff4d4f" />
              </div>
              <div>
                <span>Unauthorized</span>
                <Progress percent={2} strokeColor="#722ed1" />
              </div>
            </div>
          </Card>
        </Col>
      </Row>

      {/* Tables */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={14}>
          <Card title="Integration Performance" size="small">
            <Table
              dataSource={integrationStatus}
              rowKey="name"
              size="small"
              pagination={false}
              columns={[
                { title: 'Integration', dataIndex: 'name', key: 'name', ellipsis: true },
                { title: 'Status', dataIndex: 'status', key: 'status', width: 90, render: s => <Tag color={s === 'deployed' ? 'green' : s === 'error' ? 'red' : 'orange'}>{s}</Tag> },
                { title: 'Requests', dataIndex: 'requests', key: 'requests', width: 80, render: v => v.toLocaleString() },
                { title: 'Latency', dataIndex: 'latency', key: 'latency', width: 80, render: v => v ? `${v}ms` : '-' },
              ]}
            />
          </Card>
        </Col>
        <Col span={10}>
          <Card title="Service Health" size="small">
            <Table
              dataSource={serviceHealth}
              rowKey="service"
              size="small"
              pagination={false}
              columns={[
                { title: 'Service', dataIndex: 'service', key: 'service' },
                { title: 'Status', dataIndex: 'status', key: 'status', width: 70, render: () => <Tag color="green">●</Tag> },
                { title: 'Latency', dataIndex: 'latency', key: 'latency', width: 70, render: v => `${v}ms` },
                { title: 'Uptime', dataIndex: 'uptime', key: 'uptime', width: 70, render: v => `${v}%` },
              ]}
            />
          </Card>
        </Col>
      </Row>

      {/* Recent Logs */}
      <Card title="Recent Logs" size="small">
        <Table
          dataSource={recentLogs}
          rowKey="time"
          size="small"
          pagination={false}
          columns={[
            { title: 'Time', dataIndex: 'time', key: 'time', width: 100 },
            { title: 'Level', dataIndex: 'level', key: 'level', width: 80, render: l => <Tag color={l === 'ERROR' ? 'red' : l === 'WARN' ? 'orange' : 'blue'}>{l}</Tag> },
            { title: 'Integration', dataIndex: 'integration', key: 'integration', width: 150 },
            { title: 'Message', dataIndex: 'message', key: 'message' },
          ]}
        />
      </Card>
    </div>
  );
}
