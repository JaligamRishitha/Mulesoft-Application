import React, { useState } from 'react';
import { Card, Row, Col, Button, Input, Table, Tag, Space, Modal, Form, Tabs, message, Tooltip } from 'antd';
import { PlusOutlined, PlayCircleOutlined, CopyOutlined, DownloadOutlined, DeleteOutlined, EditOutlined, SaveOutlined, CodeOutlined } from '@ant-design/icons';

const { TextArea } = Input;

const defaultOpenAPISpec = `openapi: 3.0.3
info:
  title: Sample API
  description: Auto-generated API specification
  version: 1.0.0
servers:
  - url: http://localhost:8094
paths:
  /customers:
    get:
      summary: List all customers
      operationId: listCustomers
      responses:
        '200':
          description: Successful response
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/Customer'
    post:
      summary: Create a customer
      operationId: createCustomer
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/Customer'
      responses:
        '201':
          description: Customer created
  /customers/{id}:
    get:
      summary: Get customer by ID
      operationId: getCustomer
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: string
      responses:
        '200':
          description: Successful response
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Customer'
components:
  schemas:
    Customer:
      type: object
      properties:
        id:
          type: string
          example: "cust-001"
        name:
          type: string
          example: "John Doe"
        email:
          type: string
          format: email
          example: "john@example.com"
        phone:
          type: string
          example: "+1-555-0123"
        createdAt:
          type: string
          format: date-time`;

export default function APIDesigner() {
  const [specs, setSpecs] = useState([
    { id: 1, name: 'Customer API', version: '1.0.0', status: 'published', endpoints: 3, spec: defaultOpenAPISpec },
    { id: 2, name: 'Order API', version: '2.1.0', status: 'draft', endpoints: 5, spec: defaultOpenAPISpec.replace('Customer', 'Order').replace('customers', 'orders') },
    { id: 3, name: 'Inventory API', version: '1.2.0', status: 'published', endpoints: 4, spec: defaultOpenAPISpec.replace('Customer', 'Product').replace('customers', 'products') },
  ]);
  const [editorVisible, setEditorVisible] = useState(false);
  const [testVisible, setTestVisible] = useState(false);
  const [currentSpec, setCurrentSpec] = useState(null);
  const [specContent, setSpecContent] = useState('');
  const [testResult, setTestResult] = useState(null);
  const [testLoading, setTestLoading] = useState(false);
  const [form] = Form.useForm();

  const handleCreate = () => {
    setCurrentSpec(null);
    setSpecContent(defaultOpenAPISpec);
    form.resetFields();
    setEditorVisible(true);
  };

  const handleEdit = (record) => {
    setCurrentSpec(record);
    setSpecContent(record.spec);
    form.setFieldsValue({ name: record.name, version: record.version });
    setEditorVisible(true);
  };

  const handleSave = () => {
    form.validateFields().then(values => {
      const endpoints = (specContent.match(/^\s{2}\/\w+/gm) || []).length;
      if (currentSpec) {
        setSpecs(specs.map(s => s.id === currentSpec.id ? { ...s, ...values, spec: specContent, endpoints } : s));
        message.success('API spec updated');
      } else {
        setSpecs([...specs, { id: Date.now(), ...values, status: 'draft', endpoints, spec: specContent }]);
        message.success('API spec created');
      }
      setEditorVisible(false);
    });
  };

  const handleDelete = (id) => {
    setSpecs(specs.filter(s => s.id !== id));
    message.success('API spec deleted');
  };

  const handleTest = (record) => {
    setCurrentSpec(record);
    setTestResult(null);
    setTestVisible(true);
  };

  const runTest = (method, path) => {
    setTestLoading(true);
    setTimeout(() => {
      const mockResponses = {
        'GET /customers': { status: 200, data: [{ id: 'cust-001', name: 'John Doe', email: 'john@example.com' }, { id: 'cust-002', name: 'Jane Smith', email: 'jane@example.com' }] },
        'POST /customers': { status: 201, data: { id: 'cust-003', name: 'New Customer', email: 'new@example.com' } },
        'GET /customers/{id}': { status: 200, data: { id: 'cust-001', name: 'John Doe', email: 'john@example.com', phone: '+1-555-0123' } },
      };
      setTestResult(mockResponses[`${method} ${path}`] || { status: 200, data: { message: 'Mock response' } });
      setTestLoading(false);
    }, 500);
  };

  const copySpec = (spec) => {
    navigator.clipboard.writeText(spec);
    message.success('Copied to clipboard');
  };

  const downloadSpec = (record) => {
    const blob = new Blob([record.spec], { type: 'text/yaml' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${record.name.toLowerCase().replace(/\s+/g, '-')}-openapi.yaml`;
    a.click();
  };

  const columns = [
    { title: 'API Name', dataIndex: 'name', key: 'name', render: (t, r) => <a onClick={() => handleEdit(r)}>{t}</a> },
    { title: 'Version', dataIndex: 'version', key: 'version', width: 100 },
    { title: 'Endpoints', dataIndex: 'endpoints', key: 'endpoints', width: 100 },
    { title: 'Status', dataIndex: 'status', key: 'status', width: 100, render: s => <Tag color={s === 'published' ? 'green' : 'orange'}>{s}</Tag> },
    {
      title: 'Actions', key: 'actions', width: 200,
      render: (_, r) => (
        <Space size={4}>
          <Tooltip title="Edit">
            <Button size="small" icon={<EditOutlined />} onClick={() => handleEdit(r)} />
          </Tooltip>
          <Tooltip title="Test API">
            <Button size="small" icon={<PlayCircleOutlined />} onClick={() => handleTest(r)} style={{ color: '#52c41a' }} />
          </Tooltip>
          <Tooltip title="Copy Spec">
            <Button size="small" icon={<CopyOutlined />} onClick={() => copySpec(r.spec)} />
          </Tooltip>
          <Tooltip title="Download">
            <Button size="small" icon={<DownloadOutlined />} onClick={() => downloadSpec(r)} style={{ color: '#1890ff' }} />
          </Tooltip>
          <Tooltip title="Delete">
            <Button size="small" icon={<DeleteOutlined />} onClick={() => handleDelete(r.id)} danger />
          </Tooltip>
        </Space>
      )
    },
  ];

  const extractEndpoints = (spec) => {
    const paths = spec.match(/^\s{2}\/[\w{}/-]+:/gm) || [];
    const methods = ['get', 'post', 'put', 'delete', 'patch'];
    const endpoints = [];
    let currentPath = '';
    spec.split('\n').forEach(line => {
      const pathMatch = line.match(/^\s{2}(\/[\w{}/-]+):/);
      if (pathMatch) currentPath = pathMatch[1];
      methods.forEach(m => {
        if (line.match(new RegExp(`^\\s{4}${m}:`))) {
          endpoints.push({ method: m.toUpperCase(), path: currentPath });
        }
      });
    });
    return endpoints;
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>API Designer</h2>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>New API Spec</Button>
      </div>

      <Card>
        <Table dataSource={specs} columns={columns} rowKey="id" pagination={false} />
      </Card>

      {/* Editor Modal */}
      <Modal title={currentSpec ? 'Edit API Spec' : 'Create API Spec'} open={editorVisible} onCancel={() => setEditorVisible(false)} width={900} footer={[
        <Button key="cancel" onClick={() => setEditorVisible(false)}>Cancel</Button>,
        <Button key="save" type="primary" icon={<SaveOutlined />} onClick={handleSave}>Save</Button>
      ]}>
        <Form form={form} layout="vertical">
          <Row gutter={16}>
            <Col span={16}><Form.Item name="name" label="API Name" rules={[{ required: true }]}><Input placeholder="e.g. Customer API" /></Form.Item></Col>
            <Col span={8}><Form.Item name="version" label="Version" rules={[{ required: true }]}><Input placeholder="e.g. 1.0.0" /></Form.Item></Col>
          </Row>
        </Form>
        <div style={{ marginBottom: 8, display: 'flex', justifyContent: 'space-between' }}>
          <span><CodeOutlined /> OpenAPI Specification (YAML)</span>
          <Button size="small" icon={<CopyOutlined />} onClick={() => copySpec(specContent)}>Copy</Button>
        </div>
        <TextArea rows={18} value={specContent} onChange={e => setSpecContent(e.target.value)} style={{ fontFamily: 'monospace', fontSize: 12 }} />
      </Modal>

      {/* Test Modal */}
      <Modal title={`Test API: ${currentSpec?.name}`} open={testVisible} onCancel={() => setTestVisible(false)} width={700} footer={null}>
        <Tabs items={[
          {
            key: 'endpoints', label: 'Endpoints',
            children: (
              <Table
                dataSource={currentSpec ? extractEndpoints(currentSpec.spec) : []}
                rowKey={(r, i) => i}
                pagination={false}
                size="small"
                columns={[
                  { title: 'Method', dataIndex: 'method', width: 80, render: m => <Tag color={m === 'GET' ? 'blue' : m === 'POST' ? 'green' : m === 'DELETE' ? 'red' : 'orange'}>{m}</Tag> },
                  { title: 'Path', dataIndex: 'path' },
                  { title: 'Test', width: 80, render: (_, r) => <Button size="small" icon={<PlayCircleOutlined />} loading={testLoading} onClick={() => runTest(r.method, r.path)}>Run</Button> }
                ]}
              />
            )
          },
          {
            key: 'response', label: 'Response',
            children: testResult ? (
              <div>
                <Tag color={testResult.status < 300 ? 'green' : 'red'}>Status: {testResult.status}</Tag>
                <pre style={{ background: '#f5f5f5', padding: 12, borderRadius: 4, marginTop: 12, maxHeight: 300, overflow: 'auto' }}>
                  {JSON.stringify(testResult.data, null, 2)}
                </pre>
              </div>
            ) : <div style={{ color: '#999', padding: 20, textAlign: 'center' }}>Run a test to see the response</div>
          }
        ]} />
      </Modal>
    </div>
  );
}
