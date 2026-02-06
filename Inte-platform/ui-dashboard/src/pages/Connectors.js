import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Button, Table, Tag, Space, Modal, Form, Input, Select, message, Spin, Tooltip } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, PlayCircleOutlined, CheckCircleOutlined, CloseCircleOutlined, ReloadOutlined } from '@ant-design/icons';
import { backendApi as api } from '../api';

const { Option } = Select;
const { TextArea } = Input;

// Real SVG Logos for Connectors
const ConnectorLogos = {
  sap: () => (
    <img src="/images/sap.png" alt="SAP" style={{ width: 40, height: 40, objectFit: 'contain' }} />
  ),
  salesforce: () => (
    <svg width="40" height="40" viewBox="0 0 100 100" fill="none">
      <rect width="100" height="100" rx="8" fill="#00A1E0"/>
      <path d="M42 30C38 30 35 33 35 37C32 37 29 40 29 44C29 48 32 51 36 51H64C68 51 71 48 71 44C71 40 68 37 64 37C64 33 61 30 57 30C54 30 51 32 50 35C48 32 45 30 42 30Z" fill="white"/>
      <text x="50" y="72" textAnchor="middle" fill="white" fontSize="10" fontWeight="bold">Salesforce</text>
    </svg>
  ),
  servicenow: () => (
    <svg width="40" height="40" viewBox="0 0 100 100" fill="none">
      <rect width="100" height="100" rx="8" fill="#81B5A1"/>
      <circle cx="50" cy="50" r="25" fill="white"/>
      <circle cx="50" cy="50" r="15" fill="#81B5A1"/>
      <circle cx="50" cy="50" r="8" fill="white"/>
      <text x="50" y="88" textAnchor="middle" fill="white" fontSize="9" fontWeight="bold">ServiceNow</text>
    </svg>
  ),
  database: () => (
    <svg width="40" height="40" viewBox="0 0 100 100" fill="none">
      <rect width="100" height="100" rx="8" fill="#336791"/>
      <ellipse cx="50" cy="30" rx="25" ry="10" fill="white"/>
      <path d="M25 30V70C25 75.5 36 80 50 80C64 80 75 75.5 75 70V30" stroke="white" strokeWidth="4" fill="none"/>
      <path d="M25 45C25 50.5 36 55 50 55C64 55 75 50.5 75 45" stroke="white" strokeWidth="4"/>
      <path d="M25 57C25 62.5 36 67 50 67C64 67 75 62.5 75 57" stroke="white" strokeWidth="4"/>
    </svg>
  ),
  http: () => (
    <svg width="40" height="40" viewBox="0 0 100 100" fill="none">
      <rect width="100" height="100" rx="8" fill="#4CAF50"/>
      <circle cx="50" cy="50" r="25" stroke="white" strokeWidth="4" fill="none"/>
      <ellipse cx="50" cy="50" rx="10" ry="25" stroke="white" strokeWidth="3" fill="none"/>
      <line x1="25" y1="50" x2="75" y2="50" stroke="white" strokeWidth="3"/>
      <line x1="30" y1="38" x2="70" y2="38" stroke="white" strokeWidth="2"/>
      <line x1="30" y1="62" x2="70" y2="62" stroke="white" strokeWidth="2"/>
    </svg>
  ),
  kafka: () => (
    <svg width="40" height="40" viewBox="0 0 100 100" fill="none">
      <rect width="100" height="100" rx="8" fill="#231F20"/>
      <circle cx="50" cy="50" r="8" fill="white"/>
      <circle cx="50" cy="25" r="6" fill="white"/>
      <circle cx="72" cy="38" r="6" fill="white"/>
      <circle cx="72" cy="62" r="6" fill="white"/>
      <circle cx="50" cy="75" r="6" fill="white"/>
      <circle cx="28" cy="62" r="6" fill="white"/>
      <circle cx="28" cy="38" r="6" fill="white"/>
      <line x1="50" y1="42" x2="50" y2="31" stroke="white" strokeWidth="2"/>
      <line x1="56" y1="45" x2="66" y2="40" stroke="white" strokeWidth="2"/>
      <line x1="56" y1="55" x2="66" y2="60" stroke="white" strokeWidth="2"/>
      <line x1="50" y1="58" x2="50" y2="69" stroke="white" strokeWidth="2"/>
      <line x1="44" y1="55" x2="34" y2="60" stroke="white" strokeWidth="2"/>
      <line x1="44" y1="45" x2="34" y2="40" stroke="white" strokeWidth="2"/>
    </svg>
  ),
  ftp: () => (
    <svg width="40" height="40" viewBox="0 0 100 100" fill="none">
      <rect width="100" height="100" rx="8" fill="#607D8B"/>
      <rect x="25" y="35" width="50" height="35" rx="3" fill="white"/>
      <rect x="30" y="40" width="15" height="12" fill="#607D8B"/>
      <circle cx="50" cy="60" r="3" fill="#607D8B"/>
      <path d="M40 25L50 15L60 25" stroke="white" strokeWidth="3" strokeLinecap="round"/>
      <line x1="50" y1="15" x2="50" y2="35" stroke="white" strokeWidth="3"/>
    </svg>
  ),
  email: () => (
    <svg width="40" height="40" viewBox="0 0 100 100" fill="none">
      <rect width="100" height="100" rx="8" fill="#EA4335"/>
      <rect x="20" y="30" width="60" height="40" rx="3" fill="white"/>
      <path d="M20 33L50 55L80 33" stroke="#EA4335" strokeWidth="3" fill="none"/>
    </svg>
  ),
  aws_s3: () => (
    <svg width="40" height="40" viewBox="0 0 100 100" fill="none">
      <rect width="100" height="100" rx="8" fill="#FF9900"/>
      <path d="M50 20L75 35V65L50 80L25 65V35L50 20Z" fill="white"/>
      <path d="M50 20L75 35L50 50L25 35L50 20Z" fill="#FF9900" fillOpacity="0.3"/>
      <path d="M50 50V80L75 65V35L50 50Z" fill="#FF9900" fillOpacity="0.5"/>
      <text x="50" y="55" textAnchor="middle" fill="#FF9900" fontSize="14" fontWeight="bold">S3</text>
    </svg>
  ),
  azure_blob: () => (
    <svg width="40" height="40" viewBox="0 0 100 100" fill="none">
      <rect width="100" height="100" rx="8" fill="#0078D4"/>
      <path d="M30 70V40L50 25L70 40V70L50 85L30 70Z" fill="white"/>
      <path d="M50 25L70 40L50 55L30 40L50 25Z" fill="#0078D4" fillOpacity="0.3"/>
      <path d="M50 55V85L70 70V40L50 55Z" fill="#0078D4" fillOpacity="0.5"/>
    </svg>
  ),
  soap: () => (
    <svg width="40" height="40" viewBox="0 0 100 100" fill="none">
      <rect width="100" height="100" rx="8" fill="#FF6B35"/>
      <rect x="25" y="25" width="50" height="50" rx="3" fill="white"/>
      <text x="50" y="45" textAnchor="middle" fill="#FF6B35" fontSize="10" fontWeight="bold">&lt;/&gt;</text>
      <text x="50" y="62" textAnchor="middle" fill="#FF6B35" fontSize="8">SOAP</text>
    </svg>
  )
};

// Get logo component or fallback
const getConnectorLogo = (type) => {
  const Logo = ConnectorLogos[type];
  return Logo ? <Logo /> : <div style={{ width: 40, height: 40, background: '#e8e8e8', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 20 }}>🔌</div>;
};

export default function Connectors() {
  const [connectors, setConnectors] = useState([]);
  const [connectorTypes, setConnectorTypes] = useState({});
  const [loading, setLoading] = useState(true);
  const [modalVisible, setModalVisible] = useState(false);
  const [typeModalVisible, setTypeModalVisible] = useState(false);
  const [selectedType, setSelectedType] = useState(null);
  const [editingConnector, setEditingConnector] = useState(null);
  const [testingId, setTestingId] = useState(null);
  const [form] = Form.useForm();

  useEffect(() => {
    fetchConnectors();
    fetchConnectorTypes();
  }, []);

  const fetchConnectors = async () => {
    try {
      const { data } = await api.get('/connectors');
      setConnectors(data);
    } catch (err) {
      console.error('Failed to fetch connectors:', err.message);
    }
    setLoading(false);
  };

  // MCP Server configurations
  const mcpServers = {
    salesforce: { url: 'http://149.102.158.71:8090', name: 'salesforce-crm', description: 'Salesforce CRM MCP Server' },
    sap: { url: 'http://149.102.158.71:8092', name: 'sap-erp', description: 'SAP ERP MCP Server' },
    servicenow: { url: 'http://149.102.158.71:8093', name: 'servicenow', description: 'ServiceNow ITSM MCP Server' },
    database: { url: 'http://149.102.158.71:8091', name: 'mulesoft-api', description: 'MuleSoft HTTP REST API' },
    http: { url: 'http://149.102.158.71:8091', name: 'mulesoft-api', description: 'MuleSoft HTTP REST API' }
  };

  const defaultConfigSchema = {
    server_url: { type: 'string', label: 'Direct Server URL', required: false, placeholder: 'http://your-server-ip:port (optional - for direct connection)' },
    mcp_server_url: {
      type: 'select',
      label: 'MCP Server',
      required: false,
      options: [
        'http://149.102.158.71:8090 (Salesforce CRM)',
        'http://149.102.158.71:8091 (MuleSoft API)',
        'http://149.102.158.71:8092 (SAP ERP)',
        'http://149.102.158.71:8093 (ServiceNow)',
        'http://149.102.158.71:8094 (MuleSoft Integration)'
      ],
      placeholder: 'Select MCP Server'
    },
    mcp_server_name: { type: 'string', label: 'MCP Server Name', required: false, placeholder: 'Auto-filled based on selection' }
  };

  const fetchConnectorTypes = async () => {
    try {
      const { data } = await api.get('/connectors/types');
      // Convert array to object keyed by type and add default config_schema
      const typesObj = Array.isArray(data)
        ? data.reduce((acc, item) => ({
            ...acc,
            [item.type]: { ...item, config_schema: item.config_schema || defaultConfigSchema }
          }), {})
        : data;
      setConnectorTypes(typesObj);
    } catch (err) {
      console.error('Failed to fetch connector types:', err.message);
    }
  };

  const handleSelectType = (type) => {
    setSelectedType(type);
    setTypeModalVisible(false);
    setEditingConnector(null);
    form.resetFields();
    setModalVisible(true);
  };

  // MCP URL to display format mapping
  const mcpUrlToDisplay = {
    'http://149.102.158.71:8090': 'http://149.102.158.71:8090 (Salesforce CRM)',
    'http://149.102.158.71:8091': 'http://149.102.158.71:8091 (MuleSoft API)',
    'http://149.102.158.71:8092': 'http://149.102.158.71:8092 (SAP ERP)',
    'http://149.102.158.71:8093': 'http://149.102.158.71:8093 (ServiceNow)',
    'http://149.102.158.71:8094': 'http://149.102.158.71:8094 (MuleSoft Integration)'
  };

  const handleEdit = (record) => {
    setSelectedType(record.connector_type || record.type);
    setEditingConnector(record);
    const config = { ...record.connection_config, ...record.config };
    // Convert MCP URL to display format for dropdown
    if (config.mcp_server_url && mcpUrlToDisplay[config.mcp_server_url]) {
      config.mcp_server_url = mcpUrlToDisplay[config.mcp_server_url];
    }
    form.setFieldsValue({ name: record.connector_name || record.name, description: record.description, ...config });
    setModalVisible(true);
  };

  // MCP server name mapping
  const mcpServerNames = {
    'http://149.102.158.71:8090': 'salesforce-crm',
    'http://149.102.158.71:8091': 'mulesoft-api',
    'http://149.102.158.71:8092': 'sap-erp',
    'http://149.102.158.71:8093': 'servicenow',
    'http://149.102.158.71:8094': 'mulesoft-integration'
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      const { name, description, ...connection_config } = values;

      // Extract just the URL from MCP server selection (remove description in parentheses)
      if (connection_config.mcp_server_url) {
        const urlMatch = connection_config.mcp_server_url.match(/^(http[^\s]+)/);
        if (urlMatch) {
          connection_config.mcp_server_url = urlMatch[1];
          // Auto-set mcp_server_name if not provided
          if (!connection_config.mcp_server_name) {
            connection_config.mcp_server_name = mcpServerNames[connection_config.mcp_server_url] || '';
          }
        }
      }

      const payload = {
        connector_name: name,
        connector_type: selectedType,
        connection_config
      };

      if (editingConnector) {
        await api.put(`/connectors/${editingConnector.id}`, payload);
        message.success('Connector updated');
      } else {
        await api.post('/connectors', payload);
        message.success('Connector created');
      }
      setModalVisible(false);
      fetchConnectors();
    } catch (err) {
      if (err.errorFields) return;
      console.error('Connector save error:', err.response?.data);
      message.error(`Failed to save connector: ${err.response?.data?.detail || err.message}`);
    }
  };

  const handleDelete = async (id) => {
    try {
      await api.delete(`/connectors/${id}`);
      message.success('Connector deleted');
      fetchConnectors();
    } catch (err) {
      const errorMsg = err.response?.data?.detail || err.message || 'Failed to delete';
      message.error(`Delete failed: ${errorMsg}`);
    }
  };

  const handleTest = async (id) => {
    setTestingId(id);
    try {
      const { data } = await api.post(`/connectors/${id}/test`);
      if (data.success) {
        message.success(`Connection successful: ${data.message}`);
      } else {
        message.error(`Connection failed: ${data.message}`);
      }
      fetchConnectors();
    } catch (err) {
      const errorMsg = err.response?.data?.detail || err.message || 'Test failed';
      message.error(`Test failed: ${errorMsg}`);
    }
    setTestingId(null);
  };

  const renderConfigField = (key, schema) => {
    const rules = schema.required ? [{ required: true, message: `${schema.label} is required` }] : [];
    
    if (schema.type === 'password') {
      return <Form.Item key={key} name={key} label={schema.label} rules={rules}><Input.Password placeholder={schema.placeholder} /></Form.Item>;
    }
    if (schema.type === 'select') {
      return (
        <Form.Item key={key} name={key} label={schema.label} rules={rules} initialValue={schema.default}>
          <Select placeholder={`Select ${schema.label}`}>
            {schema.options?.map(opt => <Option key={opt} value={opt}>{opt}</Option>)}
          </Select>
        </Form.Item>
      );
    }
    if (schema.type === 'number') {
      return <Form.Item key={key} name={key} label={schema.label} rules={rules} initialValue={schema.default}><Input type="number" placeholder={schema.placeholder} /></Form.Item>;
    }
    if (schema.type === 'textarea') {
      return <Form.Item key={key} name={key} label={schema.label} rules={rules}><TextArea rows={4} placeholder={schema.placeholder} /></Form.Item>;
    }
    return <Form.Item key={key} name={key} label={schema.label} rules={rules} initialValue={schema.default}><Input placeholder={schema.placeholder} /></Form.Item>;
  };

  const columns = [
    {
      title: 'Connector', dataIndex: 'name', key: 'name',
      render: (name, r) => (
        <Space>
          {getConnectorLogo(r.connector_type || r.type)}
          <div>
            <div style={{ fontWeight: 500 }}>{name}</div>
            <div style={{ fontSize: 12, color: '#666' }}>{connectorTypes[r.connector_type || r.type]?.name || r.connector_type || r.type}</div>
          </div>
        </Space>
      )
    },
    { 
      title: 'Status', dataIndex: 'status', key: 'status', width: 100,
      render: s => (
        <Tag color={s === 'active' ? 'green' : s === 'error' ? 'red' : 'default'} icon={s === 'active' ? <CheckCircleOutlined /> : s === 'error' ? <CloseCircleOutlined /> : null}>
          {s}
        </Tag>
      )
    },
    { 
      title: 'Last Tested', dataIndex: 'last_tested', key: 'last_tested', width: 150,
      render: t => t ? new Date(t).toLocaleString() : 'Never'
    },
    {
      title: 'Actions', key: 'actions', width: 180,
      render: (_, r) => (
        <Space size={4}>
          <Tooltip title="Test Connection">
            <Button size="small" icon={<PlayCircleOutlined />} loading={testingId === r.id} onClick={() => handleTest(r.id)} style={{ color: '#52c41a' }} />
          </Tooltip>
          <Tooltip title="Edit">
            <Button size="small" icon={<EditOutlined />} onClick={() => handleEdit(r)} />
          </Tooltip>
          <Tooltip title="Delete">
            <Button size="small" danger icon={<DeleteOutlined />} onClick={() => handleDelete(r.id)} />
          </Tooltip>
        </Space>
      )
    }
  ];

  if (loading) return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />;

  return (
    <div className="animate-fade-in">
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 24 }}>
        <div>
          <h2 style={{ marginBottom: 4 }}>Connectors</h2>
          <p style={{ color: '#666', margin: 0 }}>Manage connections to external systems and services</p>
        </div>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={fetchConnectors}>Refresh</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setTypeModalVisible(true)}>New Connector</Button>
        </Space>
      </div>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card size="small" className="stat-card" style={{ borderTop: '4px solid #00a1e0' }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 28, fontWeight: 700, color: '#1a1a2e' }}>{connectors.length}</div>
              <div style={{ color: '#666', fontSize: 13 }}>Total Connectors</div>
            </div>
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small" className="stat-card" style={{ borderTop: '4px solid #52c41a' }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 28, fontWeight: 700, color: '#52c41a' }}>{connectors.filter(c => c.status === 'active').length}</div>
              <div style={{ color: '#666', fontSize: 13 }}>Active</div>
            </div>
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small" className="stat-card" style={{ borderTop: '4px solid #faad14' }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 28, fontWeight: 700, color: '#faad14' }}>{connectors.filter(c => c.status === 'inactive').length}</div>
              <div style={{ color: '#666', fontSize: 13 }}>Inactive</div>
            </div>
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small" className="stat-card" style={{ borderTop: '4px solid #ff4d4f' }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 28, fontWeight: 700, color: '#ff4d4f' }}>{connectors.filter(c => c.status === 'error').length}</div>
              <div style={{ color: '#666', fontSize: 13 }}>Error</div>
            </div>
          </Card>
        </Col>
      </Row>

      <Card>
        <Table dataSource={connectors} columns={columns} rowKey="id" pagination={false} />
      </Card>

      {/* Select Connector Type Modal */}
      <Modal title="Select Connector Type" open={typeModalVisible} onCancel={() => setTypeModalVisible(false)} footer={null} width={900}>
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          {Object.entries(connectorTypes).map(([key, type]) => (
            <Col span={8} key={key}>
              <Card 
                hoverable 
                size="small" 
                onClick={() => handleSelectType(key)} 
                className="connector-card"
                style={{ cursor: 'pointer', border: '1px solid #e8e8e8' }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  {getConnectorLogo(key)}
                  <div>
                    <div style={{ fontWeight: 600, fontSize: 14, color: '#1a1a2e' }}>{type.name}</div>
                    <div style={{ fontSize: 11, color: '#666', marginTop: 2 }}>{type.description}</div>
                  </div>
                </div>
              </Card>
            </Col>
          ))}
        </Row>
      </Modal>

      {/* Configure Connector Modal */}
      <Modal 
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            {selectedType && getConnectorLogo(selectedType)}
            <span>{editingConnector ? 'Edit' : 'New'} {connectorTypes[selectedType]?.name || ''} Connector</span>
          </div>
        }
        open={modalVisible} 
        onCancel={() => setModalVisible(false)} 
        onOk={handleSave}
        width={500}
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="name" label="Connector Name" rules={[{ required: true }]}>
            <Input placeholder="e.g. SAP Production" />
          </Form.Item>
          <Form.Item name="description" label="Description">
            <Input placeholder="Optional description" />
          </Form.Item>
          
          {selectedType && connectorTypes[selectedType]?.config_schema && (
            <div style={{ borderTop: '1px solid #f0f0f0', paddingTop: 16, marginTop: 16 }}>
              <div style={{ marginBottom: 12, fontWeight: 500 }}>Connection Settings</div>
              {Object.entries(connectorTypes[selectedType].config_schema).map(([key, schema]) => renderConfigField(key, schema))}
            </div>
          )}
        </Form>
      </Modal>
    </div>
  );
}
