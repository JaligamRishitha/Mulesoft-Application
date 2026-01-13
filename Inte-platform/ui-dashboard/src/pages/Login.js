import React, { useState } from 'react';
import { Form, Input, Button, Card, message, Tabs } from 'antd';
import { UserOutlined, LockOutlined, MailOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import api from '../api';

export default function Login() {
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleLogin = async (values) => {
    setLoading(true);
    try {
      const { data } = await api.post('/auth/login', values);
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
      await api.post('/auth/register', { email: values.email, password: values.password, full_name: values.fullName });
      message.success('Registration successful! Please login.');
    } catch (err) {
      message.error(err.response?.data?.detail || 'Registration failed');
    }
    setLoading(false);
  };

  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh', background: '#f0f2f5' }}>
      <Card style={{ width: 400 }}>
        <h2 style={{ textAlign: 'center' }}>MuleSoft Anypoint Platform</h2>
        <Tabs items={[
          { key: 'login', label: 'Login', children: (
            <Form onFinish={handleLogin}>
              <Form.Item name="email" rules={[{ required: true, type: 'email' }]}>
                <Input prefix={<MailOutlined />} placeholder="Email" />
              </Form.Item>
              <Form.Item name="password" rules={[{ required: true }]}>
                <Input.Password prefix={<LockOutlined />} placeholder="Password" />
              </Form.Item>
              <Button type="primary" htmlType="submit" loading={loading} block>Login</Button>
            </Form>
          )},
          { key: 'register', label: 'Register', children: (
            <Form onFinish={handleRegister}>
              <Form.Item name="fullName" rules={[{ required: true }]}>
                <Input prefix={<UserOutlined />} placeholder="Full Name" />
              </Form.Item>
              <Form.Item name="email" rules={[{ required: true, type: 'email' }]}>
                <Input prefix={<MailOutlined />} placeholder="Email" />
              </Form.Item>
              <Form.Item name="password" rules={[{ required: true, min: 6 }]}>
                <Input.Password prefix={<LockOutlined />} placeholder="Password" />
              </Form.Item>
              <Button type="primary" htmlType="submit" loading={loading} block>Register</Button>
            </Form>
          )}
        ]} />
      </Card>
    </div>
  );
}
