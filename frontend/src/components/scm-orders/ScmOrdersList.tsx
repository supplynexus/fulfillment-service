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
} from '@mui/icons-material';
import { useRouter } from 'next/navigation';
import { frontendApi } from '@/lib/api';

const ITEMS_PER_PAGE = 10;

interface ScmOrder {
  id: number;
  order_id: number;
  scm_provider: string;
  scm_order_id?: string;
  status: string;
  routing_rule_id?: number;
  created_at: string;
  updated_at?: string;
  error_message?: string;
  retry_count: number;
  last_retry_at?: string;
}

export function ScmOrdersList() {
  const router = useRouter();
  const [orders, setOrders] = useState<ScmOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

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

      setOrders(response.data.items || []);
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
                  <TableCell>关联订单ID</TableCell>
                  <TableCell>SCM 提供商</TableCell>
                  <TableCell>状态</TableCell>
                  <TableCell>路由规则ID</TableCell>
                  <TableCell>创建时间</TableCell>
                  <TableCell>操作</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {orders.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} align='center'>
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
                        {order.scm_order_id && (
                          <Typography variant='caption' color='text.secondary'>
                            SCM: {order.scm_order_id}
                          </Typography>
                        )}
                      </TableCell>
                      <TableCell>
                        <Typography variant='body2' fontWeight='medium'>
                          #{order.order_id}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Box display='flex' alignItems='center' gap={1}>
                          <ShippingIcon fontSize='small' />
                          <Typography variant='body2'>
                            {order.scm_provider}
                          </Typography>
                        </Box>
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
                          {order.routing_rule_id || '-'}
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
