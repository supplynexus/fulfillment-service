'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Grid,
  Alert,
  CircularProgress,
  Tooltip,
  Pagination,
  Stack,
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  Visibility as ViewIcon,
  Search as SearchIcon,
  FilterList as FilterIcon,
  ShoppingCart as OrderIcon,
  Store as StoreIcon,
  CalendarToday as DateIcon,
  AttachMoney as PriceIcon,
  LocalShipping as ShippingIcon,
  CheckCircle as CheckCircleIcon,
  CheckCircle as StatusIcon,
  Error as ErrorIcon,
  Info as InfoIcon,
  Link as LinkIcon,
} from '@mui/icons-material';
import { frontendApi } from '@/lib/api';
import { frontendLogger } from '@/lib/frontend-logger';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { DashboardLayout } from '@/components/layout/DashboardLayout';

// 订单状态类型
type OrderStatus =
  | 'pending'
  | 'processing'
  | 'shipped'
  | 'delivered'
  | 'cancelled'
  | 'on_hold';

// Printify 订单接口
interface PrintifyOrder {
  id: number;
  external_order_id: string;
  scm_order_id?: number;
  status: OrderStatus;
  total_price?: string;
  currency?: string;
  customer_email?: string;
  customer_name?: string;
  shipping_address?: any;
  billing_address?: any;
  tracking_number?: string;
  tracking_url?: string;
  carrier?: string;
  created_at: string;
  updated_at?: string;
  shipped_at?: string;
  delivered_at?: string;
  external_system?: {
    id: number;
    name: string;
    system_type: string;
  };
  scm_order?: {
    id: number;
    scm_order_number?: string;
    status: string;
  };
  printify_data?: any;
  external_data?: any;
}

function PrintifyOrdersPage() {
  const [orders, setOrders] = useState<PrintifyOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<OrderStatus | 'all'>('all');
  const [selectedOrder, setSelectedOrder] = useState<PrintifyOrder | null>(
    null
  );
  const [openOrderDialog, setOpenOrderDialog] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const [loadingOrders, setLoadingOrders] = useState(false);
  const [syncingLogistics, setSyncingLogistics] = useState(false);
  const [syncMessage, setSyncMessage] = useState<string | null>(null);

  // 获取订单列表
  const fetchOrders = useCallback(
    async (page: number = 1) => {
      try {
        setLoadingOrders(true);
        setError(null);

        frontendLogger.info('🔍 开始获取 Printify 订单列表', {
          page: page,
          status: statusFilter,
          search: searchTerm,
        });

        const params = new URLSearchParams({
          page: page.toString(),
          limit: '20',
        });

        if (statusFilter !== 'all') {
          params.append('status', statusFilter);
        }

        if (searchTerm) {
          params.append('search', searchTerm);
        }

        const response = await frontendApi.get(
          `/api/printify-orders?${params.toString()}`
        );

        if (response.data.success && response.data.orders) {
          const ordersData = response.data.orders || [];
          setOrders(ordersData);
          setTotalCount(response.data.total_count || 0);
          setTotalPages(response.data.total_pages || 1);
          setCurrentPage(page);
          frontendLogger.info('✅ Printify 订单列表获取成功', {
            count: ordersData.length,
            total: response.data.total_count,
          });
        } else {
          throw new Error(response.data.message || '获取订单列表失败');
        }
      } catch (error) {
        frontendLogger.error('❌ 获取 Printify 订单列表失败', {
          error: String(error),
        });
        setError('获取订单列表失败');
      } finally {
        setLoadingOrders(false);
      }
    },
    [statusFilter, searchTerm]
  );

  // 刷新订单列表
  const handleRefresh = useCallback(async () => {
    setRefreshing(true);
    try {
      await fetchOrders(currentPage);
      frontendLogger.info('✅ 订单列表刷新成功');
    } catch (error) {
      frontendLogger.error('❌ 订单列表刷新失败', { error: String(error) });
    } finally {
      setRefreshing(false);
    }
  }, [fetchOrders, currentPage]);

  // 搜索处理
  const handleSearch = (event: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(event.target.value);
    setCurrentPage(1);
  };

  // 状态过滤处理
  const handleStatusFilter = (event: any) => {
    setStatusFilter(event.target.value);
    setCurrentPage(1);
  };

  // 查看订单详情
  const handleViewOrder = (order: PrintifyOrder) => {
    setSelectedOrder(order);
    setOpenOrderDialog(true);
  };

  // 分页处理
  const handlePageChange = (
    event: React.ChangeEvent<unknown>,
    page: number
  ) => {
    setCurrentPage(page);
  };

  // 同步物流信息
  const handleSyncLogistics = useCallback(async () => {
    try {
      setSyncingLogistics(true);
      setSyncMessage('正在同步物流信息...');
      setError(null);

      frontendLogger.info('🔍 开始同步 Printify 订单物流信息');

      const response = await frontendApi.post(
        '/api/printify-orders/sync-logistics'
      );

      if (response.data.success) {
        setSyncMessage(
          `✅ 同步完成！共同步了 ${response.data.synced_count || 0} 个订单的物流信息`
        );
        frontendLogger.info('✅ Printify 订单物流信息同步成功', {
          syncedCount: response.data.synced_count,
          totalOrders: response.data.total_orders,
          errorCount: response.data.error_count,
        });

        // 同步完成后刷新订单列表
        await fetchOrders(currentPage);
      } else {
        setSyncMessage(`⚠️ 同步失败: ${response.data.message || '未知错误'}`);
        frontendLogger.error('❌ Printify 订单物流信息同步失败', response.data);
      }
    } catch (error: any) {
      frontendLogger.error('❌ Printify 订单物流信息同步失败', {
        error: error.message,
      });
      setError(error.response?.data?.detail || '同步失败，请稍后重试');
      setSyncMessage(null);
    } finally {
      setSyncingLogistics(false);
      // 3秒后清除同步消息
      setTimeout(() => setSyncMessage(null), 3000);
    }
  }, [fetchOrders, currentPage]);

  // 初始加载
  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      try {
        await fetchOrders(1);
      } catch (error) {
        frontendLogger.error('❌ 初始数据加载失败', { error: String(error) });
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [fetchOrders]);

  // 状态颜色映射
  const getStatusColor = (status: OrderStatus) => {
    switch (status) {
      case 'pending':
        return 'warning';
      case 'processing':
        return 'info';
      case 'shipped':
        return 'primary';
      case 'delivered':
        return 'success';
      case 'cancelled':
        return 'error';
      case 'on_hold':
        return 'default';
      default:
        return 'default';
    }
  };

  // 状态图标映射
  const getStatusIcon = (status: OrderStatus) => {
    switch (status) {
      case 'pending':
        return <InfoIcon />;
      case 'processing':
        return <StatusIcon />;
      case 'shipped':
        return <ShippingIcon />;
      case 'delivered':
        return <CheckCircleIcon />;
      case 'cancelled':
        return <ErrorIcon />;
      case 'on_hold':
        return <InfoIcon />;
      default:
        return <InfoIcon />;
    }
  };

  // 格式化日期
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  // 格式化价格
  const formatPrice = (price: string | undefined, currency: string = 'USD') => {
    if (!price) return 'N/A';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency,
    }).format(parseFloat(price));
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

  return (
    <Box>
      <Box
        display='flex'
        justifyContent='space-between'
        alignItems='center'
        mb={3}
      >
        <Typography variant='h4' component='h1'>
          Printify 订单管理
        </Typography>
        <Box display='flex' gap={2}>
          <Button
            variant='outlined'
            startIcon={<ShippingIcon />}
            onClick={handleSyncLogistics}
            disabled={syncingLogistics}
            color='primary'
          >
            {syncingLogistics ? '同步中...' : '同步物流信息'}
          </Button>
          <Tooltip title='刷新'>
            <IconButton onClick={handleRefresh} disabled={refreshing}>
              <RefreshIcon />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      {error && (
        <Alert severity='error' sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {syncMessage && (
        <Alert
          severity={syncMessage.includes('✅') ? 'success' : 'warning'}
          sx={{ mb: 2 }}
        >
          {syncMessage}
        </Alert>
      )}

      {/* 搜索和过滤 */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }} spacing={2} alignItems='center'>
            <Box sx={{ width: "100%" }} sm={6} md={4}>
              <TextField
                fullWidth
                label='搜索订单'
                value={searchTerm}
                onChange={handleSearch}
                InputProps={{
                  startAdornment: (
                    <SearchIcon sx={{ mr: 1, color: 'text.secondary' }} />
                  ),
                }}
                placeholder='搜索订单ID或客户邮箱'
              />
            </Box>
            <Box sx={{ width: "100%" }} sm={6} md={3}>
              <FormControl fullWidth>
                <InputLabel>状态过滤</InputLabel>
                <Select
                  value={statusFilter}
                  onChange={handleStatusFilter}
                  label='状态过滤'
                >
                  <MenuItem value='all'>全部状态</MenuItem>
                  <MenuItem value='pending'>待处理</MenuItem>
                  <MenuItem value='processing'>处理中</MenuItem>
                  <MenuItem value='shipped'>已发货</MenuItem>
                  <MenuItem value='delivered'>已送达</MenuItem>
                  <MenuItem value='cancelled'>已取消</MenuItem>
                  <MenuItem value='on_hold'>暂停</MenuItem>
                </Select>
              </FormControl>
            </Box>
          </Box>
        </CardContent>
      </Card>

      {/* 订单列表 */}
      <Card>
        <CardContent>
          <Box
            display='flex'
            justifyContent='space-between'
            alignItems='center'
            mb={2}
          >
            <Typography variant='h6'>订单列表 ({totalCount} 个订单)</Typography>
            {loadingOrders && <CircularProgress size={24} />}
          </Box>

          {orders.length === 0 ? (
            <Box textAlign='center' py={4}>
              <Typography variant='body1' color='text.secondary'>
                暂无订单数据
              </Typography>
            </Box>
          ) : (
            <>
              <TableContainer component={Paper}>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>订单ID</TableCell>
                      <TableCell>SCM订单</TableCell>
                      <TableCell>客户信息</TableCell>
                      <TableCell>状态</TableCell>
                      <TableCell>总价</TableCell>
                      <TableCell>创建时间</TableCell>
                      <TableCell>操作</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {orders.map(order => (
                      <TableRow key={order.id}>
                        <TableCell>
                          <Typography variant='body2' fontFamily='monospace'>
                            {order.external_order_id}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          {order.scm_order ? (
                            <Box display='flex' alignItems='center' gap={1}>
                              <LinkIcon fontSize='small' color='primary' />
                              <Typography variant='body2'>
                                SCM-{order.scm_order.id}
                              </Typography>
                            </Box>
                          ) : (
                            <Typography variant='body2' color='text.secondary'>
                              N/A
                            </Typography>
                          )}
                        </TableCell>
                        <TableCell>
                          <Box>
                            <Typography variant='body2'>
                              {order.customer_name || 'N/A'}
                            </Typography>
                            <Typography
                              variant='caption'
                              color='text.secondary'
                            >
                              {order.customer_email || 'N/A'}
                            </Typography>
                          </Box>
                        </TableCell>
                        <TableCell>
                          <Chip
                            icon={getStatusIcon(order.status)}
                            label={order.status}
                            color={getStatusColor(order.status) as any}
                            size='small'
                          />
                        </TableCell>
                        <TableCell>
                          <Typography variant='body2'>
                            {formatPrice(order.total_price, order.currency)}
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
                              onClick={() => handleViewOrder(order)}
                            >
                              <ViewIcon />
                            </IconButton>
                          </Tooltip>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>

              {/* 分页 */}
              {totalPages > 1 && (
                <Box display='flex' justifyContent='center' mt={3}>
                  <Pagination
                    count={totalPages}
                    page={currentPage}
                    onChange={handlePageChange}
                    color='primary'
                  />
                </Box>
              )}
            </>
          )}
        </CardContent>
      </Card>

      {/* 订单详情对话框 */}
      <Dialog
        open={openOrderDialog}
        onClose={() => setOpenOrderDialog(false)}
        maxWidth='md'
        fullWidth
      >
        <DialogTitle>
          <Box display='flex' alignItems='center' gap={2}>
            <OrderIcon color='primary' />
            订单详情
          </Box>
        </DialogTitle>
        <DialogContent>
          {selectedOrder && (
            <Box>
              {/* 订单基本信息 */}
              <Card sx={{ mb: 2 }}>
                <CardContent>
                  <Typography variant='h6' gutterBottom>
                    订单信息
                  </Typography>
                  <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }} spacing={2}>
                    <Box sx={{ width: "100%" }} sm={6}>
                      <Typography variant='body2' color='text.secondary'>
                        订单ID
                      </Typography>
                      <Typography variant='body1' fontFamily='monospace'>
                        {selectedOrder.external_order_id}
                      </Typography>
                    </Box>
                    <Box sx={{ width: "100%" }} sm={6}>
                      <Typography variant='body2' color='text.secondary'>
                        状态
                      </Typography>
                      <Chip
                        icon={getStatusIcon(selectedOrder.status)}
                        label={selectedOrder.status}
                        color={getStatusColor(selectedOrder.status) as any}
                        size='small'
                      />
                    </Box>
                    <Box sx={{ width: "100%" }} sm={6}>
                      <Typography variant='body2' color='text.secondary'>
                        SCM订单
                      </Typography>
                      <Typography variant='body1'>
                        {selectedOrder.scm_order
                          ? `SCM-${selectedOrder.scm_order.id}`
                          : 'N/A'}
                      </Typography>
                    </Box>
                    <Box sx={{ width: "100%" }} sm={6}>
                      <Typography variant='body2' color='text.secondary'>
                        总价
                      </Typography>
                      <Typography variant='body1'>
                        {formatPrice(
                          selectedOrder.total_price,
                          selectedOrder.currency
                        )}
                      </Typography>
                    </Box>
                    <Box sx={{ width: "100%" }} sm={6}>
                      <Typography variant='body2' color='text.secondary'>
                        创建时间
                      </Typography>
                      <Typography variant='body1'>
                        {formatDate(selectedOrder.created_at)}
                      </Typography>
                    </Box>
                    <Box sx={{ width: "100%" }} sm={6}>
                      <Typography variant='body2' color='text.secondary'>
                        更新时间
                      </Typography>
                      <Typography variant='body1'>
                        {selectedOrder.updated_at
                          ? formatDate(selectedOrder.updated_at)
                          : 'N/A'}
                      </Typography>
                    </Box>
                  </Box>
                </CardContent>
              </Card>

              {/* 客户信息 */}
              <Card sx={{ mb: 2 }}>
                <CardContent>
                  <Typography variant='h6' gutterBottom>
                    客户信息
                  </Typography>
                  <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }} spacing={2}>
                    <Box sx={{ width: "100%" }} sm={6}>
                      <Typography variant='body2' color='text.secondary'>
                        姓名
                      </Typography>
                      <Typography variant='body1'>
                        {selectedOrder.customer_name || 'N/A'}
                      </Typography>
                    </Box>
                    <Box sx={{ width: "100%" }} sm={6}>
                      <Typography variant='body2' color='text.secondary'>
                        邮箱
                      </Typography>
                      <Typography variant='body1'>
                        {selectedOrder.customer_email || 'N/A'}
                      </Typography>
                    </Box>
                  </Box>
                </CardContent>
              </Card>

              {/* 物流信息 */}
              {(selectedOrder.tracking_number ||
                selectedOrder.tracking_url) && (
                <Card sx={{ mb: 2 }}>
                  <CardContent>
                    <Typography variant='h6' gutterBottom>
                      物流信息
                    </Typography>
                    <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }} spacing={2}>
                      <Box sx={{ width: "100%" }} sm={6}>
                        <Typography variant='body2' color='text.secondary'>
                          跟踪号
                        </Typography>
                        <Typography variant='body1'>
                          {selectedOrder.tracking_number || 'N/A'}
                        </Typography>
                      </Box>
                      <Box sx={{ width: "100%" }} sm={6}>
                        <Typography variant='body2' color='text.secondary'>
                          承运商
                        </Typography>
                        <Typography variant='body1'>
                          {selectedOrder.carrier || 'N/A'}
                        </Typography>
                      </Box>
                      {selectedOrder.tracking_url && (
                        <Box sx={{ width: "100%" }}>
                          <Typography variant='body2' color='text.secondary'>
                            跟踪链接
                          </Typography>
                          <Typography
                            variant='body1'
                            component='a'
                            href={selectedOrder.tracking_url}
                            target='_blank'
                            rel='noopener noreferrer'
                            sx={{
                              color: 'primary.main',
                              textDecoration: 'none',
                            }}
                          >
                            {selectedOrder.tracking_url}
                          </Typography>
                        </Box>
                      )}
                    </Box>
                  </CardContent>
                </Card>
              )}
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenOrderDialog(false)}>关闭</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default function Page() {
  return (
    <ProtectedRoute>
      <DashboardLayout>
        <PrintifyOrdersPage />
      </DashboardLayout>
    </ProtectedRoute>
  );
}
