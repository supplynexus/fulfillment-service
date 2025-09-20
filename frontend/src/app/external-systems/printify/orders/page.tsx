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
  CheckCircle as StatusIcon,
  Error as ErrorIcon,
  Info as InfoIcon,
} from '@mui/icons-material';
import { frontendApi } from '@/lib/api';
import { frontendLogger } from '@/lib/frontend-logger';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { DashboardLayout } from '@/components/layout/DashboardLayout';

// 订单状态类型
type OrderStatus = 'pending' | 'processing' | 'shipped' | 'delivered' | 'cancelled' | 'on_hold';

// Printify 订单接口
interface PrintifyOrder {
  id: string;
  app_order_id: string;
  shop_id: number;
  address_to: {
    first_name: string;
    last_name: string;
    email: string;
    phone?: string;
    country: string;
    region: string;
    city: string;
    address1: string;
    address2?: string;
    zip: string;
    company?: string;
  };
  line_items: Array<{
    id: string;
    variant_id: string;
    quantity: number;
    product_id: string;
    blueprint_id: number;
    print_provider_id: number;
    shipping_cost: number;
    cost: number;
    status: string;
    metadata: {
      title: string;
      price: number;
      variant_label: string;
      sku: string;
      country: string;
    };
  }>;
  metadata: {
    order_type: string;
    shop_order_id: string;
    shop_order_label: string;
  };
  total_price: number;
  total_shipping: number;
  total_tax: number;
  status: OrderStatus;
  shipping_method: number;
  created_at: string;
  fulfilment_type: string;
  printify_connect?: {
    url: string;
    id: string;
  };
  sales_channel_type_id: number;
}

// Printify 店铺接口
interface PrintifyStore {
  id_hashid: string;
  name: string;
  system_type: string;
  external_id: string;
  is_active: boolean;
}

function PrintifyOrdersPage() {
  const [orders, setOrders] = useState<PrintifyOrder[]>([]);
  const [stores, setStores] = useState<PrintifyStore[]>([]);
  const [selectedStore, setSelectedStore] = useState<PrintifyStore | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<OrderStatus | 'all'>('all');
  const [selectedOrder, setSelectedOrder] = useState<PrintifyOrder | null>(null);
  const [openOrderDialog, setOpenOrderDialog] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const [loadingOrders, setLoadingOrders] = useState(false);

  // 获取店铺列表
  const fetchStores = useCallback(async () => {
    try {
      frontendLogger.info('🔍 开始获取 Printify 店铺列表');
      const response = await frontendApi.get(
        '/api/external-systems?system_type=printify'
      );

      if (response.data && response.data.external_systems) {
        const printifyStores = response.data.external_systems.filter(
          (store: any) => store.system_type === 'printify' && store.is_active
        );
        setStores(printifyStores);
        frontendLogger.info('✅ Printify 店铺列表获取成功', {
          count: printifyStores.length,
        });

        // 如果有店铺，默认选择第一个
        if (printifyStores.length > 0) {
          setSelectedStore(printifyStores[0]);
        }
      } else {
        throw new Error('获取店铺列表失败：响应数据格式不正确');
      }
    } catch (error) {
      frontendLogger.error('❌ 获取 Printify 店铺列表失败', {
        error: String(error),
      });
      setError('获取店铺列表失败');
    }
  }, []);

  // 获取订单列表
  const fetchOrders = useCallback(async (store: PrintifyStore, page: number = 1) => {
    if (!store) return;

    try {
      setLoadingOrders(true);
      setError(null);

      frontendLogger.info('🔍 开始获取 Printify 订单列表', {
        storeId: store.id_hashid,
        storeName: store.name,
        page: page,
      });

      const response = await frontendApi.get(
        `/api/external-systems/printify/${store.id_hashid}/orders?limit=20&page=${page}`
      );

      if (response.data.success && response.data.orders) {
        const ordersData = response.data.orders || [];
        setOrders(ordersData);
        setTotalCount(response.data.total_count || 0);
        setTotalPages(Math.ceil((response.data.total_count || 0) / 20));
        setCurrentPage(page);
        frontendLogger.info('✅ Printify 订单列表获取成功', {
          count: ordersData.length,
          total: response.data.total_count,
          storeName: store.name,
        });
      } else {
        throw new Error(response.data.message || '获取订单列表失败');
      }
    } catch (error) {
      frontendLogger.error('❌ 获取 Printify 订单列表失败', {
        error: String(error),
        storeId: store.id_hashid,
      });
      setError('获取订单列表失败');
    } finally {
      setLoadingOrders(false);
    }
  }, []);

  // 刷新订单列表
  const handleRefresh = useCallback(async () => {
    if (!selectedStore) return;

    setRefreshing(true);
    try {
      await fetchOrders(selectedStore, currentPage);
      frontendLogger.info('✅ 订单列表刷新成功');
    } catch (error) {
      frontendLogger.error('❌ 订单列表刷新失败', { error: String(error) });
    } finally {
      setRefreshing(false);
    }
  }, [selectedStore, currentPage, fetchOrders]);

  // 搜索过滤
  const filteredOrders = orders.filter((order) => {
    const matchesSearch = 
      (order.app_order_id || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (order.metadata?.shop_order_id || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (order.address_to?.first_name || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (order.address_to?.last_name || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (order.address_to?.email || '').toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesStatus = statusFilter === 'all' || order.status === statusFilter;
    
    return matchesSearch && matchesStatus;
  });

  // 获取状态颜色
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

  // 获取状态图标
  const getStatusIcon = (status: OrderStatus) => {
    switch (status) {
      case 'pending':
        return <InfoIcon />;
      case 'processing':
        return <RefreshIcon />;
      case 'shipped':
        return <ShippingIcon />;
      case 'delivered':
        return <StatusIcon />;
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
  const formatPrice = (price: number, currency: string = 'USD') => {
    return new Intl.NumberFormat('zh-CN', {
      style: 'currency',
      currency: currency,
    }).format(price);
  };

  // 查看订单详情
  const handleViewOrder = (order: PrintifyOrder) => {
    setSelectedOrder(order);
    setOpenOrderDialog(true);
  };

  // 分页处理
  const handlePageChange = (event: React.ChangeEvent<unknown>, page: number) => {
    if (selectedStore) {
      fetchOrders(selectedStore, page);
    }
  };

  // 店铺选择处理
  const handleStoreChange = (store: PrintifyStore) => {
    setSelectedStore(store);
    setCurrentPage(1);
    fetchOrders(store, 1);
  };

  // 初始化
  useEffect(() => {
    const initialize = async () => {
      setLoading(true);
      try {
        await fetchStores();
      } finally {
        setLoading(false);
      }
    };
    initialize();
  }, [fetchStores]);

  // 当选择店铺时获取订单
  useEffect(() => {
    if (selectedStore) {
      fetchOrders(selectedStore, 1);
    }
  }, [selectedStore, fetchOrders]);

  if (loading) {
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
          <OrderIcon color="primary" />
          <Typography variant="h4" component="h1">
            Printify 订单管理
          </Typography>
        </Box>
        <Button
          variant="contained"
          startIcon={<RefreshIcon />}
          onClick={handleRefresh}
          disabled={refreshing || !selectedStore}
        >
          {refreshing ? '刷新中...' : '刷新'}
        </Button>
      </Box>

      {/* 店铺选择 */}
      {stores.length > 0 && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              选择店铺
            </Typography>
            <Grid container spacing={2}>
              {stores.map((store) => (
                <Grid key={store.id_hashid} size={{ xs: 12, sm: 6, md: 4 }}>
                  <Card
                    variant={selectedStore?.id_hashid === store.id_hashid ? 'elevation' : 'outlined'}
                    sx={{
                      cursor: 'pointer',
                      border: selectedStore?.id_hashid === store.id_hashid ? 2 : 1,
                      borderColor: selectedStore?.id_hashid === store.id_hashid ? 'primary.main' : 'divider',
                    }}
                    onClick={() => handleStoreChange(store)}
                  >
                    <CardContent>
                      <Box display="flex" alignItems="center" gap={2}>
                        <StoreIcon color="primary" />
                        <Box>
                          <Typography variant="h6">{store.name}</Typography>
                          <Typography variant="body2" color="text.secondary">
                            ID: {store.external_id}
                          </Typography>
                        </Box>
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          </CardContent>
        </Card>
      )}

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
                  onChange={(e) => setStatusFilter(e.target.value as OrderStatus | 'all')}
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
          </Grid>
        </CardContent>
      </Card>

      {/* 订单列表 */}
      <Card>
        <CardContent>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="h6">
              订单列表 {totalCount > 0 && `(${totalCount} 个订单)`}
            </Typography>
            {loadingOrders && <CircularProgress size={24} />}
          </Box>

          {filteredOrders.length === 0 ? (
            <Box textAlign="center" py={4}>
              <OrderIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
              <Typography variant="h6" color="text.secondary">
                {searchTerm || statusFilter !== 'all' ? '没有找到符合条件的订单' : '暂无订单'}
              </Typography>
            </Box>
          ) : (
            <>
              <TableContainer component={Paper} variant="outlined">
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>订单ID</TableCell>
                      <TableCell>客户信息</TableCell>
                      <TableCell>商品</TableCell>
                      <TableCell>状态</TableCell>
                      <TableCell>总价</TableCell>
                      <TableCell>创建时间</TableCell>
                      <TableCell>操作</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {filteredOrders.map((order) => (
                      <TableRow key={order.id} hover>
                        <TableCell>
                          <Typography variant="body2" fontFamily="monospace">
                            {order.app_order_id}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {order.metadata?.shop_order_id}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Box>
                            <Typography variant="body2" fontWeight="medium">
                              {order.address_to?.first_name || 'N/A'} {order.address_to?.last_name || ''}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              {order.address_to?.email || 'N/A'}
                            </Typography>
                            <br />
                            <Typography variant="caption" color="text.secondary">
                              {order.address_to?.city || 'N/A'}, {order.address_to?.country || 'N/A'}
                            </Typography>
                          </Box>
                        </TableCell>
                        <TableCell>
                          <Box>
                            {order.line_items.slice(0, 2).map((item, index) => (
                              <Typography key={index} variant="caption" display="block">
                                {item.metadata?.title || 'Unknown Product'} x{item.quantity}
                              </Typography>
                            ))}
                            {order.line_items.length > 2 && (
                              <Typography variant="caption" color="text.secondary">
                                +{order.line_items.length - 2} 更多
                              </Typography>
                            )}
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
                            {formatPrice(order.total_price / 100, 'USD')}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Typography variant="caption">
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
            <OrderIcon color="primary" />
            订单详情
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
                        订单ID
                      </Typography>
                      <Typography variant="body1" fontFamily="monospace">
                        {selectedOrder.app_order_id}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {selectedOrder.metadata?.shop_order_id}
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
                        {formatPrice(selectedOrder.total_price / 100, 'USD')}
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
                  </Grid>
                </CardContent>
              </Card>

              {/* 商品列表 */}
              <Card sx={{ mb: 2 }}>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    商品列表
                  </Typography>
                  {selectedOrder.line_items.map((item, index) => (
                    <Box key={index} display="flex" alignItems="center" gap={2} mb={2}>
                      <Box flex={1}>
                        <Typography variant="body1" fontWeight="medium">
                          {item.metadata?.title || 'Unknown Product'}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          数量: {item.quantity} | SKU: {item.metadata?.sku || 'N/A'}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          规格: {item.metadata?.variant_label || 'N/A'}
                        </Typography>
                      </Box>
                      <Typography variant="body1" fontWeight="medium">
                        {formatPrice(item.cost / 100, 'USD')}
                      </Typography>
                    </Box>
                  ))}
                </CardContent>
              </Card>

              {/* 收货地址 */}
              <Card sx={{ mb: 2 }}>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    收货地址
                  </Typography>
                  <Typography variant="body1">
                    {selectedOrder.address_to?.first_name || 'N/A'} {selectedOrder.address_to?.last_name || ''}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {selectedOrder.address_to?.email || 'N/A'}
                    {selectedOrder.address_to?.phone && ` | ${selectedOrder.address_to.phone}`}
                  </Typography>
                  <Typography variant="body2">
                    {selectedOrder.address_to?.address1 || 'N/A'}
                    {selectedOrder.address_to?.address2 && `, ${selectedOrder.address_to.address2}`}
                  </Typography>
                  <Typography variant="body2">
                    {selectedOrder.address_to?.city || 'N/A'}, {selectedOrder.address_to?.region || 'N/A'} {selectedOrder.address_to?.zip || 'N/A'}
                  </Typography>
                  <Typography variant="body2">
                    {selectedOrder.address_to?.country || 'N/A'}
                  </Typography>
                </CardContent>
              </Card>

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

export default PrintifyOrdersPage;
