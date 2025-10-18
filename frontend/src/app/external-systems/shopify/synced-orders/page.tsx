'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Alert,
  CircularProgress,
  Grid,
  TextField,
  InputAdornment,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Pagination,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Stack,
  Divider,
  Badge,
  Avatar,
} from '@mui/material';
import Checkbox from '@mui/material/Checkbox';
import {
  Search as SearchIcon,
  Refresh as RefreshIcon,
  Visibility as ViewIcon,
  Storage as DatabaseIcon,
  ShoppingCart as ShoppingCartIcon,
  Person as PersonIcon,
  AttachMoney as MoneyIcon,
  CalendarToday as CalendarIcon,
  FilterList as FilterIcon,
  Sync as SyncIcon,
  Delete as DeleteIcon,
} from '@mui/icons-material';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { frontendApi } from '@/lib/api';
import { frontendLogger } from '@/lib/frontend-logger';
import toast from 'react-hot-toast';

interface SyncedShopifyOrder {
  id: number;
  id_hashid: string; // 添加 hashid 字段
  shopify_order_id: string;
  name: string;
  confirmation_number?: string;
  financial_status: string;
  fulfillment_status: string;
  confirmed: boolean;
  closed: boolean;
  cancelled: boolean;
  currency_code: string;
  total_price: number;
  subtotal_price?: number;
  total_tax?: number;
  total_shipping?: number;
  tags?: string;
  note?: string;
  customer_data?: any;
  billing_address?: any;
  shipping_address?: any;
  line_items?: any[];
  fulfillments?: any[];
  refunds?: any[];
  raw_data?: any;
  created_at: string;
  updated_at?: string;
  last_synced_at?: string;
}

const SyncedShopifyOrdersPage: React.FC = () => {
  const [orders, setOrders] = useState<SyncedShopifyOrder[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const [selectedOrder, setSelectedOrder] = useState<SyncedShopifyOrder | null>(
    null
  );
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [sortBy, setSortBy] = useState<
    'created_at' | 'updated_at' | 'total_price' | 'name'
  >('created_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [financialStatusFilter, setFinancialStatusFilter] =
    useState<string>('all');
  const [fulfillmentStatusFilter, setFulfillmentStatusFilter] =
    useState<string>('all');
  const [jsonModalOpen, setJsonModalOpen] = useState(false);
  const [orderJson, setOrderJson] = useState<any>(null);
  const [syncingOrders, setSyncingOrders] = useState<Set<number>>(new Set());
  const [selectedOrders, setSelectedOrders] = useState<Set<number>>(new Set()); // Selected orders for bulk sync
  const [bulkSyncing, setBulkSyncing] = useState(false); // Bulk sync status
  const [deletingOrders, setDeletingOrders] = useState<Set<number>>(new Set()); // Orders being deleted
  const [bulkDeleting, setBulkDeleting] = useState(false); // Bulk delete status
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false); // Delete confirmation dialog

  // 获取同步的Shopify订单列表
  const fetchOrders = useCallback(
    async (pageNum: number = 1) => {
      setLoading(true);
      setError(null);

      try {
        frontendLogger.info('🔄 获取同步的Shopify订单列表', { page: pageNum });
        const response = await frontendApi.get('/api/shopify-orders', {
          params: {
            page: pageNum,
            limit: 20,
            search: searchTerm,
            sort_by: sortBy,
            sort_order: sortOrder,
            financial_status:
              financialStatusFilter !== 'all'
                ? financialStatusFilter
                : undefined,
            fulfillment_status:
              fulfillmentStatusFilter !== 'all'
                ? fulfillmentStatusFilter
                : undefined,
          },
        });

        setOrders(response.data.orders || []);
        setTotalPages(response.data.total_pages || 1);
        setTotalCount(response.data.total || 0);
        setPage(pageNum);

        frontendLogger.info('✅ 同步的Shopify订单列表获取成功', {
          count: response.data.orders?.length || 0,
          totalPages: response.data.total_pages || 1,
        });
      } catch (error: any) {
        frontendLogger.error('❌ 获取同步的Shopify订单列表失败', {
          error: error.message,
        });
        setError('获取订单列表失败');
      } finally {
        setLoading(false);
      }
    },
    [
      searchTerm,
      sortBy,
      sortOrder,
      financialStatusFilter,
      fulfillmentStatusFilter,
    ]
  );

  // 初始化
  useEffect(() => {
    fetchOrders(1);
  }, [fetchOrders]);

  // 搜索处理
  const handleSearch = useCallback(() => {
    fetchOrders(1);
  }, [fetchOrders]);

  // 刷新数据
  const handleRefresh = useCallback(() => {
    fetchOrders(page);
  }, [fetchOrders, page]);

  // 查看订单详情
  const handleViewOrder = async (order: SyncedShopifyOrder) => {
    setSelectedOrder(order);
    setDetailsOpen(true);
  };

  // 查看原始JSON数据
  const handleViewJson = (order: SyncedShopifyOrder) => {
    setOrderJson(order.raw_data);
    setJsonModalOpen(true);
  };

  // 同步到核心订单
  const handleSyncToCoreOrder = async (order: SyncedShopifyOrder) => {
    try {
      setSyncingOrders(prev => new Set(prev).add(order.id));
      frontendLogger.info('🔄 开始同步到核心订单', {
        orderId: order.id,
        orderName: order.name,
      });

      const response = await frontendApi.post(
        `/api/shopify-orders/${order.id_hashid}/sync-to-core`
      );

      if (response.data.success) {
        frontendLogger.info('✅ 同步到核心订单成功', { orderId: order.id });
        toast.success(`订单 ${order.name} 已成功同步到核心订单系统！`);
      } else {
        frontendLogger.error('❌ 同步到核心订单失败', {
          orderId: order.id,
          error: response.data.message,
        });
        toast.error(`同步失败：${response.data.message || '未知错误'}`);
      }
    } catch (error: any) {
      frontendLogger.error('❌ 同步到核心订单异常', {
        orderId: order.id,
        error: error.message,
      });
      toast.error(`同步失败：${error.message || '网络错误'}`);
    } finally {
      setSyncingOrders(prev => {
        const newSet = new Set(prev);
        newSet.delete(order.id);
        return newSet;
      });
    }
  };

  // 处理单个订单选择
  const handleOrderSelect = (orderId: number, selected: boolean) => {
    setSelectedOrders(prev => {
      const newSet = new Set(prev);
      if (selected) {
        newSet.add(orderId);
      } else {
        newSet.delete(orderId);
      }
      return newSet;
    });
  };

  // 处理全选
  const handleSelectAll = (selected: boolean) => {
    if (selected) {
      setSelectedOrders(new Set(orders.map(order => order.id)));
    } else {
      setSelectedOrders(new Set());
    }
  };

  // 批量同步到核心订单
  const handleBulkSyncToCore = async () => {
    if (selectedOrders.size === 0) {
      toast.error('请先选择要同步的订单');
      return;
    }

    setBulkSyncing(true);
    frontendLogger.info('🔄 开始批量同步到核心订单', {
      selectedCount: selectedOrders.size,
    });

    try {
      const syncPromises = Array.from(selectedOrders).map(async orderId => {
        const order = orders.find(o => o.id === orderId);
        if (!order) return null;

        try {
          const response = await frontendApi.post(
            `/api/shopify-orders/${order.id_hashid}/sync-to-core`
          );
          return {
            orderId,
            success: response.data.success,
            orderName: order.name,
          };
        } catch (error: any) {
          return {
            orderId,
            success: false,
            error: error.message,
            orderName: order.name,
          };
        }
      });

      const results = await Promise.all(syncPromises);
      const successful = results.filter(r => r?.success).length;
      const failed = results.filter(r => r && !r.success).length;

      frontendLogger.info('✅ 批量同步完成', { successful, failed });
      toast.success(`批量同步完成：成功 ${successful} 个，失败 ${failed} 个`);

      // 清空选择
      setSelectedOrders(new Set());
    } catch (error: any) {
      frontendLogger.error('❌ 批量同步异常', { error: error.message });
      toast.error(`批量同步失败：${error.message || '网络错误'}`);
    } finally {
      setBulkSyncing(false);
    }
  };

  // 单个订单删除
  const handleDeleteOrder = async (order: SyncedShopifyOrder) => {
    try {
      setDeletingOrders(prev => new Set(prev).add(order.id));
      frontendLogger.info('🔄 开始删除订单', {
        orderId: order.id,
        orderName: order.name,
      });

      const response = await frontendApi.delete(
        `/api/shopify-orders/${order.id_hashid}`
      );

      if (response.data.success) {
        frontendLogger.info('✅ 订单删除成功', { orderId: order.id });
        toast.success(`订单 ${order.name} 已成功删除！`);
        // 刷新列表
        fetchOrders(page);
      } else {
        frontendLogger.error('❌ 订单删除失败', {
          orderId: order.id,
          error: response.data.message,
        });
        toast.error(`删除失败：${response.data.message || '未知错误'}`);
      }
    } catch (error: any) {
      frontendLogger.error('❌ 订单删除异常', {
        orderId: order.id,
        error: error.message,
      });
      toast.error(`删除失败：${error.message || '网络错误'}`);
    } finally {
      setDeletingOrders(prev => {
        const newSet = new Set(prev);
        newSet.delete(order.id);
        return newSet;
      });
    }
  };

  // 批量删除订单
  const handleBulkDelete = async () => {
    if (selectedOrders.size === 0) {
      toast.error('请先选择要删除的订单');
      return;
    }

    setBulkDeleting(true);
    frontendLogger.info('🔄 开始批量删除订单', {
      selectedCount: selectedOrders.size,
    });

    try {
      const deletePromises = Array.from(selectedOrders).map(async orderId => {
        const order = orders.find(o => o.id === orderId);
        if (!order) return null;

        try {
          const response = await frontendApi.delete(
            `/api/shopify-orders/${order.id_hashid}`
          );
          return {
            orderId,
            success: response.data.success,
            orderName: order.name,
          };
        } catch (error: any) {
          return {
            orderId,
            success: false,
            error: error.message,
            orderName: order.name,
          };
        }
      });

      const results = await Promise.all(deletePromises);
      const successful = results.filter(r => r?.success).length;
      const failed = results.filter(r => r && !r.success).length;

      frontendLogger.info('✅ 批量删除完成', { successful, failed });
      toast.success(`批量删除完成：成功 ${successful} 个，失败 ${failed} 个`);

      // 关闭确认对话框，清空选择并刷新列表
      setDeleteConfirmOpen(false);
      setSelectedOrders(new Set());
      fetchOrders(page);
    } catch (error: any) {
      frontendLogger.error('❌ 批量删除异常', { error: error.message });
      toast.error(`批量删除失败：${error.message || '网络错误'}`);
    } finally {
      setBulkDeleting(false);
    }
  };

  // 确认删除对话框
  const handleConfirmDelete = () => {
    if (selectedOrders.size === 0) {
      toast.error('请先选择要删除的订单');
      return;
    }
    setDeleteConfirmOpen(true);
  };

  // 格式化价格
  const formatPrice = (price: number, currency: string) => {
    const numPrice = typeof price === 'string' ? parseFloat(price) : price;
    return `${currency} ${numPrice.toFixed(2)}`;
  };

  // 获取状态颜色
  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'paid':
      case 'fulfilled':
        return 'success';
      case 'pending':
      case 'unfulfilled':
        return 'warning';
      case 'refunded':
      case 'cancelled':
        return 'error';
      default:
        return 'default';
    }
  };

  // 格式化日期
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('zh-CN');
  };

  if (loading && orders.length === 0) {
    return (
      <ProtectedRoute>
        <DashboardLayout>
          <Box
            sx={{
              p: 3,
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              minHeight: '50vh',
            }}
          >
            <CircularProgress />
          </Box>
        </DashboardLayout>
      </ProtectedRoute>
    );
  }

  return (
    <ProtectedRoute>
      <DashboardLayout>
        <Box sx={{ p: 3 }}>
          <Box
            sx={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              mb: 3,
            }}
          >
            <Box>
              <Typography variant='h4' gutterBottom>
                同步的Shopify订单
              </Typography>
              <Typography variant='body2' color='text.secondary'>
                显示已同步到数据库的Shopify订单数据
              </Typography>
            </Box>
            <Button
              variant='outlined'
              startIcon={<RefreshIcon />}
              onClick={handleRefresh}
              disabled={loading}
            >
              刷新
            </Button>
          </Box>

          {/* 搜索和筛选 */}
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
                <Box sx={{ width: { xs: "100%", md: "33.33%" } }}>
                  <TextField
                    fullWidth
                    placeholder='搜索订单名称、确认号、客户邮箱...'
                    value={searchTerm}
                    onChange={e => setSearchTerm(e.target.value)}
                    onKeyPress={e => e.key === 'Enter' && handleSearch()}
                    InputProps={{
                      startAdornment: (
                        <InputAdornment position='start'>
                          <SearchIcon />
                        </InputAdornment>
                      ),
                    }}
                  />
                </Box>
                <Box sx={{ width: { xs: "100%", md: "16.67%" } }}>
                  <FormControl fullWidth>
                    <InputLabel>财务状态</InputLabel>
                    <Select
                      value={financialStatusFilter}
                      onChange={e => setFinancialStatusFilter(e.target.value)}
                    >
                      <MenuItem value='all'>全部</MenuItem>
                      <MenuItem value='PAID'>已付款</MenuItem>
                      <MenuItem value='PENDING'>待付款</MenuItem>
                      <MenuItem value='REFUNDED'>已退款</MenuItem>
                    </Select>
                  </FormControl>
                </Box>
                <Box sx={{ width: { xs: "100%", md: "16.67%" } }}>
                  <FormControl fullWidth>
                    <InputLabel>履行状态</InputLabel>
                    <Select
                      value={fulfillmentStatusFilter}
                      onChange={e => setFulfillmentStatusFilter(e.target.value)}
                    >
                      <MenuItem value='all'>全部</MenuItem>
                      <MenuItem value='FULFILLED'>已履行</MenuItem>
                      <MenuItem value='UNFULFILLED'>未履行</MenuItem>
                      <MenuItem value='PARTIAL'>部分履行</MenuItem>
                    </Select>
                  </FormControl>
                </Box>
                <Box sx={{ width: { xs: "100%", md: "16.67%" } }}>
                  <FormControl fullWidth>
                    <InputLabel>排序字段</InputLabel>
                    <Select
                      value={sortBy}
                      onChange={e => setSortBy(e.target.value as any)}
                    >
                      <MenuItem value='created_at'>创建时间</MenuItem>
                      <MenuItem value='updated_at'>更新时间</MenuItem>
                      <MenuItem value='total_price'>总价</MenuItem>
                      <MenuItem value='name'>订单名称</MenuItem>
                    </Select>
                  </FormControl>
                </Box>
                <Box sx={{ width: { xs: "100%", md: "16.67%" } }}>
                  <Button
                    variant='contained'
                    onClick={handleSearch}
                    disabled={loading}
                    fullWidth
                  >
                    搜索
                  </Button>
                </Box>
              </Box>
            </CardContent>
          </Card>

          {error && (
            <Alert severity='error' sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          {/* 订单列表 */}
          <Card>
            <CardContent>
              <Box
                sx={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  mb: 2,
                }}
              >
                <Typography variant='h6'>
                  订单列表 ({totalCount} 个订单)
                </Typography>
                <Stack direction='row' spacing={1}>
                  <Chip
                    icon={<DatabaseIcon />}
                    label='数据库同步'
                    color='info'
                    variant='outlined'
                  />
                  {selectedOrders.size > 0 && (
                    <Chip
                      label={`已选择 ${selectedOrders.size} 个订单`}
                      color='primary'
                      variant='filled'
                    />
                  )}
                </Stack>
              </Box>

              {/* 批量操作按钮 */}
              {selectedOrders.size > 0 && (
                <Box sx={{ mb: 2, display: 'flex', gap: 1 }}>
                  <Button
                    variant='contained'
                    color='primary'
                    startIcon={
                      bulkSyncing ? (
                        <CircularProgress size={16} />
                      ) : (
                        <SyncIcon />
                      )
                    }
                    onClick={handleBulkSyncToCore}
                    disabled={bulkSyncing}
                  >
                    {bulkSyncing
                      ? '批量同步中...'
                      : `同步到核心订单 (${selectedOrders.size})`}
                  </Button>
                  <Button
                    variant='contained'
                    color='error'
                    startIcon={
                      bulkDeleting ? (
                        <CircularProgress size={16} />
                      ) : (
                        <DeleteIcon />
                      )
                    }
                    onClick={handleConfirmDelete}
                    disabled={bulkDeleting}
                  >
                    {bulkDeleting
                      ? '批量删除中...'
                      : `删除订单 (${selectedOrders.size})`}
                  </Button>
                  <Button
                    variant='outlined'
                    onClick={() => setSelectedOrders(new Set())}
                  >
                    取消选择
                  </Button>
                </Box>
              )}

              <TableContainer component={Paper}>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell padding='checkbox'>
                        <Checkbox
                          indeterminate={
                            selectedOrders.size > 0 &&
                            selectedOrders.size < orders.length
                          }
                          checked={
                            orders.length > 0 &&
                            selectedOrders.size === orders.length
                          }
                          onChange={e => handleSelectAll(e.target.checked)}
                        />
                      </TableCell>
                      <TableCell>订单信息</TableCell>
                      <TableCell>客户</TableCell>
                      <TableCell>状态</TableCell>
                      <TableCell>金额</TableCell>
                      <TableCell>创建时间</TableCell>
                      <TableCell>最后同步</TableCell>
                      <TableCell>操作</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {orders.map(order => (
                      <TableRow key={order.id} hover>
                        <TableCell padding='checkbox'>
                          <Checkbox
                            checked={selectedOrders.has(order.id)}
                            onChange={e =>
                              handleOrderSelect(order.id, e.target.checked)
                            }
                          />
                        </TableCell>
                        <TableCell>
                          <Box>
                            <Typography variant='subtitle2' fontWeight='bold'>
                              {order.name}
                            </Typography>
                            <Typography
                              variant='caption'
                              color='text.secondary'
                            >
                              ID: {order.shopify_order_id}
                            </Typography>
                            {order.confirmation_number && (
                              <Typography
                                variant='caption'
                                color='text.secondary'
                                display='block'
                              >
                                确认号: {order.confirmation_number}
                              </Typography>
                            )}
                          </Box>
                        </TableCell>
                        <TableCell>
                          {order.customer_data?.email && (
                            <Box>
                              <Typography variant='body2'>
                                {order.customer_data.email}
                              </Typography>
                              {order.customer_data.first_name &&
                                order.customer_data.last_name && (
                                  <Typography
                                    variant='caption'
                                    color='text.secondary'
                                  >
                                    {order.customer_data.first_name}{' '}
                                    {order.customer_data.last_name}
                                  </Typography>
                                )}
                            </Box>
                          )}
                        </TableCell>
                        <TableCell>
                          <Stack spacing={1}>
                            <Chip
                              label={order.financial_status}
                              color={
                                getStatusColor(order.financial_status) as any
                              }
                              size='small'
                            />
                            <Chip
                              label={order.fulfillment_status}
                              color={
                                getStatusColor(order.fulfillment_status) as any
                              }
                              size='small'
                            />
                          </Stack>
                        </TableCell>
                        <TableCell>
                          <Typography variant='body2' fontWeight='bold'>
                            {formatPrice(
                              order.total_price,
                              order.currency_code
                            )}
                          </Typography>
                          {order.subtotal_price && (
                            <Typography
                              variant='caption'
                              color='text.secondary'
                            >
                              小计:{' '}
                              {formatPrice(
                                order.subtotal_price,
                                order.currency_code
                              )}
                            </Typography>
                          )}
                        </TableCell>
                        <TableCell>
                          <Typography variant='body2'>
                            {formatDate(order.created_at)}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          {order.last_synced_at && (
                            <Typography variant='body2'>
                              {formatDate(order.last_synced_at)}
                            </Typography>
                          )}
                        </TableCell>
                        <TableCell>
                          <Stack direction='row' spacing={1}>
                            <Tooltip title='查看详情'>
                              <IconButton
                                size='small'
                                onClick={() => handleViewOrder(order)}
                              >
                                <ViewIcon />
                              </IconButton>
                            </Tooltip>
                            <Tooltip title='查看原始数据'>
                              <IconButton
                                size='small'
                                onClick={() => handleViewJson(order)}
                              >
                                <DatabaseIcon />
                              </IconButton>
                            </Tooltip>
                            <Tooltip title='删除订单'>
                              <IconButton
                                size='small'
                                color='error'
                                onClick={() => handleDeleteOrder(order)}
                                disabled={deletingOrders.has(order.id)}
                              >
                                {deletingOrders.has(order.id) ? (
                                  <CircularProgress size={16} />
                                ) : (
                                  <DeleteIcon />
                                )}
                              </IconButton>
                            </Tooltip>
                          </Stack>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>

              {/* 分页 */}
              {totalPages > 1 && (
                <Box sx={{ display: 'flex', justifyContent: 'center', mt: 3 }}>
                  <Pagination
                    count={totalPages}
                    page={page}
                    onChange={(_, newPage) => fetchOrders(newPage)}
                    color='primary'
                  />
                </Box>
              )}
            </CardContent>
          </Card>

          {/* 订单详情对话框 */}
          <Dialog
            open={detailsOpen}
            onClose={() => setDetailsOpen(false)}
            maxWidth='md'
            fullWidth
          >
            <DialogTitle>订单详情 - {selectedOrder?.name}</DialogTitle>
            <DialogContent>
              {selectedOrder && (
                <Box>
                  <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
                    <Box sx={{ width: { xs: "100%", md: "50%" } }}>
                      <Typography variant='h6' gutterBottom>
                        基本信息
                      </Typography>
                      <Stack spacing={1}>
                        <Typography variant='body2'>
                          <strong>订单ID:</strong>{' '}
                          {selectedOrder.shopify_order_id}
                        </Typography>
                        <Typography variant='body2'>
                          <strong>确认号:</strong>{' '}
                          {selectedOrder.confirmation_number || 'N/A'}
                        </Typography>
                        <Typography variant='body2'>
                          <strong>财务状态:</strong>{' '}
                          {selectedOrder.financial_status}
                        </Typography>
                        <Typography variant='body2'>
                          <strong>履行状态:</strong>{' '}
                          {selectedOrder.fulfillment_status}
                        </Typography>
                        <Typography variant='body2'>
                          <strong>总价:</strong>{' '}
                          {formatPrice(
                            selectedOrder.total_price,
                            selectedOrder.currency_code
                          )}
                        </Typography>
                      </Stack>
                    </Box>
                    <Box sx={{ width: { xs: "100%", md: "50%" } }}>
                      <Typography variant='h6' gutterBottom>
                        时间信息
                      </Typography>
                      <Stack spacing={1}>
                        <Typography variant='body2'>
                          <strong>创建时间:</strong>{' '}
                          {formatDate(selectedOrder.created_at)}
                        </Typography>
                        {selectedOrder.updated_at && (
                          <Typography variant='body2'>
                            <strong>更新时间:</strong>{' '}
                            {formatDate(selectedOrder.updated_at)}
                          </Typography>
                        )}
                        {selectedOrder.last_synced_at && (
                          <Typography variant='body2'>
                            <strong>最后同步:</strong>{' '}
                            {formatDate(selectedOrder.last_synced_at)}
                          </Typography>
                        )}
                      </Stack>
                    </Box>
                  </Box>

                  {/* 商品列表 */}
                  {selectedOrder.line_items &&
                    selectedOrder.line_items.length > 0 && (
                      <Box sx={{ mt: 3 }}>
                        <Typography variant='h6' gutterBottom>
                          商品列表
                        </Typography>
                        <TableContainer component={Paper} variant='outlined'>
                          <Table size='small'>
                            <TableHead>
                              <TableRow>
                                <TableCell>商品名称</TableCell>
                                <TableCell>变体</TableCell>
                                <TableCell align='right'>数量</TableCell>
                                <TableCell align='right'>单价</TableCell>
                                <TableCell align='right'>小计</TableCell>
                              </TableRow>
                            </TableHead>
                            <TableBody>
                              {selectedOrder.line_items.map(
                                (item: any, index: number) => (
                                  <TableRow key={index}>
                                    <TableCell>
                                      <Typography
                                        variant='body2'
                                        fontWeight='medium'
                                      >
                                        {item.title}
                                      </Typography>
                                      {item.sku && (
                                        <Typography
                                          variant='caption'
                                          color='text.secondary'
                                        >
                                          SKU: {item.sku}
                                        </Typography>
                                      )}
                                    </TableCell>
                                    <TableCell>
                                      <Typography
                                        variant='body2'
                                        color='text.secondary'
                                      >
                                        {item.variant?.title || 'N/A'}
                                      </Typography>
                                    </TableCell>
                                    <TableCell align='right'>
                                      <Typography variant='body2'>
                                        {item.quantity}
                                      </Typography>
                                    </TableCell>
                                    <TableCell align='right'>
                                      <Typography variant='body2'>
                                        {formatPrice(
                                          item.price,
                                          item.currency ||
                                            selectedOrder.currency_code
                                        )}
                                      </Typography>
                                    </TableCell>
                                    <TableCell align='right'>
                                      <Typography
                                        variant='body2'
                                        fontWeight='medium'
                                      >
                                        {formatPrice(
                                          (
                                          parseFloat(item.price) *
                                          parseInt(item.quantity.toString())
                                          ).toString(),
                                          item.currency ||
                                            selectedOrder.currency_code
                                        )}
                                      </Typography>
                                    </TableCell>
                                  </TableRow>
                                )
                              )}
                            </TableBody>
                          </Table>
                        </TableContainer>
                      </Box>
                    )}
                </Box>
              )}
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setDetailsOpen(false)}>关闭</Button>
            </DialogActions>
          </Dialog>

          {/* JSON数据对话框 */}
          <Dialog
            open={jsonModalOpen}
            onClose={() => setJsonModalOpen(false)}
            maxWidth='lg'
            fullWidth
          >
            <DialogTitle>原始JSON数据</DialogTitle>
            <DialogContent>
              <pre
                style={{
                  backgroundColor: '#f5f5f5',
                  padding: '16px',
                  borderRadius: '4px',
                  overflow: 'auto',
                  maxHeight: '500px',
                }}
              >
                {JSON.stringify(orderJson, null, 2)}
              </pre>
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setJsonModalOpen(false)}>关闭</Button>
            </DialogActions>
          </Dialog>

          {/* 删除确认对话框 */}
          <Dialog
            open={deleteConfirmOpen && selectedOrders.size > 0}
            onClose={() => setDeleteConfirmOpen(false)}
            maxWidth='sm'
            fullWidth
          >
            <DialogTitle>确认删除订单</DialogTitle>
            <DialogContent>
              <Typography variant='body1' gutterBottom>
                您确定要删除选中的 {selectedOrders.size} 个订单吗？
              </Typography>
              <Typography variant='body2' color='text.secondary'>
                此操作不可撤销，删除的订单将从数据库中永久移除。
              </Typography>
              <Box sx={{ mt: 2 }}>
                <Typography variant='subtitle2' gutterBottom>
                  将要删除的订单：
                </Typography>
                <Box sx={{ maxHeight: '200px', overflow: 'auto' }}>
                  {Array.from(selectedOrders).map(orderId => {
                    const order = orders.find(o => o.id === orderId);
                    return order ? (
                      <Typography
                        key={orderId}
                        variant='body2'
                        color='text.secondary'
                      >
                        • {order.name} ({order.shopify_order_id})
                      </Typography>
                    ) : null;
                  })}
                </Box>
              </Box>
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setDeleteConfirmOpen(false)}>取消</Button>
              <Button
                variant='contained'
                color='error'
                startIcon={
                  bulkDeleting ? <CircularProgress size={16} /> : <DeleteIcon />
                }
                onClick={handleBulkDelete}
                disabled={bulkDeleting}
              >
                {bulkDeleting ? '删除中...' : '确认删除'}
              </Button>
            </DialogActions>
          </Dialog>
        </Box>
      </DashboardLayout>
    </ProtectedRoute>
  );
};

export default SyncedShopifyOrdersPage;
