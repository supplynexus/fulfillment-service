'use client';

import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Chip,
  Button,
  Link,
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
  FormControl,
  Select,
  MenuItem,
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

interface OrderDetailsProps {
  orderId: string;
}

export function OrderDetails({ orderId }: OrderDetailsProps) {
  const router = useRouter();
  const [order, setOrder] = useState<Order | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedItemIds, setSelectedItemIds] = useState<Set<string>>(
    new Set()
  );
  const [quantityByItemId, setQuantityByItemId] = useState<
    Record<string, number>
  >({});
  const [creatingScm, setCreatingScm] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  // 编辑相关状态
  const [isEditing, setIsEditing] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);
  const [editFormData, setEditFormData] = useState({
    status: '',
    fulfillment_status: '',
    customer_name: '',
    customer_email: '',
    customer_phone: '',
    order_number: '',
    external_order_id: '',
    shopify_order_number: '',
    shopify_order_name: '',
  });

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

  const handleEditClick = () => {
    if (!order) return;
    
    setEditFormData({
      status: order.status || '',
      fulfillment_status: order.fulfillment_status || '',
      customer_name: order.customer_name || '',
      customer_email: order.customer_email || '',
      customer_phone: order.customer_phone || '',
      order_number: order.order_number || '',
      external_order_id: order.external_order_id || order.shopify_order_id || '',
      shopify_order_number: order.shopify_order_number || '',
      shopify_order_name: order.shopify_order_name || '',
    });
    setIsEditing(true);
    setEditError(null);
  };

  const handleEditCancel = () => {
    setIsEditing(false);
    setEditError(null);
    setEditFormData({
      status: '',
      fulfillment_status: '',
      customer_name: '',
      customer_email: '',
      customer_phone: '',
      order_number: '',
      external_order_id: '',
      shopify_order_number: '',
      shopify_order_name: '',
    });
  };

  const handleEditSave = async () => {
    if (!order) return;

    try {
      setEditing(true);
      setEditError(null);

      // 准备更新数据，只发送有变化的字段
      const updateData: any = {};
      if (editFormData.status !== order.status) {
        updateData.status = editFormData.status;
      }
      if (editFormData.fulfillment_status !== (order.fulfillment_status || '')) {
        updateData.fulfillment_status = editFormData.fulfillment_status || null;
      }
      if (editFormData.customer_name !== (order.customer_name || '')) {
        updateData.customer_name = editFormData.customer_name || null;
      }
      if (editFormData.customer_email !== order.customer_email) {
        updateData.customer_email = editFormData.customer_email;
      }
      if (editFormData.customer_phone !== (order.customer_phone || '')) {
        updateData.customer_phone = editFormData.customer_phone || null;
      }
      if (editFormData.order_number !== (order.order_number || '')) {
        updateData.order_number = editFormData.order_number || null;
      }
      if (editFormData.external_order_id !== (order.external_order_id || order.shopify_order_id || '')) {
        updateData.external_order_id = editFormData.external_order_id || null;
      }
      if (editFormData.shopify_order_number !== (order.shopify_order_number || '')) {
        updateData.shopify_order_number = editFormData.shopify_order_number || null;
      }
      if (editFormData.shopify_order_name !== (order.shopify_order_name || '')) {
        updateData.shopify_order_name = editFormData.shopify_order_name || null;
      }

      // 如果没有变化，直接退出编辑模式
      if (Object.keys(updateData).length === 0) {
        setIsEditing(false);
        return;
      }

      console.log('🔍 更新核心订单:', updateData);

      const response = await frontendApi.put(`/api/orders/${orderId}`, updateData);
      console.log('✅ 核心订单更新成功:', response.data);

      // 刷新订单详情
      await fetchOrderDetails();
      
      // 退出编辑模式
      setIsEditing(false);
    } catch (error: any) {
      console.error('❌ 更新核心订单失败:', error);
      setEditError(error?.response?.data?.detail || '更新核心订单失败');
    } finally {
      setEditing(false);
    }
  };

  const toggleSelectItem = (id: string, defaultQty: number) => {
    setSelectedItemIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
    setQuantityByItemId(prev => ({
      ...prev,
      [id]: prev[id] ?? defaultQty ?? 1,
    }));
  };

  const updateQty = (id: string, value: number) => {
    setQuantityByItemId(prev => ({
      ...prev,
      [id]: Math.max(1, Number(value) || 1),
    }));
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
            price: it.price || null,
            cost: it.cost || null,
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
        routing_metadata: {
          from_ui: 'orders/[id]',
          created_via: 'manual_select',
        },
        shopify_order_id: order.external_order_id || undefined,
      };

      const resp = await frontendApi.post('/api/scm-orders', body);
      const scm = resp.data;
      router.push(`/scm-orders/${scm.id_hashid}`);
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
            订单详情 #{order.order_number || order.id_hashid || order.id}
          </Typography>
        </Box>
        <Box>
          <Tooltip title='刷新'>
            <IconButton onClick={handleRefresh} disabled={loading}>
              <RefreshIcon />
            </IconButton>
          </Tooltip>
          {!isEditing ? (
            <Tooltip title='编辑'>
              <IconButton onClick={handleEditClick}>
                <EditIcon />
              </IconButton>
            </Tooltip>
          ) : (
            <>
              <Tooltip title='保存'>
                <IconButton onClick={handleEditSave} disabled={editing} color='primary'>
                  {editing ? <CircularProgress size={20} /> : '✓'}
                </IconButton>
              </Tooltip>
              <Tooltip title='取消'>
                <IconButton onClick={handleEditCancel} disabled={editing}>
                  ✕
                </IconButton>
              </Tooltip>
            </>
          )}
          <Tooltip title='打印'>
            <IconButton disabled>
              <PrintIcon />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      <Stack spacing={3}>
        {/* 地址验证结果提示 */}
        {order.address_validation_status &&
          order.address_validation_status !== 'valid' && (
            <Alert
              severity={
                order.address_validation_status === 'invalid'
                  ? 'error'
                  : order.address_validation_status === 'suspicious'
                    ? 'warning'
                    : 'info'
              }
            >
              {order.address_validation_status === 'invalid' && (
                <>
                  系统检测到该订单的收货地址可能不正确，请在发货前确认并必要时修改。
                  {order.address_validation_message && (
                    <>
                      {' '}
                      （原因: {order.address_validation_message}）
                    </>
                  )}
                </>
              )}
              {order.address_validation_status === 'suspicious' && (
                <>
                  系统检测到该订单的收货地址存在潜在问题，建议在发货前人工确认。
                  {order.address_validation_message && (
                    <>
                      {' '}
                      （原因: {order.address_validation_message}）
                    </>
                  )}
                </>
              )}
              {order.address_validation_status === 'failed' && (
                <>
                  地址验证服务暂时失败，目前无法自动判断地址是否有效。订单已继续处理，
                  建议在发货前按需人工检查。
                  {order.address_validation_message && (
                    <>
                      {' '}
                      （错误信息: {order.address_validation_message}）
                    </>
                  )}
                </>
              )}
            </Alert>
          )}

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
                {isEditing ? (
                  <FormControl size='small' sx={{ minWidth: 150 }}>
                    <Select
                      value={editFormData.status}
                      onChange={(e) => setEditFormData(prev => ({ ...prev, status: e.target.value }))}
                    >
                      <MenuItem value="pending">待处理</MenuItem>
                      <MenuItem value="processing">处理中</MenuItem>
                      <MenuItem value="fulfilled">已完成</MenuItem>
                      <MenuItem value="cancelled">已取消</MenuItem>
                      <MenuItem value="failed">失败</MenuItem>
                      <MenuItem value="refunded">已退款</MenuItem>
                    </Select>
                  </FormControl>
                ) : (
                  <Chip
                    label={order.status}
                    color={getStatusColor(order.status) as any}
                    size='medium'
                  />
                )}
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
                <Box display='flex' justifyContent='space-between' alignItems='center'>
                  <Typography variant='body2' color='text.secondary'>
                    Shopify订单ID:
                  </Typography>
                  {isEditing ? (
                    <TextField
                      size='small'
                      value={editFormData.external_order_id}
                      onChange={(e) => setEditFormData(prev => ({ ...prev, external_order_id: e.target.value }))}
                      placeholder='输入Shopify订单ID'
                      sx={{ width: 200 }}
                    />
                  ) : (
                    <Typography variant='body2' fontWeight='medium'>
                      {order.external_order_id || order.shopify_order_id || '未设置'}
                    </Typography>
                  )}
                </Box>
                <Box display='flex' justifyContent='space-between' alignItems='center'>
                  <Typography variant='body2' color='text.secondary'>
                    订单号:
                  </Typography>
                  {isEditing ? (
                    <TextField
                      size='small'
                      value={editFormData.order_number}
                      onChange={(e) => setEditFormData(prev => ({ ...prev, order_number: e.target.value }))}
                      placeholder='输入订单号'
                      sx={{ width: 200 }}
                    />
                  ) : (
                    <Typography variant='body2' fontWeight='medium'>
                      {order.order_number || '未设置'}
                    </Typography>
                  )}
                </Box>
                <Box display='flex' justifyContent='space-between' alignItems='center'>
                  <Typography variant='body2' color='text.secondary'>
                    Shopify订单号:
                  </Typography>
                  {isEditing ? (
                    <TextField
                      size='small'
                      value={editFormData.shopify_order_number}
                      onChange={(e) => setEditFormData(prev => ({ ...prev, shopify_order_number: e.target.value }))}
                      placeholder='输入Shopify订单号'
                      sx={{ width: 200 }}
                    />
                  ) : (
                    <Typography variant='body2' fontWeight='medium'>
                      {order.shopify_order_number || '未设置'}
                    </Typography>
                  )}
                </Box>
                <Box display='flex' justifyContent='space-between' alignItems='center'>
                  <Typography variant='body2' color='text.secondary'>
                    订单名称:
                  </Typography>
                  {isEditing ? (
                    <TextField
                      size='small'
                      value={editFormData.shopify_order_name}
                      onChange={(e) => setEditFormData(prev => ({ ...prev, shopify_order_name: e.target.value }))}
                      placeholder='输入订单名称'
                      sx={{ width: 200 }}
                    />
                  ) : (
                    <Typography variant='body2' fontWeight='medium'>
                      {order.shopify_order_name || '未设置'}
                    </Typography>
                  )}
                </Box>
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
                <Box display='flex' justifyContent='space-between' alignItems='center'>
                  <Typography variant='body2' color='text.secondary'>
                    履行状态:
                  </Typography>
                  {isEditing ? (
                    <FormControl size='small' sx={{ width: 200 }}>
                      <Select
                        value={editFormData.fulfillment_status}
                        onChange={(e) => setEditFormData(prev => ({ ...prev, fulfillment_status: e.target.value }))}
                        displayEmpty
                      >
                        <MenuItem value="">未设置</MenuItem>
                        <MenuItem value="unfulfilled">未履行</MenuItem>
                        <MenuItem value="partial">部分履行</MenuItem>
                        <MenuItem value="fulfilled">已履行</MenuItem>
                        <MenuItem value="shipped">已发货</MenuItem>
                        <MenuItem value="delivered">已送达</MenuItem>
                      </Select>
                    </FormControl>
                  ) : (
                    order.fulfillment_status ? (
                      <Typography variant='body2' fontWeight='medium'>
                        {order.fulfillment_status}
                      </Typography>
                    ) : (
                      <Typography variant='body2' color='text.secondary'>
                        未设置
                      </Typography>
                    )
                  )}
                </Box>
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
                <Box display='flex' justifyContent='space-between' alignItems='center'>
                  <Typography variant='body2' color='text.secondary'>
                    姓名:
                  </Typography>
                  {isEditing ? (
                    <TextField
                      size='small'
                      value={editFormData.customer_name}
                      onChange={(e) => setEditFormData(prev => ({ ...prev, customer_name: e.target.value }))}
                      placeholder='输入客户姓名'
                      sx={{ width: 200 }}
                    />
                  ) : (
                    <Typography variant='body2' fontWeight='medium'>
                      {order.customer_name || '未知'}
                    </Typography>
                  )}
                </Box>
                <Box display='flex' justifyContent='space-between' alignItems='center'>
                  <Typography variant='body2' color='text.secondary'>
                    邮箱:
                  </Typography>
                  {isEditing ? (
                    <TextField
                      size='small'
                      value={editFormData.customer_email}
                      onChange={(e) => setEditFormData(prev => ({ ...prev, customer_email: e.target.value }))}
                      placeholder='输入客户邮箱'
                      sx={{ width: 200 }}
                    />
                  ) : (
                    <Typography variant='body2' fontWeight='medium'>
                      {order.customer_email}
                    </Typography>
                  )}
                </Box>
                <Box display='flex' justifyContent='space-between' alignItems='center'>
                  <Typography variant='body2' color='text.secondary'>
                    电话:
                  </Typography>
                  {isEditing ? (
                    <TextField
                      size='small'
                      value={editFormData.customer_phone}
                      onChange={(e) => setEditFormData(prev => ({ ...prev, customer_phone: e.target.value }))}
                      placeholder='输入客户电话'
                      sx={{ width: 200 }}
                    />
                  ) : (
                    <Typography variant='body2' fontWeight='medium'>
                      {order.customer_phone || '未设置'}
                    </Typography>
                  )}
                </Box>
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
                      {order.shipping_address.province}{' '}
                      {order.shipping_address.zip}
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
                        {order.billing_address.province}{' '}
                        {order.billing_address.zip}
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

        {/* Line Items - 下单的商品 */}
        <Card>
          <CardContent>
            <Typography variant='h6' gutterBottom>
              下单的商品
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
                disabled={
                  creatingScm ||
                  selectedItemIds.size === 0 ||
                  order.status === OrderStatus.CANCELLED
                }
              >
                {creatingScm
                  ? '创建中...'
                  : order.status === OrderStatus.CANCELLED
                    ? '已取消订单不可创建SCM订单'
                    : `创建核心SCM订单（已选 ${selectedItemIds.size} 项）`}
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
                  {(order.line_items || []).length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={6} align='center' sx={{ py: 3 }}>
                        <Typography color='text.secondary'>
                          该订单暂无商品明细
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ) : (
                  (order.line_items || []).map(item => (
                    <TableRow key={String(item.id)}>
                      <TableCell padding='checkbox'>
                        <Checkbox
                          color='primary'
                          checked={selectedItemIds.has(item.id)}
                          disabled={order.status === OrderStatus.CANCELLED}
                          onChange={() =>
                            toggleSelectItem(item.id, item.quantity)
                          }
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
                          <Stack direction='row' spacing={1} sx={{ mt: 0.5 }} flexWrap='wrap' useFlexGap>
                            {item.shopify_product_url && (
                              <Link
                                href={item.shopify_product_url}
                                target='_blank'
                                rel='noopener noreferrer'
                                variant='caption'
                              >
                                Shopify 商品
                              </Link>
                            )}
                            {item.printify_product_url && (
                              <Link
                                href={item.printify_product_url}
                                target='_blank'
                                rel='noopener noreferrer'
                                variant='caption'
                              >
                                Printify 商品
                              </Link>
                            )}
                            {!item.printify_product_url && item.core_product_id_hashid && (
                              <Link
                                href={`/product-mapping/printify?core_product_id=${encodeURIComponent(item.core_product_id_hashid)}`}
                                variant='caption'
                              >
                                去绑定 Printify
                              </Link>
                            )}
                          </Stack>
                        </Box>
                      </TableCell>
                      <TableCell>
                        <Box>
                          {item.sku ? (
                            <Typography variant='body2' fontWeight='medium'>
                              SKU: {item.sku}
                            </Typography>
                          ) : (
                            <Typography variant='body2' color='text.secondary'>
                              SKU: 无
                            </Typography>
                          )}
                          {item.core_product_id && (
                            <Typography
                              variant='caption'
                              color='primary'
                              display='block'
                            >
                              核心商品: {item.core_product_id}
                            </Typography>
                          )}
                          {item.core_variant_id && (
                            <Typography
                              variant='caption'
                              color='primary'
                              display='block'
                            >
                              核心变体: {item.core_variant_id}
                            </Typography>
                          )}
                          {item.external_product_id && (
                            <Typography
                              variant='caption'
                              color='text.secondary'
                              display='block'
                            >
                              外部商品: {item.external_product_id}
                            </Typography>
                          )}
                          {item.external_variant_id && (
                            <Typography
                              variant='caption'
                              color='text.secondary'
                              display='block'
                            >
                              外部变体: {item.external_variant_id}
                            </Typography>
                          )}
                        </Box>
                      </TableCell>
                      <TableCell align='right'>
                        {selectedItemIds.has(item.id) ? (
                          <TextField
                            type='number'
                            size='small'
                            inputProps={{
                              min: 1,
                              style: { textAlign: 'right', width: 72 },
                            }}
                            value={
                              quantityByItemId[item.id] ?? item.quantity ?? 1
                            }
                            onChange={e =>
                              updateQty(item.id, Number(e.target.value))
                            }
                          />
                        ) : (
                          <Typography variant='body2'>
                            {item.quantity}
                          </Typography>
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
                  ))
                  )}
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

        {/* 编辑错误提示 */}
        {editError && (
          <Alert severity="error" onClose={() => setEditError(null)}>
            {editError}
          </Alert>
        )}


        {/* Shopify Fulfillment Information */}
        {order.external_data?.fulfillments && order.external_data.fulfillments.length > 0 && (
          <Card>
            <CardContent>
              <Typography variant='h6' gutterBottom>
                Shopify 履行信息
              </Typography>
              <Stack spacing={2}>
                {order.external_data.fulfillments.map((fulfillment: any, index: number) => (
                  <Box key={index} sx={{ p: 2, border: '1px solid', borderColor: 'divider', borderRadius: 1 }}>
                    <Typography variant='subtitle2' gutterBottom>
                      履行 #{index + 1}
                    </Typography>
                    <Stack spacing={1}>
                      <Box display='flex' justifyContent='space-between'>
                        <Typography variant='body2' color='text.secondary'>
                          履行ID:
                        </Typography>
                        <Typography variant='body2' fontWeight='medium' fontFamily="monospace" fontSize="0.75rem">
                          {fulfillment.id}
                        </Typography>
                      </Box>
                      <Box display='flex' justifyContent='space-between'>
                        <Typography variant='body2' color='text.secondary'>
                          状态:
                        </Typography>
                        <Typography variant='body2' fontWeight='medium'>
                          {fulfillment.status}
                        </Typography>
                      </Box>
                      {fulfillment.trackingInfo && fulfillment.trackingInfo.length > 0 && (
                        <Box>
                          <Typography variant='body2' color='text.secondary' gutterBottom>
                            跟踪信息:
                          </Typography>
                          {fulfillment.trackingInfo.map((tracking: any, trackingIndex: number) => (
                            <Box key={trackingIndex} sx={{ ml: 2, mt: 1 }}>
                              {tracking.number && (
                                <Box display='flex' justifyContent='space-between' mb={0.5}>
                                  <Typography variant='body2' color='text.secondary'>
                                    跟踪号:
                                  </Typography>
                                  <Typography variant='body2' fontWeight='medium' fontFamily="monospace" fontSize="0.75rem">
                                    {tracking.number}
                                  </Typography>
                                </Box>
                              )}
                              {tracking.company && (
                                <Box display='flex' justifyContent='space-between' mb={0.5}>
                                  <Typography variant='body2' color='text.secondary'>
                                    承运商:
                                  </Typography>
                                  <Typography variant='body2' fontWeight='medium'>
                                    {tracking.company}
                                  </Typography>
                                </Box>
                              )}
                              {tracking.url && (
                                <Box display='flex' justifyContent='space-between' mb={0.5}>
                                  <Typography variant='body2' color='text.secondary'>
                                    跟踪链接:
                                  </Typography>
                                  <Button
                                    size='small'
                                    href={tracking.url}
                                    target='_blank'
                                    rel='noopener noreferrer'
                                    variant='outlined'
                                  >
                                    查看物流
                                  </Button>
                                </Box>
                              )}
                            </Box>
                          ))}
                        </Box>
                      )}
                      {fulfillment.createdAt && (
                        <Box display='flex' justifyContent='space-between'>
                          <Typography variant='body2' color='text.secondary'>
                            创建时间:
                          </Typography>
                          <Typography variant='body2' fontWeight='medium'>
                            {formatDate(fulfillment.createdAt)}
                          </Typography>
                        </Box>
                      )}
                    </Stack>
                  </Box>
                ))}
              </Stack>
            </CardContent>
          </Card>
        )}
      </Stack>
    </Box>
  );
}
