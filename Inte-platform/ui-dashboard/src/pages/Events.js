import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Table, Tag, Space, Button, Form, Input, Select, message, Spin, Tabs, Modal, Alert, Tooltip, Badge } from 'antd';
import {
  SendOutlined, ReloadOutlined, CheckCircleOutlined, ClockCircleOutlined,
  ExclamationCircleOutlined, CloseCircleOutlined, SearchOutlined,
  ThunderboltOutlined, DatabaseOutlined, FileTextOutlined, PlusOutlined
} from '@ant-design/icons';
import { backendApi as api } from '../api';

const { Option } = Select;
const { TextArea } = Input;

export default function Events() {
  const [events, setEvents] = useState([]);
  const [mappings, setMappings] = useState([]);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [statusLoading, setStatusLoading] = useState(false);
  const [selectedEventId, setSelectedEventId] = useState(null);
  const [eventStatus, setEventStatus] = useState(null);
  const [statusModalVisible, setStatusModalVisible] = useState(false);
  const [form] = Form.useForm();

  useEffect(() => {
    fetchEvents();
    fetchMappings();
  }, []);

  const fetchEvents = async () => {
    setLoading(true);
    try {
      const { data } = await api.get('/events/');
      setEvents(data.events || data || []);
    } catch (err) {
      console.error('Failed to fetch events:', err);
      message.error('Failed to fetch events');
    }
    setLoading(false);
  };

  const fetchMappings = async () => {
    try {
      const { data } = await api.get('/events/mappings');
      setMappings(data.mappings || data || []);
    } catch (err) {
      console.error('Failed to fetch mappings:', err);
    }
  };

  const handleSubmitEvent = async (values) => {
    setSubmitting(true);
    try {
      const payload = {
        event_type: values.event_type,
        source_system: values.source_system,
        title: values.title,
        description: values.description,
        affected_user: values.affected_user || null,
        priority: values.priority || 'medium'
      };

      const { data } = await api.post('/events/capture', payload);

      if (data.success || data.event_id) {
        message.success(`Event captured successfully! ID: ${data.event_id}`);
        form.resetFields();
        fetchEvents();
      } else {
        message.error(data.message || 'Failed to capture event');
      }
    } catch (err) {
      console.error('Failed to capture event:', err);
      message.error(err.response?.data?.detail || 'Failed to capture event');
    }
    setSubmitting(false);
  };

  const checkEventStatus = async (eventId) => {
    setSelectedEventId(eventId);
    setStatusLoading(true);
    setStatusModalVisible(true);
    setEventStatus(null);

    try {
      const { data } = await api.get(`/events/${eventId}/status`);
      setEventStatus(data);
    } catch (err) {
      console.error('Failed to fetch event status:', err);
      setEventStatus({ error: err.response?.data?.detail || 'Failed to fetch status' });
    }
    setStatusLoading(false);
  };

  const getStatusTag = (status) => {
    const statusConfig = {
      pending: { color: 'orange', icon: <ClockCircleOutlined /> },
      processing: { color: 'blue', icon: <ThunderboltOutlined spin /> },
      completed: { color: 'green', icon: <CheckCircleOutlined /> },
      failed: { color: 'red', icon: <CloseCircleOutlined /> },
      warning: { color: 'gold', icon: <ExclamationCircleOutlined /> }
    };
    const config = statusConfig[status?.toLowerCase()] || statusConfig.pending;
    return <Tag icon={config.icon} color={config.color} style={{ borderRadius: 12 }}>{status || 'Unknown'}</Tag>;
  };

  const getPriorityTag = (priority) => {
    const colors = { critical: 'red', high: 'orange', medium: 'blue', low: 'green' };
    return <Tag color={colors[priority] || 'default'} style={{ borderRadius: 12 }}>{priority || 'medium'}</Tag>;
  };

  const eventColumns = [
    {
      title: 'Event ID',
      dataIndex: 'id',
      key: 'id',
      width: 100,
      render: (id) => <span style={{ fontWeight: 600, color: '#1890ff', fontFamily: 'monospace' }}>#{id}</span>
    },
    {
      title: 'Type',
      dataIndex: 'event_type',
      key: 'event_type',
      width: 150,
      filters: [
        { text: 'User Creation', value: 'user_creation' },
        { text: 'Password Reset', value: 'password_reset' },
        { text: 'Work Order', value: 'work_order' },
        { text: 'Access Request', value: 'access_request' },
        { text: 'System Alert', value: 'system_alert' }
      ],
      onFilter: (value, record) => record.event_type === value,
      render: (type) => <Tag color="purple" style={{ borderRadius: 8 }}>{type?.replace(/_/g, ' ')}</Tag>
    },
    {
      title: 'Source',
      dataIndex: 'source_system',
      key: 'source_system',
      width: 120,
      render: (source) => <Tag color="cyan" style={{ borderRadius: 8 }}>{source}</Tag>
    },
    {
      title: 'Title',
      dataIndex: 'title',
      key: 'title',
      ellipsis: true,
      render: (title) => <Tooltip title={title}><span style={{ fontWeight: 500 }}>{title}</span></Tooltip>
    },
    {
      title: 'Priority',
      dataIndex: 'priority',
      key: 'priority',
      width: 100,
      filters: [
        { text: 'Critical', value: 'critical' },
        { text: 'High', value: 'high' },
        { text: 'Medium', value: 'medium' },
        { text: 'Low', value: 'low' }
      ],
      onFilter: (value, record) => record.priority === value,
      render: (priority) => getPriorityTag(priority)
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status) => getStatusTag(status)
    },
    {
      title: 'Created',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 150,
      sorter: (a, b) => new Date(a.created_at) - new Date(b.created_at),
      render: (date) => <span style={{ fontSize: 12, color: '#8c8c8c' }}>{date ? new Date(date).toLocaleString() : 'N/A'}</span>
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 100,
      render: (_, record) => (
        <Tooltip title="Check Status">
          <Button
            size="small"
            icon={<SearchOutlined />}
            onClick={() => checkEventStatus(record.id)}
            style={{ borderRadius: 6 }}
          >
            Status
          </Button>
        </Tooltip>
      )
    }
  ];

  const mappingColumns = [
    {
      title: 'Event Type',
      dataIndex: 'event_type',
      key: 'event_type',
      render: (type) => <Tag color="purple" style={{ borderRadius: 8 }}>{type?.replace(/_/g, ' ')}</Tag>
    },
    {
      title: 'Category',
      dataIndex: 'category',
      key: 'category',
      render: (cat) => <Tag color="blue" style={{ borderRadius: 8 }}>{cat}</Tag>
    },
    {
      title: 'Target System',
      dataIndex: 'target_system',
      key: 'target_system',
      render: (sys) => <Tag color="geekblue" style={{ borderRadius: 8 }}>{sys}</Tag>
    },
    {
      title: 'Priority Mapping',
      dataIndex: 'priority_mapping',
      key: 'priority_mapping',
      render: (mapping) => mapping ? Object.entries(mapping).map(([k, v]) => (
        <Tag key={k} style={{ marginBottom: 4, borderRadius: 8 }}>{k} → {v}</Tag>
      )) : '-'
    },
    {
      title: 'Auto Process',
      dataIndex: 'auto_process',
      key: 'auto_process',
      render: (auto) => auto ? <Tag color="green">Yes</Tag> : <Tag color="default">No</Tag>
    }
  ];

  const statsCards = [
    { title: 'Total Events', value: events.length, color: '#1890ff', icon: <DatabaseOutlined /> },
    { title: 'Pending', value: events.filter(e => e.status === 'pending').length, color: '#faad14', icon: <ClockCircleOutlined /> },
    { title: 'Processing', value: events.filter(e => e.status === 'processing').length, color: '#1890ff', icon: <ThunderboltOutlined /> },
    { title: 'Completed', value: events.filter(e => e.status === 'completed').length, color: '#52c41a', icon: <CheckCircleOutlined /> }
  ];

  return (
    <div className="animate-fade-in">
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ marginBottom: 4, color: '#262626' }}>System Events</h2>
        <p style={{ color: '#8c8c8c', margin: 0 }}>Capture and track system events for processing</p>
      </div>

      {/* Stats Cards */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        {statsCards.map((stat, index) => (
          <Col span={6} key={index}>
            <Card size="small" style={{ borderRadius: 12, borderTop: `4px solid ${stat.color}` }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div>
                  <div style={{ fontSize: 28, fontWeight: 700, color: stat.color }}>{stat.value}</div>
                  <div style={{ color: '#8c8c8c', fontSize: 13 }}>{stat.title}</div>
                </div>
                <div style={{ fontSize: 32, color: stat.color, opacity: 0.3 }}>{stat.icon}</div>
              </div>
            </Card>
          </Col>
        ))}
      </Row>

      <Tabs defaultActiveKey="capture" items={[
        {
          key: 'capture',
          label: <span><PlusOutlined /> Capture Event</span>,
          children: (
            <Card style={{ borderRadius: 12 }}>
              <Form
                form={form}
                layout="vertical"
                onFinish={handleSubmitEvent}
                style={{ maxWidth: 800 }}
              >
                <Row gutter={16}>
                  <Col span={12}>
                    <Form.Item
                      name="event_type"
                      label="Event Type"
                      rules={[{ required: true, message: 'Please select event type' }]}
                    >
                      <Select placeholder="Select event type" size="large">
                        <Option value="user_creation">User Creation</Option>
                        <Option value="password_reset">Password Reset</Option>
                        <Option value="work_order">Work Order</Option>
                        <Option value="access_request">Access Request</Option>
                        <Option value="system_alert">System Alert</Option>
                      </Select>
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item
                      name="source_system"
                      label="Source System"
                      rules={[{ required: true, message: 'Please select source system' }]}
                    >
                      <Select placeholder="Select source system" size="large">
                        <Option value="salesforce">Salesforce</Option>
                        <Option value="sap">SAP</Option>
                        <Option value="monitoring">Monitoring</Option>
                        <Option value="email">Email</Option>
                      </Select>
                    </Form.Item>
                  </Col>
                </Row>

                <Form.Item
                  name="title"
                  label="Title"
                  rules={[{ required: true, message: 'Please enter event title' }]}
                >
                  <Input placeholder="Enter event title" size="large" />
                </Form.Item>

                <Form.Item
                  name="description"
                  label="Description"
                  rules={[{ required: true, message: 'Please enter description' }]}
                >
                  <TextArea rows={4} placeholder="Enter event description" />
                </Form.Item>

                <Row gutter={16}>
                  <Col span={12}>
                    <Form.Item name="affected_user" label="Affected User (Optional)">
                      <Input placeholder="Enter affected user email or ID" size="large" />
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item name="priority" label="Priority (Optional)" initialValue="medium">
                      <Select size="large">
                        <Option value="critical">Critical</Option>
                        <Option value="high">High</Option>
                        <Option value="medium">Medium</Option>
                        <Option value="low">Low</Option>
                      </Select>
                    </Form.Item>
                  </Col>
                </Row>

                <Form.Item>
                  <Button
                    type="primary"
                    htmlType="submit"
                    icon={<SendOutlined />}
                    loading={submitting}
                    size="large"
                    style={{ borderRadius: 8 }}
                  >
                    Capture Event
                  </Button>
                </Form.Item>
              </Form>
            </Card>
          )
        },
        {
          key: 'events',
          label: <span><DatabaseOutlined /> Recent Events <Badge count={events.length} style={{ marginLeft: 8 }} /></span>,
          children: (
            <Card
              style={{ borderRadius: 12 }}
              title={
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span>Recent Events</span>
                  <Button icon={<ReloadOutlined />} onClick={fetchEvents} loading={loading} style={{ borderRadius: 8 }}>
                    Refresh
                  </Button>
                </div>
              }
            >
              {loading ? (
                <div style={{ textAlign: 'center', padding: 60 }}>
                  <Spin size="large" />
                  <div style={{ marginTop: 16, color: '#8c8c8c' }}>Loading events...</div>
                </div>
              ) : events.length > 0 ? (
                <Table
                  dataSource={events}
                  columns={eventColumns}
                  rowKey="id"
                  pagination={{ pageSize: 10, showSizeChanger: true }}
                  style={{ borderRadius: 8 }}
                />
              ) : (
                <div style={{ textAlign: 'center', padding: 60, color: '#8c8c8c' }}>
                  <DatabaseOutlined style={{ fontSize: 48, marginBottom: 16 }} />
                  <div>No events captured yet</div>
                  <Button type="primary" onClick={() => {}} style={{ marginTop: 16, borderRadius: 8 }}>
                    Capture First Event
                  </Button>
                </div>
              )}
            </Card>
          )
        },
        {
          key: 'mappings',
          label: <span><FileTextOutlined /> Event Mappings</span>,
          children: (
            <Card style={{ borderRadius: 12 }}>
              <Alert
                message="Event Mappings"
                description="These mappings determine how events are categorized and routed to target systems."
                type="info"
                showIcon
                style={{ marginBottom: 16, borderRadius: 8 }}
              />
              {mappings.length > 0 ? (
                <Table
                  dataSource={mappings}
                  columns={mappingColumns}
                  rowKey="event_type"
                  pagination={false}
                  style={{ borderRadius: 8 }}
                />
              ) : (
                <div style={{ textAlign: 'center', padding: 60, color: '#8c8c8c' }}>
                  <FileTextOutlined style={{ fontSize: 48, marginBottom: 16 }} />
                  <div>No mappings configured</div>
                </div>
              )}
            </Card>
          )
        }
      ]} />

      {/* Event Status Modal */}
      <Modal
        title={<Space><SearchOutlined /> Event Status - #{selectedEventId}</Space>}
        open={statusModalVisible}
        onCancel={() => { setStatusModalVisible(false); setEventStatus(null); }}
        footer={[
          <Button key="close" onClick={() => setStatusModalVisible(false)}>Close</Button>,
          <Button key="refresh" icon={<ReloadOutlined />} onClick={() => checkEventStatus(selectedEventId)} loading={statusLoading}>
            Refresh
          </Button>
        ]}
        width={600}
      >
        {statusLoading ? (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <Spin size="large" />
            <div style={{ marginTop: 16, color: '#8c8c8c' }}>Fetching event status...</div>
          </div>
        ) : eventStatus?.error ? (
          <Alert type="error" message="Error" description={eventStatus.error} showIcon />
        ) : eventStatus ? (
          <div>
            <Row gutter={[16, 16]}>
              <Col span={12}>
                <Card size="small" style={{ borderRadius: 8 }}>
                  <div style={{ color: '#8c8c8c', fontSize: 12 }}>Status</div>
                  <div style={{ marginTop: 8 }}>{getStatusTag(eventStatus.status)}</div>
                </Card>
              </Col>
              <Col span={12}>
                <Card size="small" style={{ borderRadius: 8 }}>
                  <div style={{ color: '#8c8c8c', fontSize: 12 }}>Processing Stage</div>
                  <div style={{ marginTop: 8, fontWeight: 500 }}>{eventStatus.stage || 'N/A'}</div>
                </Card>
              </Col>
            </Row>

            {eventStatus.message && (
              <Alert
                message="Status Message"
                description={eventStatus.message}
                type="info"
                showIcon
                style={{ marginTop: 16, borderRadius: 8 }}
              />
            )}

            {eventStatus.history && eventStatus.history.length > 0 && (
              <Card size="small" title="Processing History" style={{ marginTop: 16, borderRadius: 8 }}>
                {eventStatus.history.map((item, index) => (
                  <div key={index} style={{ padding: '8px 0', borderBottom: index < eventStatus.history.length - 1 ? '1px solid #f0f0f0' : 'none' }}>
                    <Space>
                      {getStatusTag(item.status)}
                      <span style={{ color: '#8c8c8c', fontSize: 12 }}>{new Date(item.timestamp).toLocaleString()}</span>
                    </Space>
                    {item.message && <div style={{ marginTop: 4, color: '#595959' }}>{item.message}</div>}
                  </div>
                ))}
              </Card>
            )}

            {eventStatus.result && (
              <Card size="small" title="Processing Result" style={{ marginTop: 16, borderRadius: 8 }}>
                <pre style={{ background: '#f6f8fa', padding: 12, borderRadius: 6, overflow: 'auto', maxHeight: 200, fontSize: 12 }}>
                  {JSON.stringify(eventStatus.result, null, 2)}
                </pre>
              </Card>
            )}
          </div>
        ) : null}
      </Modal>
    </div>
  );
}
