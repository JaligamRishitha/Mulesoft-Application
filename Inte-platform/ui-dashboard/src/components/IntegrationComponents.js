import React from 'react';
import { Tag, Typography, Collapse } from 'antd';
import {
  WarningOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  CloseCircleOutlined,
  CodeOutlined,
  EyeOutlined
} from '@ant-design/icons';

const { Text } = Typography;
const { Panel } = Collapse;

// JSON Formatter Component
export const JsonDisplay = ({ data, title = "JSON Payload" }) => {
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
export const CaseStatus = ({ status }) => {
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
export const CasePriority = ({ priority }) => {
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

// Account request status tag
export const RequestStatus = ({ status }) => {
  const config = {
    'PENDING': { color: 'orange', icon: <ClockCircleOutlined /> },
    'COMPLETED': { color: 'green', icon: <CheckCircleOutlined /> },
    'REJECTED': { color: 'red', icon: <WarningOutlined /> },
    'FAILED': { color: 'red', icon: <ExclamationCircleOutlined /> }
  };
  const c = config[status] || { color: 'default', icon: <ClockCircleOutlined /> };
  return <Tag icon={c.icon} color={c.color} style={{ borderRadius: 12, fontWeight: 500 }}>{status || 'Unknown'}</Tag>;
};

// Integration status tag with ServiceNow status handling
// Shows only: PENDING, VALIDATED, COMPLETED
export const IntegrationStatusTag = ({ status, servicenowStatus }) => {
  // Check ServiceNow status for approved/rejected - both map to COMPLETED
  const snStatus = servicenowStatus?.toLowerCase();
  if (snStatus === 'approved' || snStatus === 'rejected') {
    return <Tag icon={<CheckCircleOutlined />} color="success" style={{ borderRadius: 12, fontWeight: 600 }}>COMPLETED</Tag>;
  }

  const upperStatus = status?.toUpperCase() || '';

  // Map all statuses to only: PENDING, VALIDATED, COMPLETED
  const config = {
    'COMPLETED': { color: 'green', icon: <CheckCircleOutlined />, label: 'COMPLETED' },
    'APPROVED': { color: 'green', icon: <CheckCircleOutlined />, label: 'COMPLETED' },
    'SYNCED': { color: 'green', icon: <CheckCircleOutlined />, label: 'COMPLETED' },
    'REQUESTED': { color: 'green', icon: <CheckCircleOutlined />, label: 'COMPLETED' },
    'FAILED': { color: 'red', icon: <CloseCircleOutlined />, label: 'FAILED' },
    'PENDING': { color: 'orange', icon: <ClockCircleOutlined />, label: 'PENDING' },
    'PENDING_MULE': { color: 'blue', icon: <CheckCircleOutlined />, label: 'VALIDATED' },
    'PENDING_MULESOFT': { color: 'blue', icon: <CheckCircleOutlined />, label: 'VALIDATED' }
  };
  const c = config[upperStatus] || { color: 'orange', icon: <ClockCircleOutlined />, label: 'PENDING' };
  return <Tag icon={c.icon} color={c.color} style={{ borderRadius: 12 }}>{c.label}</Tag>;
};

// Helper to build the full payload for case expanded view
export const buildCasePayload = (caseData, sfConnector) => {
  return {
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
      customerData: {
        customerType: caseData.customerType || 'Business',
        region: caseData.region || 'London',
        serviceLevel: caseData.serviceLevel || 'Premium',
        contractNumber: caseData.contractNumber || `CNT-${caseData.id}`,
        billingAccount: caseData.billingAccount || `BILL-${caseData.id}`
      },
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
};

// Expanded row render for cases
export const CaseExpandedRow = ({ record, sfConnector }) => {
  const caseData = record.originalData;
  const fullPayload = buildCasePayload(caseData, sfConnector);

  return (
    <div style={{ padding: '16px 24px', background: '#fafafa' }}>
      <Collapse
        defaultActiveKey={['payload']}
        ghost
        expandIconPosition="right"
      >
        <Panel
          header={
            <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <CodeOutlined style={{ color: '#1890ff' }} />
              <Text strong>Platform Event Payload</Text>
              <Tag color="blue" style={{ borderRadius: 8 }}>JSON Format</Tag>
            </span>
          }
          key="payload"
        >
          <JsonDisplay data={fullPayload} title="Complete Salesforce Case Event" />
        </Panel>

        <Panel
          header={
            <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <EyeOutlined style={{ color: '#52c41a' }} />
              <Text strong>Raw Case Data</Text>
              <Tag color="green" style={{ borderRadius: 8 }}>Source Data</Tag>
            </span>
          }
          key="raw"
        >
          <JsonDisplay data={caseData} title="Original Salesforce Case Data" />
        </Panel>
      </Collapse>
    </div>
  );
};
