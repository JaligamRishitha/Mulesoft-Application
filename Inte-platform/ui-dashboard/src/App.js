import React, { useState } from 'react';
import { Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu } from 'antd';
import { DashboardOutlined, ApiOutlined, SettingOutlined, CloudServerOutlined, LogoutOutlined } from '@ant-design/icons';
import Dashboard from './pages/Dashboard';
import Integrations from './pages/Integrations';
import Runtime from './pages/Runtime';
import APIs from './pages/APIs';
import Login from './pages/Login';

const { Sider, Content } = Layout;

export default function App() {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const isAuth = !!localStorage.getItem('token');

  if (!isAuth && location.pathname !== '/login') return <Navigate to="/login" />;
  if (location.pathname === '/login') return <Login />;

  const menuItems = [
    { key: '/', icon: <DashboardOutlined />, label: 'Dashboard' },
    { key: '/integrations', icon: <SettingOutlined />, label: 'Integrations' },
    { key: '/runtime', icon: <CloudServerOutlined />, label: 'Runtime' },
    { key: '/apis', icon: <ApiOutlined />, label: 'API Manager' },
    { key: 'logout', icon: <LogoutOutlined />, label: 'Logout', danger: true },
  ];

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider collapsible collapsed={collapsed} onCollapse={setCollapsed}>
        <div style={{ height: 32, margin: 16, background: 'rgba(255,255,255,0.2)', borderRadius: 6, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontWeight: 'bold' }}>
          {collapsed ? 'MS' : 'MuleSoft'}
        </div>
        <Menu theme="dark" selectedKeys={[location.pathname]} items={menuItems}
          onClick={({ key }) => key === 'logout' ? (localStorage.removeItem('token'), navigate('/login')) : navigate(key)} />
      </Sider>
      <Layout>
        <Content className="site-layout-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/integrations" element={<Integrations />} />
            <Route path="/runtime" element={<Runtime />} />
            <Route path="/apis" element={<APIs />} />
          </Routes>
        </Content>
      </Layout>
    </Layout>
  );
}
