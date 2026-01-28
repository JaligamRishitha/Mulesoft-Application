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
  ApiOutlined,
  ThunderboltOutlined,
  UserAddOutlined,
  SyncOutlined,
  FileProtectOutlined
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
  const [sfConnector, setSfConnector] = useState(null);
  const [snowModal, setSnowModal] = useState({ visible: false, caseData: null, loading: false });
  const [snowResult, setSnowResult] = useState(null);
  const [snowPreview, setSnowPreview] = useState({ ticket: null, approval: null });

  // Account Requests state
  const [accountRequests, setAccountRequests] = useState([]);
  const [accountLoading, setAccountLoading] = useState(false);
  const [accountError, setAccountError] = useState(null);
  const [orchestrating, setOrchestrating] = useState(false);
  const [orchestrationResult, setOrchestrationResult] = useState(null);
  const [activeTab, setActiveTab] = useState('cases');

  const fetchSalesforceConnector = async () => {
    try {
      const { data } = await api.get('/connectors');
      const connector = data.find(c => c.type === 'salesforce');
      if (connector) {
        setSfConnector(connector);
        // Fetch full config for this connector
        const detail = await api.get(`/connectors/${connector.id}`);
        setSfConnector(detail.data);
        return connector;
      }
    } catch (err) {
      console.error('Error fetching Salesforce connector:', err);
    }
    return null;
  };

  const fetchSalesforceCases = async () => {
    setLoading(true);
    setError(null);

    try {
      // First get the Salesforce connector
      let connector = sfConnector;
      if (!connector) {
        connector = await fetchSalesforceConnector();
      }

      if (!connector) {
        throw new Error('No Salesforce connector configured. Please create one in the Connectors page.');
      }

      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 10000);

      const response = await api.get(`/cases/external/cases?connector_id=${connector.id}`, {
        signal: controller.signal,
        timeout: 10000
      });

      clearTimeout(timeoutId);

      if (response.data.status === 'success') {
        const cases = response.data.cases.items || response.data.cases || [];
        setSalesforceCases(cases);
      } else {
        throw new Error(response.data.message || 'Failed to fetch cases from remote server');
      }
    } catch (error) {
      console.error('Error fetching Salesforce cases:', error);
      setError(error.message || 'Failed to connect to the remote Salesforce server');
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

  // Open ServiceNow modal and preview payloads
  const handleSendToServiceNow = async (caseData) => {
    setSnowModal({ visible: true, caseData, loading: true });
    setSnowResult(null);

    const transformData = {
      id: caseData.id,
      caseId: caseData.id,
      caseNumber: caseData.caseNumber || `CASE-${caseData.id}`,
      subject: caseData.subject,
      description: caseData.description,
      status: caseData.status,
      priority: caseData.priority,
      account: caseData.account || { id: caseData.accountId, name: caseData.accountName },
      contact: caseData.contact || { id: caseData.contactId, name: caseData.contactName },
      userName: caseData.userName || '',
      userEmail: caseData.userEmail || '',
      userRole: caseData.userRole || 'Standard User',
      department: caseData.department || '',
      category: caseData.category || 'User Account',
      createdDate: caseData.createdDate || new Date().toISOString()
    };

    try {
      const [ticketPreview, approvalPreview] = await Promise.all([
        api.post('/servicenow/preview-ticket', transformData, { params: { ticket_type: 'incident' } }),
        api.post('/servicenow/preview-approval', transformData, { params: { approval_type: 'user_account' } })
      ]);
      setSnowPreview({
        ticket: ticketPreview.data.ticket_payload,
        approval: approvalPreview.data.approval_payload
      });
    } catch (err) {
      setSnowPreview({ ticket: null, approval: null });
    }

    setSnowModal(prev => ({ ...prev, loading: false }));
  };

  // Send ticket to ServiceNow
  const executeSendTicketToServiceNow = async () => {
    setSnowModal(prev => ({ ...prev, loading: true }));

    const caseData = snowModal.caseData;
    const transformData = {
      id: caseData.id,
      caseId: caseData.id,
      caseNumber: caseData.caseNumber || `CASE-${caseData.id}`,
      subject: caseData.subject,
      description: caseData.description,
      status: caseData.status,
      priority: caseData.priority,
      account: caseData.account || { id: caseData.accountId, name: caseData.accountName },
      contact: caseData.contact || { id: caseData.contactId, name: caseData.contactName },
      userName: caseData.userName || '',
      userEmail: caseData.userEmail || '',
      userRole: caseData.userRole || 'Standard User',
      department: caseData.department || '',
      category: caseData.category || 'User Account',
      createdDate: caseData.createdDate || new Date().toISOString()
    };

    try {
      const response = await api.post('/servicenow/send-ticket-and-approval', transformData, {
        params: { ticket_type: 'incident', approval_type: 'user_account' }
      });

      setSnowResult(response.data);

      if (response.data.ticket?.success || response.data.approval?.success) {
        message.success('Data sent to ServiceNow successfully!');
      } else {
        message.error('Failed to send to ServiceNow');
      }
    } catch (err) {
      setSnowResult({
        ticket: { success: false, error: err.response?.data?.detail || err.message },
        approval: { success: false, error: err.response?.data?.detail || err.message }
      });
      message.error('Failed to send to ServiceNow');
    }

    setSnowModal(prev => ({ ...prev, loading: false }));
  };

  // Test ServiceNow connection
  const testServiceNowConnection = async () => {
    try {
      const response = await api.get('/servicenow/test-connection');
      if (response.data.success) {
        message.success('ServiceNow connection successful!');
      } else {
        message.warning(response.data.message || 'ServiceNow not reachable');
      }
    } catch (err) {
      message.error('Cannot connect to ServiceNow application');
    }
  };

  // Fetch account creation requests
  const fetchAccountRequests = async () => {
    setAccountLoading(true);
    setAccountError(null);

    try {
      let connector = sfConnector;
      if (!connector) {
        connector = await fetchSalesforceConnector();
      }
      if (!connector) {
        throw new Error('No Salesforce connector configured.');
      }

      const response = await api.get(`/cases/external/account-requests?connector_id=${connector.id}`, {
        timeout: 15000
      });

      if (response.data.status === 'success') {
        setAccountRequests(response.data.requests || []);
      } else {
        throw new Error(response.data.message || 'Failed to fetch account requests');
      }
    } catch (err) {
      console.error('Error fetching account requests:', err);
      setAccountError(err.message || 'Failed to fetch account requests');
      setAccountRequests([]);
    } finally {
      setAccountLoading(false);
    }
  };

  // Run full orchestration
  const runOrchestration = async () => {
    setOrchestrating(true);
    setOrchestrationResult(null);

    try {
      let connector = sfConnector;
      if (!connector) {
        connector = await fetchSalesforceConnector();
      }
      if (!connector) {
        throw new Error('No Salesforce connector configured.');
      }

      const response = await api.post(`/cases/orchestrate/account-requests?connector_id=${connector.id}`, null, {
        timeout: 60000
      });

      setOrchestrationResult(response.data);

      if (response.data.total_sent_to_servicenow > 0) {
        message.success(`${response.data.total_sent_to_servicenow} requests validated and sent to ServiceNow for manual approval`);
      } else if (response.data.total_fetched === 0) {
        message.info('No pending account requests to process');
      } else if (response.data.total_invalid > 0) {
        message.warning(`Validation failed for ${response.data.total_invalid} requests - check errors below`);
      } else {
        message.warning(`Completed with ${response.data.total_failed} failures`);
      }

      // Refresh the account requests list
      await fetchAccountRequests();
    } catch (err) {
      console.error('Orchestration error:', err);
      message.error(err.response?.data?.detail || err.message || 'Orchestration failed');
      setOrchestrationResult({
        status: 'error',
        message: err.response?.data?.detail || err.message
      });
    } finally {
      setOrchestrating(false);
    }
  };

  // Account request status tag
  const RequestStatus = ({ status }) => {
    const config = {
      'PENDING': { color: 'orange', icon: <ClockCircleOutlined /> },
      'COMPLETED': { color: 'green', icon: <CheckCircleOutlined /> },
      'REJECTED': { color: 'red', icon: <WarningOutlined /> },
      'FAILED': { color: 'red', icon: <ExclamationCircleOutlined /> }
    };
    const c = config[status] || { color: 'default', icon: <ClockCircleOutlined /> };
    return <Tag icon={c.icon} color={c.color} style={{ borderRadius: 12, fontWeight: 500 }}>{status || 'Unknown'}</Tag>;
  };

  const IntegrationStatusTag = ({ status }) => {
    const config = {
      'COMPLETED': { color: 'green' },
      'FAILED': { color: 'red' },
      'REQUESTED': { color: 'blue' },
      'PENDING': { color: 'orange' }
    };
    const c = config[status] || { color: 'default' };
    return <Tag color={c.color} style={{ borderRadius: 12 }}>{status || 'N/A'}</Tag>;
  };

  const accountColumns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 60,
      render: (id) => <Text code style={{ fontWeight: 600, color: '#1890ff' }}>{id}</Text>
    },
    {
      title: 'Account Name',
      dataIndex: 'name',
      key: 'name',
      render: (name) => <Text strong style={{ color: '#262626' }}>{name}</Text>
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      width: 140,
      render: (status) => <RequestStatus status={status} />
    },
    {
      title: 'Integration',
      dataIndex: 'integration_status',
      key: 'integration_status',
      width: 130,
      render: (status) => <IntegrationStatusTag status={status} />
    },
    {
      title: 'ServiceNow Ticket',
      dataIndex: 'servicenow_ticket_id',
      key: 'servicenow_ticket_id',
      width: 160,
      render: (id) => id ? <Tag color="purple" style={{ borderRadius: 8 }}>{id}</Tag> : <Text type="secondary">-</Text>
    },
    {
      title: 'MuleSoft TX ID',
      dataIndex: 'mulesoft_transaction_id',
      key: 'mulesoft_transaction_id',
      width: 170,
      render: (id) => id ? <Tag color="cyan" style={{ borderRadius: 8 }}>{id}</Tag> : <Text type="secondary">-</Text>
    },
    {
      title: 'Created Account',
      dataIndex: 'created_account_id',
      key: 'created_account_id',
      width: 130,
      render: (id) => id ? <Tag color="green" icon={<CheckCircleOutlined />} style={{ borderRadius: 8 }}>Account #{id}</Tag> : <Text type="secondary">Not yet</Text>
    },
    {
      title: 'Requested At',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 140,
      render: (date) => <Text style={{ fontSize: 12, color: '#8c8c8c' }}>{date ? new Date(date).toLocaleString() : 'N/A'}</Text>
    }
  ];

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
      width: 280,
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
          <Tooltip title="Send as Ticket & Approval to ServiceNow">
            <Button
              icon={<SendOutlined />}
              size="small"
              onClick={() => handleSendToServiceNow(record.originalData)}
              style={{ borderRadius: 6, background: '#81B5A1', borderColor: '#81B5A1', color: '#fff' }}
            >
              ServiceNow
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
        externalAppUrl: sfConnector?.config?.server_url || "not-configured",
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
              Live Salesforce data - Cases, account creation requests, and orchestration to ServiceNow
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
              icon={<ApiOutlined />}
              onClick={testServiceNowConnection}
              style={{ borderRadius: 8, background: '#81B5A1', borderColor: '#81B5A1', color: '#fff' }}
            >
              Test ServiceNow
            </Button>
          </Space>
        </div>
      </div>

      <Tabs
        activeKey={activeTab}
        onChange={(key) => {
          setActiveTab(key);
          if (key === 'account-requests' && accountRequests.length === 0) {
            fetchAccountRequests();
          }
        }}
        type="card"
        style={{ marginBottom: 16 }}
        items={[
          {
            key: 'cases',
            label: (
              <span>
                <CodeOutlined style={{ marginRight: 6 }} />
                Salesforce Cases
                <Tag color="blue" style={{ marginLeft: 8, borderRadius: 12 }}>{salesforceCases.length}</Tag>
              </span>
            ),
            children: (
              <>
                {/* Integration Info */}
                <Alert
                  message="Salesforce Case Integration Active"
                  description={
                    <span>
                      Cases from <Text code>http://149.102.158.71:4799</Text> are displayed below.
                      Click <strong>"ServiceNow"</strong> to send as tickets & approvals to <Text code>http://149.102.158.71:4780</Text>.
                      Click <strong>"SAP"</strong> to send to SAP.
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
                    style={{ marginBottom: 16, borderRadius: 8 }}
                    action={<Button size="small" onClick={fetchSalesforceCases}>Retry</Button>}
                  />
                )}

                <Card
                  title={
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Space>
                        <span style={{ fontWeight: 600, fontSize: 16 }}>Live Salesforce Cases</span>
                        <Tag color={salesforceCases.length > 0 ? 'success' : 'error'} style={{ borderRadius: 12 }}>
                          {loading ? 'Loading...' : `${salesforceCases.length} Cases`}
                        </Tag>
                      </Space>
                      <Button icon={<ReloadOutlined />} onClick={fetchSalesforceCases} loading={loading} type="primary" style={{ borderRadius: 8 }}>
                        Refresh
                      </Button>
                    </div>
                  }
                  className="animate-fade-in-up"
                  style={{ borderRadius: 12 }}
                >
                  {loading ? (
                    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 200 }}>
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
                          <Button type="text" size="small" icon={<EyeOutlined />}
                            onClick={e => { e.stopPropagation(); onExpand(record, e); }}
                            style={{ color: expanded ? '#1890ff' : '#8c8c8c' }}
                          />
                        )
                      }}
                      pagination={{ pageSize: 10, showSizeChanger: true, showTotal: (total, range) => `${range[0]}-${range[1]} of ${total} cases` }}
                      size="middle"
                      scroll={{ x: 1000 }}
                      style={{ background: '#ffffff', borderRadius: 8 }}
                    />
                  ) : (
                    <div style={{ textAlign: 'center', padding: '60px 0', color: '#8c8c8c' }}>
                      <WarningOutlined style={{ fontSize: 48, color: '#ff4d4f', marginBottom: 16 }} />
                      <h3 style={{ color: '#595959' }}>No Salesforce Cases Found</h3>
                      <Paragraph style={{ color: '#8c8c8c', maxWidth: 500, margin: '0 auto' }}>
                        {sfConnector?.config?.server_url
                          ? <>Make sure your remote Salesforce backend is running and accessible at <Text code>{sfConnector.config.server_url}</Text></>
                          : <>No Salesforce connector configured. Please create one in the <Text strong>Connectors</Text> page.</>
                        }
                      </Paragraph>
                      <Button type="primary" icon={<ReloadOutlined />} onClick={fetchSalesforceCases} style={{ marginTop: 16, borderRadius: 8 }}>Try Again</Button>
                    </div>
                  )}
                </Card>
              </>
            )
          },
          {
            key: 'account-requests',
            label: (
              <span>
                <UserAddOutlined style={{ marginRight: 6 }} />
                Account Requests
                {accountRequests.length > 0 && (
                  <Tag
                    color={accountRequests.some(r => r.status === 'PENDING') ? 'orange' : 'green'}
                    style={{ marginLeft: 8, borderRadius: 12 }}
                  >
                    {accountRequests.filter(r => r.status === 'PENDING').length} Pending
                  </Tag>
                )}
              </span>
            ),
            children: (
              <>
                <Alert
                  message="Salesforce → MuleSoft (Validate) → ServiceNow (Manual Approval)"
                  description={
                    <span>
                      Account creation requests from Salesforce are <strong>validated</strong> by MuleSoft and sent to ServiceNow for <strong>manual approval</strong>.
                      MuleSoft does NOT auto-approve accounts. An admin must approve each request in ServiceNow before the account is created.
                      Click <strong>"Validate & Send to ServiceNow"</strong> to validate pending requests and create approval tickets.
                    </span>
                  }
                  type="info"
                  showIcon
                  icon={<SyncOutlined />}
                  style={{ marginBottom: 16, borderRadius: 8 }}
                />

                {accountError && (
                  <Alert
                    message="Error Fetching Account Requests"
                    description={accountError}
                    type="error"
                    showIcon
                    style={{ marginBottom: 16, borderRadius: 8 }}
                    action={<Button size="small" onClick={fetchAccountRequests}>Retry</Button>}
                  />
                )}

                {/* Orchestration Result */}
                {orchestrationResult && (
                  <Card
                    size="small"
                    style={{ marginBottom: 16, borderRadius: 12, borderColor: orchestrationResult.status === 'success' ? '#b7eb8f' : '#ffa39e' }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                      <Space>
                        <ThunderboltOutlined style={{ color: orchestrationResult.total_sent_to_servicenow > 0 ? '#52c41a' : '#faad14', fontSize: 18 }} />
                        <Text strong style={{ fontSize: 15 }}>Validation & Routing Result</Text>
                      </Space>
                      <Button size="small" type="text" onClick={() => setOrchestrationResult(null)}>Dismiss</Button>
                    </div>

                    {orchestrationResult.status === 'error' ? (
                      <Alert type="error" message={orchestrationResult.message} showIcon />
                    ) : (
                      <>
                        <div style={{ display: 'flex', gap: 16, marginBottom: 16 }}>
                          <Card size="small" style={{ flex: 1, textAlign: 'center', borderRadius: 8 }}>
                            <Text type="secondary" style={{ fontSize: 12 }}>Fetched</Text>
                            <div style={{ fontSize: 24, fontWeight: 700, color: '#1890ff' }}>{orchestrationResult.total_fetched}</div>
                          </Card>
                          <Card size="small" style={{ flex: 1, textAlign: 'center', borderRadius: 8 }}>
                            <Text type="secondary" style={{ fontSize: 12 }}>Passed Validation</Text>
                            <div style={{ fontSize: 24, fontWeight: 700, color: '#52c41a' }}>{orchestrationResult.total_valid}</div>
                          </Card>
                          <Card size="small" style={{ flex: 1, textAlign: 'center', borderRadius: 8 }}>
                            <Text type="secondary" style={{ fontSize: 12 }}>Failed Validation</Text>
                            <div style={{ fontSize: 24, fontWeight: 700, color: '#ff4d4f' }}>{orchestrationResult.total_invalid || 0}</div>
                          </Card>
                          <Card size="small" style={{ flex: 1, textAlign: 'center', borderRadius: 8 }}>
                            <Text type="secondary" style={{ fontSize: 12 }}>Sent to ServiceNow</Text>
                            <div style={{ fontSize: 24, fontWeight: 700, color: '#722ed1' }}>{orchestrationResult.total_sent_to_servicenow || 0}</div>
                          </Card>
                        </div>

                        {orchestrationResult.processed_requests?.map((req, idx) => {
                          const isValid = req.outcome === 'SENT_TO_SERVICENOW';
                          const isFailed = req.outcome === 'VALIDATION_FAILED';
                          const bgColor = isValid ? '#f6ffed' : isFailed ? '#fff1f0' : '#fff7e6';
                          const borderColor = isValid ? '#b7eb8f' : isFailed ? '#ffa39e' : '#ffd591';
                          const icon = isValid ? <CheckCircleOutlined style={{ color: '#52c41a' }} /> :
                                       isFailed ? <WarningOutlined style={{ color: '#ff4d4f' }} /> :
                                       <ExclamationCircleOutlined style={{ color: '#faad14' }} />;
                          const tagColor = isValid ? 'green' : isFailed ? 'red' : 'orange';

                          return (
                            <div key={idx} style={{ padding: 12, marginBottom: 8, borderRadius: 8, background: bgColor, border: `1px solid ${borderColor}` }}>
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <Space>
                                  {icon}
                                  <Text strong>{req.account_name}</Text>
                                  <Text type="secondary">(Request #{req.request_id})</Text>
                                </Space>
                                <Tag color={tagColor} style={{ borderRadius: 12 }}>{req.outcome}</Tag>
                              </div>

                              {/* Validation errors */}
                              {req.steps?.validation?.errors?.length > 0 && (
                                <div style={{ marginTop: 8, marginLeft: 22 }}>
                                  {req.steps.validation.errors.map((err, i) => (
                                    <div key={i} style={{ color: '#ff4d4f', fontSize: 12 }}>
                                      <WarningOutlined style={{ marginRight: 4 }} /> {err}
                                    </div>
                                  ))}
                                </div>
                              )}

                              {/* Validation warnings */}
                              {req.steps?.validation?.warnings?.length > 0 && (
                                <div style={{ marginTop: 4, marginLeft: 22 }}>
                                  {req.steps.validation.warnings.map((w, i) => (
                                    <div key={i} style={{ color: '#faad14', fontSize: 12 }}>
                                      <ExclamationCircleOutlined style={{ marginRight: 4 }} /> {w}
                                    </div>
                                  ))}
                                </div>
                              )}

                              {/* ServiceNow ticket info */}
                              {req.steps?.servicenow_ticket?.ticket_number && (
                                <div style={{ marginTop: 6, marginLeft: 22 }}>
                                  <Text type="secondary" style={{ fontSize: 12 }}>
                                    ServiceNow Ticket: <Tag color="purple" style={{ borderRadius: 8 }}>{req.steps.servicenow_ticket.ticket_number}</Tag>
                                    <Tag color="orange" style={{ borderRadius: 8 }}>Awaiting Manual Approval</Tag>
                                  </Text>
                                </div>
                              )}

                              {/* Note about manual approval */}
                              {req.note && (
                                <div style={{ marginTop: 6, marginLeft: 22 }}>
                                  <Text type="secondary" style={{ fontSize: 11, fontStyle: 'italic' }}>{req.note}</Text>
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </>
                    )}
                  </Card>
                )}

                <Card
                  title={
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Space>
                        <span style={{ fontWeight: 600, fontSize: 16 }}>Account Creation Requests</span>
                        <Tag color={accountRequests.length > 0 ? 'success' : 'default'} style={{ borderRadius: 12 }}>
                          {accountLoading ? 'Loading...' : `${accountRequests.length} Requests`}
                        </Tag>
                        {accountRequests.filter(r => r.status === 'PENDING').length > 0 && (
                          <Tag color="orange" style={{ borderRadius: 12 }}>
                            {accountRequests.filter(r => r.status === 'PENDING').length} Pending
                          </Tag>
                        )}
                      </Space>
                      <Space>
                        <Tooltip title="Fetch PENDING requests from Salesforce, validate, create ServiceNow tickets, and accept accounts">
                          <Button
                            icon={<ThunderboltOutlined />}
                            onClick={runOrchestration}
                            loading={orchestrating}
                            disabled={accountRequests.filter(r => r.status === 'PENDING').length === 0 && !orchestrating}
                            style={{
                              borderRadius: 8,
                              background: '#722ed1',
                              borderColor: '#722ed1',
                              color: '#fff'
                            }}
                          >
                            {orchestrating ? 'Validating...' : 'Validate & Send to ServiceNow'}
                          </Button>
                        </Tooltip>
                        <Button icon={<ReloadOutlined />} onClick={fetchAccountRequests} loading={accountLoading} type="primary" style={{ borderRadius: 8 }}>
                          Refresh
                        </Button>
                      </Space>
                    </div>
                  }
                  className="animate-fade-in-up"
                  style={{ borderRadius: 12 }}
                >
                  {accountLoading ? (
                    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 200 }}>
                      <Spin size="large" />
                      <span style={{ marginLeft: 16 }}>Loading account requests from Salesforce...</span>
                    </div>
                  ) : accountRequests.length > 0 ? (
                    <Table
                      dataSource={accountRequests.map((req, idx) => ({ ...req, key: `req-${idx}` }))}
                      columns={accountColumns}
                      expandable={{
                        expandedRowRender: (record) => (
                          <div style={{ padding: '12px 24px', background: '#fafafa' }}>
                            <JsonDisplay data={record} title={`Account Request #${record.id} - ${record.name}`} />
                          </div>
                        ),
                        expandRowByClick: true
                      }}
                      pagination={{ pageSize: 10, showTotal: (total, range) => `${range[0]}-${range[1]} of ${total} requests` }}
                      size="middle"
                      scroll={{ x: 1200 }}
                      style={{ background: '#ffffff', borderRadius: 8 }}
                    />
                  ) : (
                    <div style={{ textAlign: 'center', padding: '60px 0', color: '#8c8c8c' }}>
                      <FileProtectOutlined style={{ fontSize: 48, color: '#bfbfbf', marginBottom: 16 }} />
                      <h3 style={{ color: '#595959' }}>No Account Requests Found</h3>
                      <Paragraph style={{ color: '#8c8c8c', maxWidth: 500, margin: '0 auto' }}>
                        No account creation requests from Salesforce. When users create accounts in the Salesforce app, pending requests will appear here.
                      </Paragraph>
                      <Button type="primary" icon={<ReloadOutlined />} onClick={fetchAccountRequests} style={{ marginTop: 16, borderRadius: 8 }}>Refresh</Button>
                    </div>
                  )}
                </Card>
              </>
            )
          }
        ]}
      />

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

      {/* ServiceNow Send Modal */}
      <Modal
        title={
          <Space>
            <CloudUploadOutlined style={{ color: '#81B5A1' }} />
            <span>Send to ServiceNow - Ticket & Approval</span>
          </Space>
        }
        open={snowModal.visible}
        onCancel={() => {
          setSnowModal({ visible: false, caseData: null, loading: false });
          setSnowResult(null);
          setSnowPreview({ ticket: null, approval: null });
        }}
        width={900}
        footer={[
          <Button key="cancel" onClick={() => setSnowModal({ visible: false, caseData: null, loading: false })}>
            Cancel
          </Button>,
          <Button
            key="send"
            style={{ background: '#81B5A1', borderColor: '#81B5A1' }}
            type="primary"
            icon={<SendOutlined />}
            loading={snowModal.loading}
            onClick={executeSendTicketToServiceNow}
            disabled={snowResult?.ticket?.success && snowResult?.approval?.success}
          >
            {snowResult?.ticket?.success ? 'Sent Successfully' : 'Send Ticket & Approval'}
          </Button>
        ]}
      >
        {snowModal.caseData && (
          <Tabs defaultActiveKey="ticket-preview">
            <TabPane tab="Ticket Preview" key="ticket-preview">
              <div style={{ marginBottom: 16 }}>
                <Text strong>Target: </Text>
                <Text code>POST http://149.102.158.71:4780/api/tickets</Text>
              </div>
              <div style={{ marginBottom: 16 }}>
                <Text strong>Source Case: </Text>
                <Tag color="blue">{snowModal.caseData.id}</Tag>
                <Text>{snowModal.caseData.subject}</Text>
              </div>
              {snowModal.loading ? (
                <div style={{ textAlign: 'center', padding: 40 }}>
                  <Spin /> Generating ticket preview...
                </div>
              ) : snowPreview.ticket ? (
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
                  {JSON.stringify(snowPreview.ticket, null, 2)}
                </pre>
              ) : (
                <Text type="secondary">Preview not available</Text>
              )}
            </TabPane>

            <TabPane tab="Approval Preview" key="approval-preview">
              <div style={{ marginBottom: 16 }}>
                <Text strong>Target: </Text>
                <Text code>POST http://149.102.158.71:4780/api/approvals</Text>
              </div>
              <div style={{ marginBottom: 16 }}>
                <Text strong>Approval Type: </Text>
                <Tag color="green">User Account Creation</Tag>
              </div>
              {snowModal.loading ? (
                <div style={{ textAlign: 'center', padding: 40 }}>
                  <Spin /> Generating approval preview...
                </div>
              ) : snowPreview.approval ? (
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
                  {JSON.stringify(snowPreview.approval, null, 2)}
                </pre>
              ) : (
                <Text type="secondary">Preview not available</Text>
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
                {JSON.stringify(snowModal.caseData, null, 2)}
              </pre>
            </TabPane>

            {snowResult && (
              <TabPane tab="ServiceNow Response" key="response">
                {/* Ticket Result */}
                <div style={{ marginBottom: 16 }}>
                  <Text strong style={{ fontSize: 14 }}>Ticket Result:</Text>
                  <Alert
                    message={snowResult.ticket?.success ? 'Ticket Created' : 'Ticket Failed'}
                    description={snowResult.ticket?.success
                      ? `Ticket ${snowResult.ticket.ticket_number || snowResult.ticket.response?.ticket_number || ''} created successfully`
                      : (snowResult.ticket?.error || 'Failed to create ticket')}
                    type={snowResult.ticket?.success ? 'success' : 'error'}
                    showIcon
                    style={{ marginTop: 8, marginBottom: 12 }}
                  />
                  {snowResult.ticket?.response && (
                    <pre style={{
                      background: '#f6f8fa',
                      padding: 12,
                      borderRadius: 8,
                      overflow: 'auto',
                      maxHeight: 200,
                      fontSize: 12,
                      marginBottom: 16
                    }}>
                      {JSON.stringify(snowResult.ticket.response, null, 2)}
                    </pre>
                  )}
                </div>

                {/* Approval Result */}
                <div>
                  <Text strong style={{ fontSize: 14 }}>Approval Result:</Text>
                  <Alert
                    message={snowResult.approval?.success ? 'Approval Created' : 'Approval Failed'}
                    description={snowResult.approval?.success
                      ? `Approval ${snowResult.approval.approval_id || snowResult.approval.response?.approval_id || ''} created successfully`
                      : (snowResult.approval?.error || 'Failed to create approval')}
                    type={snowResult.approval?.success ? 'success' : 'error'}
                    showIcon
                    style={{ marginTop: 8 }}
                  />
                  {snowResult.approval?.response && (
                    <pre style={{
                      background: '#f6f8fa',
                      padding: 12,
                      borderRadius: 8,
                      overflow: 'auto',
                      maxHeight: 200,
                      fontSize: 12,
                      marginTop: 8
                    }}>
                      {JSON.stringify(snowResult.approval.response, null, 2)}
                    </pre>
                  )}
                </div>
              </TabPane>
            )}
          </Tabs>
        )}
      </Modal>
    </div>
  );
}