import React, { useState, useEffect } from 'react';
import { Card, Select, Button, Space, Tag, Alert, Spin, Tabs, Table, Input, Form, message } from 'antd';
import { ReloadOutlined, SendOutlined, CopyOutlined } from '@ant-design/icons';

const { Option } = Select;
const { TextArea } = Input;

// Mock OpenAPI specs for different services
const apiSpecs = {
  platform: {
    name: 'Platform Backend API',
    baseUrl: 'http://localhost:8080',
    endpoints: [
      { method: 'POST', path: '/api/auth/register', summary: 'Register new user', body: { email: 'user@example.com', password: 'password123', full_name: 'John Doe' } },
      { method: 'POST', path: '/api/auth/login', summary: 'User login', body: { username: 'user@example.com', password: 'password123' } },
      { method: 'GET', path: '/api/integrations', summary: 'List all integrations', auth: true },
      { method: 'POST', path: '/api/integrations', summary: 'Create integration', auth: true, body: { name: 'New Integration', description: 'Description', flow_config: 'routes: []' } },
      { method: 'GET', path: '/api/dashboard/stats', summary: 'Get dashboard statistics', auth: true },
      { method: 'GET', path: '/api/apis/endpoints', summary: 'List API endpoints', auth: true },
    ]
  },
  erp: {
    name: 'ERP Mock Service',
    baseUrl: 'http://localhost:8091',
    endpoints: [
      { method: 'GET', path: '/', summary: 'Service info' },
      { method: 'GET', path: '/health', summary: 'Health check' },
      { method: 'GET', path: '/api/products', summary: 'List products' },
      { method: 'GET', path: '/api/orders', summary: 'List orders' },
      { method: 'POST', path: '/api/orders', summary: 'Create order', body: { product_id: 'PROD-001', quantity: 5, customer_id: 'CUST-001' } },
    ]
  },
  crm: {
    name: 'CRM Mock Service',
    baseUrl: 'http://localhost:8092',
    endpoints: [
      { method: 'GET', path: '/', summary: 'Service info' },
      { method: 'GET', path: '/health', summary: 'Health check' },
      { method: 'GET', path: '/api/customers', summary: 'List customers' },
      { method: 'GET', path: '/api/contacts', summary: 'List contacts' },
      { method: 'POST', path: '/api/customers', summary: 'Create customer', body: { name: 'New Customer', email: 'customer@example.com', company: 'Acme Inc' } },
    ]
  },
  itsm: {
    name: 'ITSM Mock Service',
    baseUrl: 'http://localhost:8093',
    endpoints: [
      { method: 'GET', path: '/', summary: 'Service info' },
      { method: 'GET', path: '/health', summary: 'Health check' },
      { method: 'GET', path: '/api/incidents', summary: 'List incidents' },
      { method: 'POST', path: '/api/incidents', summary: 'Create incident', body: { title: 'Server Down', priority: 'high', description: 'Production server not responding' } },
    ]
  }
};

export default function SwaggerUI() {
  const [selectedApi, setSelectedApi] = useState('platform');
  const [selectedEndpoint, setSelectedEndpoint] = useState(null);
  const [response, setResponse] = useState(null);
  const [loading, setLoading] = useState(false);
  const [requestBody, setRequestBody] = useState('');

  const currentApi = apiSpecs[selectedApi];

  const handleEndpointSelect = (endpoint) => {
    setSelectedEndpoint(endpoint);
    setRequestBody(endpoint.body ? JSON.stringify(endpoint.body, null, 2) : '');
    setResponse(null);
  };

  const executeRequest = async () => {
    if (!selectedEndpoint) return;
    
    setLoading(true);
    const startTime = Date.now();
    
    try {
      const options = {
        method: selectedEndpoint.method,
        headers: { 'Content-Type': 'application/json' },
      };
      
      if (selectedEndpoint.auth) {
        const token = localStorage.getItem('token');
        if (token) options.headers['Authorization'] = `Bearer ${token}`;
      }
      
      if (selectedEndpoint.body && ['POST', 'PUT', 'PATCH'].includes(selectedEndpoint.method)) {
        options.body = requestBody;
      }
      
      const res = await fetch(`${currentApi.baseUrl}${selectedEndpoint.path}`, options);
      const duration = Date.now() - startTime;
      
      let data;
      const contentType = res.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        data = await res.json();
      } else {
        data = await res.text();
      }
      
      setResponse({ status: res.status, statusText: res.statusText, duration, data, headers: Object.fromEntries(res.headers.entries()) });
    } catch (error) {
      setResponse({ status: 0, statusText: 'Network Error', duration: Date.now() - startTime, data: { error: error.message } });
    }
    
    setLoading(false);
  };

  const copyResponse = () => {
    if (response) {
      navigator.clipboard.writeText(JSON.stringify(response.data, null, 2));
      message.success('Response copied');
    }
  };

  const getMethodColor = (method) => {
    const colors = { GET: 'blue', POST: 'green', PUT: 'orange', DELETE: 'red', PATCH: 'purple' };
    return colors[method] || 'default';
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>API Explorer</h2>
        <Space>
          <Select value={selectedApi} onChange={setSelectedApi} style={{ width: 200 }}>
            {Object.entries(apiSpecs).map(([key, api]) => (
              <Option key={key} value={key}>{api.name}</Option>
            ))}
          </Select>
        </Space>
      </div>

      <Alert message={`Base URL: ${currentApi.baseUrl}`} type="info" showIcon style={{ marginBottom: 16 }} />

      <div style={{ display: 'flex', gap: 16 }}>
        {/* Endpoints List */}
        <Card title="Endpoints" style={{ width: 350 }} size="small">
          {currentApi.endpoints.map((ep, i) => (
            <div
              key={i}
              onClick={() => handleEndpointSelect(ep)}
              style={{
                padding: '8px 12px',
                marginBottom: 8,
                borderRadius: 4,
                cursor: 'pointer',
                background: selectedEndpoint === ep ? '#e6f7ff' : '#fafafa',
                border: selectedEndpoint === ep ? '1px solid #1890ff' : '1px solid #f0f0f0'
              }}
            >
              <Tag color={getMethodColor(ep.method)} style={{ marginRight: 8 }}>{ep.method}</Tag>
              <span style={{ fontFamily: 'monospace', fontSize: 12 }}>{ep.path}</span>
              {ep.auth && <Tag color="gold" style={{ marginLeft: 8, fontSize: 10 }}>Auth</Tag>}
              <div style={{ fontSize: 11, color: '#666', marginTop: 4 }}>{ep.summary}</div>
            </div>
          ))}
        </Card>

        {/* Request/Response Panel */}
        <Card title="Try it out" style={{ flex: 1 }} size="small">
          {selectedEndpoint ? (
            <>
              <div style={{ marginBottom: 16 }}>
                <Tag color={getMethodColor(selectedEndpoint.method)}>{selectedEndpoint.method}</Tag>
                <span style={{ fontFamily: 'monospace', marginLeft: 8 }}>{currentApi.baseUrl}{selectedEndpoint.path}</span>
              </div>

              {selectedEndpoint.body && (
                <div style={{ marginBottom: 16 }}>
                  <div style={{ marginBottom: 8, fontWeight: 500 }}>Request Body</div>
                  <TextArea
                    rows={6}
                    value={requestBody}
                    onChange={e => setRequestBody(e.target.value)}
                    style={{ fontFamily: 'monospace', fontSize: 12 }}
                  />
                </div>
              )}

              <Button type="primary" icon={<SendOutlined />} onClick={executeRequest} loading={loading}>
                Execute
              </Button>

              {response && (
                <div style={{ marginTop: 16 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                    <Space>
                      <Tag color={response.status >= 200 && response.status < 300 ? 'green' : response.status >= 400 ? 'red' : 'orange'}>
                        {response.status} {response.statusText}
                      </Tag>
                      <span style={{ fontSize: 12, color: '#666' }}>{response.duration}ms</span>
                    </Space>
                    <Button size="small" icon={<CopyOutlined />} onClick={copyResponse}>Copy</Button>
                  </div>
                  <pre style={{ background: '#f5f5f5', padding: 12, borderRadius: 4, maxHeight: 300, overflow: 'auto', fontSize: 12 }}>
                    {typeof response.data === 'string' ? response.data : JSON.stringify(response.data, null, 2)}
                  </pre>
                </div>
              )}
            </>
          ) : (
            <div style={{ color: '#999', textAlign: 'center', padding: 40 }}>
              Select an endpoint to test
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
