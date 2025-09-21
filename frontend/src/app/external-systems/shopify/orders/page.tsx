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
  Divider,
  Badge,
  Accordion,
  AccordionSummary,
  AccordionDetails,
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
  Person as CustomerIcon,
  LocationOn as AddressIcon,
  Payment as PaymentIcon,
  Inventory as InventoryIcon,
  ExpandMore as ExpandMoreIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
} from '@mui/icons-material';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { frontendApi } from '@/lib/api';
import { frontendLogger } from '@/lib/frontend-logger';

interface ShopifyOrder {
  id: number;
  shopify_id: string;
  email: string;
  created_at: string;
  updated_at: string;
  number: number;
  note: string;
  token: string;
  gateway: string;
  test: boolean;
  total_price: string;
  subtotal_price: string;
  total_tax: string;
  taxes_included: boolean;
  currency: string;
  financial_status: string;
  confirmed: boolean;
  total_discounts: string;
  buyer_accepts_marketing: boolean;
  name: string;
  referring_site: string;
  landing_site: string;
  cancelled_at: string;
  cancel_reason: string;
  total_line_items_price: string;
  total_tip_received: string;
  total_outstanding: string;
  total_weight: number;
  total_tax_set: any;
  total_discounts_set: any;
  total_shipping_price_set: any;
  total_price_set: any;
  total_tip_received_set: any;
  total_tax_set: any;
  total_outstanding_set: any;
  order_number: number;
  processing_method: string;
  source_name: string;
  fulfillment_status: string;
  tags: string;
  contact_email: string;
  order_status_url: string;
  presentment_currency: string;
  total_line_items_price_set: any;
  total_discounts_set: any;
  total_shipping_price_set: any;
  total_tax_set: any;
  total_tip_received_set: any;
  total_outstanding_set: any;
  total_price_set: any;
  admin_graphql_api_id: string;
  shipping_address: ShopifyAddress;
  billing_address: ShopifyAddress;
  customer: ShopifyCustomer;
  line_items: ShopifyLineItem[];
  fulfillments: ShopifyFulfillment[];
  refunds: ShopifyRefund[];
}

interface ShopifyAddress {
  first_name: string;
  address1: string;
  phone: string;
  city: string;
  zip: string;
  province: string;
  country: string;
  last_name: string;
  address2: string;
  company: string;
  latitude: number;
  longitude: number;
  name: string;
  country_code: string;
  province_code: string;
}

interface ShopifyCustomer {
  id: number;
  email: string;
  accepts_marketing: boolean;
  created_at: string;
  updated_at: string;
  first_name: string;
  last_name: string;
  orders_count: number;
  state: string;
  total_spent: string;
  last_order_id: number;
  note: string;
  verified_email: boolean;
  multipass_identifier: string;
  tax_exempt: boolean;
  phone: string;
  tags: string;
  last_order_name: string;
  currency: string;
  accepts_marketing_updated_at: string;
  marketing_opt_in_level: string;
  admin_graphql_api_id: string;
  default_address: ShopifyAddress;
}

interface ShopifyLineItem {
  id: number;
  variant_id: number;
  title: string;
  quantity: number;
  sku: string;
  variant_title: string;
  vendor: string;
  fulfillment_service: string;
  product_id: number;
  requires_shipping: boolean;
  taxable: boolean;
  gift_card: boolean;
  name: string;
  variant_inventory_management: string;
  properties: any[];
  product_exists: boolean;
  fulfillable_quantity: number;
  grams: number;
  price: string;
  total_discount: string;
  fulfillment_status: string;
  price_set: any;
  total_discount_set: any;
  discount_allocations: any[];
  duties: any[];
  admin_graphql_api_id: string;
  tax_lines: any[];
}

interface ShopifyFulfillment {
  id: number;
  order_id: number;
  status: string;
  created_at: string;
  service: string;
  updated_at: string;
  tracking_company: string;
  tracking_number: string;
  tracking_numbers: string[];
  tracking_url: string;
  tracking_urls: string[];
  receipt: any;
  name: string;
  admin_graphql_api_id: string;
  line_items: ShopifyLineItem[];
}

interface ShopifyRefund {
  id: number;
  order_id: number;
  created_at: string;
  note: string;
  user_id: number;
  processed_at: string;
  restock: boolean;
  admin_graphql_api_id: string;
  order_adjustments: any[];
  transactions: any[];
  refund_line_items: any[];
}

interface ShopifyStore {
  id: number;
  name: string;
  shop_domain: string;
  access_token: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

const ShopifyOrdersPage: React.FC = () => {
  const [orders, setOrders] = useState<ShopifyOrder[]>([]);
  const [stores, setStores] = useState<ShopifyStore[]>([]);
  const [selectedStore, setSelectedStore] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [selectedOrder, setSelectedOrder] = useState<ShopifyOrder | null>(null);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [sortBy, setSortBy] = useState<'created_at' | 'updated_at' | 'total_price' | 'order_number'>('created_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [financialStatusFilter, setFinancialStatusFilter] = useState<string>('all');
  const [fulfillmentStatusFilter, setFulfillmentStatusFilter] = useState<string>('all');

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
  const fetchOrders = useCallback(async (storeId: number, pageNum: number = 1) => {
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
  const handleViewDetails = (order: ShopifyOrder) => {
    setSelectedOrder(order);
    setDetailsOpen(true);
  };

  // 格式化价格
  const formatPrice = (price: string, currency: string = 'USD') => {
    return `${currency} ${parseFloat(price).toFixed(2)}`;
  };

  // 格式化日期
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  // 获取财务状态颜色
  const getFinancialStatusColor = (status: string) => {
    switch (status) {
      case 'paid':
        return 'success';
      case 'pending':
        return 'warning';
      case 'partially_paid':
        return 'info';
      case 'refunded':
      case 'partially_refunded':
        return 'error';
      case 'voided':
        return 'default';
      default:
        return 'default';
    }
  };

  // 获取财务状态标签
  const getFinancialStatusLabel = (status: string) => {
    switch (status) {
      case 'paid':
        return '已支付';
      case 'pending':
        return '待支付';
      case 'partially_paid':
        return '部分支付';
      case 'refunded':
        return '已退款';
      case 'partially_refunded':
        return '部分退款';
      case 'voided':
        return '已作废';
      default:
        return status;
    }
  };

  // 获取履行状态颜色
  const getFulfillmentStatusColor = (status: string) => {
    switch (status) {
      case 'fulfilled':
        return 'success';
      case 'partial':
        return 'warning';
      case 'unfulfilled':
        return 'error';
      default:
        return 'default';
    }
  };

  // 获取履行状态标签
  const getFulfillmentStatusLabel = (status: string) => {
    switch (status) {
      case 'fulfilled':
        return '已履行';
      case 'partial':
        return '部分履行';
      case 'unfulfilled':
        return '未履行';
      default:
        return status || '未知';
    }
  };

  return (
    <ProtectedRoute>
      <DashboardLayout>
        <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <OrderIcon />
          Shopify 订单管理
        </Typography>
        <Button
          variant="contained"
          startIcon={<RefreshIcon />}
          onClick={handleRefresh}
          disabled={loading}
        >
          刷新
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
                    border: selectedStore === store.id ? 2 : 1,
                    borderColor: selectedStore === store.id ? 'primary.main' : 'divider',
                    '&:hover': { borderColor: 'primary.main' },
                  }}
                  onClick={() => setSelectedStore(store.id)}
                >
                  <CardContent>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                      <StoreIcon />
                      <Typography variant="h6">{store.name}</Typography>
                      <Chip
                        label={store.is_active ? '活跃' : '非活跃'}
                        color={store.is_active ? 'success' : 'default'}
                        size="small"
                      />
                    </Box>
                    <Typography variant="body2" color="text.secondary">
                      {store.shop_domain}
                    </Typography>
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
                <Grid item xs={12} md={3}>
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
                    <InputLabel>排序</InputLabel>
                    <Select
                      value={sortBy}
                      onChange={(e) => setSortBy(e.target.value as any)}
                    >
                      <MenuItem value="created_at">创建时间</MenuItem>
                      <MenuItem value="updated_at">更新时间</MenuItem>
                      <MenuItem value="total_price">总价</MenuItem>
                      <MenuItem value="order_number">订单号</MenuItem>
                    </Select>
                  </FormControl>
                </Grid>
                <Grid item xs={12} md={2}>
                  <FormControl fullWidth>
                    <InputLabel>财务状态</InputLabel>
                    <Select
                      value={financialStatusFilter}
                      onChange={(e) => setFinancialStatusFilter(e.target.value)}
                    >
                      <MenuItem value="all">全部</MenuItem>
                      <MenuItem value="paid">已支付</MenuItem>
                      <MenuItem value="pending">待支付</MenuItem>
                      <MenuItem value="partially_paid">部分支付</MenuItem>
                      <MenuItem value="refunded">已退款</MenuItem>
                      <MenuItem value="voided">已作废</MenuItem>
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
                      <MenuItem value="fulfilled">已履行</MenuItem>
                      <MenuItem value="partial">部分履行</MenuItem>
                      <MenuItem value="unfulfilled">未履行</MenuItem>
                    </Select>
                  </FormControl>
                </Grid>
                <Grid item xs={12} md={1}>
                  <Button
                    fullWidth
                    variant="outlined"
                    onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
                    startIcon={<FilterIcon />}
                  >
                    {sortOrder === 'asc' ? '升序' : '降序'}
                  </Button>
                </Grid>
                <Grid item xs={12} md={2}>
                  <Button
                    fullWidth
                    variant="contained"
                    onClick={handleSearch}
                    startIcon={<SearchIcon />}
                  >
                    搜索
                  </Button>
                </Grid>
              </Grid>
            </CardContent>
          </Card>

          {/* 订单列表 */}
          {loading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
              <CircularProgress />
            </Box>
          ) : error ? (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          ) : orders.length === 0 ? (
            <Card>
              <CardContent sx={{ textAlign: 'center', p: 4 }}>
                <Typography variant="h6" color="text.secondary">
                  暂无订单数据
                </Typography>
              </CardContent>
            </Card>
          ) : (
            <>
              <TableContainer component={Paper}>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>订单号</TableCell>
                      <TableCell>客户</TableCell>
                      <TableCell>总价</TableCell>
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
                            #{order.order_number || order.number}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {order.name}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Box>
                            <Typography variant="body2">
                              {order.customer?.first_name} {order.customer?.last_name}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              {order.email}
                            </Typography>
                          </Box>
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" fontWeight="medium">
                            {formatPrice(order.total_price, order.currency)}
                          </Typography>
                          {order.total_discounts && parseFloat(order.total_discounts) > 0 && (
                            <Typography variant="caption" color="success.main">
                              折扣: {formatPrice(order.total_discounts, order.currency)}
                            </Typography>
                          )}
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={getFinancialStatusLabel(order.financial_status)}
                            color={getFinancialStatusColor(order.financial_status) as any}
                            size="small"
                          />
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={getFulfillmentStatusLabel(order.fulfillment_status)}
                            color={getFulfillmentStatusColor(order.fulfillment_status) as any}
                            size="small"
                          />
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2">
                            {formatDate(order.created_at)}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Stack direction="row" spacing={1}>
                            <Tooltip title="查看详情">
                              <IconButton
                                size="small"
                                onClick={() => handleViewDetails(order)}
                              >
                                <ViewIcon />
                              </IconButton>
                            </Tooltip>
                            <Tooltip title="编辑">
                              <IconButton size="small" color="secondary">
                                <EditIcon />
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
                    onChange={(_, newPage) => fetchOrders(selectedStore, newPage)}
                    color="primary"
                  />
                </Box>
              )}
            </>
          )}
        </>
      )}

      {/* 订单详情对话框 */}
      <Dialog
        open={detailsOpen}
        onClose={() => setDetailsOpen(false)}
        maxWidth="lg"
        fullWidth
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <OrderIcon />
            订单详情 #{selectedOrder?.order_number || selectedOrder?.number}
          </Box>
        </DialogTitle>
        <DialogContent>
          {selectedOrder && (
            <Box>
              {/* 订单基本信息 */}
              <Grid container spacing={3} sx={{ mb: 3 }}>
                <Grid item xs={12} md={6}>
                  <Typography variant="h6" gutterBottom>
                    订单信息
                  </Typography>
                  <Typography variant="body2" paragraph>
                    <strong>订单号:</strong> #{selectedOrder.order_number || selectedOrder.number}
                  </Typography>
                  <Typography variant="body2" paragraph>
                    <strong>订单名称:</strong> {selectedOrder.name}
                  </Typography>
                  <Typography variant="body2" paragraph>
                    <strong>创建时间:</strong> {formatDate(selectedOrder.created_at)}
                  </Typography>
                  <Typography variant="body2" paragraph>
                    <strong>更新时间:</strong> {formatDate(selectedOrder.updated_at)}
                  </Typography>
                  <Typography variant="body2" paragraph>
                    <strong>财务状态:</strong> 
                    <Chip
                      label={getFinancialStatusLabel(selectedOrder.financial_status)}
                      color={getFinancialStatusColor(selectedOrder.financial_status) as any}
                      size="small"
                      sx={{ ml: 1 }}
                    />
                  </Typography>
                  <Typography variant="body2" paragraph>
                    <strong>履行状态:</strong> 
                    <Chip
                      label={getFulfillmentStatusLabel(selectedOrder.fulfillment_status)}
                      color={getFulfillmentStatusColor(selectedOrder.fulfillment_status) as any}
                      size="small"
                      sx={{ ml: 1 }}
                    />
                  </Typography>
                </Grid>
                <Grid item xs={12} md={6}>
                  <Typography variant="h6" gutterBottom>
                    价格信息
                  </Typography>
                  <Typography variant="body2" paragraph>
                    <strong>小计:</strong> {formatPrice(selectedOrder.subtotal_price, selectedOrder.currency)}
                  </Typography>
                  <Typography variant="body2" paragraph>
                    <strong>税费:</strong> {formatPrice(selectedOrder.total_tax, selectedOrder.currency)}
                  </Typography>
                  {selectedOrder.total_discounts && parseFloat(selectedOrder.total_discounts) > 0 && (
                    <Typography variant="body2" paragraph>
                      <strong>折扣:</strong> -{formatPrice(selectedOrder.total_discounts, selectedOrder.currency)}
                    </Typography>
                  )}
                  <Typography variant="body2" paragraph>
                    <strong>总价:</strong> {formatPrice(selectedOrder.total_price, selectedOrder.currency)}
                  </Typography>
                  <Typography variant="body2" paragraph>
                    <strong>货币:</strong> {selectedOrder.currency}
                  </Typography>
                </Grid>
              </Grid>

              <Divider sx={{ my: 3 }} />

              {/* 客户信息 */}
              {selectedOrder.customer && (
                <Accordion>
                  <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                    <Typography variant="h6">客户信息</Typography>
                  </AccordionSummary>
                  <AccordionDetails>
                    <Grid container spacing={2}>
                      <Grid item xs={12} md={6}>
                        <Typography variant="body2" paragraph>
                          <strong>姓名:</strong> {selectedOrder.customer.first_name} {selectedOrder.customer.last_name}
                        </Typography>
                        <Typography variant="body2" paragraph>
                          <strong>邮箱:</strong> {selectedOrder.customer.email}
                        </Typography>
                        <Typography variant="body2" paragraph>
                          <strong>电话:</strong> {selectedOrder.customer.phone || '-'}
                        </Typography>
                        <Typography variant="body2" paragraph>
                          <strong>订单数:</strong> {selectedOrder.customer.orders_count}
                        </Typography>
                      </Grid>
                      <Grid item xs={12} md={6}>
                        <Typography variant="body2" paragraph>
                          <strong>总消费:</strong> {formatPrice(selectedOrder.customer.total_spent, selectedOrder.currency)}
                        </Typography>
                        <Typography variant="body2" paragraph>
                          <strong>状态:</strong> {selectedOrder.customer.state}
                        </Typography>
                        <Typography variant="body2" paragraph>
                          <strong>接受营销:</strong> {selectedOrder.customer.accepts_marketing ? '是' : '否'}
                        </Typography>
                        <Typography variant="body2" paragraph>
                          <strong>标签:</strong> {selectedOrder.customer.tags || '-'}
                        </Typography>
                      </Grid>
                    </Grid>
                  </AccordionDetails>
                </Accordion>
              )}

              {/* 收货地址 */}
              {selectedOrder.shipping_address && (
                <Accordion>
                  <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                    <Typography variant="h6">收货地址</Typography>
                  </AccordionSummary>
                  <AccordionDetails>
                    <Typography variant="body2" paragraph>
                      <strong>姓名:</strong> {selectedOrder.shipping_address.first_name} {selectedOrder.shipping_address.last_name}
                    </Typography>
                    <Typography variant="body2" paragraph>
                      <strong>地址:</strong> {selectedOrder.shipping_address.address1}
                      {selectedOrder.shipping_address.address2 && `, ${selectedOrder.shipping_address.address2}`}
                    </Typography>
                    <Typography variant="body2" paragraph>
                      <strong>城市:</strong> {selectedOrder.shipping_address.city}, {selectedOrder.shipping_address.province} {selectedOrder.shipping_address.zip}
                    </Typography>
                    <Typography variant="body2" paragraph>
                      <strong>国家:</strong> {selectedOrder.shipping_address.country}
                    </Typography>
                    <Typography variant="body2" paragraph>
                      <strong>电话:</strong> {selectedOrder.shipping_address.phone || '-'}
                    </Typography>
                  </AccordionDetails>
                </Accordion>
              )}

              {/* 订单商品 */}
              <Accordion>
                <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                  <Typography variant="h6">订单商品 ({selectedOrder.line_items?.length || 0})</Typography>
                </AccordionSummary>
                <AccordionDetails>
                  <TableContainer component={Paper}>
                    <Table>
                      <TableHead>
                        <TableRow>
                          <TableCell>商品</TableCell>
                          <TableCell>SKU</TableCell>
                          <TableCell>数量</TableCell>
                          <TableCell>单价</TableCell>
                          <TableCell>小计</TableCell>
                          <TableCell>履行状态</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {selectedOrder.line_items?.map((item) => (
                          <TableRow key={item.id}>
                            <TableCell>
                              <Typography variant="body2" fontWeight="medium">
                                {item.title}
                              </Typography>
                              {item.variant_title && (
                                <Typography variant="caption" color="text.secondary">
                                  {item.variant_title}
                                </Typography>
                              )}
                            </TableCell>
                            <TableCell>{item.sku || '-'}</TableCell>
                            <TableCell>{item.quantity}</TableCell>
                            <TableCell>{formatPrice(item.price, selectedOrder.currency)}</TableCell>
                            <TableCell>{formatPrice((parseFloat(item.price) * item.quantity).toString(), selectedOrder.currency)}</TableCell>
                            <TableCell>
                              <Chip
                                label={getFulfillmentStatusLabel(item.fulfillment_status)}
                                color={getFulfillmentStatusColor(item.fulfillment_status) as any}
                                size="small"
                              />
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                </AccordionDetails>
              </Accordion>

              {/* 履行信息 */}
              {selectedOrder.fulfillments && selectedOrder.fulfillments.length > 0 && (
                <Accordion>
                  <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                    <Typography variant="h6">履行信息 ({selectedOrder.fulfillments.length})</Typography>
                  </AccordionSummary>
                  <AccordionDetails>
                    {selectedOrder.fulfillments.map((fulfillment) => (
                      <Card key={fulfillment.id} sx={{ mb: 2 }}>
                        <CardContent>
                          <Typography variant="h6" gutterBottom>
                            履行 #{fulfillment.id}
                          </Typography>
                          <Typography variant="body2" paragraph>
                            <strong>状态:</strong> 
                            <Chip
                              label={getFulfillmentStatusLabel(fulfillment.status)}
                              color={getFulfillmentStatusColor(fulfillment.status) as any}
                              size="small"
                              sx={{ ml: 1 }}
                            />
                          </Typography>
                          <Typography variant="body2" paragraph>
                            <strong>服务:</strong> {fulfillment.service}
                          </Typography>
                          {fulfillment.tracking_number && (
                            <Typography variant="body2" paragraph>
                              <strong>跟踪号:</strong> {fulfillment.tracking_number}
                            </Typography>
                          )}
                          {fulfillment.tracking_company && (
                            <Typography variant="body2" paragraph>
                              <strong>快递公司:</strong> {fulfillment.tracking_company}
                            </Typography>
                          )}
                          <Typography variant="body2" paragraph>
                            <strong>创建时间:</strong> {formatDate(fulfillment.created_at)}
                          </Typography>
                        </CardContent>
                      </Card>
                    ))}
                  </AccordionDetails>
                </Accordion>
              )}
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
