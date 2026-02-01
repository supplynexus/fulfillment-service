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
  Checkbox,
} from '@mui/material';
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
  CheckCircle as CheckIcon,
  Error as ErrorIcon,
  Info as InfoIcon,
  LocalShipping as ShippingIcon,
  Delete as DeleteIcon,
} from '@mui/icons-material';
import { frontendApi } from '@/lib/api';
import { frontendLogger } from '@/lib/frontend-logger';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { DashboardLayout } from '@/components/layout/DashboardLayout';

// 同步订单状态类型
type SyncedOrderStatus = 'pending' | 'processing' | 'shipped' | 'delivered' | 'cancelled' | 'on_hold';

// Printify 同步订单接口
interface PrintifySyncedOrder {
  id: number;
  external_order_id: string;
  external_system_id: number;
  scm_order_id?: number;
  status: string;
  total_price: string;
  currency: string;
  customer_email: string;
  customer_name: string;
  shipping_address: any;
  billing_address: any;
  printify_data: any;
  external_data: any;
  tracking_number?: string;
  tracking_url?: string;
  carrier?: string;
  shipped_at?: string;
  delivered_at?: string;
  created_at: string;
  updated_at: string;
  // 关联的 SCM 订单信息
  scm_order?: {
    id: number;
    scm_order_number: string;
    status: string;
    fulfillment_status: string;
  };
  // 外部系统信息
  external_system?: {
    id: number;
    name: string;
    system_type: string;
  };
}

function PrintifySyncedOrdersPage() {
  const [orders, setOrders] = useState<PrintifySyncedOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<SyncedOrderStatus | 'all'>('all');
  const [selectedOrder, setSelectedOrder] = useState<PrintifySyncedOrder | null>(null);
  const [openOrderDialog, setOpenOrderDialog] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const [loadingOrders, setLoadingOrders] = useState(false);
  
  // 多选相关状态
  const [selectedOrders, setSelectedOrders] = useState<Set<number>>(new Set());
  const [updatingStatus, setUpdatingStatus] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  // 获取同步订单列表
  const fetchOrders = useCallback(async (page: number = 1) => {
    try {
      setLoadingOrders(true);
      setError(null);

      frontendLogger.info('🔍 开始获取 Printify 同步订单列表', {
        page: page,
        searchTerm: searchTerm,
        statusFilter: statusFilter,
      });

      const params = new URLSearchParams({
        page: page.toString(),
        limit: '20',
      });

      if (searchTerm) {
        params.append('search', searchTerm);
      }
      if (statusFilter !== 'all') {
        params.append('status', statusFilter);
      }

      const response = await frontendApi.get(
        `/api/printify-orders/?${params.toString()}`
      );

      if (response.data && response.data.orders) {
        setOrders(response.data.orders);
        setTotalPages(response.data.total_pages || 1);
        setTotalCount(response.data.total_count || 0);
        frontendLogger.info('✅ Printify 同步订单列表获取成功', {
          count: response.data.orders.length,
          total: response.data.total_count,
          page: page,
        });
      } else {
        throw new Error('获取同步订单列表失败：响应数据格式不正确');
      }
    } catch (error) {
      frontendLogger.error('❌ 获取 Printify 同步订单列表失败', {
        error: String(error),
        page: page,
      });
      setError('获取同步订单列表失败');
    } finally {
      setLoadingOrders(false);
      setLoading(false); // 确保初始加载状态也被清除
    }
  }, [searchTerm, statusFilter]);

  // 初始加载
  useEffect(() => {
    fetchOrders();
  }, [fetchOrders]);

  // 搜索处理
  const handleSearch = useCallback(() => {
    setCurrentPage(1);
    fetchOrders(1);
  }, [fetchOrders]);

  // 状态过滤处理
  const handleStatusFilterChange = useCallback((status: SyncedOrderStatus | 'all') => {
    setStatusFilter(status);
    setCurrentPage(1);
    fetchOrders(1);
  }, [fetchOrders]);

  // 刷新处理
  const handleRefresh = useCallback(() => {
    setRefreshing(true);
    fetchOrders(currentPage).finally(() => {
      setRefreshing(false);
      // 清空选择
      setSelectedOrders(new Set());
    });
  }, [fetchOrders, currentPage]);

  // 分页处理
  const handlePageChange = (event: React.ChangeEvent<unknown>, page: number) => {
    setCurrentPage(page);
    fetchOrders(page);
  };

  // 查看订单详情
  const handleViewOrder = (order: PrintifySyncedOrder) => {
    setSelectedOrder(order);
    setOpenOrderDialog(true);
  };

  // 多选处理函数
  const handleSelectOrder = (orderId: number) => {
    const newSelected = new Set(selectedOrders);
    if (newSelected.has(orderId)) {
      newSelected.delete(orderId);
    } else {
      newSelected.add(orderId);
    }
    setSelectedOrders(newSelected);
  };

  const handleSelectAll = () => {
    if (selectedOrders.size === orders.length) {
      setSelectedOrders(new Set());
    } else {
      setSelectedOrders(new Set(orders.map(order => order.id)));
    }
  };

  // 更新SCM订单状态
  const handleUpdateScmStatus = async () => {
    if (selectedOrders.size === 0) {
      setError('请选择要更新的订单');
      return;
    }

    try {
      setUpdatingStatus(true);
      setError(null);

      frontendLogger.info('🔄 开始更新SCM订单状态', {
        selectedOrders: Array.from(selectedOrders),
        count: selectedOrders.size
      });

      const response = await frontendApi.post('/api/printify-orders/', {
        order_ids: Array.from(selectedOrders),
        action: 'update-scm-status' // 明确标识这是更新 SCM 状态请求，不是批量删除
      });

      if (response.data.success) {
        frontendLogger.info('✅ SCM订单状态更新成功', response.data);
        setError(null);
        // 刷新订单列表
        await fetchOrders(currentPage);
        // 清空选择
        setSelectedOrders(new Set());
      } else {
        setError(response.data.message || '更新失败');
      }
    } catch (error: any) {
      console.error('❌ 更新SCM订单状态失败:', error);
      setError(error.response?.data?.detail || '更新失败，请稍后重试');
    } finally {
      setUpdatingStatus(false);
    }
  };

  // 批量删除订单
  const handleBatchDelete = async () => {
    if (selectedOrders.size === 0) {
      setDeleteError('请至少选择一个订单');
      return;
    }

    if (!confirm(`确定要删除选中的 ${selectedOrders.size} 个订单吗？此操作不可恢复。`)) {
      return;
    }

    try {
      setDeleting(true);
      setDeleteError(null);
      setError(null);

      frontendLogger.info('🗑️ 开始批量删除 Printify 同步订单', {
        orderIds: Array.from(selectedOrders),
        count: selectedOrders.size,
      });

      const response = await frontendApi.post('/api/printify-orders/batch-delete', {
        order_ids: Array.from(selectedOrders),
      });

      if (response.data.success) {
        frontendLogger.info('✅ 批量删除 Printify 同步订单成功', {
          deletedCount: response.data.deleted_count,
        });

        // 清空选择
        setSelectedOrders(new Set());
        
        // 刷新订单列表
        await fetchOrders(currentPage);
        
        // 显示成功消息
        alert(`成功删除 ${response.data.deleted_count} 个订单`);
      } else {
        throw new Error(response.data.message || '删除失败');
      }
    } catch (error: any) {
      frontendLogger.error('❌ 批量删除 Printify 同步订单失败', {
        error: error.message,
        response: error.response?.data,
      });
      setDeleteError(error.response?.data?.detail || error.message || '删除失败，请稍后重试');
    } finally {
      setDeleting(false);
    }
  };

  // 获取状态颜色
  const getStatusColor = (status: string) => {
    const statusColors: Record<string, 'default' | 'primary' | 'secondary' | 'error' | 'info' | 'success' | 'warning'> = {
      'pending': 'warning',
      'processing': 'info',
      'shipped': 'primary',
      'delivered': 'success',
      'cancelled': 'error',
      'on_hold': 'default',
    };
    return statusColors[status.toLowerCase()] || 'default';
  };

  // 获取状态图标
  const getStatusIcon = (status: string) => {
    const statusIcons: Record<string, React.ReactElement> = {
      'pending': <InfoIcon />,
      'processing': <SyncIcon />,
      'shipped': <ShippingIcon />,
      'delivered': <CheckIcon />,
      'cancelled': <ErrorIcon />,
      'on_hold': <InfoIcon />,
    };
    return statusIcons[status.toLowerCase()] || <InfoIcon />;
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

  // 格式化价格（Printify 订单总价为分，显示时除以 100 转为元）
  const formatPrice = (price: string, currency: string) => {
    const numPrice = parseFloat(price);
    if (Number.isNaN(numPrice)) return 'N/A';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency,
    }).format(numPrice / 100);
  };

  // 过滤订单
  const filteredOrders = orders.filter(order => {
    const matchesSearch = !searchTerm || 
      order.external_order_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      order.customer_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      order.customer_email.toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesStatus = statusFilter === 'all' || order.status === statusFilter;
    
    return matchesSearch && matchesStatus;
  });

  if (loading && !orders.length) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  if (error && !orders.length) {
    return (
      <Box p={3}>
        <Alert severity="error" action={
          <Button color="inherit" size="small" onClick={handleRefresh}>
            重试
          </Button>
        }>
          {error}
        </Alert>
      </Box>
    );
  }

  return (
    <ProtectedRoute>
      <DashboardLayout>
        <Box p={3}>
          {/* 页面标题 */}
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
            <Box display="flex" alignItems="center" gap={2}>
              <DatabaseIcon color="primary" />
              <Typography variant="h4" component="h1">
                Printify 同步订单
              </Typography>
              <Badge badgeContent={totalCount} color="primary">
                <ShoppingCartIcon />
              </Badge>
            </Box>
            <Box display="flex" gap={2}>
              {selectedOrders.size > 0 && (
                <>
                  <Button
                    variant="contained"
                    color="secondary"
                    startIcon={updatingStatus ? <CircularProgress size={16} /> : <SyncIcon />}
                    onClick={handleUpdateScmStatus}
                    disabled={updatingStatus || refreshing || deleting}
                  >
                    {updatingStatus ? '更新中...' : `更新SCM订单状态 (${selectedOrders.size})`}
                  </Button>
                  <Button
                    variant="contained"
                    color="error"
                    startIcon={deleting ? <CircularProgress size={16} /> : <DeleteIcon />}
                    onClick={handleBatchDelete}
                    disabled={deleting || refreshing || updatingStatus}
                  >
                    {deleting ? '删除中...' : `删除订单 (${selectedOrders.size})`}
                  </Button>
                </>
              )}
              <Button
                variant="contained"
                startIcon={<RefreshIcon />}
                onClick={handleRefresh}
                disabled={refreshing}
              >
                {refreshing ? '刷新中...' : '刷新'}
              </Button>
            </Box>
          </Box>

          {/* 搜索和过滤 */}
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Grid container spacing={2} alignItems="center">
                <Grid size={{ xs: 12, sm: 6, md: 4 }}>
                  <TextField
                    fullWidth
                    label="搜索订单"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                    InputProps={{
                      startAdornment: <SearchIcon sx={{ mr: 1, color: 'text.secondary' }} />,
                    }}
                    placeholder="订单ID、客户姓名或邮箱"
                  />
                </Grid>
                <Grid size={{ xs: 12, sm: 6, md: 4 }}>
                  <FormControl fullWidth>
                    <InputLabel>订单状态</InputLabel>
                    <Select
                      value={statusFilter}
                      onChange={(e) => handleStatusFilterChange(e.target.value as SyncedOrderStatus | 'all')}
                      label="订单状态"
                    >
                      <MenuItem value="all">全部状态</MenuItem>
                      <MenuItem value="pending">待处理</MenuItem>
                      <MenuItem value="processing">处理中</MenuItem>
                      <MenuItem value="shipped">已发货</MenuItem>
                      <MenuItem value="delivered">已送达</MenuItem>
                      <MenuItem value="cancelled">已取消</MenuItem>
                      <MenuItem value="on_hold">暂停</MenuItem>
                    </Select>
                  </FormControl>
                </Grid>
                <Grid size={{ xs: 12, sm: 6, md: 4 }}>
                  <Button
                    variant="outlined"
                    startIcon={<SearchIcon />}
                    onClick={handleSearch}
                    fullWidth
                  >
                    搜索
                  </Button>
                </Grid>
              </Grid>
            </CardContent>
          </Card>

          {/* 订单列表 */}
          <Card>
            <CardContent>
              <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                <Typography variant="h6">
                  同步订单列表 ({totalCount} 个订单)
                </Typography>
                {loadingOrders && <CircularProgress size={24} />}
              </Box>

              {error && (
                <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
                  {error}
                </Alert>
              )}

              {deleteError && (
                <Alert severity="error" sx={{ mb: 2 }} onClose={() => setDeleteError(null)}>
                  {deleteError}
                </Alert>
              )}

              {!loadingOrders && !error && orders.length === 0 && (
                <Box sx={{ textAlign: 'center', py: 4 }}>
                  <DatabaseIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
                  <Typography variant="h6" color="text.secondary" gutterBottom>
                    暂无同步订单数据
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    已保存到数据库的 Printify 订单将显示在这里
                  </Typography>
                </Box>
              )}

              {!loadingOrders && !error && orders.length > 0 && (
                <>
                  <TableContainer component={Paper}>
                    <Table>
                      <TableHead>
                        <TableRow>
                          <TableCell padding="checkbox">
                            <Checkbox
                              indeterminate={selectedOrders.size > 0 && selectedOrders.size < orders.length}
                              checked={orders.length > 0 && selectedOrders.size === orders.length}
                              onChange={handleSelectAll}
                            />
                          </TableCell>
                          <TableCell>订单ID</TableCell>
                          <TableCell>客户信息</TableCell>
                          <TableCell>状态</TableCell>
                          <TableCell>总价</TableCell>
                          <TableCell>物流信息</TableCell>
                          <TableCell>SCM关联</TableCell>
                          <TableCell>创建时间</TableCell>
                          <TableCell>操作</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {filteredOrders.map((order) => (
                          <TableRow key={order.id} hover>
                            <TableCell padding="checkbox">
                              <Checkbox
                                checked={selectedOrders.has(order.id)}
                                onChange={() => handleSelectOrder(order.id)}
                              />
                            </TableCell>
                            <TableCell>
                              <Typography variant="body2" fontFamily="monospace">
                                {order.external_order_id}
                              </Typography>
                              <Typography variant="caption" color="text.secondary">
                                ID: {order.id}
                              </Typography>
                            </TableCell>
                            <TableCell>
                              <Box>
                                <Typography variant="body2" fontWeight="medium">
                                  {order.customer_name}
                                </Typography>
                                <Typography variant="caption" color="text.secondary">
                                  {order.customer_email}
                                </Typography>
                              </Box>
                            </TableCell>
                            <TableCell>
                              <Chip
                                icon={getStatusIcon(order.status)}
                                label={order.status}
                                color={getStatusColor(order.status) as any}
                                size="small"
                              />
                            </TableCell>
                            <TableCell>
                              <Typography variant="body2" fontWeight="medium">
                                {formatPrice(order.total_price, order.currency)}
                              </Typography>
                            </TableCell>
                            <TableCell>
                              {order.tracking_number || order.carrier ? (
                                <Box>
                                  {order.tracking_number && (
                                    <Typography variant="body2" fontFamily="monospace" color="primary">
                                      {order.tracking_number}
                                    </Typography>
                                  )}
                                  {order.carrier && (
                                    <Typography variant="caption" color="text.secondary" display="block">
                                      {order.carrier}
                                    </Typography>
                                  )}
                                  {order.tracking_url && (
                                    <Button
                                      size="small"
                                      href={order.tracking_url}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      variant="outlined"
                                      sx={{ mt: 0.5, fontSize: '0.75rem' }}
                                    >
                                      查看物流
                                    </Button>
                                  )}
                                </Box>
                              ) : (
                                <Typography variant="body2" color="text.secondary">
                                  暂无物流信息
                                </Typography>
                              )}
                            </TableCell>
                            <TableCell>
                              {order.scm_order ? (
                                <Chip
                                  label={order.scm_order.scm_order_number}
                                  color="primary"
                                  size="small"
                                  icon={<CheckIcon />}
                                />
                              ) : (
                                <Chip
                                  label="未关联"
                                  color="default"
                                  size="small"
                                />
                              )}
                            </TableCell>
                            <TableCell>
                              <Typography variant="body2">
                                {formatDate(order.created_at)}
                              </Typography>
                            </TableCell>
                            <TableCell>
                              <Tooltip title="查看详情">
                                <IconButton
                                  size="small"
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
                    <Box display="flex" justifyContent="center" mt={3}>
                      <Pagination
                        count={totalPages}
                        page={currentPage}
                        onChange={handlePageChange}
                        color="primary"
                        disabled={loadingOrders}
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
            maxWidth="md"
            fullWidth
          >
            <DialogTitle>
              <Box display="flex" alignItems="center" gap={2}>
                <DatabaseIcon color="primary" />
                同步订单详情
              </Box>
            </DialogTitle>
            <DialogContent>
              {selectedOrder && (
                <Box>
                  {/* 订单基本信息 */}
                  <Card sx={{ mb: 2 }}>
                    <CardContent>
                      <Typography variant="h6" gutterBottom>
                        订单信息
                      </Typography>
                      <Grid container spacing={2}>
                        <Grid size={{ xs: 12, sm: 6 }}>
                          <Typography variant="body2" color="text.secondary">
                            外部订单ID
                          </Typography>
                          <Typography variant="body1" fontFamily="monospace">
                            {selectedOrder.external_order_id}
                          </Typography>
                        </Grid>
                        <Grid size={{ xs: 12, sm: 6 }}>
                          <Typography variant="body2" color="text.secondary">
                            内部订单ID
                          </Typography>
                          <Typography variant="body1" fontFamily="monospace">
                            {selectedOrder.id}
                          </Typography>
                        </Grid>
                        <Grid size={{ xs: 12, sm: 6 }}>
                          <Typography variant="body2" color="text.secondary">
                            状态
                          </Typography>
                          <Chip
                            icon={getStatusIcon(selectedOrder.status)}
                            label={selectedOrder.status}
                            color={getStatusColor(selectedOrder.status) as any}
                            size="small"
                          />
                        </Grid>
                        <Grid size={{ xs: 12, sm: 6 }}>
                          <Typography variant="body2" color="text.secondary">
                            总价
                          </Typography>
                          <Typography variant="h6" color="primary">
                            {formatPrice(selectedOrder.total_price, selectedOrder.currency)}
                          </Typography>
                        </Grid>
                        <Grid size={{ xs: 12, sm: 6 }}>
                          <Typography variant="body2" color="text.secondary">
                            创建时间
                          </Typography>
                          <Typography variant="body1">
                            {formatDate(selectedOrder.created_at)}
                          </Typography>
                        </Grid>
                        <Grid size={{ xs: 12, sm: 6 }}>
                          <Typography variant="body2" color="text.secondary">
                            更新时间
                          </Typography>
                          <Typography variant="body1">
                            {formatDate(selectedOrder.updated_at)}
                          </Typography>
                        </Grid>
                      </Grid>
                    </CardContent>
                  </Card>

                  {/* 客户信息 */}
                  <Card sx={{ mb: 2 }}>
                    <CardContent>
                      <Typography variant="h6" gutterBottom>
                        客户信息
                      </Typography>
                      <Grid container spacing={2}>
                        <Grid size={{ xs: 12, sm: 6 }}>
                          <Typography variant="body2" color="text.secondary">
                            姓名
                          </Typography>
                          <Typography variant="body1">
                            {selectedOrder.customer_name}
                          </Typography>
                        </Grid>
                        <Grid size={{ xs: 12, sm: 6 }}>
                          <Typography variant="body2" color="text.secondary">
                            邮箱
                          </Typography>
                          <Typography variant="body1">
                            {selectedOrder.customer_email}
                          </Typography>
                        </Grid>
                      </Grid>
                    </CardContent>
                  </Card>

                  {/* SCM 关联信息 */}
                  {selectedOrder.scm_order && (
                    <Card sx={{ mb: 2 }}>
                      <CardContent>
                        <Typography variant="h6" gutterBottom>
                          SCM 订单关联
                        </Typography>
                        <Grid container spacing={2}>
                          <Grid size={{ xs: 12, sm: 6 }}>
                            <Typography variant="body2" color="text.secondary">
                              SCM 订单号
                            </Typography>
                            <Typography variant="body1" fontFamily="monospace">
                              {selectedOrder.scm_order.scm_order_number}
                            </Typography>
                          </Grid>
                          <Grid size={{ xs: 12, sm: 6 }}>
                            <Typography variant="body2" color="text.secondary">
                              SCM 状态
                            </Typography>
                            <Chip
                              label={selectedOrder.scm_order.status}
                              color="primary"
                              size="small"
                            />
                          </Grid>
                        </Grid>
                      </CardContent>
                    </Card>
                  )}

                  {/* 物流信息 */}
                  {(selectedOrder.tracking_number || selectedOrder.tracking_url) && (
                    <Card sx={{ mb: 2 }}>
                      <CardContent>
                        <Typography variant="h6" gutterBottom>
                          物流信息
                        </Typography>
                        <Grid container spacing={2}>
                          {selectedOrder.tracking_number && (
                            <Grid size={{ xs: 12, sm: 6 }}>
                              <Typography variant="body2" color="text.secondary">
                                追踪号
                              </Typography>
                              <Typography variant="body1" fontFamily="monospace">
                                {selectedOrder.tracking_number}
                              </Typography>
                            </Grid>
                          )}
                          {selectedOrder.carrier && (
                            <Grid size={{ xs: 12, sm: 6 }}>
                              <Typography variant="body2" color="text.secondary">
                                物流公司
                              </Typography>
                              <Typography variant="body1">
                                {selectedOrder.carrier}
                              </Typography>
                            </Grid>
                          )}
                          {selectedOrder.tracking_url && (
                            <Grid size={{ xs: 12 }}>
                              <Typography variant="body2" color="text.secondary">
                                追踪链接
                              </Typography>
                              <Button
                                size="small"
                                href={selectedOrder.tracking_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                variant="outlined"
                              >
                                查看物流状态
                              </Button>
                            </Grid>
                          )}
                        </Grid>
                      </CardContent>
                    </Card>
                  )}
                </Box>
              )}
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setOpenOrderDialog(false)}>
                关闭
              </Button>
            </DialogActions>
          </Dialog>
        </Box>
      </DashboardLayout>
    </ProtectedRoute>
  );
}

export default PrintifySyncedOrdersPage;
