'use client';

import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  CircularProgress,
  Alert,
  Button,
  Chip,
  Divider,
  Grid,
  Card,
  CardContent,
  IconButton,
  Tooltip,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from '@mui/material';
import {
  ArrowBack as ArrowBackIcon,
  Refresh as RefreshIcon,
  Edit as EditIcon,
  Print as PrintIcon,
} from '@mui/icons-material';
import { useRouter } from 'next/navigation';
import { frontendApi } from '@/lib/api';

interface ScmOrderDetailsProps {
  orderId: string;
}

interface ScmOrder {
  id: number;
  tenant_id: number;
  source_order_id?: number;
  target_system_type: string;
  target_system_id?: string;
  scm_order_number?: string;
  status: string;
  fulfillment_status?: string;
  routing_strategy?: string;
  line_items: any[];
  total_amount: number;
  currency: string;
  customer_email: string;
  customer_name?: string;
  customer_phone?: string;
  shipping_address: any;
  billing_address?: any;
  routing_metadata?: any;
  tracking_number?: string;
  tracking_url?: string;
  carrier?: string;
  shipped_at?: string;
  delivered_at?: string;
  error_message?: string;
  retry_count: number;
  last_retry_at?: string;
  created_at: string;
  updated_at?: string;
}

export function ScmOrderDetails({ orderId }: ScmOrderDetailsProps) {
  const router = useRouter();
  const [order, setOrder] = useState<ScmOrder | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchOrderDetails();
  }, [orderId]);

  const fetchOrderDetails = async () => {
    try {
      setLoading(true);
      setError(null);

      console.log(`🔍 正在获取SCM订单详情: /api/scm-orders/${orderId}`);
      const response = await frontendApi.get(`/api/scm-orders/${orderId}`);
      console.log('✅ SCM订单详情获取成功:', response.data);
      setOrder(response.data);
    } catch (err: any) {
      console.error('❌ Failed to fetch SCM order details:', err);
      setError(err.response?.data?.detail || 'Failed to fetch order details');
    } finally {
      setLoading(false);
    }
  };

  const handleBack = () => {
    router.push('/scm-orders');
  };

  const handleRefresh = () => {
    fetchOrderDetails();
  };

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'completed':
        return 'success';
      case 'processing':
        return 'warning';
      case 'pending':
        return 'info';
      case 'failed':
        return 'error';
      default:
        return 'default';
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  const formatCurrency = (amount: number, currency: string) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency || 'USD',
    }).format(amount);
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box>
        <Box display="flex" alignItems="center" mb={3}>
          <IconButton onClick={handleBack} sx={{ mr: 1 }}>
            <ArrowBackIcon />
          </IconButton>
          <Typography variant="h4" component="h1">
            SCM 订单详情
          </Typography>
        </Box>
        <Alert severity="error">{error}</Alert>
      </Box>
    );
  }

  if (!order) {
    return (
      <Box>
        <Box display="flex" alignItems="center" mb={3}>
          <IconButton onClick={handleBack} sx={{ mr: 1 }}>
            <ArrowBackIcon />
          </IconButton>
          <Typography variant="h4" component="h1">
            SCM 订单详情
          </Typography>
        </Box>
        <Alert severity="warning">订单不存在</Alert>
      </Box>
    );
  }

  return (
    <Box>
      <Box
        display="flex"
        alignItems="center"
        justifyContent="space-between"
        mb={3}
      >
        <Box display="flex" alignItems="center">
          <IconButton onClick={handleBack} sx={{ mr: 1 }}>
            <ArrowBackIcon />
          </IconButton>
          <Typography variant="h4" component="h1">
            SCM 订单详情 #{order.id}
          </Typography>
        </Box>
        <Box>
          <Tooltip title="刷新">
            <IconButton onClick={handleRefresh} disabled={loading}>
              <RefreshIcon />
            </IconButton>
          </Tooltip>
          <Tooltip title="编辑">
            <IconButton disabled>
              <EditIcon />
            </IconButton>
          </Tooltip>
          <Tooltip title="打印">
            <IconButton disabled>
              <PrintIcon />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      <Stack spacing={3}>
        {/* Order Status and Basic Info */}
        <Card>
          <CardContent>
            <Stack
              direction={{ xs: 'column', sm: 'row' }}
              spacing={2}
              alignItems="center"
            >
              <Box flex={1}>
                <Typography variant="h6" gutterBottom>
                  订单状态
                </Typography>
                <Chip
                  label={order.status}
                  color={getStatusColor(order.status) as any}
                  size="medium"
                />
              </Box>
              <Box flex={1}>
                <Typography variant="h6" gutterBottom>
                  订单金额
                </Typography>
                <Typography variant="h5" color="primary" fontWeight="bold">
                  {formatCurrency(order.total_amount, order.currency)}
                </Typography>
              </Box>
            </Stack>
          </CardContent>
        </Card>

        <Stack direction={{ xs: 'column', md: 'row' }} spacing={3}>
          {/* SCM Order Information */}
          <Card sx={{ flex: 1 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                SCM 订单信息
              </Typography>
              <Stack spacing={1}>
                <Box display="flex" justifyContent="space-between">
                  <Typography variant="body2" color="text.secondary">
                    SCM 订单ID:
                  </Typography>
                  <Typography variant="body2" fontWeight="medium">
                    #{order.id}
                  </Typography>
                </Box>
                {order.scm_order_number && (
                  <Box display="flex" justifyContent="space-between">
                    <Typography variant="body2" color="text.secondary">
                      SCM 订单号:
                    </Typography>
                    <Typography variant="body2" fontWeight="medium">
                      {order.scm_order_number}
                    </Typography>
                  </Box>
                )}
                <Box display="flex" justifyContent="space-between">
                  <Typography variant="body2" color="text.secondary">
                    目标系统:
                  </Typography>
                  <Typography variant="body2" fontWeight="medium">
                    {order.target_system_type}
                  </Typography>
                </Box>
                {order.target_system_id && (
                  <Box display="flex" justifyContent="space-between">
                    <Typography variant="body2" color="text.secondary">
                      目标系统ID:
                    </Typography>
                    <Typography variant="body2" fontWeight="medium">
                      {order.target_system_id}
                    </Typography>
                  </Box>
                )}
                {order.routing_metadata?.printify_order_id && (
                  <Box display="flex" justifyContent="space-between">
                    <Typography variant="body2" color="text.secondary">
                      Printify 订单ID:
                    </Typography>
                    <Typography variant="body2" fontWeight="medium" fontFamily="monospace">
                      {order.routing_metadata.printify_order_id}
                    </Typography>
                  </Box>
                )}
                {order.routing_metadata?.printify_shop_id && (
                  <Box display="flex" justifyContent="space-between">
                    <Typography variant="body2" color="text.secondary">
                      Printify 店铺ID:
                    </Typography>
                    <Typography variant="body2" fontWeight="medium">
                      {order.routing_metadata.printify_shop_id}
                    </Typography>
                  </Box>
                )}
                {order.routing_metadata?.app_order_id && (
                  <Box display="flex" justifyContent="space-between">
                    <Typography variant="body2" color="text.secondary">
                      应用订单ID:
                    </Typography>
                    <Typography variant="body2" fontWeight="medium" fontFamily="monospace">
                      {order.routing_metadata.app_order_id}
                    </Typography>
                  </Box>
                )}
                {order.fulfillment_status && (
                  <Box display="flex" justifyContent="space-between">
                    <Typography variant="body2" color="text.secondary">
                      履行状态:
                    </Typography>
                    <Chip
                      label={order.fulfillment_status}
                      color={getStatusColor(order.fulfillment_status) as any}
                      size="small"
                    />
                  </Box>
                )}
                <Box display="flex" justifyContent="space-between">
                  <Typography variant="body2" color="text.secondary">
                    创建时间:
                  </Typography>
                  <Typography variant="body2" fontWeight="medium">
                    {formatDate(order.created_at)}
                  </Typography>
                </Box>
                {order.updated_at && (
                  <Box display="flex" justifyContent="space-between">
                    <Typography variant="body2" color="text.secondary">
                      更新时间:
                    </Typography>
                    <Typography variant="body2" fontWeight="medium">
                      {formatDate(order.updated_at)}
                    </Typography>
                  </Box>
                )}
              </Stack>
            </CardContent>
          </Card>

          {/* Customer Information */}
          <Card sx={{ flex: 1 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                客户信息
              </Typography>
              <Stack spacing={1}>
                <Box display="flex" justifyContent="space-between">
                  <Typography variant="body2" color="text.secondary">
                    客户邮箱:
                  </Typography>
                  <Typography variant="body2" fontWeight="medium">
                    {order.customer_email}
                  </Typography>
                </Box>
                {order.customer_name && (
                  <Box display="flex" justifyContent="space-between">
                    <Typography variant="body2" color="text.secondary">
                      客户姓名:
                    </Typography>
                    <Typography variant="body2" fontWeight="medium">
                      {order.customer_name}
                    </Typography>
                  </Box>
                )}
                {order.customer_phone && (
                  <Box display="flex" justifyContent="space-between">
                    <Typography variant="body2" color="text.secondary">
                      客户电话:
                    </Typography>
                    <Typography variant="body2" fontWeight="medium">
                      {order.customer_phone}
                    </Typography>
                  </Box>
                )}
              </Stack>
            </CardContent>
          </Card>
        </Stack>

        <Stack direction={{ xs: 'column', md: 'row' }} spacing={3}>
          {/* Shipping Address */}
          <Card sx={{ flex: 1 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                收货地址
              </Typography>
              {order.shipping_address ? (
                <Stack spacing={1}>
                  {order.shipping_address.address1 && (
                    <Box display="flex" justifyContent="space-between">
                      <Typography variant="body2" color="text.secondary">
                        地址1:
                      </Typography>
                      <Typography variant="body2" fontWeight="medium">
                        {order.shipping_address.address1}
                      </Typography>
                    </Box>
                  )}
                  {order.shipping_address.address2 && (
                    <Box display="flex" justifyContent="space-between">
                      <Typography variant="body2" color="text.secondary">
                        地址2:
                      </Typography>
                      <Typography variant="body2" fontWeight="medium">
                        {order.shipping_address.address2}
                      </Typography>
                    </Box>
                  )}
                  {order.shipping_address.city && (
                    <Box display="flex" justifyContent="space-between">
                      <Typography variant="body2" color="text.secondary">
                        城市:
                      </Typography>
                      <Typography variant="body2" fontWeight="medium">
                        {order.shipping_address.city}
                      </Typography>
                    </Box>
                  )}
                  {(order.shipping_address.state || order.shipping_address.province) && (
                    <Box display="flex" justifyContent="space-between">
                      <Typography variant="body2" color="text.secondary">
                        州/省:
                      </Typography>
                      <Typography variant="body2" fontWeight="medium">
                        {order.shipping_address.state || order.shipping_address.province}
                      </Typography>
                    </Box>
                  )}
                  {order.shipping_address.zip && (
                    <Box display="flex" justifyContent="space-between">
                      <Typography variant="body2" color="text.secondary">
                        邮编:
                      </Typography>
                      <Typography variant="body2" fontWeight="medium">
                        {order.shipping_address.zip}
                      </Typography>
                    </Box>
                  )}
                  {order.shipping_address.country && (
                    <Box display="flex" justifyContent="space-between">
                      <Typography variant="body2" color="text.secondary">
                        国家:
                      </Typography>
                      <Typography variant="body2" fontWeight="medium">
                        {order.shipping_address.country}
                      </Typography>
                    </Box>
                  )}
                  {order.shipping_address.phone && (
                    <Box display="flex" justifyContent="space-between">
                      <Typography variant="body2" color="text.secondary">
                        电话:
                      </Typography>
                      <Typography variant="body2" fontWeight="medium">
                        {order.shipping_address.phone}
                      </Typography>
                    </Box>
                  )}
                </Stack>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  无收货地址信息
                </Typography>
              )}
            </CardContent>
          </Card>

          {/* Tracking Information */}
          <Card sx={{ flex: 1 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                物流信息
              </Typography>
              <Stack spacing={1}>
                {order.tracking_number && (
                  <Box display="flex" justifyContent="space-between">
                    <Typography variant="body2" color="text.secondary">
                      跟踪号:
                    </Typography>
                    <Typography variant="body2" fontWeight="medium" fontFamily="monospace">
                      {order.tracking_number}
                    </Typography>
                  </Box>
                )}
                {order.tracking_url && (
                  <Box display="flex" justifyContent="space-between">
                    <Typography variant="body2" color="text.secondary">
                      跟踪链接:
                    </Typography>
                    <Button
                      size="small"
                      href={order.tracking_url}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      查看跟踪
                    </Button>
                  </Box>
                )}
               {/* 从订单字段和 shipments 数据中提取物流公司、发货时间、送达时间 */}
               <Box display="flex" justifyContent="space-between">
                 <Typography variant="body2" color="text.secondary">
                   物流公司:
                 </Typography>
                 <Typography variant="body2" fontWeight="medium">
                   {order.carrier || order.routing_metadata?.shipments?.[0]?.carrier || '未提供'}
                 </Typography>
               </Box>
               <Box display="flex" justifyContent="space-between">
                 <Typography variant="body2" color="text.secondary">
                   发货时间:
                 </Typography>
                 <Typography variant="body2" fontWeight="medium">
                   {order.shipped_at ? formatDate(order.shipped_at) : order.routing_metadata?.shipments?.[0]?.shipped_at ? formatDate(order.routing_metadata.shipments[0].shipped_at) : '未发货'}
                 </Typography>
               </Box>
               <Box display="flex" justifyContent="space-between">
                 <Typography variant="body2" color="text.secondary">
                   送达时间:
                 </Typography>
                 <Typography variant="body2" fontWeight="medium">
                   {order.delivered_at ? formatDate(order.delivered_at) : order.routing_metadata?.shipments?.[0]?.delivered_at ? formatDate(order.routing_metadata.shipments[0].delivered_at) : '未送达'}
                 </Typography>
               </Box>
                {order.retry_count > 0 && (
                  <Box display="flex" justifyContent="space-between">
                    <Typography variant="body2" color="text.secondary">
                      重试次数:
                    </Typography>
                    <Typography variant="body2" fontWeight="medium">
                      {order.retry_count}
                    </Typography>
                  </Box>
                )}
                {order.error_message && (
                  <Box>
                    <Typography variant="body2" color="error">
                      错误信息: {order.error_message}
                    </Typography>
                  </Box>
                )}
              </Stack>
              
              {/* Printify Shipments 详细信息 */}
              {order.routing_metadata?.shipments && order.routing_metadata.shipments.length > 0 && (
                <Box sx={{ mt: 2 }}>
                  <Typography variant="subtitle1" gutterBottom>
                    Printify 发货详情
                  </Typography>
                  {order.routing_metadata.shipments.map((shipment: any, index: number) => (
                    <Box key={index} sx={{ mb: 2, p: 2, border: '1px solid #e0e0e0', borderRadius: 1 }}>
                      <Typography variant="subtitle2" gutterBottom>
                        包裹 {index + 1}
                      </Typography>
                      <Stack spacing={1}>
                        <Box display="flex" justifyContent="space-between">
                          <Typography variant="body2" color="text.secondary">
                            追踪号:
                          </Typography>
                          <Typography variant="body2" fontWeight="medium" fontFamily="monospace">
                            {shipment.number}
                          </Typography>
                        </Box>
                        <Box display="flex" justifyContent="space-between">
                          <Typography variant="body2" color="text.secondary">
                            物流公司:
                          </Typography>
                          <Typography variant="body2" fontWeight="medium">
                            {shipment.carrier}
                          </Typography>
                        </Box>
                        {shipment.url && (
                          <Box display="flex" justifyContent="space-between">
                            <Typography variant="body2" color="text.secondary">
                              追踪链接:
                            </Typography>
                            <Button
                              size="small"
                              href={shipment.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              variant="outlined"
                            >
                              查看物流状态
                            </Button>
                          </Box>
                        )}
                        <Box display="flex" justifyContent="space-between">
                          <Typography variant="body2" color="text.secondary">
                            发货时间:
                          </Typography>
                          <Typography variant="body2" fontWeight="medium">
                            {formatDate(shipment.shipped_at)}
                          </Typography>
                        </Box>
                        <Box display="flex" justifyContent="space-between">
                          <Typography variant="body2" color="text.secondary">
                            送达时间:
                          </Typography>
                          <Typography variant="body2" fontWeight="medium">
                            {shipment.delivered_at ? formatDate(shipment.delivered_at) : '未送达'}
                          </Typography>
                        </Box>
                      </Stack>
                    </Box>
                  ))}
                </Box>
              )}
            </CardContent>
          </Card>
        </Stack>

        {/* Line Items */}
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              商品清单
            </Typography>
            {order.line_items && order.line_items.length > 0 ? (
              <TableContainer component={Paper} variant="outlined">
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>商品名称</TableCell>
                      <TableCell>SKU</TableCell>
                      <TableCell>规格</TableCell>
                      <TableCell align="right">数量</TableCell>
                      <TableCell align="right">单价</TableCell>
                      <TableCell align="right">小计</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {order.line_items.map((item: any, index: number) => (
                      <TableRow key={index}>
                        <TableCell>
                          <Typography variant="body2" fontWeight="medium">
                            {item.metadata?.title || item.title || `商品 ${index + 1}`}
                          </Typography>
                          {item.metadata?.variant_label && (
                            <Typography variant="caption" color="text.secondary">
                              {item.metadata.variant_label}
                            </Typography>
                          )}
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" fontFamily="monospace">
                            {item.metadata?.sku || item.sku || 'N/A'}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" color="text.secondary">
                            {item.metadata?.variant_label || item.variant_title || 'N/A'}
                          </Typography>
                        </TableCell>
                        <TableCell align="right">
                          <Typography variant="body2">
                            {item.quantity || 1}
                          </Typography>
                        </TableCell>
                        <TableCell align="right">
                          <Typography variant="body2">
                            {formatCurrency(
                              (item.metadata?.price || item.cost || item.price || 0) / 100, 
                              item.currency || order.currency
                            )}
                          </Typography>
                        </TableCell>
                        <TableCell align="right">
                          <Typography variant="body2" fontWeight="medium">
                            {formatCurrency(
                              ((item.metadata?.price || item.cost || item.price || 0) / 100) * (item.quantity || 1),
                              item.currency || order.currency
                            )}
                          </Typography>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            ) : (
              <Typography variant="body2" color="text.secondary">
                无商品信息
              </Typography>
            )}
          </CardContent>
        </Card>
      </Stack>
    </Box>
  );
}
