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
  IconButton,
  Tooltip,
  Alert,
  CircularProgress,
  Pagination,
  Stack,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Checkbox,
  Collapse,
  Autocomplete,
  Link,
} from '@mui/material';
import {
  Search as SearchIcon,
  Refresh as RefreshIcon,
  Visibility as ViewIcon,
  FilterList as FilterIcon,
  Sync as SyncIcon,
  ArrowUpward as ArrowUpwardIcon,
  ArrowDownward as ArrowDownwardIcon,
  Delete as DeleteIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  LinkOff as LinkOffIcon,
  Clear as ClearIcon,
  OpenInNew as OpenInNewIcon,
} from '@mui/icons-material';
import { useRouter, useSearchParams } from 'next/navigation';
import { Order, OrderStatus } from '@/types/order';
import { frontendApi } from '@/lib/api';

const ITEMS_PER_PAGE = 20; // 每页显示20个订单

/** 商品选项，用于订单列表「按商品筛选」下拉 */
interface ProductOption {
  id_hashid: string;
  title: string;
}

const getAddressValidationDisplay = (
  status: Order['address_validation_status'],
  reasonCode?: string
) => {
  if (!status || status === 'not_checked') {
    return {
      label: '未校验',
      color: 'default' as const,
      tooltip: '此订单的地址尚未进行自动校验',
    };
  }

  switch (status) {
    case 'valid':
      return {
        label: '地址正常',
        color: 'success' as const,
        tooltip: '地址通过基础规则校验',
      };
    case 'invalid':
      return {
        label: '地址有问题',
        color: 'error' as const,
        tooltip:
          '系统判断该地址存在明显问题，请在发货前人工确认（原因: ' +
          (reasonCode || '请查看详情') +
          '）',
      };
    case 'suspicious':
      return {
        label: '地址需确认',
        color: 'warning' as const,
        tooltip:
          '系统检测到地址存在潜在风险，建议在发货前确认（原因: ' +
          (reasonCode || '请查看详情') +
          '）',
      };
    case 'failed':
      return {
        label: '校验失败',
        color: 'info' as const,
        tooltip:
          '地址校验服务暂时失败，可能是系统或网络问题，并不代表地址本身有问题',
      };
    default:
      return {
        label: status,
        color: 'default' as const,
        tooltip: '地址校验状态: ' + status,
      };
  }
};

export function OrdersList() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const productFromUrl = searchParams.get('product') ?? '';
  const searchFromUrl = searchParams.get('search') ?? '';
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState(() => searchFromUrl || '');
  const [productFilter, setProductFilter] = useState(productFromUrl);
  const [productFilterLabel, setProductFilterLabel] = useState<string>('');
  const [productOptions, setProductOptions] = useState<ProductOption[]>([]);
  const [loadingProductOptions, setLoadingProductOptions] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCount, setTotalCount] = useState(0);

  // 删除相关状态
  const [selectedOrders, setSelectedOrders] = useState<Set<string>>(new Set());
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deletingOrders, setDeletingOrders] = useState<Set<string>>(new Set());
  const [bulkDeleting, setBulkDeleting] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState<string | null>(null);
  const [updateFeedback, setUpdateFeedback] = useState<{ message: string; severity: 'success' | 'info' | 'error' } | null>(null);
  const [bulkUpdating, setBulkUpdating] = useState(false);
  const [updateDialogOpen, setUpdateDialogOpen] = useState(false);
  const [sortBy, setSortBy] = useState<'created_at' | 'order_date'>(
    'created_at'
  );
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  
  // SCM 订单展开/收起相关状态
  const [expandedOrders, setExpandedOrders] = useState<Set<string>>(new Set());
  const [scmOrdersMap, setScmOrdersMap] = useState<Map<string, any[]>>(new Map());
  const [loadingScmOrders, setLoadingScmOrders] = useState<Set<string>>(new Set());
  const [unbindingOrderId, setUnbindingOrderId] = useState<string | null>(null);

  const fetchOrders = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await frontendApi.get('/api/orders', {
        params: {
          page: currentPage,
          limit: ITEMS_PER_PAGE,
          search: searchTerm || undefined,
          sort_by: sortBy,
          sort_order: sortOrder,
          ...(productFilter ? { product: productFilter } : {}),
        },
      });

      console.log('🔍 前端接收到的订单数据:', {
        orders: response.data.orders?.length || 0,
        total: response.data.total,
        total_pages: response.data.total_pages,
        current_page: response.data.current_page,
        fullResponse: response.data,
      });

      setOrders(response.data.orders || []);
      setTotalPages(response.data.total_pages || 1);
      setTotalCount(response.data.total || 0);
    } catch (err: any) {
      console.error('Failed to fetch orders:', err);
      setError(err.response?.data?.detail || 'Failed to fetch orders');
    } finally {
      setLoading(false);
    }
  }, [currentPage, searchTerm, sortBy, sortOrder, productFilter]);

  // 从 URL 同步商品筛选（例如从商品管理「前往订单管理」跳转带入）
  useEffect(() => {
    const p = searchParams.get('product') ?? '';
    if (p !== productFilter) {
      setProductFilter(p);
      if (!p) setProductFilterLabel('');
    }
  }, [searchParams]);

  // 从 URL 同步搜索关键词（例如从同步订单页「核心订单」跳转带入订单号筛选）
  useEffect(() => {
    const q = searchParams.get('search') ?? '';
    if (q !== searchTerm) setSearchTerm(q);
  }, [searchParams]);

  // 当 URL 带入商品 hashid 时，拉取该商品标题用于展示（人类可读）
  useEffect(() => {
    if (!productFilter) return;
    const found = productOptions.find((o) => o.id_hashid === productFilter);
    if (found) {
      setProductFilterLabel(found.title);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const res = await frontendApi.get<{ title?: string }>(
          `/api/products/${productFilter}`
        );
        if (!cancelled && res.data?.title) setProductFilterLabel(res.data.title);
      } catch {
        if (!cancelled) setProductFilterLabel('');
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [productFilter, productOptions]);

  // 拉取商品列表，供「按商品筛选」下拉选择（只取 id_hashid + title）
  const fetchProductOptions = useCallback(async () => {
    setLoadingProductOptions(true);
    try {
      const res = await frontendApi.get<{
        products?: { id_hashid: string; title: string }[];
      }>('/api/products', { params: { limit: 200, page: 1 } });
      const list = res.data?.products ?? [];
      setProductOptions(
        list.map((p) => ({ id_hashid: p.id_hashid, title: p.title || p.id_hashid }))
      );
    } catch (e) {
      console.error('Failed to fetch product options for order filter:', e);
    } finally {
      setLoadingProductOptions(false);
    }
  }, []);

  useEffect(() => {
    fetchOrders();
  }, [fetchOrders]);

  const handleSearch = (event: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(event.target.value);
    setCurrentPage(1); // 搜索时重置到第一页
  };

  const handleProductFilterChange = (
    _event: React.SyntheticEvent,
    value: ProductOption | null
  ) => {
    if (!value) {
      setProductFilter('');
      setProductFilterLabel('');
      setCurrentPage(1);
      router.replace('/orders');
      return;
    }
    setProductFilter(value.id_hashid);
    setProductFilterLabel(value.title);
    setCurrentPage(1);
    router.replace(`/orders?product=${encodeURIComponent(value.id_hashid)}`);
  };

  const handleClearProductFilter = () => {
    setProductFilter('');
    setProductFilterLabel('');
    setCurrentPage(1);
    router.replace('/orders');
  };

  const handleRefresh = () => {
    fetchOrders();
  };

  const handlePageChange = (
    event: React.ChangeEvent<unknown>,
    page: number
  ) => {
    setCurrentPage(page);
  };

  const handleSort = (field: 'created_at' | 'order_date') => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(field);
      setSortOrder('desc'); // 默认降序
    }
    setCurrentPage(1); // 排序时重置到第一页
  };

  // 批量更新 Shopify 订单状态
  const handleBulkUpdateShopifyStatus = () => {
    if (selectedOrders.size === 0) {
      setError('请先选择要更新的订单');
      return;
    }
    setUpdateDialogOpen(true);
  };

  const handleConfirmUpdate = async () => {
    try {
      setBulkUpdating(true);
      setError(null);
      setUpdateFeedback(null);

      const response = await frontendApi.post('/api/orders/batch-update-shopify-status', {
        order_ids: Array.from(selectedOrders)
      });

      console.log('✅ 批量更新 Shopify 订单状态成功:', response.data);

      const results = response.data.results || { success: [], failed: [] };
      const successCount = results.success?.length || 0;
      const failedCount = results.failed?.length || 0;

      let message = `Shopify 订单状态更新: ${successCount} 个成功`;
      if (failedCount > 0) {
        message += `, ${failedCount} 个失败`;
        const failedReasons = (results.failed || [])
          .map((f: { order_id?: number; error?: string }) => `${f.order_id || ''}: ${f.error || '未知错误'}`)
          .join('；');
        if (failedReasons) message += `。失败原因: ${failedReasons}`;
      }

      const severity = failedCount > 0 ? 'error' : 'success';
      setUpdateFeedback({ message, severity });
      setSelectedOrders(new Set());
      setUpdateDialogOpen(false);
      await fetchOrders();
    } catch (error: any) {
      console.error('❌ 批量更新 Shopify 订单状态失败:', error);
      setUpdateFeedback(null);
      setError(error.response?.data?.detail || '批量更新失败');
    } finally {
      setBulkUpdating(false);
    }
  };

  const handleViewOrder = (orderId: string) => {
    if (!orderId) return;
    router.push(`/orders/${orderId}`);
  };

  // 删除相关函数
  const handleSelectOrder = (orderId: string, checked: boolean) => {
    setSelectedOrders(prev => {
      const newSet = new Set(prev);
      if (checked) {
        newSet.add(orderId);
      } else {
        newSet.delete(orderId);
      }
      return newSet;
    });
  };

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedOrders(new Set(orders.map(order => order.id_hashid)));
    } else {
      setSelectedOrders(new Set());
    }
  };

  const handleUnbindOrder = async (orderId: string) => {
    try {
      setUnbindingOrderId(orderId);
      setError(null);
      await frontendApi.post(`/api/orders/${orderId}/unbind-external`);
      await fetchOrders();
    } catch (err: any) {
      console.error('❌ 解除订单外部映射失败:', err);
      setError(
        err.response?.data?.detail || err.message || '解除映射失败'
      );
    } finally {
      setUnbindingOrderId(null);
    }
  };

  const hasExternalMapping = (order: Order) =>
    !!(order.shopify_order_id || order.external_order_id);

  const handleDeleteOrder = async (orderId: string) => {
    try {
      setDeletingOrders(prev => new Set(prev).add(orderId));

      const response = await frontendApi.delete(`/api/orders/${orderId}`);

      if (response.data.success) {
        // 删除成功后刷新列表
        fetchOrders();
        setError(null);
      } else {
        setError(`删除失败：${response.data.message || '未知错误'}`);
      }
    } catch (error: any) {
      console.error('❌ 删除订单失败:', error);
      setError(
        `删除失败：${error.response?.data?.detail || error.message || '网络错误'}`
      );
    } finally {
      setDeletingOrders(prev => {
        const newSet = new Set(prev);
        newSet.delete(orderId);
        return newSet;
      });
    }
  };

  const handleBulkDelete = async () => {
    if (selectedOrders.size === 0) {
      setError('请先选择要删除的订单');
      return;
    }

    setBulkDeleting(true);

    try {
      const deletePromises = Array.from(selectedOrders).map(async orderId => {
        try {
          const response = await frontendApi.delete(`/api/orders/${orderId}`);
          return { orderId, success: response.data.success, error: undefined };
        } catch (error: any) {
          return {
            orderId,
            success: false,
            error: error.response?.data?.detail || error.message,
          };
        }
      });

      const results = await Promise.all(deletePromises);
      const successful = results.filter(r => r.success).length;
      const failed = results.filter(r => !r.success).length;

      if (successful > 0) {
        fetchOrders();
        setSelectedOrders(new Set());
        setDeleteDialogOpen(false);
      }

      if (failed > 0) {
        const failedReasons = results
          .filter(r => !r.success && r.error)
          .map(r => r.error)
          .filter(Boolean);
        const msg =
          failedReasons.length > 0
            ? `批量删除完成：成功 ${successful} 个，失败 ${failed} 个。失败原因：${failedReasons.slice(0, 3).join('；')}`
            : `批量删除完成：成功 ${successful} 个，失败 ${failed} 个`;
        setError(msg);
      }
    } catch (error: any) {
      console.error('❌ 批量删除失败:', error);
      setError(`批量删除失败：${error.message || '网络错误'}`);
    } finally {
      setBulkDeleting(false);
    }
  };

  const handleConfirmDelete = () => {
    if (selectedOrders.size === 0) {
      setError('请先选择要删除的订单');
      return;
    }
    setDeleteDialogOpen(true);
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

  const getFulfillmentStatusColor = (
    fulfillmentStatus: string | null | undefined
  ) => {
    if (!fulfillmentStatus) return 'default';

    switch (fulfillmentStatus.toLowerCase()) {
      case 'fulfilled':
        return 'success';
      case 'partial':
        return 'warning';
      case 'unfulfilled':
        return 'default';
      case 'cancelled':
        return 'error';
      case 'in_progress':
        return 'info';
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

  // 获取订单的 SCM 订单
  const fetchScmOrders = useCallback(async (orderIdHashid: string) => {
    // 如果已经加载过，直接返回
    if (scmOrdersMap.has(orderIdHashid)) {
      return;
    }

    try {
      setLoadingScmOrders(prev => new Set(prev).add(orderIdHashid));
      
      // 调用后端 API 获取 SCM 订单
      // 注意：后端 API 使用的是 order_id (整数)，但我们需要先解码 hashid
      // 实际上，我们可以直接使用 hashid，让后端处理解码
      const response = await frontendApi.get(`/api/scm-orders/order/${orderIdHashid}`);
      
      const scmOrders = response.data || [];
      setScmOrdersMap(prev => {
        const newMap = new Map(prev);
        newMap.set(orderIdHashid, scmOrders);
        return newMap;
      });
    } catch (err: any) {
      console.error(`Failed to fetch SCM orders for order ${orderIdHashid}:`, err);
      // 如果获取失败，设置为空数组（可能是没有 SCM 订单）
      setScmOrdersMap(prev => {
        const newMap = new Map(prev);
        newMap.set(orderIdHashid, []);
        return newMap;
      });
    } finally {
      setLoadingScmOrders(prev => {
        const newSet = new Set(prev);
        newSet.delete(orderIdHashid);
        return newSet;
      });
    }
  }, [scmOrdersMap]);

  // 切换订单展开/收起
  const handleToggleExpand = useCallback(async (orderIdHashid: string) => {
    const isExpanded = expandedOrders.has(orderIdHashid);
    
    if (isExpanded) {
      // 收起
      setExpandedOrders(prev => {
        const newSet = new Set(prev);
        newSet.delete(orderIdHashid);
        return newSet;
      });
    } else {
      // 展开 - 先加载 SCM 订单
      setExpandedOrders(prev => new Set(prev).add(orderIdHashid));
      await fetchScmOrders(orderIdHashid);
    }
  }, [expandedOrders, fetchScmOrders]);

  // 检查订单是否有 SCM 订单
  const hasScmOrders = useCallback((order: Order) => {
    // 优先使用订单数据中的 scm_orders_count 字段（从后端 API 返回）
    if (order.scm_orders_count !== undefined) {
      return order.scm_orders_count > 0;
    }
    // 如果已经加载过，检查是否有数据
    if (scmOrdersMap.has(order.id_hashid)) {
      const scmOrders = scmOrdersMap.get(order.id_hashid);
      return scmOrders && scmOrders.length > 0;
    }
    // 如果正在加载，显示箭头（允许查看）
    if (loadingScmOrders.has(order.id_hashid)) {
      return true;
    }
    // 如果从未加载过，默认不显示箭头（符合用户要求：如果没有就不显示箭头）
    return false;
  }, [scmOrdersMap, loadingScmOrders]);

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
        <Box display='flex' gap={2}>
          <Button
            variant='outlined'
            startIcon={<RefreshIcon />}
            onClick={handleRefresh}
            disabled={loading}
          >
            刷新
          </Button>
        </Box>
      </Box>

      {error && (
        <Alert severity='error' sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {updateFeedback && (
        <Alert
          severity={updateFeedback.severity}
          sx={{ mb: 2 }}
          onClose={() => setUpdateFeedback(null)}
        >
          {updateFeedback.message}
        </Alert>
      )}

      {syncMessage && (
        <Alert
          severity={
            syncMessage.includes('✅')
              ? 'success'
              : syncMessage.includes('⚠️')
                ? 'warning'
                : 'info'
          }
          sx={{ mb: 2 }}
        >
          {syncMessage}
        </Alert>
      )}

      <Card>
        <CardContent>
          <Box display='flex' flexDirection='column' gap={2} mb={3}>
            <Box display='flex' gap={2} alignItems='center' flexWrap='wrap'>
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
            {/* 筛选条件：可扩展，当前支持「按商品」等 */}
            <Box display='flex' gap={2} alignItems='center' flexWrap='wrap'>
              <Typography variant='body2' color='text.secondary' sx={{ minWidth: 56 }}>
                筛选条件
              </Typography>
              <Autocomplete
                size='small'
                options={productOptions}
                getOptionLabel={(opt) => opt.title}
                value={
                  productFilter
                    ? productOptions.find((o) => o.id_hashid === productFilter) ?? {
                        id_hashid: productFilter,
                        title: productFilterLabel || productFilter,
                      }
                    : null
                }
                onChange={handleProductFilterChange}
                onOpen={() => fetchProductOptions()}
                loading={loadingProductOptions}
                sx={{ minWidth: 280 }}
                renderInput={(params) => (
                  <TextField
                    {...params}
                    placeholder='按商品筛选（从列表选择）'
                    label='商品'
                  />
                )}
                isOptionEqualToValue={(opt, val) => opt.id_hashid === val.id_hashid}
              />
              {productFilter ? (
                <Chip
                  label={
                    productFilterLabel
                      ? `仅显示包含「${productFilterLabel}」的订单`
                      : '仅显示包含该商品的订单'
                  }
                  size='small'
                  onDelete={handleClearProductFilter}
                  color='primary'
                  variant='outlined'
                />
              ) : null}
            </Box>
          </Box>

          {/* 批量操作区域 */}
          {selectedOrders.size > 0 && (
            <Box sx={{ mb: 2, display: 'flex', gap: 1, alignItems: 'center' }}>
              <Button
                variant='contained'
                color='primary'
                startIcon={
                  bulkUpdating ? <CircularProgress size={16} /> : <SyncIcon />
                }
                onClick={handleBulkUpdateShopifyStatus}
                disabled={bulkUpdating}
              >
                {bulkUpdating ? '更新中...' : '同步更新 Shopify 订单状态'}
              </Button>
              <Button
                variant='contained'
                color='error'
                startIcon={
                  bulkDeleting ? <CircularProgress size={16} /> : <DeleteIcon />
                }
                onClick={handleConfirmDelete}
                disabled={bulkDeleting}
              >
                {bulkDeleting
                  ? '删除中...'
                  : `删除订单 (${selectedOrders.size})`}
              </Button>
              <Button
                variant='outlined'
                onClick={() => setSelectedOrders(new Set())}
              >
                取消选择
              </Button>
              <Typography variant='body2' color='text.secondary'>
                已选择 {selectedOrders.size} 个订单
              </Typography>
            </Box>
          )}

          <TableContainer component={Paper} variant='outlined'>
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
                  <TableCell width={50}></TableCell>
                  <TableCell>订单ID</TableCell>
                  <TableCell>Shopify订单号</TableCell>
                  <TableCell>SCM / Printify</TableCell>
                  <TableCell>客户</TableCell>
                  <TableCell>金额</TableCell>
                  <TableCell>状态</TableCell>
                  <TableCell>履约状态</TableCell>
                  <TableCell>地址</TableCell>
                  <TableCell>
                    <Box display='flex' alignItems='center' gap={1}>
                      订单日期
                      <IconButton
                        size='small'
                        onClick={() => handleSort('order_date')}
                        color={sortBy === 'order_date' ? 'primary' : 'default'}
                      >
                        {sortBy === 'order_date' && sortOrder === 'desc' ? (
                          <ArrowDownwardIcon fontSize='small' />
                        ) : (
                          <ArrowUpwardIcon fontSize='small' />
                        )}
                      </IconButton>
                    </Box>
                  </TableCell>
                  <TableCell>操作</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {orders.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={10} align='center'>
                      <Typography variant='body2' color='text.secondary'>
                        {searchTerm || productFilter
                          ? '没有找到匹配的订单'
                          : '暂无订单数据'}
                      </Typography>
                    </TableCell>
                  </TableRow>
                ) : (
                  orders.map(order => {
                    const isExpanded = expandedOrders.has(order.id_hashid);
                    const scmOrders = scmOrdersMap.get(order.id_hashid) || [];
                    const isLoadingScm = loadingScmOrders.has(order.id_hashid);
                    // 检查是否有 SCM 订单（使用订单对象，可以访问 scm_orders_count）
                    const hasScm = hasScmOrders(order);
                    
                    return (
                      <React.Fragment key={order.id_hashid}>
                        <TableRow hover>
                          <TableCell padding='checkbox'>
                            <Checkbox
                              checked={selectedOrders.has(order.id_hashid)}
                              onChange={e =>
                                handleSelectOrder(order.id_hashid, e.target.checked)
                              }
                            />
                          </TableCell>
                          <TableCell>
                            {hasScm && (
                              <IconButton
                                size='small'
                                onClick={() => handleToggleExpand(order.id_hashid)}
                                disabled={isLoadingScm}
                              >
                                {isLoadingScm ? (
                                  <CircularProgress size={16} />
                                ) : isExpanded ? (
                                  <ExpandLessIcon />
                                ) : (
                                  <ExpandMoreIcon />
                                )}
                              </IconButton>
                            )}
                          </TableCell>
                          <TableCell>
                            <Typography variant='body2' fontWeight='medium'>
                              {order.order_number || order.id_hashid}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Typography variant='body2'>
                              {order.external_order_name || order.external_order_number || order.external_order_id || '—'}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            {order.scm_orders_preview && order.scm_orders_preview.length > 0 ? (
                              <Stack spacing={0.5}>
                                {order.scm_orders_preview.slice(0, 2).map((scm: any) => (
                                  <Link
                                    key={scm.id_hashid}
                                    component="button"
                                    variant="body2"
                                    sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.5, textAlign: 'left' }}
                                    onClick={() => router.push(`/scm-orders/${scm.id_hashid}`)}
                                  >
                                    {scm.scm_order_number || scm.id_hashid}
                                  </Link>
                                ))}
                                {(() => {
                                  const withPrintify = order.scm_orders_preview?.find((s: any) => s.printify_order_id && s.printify_shop_id);
                                  const printifyUrl = withPrintify
                                    ? `https://printify.com/app/store/${withPrintify.printify_shop_id}/order/${withPrintify.printify_order_id}`
                                    : null;
                                  return printifyUrl ? (
                                    <Link
                                      href={printifyUrl}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      variant="body2"
                                      sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.5 }}
                                    >
                                      Printify 订单
                                      <OpenInNewIcon sx={{ fontSize: 14 }} />
                                    </Link>
                                  ) : null;
                                })()}
                              </Stack>
                            ) : (
                              <Typography variant='body2' color='text.secondary'>—</Typography>
                            )}
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
                            <Chip
                              label={order.fulfillment_status || 'unfulfilled'}
                              color={getFulfillmentStatusColor(
                                order.fulfillment_status
                              )}
                              size='small'
                            />
                          </TableCell>
                          <TableCell>
                            {(() => {
                              const {
                                label,
                                color,
                                tooltip,
                              } = getAddressValidationDisplay(
                                order.address_validation_status,
                                order.address_validation_reason_code
                              );
                              return (
                                <Tooltip title={tooltip}>
                                  <Chip label={label} color={color as any} size='small' />
                                </Tooltip>
                              );
                            })()}
                          </TableCell>
                          <TableCell>
                            <Typography variant='body2'>
                              {formatDate(order.order_date)}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Box display='flex' gap={1}>
                              <Tooltip title='查看详情'>
                                <IconButton
                                  size='small'
                                  onClick={() => handleViewOrder(order.id_hashid)}
                                >
                                  <ViewIcon />
                                </IconButton>
                              </Tooltip>
                              {hasExternalMapping(order) && (
                                <Tooltip title='解除与外部订单的映射后可删除'>
                                  <IconButton
                                    size='small'
                                    color='primary'
                                    onClick={() => handleUnbindOrder(order.id_hashid)}
                                    disabled={unbindingOrderId === order.id_hashid}
                                  >
                                    {unbindingOrderId === order.id_hashid ? (
                                      <CircularProgress size={16} />
                                    ) : (
                                      <LinkOffIcon />
                                    )}
                                  </IconButton>
                                </Tooltip>
                              )}
                              <Tooltip title='删除订单'>
                                <IconButton
                                  size='small'
                                  color='error'
                                  onClick={() => handleDeleteOrder(order.id_hashid)}
                                  disabled={deletingOrders.has(order.id_hashid)}
                                >
                                  {deletingOrders.has(order.id_hashid) ? (
                                    <CircularProgress size={16} />
                                  ) : (
                                    <DeleteIcon />
                                  )}
                                </IconButton>
                              </Tooltip>
                            </Box>
                          </TableCell>
                        </TableRow>
                        {/* SCM 订单展开行 */}
                        <TableRow>
                          <TableCell colSpan={12} style={{ paddingBottom: 0, paddingTop: 0, paddingLeft: 0, paddingRight: 0 }}>
                            <Collapse in={isExpanded} timeout='auto' unmountOnExit>
                              <Box sx={{ py: 1 }}>
                                {isLoadingScm ? (
                                  <Box display='flex' justifyContent='center' p={2}>
                                    <CircularProgress size={24} />
                                  </Box>
                                ) : scmOrders.length === 0 ? (
                                  <Typography variant='body2' color='text.secondary' align='center' p={2}>
                                    该订单没有关联的 SCM 订单
                                  </Typography>
                                ) : (
                                  <TableContainer component={Paper} variant='outlined' sx={{ backgroundColor: 'grey.50', borderRadius: 0 }}>
                                    <Table size='small'>
                                      <TableHead>
                                        <TableRow sx={{ backgroundColor: 'grey.400' }}>
                                          <TableCell>SCM订单编号</TableCell>
                                          <TableCell>状态</TableCell>
                                          <TableCell>履约状态</TableCell>
                                          <TableCell>目标系统</TableCell>
                                          <TableCell>客户</TableCell>
                                          <TableCell>创建时间</TableCell>
                                          <TableCell>操作</TableCell>
                                        </TableRow>
                                      </TableHead>
                                      <TableBody>
                                        {scmOrders.map((scmOrder: any) => (
                                          <TableRow key={scmOrder.id_hashid} hover sx={{ backgroundColor: 'grey.300' }}>
                                            <TableCell>
                                              <Typography variant='body2' fontWeight='medium'>
                                                {scmOrder.scm_order_number || scmOrder.id_hashid}
                                              </Typography>
                                            </TableCell>
                                            <TableCell>
                                              <Chip
                                                label={scmOrder.status || 'N/A'}
                                                size='small'
                                                color={
                                                  scmOrder.status === 'fulfilled'
                                                    ? 'success'
                                                    : scmOrder.status === 'failed'
                                                    ? 'error'
                                                    : 'default'
                                                }
                                              />
                                            </TableCell>
                                            <TableCell>
                                              <Chip
                                                label={scmOrder.fulfillment_status || 'unfulfilled'}
                                                size='small'
                                                color={
                                                  scmOrder.fulfillment_status === 'fulfilled'
                                                    ? 'success'
                                                    : 'default'
                                                }
                                              />
                                            </TableCell>
                                            <TableCell>
                                              <Typography variant='body2'>
                                                {scmOrder.routing_metadata?.target_system_type || 'N/A'}
                                              </Typography>
                                            </TableCell>
                                            <TableCell>
                                              <Box>
                                                <Typography variant='body2' fontWeight='medium'>
                                                  {scmOrder.customer_name || '未知客户'}
                                                </Typography>
                                                <Typography variant='caption' color='text.secondary'>
                                                  {scmOrder.customer_email}
                                                </Typography>
                                              </Box>
                                            </TableCell>
                                            <TableCell>
                                              <Typography variant='body2'>
                                                {scmOrder.created_at
                                                  ? formatDate(scmOrder.created_at)
                                                  : 'N/A'}
                                              </Typography>
                                            </TableCell>
                                            <TableCell>
                                              <Tooltip title='查看SCM订单详情'>
                                                <IconButton
                                                  size='small'
                                                  onClick={() =>
                                                    router.push(`/scm-orders/${scmOrder.id_hashid}`)
                                                  }
                                                >
                                                  <ViewIcon fontSize='small' />
                                                </IconButton>
                                              </Tooltip>
                                            </TableCell>
                                          </TableRow>
                                        ))}
                                      </TableBody>
                                    </Table>
                                  </TableContainer>
                                )}
                              </Box>
                            </Collapse>
                          </TableCell>
                        </TableRow>
                      </React.Fragment>
                    );
                  })
                )}
              </TableBody>
            </Table>
          </TableContainer>

          {/* 分页组件 */}
          <Box display='flex' justifyContent='center' mt={3}>
            <Stack spacing={2}>
              <Pagination
                count={totalPages}
                page={currentPage}
                onChange={handlePageChange}
                color='primary'
                showFirstButton
                showLastButton
              />
              <Typography
                variant='body2'
                color='text.secondary'
                textAlign='center'
              >
                共 {totalCount} 个订单，第 {currentPage} 页，共 {totalPages} 页
              </Typography>
            </Stack>
          </Box>
        </CardContent>
      </Card>

      {/* 更新 Shopify 订单状态确认对话框 */}
      <Dialog
        open={updateDialogOpen}
        onClose={() => setUpdateDialogOpen(false)}
        maxWidth='sm'
        fullWidth
      >
        <DialogTitle>
          确认同步更新 Shopify 订单状态
        </DialogTitle>
        <DialogContent>
          <Typography variant='body1' gutterBottom>
            您确定要同步更新选中的 {selectedOrders.size} 个订单的 Shopify 状态吗？
          </Typography>
          <Typography variant='body2' color='text.secondary'>
            此操作将从 Shopify 获取最新的履行信息并更新到核心订单中。
          </Typography>
          <Box sx={{ mt: 2 }}>
            <Typography variant='subtitle2' gutterBottom>
              将要更新的订单：
            </Typography>
            <Box sx={{ maxHeight: '200px', overflow: 'auto' }}>
              {Array.from(selectedOrders).map(orderId => {
                const order = orders.find(o => o.id_hashid === orderId);
                return order ? (
                  <Typography key={orderId} variant='body2' color='text.secondary'>
                    • {order.order_number || order.id_hashid} - {order.external_order_name || order.external_order_id}
                  </Typography>
                ) : null;
              })}
            </Box>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setUpdateDialogOpen(false)}>
            取消
          </Button>
          <Button
            variant='contained'
            color='primary'
            startIcon={bulkUpdating ? <CircularProgress size={16} /> : <SyncIcon />}
            onClick={handleConfirmUpdate}
            disabled={bulkUpdating}
          >
            {bulkUpdating ? '更新中...' : '确认更新'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* 删除确认对话框 */}
      <Dialog
        open={deleteDialogOpen}
        onClose={() => setDeleteDialogOpen(false)}
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
                const order = orders.find(o => o.id_hashid === orderId);
                return order ? (
                  <Typography
                    key={orderId}
                    variant='body2'
                    color='text.secondary'
                  >
                    • {order.order_number || order.id_hashid} -{' '}
                    {order.external_order_name || order.external_order_id}
                  </Typography>
                ) : null;
              })}
            </Box>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)}>取消</Button>
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
  );
}
