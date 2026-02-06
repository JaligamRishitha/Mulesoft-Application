import React, { useState } from 'react';
import { Card, Select, Button, Space, Tag, Alert, Input, message } from 'antd';
import { SendOutlined, CopyOutlined } from '@ant-design/icons';
import { backendApi as api } from '../api';

const { Option } = Select;
const { TextArea } = Input;

// API specs for different services - calls go through backend proxy
const apiSpecs = {
  platform: {
    name: 'Platform Backend API',
    baseUrl: '/api',
    direct: true,
    endpoints: [
      { method: 'GET', path: '/dashboard/stats', summary: 'Get dashboard statistics', auth: true },
      { method: 'GET', path: '/integrations', summary: 'List all integrations', auth: true },
      { method: 'GET', path: '/apis/endpoints', summary: 'List API endpoints', auth: true },
      { method: 'GET', path: '/connectors', summary: 'List connectors', auth: true },
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
    ]
  },
  itsm: {
    name: 'ITSM Mock Service',
    baseUrl: 'http://localhost:8093',
    endpoints: [
      { method: 'GET', path: '/', summary: 'Service info' },
      { method: 'GET', path: '/health', summary: 'Health check' },
      { method: 'GET', path: '/api/incidents', summary: 'List incidents' },
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
      let res;
      const duration = () => Date.now() - startTime;
      
      if (currentApi.direct) {
        // Use axios api instance for platform backend
        if (selectedEndpoint.method === 'GET') {
          res = await api.get(selectedEndpoint.path);
        } else if (selectedEndpoint.method === 'POST') {
          res = await api.post(selectedEndpoint.path, requestBody ? JSON.parse(requestBody) : {});
        }
        setResponse({ 
          status: res.status, 
          statusText: 'OK', 
          duration: duration(), 
          data: res.data 
        });
      } else {
        // For external services, call through backend proxy
        const proxyRes = await api.post('/proxy/request', {
          url: `${currentApi.baseUrl}${selectedEndpoint.path}`,
          method: selectedEndpoint.method,
          body: selectedEndpoint.body && requestBody ? JSON.parse(requestBody) : null
        });
        setResponse({ 
          status: proxyRes.data.status || 200, 
          statusText: proxyRes.data.statusText || 'OK', 
          duration: duration(), 
          data: proxyRes.data.data || proxyRes.data 
        });
      }
    } catch (error) {
      const duration = Date.now() - startTime;
      if (error.response) {
        setResponse({ 
          status: error.response.status, 
          statusText: error.response.statusText || 'Error', 
          duration, 
          data: error.response.data 
        });
      } else {
        setResponse({ 
          status: 0, 
          statusText: 'Network Error', 
          duration, 
          data: { error: error.message, hint: 'Make sure the service is running' } 
        });
      }
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
          <Select value={selectedApi} onChange={(v) => { setSelectedApi(v); setSelectedEndpoint(null); setResponse(null); }} style={{ width: 200 }}>
            {Object.entries(apiSpecs).map(([key, apiDef]) => (
              <Option key={key} value={key}>{apiDef.name}</Option>
            ))}
          </Select>
        </Space>
      </div>

      <Alert 
        message={currentApi.direct ? 'Platform API (Direct)' : `External Service: ${currentApi.baseUrl}`} 
        type="info" 
        showIcon 
        style={{ marginBottom: 16 }} 
      />

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
                <span style={{ fontFamily: 'monospace', marginLeft: 8 }}>
                  {currentApi.direct ? selectedEndpoint.path : `${currentApi.baseUrl}${selectedEndpoint.path}`}
                </span>
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
