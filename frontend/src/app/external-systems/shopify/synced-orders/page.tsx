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
} from '@mui/icons-material';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { frontendApi } from '@/lib/api';
import { frontendLogger } from '@/lib/frontend-logger';

interface SyncedShopifyOrder {
  id: number;
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
  const [selectedOrder, setSelectedOrder] = useState<SyncedShopifyOrder | null>(null);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [sortBy, setSortBy] = useState<'created_at' | 'updated_at' | 'total_price' | 'name'>('created_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [financialStatusFilter, setFinancialStatusFilter] = useState<string>('all');
  const [fulfillmentStatusFilter, setFulfillmentStatusFilter] = useState<string>('all');
  const [jsonModalOpen, setJsonModalOpen] = useState(false);
  const [orderJson, setOrderJson] = useState<any>(null);
  const [syncingOrders, setSyncingOrders] = useState<Set<number>>(new Set());

  // 获取同步的Shopify订单列表
  const fetchOrders = useCallback(async (pageNum: number = 1) => {
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
          financial_status: financialStatusFilter !== 'all' ? financialStatusFilter : undefined,
          fulfillment_status: fulfillmentStatusFilter !== 'all' ? fulfillmentStatusFilter : undefined,
        },
      });
      
      setOrders(response.data.orders || []);
      setTotalPages(response.data.pagination?.total_pages || 1);
      setTotalCount(response.data.pagination?.total_count || 0);
      setPage(pageNum);
      
      frontendLogger.info('✅ 同步的Shopify订单列表获取成功', { 
        count: response.data.orders?.length || 0,
        totalPages: response.data.pagination?.total_pages || 1
      });
    } catch (error: any) {
      frontendLogger.error('❌ 获取同步的Shopify订单列表失败', { error: error.message });
      setError('获取订单列表失败');
    } finally {
      setLoading(false);
    }
  }, [searchTerm, sortBy, sortOrder, financialStatusFilter, fulfillmentStatusFilter]);

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
      frontendLogger.info('🔄 开始同步到核心订单', { orderId: order.id, orderName: order.name });

      const response = await frontendApi.post(`/api/shopify-orders/${order.id}/sync-to-core`);
      
      if (response.data.success) {
        frontendLogger.info('✅ 同步到核心订单成功', { orderId: order.id });
        // 可以显示成功消息
        alert(`订单 ${order.name} 已成功同步到核心订单系统！`);
      } else {
        frontendLogger.error('❌ 同步到核心订单失败', { orderId: order.id, error: response.data.message });
        alert(`同步失败：${response.data.message || '未知错误'}`);
      }
    } catch (error: any) {
      frontendLogger.error('❌ 同步到核心订单异常', { orderId: order.id, error: error.message });
      alert(`同步失败：${error.message || '网络错误'}`);
    } finally {
      setSyncingOrders(prev => {
        const newSet = new Set(prev);
        newSet.delete(order.id);
        return newSet;
      });
    }
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
          <Box sx={{ p: 3, display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '50vh' }}>
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
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
            <Box>
              <Typography variant="h4" gutterBottom>
                同步的Shopify订单
              </Typography>
              <Typography variant="body2" color="text.secondary">
                显示已同步到数据库的Shopify订单数据
              </Typography>
            </Box>
            <Button
              variant="outlined"
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
              <Grid container spacing={2}>
                <Grid item xs={12} md={4}>
                  <TextField
                    fullWidth
                    placeholder="搜索订单名称、确认号、客户邮箱..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                    InputProps={{
                      startAdornment: (
                        <InputAdornment position="start">
                          <SearchIcon />
                        </InputAdornment>
                      ),
                    }}
                  />
                </Grid>
                <Grid item xs={12} md={2}>
                  <FormControl fullWidth>
                    <InputLabel>财务状态</InputLabel>
                    <Select
                      value={financialStatusFilter}
                      onChange={(e) => setFinancialStatusFilter(e.target.value)}
                    >
                      <MenuItem value="all">全部</MenuItem>
                      <MenuItem value="PAID">已付款</MenuItem>
                      <MenuItem value="PENDING">待付款</MenuItem>
                      <MenuItem value="REFUNDED">已退款</MenuItem>
                    </Select>
                  </FormControl>
                </Grid>
                <Grid item xs={12} md={2}>
                  <FormControl fullWidth>
                    <InputLabel>履行状态</InputLabel>
                    <Select
                      value={fulfillmentStatusFilter}
                      onChange={(e) => setFulfillmentStatusFilter(e.target.value)}
                    >
                      <MenuItem value="all">全部</MenuItem>
                      <MenuItem value="FULFILLED">已履行</MenuItem>
                      <MenuItem value="UNFULFILLED">未履行</MenuItem>
                      <MenuItem value="PARTIAL">部分履行</MenuItem>
                    </Select>
                  </FormControl>
                </Grid>
                <Grid item xs={12} md={2}>
                  <FormControl fullWidth>
                    <InputLabel>排序字段</InputLabel>
                    <Select
                      value={sortBy}
                      onChange={(e) => setSortBy(e.target.value as any)}
                    >
                      <MenuItem value="created_at">创建时间</MenuItem>
                      <MenuItem value="updated_at">更新时间</MenuItem>
                      <MenuItem value="total_price">总价</MenuItem>
                      <MenuItem value="name">订单名称</MenuItem>
                    </Select>
                  </FormControl>
                </Grid>
                <Grid item xs={12} md={2}>
                  <Button
                    variant="contained"
                    onClick={handleSearch}
                    disabled={loading}
                    fullWidth
                  >
                    搜索
                  </Button>
                </Grid>
              </Grid>
            </CardContent>
          </Card>

          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          {/* 订单列表 */}
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6">
                  订单列表 ({totalCount} 个订单)
                </Typography>
                <Stack direction="row" spacing={1}>
                  <Chip
                    icon={<DatabaseIcon />}
                    label="数据库同步"
                    color="info"
                    variant="outlined"
                  />
                </Stack>
              </Box>

              <TableContainer component={Paper}>
                <Table>
                  <TableHead>
                    <TableRow>
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
                    {orders.map((order) => (
                      <TableRow key={order.id} hover>
                        <TableCell>
                          <Box>
                            <Typography variant="subtitle2" fontWeight="bold">
                              {order.name}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              ID: {order.shopify_order_id}
                            </Typography>
                            {order.confirmation_number && (
                              <Typography variant="caption" color="text.secondary" display="block">
                                确认号: {order.confirmation_number}
                              </Typography>
                            )}
                          </Box>
                        </TableCell>
                        <TableCell>
                          {order.customer_data?.email && (
                            <Box>
                              <Typography variant="body2">
                                {order.customer_data.email}
                              </Typography>
                              {order.customer_data.first_name && order.customer_data.last_name && (
                                <Typography variant="caption" color="text.secondary">
                                  {order.customer_data.first_name} {order.customer_data.last_name}
                                </Typography>
                              )}
                            </Box>
                          )}
                        </TableCell>
                        <TableCell>
                          <Stack spacing={1}>
                            <Chip
                              label={order.financial_status}
                              color={getStatusColor(order.financial_status) as any}
                              size="small"
                            />
                            <Chip
                              label={order.fulfillment_status}
                              color={getStatusColor(order.fulfillment_status) as any}
                              size="small"
                            />
                          </Stack>
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" fontWeight="bold">
                            {formatPrice(order.total_price, order.currency_code)}
                          </Typography>
                          {order.subtotal_price && (
                            <Typography variant="caption" color="text.secondary">
                              小计: {formatPrice(order.subtotal_price, order.currency_code)}
                            </Typography>
                          )}
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2">
                            {formatDate(order.created_at)}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          {order.last_synced_at && (
                            <Typography variant="body2">
                              {formatDate(order.last_synced_at)}
                            </Typography>
                          )}
                        </TableCell>
                        <TableCell>
                          <Stack direction="row" spacing={1}>
                            <Tooltip title="查看详情">
                              <IconButton
                                size="small"
                                onClick={() => handleViewOrder(order)}
                              >
                                <ViewIcon />
                              </IconButton>
                            </Tooltip>
                            <Tooltip title="查看原始数据">
                              <IconButton
                                size="small"
                                onClick={() => handleViewJson(order)}
                              >
                                <DatabaseIcon />
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
                    color="primary"
                  />
                </Box>
              )}
            </CardContent>
          </Card>

          {/* 订单详情对话框 */}
          <Dialog
            open={detailsOpen}
            onClose={() => setDetailsOpen(false)}
            maxWidth="md"
            fullWidth
          >
            <DialogTitle>
              订单详情 - {selectedOrder?.name}
            </DialogTitle>
            <DialogContent>
              {selectedOrder && (
                <Box>
                  <Grid container spacing={2}>
                    <Grid item xs={12} md={6}>
                      <Typography variant="h6" gutterBottom>
                        基本信息
                      </Typography>
                      <Stack spacing={1}>
                        <Typography variant="body2">
                          <strong>订单ID:</strong> {selectedOrder.shopify_order_id}
                        </Typography>
                        <Typography variant="body2">
                          <strong>确认号:</strong> {selectedOrder.confirmation_number || 'N/A'}
                        </Typography>
                        <Typography variant="body2">
                          <strong>财务状态:</strong> {selectedOrder.financial_status}
                        </Typography>
                        <Typography variant="body2">
                          <strong>履行状态:</strong> {selectedOrder.fulfillment_status}
                        </Typography>
                        <Typography variant="body2">
                          <strong>总价:</strong> {formatPrice(selectedOrder.total_price, selectedOrder.currency_code)}
                        </Typography>
                      </Stack>
                    </Grid>
                    <Grid item xs={12} md={6}>
                      <Typography variant="h6" gutterBottom>
                        时间信息
                      </Typography>
                      <Stack spacing={1}>
                        <Typography variant="body2">
                          <strong>创建时间:</strong> {formatDate(selectedOrder.created_at)}
                        </Typography>
                        {selectedOrder.updated_at && (
                          <Typography variant="body2">
                            <strong>更新时间:</strong> {formatDate(selectedOrder.updated_at)}
                          </Typography>
                        )}
                        {selectedOrder.last_synced_at && (
                          <Typography variant="body2">
                            <strong>最后同步:</strong> {formatDate(selectedOrder.last_synced_at)}
                          </Typography>
                        )}
                      </Stack>
                    </Grid>
                  </Grid>
                </Box>
              )}
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setDetailsOpen(false)}>
                关闭
              </Button>
            </DialogActions>
          </Dialog>

          {/* JSON数据对话框 */}
          <Dialog
            open={jsonModalOpen}
            onClose={() => setJsonModalOpen(false)}
            maxWidth="lg"
            fullWidth
          >
            <DialogTitle>
              原始JSON数据
            </DialogTitle>
            <DialogContent>
              <pre style={{ 
                backgroundColor: '#f5f5f5', 
                padding: '16px', 
                borderRadius: '4px',
                overflow: 'auto',
                maxHeight: '500px'
              }}>
                {JSON.stringify(orderJson, null, 2)}
              </pre>
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setJsonModalOpen(false)}>
                关闭
              </Button>
            </DialogActions>
          </Dialog>
        </Box>
      </DashboardLayout>
    </ProtectedRoute>
  );
};

export default SyncedShopifyOrdersPage;
