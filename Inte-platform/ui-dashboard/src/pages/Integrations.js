import React, { useState, useEffect } from 'react';
import { Table, Button, Modal, Form, Input, Upload, message, Tag, Space, Select, Tabs, Card, Collapse, Divider, Alert } from 'antd';
import { PlusOutlined, UploadOutlined, CheckCircleOutlined, RocketOutlined, CodeOutlined, SwapOutlined, EyeOutlined, DeleteOutlined } from '@ant-design/icons';
import api from '../api';

const { TextArea } = Input;
const { Option } = Select;
const { TabPane } = Tabs;
const { Panel } = Collapse;

// SAP IDoc types for transform
const IDOC_TYPES = [
  { value: 'SRCLST', label: 'SRCLST - Service Request', description: 'SAP IDoc for service/case creation' },
  { value: 'DEBMAS', label: 'DEBMAS - Customer Master', description: 'SAP IDoc for customer master data' },
  { value: 'ORDERS', label: 'ORDERS - Sales Order', description: 'SAP IDoc for sales order creation' },
  { value: 'CRMXIF_ORDER', label: 'CRMXIF_ORDER - CRM Order', description: 'SAP CRM Order IDoc' },
  { value: 'MATMAS', label: 'MATMAS - Material Master', description: 'SAP IDoc for material master data' }
];

// Pre-built flow templates
const FLOW_TEMPLATES = {
  salesforce_to_sap: {
    name: 'Salesforce Case to SAP Service Request',
    description: 'Transform Salesforce Case events to SAP IDoc format and send to SAP',
    config: `routes:
  - from: "salesforce:cases"
    description: "Fetch Salesforce Case events"
    transform:
      type: "sap_idoc"
      idoc_type: "SRCLST"
      include_metadata: true
    to: "sap:service-requests"
    error_handler: "dead-letter-queue"`
  },
  salesforce_to_sap_customer: {
    name: 'Salesforce Account to SAP Customer',
    description: 'Sync Salesforce Account data to SAP Customer Master',
    config: `routes:
  - from: "salesforce:accounts"
    description: "Fetch Salesforce Account updates"
    transform:
      type: "sap_idoc"
      idoc_type: "DEBMAS"
      include_metadata: true
    to: "sap:customer-master"
    error_handler: "retry-queue"`
  },
  generic_json_to_xml: {
    name: 'Generic JSON to XML',
    description: 'Convert any JSON payload to XML format',
    config: `routes:
  - from: "http:webhook"
    description: "Receive JSON webhook"
    transform:
      type: "generic_xml"
      root_element: "DATA"
    to: "http:destination"
    error_handler: "log-and-continue"`
  }
};

export default function Integrations() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(false);
  const [previewModal, setPreviewModal] = useState(false);
  const [previewData, setPreviewData] = useState({ xml: '', loading: false });
  const [form] = Form.useForm();
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [transformConfig, setTransformConfig] = useState({
    type: 'sap_idoc',
    idoc_type: 'SRCLST',
    include_metadata: true
  });

  const fetch = () => {
    setLoading(true);
    api.get('/integrations').then(({ data }) => setData(data)).finally(() => setLoading(false));
  };

  useEffect(() => { fetch(); }, []);

  const handleCreate = async (values) => {
    await api.post('/integrations', values);
    message.success('Integration created successfully');
    setModal(false);
    form.resetFields();
    setSelectedTemplate(null);
    fetch();
  };

  const handleValidate = async (id) => {
    const { data } = await api.post(`/integrations/${id}/validate`);
    message[data.valid ? 'success' : 'error'](data.message);
  };

  const handleDeploy = async (id) => {
    await api.post(`/integrations/${id}/deploy`);
    message.success('Integration deployed successfully');
    fetch();
  };

  const handleDelete = async (id) => {
    Modal.confirm({
      title: 'Delete Integration',
      content: 'Are you sure you want to delete this integration?',
      onOk: async () => {
        await api.delete(`/integrations/${id}`);
        message.success('Integration deleted');
        fetch();
      }
    });
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

  const handleTemplateSelect = (templateKey) => {
    setSelectedTemplate(templateKey);
    if (templateKey && FLOW_TEMPLATES[templateKey]) {
      const template = FLOW_TEMPLATES[templateKey];
      form.setFieldsValue({
        name: template.name,
        description: template.description,
        flowConfig: template.config
      });
    }
  };

  const handlePreviewTransform = async () => {
    setPreviewData({ xml: '', loading: true });
    setPreviewModal(true);

    // Sample Salesforce event data for preview
    const sampleData = {
      caseId: "SF-CASE-001",
      caseNumber: "00001001",
      subject: "Network connectivity issue in Building A",
      description: "Users reporting intermittent network drops. Affecting productivity.",
      status: "New",
      priority: "High",
      origin: "Web",
      account: {
        id: "ACC-001",
        name: "Acme Corporation"
      },
      contact: {
        id: "CON-001",
        name: "John Smith"
      },
      owner: {
        id: "USR-001",
        name: "Support Team"
      },
      createdDate: new Date().toISOString(),
      lastModifiedDate: new Date().toISOString()
    };

    try {
      const response = await api.post('/transform/preview', {
        source_data: sampleData,
        target_format: transformConfig.type,
        idoc_type: transformConfig.idoc_type,
        include_metadata: transformConfig.include_metadata
      });
      setPreviewData({ xml: response.data.output, loading: false, warnings: response.data.warnings });
    } catch (error) {
      setPreviewData({ xml: 'Error generating preview: ' + (error.response?.data?.detail || error.message), loading: false });
    }
  };

  const generateFlowConfig = () => {
    const config = `routes:
  - from: "salesforce:cases"
    description: "Fetch Salesforce Case events"
    transform:
      type: "${transformConfig.type}"
      idoc_type: "${transformConfig.idoc_type}"
      include_metadata: ${transformConfig.include_metadata}
    to: "sap:service-requests"
    error_handler: "dead-letter-queue"`;
    form.setFieldsValue({ flowConfig: config });
    message.success('Flow configuration generated');
  };

  const columns = [
    { title: 'Name', dataIndex: 'name', key: 'name' },
    { title: 'Description', dataIndex: 'description', key: 'description', ellipsis: true },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (s) => (
        <Tag color={s === 'deployed' ? 'green' : s === 'error' ? 'red' : s === 'stopped' ? 'orange' : 'default'}>
          {s?.toUpperCase()}
        </Tag>
      )
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, r) => (
        <Space>
          <Button size="small" icon={<CheckCircleOutlined />} onClick={() => handleValidate(r.id)}>Validate</Button>
          <Button size="small" type="primary" icon={<RocketOutlined />} onClick={() => handleDeploy(r.id)}>Deploy</Button>
          <Button size="small" danger icon={<DeleteOutlined />} onClick={() => handleDelete(r.id)} />
        </Space>
      )
    }
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <h2>Integration Designer</h2>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setModal(true)}>New Integration</Button>
      </div>

      <Alert
        message="Salesforce to SAP Integration"
        description="Create integration flows that transform Salesforce events to SAP XML/IDoc format. Use the transform step in your flow configuration to convert JSON data to SAP-compatible XML."
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
      />

      <Table dataSource={data} columns={columns} rowKey="id" loading={loading} />

      {/* Create Integration Modal */}
      <Modal
        title="Create Integration Flow"
        open={modal}
        onCancel={() => { setModal(false); setSelectedTemplate(null); form.resetFields(); }}
        onOk={() => form.submit()}
        width={800}
        okText="Create Integration"
      >
        <Tabs defaultActiveKey="template">
          <TabPane tab="Use Template" key="template">
            <div style={{ marginBottom: 16 }}>
              <Select
                placeholder="Select a flow template"
                style={{ width: '100%' }}
                onChange={handleTemplateSelect}
                value={selectedTemplate}
                allowClear
              >
                {Object.entries(FLOW_TEMPLATES).map(([key, template]) => (
                  <Option key={key} value={key}>
                    <div>
                      <strong>{template.name}</strong>
                      <div style={{ fontSize: 12, color: '#888' }}>{template.description}</div>
                    </div>
                  </Option>
                ))}
              </Select>
            </div>
          </TabPane>

          <TabPane tab="Transform Builder" key="builder">
            <Card size="small" title="Configure Salesforce to SAP Transform" style={{ marginBottom: 16 }}>
              <Space direction="vertical" style={{ width: '100%' }}>
                <div>
                  <label>Transform Type:</label>
                  <Select
                    style={{ width: '100%', marginTop: 4 }}
                    value={transformConfig.type}
                    onChange={(v) => setTransformConfig({ ...transformConfig, type: v })}
                  >
                    <Option value="sap_idoc">SAP IDoc Format</Option>
                    <Option value="sap_xml">SAP XML Format</Option>
                    <Option value="generic_xml">Generic XML</Option>
                  </Select>
                </div>

                {(transformConfig.type === 'sap_idoc' || transformConfig.type === 'sap_xml') && (
                  <div>
                    <label>SAP IDoc Type:</label>
                    <Select
                      style={{ width: '100%', marginTop: 4 }}
                      value={transformConfig.idoc_type}
                      onChange={(v) => setTransformConfig({ ...transformConfig, idoc_type: v })}
                    >
                      {IDOC_TYPES.map(t => (
                        <Option key={t.value} value={t.value}>
                          <div>
                            <strong>{t.label}</strong>
                            <div style={{ fontSize: 11, color: '#888' }}>{t.description}</div>
                          </div>
                        </Option>
                      ))}
                    </Select>
                  </div>
                )}

                <Space style={{ marginTop: 8 }}>
                  <Button icon={<CodeOutlined />} onClick={generateFlowConfig}>
                    Generate Flow Config
                  </Button>
                  <Button icon={<EyeOutlined />} onClick={handlePreviewTransform}>
                    Preview XML Output
                  </Button>
                </Space>
              </Space>
            </Card>
          </TabPane>
        </Tabs>

        <Divider />

        <Form form={form} layout="vertical" onFinish={handleCreate}>
          <Form.Item name="name" label="Integration Name" rules={[{ required: true, message: 'Please enter a name' }]}>
            <Input placeholder="e.g., Salesforce Case to SAP Service Request" />
          </Form.Item>

          <Form.Item name="description" label="Description">
            <Input placeholder="Brief description of what this integration does" />
          </Form.Item>

          <Form.Item label="Upload YAML (Optional)">
            <Upload beforeUpload={handleUpload} accept=".yaml,.yml" maxCount={1}>
              <Button icon={<UploadOutlined />}>Upload YAML File</Button>
            </Upload>
          </Form.Item>

          <Form.Item
            name="flowConfig"
            label="Flow Configuration (YAML)"
            rules={[{ required: true, message: 'Please provide flow configuration' }]}
          >
            <TextArea
              rows={12}
              placeholder={`routes:
  - from: "salesforce:cases"
    transform:
      type: "sap_idoc"
      idoc_type: "SRCLST"
    to: "sap:service-requests"`}
              style={{ fontFamily: 'monospace', fontSize: 12 }}
            />
          </Form.Item>
        </Form>
      </Modal>

      {/* Preview Modal */}
      <Modal
        title={<><SwapOutlined /> Transform Preview: Salesforce JSON → SAP XML</>}
        open={previewModal}
        onCancel={() => setPreviewModal(false)}
        width={900}
        footer={[
          <Button key="close" onClick={() => setPreviewModal(false)}>Close</Button>
        ]}
      >
        {previewData.loading ? (
          <div style={{ textAlign: 'center', padding: 40 }}>Loading preview...</div>
        ) : (
          <>
            {previewData.warnings && previewData.warnings.length > 0 && (
              <Alert
                message="Warnings"
                description={previewData.warnings.join(', ')}
                type="warning"
                style={{ marginBottom: 16 }}
                showIcon
              />
            )}
            <Collapse defaultActiveKey={['output']}>
              <Panel header="Sample Salesforce Input (JSON)" key="input">
                <pre style={{ background: '#f5f5f5', padding: 12, borderRadius: 4, overflow: 'auto', maxHeight: 200, fontSize: 11 }}>
{`{
  "caseId": "SF-CASE-001",
  "caseNumber": "00001001",
  "subject": "Network connectivity issue in Building A",
  "status": "New",
  "priority": "High",
  "account": { "id": "ACC-001", "name": "Acme Corporation" },
  "contact": { "id": "CON-001", "name": "John Smith" }
}`}
                </pre>
              </Panel>
              <Panel header="SAP XML Output" key="output">
                <pre style={{ background: '#1e1e1e', color: '#d4d4d4', padding: 12, borderRadius: 4, overflow: 'auto', maxHeight: 400, fontSize: 11 }}>
                  {previewData.xml}
                </pre>
              </Panel>
            </Collapse>
          </>
        )}
      </Modal>
    </div>
  );
}
