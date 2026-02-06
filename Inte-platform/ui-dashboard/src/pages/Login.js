import React, { useState } from 'react';
import { Form, Input, Button, Card, message, Tabs } from 'antd';
import { UserOutlined, LockOutlined, MailOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { backendApi } from '../api';

export default function Login() {
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleLogin = async (values) => {
    setLoading(true);
    try {
      const { data } = await backendApi.post('/auth/login', values);
      localStorage.setItem('token', data.token);
      message.success('Login successful');
      navigate('/');
    } catch (err) {
      message.error(err.response?.data?.detail || 'Login failed');
    }
    setLoading(false);
  };

  const handleRegister = async (values) => {
    setLoading(true);
    try {
      await backendApi.post('/auth/register', { email: values.email, password: values.password, full_name: values.fullName });
      message.success('Registration successful! Please login.');
    } catch (err) {
      message.error(err.response?.data?.detail || 'Registration failed');
    }
    setLoading(false);
  };

  const containerStyle = {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    minHeight: '100vh',
    background: 'linear-gradient(135deg, #0a1628 0%, #1a2744 50%, #0a1628 100%)',
    position: 'relative',
    overflow: 'hidden'
  };

  const backgroundStyle = {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    background: `
      radial-gradient(circle at 20% 80%, rgba(0, 161, 224, 0.15) 0%, transparent 50%),
      radial-gradient(circle at 80% 20%, rgba(92, 107, 192, 0.15) 0%, transparent 50%),
      radial-gradient(circle at 40% 40%, rgba(0, 212, 170, 0.1) 0%, transparent 40%)
    `,
    pointerEvents: 'none'
  };

  const cardStyle = {
    width: 420,
    borderRadius: 20,
    boxShadow: '0 20px 60px rgba(0, 0, 0, 0.3), 0 0 40px rgba(0, 161, 224, 0.1)',
    border: '1px solid rgba(255, 255, 255, 0.1)',
    background: 'rgba(255, 255, 255, 0.95)',
    backdropFilter: 'blur(20px)',
    overflow: 'hidden'
  };

  const logoStyle = {
    textAlign: 'center',
    padding: '30px 0 20px',
    background: 'linear-gradient(135deg, #00a1e0 0%, #5c6bc0 100%)',
    margin: '-24px -24px 24px -24px'
  };

  const titleStyle = {
    color: '#fff',
    fontSize: 24,
    fontWeight: 700,
    margin: 0,
    marginTop: 12,
    letterSpacing: 1,
    textShadow: '0 2px 10px rgba(0, 0, 0, 0.2)'
  };

  const subtitleStyle = {
    color: 'rgba(255, 255, 255, 0.8)',
    fontSize: 13,
    marginTop: 8
  };

  return (
    <div style={containerStyle}>
      <div style={backgroundStyle} />
      
      {/* Floating particles effect */}
      <div style={{ position: 'absolute', top: '10%', left: '10%', width: 6, height: 6, borderRadius: '50%', background: '#00a1e0', opacity: 0.6, animation: 'pulse 3s infinite' }} />
      <div style={{ position: 'absolute', top: '20%', right: '15%', width: 8, height: 8, borderRadius: '50%', background: '#5c6bc0', opacity: 0.5, animation: 'pulse 4s infinite' }} />
      <div style={{ position: 'absolute', bottom: '30%', left: '20%', width: 5, height: 5, borderRadius: '50%', background: '#00d4aa', opacity: 0.6, animation: 'pulse 2.5s infinite' }} />
      <div style={{ position: 'absolute', bottom: '15%', right: '25%', width: 7, height: 7, borderRadius: '50%', background: '#00a1e0', opacity: 0.4, animation: 'pulse 3.5s infinite' }} />
      
      <Card style={cardStyle} className="animate-fade-in-up">
        <div style={logoStyle}>
          <img src="/images/mulesoft.png" alt="MuleSoft" style={{ height: 60, width: 60, filter: 'brightness(0) invert(1)' }} />
          <h2 style={titleStyle}>MuleSoft</h2>
          <p style={subtitleStyle}>Anypoint Integration Platform</p>
        </div>
        
        <Tabs 
          centered
          items={[
            { 
              key: 'login', 
              label: <span style={{ fontWeight: 500, padding: '0 16px' }}>Sign In</span>, 
              children: (
                <Form onFinish={handleLogin} style={{ marginTop: 8 }}>
                  <Form.Item name="email" rules={[{ required: true, type: 'email', message: 'Please enter a valid email' }]}>
                    <Input 
                      prefix={<MailOutlined style={{ color: '#00a1e0' }} />} 
                      placeholder="Email address" 
                      size="large"
                      style={{ borderRadius: 10 }}
                    />
                  </Form.Item>
                  <Form.Item name="password" rules={[{ required: true, message: 'Please enter your password' }]}>
                    <Input.Password 
                      prefix={<LockOutlined style={{ color: '#00a1e0' }} />} 
                      placeholder="Password" 
                      size="large"
                      style={{ borderRadius: 10 }}
                    />
                  </Form.Item>
                  <Button 
                    type="primary" 
                    htmlType="submit" 
                    loading={loading} 
                    block 
                    size="large"
                    style={{ 
                      height: 48, 
                      borderRadius: 10, 
                      fontWeight: 600,
                      fontSize: 16,
                      background: 'linear-gradient(135deg, #00a1e0 0%, #5c6bc0 100%)',
                      border: 'none',
                      boxShadow: '0 4px 15px rgba(0, 161, 224, 0.4)'
                    }}
                  >
                    Sign In
                  </Button>
                </Form>
              )
            },
            { 
              key: 'register', 
              label: <span style={{ fontWeight: 500, padding: '0 16px' }}>Create Account</span>, 
              children: (
                <Form onFinish={handleRegister} style={{ marginTop: 8 }}>
                  <Form.Item name="fullName" rules={[{ required: true, message: 'Please enter your name' }]}>
                    <Input 
                      prefix={<UserOutlined style={{ color: '#00a1e0' }} />} 
                      placeholder="Full Name" 
                      size="large"
                      style={{ borderRadius: 10 }}
                    />
                  </Form.Item>
                  <Form.Item name="email" rules={[{ required: true, type: 'email', message: 'Please enter a valid email' }]}>
                    <Input 
                      prefix={<MailOutlined style={{ color: '#00a1e0' }} />} 
                      placeholder="Email address" 
                      size="large"
                      style={{ borderRadius: 10 }}
                    />
                  </Form.Item>
                  <Form.Item name="password" rules={[{ required: true, min: 6, message: 'Password must be at least 6 characters' }]}>
                    <Input.Password 
                      prefix={<LockOutlined style={{ color: '#00a1e0' }} />} 
                      placeholder="Password" 
                      size="large"
                      style={{ borderRadius: 10 }}
                    />
                  </Form.Item>
                  <Button 
                    type="primary" 
                    htmlType="submit" 
                    loading={loading} 
                    block 
                    size="large"
                    style={{ 
                      height: 48, 
                      borderRadius: 10, 
                      fontWeight: 600,
                      fontSize: 16,
                      background: 'linear-gradient(135deg, #00d4aa 0%, #00a1e0 100%)',
                      border: 'none',
                      boxShadow: '0 4px 15px rgba(0, 212, 170, 0.4)'
                    }}
                  >
                    Create Account
                  </Button>
                </Form>
              )
            }
          ]} 
        />
        
        <div style={{ textAlign: 'center', marginTop: 20, color: '#999', fontSize: 12 }}>
          Enterprise Integration Platform
        </div>
      </Card>
    </div>
  );
}
