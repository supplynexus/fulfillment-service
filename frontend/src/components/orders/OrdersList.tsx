'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  Button,
  TextField,
  InputAdornment,
  IconButton,
  Tooltip,
  Alert,
  CircularProgress,
} from '@mui/material';
import {
  Search as SearchIcon,
  Refresh as RefreshIcon,
  Visibility as ViewIcon,
  FilterList as FilterIcon,
  Sync as SyncIcon,
} from '@mui/icons-material';
import { useRouter } from 'next/navigation';
import { Order, OrderStatus } from '@/types/order';
import { frontendApi } from '@/lib/api';

const ITEMS_PER_PAGE = 1000; // 显示所有订单，设置一个较大的值

export function OrdersList() {
  const router = useRouter();
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  // 移除分页相关状态，显示所有订单
  const [syncing, setSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState<string | null>(null);

  const fetchOrders = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await frontendApi.get('/api/orders', {
        params: {
          limit: ITEMS_PER_PAGE,
          search: searchTerm || undefined,
        },
      });

      setOrders(response.data.orders || []);
    } catch (err: any) {
      console.error('Failed to fetch orders:', err);
      setError(err.response?.data?.detail || 'Failed to fetch orders');
    } finally {
      setLoading(false);
    }
  }, [searchTerm]);

  useEffect(() => {
    fetchOrders();
  }, [fetchOrders]);

  const handleSearch = (event: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(event.target.value);
  };

  const handleRefresh = () => {
    fetchOrders();
  };

  const handleSyncShopifyOrders = async () => {
    try {
      setSyncing(true);
      setSyncMessage('正在同步 Shopify 订单...');
      setError(null);

      // 首先获取所有 Shopify 店铺
      const storesResponse = await frontendApi.get('/api/external-systems?system_type=shopify');
      const shopifyStores = storesResponse.data.external_systems || [];

      if (shopifyStores.length === 0) {
        setSyncMessage('没有找到 Shopify 店铺，请先配置 Shopify 连接');
        return;
      }

      let totalSynced = 0;
      let totalErrors = 0;

      // 为每个 Shopify 店铺同步订单
      for (const store of shopifyStores) {
        try {
          setSyncMessage(`正在同步店铺: ${store.name}...`);
          
          const syncResponse = await frontendApi.post(
            `/api/external-systems/shopify/${store.id_hashid}/sync-orders`,
            {
              limit: 100, // 每次同步最多100个订单
              status: 'any', // 同步所有状态的订单
            }
          );

          if (syncResponse.data.success) {
            totalSynced += syncResponse.data.synced_count || 0;
            console.log(`✅ 店铺 ${store.name} 同步成功: ${syncResponse.data.synced_count || 0} 个订单`);
          }
        } catch (storeError: any) {
          console.error(`❌ 店铺 ${store.name} 同步失败:`, storeError);
          totalErrors++;
        }
      }

      if (totalErrors === 0) {
        setSyncMessage(`✅ 同步完成！共同步了 ${totalSynced} 个订单`);
      } else {
        setSyncMessage(`⚠️ 同步完成，成功同步 ${totalSynced} 个订单，${totalErrors} 个店铺同步失败`);
      }

      // 同步完成后刷新订单列表
      await fetchOrders();

    } catch (error: any) {
      console.error('❌ Shopify 订单同步失败:', error);
      setError(error.response?.data?.detail || '同步失败，请稍后重试');
      setSyncMessage(null);
    } finally {
      setSyncing(false);
      // 3秒后清除同步消息
      setTimeout(() => setSyncMessage(null), 3000);
    }
  };

  const handleViewOrder = (orderId: number) => {
    router.push(`/orders/${orderId}`);
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
    return new Date(dateString).toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (loading && orders.length === 0) {
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

  return (
    <Box>
      <Box
        display='flex'
        justifyContent='space-between'
        alignItems='center'
        mb={3}
      >
        <Typography variant='h4' component='h1'>
          订单管理
        </Typography>
        <Box display='flex' gap={2}>
          <Button
            variant='contained'
            startIcon={syncing ? <CircularProgress size={16} /> : <SyncIcon />}
            onClick={handleSyncShopifyOrders}
            disabled={syncing || loading}
            color='primary'
          >
            {syncing ? '同步中...' : '同步 Shopify 订单'}
          </Button>
          <Button
            variant='outlined'
            startIcon={<RefreshIcon />}
            onClick={handleRefresh}
            disabled={loading || syncing}
          >
            刷新
          </Button>
        </Box>
      </Box>

      {error && (
        <Alert severity='error' sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {syncMessage && (
        <Alert 
          severity={syncMessage.includes('✅') ? 'success' : syncMessage.includes('⚠️') ? 'warning' : 'info'} 
          sx={{ mb: 2 }}
        >
          {syncMessage}
        </Alert>
      )}

      <Card>
        <CardContent>
          <Box display='flex' gap={2} mb={3}>
            <TextField
              fullWidth
              placeholder='搜索订单ID、客户邮箱或订单号...'
              value={searchTerm}
              onChange={handleSearch}
              InputProps={{
                startAdornment: (
                  <InputAdornment position='start'>
                    <SearchIcon />
                  </InputAdornment>
                ),
              }}
            />
            <Button variant='outlined' startIcon={<FilterIcon />} disabled>
              筛选
            </Button>
          </Box>

          <TableContainer component={Paper} variant='outlined'>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>订单ID</TableCell>
                  <TableCell>Shopify订单号</TableCell>
                  <TableCell>客户</TableCell>
                  <TableCell>金额</TableCell>
                  <TableCell>状态</TableCell>
                  <TableCell>订单日期</TableCell>
                  <TableCell>操作</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {orders.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} align='center'>
                      <Typography variant='body2' color='text.secondary'>
                        {searchTerm ? '没有找到匹配的订单' : '暂无订单数据'}
                      </Typography>
                    </TableCell>
                  </TableRow>
                ) : (
                  orders.map(order => (
                    <TableRow key={order.id} hover>
                      <TableCell>
                        <Typography variant='body2' fontWeight='medium'>
                          #{order.id}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant='body2'>
                          {order.external_order_name || order.external_order_id}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Box>
                          <Typography variant='body2' fontWeight='medium'>
                            {order.customer_name || '未知客户'}
                          </Typography>
                          <Typography variant='caption' color='text.secondary'>
                            {order.customer_email}
                          </Typography>
                        </Box>
                      </TableCell>
                      <TableCell>
                        <Typography variant='body2' fontWeight='medium'>
                          {formatCurrency(order.total_amount, order.currency)}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={order.status}
                          color={getStatusColor(order.status) as any}
                          size='small'
                        />
                      </TableCell>
                      <TableCell>
                        <Typography variant='body2'>
                          {formatDate(order.order_date)}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Tooltip title='查看详情'>
                          <IconButton
                            size='small'
                            onClick={() => handleViewOrder(order.id)}
                          >
                            <ViewIcon />
                          </IconButton>
                        </Tooltip>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </TableContainer>

          {/* 移除分页组件，显示所有订单 */}
        </CardContent>
      </Card>
    </Box>
  );
}
