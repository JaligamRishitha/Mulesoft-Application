import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Table, Tag, Tabs, Spin, Statistic, Button, message } from 'antd';
import { ShoppingCartOutlined, InboxOutlined, TeamOutlined, DollarOutlined, FactoryOutlined, ReloadOutlined } from '@ant-design/icons';
import axios from 'axios';

const sapApi = axios.create({
  baseURL: 'http://localhost:8100',
  headers: { 'Content-Type': 'application/json' }
});

export default function SapErp() {
  const [loading, setLoading] = useState(true);
  const [orders, setOrders] = useState([]);
  const [stock, setStock] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [vendors, setVendors] = useState([]);
  const [invoices, setInvoices] = useState([]);
  const [production, setProduction] = useState([]);
  const [health, setHealth] = useState(null);

  const fetchAll = async () => {
    setLoading(true);
    try {
      const [ordersRes, stockRes, customersRes, vendorsRes, invoicesRes, productionRes, healthRes] = await Promise.all([
        sapApi.get('/api/sales/orders'),
        sapApi.get('/api/inventory/stock'),
        sapApi.get('/api/customers'),
        sapApi.get('/api/vendors'),
        sapApi.get('/api/finance/invoices'),
        sapApi.get('/api/production/orders'),
        sapApi.get('/api/system/health')
      ]);
      setOrders(ordersRes.data.orders || []);
      setStock(stockRes.data.stock || []);
      setCustomers(customersRes.data.customers || []);
      setVendors(vendorsRes.data.vendors || []);
      setInvoices(invoicesRes.data.invoices || []);
      setProduction(productionRes.data.production_orders || []);
      setHealth(healthRes.data);
      message.success('SAP ERP data loaded');
    } catch (err) {
      message.error('Failed to fetch SAP ERP data');
      console.error(err);
    }
    setLoading(false);
  };

  useEffect(() => { fetchAll(); }, []);

  const orderColumns = [
    { title: 'Order ID', dataIndex: 'order_id', key: 'order_id' },
    { title: 'Customer', dataIndex: 'customer_name', key: 'customer_name' },
    { title: 'Order Date', dataIndex: 'order_date', key: 'order_date' },
    { title: 'Amount', dataIndex: 'total_amount', key: 'total_amount', render: v => `$${v?.toLocaleString()}` },
    { title: 'Status', dataIndex: 'status', key: 'status', render: s => <Tag color={s === 'shipped' ? 'green' : s === 'processing' ? 'blue' : 'default'}>{s}</Tag> }
  ];

  const stockColumns = [
    { title: 'Material ID', dataIndex: 'material_id', key: 'material_id' },
    { title: 'Description', dataIndex: 'material_description', key: 'material_description' },
    { title: 'Plant', dataIndex: 'plant', key: 'plant' },
    { title: 'Location', dataIndex: 'storage_location', key: 'storage_location' },
    { title: 'Available', dataIndex: 'available_stock', key: 'available_stock', render: v => <span style={{ color: v > 100 ? '#52c41a' : '#faad14' }}>{v}</span> },
    { title: 'Reserved', dataIndex: 'reserved_stock', key: 'reserved_stock' }
  ];

  const customerColumns = [
    { title: 'ID', dataIndex: 'customer_id', key: 'customer_id' },
    { title: 'Name', dataIndex: 'name', key: 'name' },
    { title: 'Industry', dataIndex: 'industry', key: 'industry' },
    { title: 'Credit Limit', dataIndex: 'credit_limit', key: 'credit_limit', render: v => `$${v?.toLocaleString()}` },
    { title: 'Credit Used', dataIndex: 'credit_used', key: 'credit_used', render: v => `$${v?.toLocaleString()}` },
    { title: 'Status', dataIndex: 'status', key: 'status', render: s => <Tag color={s === 'active' ? 'green' : 'default'}>{s}</Tag> }
  ];

  const vendorColumns = [
    { title: 'ID', dataIndex: 'vendor_id', key: 'vendor_id' },
    { title: 'Name', dataIndex: 'name', key: 'name' },
    { title: 'Industry', dataIndex: 'industry', key: 'industry' },
    { title: 'Payment Terms', dataIndex: 'payment_terms', key: 'payment_terms' },
    { title: 'Status', dataIndex: 'status', key: 'status', render: s => <Tag color={s === 'active' ? 'green' : 'default'}>{s}</Tag> }
  ];

  const invoiceColumns = [
    { title: 'Invoice ID', dataIndex: 'invoice_id', key: 'invoice_id' },
    { title: 'Order ID', dataIndex: 'order_id', key: 'order_id' },
    { title: 'Customer', dataIndex: 'customer_name', key: 'customer_name' },
    { title: 'Amount', dataIndex: 'total_amount', key: 'total_amount', render: v => `$${v?.toLocaleString()}` },
    { title: 'Due Date', dataIndex: 'due_date', key: 'due_date' },
    { title: 'Status', dataIndex: 'payment_status', key: 'payment_status', render: s => <Tag color={s === 'paid' ? 'green' : s === 'unpaid' ? 'orange' : 'red'}>{s}</Tag> }
  ];

  const productionColumns = [
    { title: 'Order ID', dataIndex: 'order_id', key: 'order_id' },
    { title: 'Material', dataIndex: 'material_description', key: 'material_description' },
    { title: 'Quantity', dataIndex: 'quantity', key: 'quantity' },
    { title: 'Work Center', dataIndex: 'work_center', key: 'work_center' },
    { title: 'Status', dataIndex: 'status', key: 'status', render: s => <Tag color={s === 'completed' ? 'green' : s === 'in_progress' ? 'blue' : 'default'}>{s}</Tag> }
  ];

  if (loading) return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />;

  const tabItems = [
    { key: 'orders', label: <span><ShoppingCartOutlined /> Sales Orders ({orders.length})</span>, children: <Table dataSource={orders} columns={orderColumns} rowKey="order_id" pagination={{ pageSize: 5 }} /> },
    { key: 'inventory', label: <span><InboxOutlined /> Inventory ({stock.length})</span>, children: <Table dataSource={stock} columns={stockColumns} rowKey="material_id" pagination={{ pageSize: 5 }} /> },
    { key: 'customers', label: <span><TeamOutlined /> Customers ({customers.length})</span>, children: <Table dataSource={customers} columns={customerColumns} rowKey="customer_id" pagination={{ pageSize: 5 }} /> },
    { key: 'vendors', label: <span><TeamOutlined /> Vendors ({vendors.length})</span>, children: <Table dataSource={vendors} columns={vendorColumns} rowKey="vendor_id" pagination={{ pageSize: 5 }} /> },
    { key: 'invoices', label: <span><DollarOutlined /> Invoices ({invoices.length})</span>, children: <Table dataSource={invoices} columns={invoiceColumns} rowKey="invoice_id" pagination={{ pageSize: 5 }} /> },
    { key: 'production', label: <span><FactoryOutlined /> Production ({production.length})</span>, children: <Table dataSource={production} columns={productionColumns} rowKey="order_id" pagination={{ pageSize: 5 }} /> }
  ];

  return (
    <div className="animate-fade-in">
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 24 }}>
        <div>
          <h2 style={{ marginBottom: 4 }}>SAP ERP Integration</h2>
          <p style={{ color: '#666', margin: 0 }}>Real-time data from SAP ERP system (localhost:8100)</p>
        </div>
        <Button icon={<ReloadOutlined />} onClick={fetchAll}>Refresh</Button>
      </div>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col span={4}>
          <Card size="small" style={{ borderTop: '4px solid #00a1e0' }}>
            <Statistic title="Sales Orders" value={orders.length} prefix={<ShoppingCartOutlined />} />
          </Card>
        </Col>
        <Col span={4}>
          <Card size="small" style={{ borderTop: '4px solid #52c41a' }}>
            <Statistic title="Stock Items" value={stock.length} prefix={<InboxOutlined />} />
          </Card>
        </Col>
        <Col span={4}>
          <Card size="small" style={{ borderTop: '4px solid #5c6bc0' }}>
            <Statistic title="Customers" value={customers.length} prefix={<TeamOutlined />} />
          </Card>
        </Col>
        <Col span={4}>
          <Card size="small" style={{ borderTop: '4px solid #faad14' }}>
            <Statistic title="Vendors" value={vendors.length} prefix={<TeamOutlined />} />
          </Card>
        </Col>
        <Col span={4}>
          <Card size="small" style={{ borderTop: '4px solid #ff4d4f' }}>
            <Statistic title="Invoices" value={invoices.length} prefix={<DollarOutlined />} />
          </Card>
        </Col>
        <Col span={4}>
          <Card size="small" style={{ borderTop: '4px solid #722ed1' }}>
            <Statistic title="Production" value={production.length} prefix={<FactoryOutlined />} />
          </Card>
        </Col>
      </Row>

      {health && (
        <Card size="small" style={{ marginBottom: 16 }}>
          <Row gutter={16}>
            <Col span={6}><strong>Service:</strong> {health.service}</Col>
            <Col span={6}><strong>Status:</strong> <Tag color="green">{health.status}</Tag></Col>
            <Col span={6}><strong>Version:</strong> {health.version}</Col>
            <Col span={6}><strong>Database:</strong> <Tag color="green">{health.components?.database}</Tag></Col>
          </Row>
        </Card>
      )}

      <Card>
        <Tabs items={tabItems} />
      </Card>
    </div>
  );
}
