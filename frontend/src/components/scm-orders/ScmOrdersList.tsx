'use client';

import React, { useState, useEffect } from 'react';
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
  Pagination,
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
  LocalShipping as ShippingIcon,
  Sync as SyncIcon,
} from '@mui/icons-material';
import { useRouter } from 'next/navigation';
import { frontendApi } from '@/lib/api';

const ITEMS_PER_PAGE = 10;

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
  error_message?: string;
  retry_count: number;
  last_retry_at?: string;
  created_at: string;
  updated_at?: string;
}

export function ScmOrdersList() {
  console.log('🔍 ScmOrdersList 组件文件加载');
  
  const router = useRouter();
  const [orders, setOrders] = useState<ScmOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [syncing, setSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState<string | null>(null);

  console.log('🔍 ScmOrdersList 组件渲染，当前状态:', {
    orders: orders.length,
    loading,
    error,
    searchTerm,
    currentPage,
    totalPages
  });

  const fetchScmOrders = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await frontendApi.get('/api/scm-orders', {
        params: {
          page: currentPage,
          limit: ITEMS_PER_PAGE,
          search: searchTerm || undefined,
        },
      });

      console.log('🔍 SCM订单API响应:', response.data);
      console.log('🔍 SCM订单数据:', response.data.scm_orders);
      console.log('🔍 SCM订单数量:', response.data.scm_orders?.length || 0);
      
      setOrders(response.data.scm_orders || []);
      setTotalPages(Math.ceil((response.data.total || 0) / ITEMS_PER_PAGE));
    } catch (err: any) {
      console.error('Failed to fetch SCM orders:', err);
      setError(err.response?.data?.detail || 'Failed to fetch SCM orders');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchScmOrders();
  }, [currentPage, searchTerm]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSearch = (event: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(event.target.value);
    setCurrentPage(1);
  };

  const handleRefresh = () => {
    fetchScmOrders();
  };

  const handleSyncPrintifyOrders = async () => {
    try {
      setSyncing(true);
      setSyncMessage('正在同步 Printify 发货单...');
      setError(null);

      // 调用 Printify 发货单同步 API
      const response = await frontendApi.post('/api/scm-orders/sync-printify-orders');

      if (response.data.success) {
        setSyncMessage(`✅ 同步完成！共同步了 ${response.data.synced_count || 0} 个发货单`);
        console.log('✅ Printify 发货单同步成功:', response.data);
      } else {
        setSyncMessage(`⚠️ 同步失败: ${response.data.message || '未知错误'}`);
        console.error('❌ Printify 发货单同步失败:', response.data);
      }

      // 同步完成后刷新订单列表
      await fetchScmOrders();

    } catch (error: any) {
      console.error('❌ Printify 发货单同步失败:', error);
      setError(error.response?.data?.detail || '同步失败，请稍后重试');
      setSyncMessage(null);
    } finally {
      setSyncing(false);
      // 3秒后清除同步消息
      setTimeout(() => setSyncMessage(null), 3000);
    }
  };

  const handleViewOrder = (orderId: number) => {
    router.push(`/scm-orders/${orderId}`);
  };

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'pending':
        return 'warning';
      case 'processing':
        return 'info';
      case 'completed':
        return 'success';
      case 'failed':
        return 'error';
      case 'cancelled':
        return 'error';
      default:
        return 'default';
    }
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
          SCM 订单管理
        </Typography>
        <Box display='flex' gap={2}>
          <Button
            variant='contained'
            startIcon={syncing ? <CircularProgress size={16} /> : <SyncIcon />}
            onClick={handleSyncPrintifyOrders}
            disabled={syncing || loading}
            color='primary'
          >
            {syncing ? '同步中...' : '同步 Printify 发货单'}
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
              placeholder='搜索 SCM 订单ID、订单ID或提供商...'
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
                  <TableCell>SCM 订单ID</TableCell>
                  <TableCell>目标系统</TableCell>
                  <TableCell>目标系统ID</TableCell>
                  <TableCell>状态</TableCell>
                  <TableCell>客户邮箱</TableCell>
                  <TableCell>总金额</TableCell>
                  <TableCell>创建时间</TableCell>
                  <TableCell>操作</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {console.log('🔍 渲染表格，订单数量:', orders.length)}
                {orders.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={8} align='center'>
                      <Typography variant='body2' color='text.secondary'>
                        {searchTerm
                          ? '没有找到匹配的 SCM 订单'
                          : '暂无 SCM 订单数据'}
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
                        {order.scm_order_number && (
                          <Typography variant='caption' color='text.secondary'>
                            SCM: {order.scm_order_number}
                          </Typography>
                        )}
                      </TableCell>
                      <TableCell>
                        <Typography variant='body2' fontWeight='medium'>
                          {order.target_system_type}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant='body2' fontWeight='medium'>
                          {order.target_system_id || 'N/A'}
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
                          {order.customer_email}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant='body2' fontWeight='medium'>
                          {order.currency} {order.total_amount.toFixed(2)}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant='body2'>
                          {formatDate(order.created_at)}
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

          {totalPages > 1 && (
            <Box display='flex' justifyContent='center' mt={3}>
              <Pagination
                count={totalPages}
                page={currentPage}
                onChange={(_, page) => setCurrentPage(page)}
                color='primary'
              />
            </Box>
          )}
        </CardContent>
      </Card>
    </Box>
  );
}
