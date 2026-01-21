import React, { useState, useEffect } from 'react';
import { Card, Table, Tag, Spin, Alert, Collapse, Typography, Space, Button, Tooltip, Modal, message, Tabs } from 'antd';
import {
  WarningOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  ReloadOutlined,
  EyeOutlined,
  CodeOutlined,
  SendOutlined,
  CloudUploadOutlined,
  ApiOutlined
} from '@ant-design/icons';
import api from '../api';

const { TabPane } = Tabs;

const { Panel } = Collapse;
const { Text, Paragraph } = Typography;

// JSON Formatter Component
const JsonDisplay = ({ data, title = "JSON Payload" }) => {
  const formatJson = (obj) => {
    try {
      return JSON.stringify(obj, null, 2);
    } catch (e) {
      return JSON.stringify(obj);
    }
  };

  return (
    <div style={{ 
      background: '#f6f8fa', 
      border: '1px solid #e1e4e8',
      borderRadius: 8,
      padding: 16,
      marginTop: 12
    }}>
      <div style={{ 
        display: 'flex', 
        alignItems: 'center', 
        marginBottom: 12,
        paddingBottom: 8,
        borderBottom: '1px solid #e1e4e8'
      }}>
        <CodeOutlined style={{ color: '#586069', marginRight: 8 }} />
        <Text strong style={{ color: '#24292e' }}>{title}</Text>
      </div>
      <pre style={{ 
        background: '#ffffff',
        border: '1px solid #e1e4e8',
        borderRadius: 6,
        padding: 12,
        margin: 0,
        fontSize: 12,
        fontFamily: 'Monaco, Menlo, "Ubuntu Mono", monospace',
        color: '#24292e',
        overflow: 'auto',
        maxHeight: 400,
        lineHeight: 1.45
      }}>
        {formatJson(data)}
      </pre>
    </div>
  );
};

// Case Status Component
const CaseStatus = ({ status }) => {
  const getStatusConfig = (status) => {
    switch (status?.toLowerCase()) {
      case 'new':
        return { color: 'blue', icon: <ClockCircleOutlined /> };
      case 'in progress':
      case 'working':
        return { color: 'orange', icon: <ExclamationCircleOutlined /> };
      case 'closed':
      case 'resolved':
        return { color: 'green', icon: <CheckCircleOutlined /> };
      case 'escalated':
      case 'critical':
        return { color: 'red', icon: <WarningOutlined /> };
      default:
        return { color: 'default', icon: <ClockCircleOutlined /> };
    }
  };

  const config = getStatusConfig(status);
  
  return (
    <Tag 
      icon={config.icon} 
      color={config.color}
      style={{ borderRadius: 12, fontWeight: 500 }}
    >
      {status || 'Unknown'}
    </Tag>
  );
};

// Priority Component
const CasePriority = ({ priority }) => {
  const getPriorityConfig = (priority) => {
    switch (priority?.toLowerCase()) {
      case 'critical':
      case 'high':
        return { color: 'red' };
      case 'medium':
        return { color: 'orange' };
      case 'low':
        return { color: 'blue' };
      default:
        return { color: 'default' };
    }
  };

  const config = getPriorityConfig(priority);
  
  return (
    <Tag 
      color={config.color}
      style={{ borderRadius: 12, fontWeight: 500 }}
    >
      {priority || 'Medium'}
    </Tag>
  );
};

export default function Events() {
  const [salesforceCases, setSalesforceCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedRows, setExpandedRows] = useState([]);
  const [sapModal, setSapModal] = useState({ visible: false, caseData: null, loading: false });
  const [sapResult, setSapResult] = useState(null);
  const [xmlPreview, setXmlPreview] = useState('');

  const fetchSalesforceCases = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout
      
      const response = await api.get('/cases/external/cases', {
        signal: controller.signal,
        timeout: 10000
      });
      
      clearTimeout(timeoutId);
      
      if (response.data.status === 'success') {
        const cases = response.data.cases.items || response.data.cases || [];
        setSalesforceCases(cases);
      } else {
        throw new Error(response.data.message || 'Failed to fetch Salesforce cases');
      }
    } catch (error) {
      console.error('Error fetching Salesforce cases:', error);
      setError(error.message || 'Failed to connect to external Salesforce application');
      setSalesforceCases([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSalesforceCases();
    
    // Refresh data every 2 minutes
    const interval = setInterval(fetchSalesforceCases, 120000);
    return () => clearInterval(interval);
  }, []);

  const handleRowExpand = (expanded, record) => {
    if (expanded) {
      setExpandedRows([...expandedRows, record.key]);
    } else {
      setExpandedRows(expandedRows.filter(key => key !== record.key));
    }
  };

  // Open SAP modal and preview XML
  const handleSendToSAP = async (caseData) => {
    setSapModal({ visible: true, caseData, loading: true });
    setSapResult(null);

    // Build the case data for transformation
    const transformData = {
      caseId: caseData.id,
      caseNumber: caseData.caseNumber || `CASE-${caseData.id}`,
      subject: caseData.subject,
      description: caseData.description,
      status: caseData.status,
      priority: caseData.priority,
      account: caseData.account || { id: caseData.accountId, name: caseData.accountName },
      contact: caseData.contact || { id: caseData.contactId, name: caseData.contactName },
      // Add load request specific fields
      currentLoad: caseData.currentLoad || 5,
      requestedLoad: caseData.requestedLoad || 10,
      connectionType: caseData.priority === 'High' || caseData.priority === 'Critical' ? 'COMMERCIAL' : 'RESIDENTIAL',
      city: caseData.city || 'Hyderabad',
      pinCode: caseData.pinCode || '500001'
    };

    try {
      // Preview the XML transformation
      const previewResponse = await api.post('/sap/preview-xml', transformData);
      setXmlPreview(previewResponse.data.xml);
    } catch (err) {
      setXmlPreview('Error generating XML preview');
    }

    setSapModal(prev => ({ ...prev, loading: false }));
  };

  // Actually send to SAP
  const executeSendToSAP = async () => {
    setSapModal(prev => ({ ...prev, loading: true }));

    const caseData = sapModal.caseData;
    const transformData = {
      caseId: caseData.id,
      caseNumber: caseData.caseNumber || `CASE-${caseData.id}`,
      subject: caseData.subject,
      description: caseData.description,
      status: caseData.status,
      priority: caseData.priority,
      account: caseData.account || { id: caseData.accountId, name: caseData.accountName },
      contact: caseData.contact || { id: caseData.contactId, name: caseData.contactName },
      currentLoad: caseData.currentLoad || 5,
      requestedLoad: caseData.requestedLoad || 10,
      connectionType: caseData.priority === 'High' || caseData.priority === 'Critical' ? 'COMMERCIAL' : 'RESIDENTIAL',
      city: caseData.city || 'Hyderabad',
      pinCode: caseData.pinCode || '500001'
    };

    try {
      const response = await api.post('/sap/send-load-request', {
        case_data: transformData,
        endpoint_type: 'load_request_xml'
      });

      setSapResult(response.data);

      if (response.data.success) {
        message.success('Case sent to SAP successfully!');
      } else {
        message.error(`SAP Error: ${response.data.error || 'Unknown error'}`);
      }
    } catch (err) {
      setSapResult({
        success: false,
        error: err.response?.data?.detail || err.message || 'Failed to connect to SAP'
      });
      message.error('Failed to send to SAP');
    }

    setSapModal(prev => ({ ...prev, loading: false }));
  };

  // Test SAP connection
  const testSAPConnection = async () => {
    try {
      const response = await api.get('/sap/test-connection');
      if (response.data.success) {
        message.success('SAP connection successful!');
      } else {
        message.warning(response.data.message || 'SAP not reachable');
      }
    } catch (err) {
      message.error('Cannot connect to SAP application on port 2004');
    }
  };

  const columns = [
    {
      title: 'Case ID',
      dataIndex: 'id',
      key: 'id',
      width: 140,
      render: (id) => (
        <Text 
          code 
          style={{ 
            fontWeight: 600, 
            color: '#1890ff',
            fontSize: 13
          }}
        >
          {id}
        </Text>
      )
    },
    {
      title: 'Subject',
      dataIndex: 'subject',
      key: 'subject',
      ellipsis: true,
      render: (subject) => (
        <Tooltip title={subject}>
          <Text strong style={{ color: '#262626' }}>
            {subject || 'No Subject'}
          </Text>
        </Tooltip>
      )
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status) => <CaseStatus status={status} />
    },
    {
      title: 'Priority',
      dataIndex: 'priority',
      key: 'priority',
      width: 100,
      render: (priority) => <CasePriority priority={priority} />
    },
    {
      title: 'Account',
      dataIndex: 'account',
      key: 'account',
      width: 180,
      ellipsis: true,
      render: (account) => (
        <Text style={{ color: '#595959' }}>
          {account || 'Unknown Account'}
        </Text>
      )
    },
    {
      title: 'Created Date',
      dataIndex: 'createdDate',
      key: 'createdDate',
      width: 140,
      render: (date) => (
        <Text style={{ fontSize: 12, color: '#8c8c8c' }}>
          {date ? new Date(date).toLocaleDateString() : 'N/A'}
        </Text>
      )
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 160,
      render: (_, record) => (
        <Space>
          <Tooltip title="View JSON Payload">
            <Button
              type="text"
              icon={<EyeOutlined />}
              size="small"
              onClick={() => {
                const isExpanded = expandedRows.includes(record.key);
                handleRowExpand(!isExpanded, record);
              }}
              style={{
                color: expandedRows.includes(record.key) ? '#1890ff' : '#8c8c8c'
              }}
            />
          </Tooltip>
          <Tooltip title="Send to SAP">
            <Button
              type="primary"
              icon={<SendOutlined />}
              size="small"
              onClick={() => handleSendToSAP(record.originalData)}
              style={{ borderRadius: 6 }}
            >
              SAP
            </Button>
          </Tooltip>
        </Space>
      )
    }
  ];

  const expandedRowRender = (record) => {
    const caseData = record.originalData;
    
    // Create comprehensive payload with all available data
    const fullPayload = {
      eventType: "CaseUpdate",
      eventId: `case-${caseData.id}-${Date.now()}`,
      eventTime: new Date().toISOString(),
      source: "External Salesforce Application",
      data: {
        caseId: caseData.id,
        caseNumber: caseData.caseNumber || `CASE-${String(caseData.id).padStart(6, '0')}`,
        subject: caseData.subject,
        description: caseData.description,
        status: caseData.status,
        priority: caseData.priority,
        origin: caseData.origin || 'Web',
        account: {
          id: caseData.accountId || `ACC-${caseData.id}`,
          name: caseData.account || caseData.accountName || 'Unknown Account'
        },
        contact: {
          id: caseData.contactId || `CON-${caseData.id}`,
          name: caseData.contact || caseData.contactName || 'Unknown Contact'
        },
        owner: {
          id: caseData.ownerId || `OWN-${caseData.id}`,
          name: caseData.owner || caseData.ownerName || 'System Administrator'
        },
        createdDate: caseData.createdDate || new Date().toISOString(),
        lastModifiedDate: caseData.lastModifiedDate || new Date().toISOString(),
        closedDate: caseData.closedDate || null,
        // Additional customer data
        customerData: {
          customerType: caseData.customerType || 'Business',
          region: caseData.region || 'London',
          serviceLevel: caseData.serviceLevel || 'Premium',
          contractNumber: caseData.contractNumber || `CNT-${caseData.id}`,
          billingAccount: caseData.billingAccount || `BILL-${caseData.id}`
        },
        // Technical details
        technicalDetails: {
          category: caseData.category || 'Power Outage',
          subcategory: caseData.subcategory || 'Planned Maintenance',
          affectedServices: caseData.affectedServices || ['Electricity Supply'],
          estimatedResolution: caseData.estimatedResolution || '4 hours',
          impactLevel: caseData.impactLevel || 'Medium'
        }
      },
      metadata: {
        syncedAt: new Date().toISOString(),
        source: "MuleSoft Integration Platform",
        version: "1.0",
        connector: "External Salesforce App",
        dataFormat: "platform-event",
        externalAppUrl: "http://localhost:5173",
        processingTimestamp: new Date().toISOString()
      }
    };

    return (
      <div style={{ padding: '16px 24px', background: '#fafafa' }}>
        <Collapse 
          defaultActiveKey={['payload']} 
          ghost
          expandIconPosition="right"
        >
          <Panel 
            header={
              <Space>
                <CodeOutlined style={{ color: '#1890ff' }} />
                <Text strong>Platform Event Payload</Text>
                <Tag color="blue" style={{ borderRadius: 8 }}>JSON Format</Tag>
              </Space>
            } 
            key="payload"
          >
            <JsonDisplay data={fullPayload} title="Complete Salesforce Case Event" />
          </Panel>
          
          <Panel 
            header={
              <Space>
                <EyeOutlined style={{ color: '#52c41a' }} />
                <Text strong>Raw Case Data</Text>
                <Tag color="green" style={{ borderRadius: 8 }}>Source Data</Tag>
              </Space>
            } 
            key="raw"
          >
            <JsonDisplay data={caseData} title="Original Salesforce Case Data" />
          </Panel>
        </Collapse>
      </div>
    );
  };

  const tableData = salesforceCases.map((caseItem, index) => ({
    key: `case-${index}`,
    id: caseItem.id || `case-${index}`,
    subject: caseItem.subject || 'No Subject',
    description: caseItem.description || 'No Description',
    status: caseItem.status || 'New',
    priority: caseItem.priority || 'Medium',
    origin: caseItem.origin || 'Web',
    account: caseItem.account?.name || caseItem.accountName || 'Unknown Account',
    contact: caseItem.contact?.name || caseItem.contactName || 'Unknown Contact',
    createdDate: caseItem.createdDate || new Date().toISOString(),
    originalData: caseItem // Store original data for expanded view
  }));

  return (
    <div className="animate-fade-in">
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h2 style={{ marginBottom: 4, color: '#262626' }}>Events</h2>
            <p style={{ color: '#8c8c8c', margin: 0 }}>
              Live Salesforce cases with JSON payload details
            </p>
          </div>
          <Space>
            <Button
              icon={<ApiOutlined />}
              onClick={testSAPConnection}
              style={{ borderRadius: 8 }}
            >
              Test SAP
            </Button>
            <Button
              icon={<ReloadOutlined />}
              onClick={fetchSalesforceCases}
              loading={loading}
              type="primary"
              style={{ borderRadius: 8 }}
            >
              Refresh
            </Button>
          </Space>
        </div>
      </div>

      {/* SAP Integration Info */}
      <Alert
        message="SAP Integration Ready"
        description={
          <span>
            Click <strong>"SAP"</strong> button on any case to transform and send data to SAP at{' '}
            <Text code>http://localhost:2004/api/integration/mulesoft/load-request/xml</Text>
          </span>
        }
        type="info"
        showIcon
        icon={<CloudUploadOutlined />}
        style={{ marginBottom: 16, borderRadius: 8 }}
      />

      {error && (
        <Alert
          message="Connection Error"
          description={error}
          type="error"
          showIcon
          style={{ marginBottom: 24, borderRadius: 8 }}
          action={
            <Button size="small" onClick={fetchSalesforceCases}>
              Retry
            </Button>
          }
        />
      )}

      <Card 
        title={
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Space>
              <span style={{ fontWeight: 600, fontSize: 16 }}>🔥 Live Salesforce Cases</span>
              <Tag 
                color={salesforceCases.length > 0 ? 'success' : 'error'} 
                style={{ borderRadius: 12 }}
              >
                {loading ? 'Loading...' : `${salesforceCases.length} Cases`}
              </Tag>
            </Space>
            <Text type="secondary" style={{ fontSize: 12 }}>
              Click on case rows to view JSON payloads
            </Text>
          </div>
        }
        className="animate-fade-in-up"
        style={{ borderRadius: 12 }}
      >
        {loading ? (
          <div style={{ 
            display: 'flex', 
            justifyContent: 'center', 
            alignItems: 'center', 
            height: 200 
          }}>
            <Spin size="large" />
            <span style={{ marginLeft: 16 }}>Loading Salesforce cases...</span>
          </div>
        ) : salesforceCases.length > 0 ? (
          <Table
            dataSource={tableData}
            columns={columns}
            expandable={{
              expandedRowRender,
              expandRowByClick: true,
              expandedRowKeys: expandedRows,
              onExpand: handleRowExpand,
              expandIcon: ({ expanded, onExpand, record }) => (
                <Button
                  type="text"
                  size="small"
                  icon={<EyeOutlined />}
                  onClick={e => {
                    e.stopPropagation();
                    onExpand(record, e);
                  }}
                  style={{ 
                    color: expanded ? '#1890ff' : '#8c8c8c',
                    transform: expanded ? 'rotate(0deg)' : 'rotate(0deg)'
                  }}
                />
              )
            }}
            pagination={{
              pageSize: 10,
              showSizeChanger: true,
              showQuickJumper: true,
              showTotal: (total, range) => 
                `${range[0]}-${range[1]} of ${total} cases`
            }}
            size="middle"
            scroll={{ x: 1000 }}
            style={{ 
              background: '#ffffff',
              borderRadius: 8
            }}
          />
        ) : (
          <div style={{ 
            textAlign: 'center', 
            padding: '60px 0', 
            color: '#8c8c8c' 
          }}>
            <WarningOutlined style={{ 
              fontSize: 48, 
              color: '#ff4d4f', 
              marginBottom: 16 
            }} />
            <h3 style={{ color: '#595959' }}>No Salesforce Cases Found</h3>
            <Paragraph style={{ color: '#8c8c8c', maxWidth: 400, margin: '0 auto' }}>
              Make sure your external Salesforce application is running on port 5173 
              and accessible at <Text code>http://localhost:5173</Text>
            </Paragraph>
            <div style={{ marginTop: 16 }}>
              <Button 
                type="primary" 
                icon={<ReloadOutlined />}
                onClick={fetchSalesforceCases}
                style={{ borderRadius: 8 }}
              >
                Try Again
              </Button>
            </div>
          </div>
        )}
      </Card>

      {/* SAP Send Modal */}
      <Modal
        title={
          <Space>
            <CloudUploadOutlined style={{ color: '#1890ff' }} />
            <span>Send to SAP - ElectricityLoadRequest</span>
          </Space>
        }
        open={sapModal.visible}
        onCancel={() => {
          setSapModal({ visible: false, caseData: null, loading: false });
          setSapResult(null);
          setXmlPreview('');
        }}
        width={900}
        footer={[
          <Button key="cancel" onClick={() => setSapModal({ visible: false, caseData: null, loading: false })}>
            Cancel
          </Button>,
          <Button
            key="send"
            type="primary"
            icon={<SendOutlined />}
            loading={sapModal.loading}
            onClick={executeSendToSAP}
            disabled={sapResult?.success}
          >
            {sapResult?.success ? 'Sent Successfully' : 'Send to SAP'}
          </Button>
        ]}
      >
        {sapModal.caseData && (
          <Tabs defaultActiveKey="preview">
            <TabPane tab="XML Preview" key="preview">
              <div style={{ marginBottom: 16 }}>
                <Text strong>Target Endpoint: </Text>
                <Text code>POST http://localhost:2004/api/integration/mulesoft/load-request/xml</Text>
              </div>
              <div style={{ marginBottom: 16 }}>
                <Text strong>Source Case: </Text>
                <Tag color="blue">{sapModal.caseData.id}</Tag>
                <Text>{sapModal.caseData.subject}</Text>
              </div>
              {sapModal.loading ? (
                <div style={{ textAlign: 'center', padding: 40 }}>
                  <Spin /> Generating XML...
                </div>
              ) : (
                <pre style={{
                  background: '#1e1e1e',
                  color: '#d4d4d4',
                  padding: 16,
                  borderRadius: 8,
                  overflow: 'auto',
                  maxHeight: 350,
                  fontSize: 12,
                  fontFamily: 'Monaco, Menlo, monospace'
                }}>
                  {xmlPreview}
                </pre>
              )}
            </TabPane>

            <TabPane tab="Source Data" key="source">
              <pre style={{
                background: '#f6f8fa',
                padding: 16,
                borderRadius: 8,
                overflow: 'auto',
                maxHeight: 400,
                fontSize: 12
              }}>
                {JSON.stringify(sapModal.caseData, null, 2)}
              </pre>
            </TabPane>

            {sapResult && (
              <TabPane tab="SAP Response" key="response">
                <Alert
                  message={sapResult.success ? 'Success' : 'Error'}
                  description={sapResult.success ? 'Data sent to SAP successfully' : sapResult.error}
                  type={sapResult.success ? 'success' : 'error'}
                  showIcon
                  style={{ marginBottom: 16 }}
                />
                {sapResult.sap_response && (
                  <>
                    <Text strong>SAP Response:</Text>
                    <pre style={{
                      background: '#f6f8fa',
                      padding: 16,
                      borderRadius: 8,
                      overflow: 'auto',
                      maxHeight: 300,
                      fontSize: 12,
                      marginTop: 8
                    }}>
                      {JSON.stringify(sapResult.sap_response, null, 2)}
                    </pre>
                    {sapResult.sap_response.tickets_created && (
                      <div style={{ marginTop: 16 }}>
                        <Text strong>Tickets Created in SAP:</Text>
                        <div style={{ marginTop: 8 }}>
                          <Tag color="blue">PM: {sapResult.sap_response.tickets_created.pm_ticket}</Tag>
                          <Tag color="green">FI: {sapResult.sap_response.tickets_created.fi_ticket}</Tag>
                          <Tag color="orange">MM: {sapResult.sap_response.tickets_created.mm_ticket}</Tag>
                        </div>
                      </div>
                    )}
                  </>
                )}
              </TabPane>
            )}
          </Tabs>
        )}
      </Modal>
    </div>
  );
}