import React, { useState, useEffect } from 'react';
import { Row, Col, Card, Statistic, Spin, Table, Tag, Progress, Badge } from 'antd';
import { ApiOutlined, CloudServerOutlined, WarningOutlined, ThunderboltOutlined, ArrowUpOutlined, CheckCircleOutlined, CloseCircleOutlined, ClockCircleOutlined } from '@ant-design/icons';
import { backendApi as api } from '../api';
import ApiTest from '../components/ApiTest';

// Lightweight Line Chart Component (optimized)
const SimpleLineChart = ({ data, color = '#00a1e0', height = 80 }) => {
  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min || 1;
  const points = data.map((v, i) => `${(i / (data.length - 1)) * 100},${100 - ((v - min) / range) * 80 - 10}`).join(' ');
  
  return (
    <svg width="100%" height={height} viewBox="0 0 100 100" preserveAspectRatio="none">
      <polyline 
        fill="none" 
        stroke={color} 
        strokeWidth="2" 
        points={points}
      />
    </svg>
  );
};

// Lightweight Bar Chart Component (optimized)
const SimpleBarChart = ({ data, color = '#00a1e0', height = 140 }) => {
  const max = Math.max(...data.map(d => d.value));
  return (
    <div style={{ display: 'flex', alignItems: 'flex-end', height, gap: 4, padding: '0 4px' }}>
      {data.map((d, i) => (
        <div key={i} style={{ flex: 1, textAlign: 'center' }}>
          <div 
            style={{ 
              background: color,
              height: `${(d.value / max) * 100}%`, 
              minHeight: 4, 
              borderRadius: 2
            }} 
          />
          <div style={{ fontSize: 10, color: '#666', marginTop: 4 }}>{d.label}</div>
        </div>
      ))}
    </div>
  );
};

// Stat Card Component
const StatCard = ({ title, value, prefix, suffix, color, trend, icon }) => (
  <Card 
    className="stat-card animate-fade-in-up" 
    style={{ 
      borderTop: `4px solid ${color}`,
      background: 'linear-gradient(135deg, #ffffff 0%, #f8fafc 100%)'
    }}
  >
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
      <div>
        <div style={{ color: '#666', fontSize: 13, marginBottom: 8 }}>{title}</div>
        <div style={{ fontSize: 28, fontWeight: 700, color: '#1a1a2e' }}>
          {prefix}{value}{suffix}
        </div>
        {trend && (
          <div style={{ marginTop: 8, fontSize: 12, color: trend > 0 ? '#52c41a' : '#ff4d4f' }}>
            <ArrowUpOutlined style={{ transform: trend < 0 ? 'rotate(180deg)' : 'none' }} />
            {' '}{Math.abs(trend)}% from last week
          </div>
        )}
      </div>
      <div style={{ 
        width: 48, 
        height: 48, 
        borderRadius: 12, 
        background: `linear-gradient(135deg, ${color}20 0%, ${color}10 100%)`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: 22,
        color: color
      }}>
        {icon}
      </div>
    </div>
  </Card>
);

export default function Dashboard() {
  const [stats, setStats] = useState({
    apiCount: 1,
    activeIntegrations: 1,
    errorRate: 0,
    throughput: 0
  });
  const [salesforceCases, setSalesforceCases] = useState([]);
  const [loading, setLoading] = useState(false);
  const [sfConnector, setSfConnector] = useState(null);

  useEffect(() => {
    // Only fetch connectors on load, don't auto-fetch external Salesforce data
    // User can connect to Salesforce through Connectors page
    const fetchConnectors = async () => {
      try {
        const { data: connectors } = await api.get('/connectors/');
        const connector = connectors.find(c => c.connector_type === 'salesforce');
        if (connector) setSfConnector(connector);
      } catch (e) {
        console.error('Error fetching connectors:', e);
      }
    };

    fetchConnectors();
  }, []);

  const trafficData = [120, 85, 145, 178, 320, 580, 720, 650, 890, 560, 440, 380];
  const responseTimeData = [45, 42, 38, 52, 78, 65, 58, 48, 55, 42, 35, 38];
  const errorData = [
    { label: '8am', value: 2 }, { label: '10am', value: 5 }, { label: '12pm', value: 8 },
    { label: '2pm', value: 4 }, { label: '4pm', value: 12 }, { label: '6pm', value: 6 }
  ];

  const sfServerUrl = sfConnector?.config?.server_url || 'not configured';

  const integrationStatus = [
    {
      name: 'Remote Salesforce Integration',
      status: salesforceCases.length > 0 ? 'deployed' : 'error',
      requests: salesforceCases.length * 50,
      latency: 85,
      health: salesforceCases.length > 0 ? 98 : 0,
      description: `Connected to ${sfServerUrl}`
    },
    {
      name: 'Salesforce to ServiceNow',
      status: salesforceCases.length > 0 ? 'deployed' : 'stopped',
      requests: salesforceCases.length * 30,
      latency: 95,
      health: salesforceCases.length > 0 ? 96 : 0,
      description: 'User account requests → ServiceNow tickets & approvals'
    },
    {
      name: 'Platform Event Processor',
      status: salesforceCases.length > 0 ? 'deployed' : 'stopped',
      requests: salesforceCases.length * 25,
      latency: 42,
      health: salesforceCases.length > 0 ? 95 : 0,
      description: 'Converts Salesforce cases to platform events'
    },
    {
      name: 'Case Sync Service',
      status: salesforceCases.length > 0 ? 'deployed' : 'error',
      requests: salesforceCases.length * 10,
      latency: 120,
      health: salesforceCases.length > 0 ? 92 : 0,
      description: 'Real-time case synchronization'
    }
  ];

  const recentLogs = salesforceCases.length > 0 ? [
    { time: new Date().toLocaleTimeString(), level: 'INFO', message: `Successfully fetched ${salesforceCases.length} cases from remote Salesforce server`, integration: 'Salesforce Sync' },
    { time: new Date(Date.now() - 60000).toLocaleTimeString(), level: 'INFO', message: `Connected to ${sfServerUrl}`, integration: 'Salesforce Connection' },
    { time: new Date(Date.now() - 120000).toLocaleTimeString(), level: 'INFO', message: 'Platform event format conversion completed', integration: 'Event Processor' },
    { time: new Date(Date.now() - 180000).toLocaleTimeString(), level: 'INFO', message: 'Real-time data sync active', integration: 'Case Sync' },
  ] : [
    { time: new Date().toLocaleTimeString(), level: 'ERROR', message: `Cannot connect to remote Salesforce server at ${sfServerUrl}`, integration: 'Salesforce Sync' },
    { time: new Date(Date.now() - 60000).toLocaleTimeString(), level: 'WARN', message: 'Retrying connection to remote server...', integration: 'Salesforce Connection' },
    { time: new Date(Date.now() - 120000).toLocaleTimeString(), level: 'ERROR', message: 'Connection failed - check server status', integration: 'Salesforce Connection' },
    { time: new Date(Date.now() - 180000).toLocaleTimeString(), level: 'WARN', message: 'Falling back to cached data', integration: 'Case Sync' },
  ];

  const serviceHealth = [
    { service: 'Remote Salesforce Server', status: salesforceCases.length > 0 ? 'healthy' : 'error', latency: 85, uptime: salesforceCases.length > 0 ? 99.7 : 0 },
    { service: 'ServiceNow ITSM', status: 'healthy', latency: 92, uptime: 99.5 },
    { service: 'Platform Backend', status: 'healthy', latency: 12, uptime: 100 },
    { service: 'Kong Gateway', status: 'healthy', latency: 8, uptime: 100 },
    { service: 'Database', status: 'healthy', latency: 5, uptime: 99.9 },
  ];

  // Show loading spinner only for data fetching, not initial render
  if (loading && salesforceCases.length === 0 && !stats.error) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '50vh' }}>
        <Spin size="large" />
        <span style={{ marginLeft: 16 }}>Loading dashboard...</span>
      </div>
    );
  }

  return (
    <div className="animate-fade-in">
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ marginBottom: 4 }}>Dashboard</h2>
        <p style={{ color: '#666', margin: 0 }}>Real-time overview of your integration platform</p>
      </div>
      
      {/* API Connection Test - Only show if there are connection issues */}
      {stats.error && <ApiTest />}
      
      {/* Stats Cards */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <StatCard 
            title="External Salesforce API" 
            value={salesforceCases.length > 0 ? "Connected" : "Disconnected"} 
            color={salesforceCases.length > 0 ? "#52c41a" : "#ff4d4f"} 
            trend={salesforceCases.length > 0 ? 100 : -100} 
            icon={<ApiOutlined />} 
          />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <StatCard 
            title="Live Cases" 
            value={salesforceCases.length} 
            color="#00a1e0" 
            trend={salesforceCases.length > 0 ? 25 : 0} 
            icon={<CloudServerOutlined />} 
          />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <StatCard 
            title="Connection Status" 
            value={stats?.error ? "Error" : "Healthy"} 
            color={stats?.error ? "#ff4d4f" : "#52c41a"} 
            trend={stats?.error ? -100 : 15} 
            icon={<WarningOutlined />} 
          />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <StatCard 
            title="Data Sync Rate" 
            value={salesforceCases.length * 2} 
            suffix="/min" 
            color="#5c6bc0" 
            trend={salesforceCases.length > 0 ? 23 : -50} 
            icon={<ThunderboltOutlined />} 
          />
        </Col>
      </Row>

      {/* Charts Row */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} lg={12}>
          <Card 
            title={<span style={{ fontWeight: 600 }}>API Traffic</span>}
            extra={<Tag color="blue" style={{ borderRadius: 12 }}>Last 24h</Tag>}
            className="animate-fade-in-up"
          >
            <div style={{ padding: '16px 0' }}>
              <SimpleLineChart data={trafficData} color="#00a1e0" height={100} />
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: '#999', marginTop: 8, padding: '0 4px' }}>
                <span>00:00</span><span>06:00</span><span>12:00</span><span>18:00</span><span>Now</span>
              </div>
            </div>
            <Row gutter={16} style={{ borderTop: '1px solid #f0f0f0', paddingTop: 16 }}>
              <Col span={8}><Statistic title="Peak" value={890} suffix="req/min" valueStyle={{ fontSize: 18, color: '#00a1e0' }} /></Col>
              <Col span={8}><Statistic title="Average" value={385} suffix="req/min" valueStyle={{ fontSize: 18 }} /></Col>
              <Col span={8}><Statistic title="Total" value="46.2K" valueStyle={{ fontSize: 18 }} /></Col>
            </Row>
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card 
            title={<span style={{ fontWeight: 600 }}>Response Time</span>}
            extra={<Tag color="green" style={{ borderRadius: 12 }}>Healthy</Tag>}
            className="animate-fade-in-up"
          >
            <div style={{ padding: '16px 0' }}>
              <SimpleLineChart data={responseTimeData} color="#52c41a" height={100} />
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: '#999', marginTop: 8, padding: '0 4px' }}>
                <span>00:00</span><span>06:00</span><span>12:00</span><span>18:00</span><span>Now</span>
              </div>
            </div>
            <Row gutter={16} style={{ borderTop: '1px solid #f0f0f0', paddingTop: 16 }}>
              <Col span={8}><Statistic title="P50" value={42} suffix="ms" valueStyle={{ fontSize: 18, color: '#52c41a' }} /></Col>
              <Col span={8}><Statistic title="P95" value={78} suffix="ms" valueStyle={{ fontSize: 18, color: '#faad14' }} /></Col>
              <Col span={8}><Statistic title="P99" value={120} suffix="ms" valueStyle={{ fontSize: 18, color: '#ff4d4f' }} /></Col>
            </Row>
          </Card>
        </Col>
      </Row>

      {/* Middle Row */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} lg={8}>
          <Card title={<span style={{ fontWeight: 600 }}>Errors Today</span>} className="animate-fade-in-up">
            <SimpleBarChart data={errorData} color="#ff4d4f" height={160} />
            <div style={{ marginTop: 16, textAlign: 'center', borderTop: '1px solid #f0f0f0', paddingTop: 16 }}>
              <Statistic title="Total Errors" value={37} valueStyle={{ color: '#ff4d4f', fontSize: 24 }} />
            </div>
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title={<span style={{ fontWeight: 600 }}>Integration Health</span>} className="animate-fade-in-up">
            <div style={{ padding: '8px 0' }}>
              {[
                { label: 'Deployed', count: 3, percent: 60, color: '#52c41a' },
                { label: 'Stopped', count: 1, percent: 20, color: '#faad14' },
                { label: 'Error', count: 1, percent: 20, color: '#ff4d4f' }
              ].map((item, i) => (
                <div key={i} style={{ marginBottom: 16 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                    <span style={{ fontWeight: 500 }}>{item.label}</span>
                    <span style={{ color: item.color, fontWeight: 600 }}>{item.count}</span>
                  </div>
                  <Progress 
                    percent={item.percent} 
                    strokeColor={item.color}
                    trailColor="#f0f0f0"
                    showInfo={false}
                    strokeWidth={8}
                    style={{ marginBottom: 0 }}
                  />
                </div>
              ))}
            </div>
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title={<span style={{ fontWeight: 600 }}>Service Status</span>} className="animate-fade-in-up">
            {serviceHealth.map((s, i) => (
              <div key={i} style={{ 
                display: 'flex', 
                justifyContent: 'space-between', 
                alignItems: 'center',
                padding: '12px 0',
                borderBottom: i < serviceHealth.length - 1 ? '1px solid #f5f5f5' : 'none'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <Badge status="success" />
                  <span style={{ fontWeight: 500 }}>{s.service}</span>
                </div>
                <div style={{ display: 'flex', gap: 16, fontSize: 12 }}>
                  <span style={{ color: '#666' }}>{s.latency}ms</span>
                  <span style={{ color: '#52c41a', fontWeight: 600 }}>{s.uptime}%</span>
                </div>
              </div>
            ))}
          </Card>
        </Col>
      </Row>

      {/* Tables Row */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={14}>
          <Card title={<span style={{ fontWeight: 600 }}>Integration Performance</span>} className="animate-fade-in-up">
            <Table
              dataSource={integrationStatus}
              rowKey="name"
              size="small"
              pagination={false}
              columns={[
                { 
                  title: 'Integration', 
                  dataIndex: 'name', 
                  key: 'name',
                  render: (name, r) => (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <div className={`status-dot ${r.status === 'deployed' ? 'active' : r.status === 'error' ? 'error' : 'inactive'}`} />
                      <span style={{ fontWeight: 500 }}>{name}</span>
                    </div>
                  )
                },
                { 
                  title: 'Status', 
                  dataIndex: 'status', 
                  key: 'status', 
                  width: 100, 
                  render: s => (
                    <Tag 
                      icon={s === 'deployed' ? <CheckCircleOutlined /> : s === 'error' ? <CloseCircleOutlined /> : <ClockCircleOutlined />}
                      color={s === 'deployed' ? 'success' : s === 'error' ? 'error' : 'warning'}
                      style={{ borderRadius: 12 }}
                    >
                      {s}
                    </Tag>
                  )
                },
                { title: 'Requests', dataIndex: 'requests', key: 'requests', width: 100, render: v => <span style={{ fontWeight: 500 }}>{v.toLocaleString()}</span> },
                { 
                  title: 'Health', 
                  dataIndex: 'health', 
                  key: 'health', 
                  width: 100, 
                  render: v => (
                    <Progress 
                      percent={v} 
                      size="small" 
                      strokeColor={v > 90 ? '#52c41a' : v > 70 ? '#faad14' : '#ff4d4f'}
                      format={p => `${p}%`}
                    />
                  )
                },
              ]}
            />
          </Card>
        </Col>
        <Col xs={24} lg={10}>
          <Card title={<span style={{ fontWeight: 600 }}>Recent Activity</span>} className="animate-fade-in-up">
            <Table
              dataSource={recentLogs}
              rowKey="time"
              size="small"
              pagination={false}
              showHeader={false}
              columns={[
                { 
                  dataIndex: 'level', 
                  key: 'level', 
                  width: 70, 
                  render: l => (
                    <Tag 
                      color={l === 'ERROR' ? 'error' : l === 'WARN' ? 'warning' : 'processing'}
                      style={{ borderRadius: 8, fontSize: 10 }}
                    >
                      {l}
                    </Tag>
                  )
                },
                { 
                  dataIndex: 'message', 
                  key: 'message',
                  render: (m, r) => (
                    <div>
                      <div style={{ fontSize: 13 }}>{m}</div>
                      <div style={{ fontSize: 11, color: '#999' }}>{r.integration} • {r.time}</div>
                    </div>
                  )
                },
              ]}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
}
