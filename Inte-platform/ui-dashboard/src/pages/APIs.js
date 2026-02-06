import React, { useState, useEffect } from 'react';
import { Table, Button, Modal, Form, Input, InputNumber, Switch, Tabs, Tag, Space, message, Popconfirm } from 'antd';
import { PlusOutlined, DeleteOutlined, KeyOutlined } from '@ant-design/icons';
import { backendApi as api } from '../api';

export default function APIs() {
  const [endpoints, setEndpoints] = useState([]);
  const [keys, setKeys] = useState([]);
  const [loading, setLoading] = useState(true);
  const [endpointModal, setEndpointModal] = useState(false);
  const [keyModal, setKeyModal] = useState(false);
  const [form] = Form.useForm();
  const [keyForm] = Form.useForm();

  const fetch = () => {
    setLoading(true);
    Promise.all([api.get('/apis/endpoints'), api.get('/apis/keys')])
      .then(([e, k]) => { setEndpoints(e.data); setKeys(k.data); })
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetch(); }, []);

  const handleCreateEndpoint = async (values) => {
    values.ipWhitelist = values.ipWhitelist ? values.ipWhitelist.split(',').map(s => s.trim()) : [];
    await api.post('/apis/endpoints', values);
    message.success('Created');
    setEndpointModal(false);
    form.resetFields();
    fetch();
  };

  const handleDeleteEndpoint = async (id) => { await api.delete(`/apis/endpoints/${id}`); message.success('Deleted'); fetch(); };
  const handleCreateKey = async (values) => { await api.post('/apis/keys', values); message.success('Created'); setKeyModal(false); keyForm.resetFields(); fetch(); };
  const handleRevokeKey = async (id) => { await api.delete(`/apis/keys/${id}`); message.success('Revoked'); fetch(); };

  const endpointCols = [
    { title: 'Name', dataIndex: 'name' },
    { title: 'Path', dataIndex: 'path' },
    { title: 'Method', dataIndex: 'method', render: (m) => <Tag>{m}</Tag> },
    { title: 'Rate Limit', dataIndex: 'rateLimit', render: (r) => `${r} req/min` },
    { title: 'Auth', dataIndex: 'requiresAuth', render: (a) => <Tag color={a ? 'green' : 'orange'}>{a ? 'Yes' : 'No'}</Tag> },
    { title: 'Actions', render: (_, r) => <Popconfirm title="Delete?" onConfirm={() => handleDeleteEndpoint(r.id)}><Button danger icon={<DeleteOutlined />}>Delete</Button></Popconfirm> }
  ];

  const keyCols = [
    { title: 'Name', dataIndex: 'name' },
    { title: 'Key', dataIndex: 'key', render: (k) => <code>{k.substring(0, 16)}...</code> },
    { title: 'Status', dataIndex: 'isActive', render: (a) => <Tag color={a ? 'green' : 'red'}>{a ? 'Active' : 'Revoked'}</Tag> },
    { title: 'Actions', render: (_, r) => r.isActive && <Popconfirm title="Revoke?" onConfirm={() => handleRevokeKey(r.id)}><Button danger icon={<DeleteOutlined />}>Revoke</Button></Popconfirm> }
  ];

  return (
    <div>
      <h2>API Manager</h2>
      <Tabs items={[
        { key: 'endpoints', label: 'Endpoints', children: (
          <>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setEndpointModal(true)} style={{ marginBottom: 16 }}>New Endpoint</Button>
            <Table dataSource={endpoints} columns={endpointCols} rowKey="id" loading={loading} />
          </>
        )},
        { key: 'keys', label: 'API Keys', children: (
          <>
            <Button type="primary" icon={<KeyOutlined />} onClick={() => setKeyModal(true)} style={{ marginBottom: 16 }}>Generate Key</Button>
            <Table dataSource={keys} columns={keyCols} rowKey="id" loading={loading} />
          </>
        )}
      ]} />
      <Modal title="Create Endpoint" open={endpointModal} onCancel={() => setEndpointModal(false)} onOk={() => form.submit()}>
        <Form form={form} layout="vertical" onFinish={handleCreateEndpoint} initialValues={{ rateLimit: 100, requiresAuth: true }}>
          <Form.Item name="name" label="Name" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="path" label="Path" rules={[{ required: true }]}><Input placeholder="/api/v1/resource" /></Form.Item>
          <Form.Item name="method" label="Method" rules={[{ required: true }]}><Input placeholder="GET" /></Form.Item>
          <Form.Item name="rateLimit" label="Rate Limit"><InputNumber min={1} /></Form.Item>
          <Form.Item name="ipWhitelist" label="IP Whitelist"><Input placeholder="192.168.1.1, 10.0.0.1" /></Form.Item>
          <Form.Item name="requiresAuth" label="Requires Auth" valuePropName="checked"><Switch /></Form.Item>
        </Form>
      </Modal>
      <Modal title="Generate API Key" open={keyModal} onCancel={() => setKeyModal(false)} onOk={() => keyForm.submit()}>
        <Form form={keyForm} layout="vertical" onFinish={handleCreateKey}>
          <Form.Item name="name" label="Key Name" rules={[{ required: true }]}><Input /></Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
