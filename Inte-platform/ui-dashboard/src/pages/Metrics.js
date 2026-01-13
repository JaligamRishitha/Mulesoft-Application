import React, { useState } from 'react';
import { Card, Tabs, Alert, Button, Space, Tag } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';

const { TabPane } = Tabs;

export default function Metrics() {
  const [refreshKey, setRefreshKey] = useState(0);
  
  const prometheusUrl = 'http://localhost:9090';
  const grafanaUrl = 'http://localhost:3002';
  
  const handleRefresh = () => setRefreshKey(prev => prev + 1);
  
  const handleOpenExternal = (url) => window.open(url, '_blank');

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>Observability</h2>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={handleRefresh}>Refresh</Button>
        </Space>
      </div>

      <Alert
        message="Embedded Monitoring Dashboards"
        description="Prometheus collects metrics from all services. Grafana visualizes integration performance, API calls, and error rates."
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
      />

      <Tabs defaultActiveKey="grafana" type="card">
        <TabPane 
          tab={<span><Tag color="orange">Grafana</Tag> Dashboards</span>} 
          key="grafana"
        >
          <Card size="small">
            <iframe
              key={`grafana-${refreshKey}`}
              src={`${grafanaUrl}/d/mulesoft-main?orgId=1&kiosk`}
              width="100%"
              height="700"
              frameBorder="0"
              title="Grafana Dashboard"
              style={{ border: 'none', borderRadius: 4 }}
            />
          </Card>
        </TabPane>

        <TabPane 
          tab={<span><Tag color="red">Prometheus</Tag> Metrics</span>} 
          key="prometheus"
        >
          <Card size="small">
            <iframe
              key={`prometheus-${refreshKey}`}
              src={`${prometheusUrl}/graph`}
              width="100%"
              height="700"
              frameBorder="0"
              title="Prometheus"
              style={{ border: 'none', borderRadius: 4 }}
            />
          </Card>
        </TabPane>
      </Tabs>
    </div>
  );
}
