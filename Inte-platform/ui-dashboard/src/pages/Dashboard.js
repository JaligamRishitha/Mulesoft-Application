import React, { useState, useEffect } from 'react';
import { Row, Col, Card, Statistic, Spin, Table, Tag, Progress, Badge } from 'antd';
import { ApiOutlined, CloudServerOutlined, WarningOutlined, ThunderboltOutlined, ArrowUpOutlined, CheckCircleOutlined, CloseCircleOutlined, ClockCircleOutlined } from '@ant-design/icons';
import api from '../api';

// Animated Line Chart Component
const AnimatedLineChart = ({ data, color = '#00a1e0', height = 80 }) => {
  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min || 1;
  const points = data.map((v, i) => `${(i / (data.length - 1)) * 100},${100 - ((v - min) / range) * 80 - 10}`).join(' ');
  const areaPoints = `0,100 ${points} 100,100`;
  
  return (
    <svg width="100%" height={height} viewBox="0 0 100 100" preserveAspectRatio="none" style={{ overflow: 'visible' }}>
      <defs>
        <linearGradient id={`gradient-${color.replace('#', '')}`} x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor={color} stopOpacity="0.3" />
          <stop offset="100%" stopColor={color} stopOpacity="0.05" />
        </linearGradient>
      </defs>
      <polygon fill={`url(#gradient-${color.replace('#', '')})`} points={areaPoints} />
      <polyline 
        fill="none" 
        stroke={color} 
        strokeWidth="2.5" 
        strokeLinecap="round"
        strokeLinejoin="round"
        points={points}
        style={{ filter: `drop-shadow(0 2px 4px ${color}40)` }}
      />
    </svg>
  );
};

// Animated Bar Chart Component
const AnimatedBarChart = ({ data, color = '#00a1e0', height = 140 }) => {
  const max = Math.max(...data.map(d => d.value));
  return (
    <div style={{ display: 'flex', alignItems: 'flex-end', height, gap: 6, padding: '0 4px' }}>
      {data.map((d, i) => (
        <div key={i} style={{ flex: 1, textAlign: 'center' }} className="animate-fade-in-up stagger-item">
          <div 
            style={{ 
              background: `linear-gradient(180deg, ${color} 0%, ${color}99 100%)`,
              height: `${(d.value / max) * 100}%`, 
              minHeight: 8, 
              borderRadius: 4,
              boxShadow: `0 4px 12px ${color}40`,
              transition: 'height 0.5s ease'
            }} 
          />
          <div style={{ fontSize: 10, color: '#666', marginTop: 6, fontWeight: 500 }}>{d.label}</div>
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
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/dashboard/stats')
      .then(({ data }) => setStats(data))
      .catch(() => setStats({ apiCount: 7, activeIntegrations: 3, errorRate: 2.4, throughput: 1250 }))
      .finally(() => setLoading(false));
  }, []);

  const trafficData = [120, 85, 145, 178, 320, 580, 720, 650, 890, 560, 440, 380];
  const responseTimeData = [45, 42, 38, 52, 78, 65, 58, 48, 55, 42, 35, 38];
  const errorData = [
    { label: '8am', value: 2 }, { label: '10am', value: 5 }, { label: '12pm', value: 8 },
    { label: '2pm', value: 4 }, { label: '4pm', value: 12 }, { label: '6pm', value: 6 }
  ];

  const integrationStatus = [
    { name: 'SAP to Salesforce Sync', status: 'deployed', requests: 1250, latency: 45, health: 98 },
    { name: 'Order Processing Pipeline', status: 'deployed', requests: 890, latency: 62, health: 95 },
    { name: 'Inventory Alert System', status: 'stopped', requests: 0, latency: 0, health: 0 },
    { name: 'Payment Gateway', status: 'deployed', requests: 2100, latency: 38, health: 99 },
    { name: 'Customer 360 Aggregator', status: 'error', requests: 45, latency: 250, health: 45 },
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
    <div className="animate-fade-in">
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ marginBottom: 4 }}>Dashboard</h2>
        <p style={{ color: '#666', margin: 0 }}>Real-time overview of your integration platform</p>
      </div>
      
      {/* Stats Cards */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <StatCard title="API Endpoints" value={stats.apiCount} color="#00a1e0" trend={12} icon={<ApiOutlined />} />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <StatCard title="Active Integrations" value={stats.activeIntegrations} color="#52c41a" trend={8} icon={<CloudServerOutlined />} />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <StatCard title="Error Rate" value={stats.errorRate} suffix="%" color="#ff4d4f" trend={-15} icon={<WarningOutlined />} />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <StatCard title="Throughput" value={stats.throughput.toLocaleString()} suffix="/min" color="#5c6bc0" trend={23} icon={<ThunderboltOutlined />} />
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
              <AnimatedLineChart data={trafficData} color="#00a1e0" height={100} />
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
              <AnimatedLineChart data={responseTimeData} color="#52c41a" height={100} />
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
            <AnimatedBarChart data={errorData} color="#ff4d4f" height={160} />
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
