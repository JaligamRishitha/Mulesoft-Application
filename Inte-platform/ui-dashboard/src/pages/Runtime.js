import React, { useState, useEffect } from 'react';
import { Table, Button, Tag, Space, Modal, List, message, Tooltip, Dropdown } from 'antd';
import { PlayCircleOutlined, PauseCircleOutlined, FileTextOutlined, HeartOutlined, ThunderboltOutlined, ReloadOutlined, MoreOutlined } from '@ant-design/icons';
import api from '../api';

export default function Runtime() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [logs, setLogs] = useState([]);
  const [logsModal, setLogsModal] = useState(false);
  const [selectedIntegration, setSelectedIntegration] = useState(null);
  const [executing, setExecuting] = useState({});

  const fetch = () => {
    setLoading(true);
    api.get('/integrations').then(({ data }) => setData(data)).finally(() => setLoading(false));
  };

  useEffect(() => { fetch(); }, []);

  const handleStart = async (id) => { 
    await api.post(`/runtime/${id}/start`); 
    message.success('Integration started'); 
    fetch(); 
  };
  
  const handleStop = async (id) => { 
    await api.post(`/runtime/${id}/stop`); 
    message.success('Integration stopped'); 
    fetch(); 
  };

  const handleExecute = async (id) => {
    setExecuting(prev => ({ ...prev, [id]: true }));
    try {
      const { data } = await api.post(`/runtime/${id}/execute`);
      message.success(`Execution completed - ${data.logsGenerated} log entries generated`);
    } catch (err) {
      message.error(err.response?.data?.detail || 'Execution failed');
    }
    setExecuting(prev => ({ ...prev, [id]: false }));
  };

  const handleLogs = async (id, name) => { 
    const { data } = await api.get(`/runtime/${id}/logs`); 
    setLogs(data); 
    setSelectedIntegration({ id, name });
    setLogsModal(true); 
  };

  const handleRefreshLogs = async () => {
    if (selectedIntegration) {
      const { data: newLogs } = await api.get(`/runtime/${selectedIntegration.id}/logs`);
      setLogs(newLogs);
      message.success('Logs refreshed');
    }
  };

  const handleHealth = async (id) => { 
    const { data } = await api.get(`/runtime/${id}/health`); 
    const healthStatus = data.healthy ? 'Healthy ✓' : 'Unhealthy ✗';
    const errorInfo = data.recentErrors > 0 ? ` (${data.recentErrors} recent errors)` : '';
    message[data.healthy ? 'success' : 'warning'](`${data.name}: ${healthStatus}${errorInfo}`); 
  };

  const getActionItems = (record) => [
    {
      key: 'execute',
      label: 'Execute Now',
      icon: <ThunderboltOutlined />,
      disabled: record.status !== 'deployed',
      onClick: () => handleExecute(record.id)
    },
    {
      key: 'logs',
      label: 'View Logs',
      icon: <FileTextOutlined />,
      onClick: () => handleLogs(record.id, record.name)
    },
    {
      key: 'health',
      label: 'Health Check',
      icon: <HeartOutlined />,
      onClick: () => handleHealth(record.id)
    }
  ];

  const columns = [
    { title: 'Name', dataIndex: 'name', key: 'name' },
    { title: 'Description', dataIndex: 'description', key: 'description', ellipsis: true },
    { 
      title: 'Status', 
      dataIndex: 'status', 
      key: 'status', 
      width: 100,
      render: (s) => (
        <Tag color={s === 'deployed' ? 'green' : s === 'stopped' ? 'orange' : s === 'error' ? 'red' : 'default'}>
          {s}
        </Tag>
      ) 
    },
    { 
      title: 'Actions', 
      key: 'actions',
      width: 200,
      render: (_, r) => (
        <Space size="small">
          <Tooltip title={r.status === 'deployed' ? 'Already running' : 'Start'}>
            <Button 
              icon={<PlayCircleOutlined />} 
              onClick={() => handleStart(r.id)} 
              disabled={r.status === 'deployed'}
              type={r.status !== 'deployed' ? 'primary' : 'default'}
              size="small"
            />
          </Tooltip>
          <Tooltip title={r.status === 'stopped' ? 'Already stopped' : 'Stop'}>
            <Button 
              icon={<PauseCircleOutlined />} 
              onClick={() => handleStop(r.id)} 
              disabled={r.status === 'stopped'}
              size="small"
            />
          </Tooltip>
          <Tooltip title="Execute now">
            <Button 
              icon={<ThunderboltOutlined />} 
              onClick={() => handleExecute(r.id)}
              disabled={r.status !== 'deployed'}
              loading={executing[r.id]}
              size="small"
              style={{ color: r.status === 'deployed' ? '#722ed1' : undefined }}
            />
          </Tooltip>
          <Dropdown menu={{ items: getActionItems(r) }} trigger={['click']}>
            <Button icon={<MoreOutlined />} size="small" />
          </Dropdown>
        </Space>
      )
    }
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h2>Runtime Manager</h2>
        <Button icon={<ReloadOutlined />} onClick={fetch}>Refresh</Button>
      </div>
      
      <Table dataSource={data} columns={columns} rowKey="id" loading={loading} />
      
      <Modal 
        title={`Logs - ${selectedIntegration?.name || 'Integration'}`} 
        open={logsModal} 
        onCancel={() => setLogsModal(false)} 
        footer={[
          <Button key="refresh" icon={<ReloadOutlined />} onClick={handleRefreshLogs}>Refresh</Button>,
          <Button key="close" type="primary" onClick={() => setLogsModal(false)}>Close</Button>
        ]}
        width={800}
      >
        <List 
          dataSource={logs} 
          style={{ maxHeight: 400, overflow: 'auto' }}
          renderItem={(l) => (
            <List.Item style={{ padding: '8px 0' }}>
              <Tag color={l.level === 'ERROR' ? 'red' : l.level === 'WARN' ? 'orange' : 'blue'} style={{ minWidth: 50, textAlign: 'center' }}>
                {l.level}
              </Tag>
              <span style={{ flex: 1, marginLeft: 8 }}>{l.message}</span>
              <span style={{ color: '#999', fontSize: 12, marginLeft: 8 }}>
                {new Date(l.timestamp).toLocaleString()}
              </span>
            </List.Item>
          )} 
          locale={{ emptyText: 'No logs available. Try executing the integration.' }} 
        />
      </Modal>
    </div>
  );
}
