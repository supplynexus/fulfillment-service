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
  Checkbox,
  TextField,
} from '@mui/material';
import {
  ArrowBack as ArrowBackIcon,
  Refresh as RefreshIcon,
  Edit as EditIcon,
  Print as PrintIcon,
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
  const [selectedItemIds, setSelectedItemIds] = useState<Set<number>>(new Set());
  const [quantityByItemId, setQuantityByItemId] = useState<Record<number, number>>({});
  const [creatingScm, setCreatingScm] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

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

  const toggleSelectItem = (id: number, defaultQty: number) => {
    setSelectedItemIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
    setQuantityByItemId(prev => ({ ...prev, [id]: prev[id] ?? defaultQty ?? 1 }));
  };

  const updateQty = (id: number, value: number) => {
    setQuantityByItemId(prev => ({ ...prev, [id]: Math.max(1, Number(value) || 1) }));
  };

  const handleCreateScmOrder = async () => {
    if (!order) return;
    if (selectedItemIds.size === 0) {
      setCreateError('请先选择要发送的商品');
      return;
    }
    try {
      setCreatingScm(true);
      setCreateError(null);
      const items = (order.line_items || [])
        .filter(it => selectedItemIds.has(it.id))
        .map(it => ({
          core_product_id: it.core_product_id ?? null,
          core_variant_id: it.core_variant_id ?? null,
          quantity: quantityByItemId[it.id] ?? it.quantity ?? 1,
          item_metadata: {
            source_line_item_id: it.id,
            sku: it.sku || null,
            title: it.title || null,
            variant_title: it.variant_title || null,
          },
        }));

      const body = {
        source_order_ids: [order.id_hashid],
        routing_strategy: 'manual',
        line_items: items,
        currency: order.currency || 'USD',
        customer_email: order.customer_email || 'no-email@example.com',
        customer_name: order.customer_name || undefined,
        customer_phone: order.customer_phone || undefined,
        shipping_address: order.shipping_address,
        billing_address: order.billing_address || undefined,
        routing_metadata: { from_ui: 'orders/[id]', created_via: 'manual_select' },
        shopify_order_id: order.external_order_id || undefined,
      };

      const resp = await frontendApi.post('/api/scm-orders', body);
      const scm = resp.data;
      router.push(`/scm-orders/${scm.id}`);
    } catch (e: any) {
      console.error('创建SCM订单失败', e);
      setCreateError(e?.response?.data?.detail || '创建SCM订单失败');
    } finally {
      setCreatingScm(false);
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
            orderId={order.id_hashid}
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
                    {order.external_order_id || order.shopify_order_id}
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
                {order.customer_id && (
                  <Box display='flex' justifyContent='space-between'>
                    <Typography variant='body2' color='text.secondary'>
                      客户ID:
                    </Typography>
                    <Typography variant='body2' fontWeight='medium'>
                      {order.customer_id}
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
              <Typography variant='h6' gutterBottom>
                收货地址
              </Typography>
              <Box>
                {order.shipping_address ? (
                  <>
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
                  </>
                ) : (
                  <Typography variant='body2' color='text.secondary'>
                    收货地址信息不可用
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
                  {order.billing_address ? (
                    <>
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
                    </>
                  ) : (
                    <Typography variant='body2' color='text.secondary'>
                      账单地址信息不可用
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
            {createError && (
              <Alert severity='error' sx={{ mb: 2 }}>
                {createError}
              </Alert>
            )}
              <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} mb={2}>
                <Button
                  variant='contained'
                  onClick={handleCreateScmOrder}
                  disabled={creatingScm || selectedItemIds.size === 0}
                >
                  {creatingScm ? '创建中...' : `创建核心SCM订单（已选 ${selectedItemIds.size} 项）`}
                </Button>
              </Stack>
            <TableContainer component={Paper} variant='outlined'>
              <Table>
                <TableHead>
                  <TableRow>
                      <TableCell padding='checkbox'>选择</TableCell>
                    <TableCell>商品</TableCell>
                    <TableCell>SKU</TableCell>
                      <TableCell align='right'>数量</TableCell>
                      <TableCell align='right'>单价</TableCell>
                      <TableCell align='right'>小计</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {(order.line_items || []).map(item => (
                    <TableRow key={item.id}>
                        <TableCell padding='checkbox'>
                          <Checkbox
                            color='primary'
                            checked={selectedItemIds.has(item.id)}
                            onChange={() => toggleSelectItem(item.id, item.quantity)}
                          />
                        </TableCell>
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
                          {selectedItemIds.has(item.id) ? (
                            <TextField
                              type='number'
                              size='small'
                              inputProps={{ min: 1, style: { textAlign: 'right', width: 72 } }}
                              value={quantityByItemId[item.id] ?? item.quantity ?? 1}
                              onChange={e => updateQty(item.id, Number(e.target.value))}
                            />
                          ) : (
                            <Typography variant='body2'>{item.quantity}</Typography>
                          )}
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
