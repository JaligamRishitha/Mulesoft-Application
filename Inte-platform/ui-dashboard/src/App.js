import React, { useState } from 'react';
import { Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu, Dropdown, Space, Avatar, Modal, Form, Input, message } from 'antd';
import {
  DownOutlined,
  UserOutlined,
  LogoutOutlined,
  DashboardOutlined,
  LinkOutlined,
  EditOutlined,
  CodeOutlined,
  LineChartOutlined,
  SafetyOutlined,
  KeyOutlined,
  EyeOutlined,
  ThunderboltOutlined,
  MailOutlined
} from '@ant-design/icons';
import Dashboard from './pages/Dashboard';
import Integrations from './pages/Integrations';
import Runtime from './pages/Runtime';
import APIs from './pages/APIs';
import Metrics from './pages/Metrics';
import APIDesigner from './pages/APIDesigner';
import SwaggerUI from './pages/SwaggerUI';
import Connectors from './pages/Connectors';
import ResilienceMonitor from './pages/ResilienceMonitor';
import Events from './pages/Events';
import Login from './pages/Login';

const { Header, Content } = Layout;

export default function App() {
  const navigate = useNavigate();
  const location = useLocation();
  const isAuth = !!localStorage.getItem('token');
  const [profileVisible, setProfileVisible] = useState(false);
  const [passwordVisible, setPasswordVisible] = useState(false);
  const [profileForm] = Form.useForm();
  const [passwordForm] = Form.useForm();

  if (!isAuth && location.pathname !== '/login') return <Navigate to="/login" />;
  if (location.pathname === '/login') return <Login />;

  const handleProfileSave = () => {
    profileForm.validateFields().then(values => {
      message.success('Profile updated successfully');
      setProfileVisible(false);
    });
  };

  const handlePasswordChange = () => {
    passwordForm.validateFields().then(values => {
      if (values.newPassword !== values.confirmPassword) {
        message.error('Passwords do not match');
        return;
      }
      message.success('Password changed successfully');
      setPasswordVisible(false);
      passwordForm.resetFields();
    });
  };

  const integrationsMenu = {
    items: [
      { key: '/integrations', icon: <EyeOutlined />, label: 'Integration Designer', description: 'Preview Salesforce data & payloads' },
      { key: '/runtime', icon: <ThunderboltOutlined />, label: 'Runtime Manager', description: 'Execute integrations to SAP/ServiceNow' },
      { key: '/events', icon: <MailOutlined />, label: 'System Events', description: 'Capture and track system events' },
      { key: '/connectors', icon: <LinkOutlined />, label: 'Connectors', description: 'Manage external connections' },
    ],
    onClick: ({ key }) => navigate(key)
  };

  const apisMenu = {
    items: [
      { key: '/apis', icon: <SafetyOutlined />, label: 'API Manager', description: 'Manage and secure APIs' },
      { key: '/api-designer', icon: <EditOutlined />, label: 'API Designer', description: 'Design APIs with OpenAPI' },
      { key: '/api-explorer', icon: <CodeOutlined />, label: 'API Explorer', description: 'Test and explore APIs' },
    ],
    onClick: ({ key }) => navigate(key)
  };

  const monitoringMenu = {
    items: [
      { key: '/', icon: <DashboardOutlined />, label: 'Dashboard', description: 'Platform overview' },
      { key: '/metrics', icon: <LineChartOutlined />, label: 'Observability', description: 'Metrics and monitoring' },
      { key: '/resilience', icon: <SafetyOutlined />, label: 'Resilience', description: 'Circuit breaker & DLQ monitoring' },
    ],
    onClick: ({ key }) => navigate(key)
  };

  const userMenu = {
    items: [
      { key: 'profile', icon: <UserOutlined />, label: 'My Profile' },
      { key: 'password', icon: <KeyOutlined />, label: 'Change Password' },
      { type: 'divider' },
      { key: 'logout', icon: <LogoutOutlined />, label: 'Sign Out', danger: true },
    ],
    onClick: ({ key }) => {
      if (key === 'logout') {
        localStorage.removeItem('token');
        navigate('/login');
      } else if (key === 'profile') {
        profileForm.setFieldsValue({ fullName: 'User', email: 'user@example.com' });
        setProfileVisible(true);
      } else if (key === 'password') {
        setPasswordVisible(true);
      }
    }
  };

  const renderDropdownMenu = (items) => ({
    items: items.map(item => ({
      key: item.key,
      icon: item.icon,
      label: (
        <div style={{ padding: '4px 0' }}>
          <div style={{ fontWeight: 500 }}>{item.label}</div>
          {item.description && <div style={{ fontSize: 12, color: '#666', marginTop: 2 }}>{item.description}</div>}
        </div>
      )
    })),
    onClick: items[0] && items[0].key ? ({ key }) => navigate(key) : undefined
  });

  const getActiveMenu = () => {
    const path = location.pathname;
    if (['/integrations', '/runtime', '/connectors', '/events'].includes(path)) return 'integrations';
    if (['/apis', '/api-designer', '/api-explorer'].includes(path)) return 'apis';
    if (['/', '/metrics'].includes(path)) return 'monitoring';
    return '';
  };

  const navItemStyle = (isActive) => ({
    padding: '0 20px',
    height: '100%',
    display: 'flex',
    alignItems: 'center',
    cursor: 'pointer',
    borderBottom: isActive ? '3px solid #00a1e0' : '3px solid transparent',
    color: isActive ? '#00a1e0' : '#333',
    fontWeight: 500,
    transition: 'all 0.2s ease'
  });

  return (
    <Layout style={{ minHeight: '100vh', background: '#f5f7fa' }}>
      {/* Top Navigation Bar */}
      <Header style={{ 
        background: '#fff', 
        padding: 0, 
        height: 56, 
        lineHeight: '56px',
        boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
        position: 'fixed',
        width: '100%',
        zIndex: 1000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        {/* Left Section - Logo & Nav */}
        <div style={{ display: 'flex', alignItems: 'center', height: '100%' }}>
          {/* Logo */}
          <div 
            onClick={() => navigate('/')}
            style={{ 
              height: 56, 
              display: 'flex', 
              alignItems: 'center', 
              padding: '0 16px',
              cursor: 'pointer',
              gap: 10
            }}
          >
            <img src="/images/mulesoft.png" alt="MuleSoft" style={{ height: 36, width: 36 }} />
            <span style={{ fontSize: 18, fontWeight: 600, color: '#333' }}>MuleSoft</span>
          </div>

          {/* Navigation Items */}
          <Dropdown menu={renderDropdownMenu(integrationsMenu.items)} trigger={['click']}>
            <div style={navItemStyle(getActiveMenu() === 'integrations')}>
              <Space>
                Integrations
                <DownOutlined style={{ fontSize: 10 }} />
              </Space>
            </div>
          </Dropdown>

          <Dropdown menu={renderDropdownMenu(apisMenu.items)} trigger={['click']}>
            <div style={navItemStyle(getActiveMenu() === 'apis')}>
              <Space>
                APIs
                <DownOutlined style={{ fontSize: 10 }} />
              </Space>
            </div>
          </Dropdown>

          <Dropdown menu={renderDropdownMenu(monitoringMenu.items)} trigger={['click']}>
            <div style={navItemStyle(getActiveMenu() === 'monitoring')}>
              <Space>
                Monitoring
                <DownOutlined style={{ fontSize: 10 }} />
              </Space>
            </div>
          </Dropdown>
        </div>

        {/* Right Section - User Profile */}
        <div style={{ display: 'flex', alignItems: 'center', paddingRight: 16 }}>
          <Dropdown menu={userMenu} trigger={['click']}>
            <div style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: 8, 
              cursor: 'pointer',
              padding: '4px 12px',
              borderRadius: 8
            }} className="nav-icon-btn">
              <Avatar 
                size={32} 
                style={{ 
                  background: 'linear-gradient(135deg, #00a1e0 0%, #5c6bc0 100%)',
                  fontSize: 14
                }}
              >
                U
              </Avatar>
              <span style={{ fontWeight: 500, color: '#333' }}>User</span>
              <DownOutlined style={{ fontSize: 10, color: '#666' }} />
            </div>
          </Dropdown>
        </div>
      </Header>

      {/* Main Content */}
      <Content style={{ 
        marginTop: 56, 
        padding: 24, 
        background: 'linear-gradient(135deg, #f5f7fa 0%, #e8ecf1 100%)',
        minHeight: 'calc(100vh - 56px)'
      }}>
        <div className="animate-fade-in">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/integrations" element={<Integrations />} />
            <Route path="/runtime" element={<Runtime />} />
            <Route path="/connectors" element={<Connectors />} />
            <Route path="/events" element={<Events />} />
            <Route path="/apis" element={<APIs />} />
            <Route path="/api-designer" element={<APIDesigner />} />
            <Route path="/api-explorer" element={<SwaggerUI />} />
            <Route path="/metrics" element={<Metrics />} />
            <Route path="/resilience" element={<ResilienceMonitor />} />
          </Routes>
        </div>
      </Content>

      {/* Profile Modal */}
      <Modal 
        title="My Profile" 
        open={profileVisible} 
        onCancel={() => setProfileVisible(false)}
        onOk={handleProfileSave}
        okText="Save"
      >
        <Form form={profileForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="fullName" label="Full Name" rules={[{ required: true }]}>
            <Input prefix={<UserOutlined />} placeholder="Enter your name" />
          </Form.Item>
          <Form.Item name="email" label="Email" rules={[{ required: true, type: 'email' }]}>
            <Input prefix={<MailOutlined />} placeholder="Enter your email" />
          </Form.Item>
        </Form>
      </Modal>

      {/* Change Password Modal */}
      <Modal 
        title="Change Password" 
        open={passwordVisible} 
        onCancel={() => { setPasswordVisible(false); passwordForm.resetFields(); }}
        onOk={handlePasswordChange}
        okText="Change Password"
      >
        <Form form={passwordForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="currentPassword" label="Current Password" rules={[{ required: true }]}>
            <Input.Password prefix={<KeyOutlined />} placeholder="Enter current password" />
          </Form.Item>
          <Form.Item name="newPassword" label="New Password" rules={[{ required: true, min: 6 }]}>
            <Input.Password prefix={<KeyOutlined />} placeholder="Enter new password" />
          </Form.Item>
          <Form.Item name="confirmPassword" label="Confirm Password" rules={[{ required: true }]}>
            <Input.Password prefix={<KeyOutlined />} placeholder="Confirm new password" />
          </Form.Item>
        </Form>
      </Modal>
    </Layout>
  );
}
