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
  Sync as SyncIcon,
  Store as StoreIcon,
  ShoppingCart as ShoppingCartIcon,
  Person as PersonIcon,
  AttachMoney as MoneyIcon,
  CalendarToday as CalendarIcon,
  FilterList as FilterIcon,
} from '@mui/icons-material';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { frontendApi } from '@/lib/api';
import { frontendLogger } from '@/lib/frontend-logger';

interface ShopifyOrder {
  id: string;
  name: string;
  email: string;
  created_at: string;
  updated_at: string;
  total_price: string;
  currency: string;
  fulfillment_status: string;
  financial_status: string;
  shipping_address?: {
    firstName?: string;
    lastName?: string;
    address1?: string;
    city?: string;
    province?: string;
    country?: string;
    zip?: string;
  };
  billing_address?: {
    firstName?: string;
    lastName?: string;
    address1?: string;
    city?: string;
    province?: string;
    country?: string;
    zip?: string;
  };
  customer?: {
    id: string;
    name: string;
    email: string;
  };
  line_items_count: number;
}

interface ShopifyStore {
  id: number;
  name: string;
  external_system_id: string;
  shop_domain: string;
  access_token: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

const ShopifyOrdersPage: React.FC = () => {
  const [orders, setOrders] = useState<ShopifyOrder[]>([]);
  const [stores, setStores] = useState<ShopifyStore[]>([]);
  const [selectedStore, setSelectedStore] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [selectedOrder, setSelectedOrder] = useState<ShopifyOrder | null>(null);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [sortBy, setSortBy] = useState<'created_at' | 'updated_at' | 'total_price' | 'name'>('created_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [financialStatusFilter, setFinancialStatusFilter] = useState<string>('all');
  const [fulfillmentStatusFilter, setFulfillmentStatusFilter] = useState<string>('all');
  const [syncing, setSyncing] = useState(false);

  // 获取 Shopify 店铺列表
  const fetchStores = useCallback(async () => {
    try {
      frontendLogger.info('🔄 获取 Shopify 店铺列表');
      const response = await frontendApi.get('/api/external-systems/shopify/stores');
      setStores(response.data.stores || []);
      frontendLogger.info('✅ Shopify 店铺列表获取成功', { count: response.data.stores?.length || 0 });
    } catch (error: any) {
      frontendLogger.error('❌ 获取 Shopify 店铺列表失败', { error: error.message });
      setError('获取店铺列表失败');
    }
  }, []);

  // 获取 Shopify 订单列表
  const fetchOrders = useCallback(async (storeId: string, pageNum: number = 1) => {
    if (!storeId) return;
    
    setLoading(true);
    setError(null);
    
    try {
      frontendLogger.info('🔄 获取 Shopify 订单列表', { storeId, page: pageNum });
      const response = await frontendApi.get(`/api/external-systems/shopify/${storeId}/orders`, {
        params: {
          page: pageNum,
          limit: 20,
          search: searchTerm,
          sort_by: sortBy,
          sort_order: sortOrder,
          status: statusFilter !== 'all' ? statusFilter : undefined,
          financial_status: financialStatusFilter !== 'all' ? financialStatusFilter : undefined,
          fulfillment_status: fulfillmentStatusFilter !== 'all' ? fulfillmentStatusFilter : undefined,
        },
      });
      
      setOrders(response.data.orders || []);
      setTotalPages(response.data.pagination?.total_pages || 1);
      setPage(pageNum);
      
      frontendLogger.info('✅ Shopify 订单列表获取成功', { 
        count: response.data.orders?.length || 0,
        totalPages: response.data.pagination?.total_pages || 1
      });
    } catch (error: any) {
      frontendLogger.error('❌ 获取 Shopify 订单列表失败', { error: error.message });
      setError('获取订单列表失败');
    } finally {
      setLoading(false);
    }
  }, [searchTerm, sortBy, sortOrder, statusFilter, financialStatusFilter, fulfillmentStatusFilter]);

  // 同步订单
  const syncOrders = useCallback(async (storeId: string) => {
    if (!storeId) return;
    
    setSyncing(true);
    setError(null);
    
    try {
      frontendLogger.info('🔄 开始同步 Shopify 订单', { storeId });
      const response = await frontendApi.post(`/api/external-systems/shopify/${storeId}/sync-orders`);
      
      frontendLogger.info('✅ Shopify 订单同步成功', { 
        ordersSynced: response.data.orders_synced,
        ordersUpdated: response.data.orders_updated,
        totalProcessed: response.data.total_processed
      });
      
      // 同步成功后刷新订单列表
      await fetchOrders(storeId, 1);
      
    } catch (error: any) {
      frontendLogger.error('❌ Shopify 订单同步失败', { error: error.message });
      setError('同步订单失败');
    } finally {
      setSyncing(false);
    }
  }, [fetchOrders]);

  // 初始化
  useEffect(() => {
    fetchStores();
  }, [fetchStores]);

  // 当选择店铺时获取订单
  useEffect(() => {
    if (selectedStore) {
      fetchOrders(selectedStore, 1);
    }
  }, [selectedStore, fetchOrders]);

  // 搜索处理
  const handleSearch = useCallback(() => {
    if (selectedStore) {
      fetchOrders(selectedStore, 1);
    }
  }, [selectedStore, fetchOrders]);

  // 刷新数据
  const handleRefresh = useCallback(() => {
    if (selectedStore) {
      fetchOrders(selectedStore, page);
    }
  }, [selectedStore, fetchOrders, page]);

  // 查看订单详情
  const handleViewOrder = (order: ShopifyOrder) => {
    setSelectedOrder(order);
    setDetailsOpen(true);
  };

  // 获取状态颜色
  const getStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'fulfilled':
      case 'paid':
        return 'success';
      case 'pending':
      case 'unfulfilled':
        return 'warning';
      case 'cancelled':
      case 'refunded':
        return 'error';
      default:
        return 'default';
    }
  };

  // 格式化日期
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('zh-CN');
  };

  // 格式化金额
  const formatPrice = (price: string, currency: string) => {
    return `${currency} ${parseFloat(price).toFixed(2)}`;
  };

  return (
    <ProtectedRoute>
      <DashboardLayout>
        <Box sx={{ p: 3 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
            <Typography variant="h4" gutterBottom>
              Shopify 订单管理
            </Typography>
            <Button
              variant="contained"
              startIcon={<SyncIcon />}
              onClick={() => selectedStore && syncOrders(selectedStore)}
              disabled={!selectedStore || syncing}
              sx={{ minWidth: 120 }}
            >
              {syncing ? <CircularProgress size={20} /> : '同步订单'}
            </Button>
          </Box>

          {/* 店铺选择 */}
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                选择店铺
              </Typography>
              <Grid container spacing={2}>
                {stores.map((store) => (
                  <Grid item xs={12} sm={6} md={4} key={store.id}>
                    <Card
                      sx={{
                        cursor: 'pointer',
                        border: selectedStore === store.external_system_id ? 2 : 1,
                        borderColor: selectedStore === store.external_system_id ? 'primary.main' : 'divider',
                        '&:hover': { borderColor: 'primary.main' },
                      }}
                      onClick={() => setSelectedStore(store.external_system_id)}
                    >
                      <CardContent>
                        <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                          <StoreIcon sx={{ mr: 1, color: 'primary.main' }} />
                          <Typography variant="h6" component="div">
                            {store.name}
                          </Typography>
                        </Box>
                        <Typography variant="body2" color="text.secondary">
                          {store.external_system_id}
                        </Typography>
                        <Chip
                          label={store.is_active ? '活跃' : '非活跃'}
                          color={store.is_active ? 'success' : 'default'}
                          size="small"
                          sx={{ mt: 1 }}
                        />
                      </CardContent>
                    </Card>
                  </Grid>
                ))}
              </Grid>
            </CardContent>
          </Card>

          {selectedStore && (
            <>
              {/* 搜索和筛选 */}
              <Card sx={{ mb: 3 }}>
                <CardContent>
                  <Grid container spacing={2} alignItems="center">
                    <Grid item xs={12} md={4}>
                      <TextField
                        fullWidth
                        placeholder="搜索订单..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        InputProps={{
                          startAdornment: (
                            <InputAdornment position="start">
                              <SearchIcon />
                            </InputAdornment>
                          ),
                        }}
                        onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                      />
                    </Grid>
                    <Grid item xs={12} md={2}>
                      <FormControl fullWidth>
                        <InputLabel>排序方式</InputLabel>
                        <Select
                          value={sortBy}
                          onChange={(e) => setSortBy(e.target.value as any)}
                          label="排序方式"
                        >
                          <MenuItem value="created_at">创建时间</MenuItem>
                          <MenuItem value="updated_at">更新时间</MenuItem>
                          <MenuItem value="total_price">金额</MenuItem>
                          <MenuItem value="name">订单号</MenuItem>
                        </Select>
                      </FormControl>
                    </Grid>
                    <Grid item xs={12} md={2}>
                      <FormControl fullWidth>
                        <InputLabel>排序顺序</InputLabel>
                        <Select
                          value={sortOrder}
                          onChange={(e) => setSortOrder(e.target.value as any)}
                          label="排序顺序"
                        >
                          <MenuItem value="desc">降序</MenuItem>
                          <MenuItem value="asc">升序</MenuItem>
                        </Select>
                      </FormControl>
                    </Grid>
                    <Grid item xs={12} md={2}>
                      <FormControl fullWidth>
                        <InputLabel>财务状态</InputLabel>
                        <Select
                          value={financialStatusFilter}
                          onChange={(e) => setFinancialStatusFilter(e.target.value)}
                          label="财务状态"
                        >
                          <MenuItem value="all">全部</MenuItem>
                          <MenuItem value="paid">已付款</MenuItem>
                          <MenuItem value="pending">待付款</MenuItem>
                          <MenuItem value="refunded">已退款</MenuItem>
                        </Select>
                      </FormControl>
                    </Grid>
                    <Grid item xs={12} md={2}>
                      <FormControl fullWidth>
                        <InputLabel>履行状态</InputLabel>
                        <Select
                          value={fulfillmentStatusFilter}
                          onChange={(e) => setFulfillmentStatusFilter(e.target.value)}
                          label="履行状态"
                        >
                          <MenuItem value="all">全部</MenuItem>
                          <MenuItem value="fulfilled">已履行</MenuItem>
                          <MenuItem value="unfulfilled">未履行</MenuItem>
                          <MenuItem value="partial">部分履行</MenuItem>
                        </Select>
                      </FormControl>
                    </Grid>
                    <Grid item xs={12} md={12}>
                      <Stack direction="row" spacing={2}>
                        <Button
                          variant="contained"
                          startIcon={<SearchIcon />}
                          onClick={handleSearch}
                        >
                          搜索
                        </Button>
                        <Button
                          variant="outlined"
                          startIcon={<RefreshIcon />}
                          onClick={handleRefresh}
                        >
                          刷新
                        </Button>
                      </Stack>
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>

              {/* 订单列表 */}
              <Card>
                <CardContent>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                    <Typography variant="h6">
                      订单列表
                      {orders.length > 0 && (
                        <Chip
                          label={`${orders.length} 个订单`}
                          color="primary"
                          size="small"
                          sx={{ ml: 2 }}
                        />
                      )}
                    </Typography>
                  </Box>

                  {loading && (
                    <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
                      <CircularProgress />
                    </Box>
                  )}

                  {error && (
                    <Alert severity="error" sx={{ mb: 2 }}>
                      {error}
                    </Alert>
                  )}

                  {!loading && !error && orders.length === 0 && (
                    <Box sx={{ textAlign: 'center', py: 4 }}>
                      <ShoppingCartIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
                      <Typography variant="h6" color="text.secondary" gutterBottom>
                        暂无订单数据
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        请先同步订单或检查筛选条件
                      </Typography>
                    </Box>
                  )}

                  {!loading && !error && orders.length > 0 && (
                    <>
                      <TableContainer component={Paper} variant="outlined">
                        <Table>
                          <TableHead>
                            <TableRow>
                              <TableCell>订单号</TableCell>
                              <TableCell>客户</TableCell>
                              <TableCell>金额</TableCell>
                              <TableCell>财务状态</TableCell>
                              <TableCell>履行状态</TableCell>
                              <TableCell>创建时间</TableCell>
                              <TableCell>操作</TableCell>
                            </TableRow>
                          </TableHead>
                          <TableBody>
                            {orders.map((order) => (
                              <TableRow key={order.id} hover>
                                <TableCell>
                                  <Typography variant="body2" fontWeight="medium">
                                    {order.name}
                                  </Typography>
                                </TableCell>
                                <TableCell>
                                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                                    <Avatar sx={{ width: 32, height: 32, mr: 1 }}>
                                      <PersonIcon />
                                    </Avatar>
                                    <Box>
                                      <Typography variant="body2">
                                        {order.customer?.name || '未知客户'}
                                      </Typography>
                                      <Typography variant="caption" color="text.secondary">
                                        {order.customer?.email || order.email || '无邮箱'}
                                      </Typography>
                                    </Box>
                                  </Box>
                                </TableCell>
                                <TableCell>
                                  <Typography variant="body2" fontWeight="medium">
                                    {formatPrice(order.total_price, order.currency)}
                                  </Typography>
                                </TableCell>
                                <TableCell>
                                  <Chip
                                    label={order.financial_status || '未知'}
                                    color={getStatusColor(order.financial_status)}
                                    size="small"
                                  />
                                </TableCell>
                                <TableCell>
                                  <Chip
                                    label={order.fulfillment_status || '未知'}
                                    color={getStatusColor(order.fulfillment_status)}
                                    size="small"
                                  />
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
                        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 3 }}>
                          <Pagination
                            count={totalPages}
                            page={page}
                            onChange={(_, value) => fetchOrders(selectedStore, value)}
                            color="primary"
                          />
                        </Box>
                      )}
                    </>
                  )}
                </CardContent>
              </Card>
            </>
          )}

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
                  <Grid container spacing={3}>
                    <Grid item xs={12} md={6}>
                      <Typography variant="h6" gutterBottom>
                        基本信息
                      </Typography>
                      <Stack spacing={1}>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                          <Typography variant="body2" color="text.secondary">订单号:</Typography>
                          <Typography variant="body2">{selectedOrder.name}</Typography>
                        </Box>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                          <Typography variant="body2" color="text.secondary">金额:</Typography>
                          <Typography variant="body2" fontWeight="medium">
                            {formatPrice(selectedOrder.total_price, selectedOrder.currency)}
                          </Typography>
                        </Box>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                          <Typography variant="body2" color="text.secondary">财务状态:</Typography>
                          <Chip
                            label={selectedOrder.financial_status || '未知'}
                            color={getStatusColor(selectedOrder.financial_status)}
                            size="small"
                          />
                        </Box>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                          <Typography variant="body2" color="text.secondary">履行状态:</Typography>
                          <Chip
                            label={selectedOrder.fulfillment_status || '未知'}
                            color={getStatusColor(selectedOrder.fulfillment_status)}
                            size="small"
                          />
                        </Box>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                          <Typography variant="body2" color="text.secondary">创建时间:</Typography>
                          <Typography variant="body2">{formatDate(selectedOrder.created_at)}</Typography>
                        </Box>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                          <Typography variant="body2" color="text.secondary">更新时间:</Typography>
                          <Typography variant="body2">{formatDate(selectedOrder.updated_at)}</Typography>
                        </Box>
                      </Stack>
                    </Grid>
                    <Grid item xs={12} md={6}>
                      <Typography variant="h6" gutterBottom>
                        客户信息
                      </Typography>
                      <Stack spacing={1}>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                          <Typography variant="body2" color="text.secondary">姓名:</Typography>
                          <Typography variant="body2">{selectedOrder.customer?.name || '未知'}</Typography>
                        </Box>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                          <Typography variant="body2" color="text.secondary">邮箱:</Typography>
                          <Typography variant="body2">{selectedOrder.customer?.email || selectedOrder.email || '无'}</Typography>
                        </Box>
                      </Stack>
                    </Grid>
                    {selectedOrder.shipping_address && (
                      <Grid item xs={12} md={6}>
                        <Typography variant="h6" gutterBottom>
                          收货地址
                        </Typography>
                        <Stack spacing={1}>
                          <Typography variant="body2">
                            {selectedOrder.shipping_address.firstName} {selectedOrder.shipping_address.lastName}
                          </Typography>
                          <Typography variant="body2">
                            {selectedOrder.shipping_address.address1}
                          </Typography>
                          <Typography variant="body2">
                            {selectedOrder.shipping_address.city}, {selectedOrder.shipping_address.province} {selectedOrder.shipping_address.zip}
                          </Typography>
                          <Typography variant="body2">
                            {selectedOrder.shipping_address.country}
                          </Typography>
                        </Stack>
                      </Grid>
                    )}
                    {selectedOrder.billing_address && (
                      <Grid item xs={12} md={6}>
                        <Typography variant="h6" gutterBottom>
                          账单地址
                        </Typography>
                        <Stack spacing={1}>
                          <Typography variant="body2">
                            {selectedOrder.billing_address.firstName} {selectedOrder.billing_address.lastName}
                          </Typography>
                          <Typography variant="body2">
                            {selectedOrder.billing_address.address1}
                          </Typography>
                          <Typography variant="body2">
                            {selectedOrder.billing_address.city}, {selectedOrder.billing_address.province} {selectedOrder.billing_address.zip}
                          </Typography>
                          <Typography variant="body2">
                            {selectedOrder.billing_address.country}
                          </Typography>
                        </Stack>
                      </Grid>
                    )}
                  </Grid>
                </Box>
              )}
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setDetailsOpen(false)}>关闭</Button>
            </DialogActions>
          </Dialog>
        </Box>
      </DashboardLayout>
    </ProtectedRoute>
  );
};

export default ShopifyOrdersPage;
