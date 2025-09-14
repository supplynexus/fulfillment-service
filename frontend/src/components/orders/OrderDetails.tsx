'use client';

import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Chip,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Alert,
  CircularProgress,
  IconButton,
  Tooltip,
  Stack,
} from '@mui/material';
import {
  ArrowBack as ArrowBackIcon,
  Refresh as RefreshIcon,
  Edit as EditIcon,
  Print as PrintIcon,
  LocalShipping as LocalShippingIcon,
} from '@mui/icons-material';
import { useRouter } from 'next/navigation';
import { Order, OrderStatus } from '@/types/order';
import { frontendApi } from '@/lib/api';
import { CreatePrintifyOrderButton } from './CreatePrintifyOrderButton';

interface OrderDetailsProps {
  orderId: string;
}

export function OrderDetails({ orderId }: OrderDetailsProps) {
  const router = useRouter();
  const [order, setOrder] = useState<Order | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchOrderDetails = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await frontendApi.get(`/api/orders/${orderId}`);
      setOrder(response.data);
    } catch (err: any) {
      console.error('Failed to fetch order details:', err);
      setError(err.response?.data?.detail || 'Failed to fetch order details');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOrderDetails();
  }, [orderId]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleBack = () => {
    router.push('/orders');
  };

  const handleRefresh = () => {
    fetchOrderDetails();
  };

  const handleCreateShippingLabel = async () => {
    try {
      console.log('开始创建发货单', orderId);

      // 调用 backend API 创建发货单
      const response = await frontendApi.post(
        `/api/orders/${orderId}/create-shipping-label`
      );

      if (response.data.success) {
        console.log('✅ 发货单创建成功:', response.data);
        // 这里可以显示成功消息或者更新UI
        alert(
          `发货单创建成功！\nPrintify 订单ID: ${response.data.printify_order_id}\n状态: ${response.data.status}`
        );
      } else {
        console.error('❌ 发货单创建失败:', response.data);
        alert('发货单创建失败: ' + (response.data.message || '未知错误'));
      }
    } catch (error: any) {
      console.error('❌ 创建发货单时发生错误:', error);
      const errorMessage =
        error.response?.data?.detail || error.message || '创建发货单失败';
      alert('创建发货单失败: ' + errorMessage);
    }
  };

  const getStatusColor = (status: OrderStatus) => {
    switch (status) {
      case OrderStatus.PENDING:
        return 'warning';
      case OrderStatus.PROCESSING:
        return 'info';
      case OrderStatus.FULFILLED:
        return 'success';
      case OrderStatus.CANCELLED:
        return 'error';
      case OrderStatus.FAILED:
        return 'error';
      case OrderStatus.REFUNDED:
        return 'default';
      default:
        return 'default';
    }
  };

  const formatCurrency = (amount: number, currency: string) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency || 'USD',
    }).format(amount);
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

  if (loading) {
    return (
      <Box
        display='flex'
        justifyContent='center'
        alignItems='center'
        minHeight='400px'
      >
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box>
        <Box display='flex' alignItems='center' mb={3}>
          <IconButton onClick={handleBack} sx={{ mr: 1 }}>
            <ArrowBackIcon />
          </IconButton>
          <Typography variant='h4' component='h1'>
            订单详情
          </Typography>
        </Box>
        <Alert severity='error'>{error}</Alert>
      </Box>
    );
  }

  if (!order) {
    return (
      <Box>
        <Box display='flex' alignItems='center' mb={3}>
          <IconButton onClick={handleBack} sx={{ mr: 1 }}>
            <ArrowBackIcon />
          </IconButton>
          <Typography variant='h4' component='h1'>
            订单详情
          </Typography>
        </Box>
        <Alert severity='warning'>订单不存在</Alert>
      </Box>
    );
  }

  return (
    <Box>
      <Box
        display='flex'
        alignItems='center'
        justifyContent='space-between'
        mb={3}
      >
        <Box display='flex' alignItems='center'>
          <IconButton onClick={handleBack} sx={{ mr: 1 }}>
            <ArrowBackIcon />
          </IconButton>
          <Typography variant='h4' component='h1'>
            订单详情 #{order.id}
          </Typography>
        </Box>
        <Box>
          <Tooltip title='刷新'>
            <IconButton onClick={handleRefresh} disabled={loading}>
              <RefreshIcon />
            </IconButton>
          </Tooltip>
          <CreatePrintifyOrderButton
            orderId={order.id}
            orderData={{
              customer_name: order.customer_name,
              customer_email: order.customer_email,
              shipping_address: order.shipping_address,
            }}
          />
          <Tooltip title='编辑'>
            <IconButton disabled>
              <EditIcon />
            </IconButton>
          </Tooltip>
          <Tooltip title='打印'>
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
              alignItems='center'
            >
              <Box flex={1}>
                <Typography variant='h6' gutterBottom>
                  订单状态
                </Typography>
                <Chip
                  label={order.status}
                  color={getStatusColor(order.status) as any}
                  size='medium'
                />
              </Box>
              <Box flex={1}>
                <Typography variant='h6' gutterBottom>
                  订单金额
                </Typography>
                <Typography variant='h5' color='primary' fontWeight='bold'>
                  {formatCurrency(order.total_amount, order.currency)}
                </Typography>
              </Box>
            </Stack>
          </CardContent>
        </Card>

        <Stack direction={{ xs: 'column', md: 'row' }} spacing={3}>
          {/* Order Information */}
          <Card sx={{ flex: 1 }}>
            <CardContent>
              <Typography variant='h6' gutterBottom>
                订单信息
              </Typography>
              <Stack spacing={1}>
                <Box display='flex' justifyContent='space-between'>
                  <Typography variant='body2' color='text.secondary'>
                    Shopify订单ID:
                  </Typography>
                  <Typography variant='body2' fontWeight='medium'>
                    {order.shopify_order_id}
                  </Typography>
                </Box>
                {order.shopify_order_number && (
                  <Box display='flex' justifyContent='space-between'>
                    <Typography variant='body2' color='text.secondary'>
                      订单号:
                    </Typography>
                    <Typography variant='body2' fontWeight='medium'>
                      {order.shopify_order_number}
                    </Typography>
                  </Box>
                )}
                {order.shopify_order_name && (
                  <Box display='flex' justifyContent='space-between'>
                    <Typography variant='body2' color='text.secondary'>
                      订单名称:
                    </Typography>
                    <Typography variant='body2' fontWeight='medium'>
                      {order.shopify_order_name}
                    </Typography>
                  </Box>
                )}
                <Box display='flex' justifyContent='space-between'>
                  <Typography variant='body2' color='text.secondary'>
                    订单日期:
                  </Typography>
                  <Typography variant='body2' fontWeight='medium'>
                    {formatDate(order.order_date)}
                  </Typography>
                </Box>
                {order.processed_at && (
                  <Box display='flex' justifyContent='space-between'>
                    <Typography variant='body2' color='text.secondary'>
                      处理时间:
                    </Typography>
                    <Typography variant='body2' fontWeight='medium'>
                      {formatDate(order.processed_at)}
                    </Typography>
                  </Box>
                )}
                {order.fulfilled_at && (
                  <Box display='flex' justifyContent='space-between'>
                    <Typography variant='body2' color='text.secondary'>
                      完成时间:
                    </Typography>
                    <Typography variant='body2' fontWeight='medium'>
                      {formatDate(order.fulfilled_at)}
                    </Typography>
                  </Box>
                )}
              </Stack>
            </CardContent>
          </Card>

          {/* Customer Information */}
          <Card sx={{ flex: 1 }}>
            <CardContent>
              <Typography variant='h6' gutterBottom>
                客户信息
              </Typography>
              <Stack spacing={1}>
                <Box display='flex' justifyContent='space-between'>
                  <Typography variant='body2' color='text.secondary'>
                    姓名:
                  </Typography>
                  <Typography variant='body2' fontWeight='medium'>
                    {order.customer_name || '未知'}
                  </Typography>
                </Box>
                <Box display='flex' justifyContent='space-between'>
                  <Typography variant='body2' color='text.secondary'>
                    邮箱:
                  </Typography>
                  <Typography variant='body2' fontWeight='medium'>
                    {order.customer_email}
                  </Typography>
                </Box>
                {order.customer_phone && (
                  <Box display='flex' justifyContent='space-between'>
                    <Typography variant='body2' color='text.secondary'>
                      电话:
                    </Typography>
                    <Typography variant='body2' fontWeight='medium'>
                      {order.customer_phone}
                    </Typography>
                  </Box>
                )}
                <Box display='flex' justifyContent='space-between'>
                  <Typography variant='body2' color='text.secondary'>
                    客户ID:
                  </Typography>
                  <Typography variant='body2' fontWeight='medium'>
                    {order.customer_id}
                  </Typography>
                </Box>
              </Stack>
            </CardContent>
          </Card>
        </Stack>

        <Stack direction={{ xs: 'column', md: 'row' }} spacing={3}>
          {/* Shipping Address */}
          <Card sx={{ flex: 1 }}>
            <CardContent>
              <Typography variant='h6' gutterBottom>
                收货地址
              </Typography>
              <Box>
                <Typography variant='body2' fontWeight='medium'>
                  {order.shipping_address.first_name}{' '}
                  {order.shipping_address.last_name}
                </Typography>
                {order.shipping_address.company && (
                  <Typography variant='body2'>
                    {order.shipping_address.company}
                  </Typography>
                )}
                <Typography variant='body2'>
                  {order.shipping_address.address1}
                </Typography>
                {order.shipping_address.address2 && (
                  <Typography variant='body2'>
                    {order.shipping_address.address2}
                  </Typography>
                )}
                <Typography variant='body2'>
                  {order.shipping_address.city},{' '}
                  {order.shipping_address.province} {order.shipping_address.zip}
                </Typography>
                <Typography variant='body2'>
                  {order.shipping_address.country}
                </Typography>
                {order.shipping_address.phone && (
                  <Typography variant='body2'>
                    电话: {order.shipping_address.phone}
                  </Typography>
                )}
              </Box>
            </CardContent>
          </Card>

          {/* Billing Address */}
          {order.billing_address && (
            <Card sx={{ flex: 1 }}>
              <CardContent>
                <Typography variant='h6' gutterBottom>
                  账单地址
                </Typography>
                <Box>
                  <Typography variant='body2' fontWeight='medium'>
                    {order.billing_address.first_name}{' '}
                    {order.billing_address.last_name}
                  </Typography>
                  {order.billing_address.company && (
                    <Typography variant='body2'>
                      {order.billing_address.company}
                    </Typography>
                  )}
                  <Typography variant='body2'>
                    {order.billing_address.address1}
                  </Typography>
                  {order.billing_address.address2 && (
                    <Typography variant='body2'>
                      {order.billing_address.address2}
                    </Typography>
                  )}
                  <Typography variant='body2'>
                    {order.billing_address.city},{' '}
                    {order.billing_address.province} {order.billing_address.zip}
                  </Typography>
                  <Typography variant='body2'>
                    {order.billing_address.country}
                  </Typography>
                  {order.billing_address.phone && (
                    <Typography variant='body2'>
                      电话: {order.billing_address.phone}
                    </Typography>
                  )}
                </Box>
              </CardContent>
            </Card>
          )}
        </Stack>

        {/* Line Items */}
        <Card>
          <CardContent>
            <Typography variant='h6' gutterBottom>
              商品清单
            </Typography>
            <TableContainer component={Paper} variant='outlined'>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>商品</TableCell>
                    <TableCell>SKU</TableCell>
                    <TableCell align='right'>数量</TableCell>
                    <TableCell align='right'>单价</TableCell>
                    <TableCell align='right'>小计</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {order.line_items.map(item => (
                    <TableRow key={item.id}>
                      <TableCell>
                        <Box>
                          <Typography variant='body2' fontWeight='medium'>
                            {item.title}
                          </Typography>
                          {item.variant_title && (
                            <Typography
                              variant='caption'
                              color='text.secondary'
                            >
                              {item.variant_title}
                            </Typography>
                          )}
                        </Box>
                      </TableCell>
                      <TableCell>
                        <Typography variant='body2'>
                          {item.sku || '-'}
                        </Typography>
                      </TableCell>
                      <TableCell align='right'>
                        <Typography variant='body2'>{item.quantity}</Typography>
                      </TableCell>
                      <TableCell align='right'>
                        <Typography variant='body2'>
                          {formatCurrency(item.price, order.currency)}
                        </Typography>
                      </TableCell>
                      <TableCell align='right'>
                        <Typography variant='body2' fontWeight='medium'>
                          {formatCurrency(
                            item.price * item.quantity,
                            order.currency
                          )}
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>

        {/* Error Information */}
        {order.error_message && (
          <Card>
            <CardContent>
              <Typography variant='h6' gutterBottom color='error'>
                错误信息
              </Typography>
              <Alert severity='error'>{order.error_message}</Alert>
              <Box mt={2}>
                <Typography variant='body2' color='text.secondary'>
                  重试次数: {order.retry_count}
                </Typography>
                {order.last_retry_at && (
                  <Typography variant='body2' color='text.secondary'>
                    最后重试时间: {formatDate(order.last_retry_at)}
                  </Typography>
                )}
              </Box>
            </CardContent>
          </Card>
        )}

        {/* Tracking Information */}
        {(order.tracking_number || order.tracking_url) && (
          <Card>
            <CardContent>
              <Typography variant='h6' gutterBottom>
                物流信息
              </Typography>
              <Stack spacing={1}>
                {order.tracking_number && (
                  <Box display='flex' justifyContent='space-between'>
                    <Typography variant='body2' color='text.secondary'>
                      追踪号:
                    </Typography>
                    <Typography variant='body2' fontWeight='medium'>
                      {order.tracking_number}
                    </Typography>
                  </Box>
                )}
                {order.tracking_url && (
                  <Box display='flex' justifyContent='space-between'>
                    <Typography variant='body2' color='text.secondary'>
                      追踪链接:
                    </Typography>
                    <Button
                      size='small'
                      href={order.tracking_url}
                      target='_blank'
                      rel='noopener noreferrer'
                    >
                      查看物流
                    </Button>
                  </Box>
                )}
                {order.fulfillment_status && (
                  <Box display='flex' justifyContent='space-between'>
                    <Typography variant='body2' color='text.secondary'>
                      履行状态:
                    </Typography>
                    <Typography variant='body2' fontWeight='medium'>
                      {order.fulfillment_status}
                    </Typography>
                  </Box>
                )}
              </Stack>
            </CardContent>
          </Card>
        )}
      </Stack>
    </Box>
  );
}
