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
  Sync as SyncIcon,
  Store as StoreIcon,
  ShoppingCart as ShoppingCartIcon,
  Person as PersonIcon,
  AttachMoney as MoneyIcon,
  CalendarToday as CalendarIcon,
  FilterList as FilterIcon,
  OpenInNew as OpenInNewIcon,
  Link as LinkIcon,
} from '@mui/icons-material';
import Link from 'next/link';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { frontendApi } from '@/lib/api';
import { frontendLogger } from '@/lib/frontend-logger';

interface ShopifyOrder {
  id: string;
  name: string;
  email: string;
  phone?: string;
  created_at: string;
  updated_at: string;
  total_price: string;
  currency: string;
  fulfillment_status: string;
  financial_status: string;
  cancelled?: boolean;
  shipping_address?: {
    firstName?: string;
    lastName?: string;
    company?: string;
    address1?: string;
    address2?: string;
    city?: string;
    province?: string;
    country?: string;
    zip?: string;
    phone?: string;
  };
  billing_address?: {
    firstName?: string;
    lastName?: string;
    company?: string;
    address1?: string;
    address2?: string;
    city?: string;
    province?: string;
    country?: string;
    zip?: string;
    phone?: string;
  };
  customer?: {
    id: string;
    name: string;
    email: string;
  };
  line_items?: any[];
  fulfillments?: any[];
  refunds?: any[];
  line_items_count: number;
}

interface ShopifyStore {
  id: number;
  id_hashid: string;
  name: string;
  external_system_id: string;
  external_id?: string; // 添加这个字段
  shop_domain: string;
  access_token: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

const ShopifyOrdersPage: React.FC = () => {
  const [orders, setOrders] = useState<ShopifyOrder[]>([]);
  const [stores, setStores] = useState<ShopifyStore[]>([]);
  const [selectedStore, setSelectedStore] = useState<ShopifyStore | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [selectedOrder, setSelectedOrder] = useState<ShopifyOrder | null>(null);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [sortBy, setSortBy] = useState<
    'created_at' | 'updated_at' | 'total_price' | 'name'
  >('created_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [financialStatusFilter, setFinancialStatusFilter] =
    useState<string>('all');
  const [fulfillmentStatusFilter, setFulfillmentStatusFilter] =
    useState<string>('all');
  const [syncing, setSyncing] = useState(false);
  const [jsonModalOpen, setJsonModalOpen] = useState(false);
  const [orderJson, setOrderJson] = useState<any>(null);
  const [loadingJson, setLoadingJson] = useState(false);
  const [savingToDatabase, setSavingToDatabase] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  /** 列表勾选的订单 id（用于在列表页直接导入，无需进详情） */
  const [selectedOrderIds, setSelectedOrderIds] = useState<string[]>([]);
  const [batchImporting, setBatchImporting] = useState(false);
  /** 已导入到本系统的 Shopify 订单 id 集合（gid 格式），用于显示「已导入」与跳转链接 */
  const [syncedOrderIds, setSyncedOrderIds] = useState<Set<string>>(new Set());

  // 获取 Shopify 店铺列表
  const fetchStores = useCallback(async () => {
    try {
      frontendLogger.info('🔄 获取 Shopify 店铺列表');
      const response = await frontendApi.get(
        '/api/external-systems/shopify/stores'
      );
      setStores(response.data.stores || []);
      frontendLogger.info('✅ Shopify 店铺列表获取成功', {
        count: response.data.stores?.length || 0,
      });
    } catch (error: any) {
      frontendLogger.error('❌ 获取 Shopify 店铺列表失败', {
        error: error.message,
      });
      setError('获取店铺列表失败');
    }
  }, []);

  // 获取 Shopify 订单列表
  const fetchOrders = useCallback(
    async (store: ShopifyStore, pageNum: number = 1) => {
      if (!store) return;

      setLoading(true);
      setError(null);

      try {
        frontendLogger.info('🔄 获取 Shopify 订单列表', {
          storeId: store.id_hashid,
          page: pageNum,
        });
        const response = await frontendApi.get(
          `/api/external-systems/shopify/${store.id_hashid}/orders`,
          {
            params: {
              page: pageNum,
              limit: 20,
              search: searchTerm,
              sort_by: sortBy,
              sort_order: sortOrder,
              status: statusFilter !== 'all' ? statusFilter : undefined,
              financial_status:
                financialStatusFilter !== 'all'
                  ? financialStatusFilter
                  : undefined,
              fulfillment_status:
                fulfillmentStatusFilter !== 'all'
                  ? fulfillmentStatusFilter
                  : undefined,
            },
          }
        );

        setOrders(response.data.orders || []);
        setTotalPages(response.data.pagination?.total_pages || 1);
        setPage(pageNum);

        frontendLogger.info('✅ Shopify 订单列表获取成功', {
          count: response.data.orders?.length || 0,
          totalPages: response.data.pagination?.total_pages || 1,
        });
      } catch (error: any) {
        frontendLogger.error('❌ 获取 Shopify 订单列表失败', {
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
      statusFilter,
      financialStatusFilter,
      fulfillmentStatusFilter,
    ]
  );

  // 同步订单
  const syncOrders = useCallback(
    async (store: ShopifyStore) => {
      if (!store) return;

      setSyncing(true);
      setError(null);

      try {
        frontendLogger.info('🔄 开始同步 Shopify 订单', {
          storeId: store.id_hashid,
        });
        const response = await frontendApi.post(
          `/api/external-systems/shopify/${store.id_hashid}/sync-orders`
        );

        frontendLogger.info('✅ Shopify 订单同步成功', {
          ordersSynced: response.data.orders_synced,
          ordersUpdated: response.data.orders_updated,
          totalProcessed: response.data.total_processed,
        });

        // 同步成功后刷新订单列表
        await fetchOrders(store, 1);
      } catch (error: any) {
        frontendLogger.error('❌ Shopify 订单同步失败', {
          error: error.message,
        });
        setError('同步订单失败');
      } finally {
        setSyncing(false);
      }
    },
    [fetchOrders]
  );

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

  // 拉取已导入订单 id 集合，用于显示「已导入」与跳转
  const fetchSyncedOrderIds = useCallback(async () => {
    try {
      const res = await frontendApi.get('/api/shopify-orders', {
        params: { page: 1, limit: 500 },
      });
      const list = res.data?.orders || [];
      const ids = new Set(list.map((o: { shopify_order_id: string }) => o.shopify_order_id));
      setSyncedOrderIds(ids);
    } catch {
      setSyncedOrderIds(new Set());
    }
  }, []);

  useEffect(() => {
    fetchSyncedOrderIds();
  }, [fetchSyncedOrderIds]);
  // 导入成功后刷新已导入集合
  const refreshSyncedOrderIds = () => fetchSyncedOrderIds();

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
  const handleViewOrder = async (order: ShopifyOrder) => {
    try {
      setLoading(true);
      setError(null);

      if (!selectedStore) {
        setError('请先选择一个店铺');
        return;
      }

      // 从订单ID中提取Shopify订单ID
      const orderId = order.id.split('/').pop(); // 移除 "gid://shopify/Order/" 前缀

      frontendLogger.info('🔍 开始获取订单详情', {
        page: 'shopify-orders',
        component: 'handleViewOrder',
        action: 'fetch-order-details',
        orderId,
        shopId: selectedStore.external_system_id,
      });

      const response = await fetch(
        `/api/external-systems/shopify/orders/${orderId}?shop_id=${selectedStore.external_system_id}`,
        {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${localStorage.getItem('access_token')}`,
          },
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP ${response.status}`);
      }

      const data = await response.json();

      frontendLogger.info('📡 订单详情响应数据', {
        page: 'shopify-orders',
        component: 'handleViewOrder',
        action: 'order-details-response',
        hasOrder: !!data.order,
        orderKeys: data.order ? Object.keys(data.order) : [],
      });

      if (data.success && data.order) {
        // 转换数据格式以匹配前端期望的结构
        const transformedOrder = {
          ...data.order,
          created_at: data.order.createdAt,
          updated_at: data.order.updatedAt,
          total_price: data.order.totalPriceSet?.shopMoney?.amount || '0',
          currency: data.order.totalPriceSet?.shopMoney?.currencyCode || 'USD',
          fulfillment_status: data.order.displayFulfillmentStatus,
          financial_status: data.order.displayFinancialStatus,
          cancelled: !!(data.order.cancelledAt || data.order.cancelReason),
          customer: data.order.customer
            ? {
                id: data.order.customer.id,
                name: `${data.order.customer.firstName || ''} ${data.order.customer.lastName || ''}`.trim(),
                email: data.order.customer.email,
              }
            : null,
          shipping_address: data.order.shippingAddress,
          billing_address: data.order.billingAddress,
          line_items:
            data.order.lineItems?.edges?.map((edge: any) => ({
              ...edge.node,
              price: edge.node.originalUnitPriceSet?.shopMoney?.amount || '0',
              currency:
                edge.node.originalUnitPriceSet?.shopMoney?.currencyCode ||
                'USD',
            })) || [],
          fulfillments: data.order.fulfillments || [],
          refunds: data.order.refunds || [],
        };

        setSelectedOrder(transformedOrder);
        setDetailsOpen(true);
      } else {
        throw new Error(data.message || '获取订单详情失败');
      }
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : '获取订单详情失败';
      setError(errorMessage);
      frontendLogger.error('❌ 获取订单详情失败', {
        page: 'shopify-orders',
        component: 'handleViewOrder',
        action: 'fetch-order-details-error',
        error: errorMessage,
      });
    } finally {
      setLoading(false);
    }
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
    if (!dateString) return '未知';
    const date = new Date(dateString);
    if (isNaN(date.getTime())) return '无效日期';
    return date.toLocaleString('zh-CN');
  };

  // 获取订单 JSON 数据
  const fetchOrderJson = useCallback(
    async (orderId: string) => {
      if (!selectedStore) return;

      try {
        setLoadingJson(true);

        // 从 GraphQL ID 中提取纯数字 ID (例如: gid://shopify/Order/5839241838692 -> 5839241838692)
        // 如果已经是纯数字，则直接使用；否则提取数字部分
        const numericOrderId = orderId.includes('gid://shopify/Order/')
          ? orderId.replace('gid://shopify/Order/', '')
          : orderId;

        frontendLogger.info('🔄 获取 Shopify 订单完整 JSON 数据', {
          originalId: orderId,
          numericId: numericOrderId,
          orderIdType: typeof orderId,
          orderIdLength: orderId.length,
          storeId: selectedStore.external_system_id,
          selectedStoreIdHashid: selectedStore.id_hashid,
          selectedStoreFull: selectedStore,
        });

        const apiUrl = `/api/external-systems/shopify/${selectedStore.id_hashid}/orders/${numericOrderId}/json`;
        frontendLogger.info('🔗 构建的 API URL', {
          apiUrl,
          numericOrderId,
          selectedStoreIdHashid: selectedStore.id_hashid,
        });

        const response = await frontendApi.get(apiUrl);

        frontendLogger.info('✅ Shopify 订单 JSON 数据获取成功', {
          orderId,
          hasData: !!response.data,
        });

        setOrderJson(response.data);
        setJsonModalOpen(true);
      } catch (error: any) {
        frontendLogger.error('❌ 获取订单 JSON 数据失败', {
          error: error.message,
          orderId,
        });
        setError(error.message || '获取订单 JSON 数据失败');
      } finally {
        setLoadingJson(false);
      }
    },
    [selectedStore]
  );

  /** 将单个订单保存到数据库（拉取 JSON + 构建 payload + POST），供详情「保存到数据库」与列表「导入选中」复用 */
  const saveOneOrderToDb = useCallback(
    async (order: ShopifyOrder): Promise<boolean> => {
      if (!selectedStore) return false;
      const numericOrderId = order.id.includes('gid://shopify/Order/')
        ? order.id.replace('gid://shopify/Order/', '')
        : order.id;
      let fullOrderJson: any;
      try {
        const jsonResponse = await frontendApi.get(
          `/api/external-systems/shopify/${selectedStore.id_hashid}/orders/${numericOrderId}/json`
        );
        fullOrderJson = jsonResponse.data;
      } catch {
        fullOrderJson = {
          id: order.id,
          name: order.name,
          financial_status: order.financial_status,
          fulfillment_status: order.fulfillment_status,
          total_price: order.total_price,
          currency: order.currency,
          customer: order.customer,
          line_items: order.line_items,
          shipping_address: order.shipping_address,
          billing_address: order.billing_address,
          created_at: order.created_at,
          updated_at: order.updated_at,
        };
      }
      const orderData = {
        shopify_order_id: order.id,
        name: order.name,
        confirmation_number: order.name,
        financial_status: order.financial_status,
        fulfillment_status: order.fulfillment_status,
        confirmed: true,
        closed: order.fulfillment_status === 'fulfilled',
        cancelled: order.cancelled ?? order.financial_status === 'cancelled',
        currency_code: order.currency,
        total_price: parseFloat(order.total_price) || 0,
        subtotal_price: parseFloat(order.total_price) || 0,
        total_tax: 0,
        total_shipping: 0,
        tags: [],
        note: '',
        customer_data: {
          id: order.customer?.id,
          name: order.customer?.name,
          email: order.customer?.email || order.email,
          phone: order.phone,
        },
        billing_address: order.billing_address,
        shipping_address: order.shipping_address,
        line_items: order.line_items || [],
        fulfillments: order.fulfillments || [],
        refunds: order.refunds || [],
        raw_data: fullOrderJson,
      };
      try {
        await frontendApi.post('/api/shopify-orders/', orderData);
        return true;
      } catch {
        return false;
      }
    },
    [selectedStore]
  );

  // 保存订单到数据库（详情弹窗内）
  const handleSaveToDatabase = useCallback(async () => {
    if (!selectedOrder || !selectedStore) return;
    try {
      setSavingToDatabase(true);
      const ok = await saveOneOrderToDb(selectedOrder);
      if (ok) {
        setError(null);
        setSaveSuccess(true);
        refreshSyncedOrderIds();
        setTimeout(() => setSaveSuccess(false), 3000);
      } else {
        setError('保存订单到数据库失败');
      }
    } catch (e: any) {
      setError(e?.message || '保存订单到数据库失败');
    } finally {
      setSavingToDatabase(false);
    }
  }, [selectedOrder, selectedStore, saveOneOrderToDb, refreshSyncedOrderIds]);

  /** 列表页：导入选中的订单到数据库 */
  const handleBatchImportSelected = useCallback(async () => {
    if (!selectedStore || selectedOrderIds.length === 0) return;
    setBatchImporting(true);
    setError(null);
    let success = 0;
    let fail = 0;
    const list = orders.filter(o => selectedOrderIds.includes(o.id));
    for (let i = 0; i < list.length; i++) {
      const ok = await saveOneOrderToDb(list[i]);
      if (ok) success++;
      else fail++;
    }
    setBatchImporting(false);
    setSelectedOrderIds([]);
    if (success > 0) refreshSyncedOrderIds();
    if (fail === 0) {
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } else {
      setError(`导入完成：成功 ${success} 个，失败 ${fail} 个`);
    }
  }, [selectedStore, selectedOrderIds, orders, saveOneOrderToDb, refreshSyncedOrderIds]);

  // 格式化金额
  const formatPrice = (price: string | number, currency: string) => {
    const numPrice = typeof price === 'string' ? parseFloat(price) : price;
    if (isNaN(numPrice)) return `${currency} 0.00`;
    return `${currency} ${numPrice.toFixed(2)}`;
  };

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
            <Typography variant='h4' gutterBottom>
              Shopify 订单管理
            </Typography>
            <Button
              variant='contained'
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
              <Typography variant='h6' gutterBottom>
                选择店铺
              </Typography>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
                {stores.map(store => (
                  <Box key={store.id} sx={{ width: { xs: '100%', sm: 'calc(50% - 8px)', md: 'calc(33.33% - 8px)' } }}>
                    <Card
                      sx={{
                        cursor: 'pointer',
                        border:
                          selectedStore?.external_system_id ===
                          store.external_system_id
                            ? 2
                            : 1,
                        borderColor:
                          selectedStore?.external_system_id ===
                          store.external_system_id
                            ? 'primary.main'
                            : 'divider',
                        '&:hover': { borderColor: 'primary.main' },
                      }}
                      onClick={() => setSelectedStore(store)}
                    >
                      <CardContent>
                        <Box
                          sx={{ display: 'flex', alignItems: 'center', mb: 1 }}
                        >
                          <StoreIcon sx={{ mr: 1, color: 'primary.main' }} />
                          <Typography variant='h6' component='div'>
                            {store.name}
                          </Typography>
                        </Box>
                        <Typography variant='body2' color='text.secondary'>
                          {store.external_system_id}
                        </Typography>
                        <Chip
                          label={store.is_active ? '活跃' : '非活跃'}
                          color={store.is_active ? 'success' : 'default'}
                          size='small'
                          sx={{ mt: 1 }}
                        />
                      </CardContent>
                    </Card>
                  </Box>
                ))}
              </Box>
            </CardContent>
          </Card>

          {selectedStore && (
            <>
              {/* 搜索和筛选 */}
              <Card sx={{ mb: 3 }}>
                <CardContent>
                  <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap' }}>
                    <Box sx={{ width: { xs: "100%", md: "33.33%" } }}>
                      <TextField
                        fullWidth
                        placeholder='搜索订单...'
                        value={searchTerm}
                        onChange={e => setSearchTerm(e.target.value)}
                        InputProps={{
                          startAdornment: (
                            <InputAdornment position='start'>
                              <SearchIcon />
                            </InputAdornment>
                          ),
                        }}
                        onKeyPress={e => e.key === 'Enter' && handleSearch()}
                      />
                    </Box>
                    <Box sx={{ width: { xs: "100%", md: "16.67%" } }}>
                      <FormControl fullWidth>
                        <InputLabel>排序方式</InputLabel>
                        <Select
                          value={sortBy}
                          onChange={e => setSortBy(e.target.value as any)}
                          label='排序方式'
                        >
                          <MenuItem value='created_at'>创建时间</MenuItem>
                          <MenuItem value='updated_at'>更新时间</MenuItem>
                          <MenuItem value='total_price'>金额</MenuItem>
                          <MenuItem value='name'>订单号</MenuItem>
                        </Select>
                      </FormControl>
                    </Box>
                    <Box sx={{ width: { xs: "100%", md: "16.67%" } }}>
                      <FormControl fullWidth>
                        <InputLabel>排序顺序</InputLabel>
                        <Select
                          value={sortOrder}
                          onChange={e => setSortOrder(e.target.value as any)}
                          label='排序顺序'
                        >
                          <MenuItem value='desc'>降序</MenuItem>
                          <MenuItem value='asc'>升序</MenuItem>
                        </Select>
                      </FormControl>
                    </Box>
                    <Box sx={{ width: { xs: "100%", md: "16.67%" } }}>
                      <FormControl fullWidth>
                        <InputLabel>财务状态</InputLabel>
                        <Select
                          value={financialStatusFilter}
                          onChange={e =>
                            setFinancialStatusFilter(e.target.value)
                          }
                          label='财务状态'
                        >
                          <MenuItem value='all'>全部</MenuItem>
                          <MenuItem value='paid'>已付款</MenuItem>
                          <MenuItem value='pending'>待付款</MenuItem>
                          <MenuItem value='refunded'>已退款</MenuItem>
                        </Select>
                      </FormControl>
                    </Box>
                    <Box sx={{ width: { xs: "100%", md: "16.67%" } }}>
                      <FormControl fullWidth>
                        <InputLabel>履行状态</InputLabel>
                        <Select
                          value={fulfillmentStatusFilter}
                          onChange={e =>
                            setFulfillmentStatusFilter(e.target.value)
                          }
                          label='履行状态'
                        >
                          <MenuItem value='all'>全部</MenuItem>
                          <MenuItem value='fulfilled'>已履行</MenuItem>
                          <MenuItem value='unfulfilled'>未履行</MenuItem>
                          <MenuItem value='partial'>部分履行</MenuItem>
                        </Select>
                      </FormControl>
                    </Box>
                    <Box sx={{ width: "100%" }}>
                      <Stack direction='row' spacing={2}>
                        <Button
                          variant='contained'
                          startIcon={<SearchIcon />}
                          onClick={handleSearch}
                        >
                          搜索
                        </Button>
                        <Button
                          variant='outlined'
                          startIcon={<RefreshIcon />}
                          onClick={handleRefresh}
                        >
                          刷新
                        </Button>
                      </Stack>
                    </Box>
                  </Box>
                </CardContent>
              </Card>

              {/* 订单列表 */}
              <Card>
                <CardContent>
                  <Box
                    sx={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      mb: 2,
                      flexWrap: 'wrap',
                      gap: 1,
                    }}
                  >
                    <Typography variant='h6'>
                      订单列表
                      {orders.length > 0 && (
                        <Chip
                          label={`${orders.length} 个订单`}
                          color='primary'
                          size='small'
                          sx={{ ml: 2 }}
                        />
                      )}
                    </Typography>
                    {selectedOrderIds.length > 0 && (
                      <Button
                        variant='contained'
                        color='primary'
                        startIcon={
                          batchImporting ? (
                            <CircularProgress size={18} color='inherit' />
                          ) : (
                            <SyncIcon />
                          )
                        }
                        onClick={handleBatchImportSelected}
                        disabled={batchImporting}
                      >
                        {batchImporting
                          ? `导入中…`
                          : `导入选中订单 (${selectedOrderIds.length})`}
                      </Button>
                    )}
                  </Box>

                  {loading && (
                    <Box
                      sx={{ display: 'flex', justifyContent: 'center', p: 3 }}
                    >
                      <CircularProgress />
                    </Box>
                  )}

                  {error && (
                    <Alert severity='error' sx={{ mb: 2 }}>
                      {error}
                    </Alert>
                  )}

                  {saveSuccess && (
                    <Alert severity='success' sx={{ mb: 2 }}>
                      订单已成功保存到数据库！
                    </Alert>
                  )}

                  {!loading && !error && orders.length === 0 && (
                    <Box sx={{ textAlign: 'center', py: 4 }}>
                      <ShoppingCartIcon
                        sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }}
                      />
                      <Typography
                        variant='h6'
                        color='text.secondary'
                        gutterBottom
                      >
                        暂无订单数据
                      </Typography>
                      <Typography variant='body2' color='text.secondary'>
                        请先同步订单或检查筛选条件
                      </Typography>
                    </Box>
                  )}

                  {!loading && !error && orders.length > 0 && (
                    <>
                      <TableContainer component={Paper} variant='outlined'>
                        <Table>
                          <TableHead>
                            <TableRow>
                              <TableCell padding='checkbox'>
                                <Checkbox
                                  indeterminate={
                                    selectedOrderIds.length > 0 &&
                                    selectedOrderIds.length < orders.length
                                  }
                                  checked={
                                    orders.length > 0 &&
                                    selectedOrderIds.length === orders.length
                                  }
                                  onChange={() => {
                                    if (selectedOrderIds.length === orders.length)
                                      setSelectedOrderIds([]);
                                    else
                                      setSelectedOrderIds(orders.map(o => o.id));
                                  }}
                                />
                              </TableCell>
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
                            {orders.map(order => (
                              <TableRow key={order.id} hover>
                                <TableCell padding='checkbox'>
                                  <Checkbox
                                    checked={selectedOrderIds.includes(order.id)}
                                    onChange={() => {
                                      setSelectedOrderIds(prev =>
                                        prev.includes(order.id)
                                          ? prev.filter(id => id !== order.id)
                                          : [...prev, order.id]
                                      );
                                    }}
                                  />
                                </TableCell>
                                <TableCell>
                                  <Typography
                                    variant='body2'
                                    fontWeight='medium'
                                  >
                                    {order.name}
                                  </Typography>
                                </TableCell>
                                <TableCell>
                                  <Box
                                    sx={{
                                      display: 'flex',
                                      alignItems: 'center',
                                    }}
                                  >
                                    <Avatar
                                      sx={{ width: 32, height: 32, mr: 1 }}
                                    >
                                      <PersonIcon />
                                    </Avatar>
                                    <Box>
                                      <Typography variant='body2'>
                                        {order.customer?.name || '未知客户'}
                                      </Typography>
                                      <Typography
                                        variant='caption'
                                        color='text.secondary'
                                      >
                                        {order.customer?.email ||
                                          order.email ||
                                          '无邮箱'}
                                      </Typography>
                                    </Box>
                                  </Box>
                                </TableCell>
                                <TableCell>
                                  <Typography
                                    variant='body2'
                                    fontWeight='medium'
                                  >
                                    {formatPrice(
                                      order.total_price,
                                      order.currency
                                    )}
                                  </Typography>
                                </TableCell>
                                <TableCell>
                                  {order.cancelled ? (
                                    <Chip label='已取消' color='error' size='small' />
                                  ) : (
                                    <Chip
                                      label={order.financial_status || '未知'}
                                      color={getStatusColor(
                                        order.financial_status
                                      )}
                                      size='small'
                                    />
                                  )}
                                </TableCell>
                                <TableCell>
                                  {order.cancelled ? (
                                    <Chip label='已取消' color='error' size='small' />
                                  ) : (
                                    <Chip
                                      label={order.fulfillment_status || '未知'}
                                      color={getStatusColor(
                                        order.fulfillment_status
                                      )}
                                      size='small'
                                    />
                                  )}
                                </TableCell>
                                <TableCell>
                                  <Typography variant='body2'>
                                    {formatDate(order.created_at)}
                                  </Typography>
                                </TableCell>
                                <TableCell>
                                  <Stack direction='row' alignItems='center' spacing={0.5} flexWrap='wrap'>
                                    {syncedOrderIds.has(order.id) && (
                                      <Chip label='已导入' size='small' color='success' sx={{ mr: 0.5 }} />
                                    )}
                                    {syncedOrderIds.has(order.id) && (
                                      <Tooltip title='在同步订单页按订单号筛选'>
                                        <Button
                                          component={Link}
                                          href={`/external-systems/shopify/synced-orders?search=${encodeURIComponent(order.name.replace(/^#/, ''))}`}
                                          size='small'
                                          startIcon={<LinkIcon />}
                                        >
                                          同步订单
                                        </Button>
                                      </Tooltip>
                                    )}
                                    {selectedStore && (
                                      <Tooltip title='在 Shopify 后台打开（新标签页）'>
                                        <IconButton
                                          size='small'
                                          component='a'
                                          href={`https://admin.shopify.com/store/${selectedStore.external_id || (selectedStore.shop_domain || '').replace(/\.myshopify\.com.*$/, '')}/orders/${order.id.replace('gid://shopify/Order/', '')}`}
                                          target='_blank'
                                          rel='noopener noreferrer'
                                        >
                                          <OpenInNewIcon fontSize='small' />
                                        </IconButton>
                                      </Tooltip>
                                    )}
                                    <Tooltip title='查看详情'>
                                      <IconButton
                                        size='small'
                                        onClick={() => handleViewOrder(order)}
                                      >
                                        <ViewIcon />
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
                        <Box
                          sx={{
                            display: 'flex',
                            justifyContent: 'center',
                            mt: 3,
                          }}
                        >
                          <Pagination
                            count={totalPages}
                            page={page}
                            onChange={(_, value) =>
                              fetchOrders(selectedStore, value)
                            }
                            color='primary'
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
            maxWidth='lg'
            fullWidth
          >
            <DialogTitle>
              <Box
                sx={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <Typography variant='h6'>
                  订单详情 - {selectedOrder?.name}
                </Typography>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Typography variant='body2' color='text.secondary'>
                    Shopify订单ID:
                  </Typography>
                  <Chip
                    label={selectedOrder?.id || ''}
                    color='primary'
                    size='small'
                    sx={{ cursor: 'pointer' }}
                    onClick={() =>
                      selectedOrder && fetchOrderJson(selectedOrder.id)
                    }
                    disabled={loadingJson}
                  />
                  {loadingJson && <CircularProgress size={16} />}
                </Box>
              </Box>
            </DialogTitle>
            <DialogContent>
              {selectedOrder && (
                <Box>
                  <Box sx={{ display: 'flex', gap: 3, flexWrap: 'wrap' }}>
                    {/* 基本信息 */}
                    <Box sx={{ width: { xs: "100%", md: "50%" } }}>
                      <Typography variant='h6' gutterBottom>
                        基本信息
                      </Typography>
                      <Stack spacing={1}>
                        <Box
                          sx={{
                            display: 'flex',
                            justifyContent: 'space-between',
                          }}
                        >
                          <Typography variant='body2' color='text.secondary'>
                            订单号:
                          </Typography>
                          <Typography variant='body2'>
                            {selectedOrder.name}
                          </Typography>
                        </Box>
                        <Box
                          sx={{
                            display: 'flex',
                            justifyContent: 'space-between',
                          }}
                        >
                          <Typography variant='body2' color='text.secondary'>
                            金额:
                          </Typography>
                          <Typography variant='body2' fontWeight='medium'>
                            {formatPrice(
                              selectedOrder.total_price,
                              selectedOrder.currency
                            )}
                          </Typography>
                        </Box>
                        <Box
                          sx={{
                            display: 'flex',
                            justifyContent: 'space-between',
                          }}
                        >
                          <Typography variant='body2' color='text.secondary'>
                            财务状态:
                          </Typography>
                          {selectedOrder.cancelled ? (
                            <Chip label='已取消' color='error' size='small' />
                          ) : (
                            <Chip
                              label={selectedOrder.financial_status || '未知'}
                              color={getStatusColor(
                                selectedOrder.financial_status
                              )}
                              size='small'
                            />
                          )}
                        </Box>
                        <Box
                          sx={{
                            display: 'flex',
                            justifyContent: 'space-between',
                          }}
                        >
                          <Typography variant='body2' color='text.secondary'>
                            履行状态:
                          </Typography>
                          {selectedOrder.cancelled ? (
                            <Chip label='已取消' color='error' size='small' />
                          ) : (
                            <Chip
                              label={selectedOrder.fulfillment_status || '未知'}
                              color={getStatusColor(
                                selectedOrder.fulfillment_status
                              )}
                              size='small'
                            />
                          )}
                        </Box>
                        <Box
                          sx={{
                            display: 'flex',
                            justifyContent: 'space-between',
                          }}
                        >
                          <Typography variant='body2' color='text.secondary'>
                            创建时间:
                          </Typography>
                          <Typography variant='body2'>
                            {formatDate(selectedOrder.created_at)}
                          </Typography>
                        </Box>
                        <Box
                          sx={{
                            display: 'flex',
                            justifyContent: 'space-between',
                          }}
                        >
                          <Typography variant='body2' color='text.secondary'>
                            更新时间:
                          </Typography>
                          <Typography variant='body2'>
                            {formatDate(selectedOrder.updated_at)}
                          </Typography>
                        </Box>
                      </Stack>
                    </Box>

                    {/* 客户信息 */}
                    <Box sx={{ width: { xs: "100%", md: "50%" } }}>
                      <Typography variant='h6' gutterBottom>
                        客户信息
                      </Typography>
                      <Stack spacing={1}>
                        <Box
                          sx={{
                            display: 'flex',
                            justifyContent: 'space-between',
                          }}
                        >
                          <Typography variant='body2' color='text.secondary'>
                            姓名:
                          </Typography>
                          <Typography variant='body2'>
                            {selectedOrder.customer?.name || '未知'}
                          </Typography>
                        </Box>
                        <Box
                          sx={{
                            display: 'flex',
                            justifyContent: 'space-between',
                          }}
                        >
                          <Typography variant='body2' color='text.secondary'>
                            邮箱:
                          </Typography>
                          <Typography variant='body2'>
                            {selectedOrder.customer?.email ||
                              selectedOrder.email ||
                              '无'}
                          </Typography>
                        </Box>
                        {selectedOrder.phone && (
                          <Box
                            sx={{
                              display: 'flex',
                              justifyContent: 'space-between',
                            }}
                          >
                            <Typography variant='body2' color='text.secondary'>
                              电话:
                            </Typography>
                            <Typography variant='body2'>
                              {selectedOrder.phone}
                            </Typography>
                          </Box>
                        )}
                      </Stack>
                    </Box>

                    {/* 收货地址 */}
                    {selectedOrder.shipping_address && (
                      <Box sx={{ width: { xs: "100%", md: "50%" } }}>
                        <Typography variant='h6' gutterBottom>
                          收货地址
                        </Typography>
                        <Stack spacing={1}>
                          <Typography variant='body2'>
                            {selectedOrder.shipping_address.firstName}{' '}
                            {selectedOrder.shipping_address.lastName}
                          </Typography>
                          {selectedOrder.shipping_address.company && (
                            <Typography variant='body2'>
                              {selectedOrder.shipping_address.company}
                            </Typography>
                          )}
                          <Typography variant='body2'>
                            {selectedOrder.shipping_address.address1}
                          </Typography>
                          {selectedOrder.shipping_address.address2 && (
                            <Typography variant='body2'>
                              {selectedOrder.shipping_address.address2}
                            </Typography>
                          )}
                          <Typography variant='body2'>
                            {selectedOrder.shipping_address.city},{' '}
                            {selectedOrder.shipping_address.province}{' '}
                            {selectedOrder.shipping_address.zip}
                          </Typography>
                          <Typography variant='body2'>
                            {selectedOrder.shipping_address.country}
                          </Typography>
                          {selectedOrder.shipping_address.phone && (
                            <Typography variant='body2'>
                              电话: {selectedOrder.shipping_address.phone}
                            </Typography>
                          )}
                        </Stack>
                      </Box>
                    )}

                    {/* 账单地址 */}
                    {selectedOrder.billing_address && (
                      <Box sx={{ width: { xs: "100%", md: "50%" } }}>
                        <Typography variant='h6' gutterBottom>
                          账单地址
                        </Typography>
                        <Stack spacing={1}>
                          <Typography variant='body2'>
                            {selectedOrder.billing_address.firstName}{' '}
                            {selectedOrder.billing_address.lastName}
                          </Typography>
                          {selectedOrder.billing_address.company && (
                            <Typography variant='body2'>
                              {selectedOrder.billing_address.company}
                            </Typography>
                          )}
                          <Typography variant='body2'>
                            {selectedOrder.billing_address.address1}
                          </Typography>
                          {selectedOrder.billing_address.address2 && (
                            <Typography variant='body2'>
                              {selectedOrder.billing_address.address2}
                            </Typography>
                          )}
                          <Typography variant='body2'>
                            {selectedOrder.billing_address.city},{' '}
                            {selectedOrder.billing_address.province}{' '}
                            {selectedOrder.billing_address.zip}
                          </Typography>
                          <Typography variant='body2'>
                            {selectedOrder.billing_address.country}
                          </Typography>
                          {selectedOrder.billing_address.phone && (
                            <Typography variant='body2'>
                              电话: {selectedOrder.billing_address.phone}
                            </Typography>
                          )}
                        </Stack>
                      </Box>
                    )}

                    {/* 商品列表 */}
                    {selectedOrder.line_items &&
                      selectedOrder.line_items.length > 0 && (
                        <Box sx={{ width: "100%" }}>
                          <Typography variant='h6' gutterBottom>
                            商品列表
                          </Typography>
                          <TableContainer component={Paper} variant='outlined'>
                            <Table size='small'>
                              <TableHead>
                                <TableRow>
                                  <TableCell>商品名称</TableCell>
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
                                        <Typography variant='body2'>
                                          {item.title}
                                        </Typography>
                                        {item.variant?.title && (
                                          <Typography
                                            variant='caption'
                                            color='text.secondary'
                                          >
                                            {item.variant.title}
                                          </Typography>
                                        )}
                                      </TableCell>
                                      <TableCell align='right'>
                                        {item.quantity}
                                      </TableCell>
                                      <TableCell align='right'>
                                        {formatPrice(item.price, item.currency)}
                                      </TableCell>
                                      <TableCell align='right'>
                                        {formatPrice(
                                          (
                                            parseFloat(item.price) *
                                            item.quantity
                                          ).toString(),
                                          item.currency
                                        )}
                                      </TableCell>
                                    </TableRow>
                                  )
                                )}
                              </TableBody>
                            </Table>
                          </TableContainer>
                        </Box>
                      )}

                    {/* 履行信息 */}
                    {selectedOrder.fulfillments &&
                      selectedOrder.fulfillments.length > 0 && (
                        <Box sx={{ width: "100%" }}>
                          <Typography variant='h6' gutterBottom>
                            履行信息
                          </Typography>
                          <Stack spacing={2}>
                            {selectedOrder.fulfillments.map(
                              (fulfillment: any, index: number) => (
                                <Card key={index} variant='outlined'>
                                  <CardContent>
                                    <Typography variant='subtitle2'>
                                      履行 #{index + 1} - {fulfillment.status}
                                    </Typography>
                                    {fulfillment.trackingInfo && fulfillment.trackingInfo.length > 0 && (
                                      <Box sx={{ mt: 1 }}>
                                        {fulfillment.trackingInfo.map((tracking: any, trackingIndex: number) => (
                                          <Box key={trackingIndex}>
                                            <Typography variant='body2'>
                                              跟踪号:{' '}
                                              {tracking.number}
                                            </Typography>
                                            {tracking.company && (
                                              <Typography variant='body2'>
                                                承运商:{' '}
                                                {tracking.company}
                                              </Typography>
                                            )}
                                            {tracking.url && (
                                              <Typography variant='body2'>
                                                <a
                                                  href={tracking.url}
                                                  target='_blank'
                                                  rel='noopener noreferrer'
                                                >
                                                  跟踪链接
                                                </a>
                                              </Typography>
                                            )}
                                          </Box>
                                        ))}
                                      </Box>
                                    )}
                                  </CardContent>
                                </Card>
                              )
                            )}
                          </Stack>
                        </Box>
                      )}

                    {/* 退款信息 */}
                    {selectedOrder.refunds &&
                      selectedOrder.refunds.length > 0 && (
                        <Box sx={{ width: "100%" }}>
                          <Typography variant='h6' gutterBottom>
                            退款信息
                          </Typography>
                          <Stack spacing={2}>
                            {selectedOrder.refunds.map(
                              (refund: any, index: number) => (
                                <Card key={index} variant='outlined'>
                                  <CardContent>
                                    <Typography variant='subtitle2'>
                                      退款 #{index + 1}
                                    </Typography>
                                    <Typography variant='body2'>
                                      金额:{' '}
                                      {formatPrice(
                                        refund.totalRefundedSet?.shopMoney
                                          ?.amount || '0',
                                        refund.totalRefundedSet?.shopMoney
                                          ?.currencyCode || 'USD'
                                      )}
                                    </Typography>
                                    {refund.note && (
                                      <Typography variant='body2'>
                                        备注: {refund.note}
                                      </Typography>
                                    )}
                                    <Typography
                                      variant='caption'
                                      color='text.secondary'
                                    >
                                      {formatDate(refund.createdAt)}
                                    </Typography>
                                  </CardContent>
                                </Card>
                              )
                            )}
                          </Stack>
                        </Box>
                      )}
                  </Box>
                </Box>
              )}
            </DialogContent>
            <DialogActions>
              <Button
                variant='contained'
                color='primary'
                startIcon={<SyncIcon />}
                onClick={handleSaveToDatabase}
                disabled={!selectedOrder || savingToDatabase}
              >
                {savingToDatabase ? (
                  <CircularProgress size={20} />
                ) : (
                  '保存到数据库'
                )}
              </Button>
              <Button onClick={() => setDetailsOpen(false)}>关闭</Button>
            </DialogActions>
          </Dialog>

          {/* JSON 数据模态框 */}
          <Dialog
            open={jsonModalOpen}
            onClose={() => setJsonModalOpen(false)}
            maxWidth='lg'
            fullWidth
          >
            <DialogTitle>
              Shopify 订单完整 JSON 数据
              {selectedOrder && (
                <Typography variant='body2' color='text.secondary'>
                  {selectedOrder.name}
                </Typography>
              )}
            </DialogTitle>
            <DialogContent>
              {orderJson ? (
                <Box sx={{ mt: 2 }}>
                  <Typography variant='h6' gutterBottom>
                    订单 JSON 数据
                  </Typography>
                  <Paper
                    sx={{
                      p: 2,
                      backgroundColor: '#f5f5f5',
                      maxHeight: '60vh',
                      overflow: 'auto',
                      fontFamily: 'monospace',
                      fontSize: '0.875rem',
                    }}
                  >
                    <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
                      {JSON.stringify(orderJson, null, 2)}
                    </pre>
                  </Paper>
                </Box>
              ) : (
                <Box
                  sx={{
                    display: 'flex',
                    justifyContent: 'center',
                    alignItems: 'center',
                    minHeight: '200px',
                  }}
                >
                  <CircularProgress />
                </Box>
              )}
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setJsonModalOpen(false)}>关闭</Button>
              {orderJson && (
                <Button
                  onClick={() => {
                    navigator.clipboard.writeText(
                      JSON.stringify(orderJson, null, 2)
                    );
                    // 这里可以添加一个提示，表示已复制到剪贴板
                  }}
                  variant='outlined'
                >
                  复制到剪贴板
                </Button>
              )}
            </DialogActions>
          </Dialog>
        </Box>
      </DashboardLayout>
    </ProtectedRoute>
  );
};

export default ShopifyOrdersPage;
