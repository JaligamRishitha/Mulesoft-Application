import React, { useState, useEffect } from 'react';
import { Card, Button, Alert, Spin } from 'antd';
import { backendApi as api } from '../api';

const ApiTest = () => {
  const [testResult, setTestResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const testConnection = async () => {
    setLoading(true);
    try {
      // Test direct connection to backend
      const response = await api.get('/test');
      setTestResult({
        success: true,
        message: 'Backend connection successful!',
        data: response.data
      });
    } catch (error) {
      console.error('API Test Error:', error);
      setTestResult({
        success: false,
        message: 'Backend connection failed',
        error: error.message,
        details: {
          baseURL: api.defaults.baseURL,
          errorCode: error.code,
          errorResponse: error.response?.data
        }
      });
    } finally {
      setLoading(false);
    }
  };

  const testHealthEndpoint = async () => {
    setLoading(true);
    try {
      // Test health endpoint directly
      const response = await fetch('http://localhost:8085/health');
      const data = await response.json();
      setTestResult({
        success: true,
        message: 'Health endpoint working!',
        data: data
      });
    } catch (error) {
      setTestResult({
        success: false,
        message: 'Health endpoint failed',
        error: error.message
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Auto-test on component mount
    testConnection();
  }, []);

  return (
    <Card title="🔧 API Connection Test" style={{ margin: '20px 0' }}>
      <div style={{ marginBottom: 16 }}>
        <Button onClick={testConnection} loading={loading} type="primary" style={{ marginRight: 8 }}>
          Test API Connection
        </Button>
        <Button onClick={testHealthEndpoint} loading={loading}>
          Test Health Endpoint
        </Button>
      </div>
      
      {loading && <Spin size="large" />}
      
      {testResult && (
        <Alert
          type={testResult.success ? 'success' : 'error'}
          message={testResult.message}
          description={
            <div>
              {testResult.data && (
                <pre style={{ background: '#f5f5f5', padding: 8, borderRadius: 4 }}>
                  {JSON.stringify(testResult.data, null, 2)}
                </pre>
              )}
              {testResult.error && (
                <div>
                  <strong>Error:</strong> {testResult.error}
                  {testResult.details && (
                    <pre style={{ background: '#fff2f0', padding: 8, borderRadius: 4, marginTop: 8 }}>
                      {JSON.stringify(testResult.details, null, 2)}
                    </pre>
                  )}
                </div>
              )}
            </div>
          }
          showIcon
        />
      )}
    </Card>
  );
};

export default ApiTest;