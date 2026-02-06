import React, { useState, useEffect } from 'react';
import { Card, Table, Tag, Spin, Alert, Typography, Space, Button, Tooltip, Modal, message, Tabs, Dropdown } from 'antd';
import {
  WarningOutlined, CheckCircleOutlined, ClockCircleOutlined, ExclamationCircleOutlined, CloseCircleOutlined,
  ReloadOutlined, CodeOutlined, SendOutlined, CloudUploadOutlined, ApiOutlined, ThunderboltOutlined,
  UserAddOutlined, SyncOutlined, FileProtectOutlined, DownOutlined, RocketOutlined, KeyOutlined, SafetyOutlined
} from '@ant-design/icons';
import { backendApi as api } from '../api';
import { JsonDisplay, CaseStatus, IntegrationStatusTag, CaseExpandedRow } from '../components/IntegrationComponents';

const { Text, Paragraph } = Typography;

export default function Runtime() {
  const [platformEvents, setPlatformEvents] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [expandedRows, setExpandedRows] = useState([]);
  const [sfConnector, setSfConnector] = useState(null);
  const [sapModal, setSapModal] = useState({ visible: false, caseData: null, loading: false });
  const [sapResult, setSapResult] = useState(null);
  const [xmlPreview, setXmlPreview] = useState('');
  const [snowModal, setSnowModal] = useState({ visible: false, caseData: null, loading: false });
  const [snowResult, setSnowResult] = useState(null);
  const [snowPreview, setSnowPreview] = useState({ ticket: null, approval: null });
  const [orchestrating, setOrchestrating] = useState(false);
  const [requestStates, setRequestStates] = useState({});
  const [passwordResetModal, setPasswordResetModal] = useState({ visible: false, ticketData: null, loading: false });
  const [passwordResetResult, setPasswordResetResult] = useState(null);
  const [passwordResetPreview, setPasswordResetPreview] = useState(null);

  const fetchSalesforceConnector = async () => {
    try {
      const { data } = await api.get('/connectors');
      const connector = data.find(c => c.connector_type === 'salesforce');
      if (connector) {
        const detail = await api.get(`/connectors/${connector.id}`);
        setSfConnector(detail.data);
        return detail.data;
      }
    } catch (err) { console.error('Error fetching Salesforce connector:', err); }
    return null;
  };

  const fetchAllPlatformEvents = async () => {
    setLoading(true);
    setError(null);
    try {
      let connector = sfConnector;
      if (!connector) connector = await fetchSalesforceConnector();

      // Fetch Salesforce events and ServiceNow Password Reset tickets in parallel
      const [casesResponse, accountsResponse, passwordResetResponse] = await Promise.all([
        connector ? api.get(`/cases/external/cases?connector_id=${connector.id}`, { timeout: 10000 }).catch(() => ({ data: { status: 'error', cases: [] } })) : Promise.resolve({ data: { status: 'error', cases: [] } }),
        connector ? api.get(`/cases/external/account-requests?connector_id=${connector.id}`, { timeout: 15000 }).catch(() => ({ data: { status: 'error', requests: [] } })) : Promise.resolve({ data: { status: 'error', requests: [] } }),
        api.get('/password-reset/tickets', { timeout: 15000 }).catch(() => ({ data: { status: 'error', tickets: [] } }))
      ]);

      console.log('Cases Response:', casesResponse.data);
      console.log('Accounts Response:', accountsResponse.data);
      console.log('Password Reset Response:', passwordResetResponse.data);

      const events = [];
      if (casesResponse.data.status === 'success') {
        (casesResponse.data.cases.items || casesResponse.data.cases || []).forEach((caseItem, index) => {
          events.push({ key: `case-${index}`, id: caseItem.id || `case-${index}`, name: caseItem.subject || 'No Subject', platformEvent: 'Case_Update__e', eventType: 'case', status: caseItem.status || 'New', integrationStatus: null, servicenowStatus: null, servicenowTicketId: null, mulesoftTransactionId: null, createdDate: caseItem.createdDate || new Date().toISOString(), originalData: caseItem });
        });
      }
      if (accountsResponse.data.status === 'success') {
        (accountsResponse.data.requests || []).forEach((req, index) => {
          events.push({ key: `account-${index}`, id: req.id, name: req.name || 'Unknown Account', platformEvent: 'Account_Creation__e', eventType: 'account', status: req.status || 'PENDING', integrationStatus: req.integration_status, servicenowStatus: req.servicenow_status, servicenowTicketId: req.servicenow_ticket_id, mulesoftTransactionId: req.mulesoft_transaction_id, createdAccountId: req.created_account_id, createdDate: req.created_at || new Date().toISOString(), originalData: req });
        });
      }
      // Add ServiceNow Password Reset tickets
      const passwordResetTickets = Array.isArray(passwordResetResponse.data?.platform_events)
        ? passwordResetResponse.data.platform_events
        : Array.isArray(passwordResetResponse.data?.tickets)
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
            mulesoftTransactionId: ticket.correlation_id,
            createdDate: ticket.created_at || new Date().toISOString(),
            originalData: ticket
          });
        });
      }
      events.sort((a, b) => new Date(b.createdDate) - new Date(a.createdDate));
      setPlatformEvents(events);
    } catch (error) {
      setError(error.message || 'Failed to connect');
      setPlatformEvents([]);
    } finally { setLoading(false); }
  };

  useEffect(() => { fetchSalesforceConnector(); }, []);

  const handleRowExpand = (expanded, record) => {
    if (expanded) setExpandedRows([...expandedRows, record.key]);
    else setExpandedRows(expandedRows.filter(key => key !== record.key));
  };

  const handleSendToSAP = async (record) => {
    const caseData = record.originalData;
    setSapModal({ visible: true, caseData, loading: true, eventType: record.eventType });
    setSapResult(null);
    const transformData = record.eventType === 'case' ? { caseId: caseData.id, caseNumber: caseData.caseNumber || `CASE-${caseData.id}`, subject: caseData.subject, description: caseData.description, status: caseData.status, priority: caseData.priority, account: caseData.account || { id: caseData.accountId, name: caseData.accountName }, contact: caseData.contact || { id: caseData.contactId, name: caseData.contactName }, currentLoad: 5, requestedLoad: 10, connectionType: caseData.priority === 'High' || caseData.priority === 'Critical' ? 'COMMERCIAL' : 'RESIDENTIAL', city: 'Hyderabad', pinCode: '500001' } : { accountId: caseData.id, accountName: caseData.name, accountType: caseData.type || 'Customer', industry: caseData.industry || 'General', status: caseData.status, requestType: 'ACCOUNT_CREATION', connectionType: 'BUSINESS', city: 'Hyderabad', pinCode: '500001' };
    try { const previewResponse = await api.post('/sap/preview-xml', transformData); setXmlPreview(previewResponse.data.xml); } catch (err) { setXmlPreview('Error generating XML preview'); }
    setSapModal(prev => ({ ...prev, loading: false }));
  };

  const executeSendToSAP = async () => {
    setSapModal(prev => ({ ...prev, loading: true }));
    const caseData = sapModal.caseData;
    const transformData = sapModal.eventType === 'case' ? { caseId: caseData.id, caseNumber: caseData.caseNumber || `CASE-${caseData.id}`, subject: caseData.subject, description: caseData.description, status: caseData.status, priority: caseData.priority, account: caseData.account || { id: caseData.accountId, name: caseData.accountName }, contact: caseData.contact || { id: caseData.contactId, name: caseData.contactName }, currentLoad: 5, requestedLoad: 10, connectionType: caseData.priority === 'High' || caseData.priority === 'Critical' ? 'COMMERCIAL' : 'RESIDENTIAL', city: 'Hyderabad', pinCode: '500001' } : { accountId: caseData.id, accountName: caseData.name, accountType: caseData.type || 'Customer', industry: caseData.industry || 'General', status: caseData.status, requestType: 'ACCOUNT_CREATION', connectionType: 'BUSINESS', city: 'Hyderabad', pinCode: '500001' };
    try { const response = await api.post('/sap/send-load-request', { case_data: transformData, endpoint_type: 'load_request_xml' }); setSapResult(response.data); if (response.data.success) message.success('Data sent to SAP successfully!'); else message.error(`SAP Error: ${response.data.error || 'Unknown error'}`); } catch (err) { setSapResult({ success: false, error: err.response?.data?.detail || err.message || 'Failed to connect to SAP' }); message.error('Failed to send to SAP'); }
    setSapModal(prev => ({ ...prev, loading: false }));
  };

  const testSAPConnection = async () => { try { const response = await api.get('/sap/test-connection'); if (response.data.success) message.success('SAP connection successful!'); else message.warning(response.data.message || 'SAP not reachable'); } catch (err) { message.error('Cannot connect to SAP'); } };

  const handleSendToServiceNow = async (record) => {
    const caseData = record.originalData;
    setSnowModal({ visible: true, caseData, loading: true, eventType: record.eventType });
    setSnowResult(null);
    const transformData = { id: caseData.id, caseId: caseData.id, caseNumber: caseData.caseNumber || `CASE-${caseData.id}`, subject: caseData.subject, description: caseData.description, status: caseData.status, priority: caseData.priority, account: caseData.account || { id: caseData.accountId, name: caseData.accountName }, contact: caseData.contact || { id: caseData.contactId, name: caseData.contactName }, userName: caseData.userName || '', userEmail: caseData.userEmail || '', userRole: caseData.userRole || 'Standard User', department: caseData.department || '', category: caseData.category || 'User Account', createdDate: caseData.createdDate || new Date().toISOString() };
    try { const ticketPreview = await api.post('/servicenow/preview-ticket', transformData, { params: { ticket_type: 'incident' } }); setSnowPreview({ ticket: ticketPreview.data.ticket_payload, approval: null }); } catch (err) { setSnowPreview({ ticket: null, approval: null }); }
    setSnowModal(prev => ({ ...prev, loading: false }));
  };

  const executeSendTicketToServiceNow = async () => {
    setSnowModal(prev => ({ ...prev, loading: true }));
    const caseData = snowModal.caseData;
    const transformData = { id: caseData.id, caseId: caseData.id, caseNumber: caseData.caseNumber || `CASE-${caseData.id}`, subject: caseData.subject, description: caseData.description, status: caseData.status, priority: caseData.priority, account: caseData.account || { id: caseData.accountId, name: caseData.accountName }, contact: caseData.contact || { id: caseData.contactId, name: caseData.contactName }, userName: caseData.userName || '', userEmail: caseData.userEmail || '', userRole: caseData.userRole || 'Standard User', department: caseData.department || '', category: caseData.category || 'User Account', createdDate: caseData.createdDate || new Date().toISOString() };
    try { const response = await api.post('/servicenow/send-ticket-only', transformData, { params: { ticket_type: 'incident' } }); setSnowResult(response.data); if (response.data.ticket?.success) message.success('Ticket created in ServiceNow successfully!'); else message.error('Failed to create ticket in ServiceNow'); } catch (err) { setSnowResult({ ticket: { success: false, error: err.response?.data?.detail || err.message }, approval: null }); message.error('Failed to send to ServiceNow'); }
    setSnowModal(prev => ({ ...prev, loading: false }));
  };

  const testServiceNowConnection = async () => { try { const response = await api.get('/servicenow/test-connection'); if (response.data.success) message.success('ServiceNow connection successful!'); else message.warning(response.data.message || 'ServiceNow not reachable'); } catch (err) { message.error('Cannot connect to ServiceNow'); } };

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

  const validateSingleRequest = async (record) => {
    const request = record.originalData;
    const requestId = request.id;
    setRequestStates(prev => ({ ...prev, [requestId]: { ...prev[requestId], validating: true, validationResult: null } }));
    try {
      let connector = sfConnector || await fetchSalesforceConnector();
      if (!connector) throw new Error('No Salesforce connector configured.');
      const response = await api.post(`/cases/validate-single-request?connector_id=${connector.id}`, { request_id: requestId, account_name: request.name }, { timeout: 30000 });
      setRequestStates(prev => ({ ...prev, [requestId]: { ...prev[requestId], validating: false, validated: true, validationResult: response.data } }));
      if (response.data.valid) message.success(`Request #${requestId} validated successfully`); else message.warning(`Request #${requestId} validation failed`);
      await fetchAllPlatformEvents();
    } catch (err) {
      setRequestStates(prev => ({ ...prev, [requestId]: { ...prev[requestId], validating: false, validated: false, validationResult: { valid: false, errors: [err.response?.data?.detail || err.message] } } }));
      message.error(`Failed to validate request #${requestId}`);
    }
  };

  const sendSingleToServiceNow = async (record) => {
    const request = record.originalData;
    const requestId = request.id;
    const currentState = requestStates[requestId];
    const integrationStatus = record.integrationStatus?.toUpperCase() || '';
    const isValidatedOnServer = integrationStatus === 'PENDING_MULESOFT' || integrationStatus === 'PENDING_MULE';
    const isValidatedLocally = currentState?.validated && currentState?.validationResult?.valid;
    if (!isValidatedLocally && !isValidatedOnServer) { message.warning('Please validate the request first'); return; }
    setRequestStates(prev => ({ ...prev, [requestId]: { ...prev[requestId], sending: true, sendResult: null } }));
    try {
      let connector = sfConnector || await fetchSalesforceConnector();
      if (!connector) throw new Error('No Salesforce connector configured.');
      const response = await api.post(`/cases/send-single-to-servicenow?connector_id=${connector.id}`, { request_id: requestId, account_name: request.name, request_data: request }, { timeout: 30000 });
      setRequestStates(prev => ({ ...prev, [requestId]: { ...prev[requestId], sending: false, sent: response.data.success, sendResult: response.data } }));
      if (response.data.success) { message.success(`Request #${requestId} sent to ServiceNow successfully`); await fetchAllPlatformEvents(); } else message.error(`Failed to send request #${requestId} to ServiceNow`);
    } catch (err) {
      setRequestStates(prev => ({ ...prev, [requestId]: { ...prev[requestId], sending: false, sent: false, sendResult: { success: false, error: err.response?.data?.detail || err.message } } }));
      message.error(`Failed to send request #${requestId} to ServiceNow`);
    }
  };

  const checkServiceNowStatus = async (record) => {
    const requestId = record.id;
    const ticketId = record.servicenowTicketId;
    if (!ticketId) { message.warning('No ServiceNow ticket found'); return; }
    setRequestStates(prev => ({ ...prev, [requestId]: { ...prev[requestId], checkingStatus: true } }));
    try {
      const response = await api.get(`/servicenow/ticket-status/${ticketId}`, { timeout: 15000 });
      setRequestStates(prev => ({ ...prev, [requestId]: { ...prev[requestId], checkingStatus: false, ticketStatus: response.data } }));
      if (response.data.status === 'approved') message.success(`Ticket ${ticketId} has been APPROVED!`);
      else if (response.data.status === 'rejected') message.error(`Ticket ${ticketId} has been REJECTED`);
      else message.info(`Ticket ${ticketId} status: ${response.data.status}`);
      await fetchAllPlatformEvents();
    } catch (err) {
      setRequestStates(prev => ({ ...prev, [requestId]: { ...prev[requestId], checkingStatus: false, ticketStatus: { status: 'unknown', error: err.message } } }));
      message.error('Failed to check ServiceNow ticket status');
    }
  };

  const runOrchestration = async () => {
    setOrchestrating(true);
    try {
      let connector = sfConnector || await fetchSalesforceConnector();
      if (!connector) throw new Error('No Salesforce connector configured.');
      const response = await api.post(`/cases/orchestrate/account-requests?connector_id=${connector.id}`, null, { timeout: 60000 });
      if (response.data.total_sent_to_servicenow > 0) message.success(`${response.data.total_sent_to_servicenow} requests sent to ServiceNow`);
      else if (response.data.total_fetched === 0) message.info('No pending account requests');
      else message.warning(`Completed with ${response.data.total_failed} failures`);
      await fetchAllPlatformEvents();
    } catch (err) { message.error(err.response?.data?.detail || err.message); }
    finally { setOrchestrating(false); }
  };

  const handleSendPasswordResetToSAP = async (record) => {
    const ticketData = record.originalData;
    setPasswordResetModal({ visible: true, ticketData, loading: true });
    setPasswordResetResult(null);
    try {
      // Create a preview payload for SAP
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
        correlationId: ticketData.correlation_id || ''
      };
      setPasswordResetPreview(previewPayload);
    } catch (err) {
      console.error('Error previewing password reset:', err);
      setPasswordResetPreview(null);
    }
    setPasswordResetModal(prev => ({ ...prev, loading: false }));
  };

  const executeSendPasswordResetToSAP = async () => {
    setPasswordResetModal(prev => ({ ...prev, loading: true }));
    const ticketData = passwordResetModal.ticketData;
    try {
      // Send the password reset request directly to SAP via the backend
      // The backend should handle sending this to SAP IDM
      const sapPayload = {
        requestId: `PWD-${ticketData.servicenow_ticket_id || ticketData.correlation_id || 'UNKNOWN'}`,
        requestType: 'PASSWORD_RESET',
        userId: ticketData.affected_user || ticketData.user_id || '',
        userEmail: ticketData.user_email || '',
        userName: ticketData.user_name || ticketData.title?.replace('Password Reset - ', '') || '',
        department: ticketData.department || '',
        priority: ticketData.priority || 'medium',
        category: 'Identity Management',
        source: 'ServiceNow',
        ticketNumber: ticketData.servicenow_ticket_id || '',
        correlationId: ticketData.correlation_id || '',
        sapTicketId: ticketData.sap_ticket_id || ''
      };

      // Call the SAP endpoint to send password reset
      const response = await api.post('/sap/send-password-reset', sapPayload);
      setPasswordResetResult(response.data);

      if (response.data.success) {
        message.success('Password reset request sent to SAP successfully!');
        await fetchAllPlatformEvents();
      } else {
        message.error(`SAP Error: ${response.data.error || 'Unknown error'}`);
      }
    } catch (err) {
      setPasswordResetResult({ success: false, error: err.response?.data?.detail || err.message || 'Failed to send to SAP' });
      message.error('Failed to send password reset to SAP');
    }
    setPasswordResetModal(prev => ({ ...prev, loading: false }));
  };

  const checkPasswordResetStatus = async (record) => {
    const correlationId = record.correlationId || record.originalData?.correlation_id;
    if (!correlationId) {
      message.warning('No correlation ID found for this ticket');
      return;
    }
    setRequestStates(prev => ({ ...prev, [record.id]: { ...prev[record.id], checkingStatus: true } }));
    try {
      const response = await api.get(`/password-reset/status/${correlationId}`, { timeout: 15000 });
      setRequestStates(prev => ({
        ...prev,
        [record.id]: { ...prev[record.id], checkingStatus: false, ticketStatus: response.data }
      }));
      const statusValue = response.data?.status || '';
      if (statusValue === 'completed') {
        message.success(`Password reset ${correlationId} completed!`);
      } else if (statusValue === 'failed') {
        message.error(`Password reset ${correlationId} failed`);
      } else {
        message.info(`Password reset status: ${statusValue || 'unknown'}`);
      }
      await fetchAllPlatformEvents();
    } catch (err) {
      setRequestStates(prev => ({
        ...prev,
        [record.id]: { ...prev[record.id], checkingStatus: false, ticketStatus: { status: 'unknown', error: err.message } }
      }));
      message.error('Failed to check password reset status');
    }
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
    { title: 'ID', dataIndex: 'id', key: 'id', width: 80, render: (id) => <Text code style={{ fontWeight: 600, color: '#1890ff', fontSize: 13 }}>{id}</Text> },
    { title: 'MulesoftID', dataIndex: 'mulesoftTransactionId', key: 'mulesoftTransactionId', width: 140, render: (mulesoftId) => mulesoftId ? <Text code style={{ fontWeight: 500, color: '#722ed1', fontSize: 12 }}>{mulesoftId}</Text> : <Text type="secondary">-</Text> },
    { title: 'Platform Event', dataIndex: 'platformEvent', key: 'platformEvent', width: 180, filters: [{ text: 'Case_Update__e', value: 'Case_Update__e' }, { text: 'Account_Creation__e', value: 'Account_Creation__e' }, { text: 'Password_Reset_e', value: 'Password_Reset_e' }], onFilter: (value, record) => record.platformEvent === value, render: (event) => <PlatformEventTag event={event} /> },
    { title: 'Name / Subject', dataIndex: 'name', key: 'name', ellipsis: true, render: (name) => <Tooltip title={name}><Text strong style={{ color: '#262626' }}>{name || 'No Name'}</Text></Tooltip> },
    { title: 'Status', dataIndex: 'status', key: 'status', width: 140, render: (status, record) => record.eventType === 'case' ? <CaseStatus status={status} /> : record.eventType === 'password_reset' ? <PasswordResetStatusTag status={status} /> : record.integrationStatus ? <IntegrationStatusTag status={record.integrationStatus} servicenowStatus={record.servicenowStatus} /> : <Tag color="orange" style={{ borderRadius: 12 }}>{status}</Tag> },
    { title: 'Created Date', dataIndex: 'createdDate', key: 'createdDate', width: 130, sorter: (a, b) => new Date(a.createdDate) - new Date(b.createdDate), render: (date) => <Text style={{ fontSize: 12, color: '#8c8c8c' }}>{date ? new Date(date).toLocaleString() : 'N/A'}</Text> },
    { title: 'Actions', key: 'actions', width: 240, fixed: 'right', render: (_, record) => {
      const reqState = requestStates[record.id] || {};
      const isValidatedLocally = reqState.validated && reqState.validationResult?.valid;
      const integrationStatus = record.integrationStatus?.toUpperCase() || '';
      const isValidatedOnServer = integrationStatus === 'PENDING_MULESOFT' || integrationStatus === 'PENDING_MULE';
      const isValidated = isValidatedLocally || isValidatedOnServer;
      const isPending = record.status === 'PENDING' || record.eventType === 'case';
      // Check if already deployed (any post-deployment state)
      const isDeployed = integrationStatus === 'COMPLETED' || integrationStatus === 'APPROVED' || integrationStatus === 'SYNCED' || integrationStatus === 'REQUESTED';

      // Handle Password Reset events
      if (record.eventType === 'password_reset') {
        const pwdStatus = record.status?.toLowerCase() || '';
        const isCompleted = pwdStatus === 'completed';
        const isFailed = pwdStatus === 'failed';
        const isProcessing = pwdStatus === 'processing';

        if (isCompleted) {
          return <Tag icon={<CheckCircleOutlined />} color="success" style={{ borderRadius: 6, padding: '4px 12px', fontSize: 13 }}>Completed</Tag>;
        }

        return (
          <Space size="small">
            <Tooltip title="Check password reset status">
              <Button icon={<SyncOutlined spin={reqState.checkingStatus} />} size="small" loading={reqState.checkingStatus} onClick={(e) => { e.stopPropagation(); checkPasswordResetStatus(record); }} style={{ borderRadius: 6 }}>Status</Button>
            </Tooltip>
            <Tooltip title={isProcessing ? 'Already processing' : isFailed ? 'Retry sending to SAP' : 'Send to SAP for password reset'}>
              <Button type="primary" icon={<SafetyOutlined />} size="small" onClick={(e) => { e.stopPropagation(); handleSendPasswordResetToSAP(record); }} disabled={isProcessing} style={{ borderRadius: 6, background: '#fa8c16', borderColor: '#fa8c16' }}>{isFailed ? 'Retry SAP' : 'Send SAP'}</Button>
            </Tooltip>
          </Space>
        );
      }

      const deployMenuItems = { items: [{ key: 'sap', icon: <SendOutlined />, label: 'SAP', onClick: () => handleSendToSAP(record) }, { key: 'servicenow', icon: <SendOutlined />, label: 'ServiceNow', onClick: () => record.eventType === 'case' ? handleSendToServiceNow(record) : sendSingleToServiceNow(record) }] };
      // Disable deploy if: not validated, already deployed, or currently sending
      const isDeployDisabled = record.eventType === 'account' && (!isValidated || isDeployed || reqState.sending);

      // After deployment, show just "Deployed" text - no buttons
      if (isDeployed) {
        return <Tag icon={<CheckCircleOutlined />} color="success" style={{ borderRadius: 6, padding: '4px 12px', fontSize: 13 }}>Deployed</Tag>;
      }

      return (
        <Space size="small">
          {/* Show Validate button only for non-deployed items */}
          <Tooltip title={record.eventType === 'case' ? 'Cases are pre-validated' : isPending ? 'Validate this request' : 'Only pending requests can be validated'}>
            <Button icon={<FileProtectOutlined />} size="small" loading={reqState.validating} disabled={record.eventType === 'case' || !isPending || reqState.validating} onClick={(e) => { e.stopPropagation(); validateSingleRequest(record); }} style={{ borderRadius: 6, background: (record.eventType === 'case' || isValidated) ? '#f6ffed' : undefined, borderColor: (record.eventType === 'case' || isValidated) ? '#b7eb8f' : undefined, color: (record.eventType === 'case' || isValidated) ? '#52c41a' : undefined }}>{record.eventType === 'case' || isValidated ? 'Validated' : 'Validate'}</Button>
          </Tooltip>
          {/* Show Deploy button */}
          <Dropdown menu={deployMenuItems} trigger={['click']} disabled={isDeployDisabled}>
            <Tooltip title={isDeployDisabled ? 'Validate first' : 'Deploy to target system'}>
              <Button type="primary" icon={<RocketOutlined />} size="small" loading={reqState.sending} disabled={isDeployDisabled} onClick={(e) => e.stopPropagation()} style={{ borderRadius: 6 }}>Deploy <DownOutlined style={{ fontSize: 10, marginLeft: 4 }} /></Button>
            </Tooltip>
          </Dropdown>
        </Space>
      );
    }}
  ];

  const expandedRowRender = (record) => {
    if (record.eventType === 'case') return <CaseExpandedRow record={record} sfConnector={sfConnector} />;

    // Handle Password Reset events
    if (record.eventType === 'password_reset') {
      const ticketData = record.originalData;
      const reqState = requestStates[record.id] || {};
      const statusData = reqState.ticketStatus;
      const pwdStatus = ticketData.status?.toLowerCase() || statusData?.ticket_status || statusData?.status || 'pending';
      const isCompleted = pwdStatus === 'completed';
      const isFailed = pwdStatus === 'failed';

      return (
        <div style={{ padding: '12px 24px', background: '#fffbe6' }}>
          <Space style={{ marginBottom: 16 }}>
            <Tag icon={<KeyOutlined />} color="orange" style={{ borderRadius: 8 }}>Password_Reset_e</Tag>
            {ticketData.servicenow_ticket_id && <Tag color="geekblue" style={{ borderRadius: 8 }}>ServiceNow: {ticketData.servicenow_ticket_id}</Tag>}
            {ticketData.sap_ticket_id && <Tag color="green" style={{ borderRadius: 8 }}>SAP: {ticketData.sap_ticket_id}</Tag>}
            {ticketData.correlation_id && <Tag color="cyan" style={{ borderRadius: 8 }}>Correlation: {ticketData.correlation_id}</Tag>}
          </Space>
          <div style={{ display: 'flex', gap: 16, marginBottom: 16 }}>
            <Card size="small" title={<Space><SafetyOutlined /> SAP IDM Status</Space>} style={{ flex: 1, borderRadius: 8, borderColor: isCompleted ? '#b7eb8f' : isFailed ? '#ffa39e' : '#ffd591' }}>
              {isCompleted ? (
                <Alert type="success" showIcon icon={<CheckCircleOutlined />} message="Password Reset Completed" description={<div><div style={{ marginBottom: 8 }}>SAP Ticket: <Tag color="green" style={{ borderRadius: 8 }}>{ticketData.sap_ticket_id || 'N/A'}</Tag></div><Tag color="green" icon={<CheckCircleOutlined />} style={{ borderRadius: 8, fontWeight: 600 }}>Completed</Tag></div>} style={{ borderRadius: 6, background: '#f6ffed', borderColor: '#b7eb8f' }} />
              ) : isFailed ? (
                <Alert type="error" showIcon icon={<CloseCircleOutlined />} message="Password Reset Failed" description={<div><div style={{ marginBottom: 8 }}>Check SAP IDM logs for details</div><Tag color="red" icon={<CloseCircleOutlined />} style={{ borderRadius: 8, fontWeight: 600 }}>Failed</Tag></div>} style={{ borderRadius: 6, background: '#fff1f0', borderColor: '#ffa39e' }} />
              ) : (
                <Alert type="warning" showIcon icon={<ClockCircleOutlined />} message="Processing" description={<div><Tag color="orange" icon={<ClockCircleOutlined />} style={{ borderRadius: 8 }}>{pwdStatus === 'processing' ? 'Processing in SAP' : 'Pending'}</Tag></div>} style={{ borderRadius: 6 }} />
              )}
            </Card>
            <Card size="small" title={<Space><SendOutlined /> ServiceNow Update</Space>} style={{ flex: 1, borderRadius: 8, borderColor: ticketData.servicenow_updated ? '#b7eb8f' : '#d9d9d9' }}>
              {ticketData.servicenow_updated ? (
                <Alert type="success" showIcon message="ServiceNow Updated" description="Ticket status has been synced back to ServiceNow" style={{ borderRadius: 6 }} />
              ) : (
                <Alert type="info" showIcon message="Pending Update" description="ServiceNow ticket will be updated when SAP processing completes" style={{ borderRadius: 6 }} />
              )}
            </Card>
          </div>
          {statusData?.history && statusData.history.length > 0 && (
            <Card size="small" title="Processing History" style={{ marginBottom: 16, borderRadius: 8 }}>
              {statusData.history.map((item, index) => (
                <div key={index} style={{ padding: '8px 0', borderBottom: index < statusData.history.length - 1 ? '1px solid #f0f0f0' : 'none' }}>
                  <Space>
                    <PasswordResetStatusTag status={item.status} />
                    <Text type="secondary" style={{ fontSize: 12 }}>{new Date(item.timestamp).toLocaleString()}</Text>
                  </Space>
                  {item.message && <div style={{ marginTop: 4, color: '#595959', fontSize: 12 }}>{item.message}</div>}
                </div>
              ))}
            </Card>
          )}
          <JsonDisplay data={ticketData} title={`Password Reset Ticket - ${ticketData.servicenow_ticket_id || ticketData.correlation_id}`} />
        </div>
      );
    }

    const accountData = record.originalData;
    const reqState = requestStates[record.id] || {};
    const validationResult = reqState.validationResult;
    const sendResult = reqState.sendResult;
    const ticketId = sendResult?.ticket_number || accountData.servicenow_ticket_id;
    const ticketStatus = reqState.ticketStatus?.status || accountData.servicenow_status;
    const isApproved = ticketStatus === 'approved' || ticketStatus === 'APPROVED';
    const isRejected = ticketStatus === 'rejected' || ticketStatus === 'REJECTED';
    return (
      <div style={{ padding: '12px 24px', background: '#fafafa' }}>
        <Space style={{ marginBottom: 16 }}>
          <Tag icon={<UserAddOutlined />} color="purple" style={{ borderRadius: 8 }}>Account_Creation__e</Tag>
          {accountData.servicenow_ticket_id && <Tag color="geekblue" style={{ borderRadius: 8 }}>ServiceNow: {accountData.servicenow_ticket_id}</Tag>}
          {accountData.mulesoft_transaction_id && <Tag color="cyan" style={{ borderRadius: 8 }}>MuleSoft TX: {accountData.mulesoft_transaction_id}</Tag>}
          {accountData.created_account_id && <Tag color="green" icon={<CheckCircleOutlined />} style={{ borderRadius: 8 }}>Account #{accountData.created_account_id}</Tag>}
        </Space>
        <div style={{ display: 'flex', gap: 16, marginBottom: 16 }}>
          <Card size="small" title={<Space><FileProtectOutlined /> Validation Status</Space>} style={{ flex: 1, borderRadius: 8, borderColor: validationResult?.valid ? '#b7eb8f' : validationResult ? '#ffa39e' : '#d9d9d9' }}>
            {!validationResult ? <Text type="secondary">Not validated yet. Click "Validate" button.</Text> : validationResult.valid ? <Alert type="success" showIcon message="Validation Passed" description="Ready to send to ServiceNow." style={{ borderRadius: 6 }} /> : <Alert type="error" showIcon message="Validation Failed" description={<div>{validationResult.errors?.map((err, i) => <div key={i} style={{ color: '#ff4d4f', fontSize: 12 }}><WarningOutlined style={{ marginRight: 4 }} /> {err}</div>)}</div>} style={{ borderRadius: 6 }} />}
          </Card>
          <Card size="small" title={<div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}><Space><SendOutlined /> ServiceNow Status</Space>{ticketId && <Button size="small" icon={<SyncOutlined spin={reqState.checkingStatus} />} loading={reqState.checkingStatus} onClick={(e) => { e.stopPropagation(); checkServiceNowStatus(record); }} style={{ borderRadius: 6 }}>Check</Button>}</div>} style={{ flex: 1, borderRadius: 8, borderColor: isApproved ? '#b7eb8f' : isRejected ? '#ffa39e' : ticketId ? '#d3adf7' : '#d9d9d9' }}>
            {!sendResult && !ticketId ? <Text type="secondary">Not sent yet. Validate first, then Deploy.</Text> : isApproved ? <Alert type="success" showIcon icon={<CheckCircleOutlined />} message="APPROVED" description={<div><div style={{ marginBottom: 8 }}>ServiceNow Ticket: <Tag color="purple" style={{ borderRadius: 8 }}>{ticketId}</Tag></div><Tag color="green" icon={<CheckCircleOutlined />} style={{ borderRadius: 8, fontWeight: 600 }}>Approved</Tag></div>} style={{ borderRadius: 6, background: '#f6ffed', borderColor: '#b7eb8f' }} /> : isRejected ? <Alert type="error" showIcon icon={<CloseCircleOutlined />} message="REJECTED" description={<div><div style={{ marginBottom: 8 }}>ServiceNow Ticket: <Tag color="purple" style={{ borderRadius: 8 }}>{ticketId}</Tag></div><Tag color="red" icon={<CloseCircleOutlined />} style={{ borderRadius: 8, fontWeight: 600 }}>Rejected</Tag></div>} style={{ borderRadius: 6, background: '#fff1f0', borderColor: '#ffa39e' }} /> : ticketId ? <Alert type="info" showIcon icon={<ClockCircleOutlined />} message="Awaiting Approval" description={<div><div style={{ marginBottom: 8 }}>ServiceNow Ticket: <Tag color="purple" style={{ borderRadius: 8 }}>{ticketId}</Tag></div><Tag color="orange" icon={<ClockCircleOutlined />} style={{ borderRadius: 8 }}>Pending Approval</Tag></div>} style={{ borderRadius: 6 }} /> : <Alert type="error" showIcon message="Failed to Send" description={sendResult?.error || 'Unknown error'} style={{ borderRadius: 6 }} />}
          </Card>
        </div>
        {accountData.integration_status === 'FAILED' && accountData.integration_error && <Alert type="error" showIcon message="Previous Integration Failed" description={accountData.integration_error} style={{ marginBottom: 16, borderRadius: 8 }} />}
        <JsonDisplay data={accountData} title={`Account Request #${accountData.id} - ${accountData.name}`} />
      </div>
    );
  };

  const casesCount = platformEvents.filter(e => e.eventType === 'case').length;
  const accountsCount = platformEvents.filter(e => e.eventType === 'account').length;
  const pendingAccountsCount = platformEvents.filter(e => e.eventType === 'account' && e.status === 'PENDING').length;
  const passwordResetCount = platformEvents.filter(e => e.eventType === 'password_reset').length;
  const pendingPasswordResetCount = platformEvents.filter(e => e.eventType === 'password_reset' && (e.status === 'pending' || e.status === 'processing')).length;

  return (
    <div className="animate-fade-in">
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div><h2 style={{ marginBottom: 4, color: '#262626' }}>Runtime Manager</h2><p style={{ color: '#8c8c8c', margin: 0 }}>Execution mode - Send data to SAP and ServiceNow, validate and process requests</p></div>
          <Space><Button icon={<ApiOutlined />} onClick={testSAPConnection} style={{ borderRadius: 8 }}>Test SAP</Button><Button icon={<ApiOutlined />} onClick={testServiceNowConnection} style={{ borderRadius: 8, background: '#81B5A1', borderColor: '#81B5A1', color: '#fff' }}>Test ServiceNow</Button><Button icon={<SafetyOutlined />} onClick={testPasswordResetHealth} style={{ borderRadius: 8, background: '#fff7e6', borderColor: '#ffd591', color: '#fa8c16' }}>Password Reset Health</Button></Space>
        </div>
      </div>
      <Alert message="Execution Mode - Platform Events" description={<span>Send Platform Events to SAP and ServiceNow. For <strong>Case_Update__e</strong>, click Deploy. For <strong>Account_Creation__e</strong>, validate first, then deploy to ServiceNow. For <strong>Password_Reset_e</strong>, send directly to SAP IDM for processing.</span>} type="info" showIcon icon={<ThunderboltOutlined />} style={{ marginBottom: 16, borderRadius: 8 }} />
      {error && <Alert message="Connection Error" description={error} type="error" showIcon style={{ marginBottom: 16, borderRadius: 8 }} action={<Button size="small" onClick={fetchAllPlatformEvents}>Retry</Button>} />}
      <Card title={<div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}><Space><span style={{ fontWeight: 600, fontSize: 16 }}>Platform Events</span><Tag color="blue" style={{ borderRadius: 12 }}>{casesCount} Cases</Tag><Tag color="purple" style={{ borderRadius: 12 }}>{accountsCount} Accounts</Tag><Tag color="orange" style={{ borderRadius: 12 }}>{passwordResetCount} Password Reset</Tag>{(pendingAccountsCount > 0 || pendingPasswordResetCount > 0) && <Tag color="gold" style={{ borderRadius: 12 }}>{pendingAccountsCount + pendingPasswordResetCount} Pending</Tag>}<Tag color={platformEvents.length > 0 ? 'success' : 'default'} style={{ borderRadius: 12 }}>{loading ? 'Loading...' : `${platformEvents.length} Total`}</Tag></Space><Space>{pendingAccountsCount > 0 && <Tooltip title="Process all pending account requests"><Button icon={<ThunderboltOutlined />} onClick={runOrchestration} loading={orchestrating} style={{ borderRadius: 8 }}>{orchestrating ? 'Processing...' : 'Process All Pending'}</Button></Tooltip>}<Button icon={<ReloadOutlined />} onClick={fetchAllPlatformEvents} loading={loading} type="primary" style={{ borderRadius: 8 }}>Refresh</Button></Space></div>} className="animate-fade-in-up" style={{ borderRadius: 12 }}>
        {loading ? <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 200 }}><Spin size="large" /><span style={{ marginLeft: 16 }}>Loading Salesforce Platform Events...</span></div> : platformEvents.length > 0 ? (
          <Table dataSource={platformEvents} columns={columns} expandable={{ expandedRowRender, expandRowByClick: true, expandedRowKeys: expandedRows, onExpand: handleRowExpand, expandIcon: () => null }} pagination={{ pageSize: 10, showSizeChanger: true, showTotal: (total, range) => `${range[0]}-${range[1]} of ${total} events` }} size="middle" scroll={{ x: 1300 }} style={{ background: '#ffffff', borderRadius: 8 }} />
        ) : (
          <div style={{ textAlign: 'center', padding: '60px 0', color: '#8c8c8c' }}><WarningOutlined style={{ fontSize: 48, color: '#ff4d4f', marginBottom: 16 }} /><h3 style={{ color: '#595959' }}>No Platform Events Found</h3><Paragraph style={{ color: '#8c8c8c', maxWidth: 500, margin: '0 auto' }}>{sfConnector?.config?.server_url ? <>Make sure your remote Salesforce backend is running at <Text code>{sfConnector.config.server_url}</Text></> : <>No Salesforce connector configured. Please create one in the <Text strong>Connectors</Text> page.</>}</Paragraph><Button type="primary" icon={<ReloadOutlined />} onClick={fetchAllPlatformEvents} style={{ marginTop: 16, borderRadius: 8 }}>Load Events</Button></div>
        )}
      </Card>

      <Modal title={<Space><CloudUploadOutlined style={{ color: '#1890ff' }} /><span>Send to SAP</span></Space>} open={sapModal.visible} onCancel={() => { setSapModal({ visible: false, caseData: null, loading: false }); setSapResult(null); setXmlPreview(''); }} width={900} footer={[<Button key="cancel" onClick={() => setSapModal({ visible: false, caseData: null, loading: false })}>Cancel</Button>, <Button key="send" type="primary" icon={<SendOutlined />} loading={sapModal.loading} onClick={executeSendToSAP} disabled={sapResult?.success}>{sapResult?.success ? 'Sent Successfully' : 'Send to SAP'}</Button>]}>
        {sapModal.caseData && (
          <Tabs defaultActiveKey="preview" items={[
            { key: 'preview', label: 'XML Preview', children: (<><div style={{ marginBottom: 16 }}><Text strong>Target Endpoint: </Text><Text code>POST http://localhost:2004/api/integration/mulesoft/load-request/xml</Text></div><div style={{ marginBottom: 16 }}><Text strong>Source: </Text><Tag color="blue">{sapModal.caseData.id || sapModal.caseData.name}</Tag><Text>{sapModal.caseData.subject || sapModal.caseData.name}</Text></div>{sapModal.loading ? <div style={{ textAlign: 'center', padding: 40 }}><Spin /> Generating XML...</div> : <pre style={{ background: '#1e1e1e', color: '#d4d4d4', padding: 16, borderRadius: 8, overflow: 'auto', maxHeight: 350, fontSize: 12, fontFamily: 'Monaco, Menlo, monospace' }}>{xmlPreview}</pre>}</>) },
            { key: 'source', label: 'Source Data', children: <pre style={{ background: '#f6f8fa', padding: 16, borderRadius: 8, overflow: 'auto', maxHeight: 400, fontSize: 12 }}>{JSON.stringify(sapModal.caseData, null, 2)}</pre> },
            ...(sapResult ? [{ key: 'response', label: 'SAP Response', children: (<><Alert message={sapResult.success ? 'Success' : 'Error'} description={sapResult.success ? 'Data sent to SAP successfully' : sapResult.error} type={sapResult.success ? 'success' : 'error'} showIcon style={{ marginBottom: 16 }} />{sapResult.sap_response && <><Text strong>SAP Response:</Text><pre style={{ background: '#f6f8fa', padding: 16, borderRadius: 8, overflow: 'auto', maxHeight: 300, fontSize: 12, marginTop: 8 }}>{JSON.stringify(sapResult.sap_response, null, 2)}</pre></>}</>) }] : [])
          ]} />
        )}
      </Modal>

      <Modal title={<Space><CloudUploadOutlined style={{ color: '#81B5A1' }} /><span>Send Ticket to ServiceNow</span></Space>} open={snowModal.visible} onCancel={() => { setSnowModal({ visible: false, caseData: null, loading: false }); setSnowResult(null); setSnowPreview({ ticket: null, approval: null }); }} width={900} footer={[<Button key="cancel" onClick={() => setSnowModal({ visible: false, caseData: null, loading: false })}>Cancel</Button>, <Button key="send" style={{ background: '#81B5A1', borderColor: '#81B5A1' }} type="primary" icon={<SendOutlined />} loading={snowModal.loading} onClick={executeSendTicketToServiceNow} disabled={snowResult?.ticket?.success}>{snowResult?.ticket?.success ? 'Sent Successfully' : 'Send Ticket'}</Button>]}>
        {snowModal.caseData && (
          <Tabs defaultActiveKey="ticket-preview" items={[
            { key: 'ticket-preview', label: 'Ticket Preview', children: (<><div style={{ marginBottom: 16 }}><Text strong>Target: </Text><Text code>POST http://149.102.158.71:4780/api/tickets</Text></div><div style={{ marginBottom: 16 }}><Text strong>Source Case: </Text><Tag color="blue">{snowModal.caseData.id}</Tag><Text>{snowModal.caseData.subject}</Text></div>{snowModal.loading ? <div style={{ textAlign: 'center', padding: 40 }}><Spin /> Generating ticket preview...</div> : snowPreview.ticket ? <pre style={{ background: '#1e1e1e', color: '#d4d4d4', padding: 16, borderRadius: 8, overflow: 'auto', maxHeight: 350, fontSize: 12, fontFamily: 'Monaco, Menlo, monospace' }}>{JSON.stringify(snowPreview.ticket, null, 2)}</pre> : <Text type="secondary">Preview not available</Text>}</>) },
            { key: 'source', label: 'Source Data', children: <pre style={{ background: '#f6f8fa', padding: 16, borderRadius: 8, overflow: 'auto', maxHeight: 400, fontSize: 12 }}>{JSON.stringify(snowModal.caseData, null, 2)}</pre> },
            ...(snowResult ? [{ key: 'response', label: 'ServiceNow Response', children: (<><div style={{ marginBottom: 16 }}><Text strong style={{ fontSize: 14 }}>Ticket Result:</Text><Alert message={snowResult.ticket?.success ? 'Ticket Created' : 'Ticket Failed'} description={snowResult.ticket?.success ? `Ticket ${snowResult.ticket.ticket_number || ''} created` : (snowResult.ticket?.error || 'Failed')} type={snowResult.ticket?.success ? 'success' : 'error'} showIcon style={{ marginTop: 8 }} /></div></>) }] : [])
          ]} />
        )}
      </Modal>

      <Modal title={<Space><SafetyOutlined style={{ color: '#fa8c16' }} /><span>Send Password Reset to SAP</span><Tag color="orange" style={{ borderRadius: 8 }}>Password_Reset_e</Tag></Space>} open={passwordResetModal.visible} onCancel={() => { setPasswordResetModal({ visible: false, ticketData: null, loading: false }); setPasswordResetResult(null); setPasswordResetPreview(null); }} width={900} footer={[<Button key="cancel" onClick={() => setPasswordResetModal({ visible: false, ticketData: null, loading: false })}>Cancel</Button>, <Button key="send" type="primary" icon={<SafetyOutlined />} loading={passwordResetModal.loading} onClick={executeSendPasswordResetToSAP} disabled={passwordResetResult?.success} style={{ background: '#fa8c16', borderColor: '#fa8c16' }}>{passwordResetResult?.success ? 'Sent Successfully' : 'Send to SAP IDM'}</Button>]}>
        {passwordResetModal.ticketData && (<><Alert message="Password Reset Request" description="This will send the password reset request to SAP Identity Management system." type="info" showIcon style={{ marginBottom: 16 }} />
          <Tabs defaultActiveKey="sap-preview" items={[
            { key: 'sap-preview', label: 'SAP IDM Payload', children: (<><div style={{ marginBottom: 16 }}><Text strong>Target: </Text><Text code>POST http://localhost:2004/api/integration/mulesoft/password-reset</Text></div><div style={{ marginBottom: 16 }}><Text strong>Source Ticket: </Text><Tag color="orange">{passwordResetModal.ticketData.servicenow_ticket_id || passwordResetModal.ticketData.correlation_id}</Tag><Text>{passwordResetModal.ticketData.title || `Password Reset - ${passwordResetModal.ticketData.user_name || 'User'}`}</Text></div>{passwordResetModal.loading ? <div style={{ textAlign: 'center', padding: 40 }}><Spin /> Generating SAP payload...</div> : passwordResetPreview ? <pre style={{ background: '#1e1e1e', color: '#d4d4d4', padding: 16, borderRadius: 8, overflow: 'auto', maxHeight: 350, fontSize: 12, fontFamily: 'Monaco, Menlo, monospace' }}>{JSON.stringify(passwordResetPreview, null, 2)}</pre> : <Text type="secondary">Preview not available</Text>}</>) },
            { key: 'source', label: 'Source Ticket Data', children: <pre style={{ background: '#f6f8fa', padding: 16, borderRadius: 8, overflow: 'auto', maxHeight: 400, fontSize: 12 }}>{JSON.stringify(passwordResetModal.ticketData, null, 2)}</pre> },
            ...(passwordResetResult ? [{ key: 'response', label: 'SAP Response', children: (<><Alert message={passwordResetResult.success ? 'Success' : 'Error'} description={passwordResetResult.success ? 'Password reset request sent to SAP IDM successfully' : passwordResetResult.error} type={passwordResetResult.success ? 'success' : 'error'} showIcon style={{ marginBottom: 16 }} />{passwordResetResult.sap_response && <><Text strong>SAP Response:</Text><pre style={{ background: '#f6f8fa', padding: 16, borderRadius: 8, overflow: 'auto', maxHeight: 300, fontSize: 12, marginTop: 8 }}>{JSON.stringify(passwordResetResult.sap_response, null, 2)}</pre></>}</>) }] : [])
          ]} /></>)}
      </Modal>
    </div>
  );
}
