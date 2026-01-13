import React, { useState, useEffect } from 'react';
import { Table, Button, Modal, Form, Input, Upload, message, Tag, Space } from 'antd';
import { PlusOutlined, UploadOutlined, CheckCircleOutlined, RocketOutlined } from '@ant-design/icons';
import api from '../api';

const { TextArea } = Input;

export default function Integrations() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(false);
  const [form] = Form.useForm();

  const fetch = () => {
    setLoading(true);
    api.get('/integrations').then(({ data }) => setData(data)).finally(() => setLoading(false));
  };

  useEffect(() => { fetch(); }, []);

  const handleCreate = async (values) => {
    await api.post('/integrations', values);
    message.success('Created');
    setModal(false);
    form.resetFields();
    fetch();
  };

  const handleValidate = async (id) => {
    const { data } = await api.post(`/integrations/${id}/validate`);
    message[data.valid ? 'success' : 'error'](data.message);
  };

  const handleDeploy = async (id) => {
    await api.post(`/integrations/${id}/deploy`);
    message.success('Deployed');
    fetch();
  };

  const handleUpload = async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    try {
      const { data } = await api.post('/integrations/upload-yaml', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
      if (data.valid) form.setFieldsValue({ flowConfig: JSON.stringify(data.config, null, 2) });
    } catch (err) {
      message.error('Invalid YAML');
    }
    return false;
  };

  const columns = [
    { title: 'Name', dataIndex: 'name' },
    { title: 'Description', dataIndex: 'description' },
    { title: 'Status', dataIndex: 'status', render: (s) => <Tag color={s === 'deployed' ? 'green' : s === 'error' ? 'red' : 'default'}>{s}</Tag> },
    { title: 'Actions', render: (_, r) => (
      <Space>
        <Button icon={<CheckCircleOutlined />} onClick={() => handleValidate(r.id)}>Validate</Button>
        <Button type="primary" icon={<RocketOutlined />} onClick={() => handleDeploy(r.id)}>Deploy</Button>
      </Space>
    )}
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <h2>Integration Designer</h2>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setModal(true)}>New Integration</Button>
      </div>
      <Table dataSource={data} columns={columns} rowKey="id" loading={loading} />
      <Modal title="Create Integration" open={modal} onCancel={() => setModal(false)} onOk={() => form.submit()}>
        <Form form={form} layout="vertical" onFinish={handleCreate}>
          <Form.Item name="name" label="Name" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="description" label="Description"><Input /></Form.Item>
          <Form.Item label="Upload YAML"><Upload beforeUpload={handleUpload} accept=".yaml,.yml"><Button icon={<UploadOutlined />}>Upload</Button></Upload></Form.Item>
          <Form.Item name="flowConfig" label="Flow Config" rules={[{ required: true }]}><TextArea rows={8} /></Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
