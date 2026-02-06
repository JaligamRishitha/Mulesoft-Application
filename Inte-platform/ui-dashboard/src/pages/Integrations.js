import React, { useState, useEffect } from 'react';
import { Card, Table, Tag, Spin, Alert, Typography, Space, Button, Tooltip, Modal, Tabs, message } from 'antd';
import {
  WarningOutlined,
  ReloadOutlined,
  EyeOutlined,
  FileSearchOutlined,
  UserAddOutlined,
  SyncOutlined,
  KeyOutlined,
  SafetyOutlined
} from '@ant-design/icons';
import { backendApi as api } from '../api';
import { JsonDisplay, CaseStatus, CasePriority, IntegrationStatusTag, CaseExpandedRow } from '../components/IntegrationComponents';

const { Text, Paragraph } = Typography;

export default function Integrations() {
  const [platformEvents, setPlatformEvents] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [expandedRows, setExpandedRows] = useState([]);
  const [sfConnector, setSfConnector] = useState(null);

  const [sapModal, setSapModal] = useState({ visible: false, caseData: null, loading: false });
  const [xmlPreview, setXmlPreview] = useState('');
  const [snowModal, setSnowModal] = useState({ visible: false, caseData: null, loading: false });
  const [snowPreview, setSnowPreview] = useState({ ticket: null, approval: null });
  const [passwordResetModal, setPasswordResetModal] = useState({ visible: false, ticketData: null, loading: false });
  const [passwordResetPreview, setPasswordResetPreview] = useState(null);

  const fetchSalesforceConnector = async () => {
    try {
      const { data } = await api.get('/connectors');
      const connector = data.find(c => c.connector_type === 'salesforce');
      if (connector) {
        setSfConnector(connector);
        const detail = await api.get(`/connectors/${connector.id}`);
        setSfConnector(detail.data);
        return detail.data;
      }
    } catch (err) {
      console.error('Error fetching Salesforce connector:', err);
    }
    return null;
  };

  const fetchAllPlatformEvents = async () => {
    setLoading(true);
    setError(null);
    try {
      let connector = sfConnector;
      if (!connector) connector = await fetchSalesforceConnector();

      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 15000);

      // Fetch Salesforce events and ServiceNow Password Reset tickets in parallel
      const [casesResponse, accountsResponse, passwordResetResponse] = await Promise.all([
        connector ? api.get(`/cases/external/cases?connector_id=${connector.id}`, { signal: controller.signal, timeout: 10000 }).catch(() => ({ data: { status: 'error', cases: [] } })) : Promise.resolve({ data: { status: 'error', cases: [] } }),
        connector ? api.get(`/cases/external/account-requests?connector_id=${connector.id}`, { timeout: 15000 }).catch(() => ({ data: { status: 'error', requests: [] } })) : Promise.resolve({ data: { status: 'error', requests: [] } }),
        api.get('/password-reset/tickets', { timeout: 15000 }).catch(() => ({ data: { status: 'error', tickets: [] } }))
      ]);
      clearTimeout(timeoutId);

      console.log('Cases Response:', casesResponse.data);
      console.log('Accounts Response:', accountsResponse.data);
      console.log('Password Reset Response:', passwordResetResponse.data);

      const events = [];
      if (casesResponse.data.status === 'success') {
        const cases = casesResponse.data.cases.items || casesResponse.data.cases || [];
        cases.forEach((caseItem, index) => {
          events.push({
            key: `case-${index}`, id: caseItem.id || `case-${index}`, name: caseItem.subject || 'No Subject',
            platformEvent: 'Case_Update__e', eventType: 'case', status: caseItem.status || 'New',
            priority: caseItem.priority || 'Medium', integrationStatus: null, servicenowStatus: null,
            createdDate: caseItem.createdDate || new Date().toISOString(), originalData: caseItem
          });
        });
      }
      if (accountsResponse.data.status === 'success') {
        const requests = accountsResponse.data.requests || [];
        requests.forEach((req, index) => {
          events.push({
            key: `account-${index}`, id: req.id, name: req.name || 'Unknown Account',
            platformEvent: 'Account_Creation__e', eventType: 'account', status: req.status || 'PENDING',
            priority: null, integrationStatus: req.integration_status, servicenowStatus: req.servicenow_status,
            servicenowTicketId: req.servicenow_ticket_id, mulesoftTransactionId: req.mulesoft_transaction_id,
            createdDate: req.created_at || new Date().toISOString(), originalData: req
          });
        });
      }
      // Add ServiceNow Password Reset tickets
      const passwordResetTickets = Array.isArray(passwordResetResponse.data?.tickets)
        ? passwordResetResponse.data.tickets
        : [];
      if (passwordResetTickets.length > 0 || passwordResetResponse.data?.status === 'success') {
        const tickets = passwordResetTickets;
        tickets.forEach((ticket, index) => {
          events.push({
            key: `password-reset-${index}`,
            id: ticket.servicenow_ticket_id || ticket.correlation_id || `pwd-${index}`,
            name: ticket.title || `Password Reset - ${ticket.user_name || ticket.affected_user || 'User'}`,
            platformEvent: 'Password_Reset_e',
            eventType: 'password_reset',
            status: ticket.status || 'pending',
            priority: ticket.priority || 'medium',
            integrationStatus: ticket.status,
            servicenowStatus: ticket.sap_status,
            servicenowTicketId: ticket.servicenow_ticket_id,
            sapTicketId: ticket.sap_ticket_id,
            correlationId: ticket.correlation_id,
            createdDate: ticket.created_at || new Date().toISOString(),
            originalData: ticket
          });
        });
      }
      events.sort((a, b) => new Date(b.createdDate) - new Date(a.createdDate));
      setPlatformEvents(events);
    } catch (error) {
      console.error('Error fetching platform events:', error);
      setError(error.message || 'Failed to connect to the remote server');
      setPlatformEvents([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchSalesforceConnector(); }, []);

  const testPasswordResetHealth = async () => {
    try {
      const response = await api.get('/password-reset/health', { timeout: 10000 });
      if (response.data?.status === 'healthy' || response.data?.status === 'ok' || response.data?.success) {
        message.success('Password reset flow is healthy.');
      } else {
        message.warning(response.data?.message || 'Password reset health check returned a warning.');
      }
    } catch (err) {
      message.error('Password reset health check failed.');
    }
  };

  const handleRowExpand = (expanded, record) => {
    if (expanded) setExpandedRows([...expandedRows, record.key]);
    else setExpandedRows(expandedRows.filter(key => key !== record.key));
  };

  const handlePreviewSAP = async (record) => {
    const caseData = record.originalData;
    setSapModal({ visible: true, caseData, loading: true });
    const transformData = record.eventType === 'case' ? {
      caseId: caseData.id, caseNumber: caseData.caseNumber || `CASE-${caseData.id}`, subject: caseData.subject,
      description: caseData.description, status: caseData.status, priority: caseData.priority,
      account: caseData.account || { id: caseData.accountId, name: caseData.accountName },
      contact: caseData.contact || { id: caseData.contactId, name: caseData.contactName },
      currentLoad: caseData.currentLoad || 5, requestedLoad: caseData.requestedLoad || 10,
      connectionType: caseData.priority === 'High' || caseData.priority === 'Critical' ? 'COMMERCIAL' : 'RESIDENTIAL',
      city: caseData.city || 'Hyderabad', pinCode: caseData.pinCode || '500001'
    } : {
      accountId: caseData.id, accountName: caseData.name, accountType: caseData.type || 'Customer',
      industry: caseData.industry || 'General', status: caseData.status, requestType: 'ACCOUNT_CREATION',
      connectionType: 'BUSINESS', city: caseData.city || 'Hyderabad', pinCode: caseData.pinCode || '500001'
    };
    try {
      const previewResponse = await api.post('/sap/preview-xml', transformData);
      setXmlPreview(previewResponse.data.xml);
    } catch (err) { setXmlPreview('Error generating XML preview'); }
    setSapModal(prev => ({ ...prev, loading: false }));
  };

  const handlePreviewServiceNow = async (record) => {
    const caseData = record.originalData;
    setSnowModal({ visible: true, caseData, loading: true, eventType: record.eventType, platformEvent: record.platformEvent });
    const transformData = record.eventType === 'case' ? {
      id: caseData.id, caseId: caseData.id, caseNumber: caseData.caseNumber || `CASE-${caseData.id}`,
      subject: caseData.subject, description: caseData.description, status: caseData.status, priority: caseData.priority,
      account: caseData.account || { id: caseData.accountId, name: caseData.accountName },
      contact: caseData.contact || { id: caseData.contactId, name: caseData.contactName },
      userName: caseData.userName || '', userEmail: caseData.userEmail || '', userRole: caseData.userRole || 'Standard User',
      department: caseData.department || '', category: caseData.category || 'User Account',
      createdDate: caseData.createdDate || new Date().toISOString()
    } : {
      id: caseData.id, accountName: caseData.name, accountType: caseData.type || 'Customer',
      industry: caseData.industry || 'General', status: caseData.status, requestType: 'account_creation',
      category: 'Account Management', createdDate: caseData.created_at || new Date().toISOString()
    };
    try {
      const ticketType = record.eventType === 'case' ? 'incident' : 'request';
      const approvalType = record.eventType === 'case' ? 'user_account' : 'account_creation';
      const [ticketPreview, approvalPreview] = await Promise.all([
        api.post('/servicenow/preview-ticket', transformData, { params: { ticket_type: ticketType } }),
        api.post('/servicenow/preview-approval', transformData, { params: { approval_type: approvalType } })
      ]);
      setSnowPreview({ ticket: ticketPreview.data.ticket_payload, approval: approvalPreview.data.approval_payload });
    } catch (err) { setSnowPreview({ ticket: null, approval: null }); }
    setSnowModal(prev => ({ ...prev, loading: false }));
  };

  const handlePreviewPasswordReset = async (record) => {
    const ticketData = record.originalData;
    setPasswordResetModal({ visible: true, ticketData, loading: true });
    try {
      // Create a preview payload for SAP - transform the ServiceNow ticket data
      const previewPayload = {
        requestId: `PWD-${ticketData.servicenow_ticket_id || ticketData.correlation_id || 'UNKNOWN'}`,
        requestType: 'PASSWORD_RESET',
        userId: ticketData.affected_user || ticketData.user_id || '',
        userEmail: ticketData.user_email || '',
        userName: ticketData.user_name || ticketData.title?.replace('Password Reset - ', '') || '',
        department: ticketData.department || '',
        priority: ticketData.priority || 'medium',
        urgency: ticketData.urgency || 'medium',
        category: 'Identity Management',
        subcategory: 'Password Reset',
        source: 'ServiceNow',
        ticketNumber: ticketData.servicenow_ticket_id || '',
        ticketId: ticketData.id || '',
        status: ticketData.status || 'pending',
        createdAt: ticketData.created_at || new Date().toISOString(),
        description: ticketData.description || '',
        correlationId: ticketData.correlation_id || `SNOW-${ticketData.servicenow_ticket_id || 'UNKNOWN'}`
      };
      setPasswordResetPreview(previewPayload);
    } catch (err) {
      console.error('Error previewing password reset:', err);
      setPasswordResetPreview(null);
    }
    setPasswordResetModal(prev => ({ ...prev, loading: false }));
  };

  const PlatformEventTag = ({ event }) => {
    if (event === 'Account_Creation__e') return <Tag icon={<UserAddOutlined />} color="purple" style={{ borderRadius: 8, fontWeight: 500 }}>Account_Creation__e</Tag>;
    if (event === 'Password_Reset_e') return <Tag icon={<KeyOutlined />} color="orange" style={{ borderRadius: 8, fontWeight: 500 }}>Password_Reset_e</Tag>;
    return <Tag icon={<SyncOutlined />} color="blue" style={{ borderRadius: 8, fontWeight: 500 }}>Case_Update__e</Tag>;
  };

  const PasswordResetStatusTag = ({ status }) => {
    const statusConfig = {
      pending: { color: 'orange', text: 'Pending' },
      processing: { color: 'blue', text: 'Processing' },
      completed: { color: 'green', text: 'Completed' },
      failed: { color: 'red', text: 'Failed' }
    };
    const config = statusConfig[status?.toLowerCase()] || statusConfig.pending;
    return <Tag color={config.color} style={{ borderRadius: 12 }}>{config.text}</Tag>;
  };

  const columns = [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 100, render: (id) => <Text code style={{ fontWeight: 600, color: '#1890ff', fontSize: 13 }}>{id}</Text> },
    { title: 'Platform Event', dataIndex: 'platformEvent', key: 'platformEvent', width: 180, filters: [{ text: 'Case_Update__e', value: 'Case_Update__e' }, { text: 'Account_Creation__e', value: 'Account_Creation__e' }, { text: 'Password_Reset_e', value: 'Password_Reset_e' }], onFilter: (value, record) => record.platformEvent === value, render: (event) => <PlatformEventTag event={event} /> },
    { title: 'Name / Subject', dataIndex: 'name', key: 'name', ellipsis: true, render: (name) => <Tooltip title={name}><Text strong style={{ color: '#262626' }}>{name || 'No Name'}</Text></Tooltip> },
    { title: 'Status', dataIndex: 'status', key: 'status', width: 130, render: (status, record) => record.eventType === 'case' ? <CaseStatus status={status} /> : record.eventType === 'password_reset' ? <PasswordResetStatusTag status={status} /> : record.integrationStatus ? <IntegrationStatusTag status={record.integrationStatus} servicenowStatus={record.servicenowStatus} /> : <Tag color="orange" style={{ borderRadius: 12 }}>{status}</Tag> },
    { title: 'Created Date', dataIndex: 'createdDate', key: 'createdDate', width: 140, sorter: (a, b) => new Date(a.createdDate) - new Date(b.createdDate), render: (date) => <Text style={{ fontSize: 12, color: '#8c8c8c' }}>{date ? new Date(date).toLocaleString() : 'N/A'}</Text> },
    { title: 'Preview', key: 'actions', width: 280, render: (_, record) => (
      <Space>
        <Tooltip title="View JSON Payload"><Button type="text" icon={<EyeOutlined />} size="small" onClick={() => { const isExpanded = expandedRows.includes(record.key); handleRowExpand(!isExpanded, record); }} style={{ color: expandedRows.includes(record.key) ? '#1890ff' : '#8c8c8c' }} /></Tooltip>
        {record.eventType === 'password_reset' ? (
          <Tooltip title="Preview SAP Password Reset Payload"><Button icon={<SafetyOutlined />} size="small" onClick={() => handlePreviewPasswordReset(record)} style={{ borderRadius: 6, background: '#fff7e6', borderColor: '#ffd591', color: '#fa8c16' }}>Preview SAP</Button></Tooltip>
        ) : (
          <>
            <Tooltip title="Preview SAP XML"><Button icon={<FileSearchOutlined />} size="small" onClick={() => handlePreviewSAP(record)} style={{ borderRadius: 6 }}>Preview SAP</Button></Tooltip>
            <Tooltip title="Preview ServiceNow Payload"><Button icon={<FileSearchOutlined />} size="small" onClick={() => handlePreviewServiceNow(record)} style={{ borderRadius: 6, background: '#f0f5ff', borderColor: '#adc6ff', color: '#2f54eb' }}>Preview SNOW</Button></Tooltip>
          </>
        )}
      </Space>
    )}
  ];

  const expandedRowRender = (record) => {
    if (record.eventType === 'case') return <CaseExpandedRow record={record} sfConnector={sfConnector} />;
    if (record.eventType === 'password_reset') {
      const ticketData = record.originalData;
      const fullPayload = {
        eventType: "Password_Reset_e",
        eventId: `password-reset-${ticketData.correlation_id || ticketData.servicenow_ticket_id}-${Date.now()}`,
        eventTime: new Date().toISOString(),
        source: "ServiceNow via MuleSoft",
        data: {
          correlationId: ticketData.correlation_id,
          servicenowTicketId: ticketData.servicenow_ticket_id,
          sapTicketId: ticketData.sap_ticket_id,
          userName: ticketData.user_name || ticketData.affected_user,
          userEmail: ticketData.user_email,
          department: ticketData.department,
          status: ticketData.status,
          sapStatus: ticketData.sap_status,
          servicenowUpdated: ticketData.servicenow_updated,
          priority: ticketData.priority,
          createdAt: ticketData.created_at
        },
        metadata: {
          syncedAt: new Date().toISOString(),
          source: "MuleSoft Integration Platform",
          version: "1.0",
          connector: "ServiceNow + SAP IDM",
          dataFormat: "platform-event"
        }
      };
      return (
        <div style={{ padding: '16px 24px', background: '#fffbe6' }}>
          <Space style={{ marginBottom: 16 }}>
            <Tag icon={<KeyOutlined />} color="orange" style={{ borderRadius: 8 }}>Password_Reset_e</Tag>
            {ticketData.servicenow_ticket_id && <Tag color="geekblue" style={{ borderRadius: 8 }}>ServiceNow: {ticketData.servicenow_ticket_id}</Tag>}
            {ticketData.sap_ticket_id && <Tag color="green" style={{ borderRadius: 8 }}>SAP: {ticketData.sap_ticket_id}</Tag>}
            {ticketData.correlation_id && <Tag color="cyan" style={{ borderRadius: 8 }}>Correlation: {ticketData.correlation_id}</Tag>}
          </Space>
          <JsonDisplay data={fullPayload} title="Password Reset Platform Event" />
          <div style={{ marginTop: 16 }}><JsonDisplay data={ticketData} title="Original ServiceNow Ticket Data" /></div>
        </div>
      );
    }
    const accountData = record.originalData;
    const fullPayload = { eventType: "Account_Creation__e", eventId: `account-creation-${accountData.id}-${Date.now()}`, eventTime: new Date().toISOString(), source: "External Salesforce Application", data: { requestId: accountData.id, accountName: accountData.name, accountType: accountData.type || 'Customer', industry: accountData.industry || 'General', status: accountData.status, integrationStatus: accountData.integration_status, servicenowTicketId: accountData.servicenow_ticket_id, servicenowStatus: accountData.servicenow_status, mulesoftTransactionId: accountData.mulesoft_transaction_id, createdAccountId: accountData.created_account_id, createdAt: accountData.created_at }, metadata: { syncedAt: new Date().toISOString(), source: "MuleSoft Integration Platform", version: "1.0", connector: "External Salesforce App", dataFormat: "platform-event", externalAppUrl: sfConnector?.config?.server_url || "not-configured" } };
    return (
      <div style={{ padding: '16px 24px', background: '#fafafa' }}>
        <Space style={{ marginBottom: 16 }}>
          <Tag icon={<UserAddOutlined />} color="purple" style={{ borderRadius: 8 }}>Account_Creation__e</Tag>
          {accountData.servicenow_ticket_id && <Tag color="geekblue" style={{ borderRadius: 8 }}>ServiceNow: {accountData.servicenow_ticket_id}</Tag>}
          {accountData.mulesoft_transaction_id && <Tag color="cyan" style={{ borderRadius: 8 }}>MuleSoft TX: {accountData.mulesoft_transaction_id}</Tag>}
        </Space>
        <JsonDisplay data={fullPayload} title="Account Creation Platform Event" />
        <div style={{ marginTop: 16 }}><JsonDisplay data={accountData} title="Original Account Request Data" /></div>
      </div>
    );
  };

  const casesCount = platformEvents.filter(e => e.eventType === 'case').length;
  const accountsCount = platformEvents.filter(e => e.eventType === 'account').length;
  const passwordResetCount = platformEvents.filter(e => e.eventType === 'password_reset').length;

  return (
    <div className="animate-fade-in">
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ marginBottom: 4, color: '#262626' }}>Integration Designer</h2>
        <p style={{ color: '#8c8c8c', margin: 0 }}>Preview mode - View Platform Events (Salesforce, ServiceNow) and preview integration payloads (SAP, ServiceNow)</p>
      </div>
      <Alert message="Preview Mode - Platform Events" description="This is the Integration Designer - preview payloads and data transformations for all Salesforce Platform Events. To send data to SAP or ServiceNow, use the Runtime Manager." type="info" showIcon icon={<EyeOutlined />} style={{ marginBottom: 16, borderRadius: 8 }} />
      {error && <Alert message="Connection Error" description={error} type="error" showIcon style={{ marginBottom: 16, borderRadius: 8 }} action={<Button size="small" onClick={fetchAllPlatformEvents}>Retry</Button>} />}
      <Card title={<div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}><Space><span style={{ fontWeight: 600, fontSize: 16 }}>Platform Events</span><Tag color="blue" style={{ borderRadius: 12 }}>{casesCount} Cases</Tag><Tag color="purple" style={{ borderRadius: 12 }}>{accountsCount} Account Requests</Tag><Tag color="orange" style={{ borderRadius: 12 }}>{passwordResetCount} Password Reset</Tag><Tag color={platformEvents.length > 0 ? 'success' : 'default'} style={{ borderRadius: 12 }}>{loading ? 'Loading...' : `${platformEvents.length} Total`}</Tag></Space><Space><Button icon={<SafetyOutlined />} onClick={testPasswordResetHealth} style={{ borderRadius: 8, background: '#fff7e6', borderColor: '#ffd591', color: '#fa8c16' }}>Password Reset Health</Button><Button icon={<ReloadOutlined />} onClick={fetchAllPlatformEvents} loading={loading} type="primary" style={{ borderRadius: 8 }}>Refresh</Button></Space></div>} className="animate-fade-in-up" style={{ borderRadius: 12 }}>
        {loading ? <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 200 }}><Spin size="large" /><span style={{ marginLeft: 16 }}>Loading Salesforce Platform Events...</span></div> : platformEvents.length > 0 ? (
          <Table dataSource={platformEvents} columns={columns} expandable={{ expandedRowRender, expandRowByClick: true, expandedRowKeys: expandedRows, onExpand: handleRowExpand, expandIcon: () => null }} pagination={{ pageSize: 10, showSizeChanger: true, showTotal: (total, range) => `${range[0]}-${range[1]} of ${total} events` }} size="middle" scroll={{ x: 1100 }} style={{ background: '#ffffff', borderRadius: 8 }} />
        ) : (
          <div style={{ textAlign: 'center', padding: '60px 0', color: '#8c8c8c' }}><WarningOutlined style={{ fontSize: 48, color: '#ff4d4f', marginBottom: 16 }} /><h3 style={{ color: '#595959' }}>No Platform Events Found</h3><Paragraph style={{ color: '#8c8c8c', maxWidth: 500, margin: '0 auto' }}>{sfConnector?.config?.server_url ? <>Click Refresh to load events from <Text code>{sfConnector.config.server_url}</Text></> : <>No Salesforce connector configured. Please create one in the <Text strong>Connectors</Text> page.</>}</Paragraph><Button type="primary" icon={<ReloadOutlined />} onClick={fetchAllPlatformEvents} style={{ marginTop: 16, borderRadius: 8 }}>Load Events</Button></div>
        )}
      </Card>

      <Modal title={<Space><FileSearchOutlined style={{ color: '#1890ff' }} /><span>Preview SAP XML</span></Space>} open={sapModal.visible} onCancel={() => { setSapModal({ visible: false, caseData: null, loading: false }); setXmlPreview(''); }} width={900} footer={[<Button key="close" type="primary" onClick={() => setSapModal({ visible: false, caseData: null, loading: false })}>Close</Button>]}>
        {sapModal.caseData && (
          <Tabs defaultActiveKey="preview" items={[
            { key: 'preview', label: 'XML Preview', children: (<><Alert message="Preview Mode" description="This is a preview only. To send to SAP, use the Runtime Manager." type="warning" showIcon style={{ marginBottom: 16 }} /><div style={{ marginBottom: 16 }}><Text strong>Target Endpoint: </Text><Text code>POST http://localhost:2004/api/integration/mulesoft/load-request/xml</Text></div><div style={{ marginBottom: 16 }}><Text strong>Source: </Text><Tag color="blue">{sapModal.caseData.id || sapModal.caseData.name}</Tag><Text>{sapModal.caseData.subject || sapModal.caseData.name}</Text></div>{sapModal.loading ? <div style={{ textAlign: 'center', padding: 40 }}><Spin /> Generating XML...</div> : <pre style={{ background: '#1e1e1e', color: '#d4d4d4', padding: 16, borderRadius: 8, overflow: 'auto', maxHeight: 400, fontSize: 12, fontFamily: 'Monaco, Menlo, monospace' }}>{xmlPreview}</pre>}</>) },
            { key: 'source', label: 'Source Data', children: <pre style={{ background: '#f6f8fa', padding: 16, borderRadius: 8, overflow: 'auto', maxHeight: 400, fontSize: 12 }}>{JSON.stringify(sapModal.caseData, null, 2)}</pre> }
          ]} />
        )}
      </Modal>

      <Modal title={<Space><FileSearchOutlined style={{ color: '#2f54eb' }} /><span>Preview ServiceNow Payloads</span>{snowModal.platformEvent && <Tag color={snowModal.eventType === 'account' ? 'purple' : 'blue'} style={{ borderRadius: 8 }}>{snowModal.platformEvent}</Tag>}</Space>} open={snowModal.visible} onCancel={() => { setSnowModal({ visible: false, caseData: null, loading: false }); setSnowPreview({ ticket: null, approval: null }); }} width={900} footer={[<Button key="close" type="primary" onClick={() => setSnowModal({ visible: false, caseData: null, loading: false })}>Close</Button>]}>
        {snowModal.caseData && (<><Alert message="Preview Mode" description="This is a preview only. To send to ServiceNow, use the Runtime Manager." type="warning" showIcon style={{ marginBottom: 16 }} />
          <Tabs defaultActiveKey="ticket-preview" items={[
            { key: 'ticket-preview', label: snowModal.eventType === 'account' ? 'Request Preview' : 'Ticket Preview', children: (<><div style={{ marginBottom: 16 }}><Text strong>Target: </Text><Text code>POST http://149.102.158.71:4780/api/tickets</Text></div><div style={{ marginBottom: 16 }}><Text strong>Source: </Text><Tag color="blue">{snowModal.caseData.id || snowModal.caseData.name}</Tag><Text>{snowModal.caseData.subject || snowModal.caseData.name}</Text></div>{snowModal.loading ? <div style={{ textAlign: 'center', padding: 40 }}><Spin /> Generating preview...</div> : snowPreview.ticket ? <pre style={{ background: '#1e1e1e', color: '#d4d4d4', padding: 16, borderRadius: 8, overflow: 'auto', maxHeight: 350, fontSize: 12, fontFamily: 'Monaco, Menlo, monospace' }}>{JSON.stringify(snowPreview.ticket, null, 2)}</pre> : <Text type="secondary">Preview not available</Text>}</>) },
            { key: 'approval-preview', label: 'Approval Preview', children: (<><div style={{ marginBottom: 16 }}><Text strong>Target: </Text><Text code>POST http://149.102.158.71:4780/api/approvals</Text></div><div style={{ marginBottom: 16 }}><Text strong>Approval Type: </Text><Tag color="green">{snowModal.eventType === 'account' ? 'Account Creation' : 'User Account'}</Tag></div>{snowModal.loading ? <div style={{ textAlign: 'center', padding: 40 }}><Spin /> Generating approval preview...</div> : snowPreview.approval ? <pre style={{ background: '#1e1e1e', color: '#d4d4d4', padding: 16, borderRadius: 8, overflow: 'auto', maxHeight: 350, fontSize: 12, fontFamily: 'Monaco, Menlo, monospace' }}>{JSON.stringify(snowPreview.approval, null, 2)}</pre> : <Text type="secondary">Preview not available</Text>}</>) },
            { key: 'source', label: 'Source Data', children: <pre style={{ background: '#f6f8fa', padding: 16, borderRadius: 8, overflow: 'auto', maxHeight: 400, fontSize: 12 }}>{JSON.stringify(snowModal.caseData, null, 2)}</pre> }
          ]} /></>)}
      </Modal>

      <Modal title={<Space><SafetyOutlined style={{ color: '#fa8c16' }} /><span>Preview SAP Password Reset Payload</span><Tag color="orange" style={{ borderRadius: 8 }}>Password_Reset_e</Tag></Space>} open={passwordResetModal.visible} onCancel={() => { setPasswordResetModal({ visible: false, ticketData: null, loading: false }); setPasswordResetPreview(null); }} width={900} footer={[<Button key="close" type="primary" onClick={() => setPasswordResetModal({ visible: false, ticketData: null, loading: false })}>Close</Button>]}>
        {passwordResetModal.ticketData && (<><Alert message="Preview Mode" description="This is a preview only. To send to SAP IDM for password reset, use the Runtime Manager." type="warning" showIcon style={{ marginBottom: 16 }} />
          <Tabs defaultActiveKey="sap-preview" items={[
            { key: 'sap-preview', label: 'SAP IDM Payload', children: (<><div style={{ marginBottom: 16 }}><Text strong>Target: </Text><Text code>POST http://localhost:2004/api/integration/mulesoft/password-reset</Text></div><div style={{ marginBottom: 16 }}><Text strong>Source Ticket: </Text><Tag color="orange">{passwordResetModal.ticketData.servicenow_ticket_id || passwordResetModal.ticketData.correlation_id}</Tag><Text>{passwordResetModal.ticketData.title || `Password Reset - ${passwordResetModal.ticketData.user_name || 'User'}`}</Text></div>{passwordResetModal.loading ? <div style={{ textAlign: 'center', padding: 40 }}><Spin /> Generating SAP payload preview...</div> : passwordResetPreview ? <pre style={{ background: '#1e1e1e', color: '#d4d4d4', padding: 16, borderRadius: 8, overflow: 'auto', maxHeight: 350, fontSize: 12, fontFamily: 'Monaco, Menlo, monospace' }}>{JSON.stringify(passwordResetPreview, null, 2)}</pre> : <Text type="secondary">Preview not available</Text>}</>) },
            { key: 'source', label: 'Source Ticket Data', children: <pre style={{ background: '#f6f8fa', padding: 16, borderRadius: 8, overflow: 'auto', maxHeight: 400, fontSize: 12 }}>{JSON.stringify(passwordResetModal.ticketData, null, 2)}</pre> }
          ]} /></>)}
      </Modal>
    </div>
  );
}
