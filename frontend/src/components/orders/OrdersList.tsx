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
} from '@mui/icons-material';
import { useRouter } from 'next/navigation';
import { Order, OrderStatus } from '@/types/order';
import { frontendApi } from '@/lib/api';

const ITEMS_PER_PAGE = 10;

export function OrdersList() {
  const router = useRouter();
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  const fetchOrders = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await frontendApi.get('/api/orders', {
        params: {
          page: currentPage,
          limit: ITEMS_PER_PAGE,
          search: searchTerm || undefined,
        },
      });

      setOrders(response.data.orders || []);
      setTotalPages(Math.ceil((response.data.total || 0) / ITEMS_PER_PAGE));
    } catch (err: any) {
      console.error('Failed to fetch orders:', err);
      setError(err.response?.data?.detail || 'Failed to fetch orders');
    } finally {
      setLoading(false);
    }
  }, [currentPage, searchTerm]);

  useEffect(() => {
    fetchOrders();
  }, [fetchOrders]);

  const handleSearch = (event: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(event.target.value);
    setCurrentPage(1); // Reset to first page when searching
  };

  const handleRefresh = () => {
    fetchOrders();
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
        <Button
          variant='outlined'
          startIcon={<RefreshIcon />}
          onClick={handleRefresh}
          disabled={loading}
        >
          刷新
        </Button>
      </Box>

      {error && (
        <Alert severity='error' sx={{ mb: 2 }}>
          {error}
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
                          {order.shopify_order_number || order.shopify_order_id}
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
