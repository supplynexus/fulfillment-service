'use client';

import {
  Search as SearchIcon,
  Refresh as RefreshIcon,
  Visibility as ViewIcon,
  Inventory as InventoryIcon,
  FilterList as FilterIcon,
  Link as LinkIcon,
  Sync as SyncIcon,
  OpenInNew as OpenInNewIcon,
  DataObject as DataObjectIcon,
  CompareArrows as CompareArrowsIcon,
  ChevronLeft as ChevronLeftIcon,
  ChevronRight as ChevronRightIcon,
  Article as ArticleIcon,
} from '@mui/icons-material';
import {
  Box,
  Typography,
  Card,
  CardContent,
  CardMedia,
  Chip,
  Button,
  Alert,
  CircularProgress,
  LinearProgress,
  Pagination,
  FormControl,
  Select,
  MenuItem,
  TextField,
  InputAdornment,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Checkbox,
} from '@mui/material';
import DOMPurify from 'dompurify';
import useEmblaCarousel from 'embla-carousel-react';
import React, { useState, useEffect, useCallback } from 'react';
import toast from 'react-hot-toast';

import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { JsonViewerDialog } from '@/components/common/JsonViewerDialog';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { ProductMappingDialog } from '@/components/printify/ProductMappingDialog';
import { frontendApi } from '@/lib/api';
import { frontendLogger } from '@/lib/frontend-logger';

const TOAST_SYNC_ID = 'printify-batch-sync';

interface PrintifyProduct {
  id: string;
  title: string;
  description?: string;
  tags: string[];
  options: Array<{
    name: string;
    type: string;
    values: Array<{
      id: number;
      title: string;
    }>;
  }>;
  variants: Array<{
    id: number;
    sku: string;
    cost: number;
    price: number;
    title: string;
    grams: number;
    is_enabled: boolean;
    is_default: boolean;
    is_available: boolean;
    options: number[];
  }>;
  images: Array<{
    src: string;
    variant_ids: number[];
    position: string;
    is_default: boolean;
  }>;
  created_at: string;
  updated_at: string;
  visible: boolean;
  is_locked: boolean;
  /** 是否已发布到销售渠道（与 Printify 后台 Published 一致），用于筛选 */
  is_published?: boolean;
  external: {
    id: string;
    handle: string;
    sku: string;
  };
  user_id: number;
  shop_id: number;
  print_provider_id: number;
  print_areas: Array<{
    variant_ids: number[];
    placeholders: Array<{
      position: string;
      images: Array<{
        id: string;
        name: string;
        type: string;
        url: string;
        position: string;
        x: number;
        y: number;
        scale: number;
        angle: number;
      }>;
    }>;
  }>;
}

interface PrintifyStore {
  id_hashid: string;
  name: string;
  system_type: string;
  external_id?: string;
  is_active: boolean;
}

type SyncStatus = 'in_sync' | 'different' | 'not_synced';

interface CompareWithLocalResult {
  success: boolean;
  is_in_sync: boolean;
  remote?: {
    updated_at?: string;
    visible?: boolean;
    sales_channel_properties?: unknown;
  };
  local?: {
    exists: boolean;
    updated_at?: string;
    last_synced_at?: string;
    raw_data_updated_at?: string;
    is_published?: boolean;
    visible?: boolean;
    sync_status?: string;
  };
}

function PrintifyProductsPage() {
  const [products, setProducts] = useState<PrintifyProduct[]>([]);
  const [stores, setStores] = useState<PrintifyStore[]>([]);
  const [selectedStore, setSelectedStore] = useState<PrintifyStore | null>(
    null
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [searchInput, setSearchInput] = useState('');
  /** 发布状态筛选: 'all' | 'published' | 'unpublished' */
  const [publishedFilter, setPublishedFilter] = useState<
    'all' | 'published' | 'unpublished'
  >('all');
  const [syncStatusFilter, setSyncStatusFilter] = useState<'all' | SyncStatus>(
    'all'
  );
  const [filteredProducts, setFilteredProducts] = useState<PrintifyProduct[]>(
    []
  );
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [serverTotalPages, setServerTotalPages] = useState(1);
  const [serverTotalCount, setServerTotalCount] = useState(0);
  const [syncStatusMap, setSyncStatusMap] = useState<
    Record<string, SyncStatus>
  >({});
  const [selectedProduct, setSelectedProduct] =
    useState<PrintifyProduct | null>(null);
  const [openProductDialog, setOpenProductDialog] = useState(false);
  const [openMappingDialog, setOpenMappingDialog] = useState(false);
  const [openJsonDialog, setOpenJsonDialog] = useState(false);
  const [openHtmlDialog, setOpenHtmlDialog] = useState(false);
  const [openCompareDialog, setOpenCompareDialog] = useState(false);
  const [productJson, setProductJson] = useState<unknown>(null);
  const [loadingProductJson, setLoadingProductJson] = useState(false);
  const [compareResult, setCompareResult] =
    useState<CompareWithLocalResult | null>(null);
  const [comparingWithLocal, setComparingWithLocal] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [syncing, setSyncing] = useState(false);
  /** 列表勾选中的 Printify 商品 id，用于批量同步到本地 */
  const [selectedProductIds, setSelectedProductIds] = useState<Set<string>>(
    () => new Set()
  );
  const [batchSyncing, setBatchSyncing] = useState(false);
  /** 当前批量同步的数量（用于同步中展示「正在同步 N 个」） */
  const [batchSyncCount, setBatchSyncCount] = useState(0);
  const [emblaRef, emblaApi] = useEmblaCarousel({ loop: true });
  const [selectedImageIndex, setSelectedImageIndex] = useState(0);

  const htmlToText = (html?: string) => {
    if (!html) return '';
    return html
      .replace(/<[^>]+>/g, ' ')
      .replace(/&nbsp;/gi, ' ')
      .replace(/&amp;/gi, '&')
      .replace(/&quot;/gi, '"')
      .replace(/&#39;/gi, "'")
      .replace(/\s+/g, ' ')
      .trim();
  };

  const sanitizeHtml = (html?: string) => {
    if (!html) return '';
    return DOMPurify.sanitize(html, {
      USE_PROFILES: { html: true },
      FORBID_TAGS: ['script', 'iframe', 'object', 'embed'],
      FORBID_ATTR: ['onerror', 'onclick', 'onload', 'style'],
    });
  };

  const enabledVariants = selectedProduct
    ? selectedProduct.variants.filter(variant => variant.is_enabled)
    : [];
  const handleCompareWithLocal = useCallback(async () => {
    if (!selectedStore || !selectedProduct) return;
    try {
      setComparingWithLocal(true);
      const response = await frontendApi.get(
        `/api/external-systems/printify/${selectedStore.id_hashid}/products/${selectedProduct.id}/compare-local`
      );
      setCompareResult(response.data as CompareWithLocalResult);
      setOpenCompareDialog(true);
    } catch (error: any) {
      frontendLogger.error('❌ 比较 Printify 商品与本地失败', {
        error: String(error),
        productId: selectedProduct.id,
      });
      toast.error(error?.response?.data?.error || '比较本地数据失败');
    } finally {
      setComparingWithLocal(false);
    }
  }, [selectedStore, selectedProduct]);

  // 获取 Printify 店铺列表
  const fetchStores = useCallback(async () => {
    try {
      frontendLogger.info('🔍 开始获取 Printify 店铺列表');
      const response = await frontendApi.get(
        '/api/external-systems?system_type=printify'
      );

      if (response.data && response.data.external_systems) {
        const printifyStores = response.data.external_systems.filter(
          (store: any) => store.system_type === 'PRINTIFY' && store.is_active
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

  const fetchLocalSyncStatuses = useCallback(
    async (store: PrintifyStore, productsData: PrintifyProduct[]) => {
      if (!store || productsData.length === 0) {
        setSyncStatusMap({});
        return {} as Record<string, SyncStatus>;
      }
      try {
        const response = await frontendApi.post(
          `/api/external-systems/printify/${store.id_hashid}/products/local-sync-status`,
          {
            products: productsData.map(p => ({
              id: p.id,
              updated_at: p.updated_at,
            })),
          }
        );
        const statuses = response.data?.statuses || {};
        const nextMap: Record<string, SyncStatus> = {};
        Object.entries(statuses).forEach(([productId, statusInfo]: any) => {
          nextMap[productId] = (statusInfo?.status ||
            'not_synced') as SyncStatus;
        });
        setSyncStatusMap(nextMap);
        return nextMap;
      } catch (error) {
        frontendLogger.warn('获取本地同步状态失败', { error: String(error) });
        setSyncStatusMap({});
        return {} as Record<string, SyncStatus>;
      }
    },
    []
  );

  const applyPageFilters = useCallback(
    (productsData: PrintifyProduct[]) => {
      let list = [...productsData];
      if (searchTerm) {
        const kw = searchTerm.toLowerCase();
        list = list.filter(
          (product: PrintifyProduct) =>
            product.title.toLowerCase().includes(kw) ||
            product.description?.toLowerCase().includes(kw) ||
            product.tags.some(tag => tag.toLowerCase().includes(kw))
        );
      }
      if (publishedFilter === 'published') {
        list = list.filter((p: PrintifyProduct) => p.is_published === true);
      } else if (publishedFilter === 'unpublished') {
        list = list.filter((p: PrintifyProduct) => p.is_published !== true);
      }
      return list;
    },
    [searchTerm, publishedFilter]
  );

  // 获取商品列表（服务端分页）
  const fetchProducts = useCallback(
    async (store: PrintifyStore) => {
      if (!store) return;

      try {
        setLoading(true);
        setError(null);

        frontendLogger.info('🔍 开始获取 Printify 商品列表', {
          storeId: store.id_hashid,
          storeName: store.name,
          page,
          pageSize,
          publishedFilter,
          searchTerm,
        });

        const response = await frontendApi.get(
          `/api/external-systems/printify/${store.id_hashid}/products`,
          {
            params: {
              page,
              limit: pageSize,
            },
          }
        );

        if (response.data.success) {
          const productsData = applyPageFilters(response.data.products || []);

          setProducts(productsData);
          setFilteredProducts(productsData);

          const pagination = response.data.pagination || {};
          const totalCount = Number(
            pagination.total || response.data.total_count || 0
          );
          const totalPages =
            Number(pagination.last_page || 0) ||
            Math.max(1, Math.ceil(totalCount / pageSize));
          setServerTotalCount(totalCount);
          setServerTotalPages(totalPages);

          const statusMap = await fetchLocalSyncStatuses(store, productsData);
          const currentPageDisplayCount =
            syncStatusFilter === 'all'
              ? productsData.length
              : productsData.filter(
                  p => (statusMap[p.id] || 'not_synced') === syncStatusFilter
                ).length;

          frontendLogger.info('✅ Printify 商品列表获取成功', {
            count: currentPageDisplayCount,
            totalCount,
            totalPages,
            storeName: store.name,
          });
        } else {
          throw new Error(response.data.message || '获取商品列表失败');
        }
      } catch (error) {
        frontendLogger.error('❌ 获取 Printify 商品列表失败', {
          error: String(error),
          storeId: store.id_hashid,
        });
        setError('获取商品列表失败');
      } finally {
        setLoading(false);
      }
    },
    [
      applyPageFilters,
      fetchLocalSyncStatuses,
      page,
      pageSize,
      syncStatusFilter,
    ]
  );

  const findNextPageWithData = useCallback(async () => {
    if (!selectedStore) return;
    if (page >= serverTotalPages) {
      toast('已经是最后一页');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      for (
        let targetPage = page + 1;
        targetPage <= serverTotalPages;
        targetPage += 1
      ) {
        const response = await frontendApi.get(
          `/api/external-systems/printify/${selectedStore.id_hashid}/products`,
          {
            params: {
              page: targetPage,
              limit: pageSize,
            },
          }
        );
        if (!response.data?.success) continue;

        const productsData = applyPageFilters(response.data.products || []);
        const statusMap = await fetchLocalSyncStatuses(
          selectedStore,
          productsData
        );
        const visibleList =
          syncStatusFilter === 'all'
            ? productsData
            : productsData.filter(
                p => (statusMap[p.id] || 'not_synced') === syncStatusFilter
              );
        if (visibleList.length > 0) {
          setPage(targetPage);
          toast.success(`已定位到第 ${targetPage} 页`);
          return;
        }
      }
      toast('后续页面也没有符合当前筛选条件的数据');
    } catch (error) {
      frontendLogger.error('❌ 自动翻页查找数据失败', { error: String(error) });
      toast.error('自动翻页失败');
    } finally {
      setLoading(false);
    }
  }, [
    applyPageFilters,
    fetchLocalSyncStatuses,
    page,
    pageSize,
    selectedStore,
    serverTotalPages,
    syncStatusFilter,
  ]);

  // 刷新商品列表
  const handleRefresh = useCallback(async () => {
    if (!selectedStore) return;

    setRefreshing(true);
    try {
      await fetchProducts(selectedStore);
      frontendLogger.info('✅ 商品列表刷新成功');
    } catch (error) {
      frontendLogger.error('❌ 商品列表刷新失败', { error: String(error) });
    } finally {
      setRefreshing(false);
    }
  }, [selectedStore, fetchProducts]);

  // 初始化
  useEffect(() => {
    const initialize = async () => {
      await fetchStores();
    };
    initialize();
  }, [fetchStores]);

  // 当选择店铺、分页、筛选变化时，重新拉取当前页
  useEffect(() => {
    if (selectedStore) {
      fetchProducts(selectedStore);
    }
  }, [selectedStore, fetchProducts]);

  useEffect(() => {
    setSelectedImageIndex(0);
  }, [selectedProduct?.id]);

  useEffect(() => {
    if (!emblaApi) return;
    const onSelect = () => setSelectedImageIndex(emblaApi.selectedScrollSnap());
    emblaApi.on('select', onSelect);
    onSelect();
    return () => {
      emblaApi.off('select', onSelect);
    };
  }, [emblaApi]);

  // 服务端分页：当前页数据就是要展示的数据（再叠加当前页的本地同步状态筛选）
  const totalPages = serverTotalPages;
  const currentProducts = filteredProducts.filter(product => {
    if (syncStatusFilter === 'all') return true;
    const status = syncStatusMap[product.id] || 'not_synced';
    return status === syncStatusFilter;
  });
  const hasPageOnlyFilter =
    publishedFilter !== 'all' || syncStatusFilter !== 'all' || !!searchTerm;

  // 获取商品主图
  const getProductImage = (product: PrintifyProduct) => {
    const defaultImage = product.images.find(img => img.is_default);
    return (
      defaultImage?.src || product.images[0]?.src || '/placeholder-product.png'
    );
  };

  const selectedProductImages = selectedProduct
    ? selectedProduct.images?.length
      ? selectedProduct.images
      : [
          {
            src: getProductImage(selectedProduct),
            variant_ids: [],
            position: 'fallback',
            is_default: true,
          },
        ]
    : [];

  // 获取商品价格范围（Printify API 返回分为单位，显示时除以 100 转为元）
  const getProductPriceRange = (product: PrintifyProduct) => {
    const prices = product.variants.map(v => v.price / 100).filter(p => p > 0);
    if (prices.length === 0) return 'N/A';
    if (prices.length === 1) return `$${prices[0].toFixed(2)}`;
    const min = Math.min(...prices);
    const max = Math.max(...prices);
    return min === max
      ? `$${min.toFixed(2)}`
      : `$${min.toFixed(2)} - $${max.toFixed(2)}`;
  };

  const getVariantSummary = (product: PrintifyProduct) => {
    const enabled = product.variants.filter(v => v.is_enabled).length;
    const total = product.variants.length;
    return `变体 ${enabled}（启用 ${enabled}/总 ${total}）`;
  };

  const getSyncStatusMeta = (status: SyncStatus | undefined) => {
    if (status === 'in_sync') {
      return { label: '本地一致', color: 'success' as const };
    }
    if (status === 'different') {
      return { label: '与本地有差异', color: 'warning' as const };
    }
    return { label: '未同步到本地', color: 'default' as const };
  };

  const getPrintifyProductUrl = (productId: string) =>
    `https://printify.com/app/product-details/${productId}?fromProductsPage=1`;

  const fetchPrintifyProductJson = useCallback(
    async (product: PrintifyProduct, openJsonDialogAfterLoad = false) => {
      if (!selectedStore) return;
      try {
        setLoadingProductJson(true);
        const response = await frontendApi.get(
          `/api/external-systems/printify/${selectedStore.id_hashid}/products/${product.id}/json`
        );
        const latestProduct = response.data?.product;
        if (latestProduct) {
          setProductJson(latestProduct);
          setSelectedProduct(latestProduct);
          setProducts(prev =>
            prev.map(p => (p.id === latestProduct.id ? latestProduct : p))
          );
        } else {
          setProductJson(response.data);
        }

        if (openJsonDialogAfterLoad) {
          setOpenJsonDialog(true);
        }
      } catch (error: any) {
        frontendLogger.error('❌ 获取 Printify 商品 JSON 失败', {
          error: String(error),
          productId: product.id,
        });
        toast.error(error?.response?.data?.error || '读取商品 JSON 失败');
      } finally {
        setLoadingProductJson(false);
      }
    },
    [selectedStore]
  );

  // 查看商品详情
  const handleViewProduct = (product: PrintifyProduct) => {
    setSelectedProduct(product);
    setProductJson(null);
    setOpenProductDialog(true);
  };

  // 同步单个商品到本地数据库
  const handleSyncProduct = async (product: PrintifyProduct) => {
    if (!selectedStore) {
      setError('请先选择店铺');
      return;
    }

    try {
      setSyncing(true);
      setError(null);
      toast.loading('正在同步该商品到本地…', { id: 'printify-single-sync' });

      frontendLogger.info('🔄 开始同步单个 Printify 商品到本地数据库', {
        productId: product.id,
        productTitle: product.title,
        storeId: selectedStore.id_hashid,
      });

      const response = await frontendApi.post(
        '/api/printify-sync/sync-products',
        {
          external_system_id_hashid: selectedStore.id_hashid,
          product_ids: [product.id], // 只同步当前商品
        }
      );

      toast.success(`同步成功：${product.title} 已写入本地`, {
        id: 'printify-single-sync',
      });
      frontendLogger.info('✅ Printify 商品同步成功', response.data);

      await fetchProducts(selectedStore);
    } catch (err: any) {
      frontendLogger.error('❌ Printify 商品同步失败', {
        error: String(err),
        productId: product.id,
      });
      const msg = err.response?.data?.detail || '同步失败';
      setError('同步 Printify 商品失败');
      toast.error(msg, { id: 'printify-single-sync' });
    } finally {
      setSyncing(false);
    }
  };

  const toggleSelect = (id: string) => {
    setSelectedProductIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const selectAllOnPage = () => {
    const ids = currentProducts.map(p => p.id);
    setSelectedProductIds(prev => {
      const next = new Set(prev);
      ids.forEach(id => next.add(id));
      return next;
    });
  };

  const selectAllFiltered = () => {
    setSelectedProductIds(new Set(currentProducts.map(p => p.id)));
  };

  const clearSelection = () => {
    setSelectedProductIds(new Set());
  };

  const handleBatchSyncToLocal = async () => {
    if (!selectedStore || selectedProductIds.size === 0) {
      setError('请先勾选要同步的商品');
      return;
    }
    const productIds = Array.from(selectedProductIds);
    const count = productIds.length;
    setBatchSyncCount(count);
    setBatchSyncing(true);
    setError(null);
    toast.loading(`正在同步 ${count} 个商品到本地，请稍候…`, {
      id: TOAST_SYNC_ID,
      duration: Infinity,
    });
    try {
      frontendLogger.info('🔄 批量同步 Printify 商品到本地', {
        storeId: selectedStore.id_hashid,
        count,
      });
      const response = await frontendApi.post(
        '/api/printify-sync/sync-products',
        {
          external_system_id_hashid: selectedStore.id_hashid,
          product_ids: productIds,
        }
      );
      const data = response?.data ?? {};
      const totalSynced = data.total_synced ?? count;
      const totalErrors = data.total_errors ?? 0;
      frontendLogger.info('✅ 批量同步完成', data);
      setSelectedProductIds(new Set());
      await fetchProducts(selectedStore);
      if (totalErrors > 0) {
        toast.success(
          `同步完成：成功 ${totalSynced} 个，失败 ${totalErrors} 个`,
          { id: TOAST_SYNC_ID, duration: 5000 }
        );
      } else {
        toast.success(`同步成功：共 ${totalSynced} 个商品已写入本地`, {
          id: TOAST_SYNC_ID,
        });
      }
    } catch (err: any) {
      frontendLogger.error('❌ 批量同步失败', { error: String(err) });
      const msg = err.response?.data?.detail || '批量同步失败';
      setError(msg);
      toast.error(msg, { id: TOAST_SYNC_ID, duration: 5000 });
    } finally {
      setBatchSyncing(false);
      setBatchSyncCount(0);
    }
  };

  return (
    <ProtectedRoute>
      <DashboardLayout>
        <Box sx={{ p: 3 }}>
          {/* 页面标题 */}
          <Box
            sx={{
              mb: 3,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <Box>
              <Typography variant='h4' component='h1' gutterBottom>
                Printify 商品管理
              </Typography>
              <Typography variant='body1' color='text.secondary'>
                管理和查看 Printify 店铺中的商品
              </Typography>
            </Box>
            <Button
              variant='outlined'
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
                <Typography variant='h6' gutterBottom>
                  选择店铺
                </Typography>
                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                  {stores.map(store => (
                    <Chip
                      key={store.id_hashid}
                      label={store.name}
                      color={
                        selectedStore?.id_hashid === store.id_hashid
                          ? 'primary'
                          : 'default'
                      }
                      onClick={() => {
                        setPage(1);
                        setSelectedProductIds(new Set());
                        setSelectedStore(store);
                      }}
                      variant={
                        selectedStore?.id_hashid === store.id_hashid
                          ? 'filled'
                          : 'outlined'
                      }
                    />
                  ))}
                </Box>
              </CardContent>
            </Card>
          )}

          {/* 搜索和过滤（当前页范围） */}
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Box
                sx={{
                  display: 'flex',
                  gap: 2,
                  alignItems: 'center',
                  flexWrap: 'wrap',
                }}
              >
                <TextField
                  fullWidth
                  placeholder='搜索商品名称、描述或标签...'
                  value={searchInput}
                  onChange={e => setSearchInput(e.target.value)}
                  onKeyDown={e => {
                    if (e.key === 'Enter') {
                      setPage(1);
                      setSearchTerm(searchInput.trim());
                    }
                  }}
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position='start'>
                        <SearchIcon />
                      </InputAdornment>
                    ),
                  }}
                />
                <Button
                  variant='outlined'
                  onClick={() => {
                    setPage(1);
                    setSearchTerm(searchInput.trim());
                  }}
                >
                  检索
                </Button>
                <Chip
                  icon={<FilterIcon />}
                  label={`当前页显示 ${currentProducts.length} / 页内 ${
                    filteredProducts.length
                  } / 总 ${serverTotalCount}`}
                  color='primary'
                  variant='outlined'
                />
                <Chip
                  label='范围：当前页'
                  size='small'
                  variant='outlined'
                  color='default'
                />
                <FormControl size='small' sx={{ minWidth: 100 }}>
                  <Select
                    value={pageSize}
                    onChange={e => {
                      setPage(1);
                      setPageSize(Number(e.target.value));
                    }}
                  >
                    <MenuItem value={10}>10 / 页</MenuItem>
                    <MenuItem value={20}>20 / 页</MenuItem>
                    <MenuItem value={50}>50 / 页</MenuItem>
                  </Select>
                </FormControl>
                <Typography
                  variant='body2'
                  color='text.secondary'
                  sx={{ whiteSpace: 'nowrap' }}
                >
                  发布状态:
                </Typography>
                <Chip
                  label='全部'
                  size='small'
                  onClick={() => {
                    setPage(1);
                    setPublishedFilter('all');
                  }}
                  color={publishedFilter === 'all' ? 'primary' : 'default'}
                  variant={publishedFilter === 'all' ? 'filled' : 'outlined'}
                />
                <Chip
                  label='已发布'
                  size='small'
                  onClick={() => {
                    setPage(1);
                    setPublishedFilter('published');
                  }}
                  color={
                    publishedFilter === 'published' ? 'primary' : 'default'
                  }
                  variant={
                    publishedFilter === 'published' ? 'filled' : 'outlined'
                  }
                />
                <Chip
                  label='未发布'
                  size='small'
                  onClick={() => {
                    setPage(1);
                    setPublishedFilter('unpublished');
                  }}
                  color={
                    publishedFilter === 'unpublished' ? 'primary' : 'default'
                  }
                  variant={
                    publishedFilter === 'unpublished' ? 'filled' : 'outlined'
                  }
                />
                <Typography
                  variant='body2'
                  color='text.secondary'
                  sx={{ whiteSpace: 'nowrap' }}
                >
                  同步状态:
                </Typography>
                <Chip
                  label='全部'
                  size='small'
                  onClick={() => setSyncStatusFilter('all')}
                  color={syncStatusFilter === 'all' ? 'primary' : 'default'}
                  variant={syncStatusFilter === 'all' ? 'filled' : 'outlined'}
                />
                <Chip
                  label='本地一致'
                  size='small'
                  onClick={() => setSyncStatusFilter('in_sync')}
                  color={syncStatusFilter === 'in_sync' ? 'primary' : 'default'}
                  variant={
                    syncStatusFilter === 'in_sync' ? 'filled' : 'outlined'
                  }
                />
                <Chip
                  label='未同步'
                  size='small'
                  onClick={() => setSyncStatusFilter('not_synced')}
                  color={
                    syncStatusFilter === 'not_synced' ? 'primary' : 'default'
                  }
                  variant={
                    syncStatusFilter === 'not_synced' ? 'filled' : 'outlined'
                  }
                />
                <Chip
                  label='有差异'
                  size='small'
                  onClick={() => setSyncStatusFilter('different')}
                  color={
                    syncStatusFilter === 'different' ? 'primary' : 'default'
                  }
                  variant={
                    syncStatusFilter === 'different' ? 'filled' : 'outlined'
                  }
                />
              </Box>
            </CardContent>
          </Card>

          {/* 批量操作工具栏：全选 + 一键同步到本地 */}
          {!loading && selectedStore && filteredProducts.length > 0 && (
            <Card sx={{ mb: 2 }}>
              <CardContent>
                <Box
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 2,
                    flexWrap: 'wrap',
                  }}
                >
                  <Button
                    size='small'
                    variant='outlined'
                    onClick={selectAllOnPage}
                    disabled={batchSyncing}
                  >
                    全选当前页
                  </Button>
                  <Button
                    size='small'
                    variant='outlined'
                    onClick={selectAllFiltered}
                    disabled={batchSyncing}
                  >
                    全选当前加载（{filteredProducts.length} 个）
                  </Button>
                  <Button
                    size='small'
                    variant='outlined'
                    onClick={clearSelection}
                    disabled={selectedProductIds.size === 0 || batchSyncing}
                  >
                    取消全选
                  </Button>
                  <Typography variant='body2' color='text.secondary'>
                    已选 {selectedProductIds.size} 个
                  </Typography>
                  <Button
                    variant='contained'
                    startIcon={
                      batchSyncing ? (
                        <CircularProgress size={16} color='inherit' />
                      ) : (
                        <SyncIcon />
                      )
                    }
                    onClick={handleBatchSyncToLocal}
                    disabled={batchSyncing || selectedProductIds.size === 0}
                  >
                    {batchSyncing ? '同步中…' : '一键同步到本地'}
                  </Button>
                </Box>
                {batchSyncing && batchSyncCount > 0 && (
                  <Box sx={{ mt: 2 }}>
                    <LinearProgress
                      sx={{ mb: 1, borderRadius: 1 }}
                      color='primary'
                    />
                    <Typography
                      variant='body2'
                      color='text.secondary'
                      sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}
                    >
                      <CircularProgress size={12} color='inherit' />
                      正在同步 {batchSyncCount} 个商品到本地，请稍候…
                    </Typography>
                  </Box>
                )}
              </CardContent>
            </Card>
          )}

          {/* 错误提示 */}
          {error && (
            <Alert severity='error' sx={{ mb: 3 }}>
              {error}
            </Alert>
          )}

          {/* 加载状态 */}
          {loading && (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
              <CircularProgress />
            </Box>
          )}

          {/* 商品网格 */}
          {!loading && !error && (
            <>
              {currentProducts.length === 0 ? (
                <Card>
                  <CardContent sx={{ textAlign: 'center', py: 4 }}>
                    <InventoryIcon
                      sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }}
                    />
                    <Typography variant='h6' color='text.secondary'>
                      {hasPageOnlyFilter
                        ? '当前页没有符合筛选条件的商品'
                        : '该店铺暂无商品'}
                    </Typography>
                    {hasPageOnlyFilter && (
                      <Typography
                        variant='body2'
                        color='text.secondary'
                        sx={{ mt: 1 }}
                      >
                        当前筛选基于「本页 20 条」计算，可翻页继续查看
                      </Typography>
                    )}
                    <Box
                      sx={{
                        mt: 2,
                        display: 'flex',
                        gap: 1,
                        justifyContent: 'center',
                        flexWrap: 'wrap',
                      }}
                    >
                      {searchTerm && (
                        <Button
                          variant='outlined'
                          onClick={() => {
                            setPage(1);
                            setSearchInput('');
                            setSearchTerm('');
                          }}
                        >
                          清除检索
                        </Button>
                      )}
                      {(publishedFilter !== 'all' ||
                        syncStatusFilter !== 'all') && (
                        <Button
                          variant='outlined'
                          onClick={() => {
                            setPage(1);
                            setPublishedFilter('all');
                            setSyncStatusFilter('all');
                          }}
                        >
                          清除状态筛选
                        </Button>
                      )}
                      {page < totalPages && (
                        <Button
                          variant='contained'
                          onClick={findNextPageWithData}
                        >
                          自动查找下一页有结果
                        </Button>
                      )}
                    </Box>
                  </CardContent>
                </Card>
              ) : (
                <>
                  <Box
                    sx={{
                      display: 'grid',
                      gridTemplateColumns: {
                        xs: 'repeat(auto-fit, minmax(280px, 1fr))',
                        sm: 'repeat(auto-fit, minmax(300px, 1fr))',
                        md: 'repeat(auto-fit, minmax(320px, 1fr))',
                        lg: 'repeat(auto-fit, minmax(300px, 1fr))',
                      },
                      gap: 3,
                      justifyContent: 'center',
                    }}
                  >
                    {currentProducts.map(product => (
                      <Box key={product.id}>
                        <Card
                          sx={{
                            height: '100%',
                            display: 'flex',
                            flexDirection: 'column',
                            position: 'relative',
                          }}
                        >
                          <Box
                            sx={{
                              position: 'absolute',
                              top: 8,
                              right: 8,
                              zIndex: 1,
                              display: 'flex',
                              flexDirection: 'column',
                              gap: 0.5,
                              alignItems: 'flex-end',
                            }}
                          >
                            <Chip
                              label={product.is_published ? '已发布' : '未发布'}
                              size='small'
                              color={
                                product.is_published ? 'success' : 'default'
                              }
                              variant='filled'
                              sx={{ opacity: 0.95 }}
                            />
                            <Chip
                              label={
                                getSyncStatusMeta(syncStatusMap[product.id])
                                  .label
                              }
                              size='small'
                              color={
                                getSyncStatusMeta(syncStatusMap[product.id])
                                  .color
                              }
                              variant='outlined'
                              sx={{
                                bgcolor: 'background.paper',
                                opacity: 0.95,
                              }}
                            />
                          </Box>
                          <Box
                            sx={{
                              position: 'absolute',
                              top: 8,
                              left: 8,
                              zIndex: 1,
                            }}
                          >
                            <Checkbox
                              size='small'
                              checked={selectedProductIds.has(product.id)}
                              onChange={() => toggleSelect(product.id)}
                              sx={{
                                bgcolor: 'background.paper',
                                borderRadius: 1,
                              }}
                            />
                          </Box>
                          <CardMedia
                            component='img'
                            image={getProductImage(product)}
                            alt={product.title}
                            sx={{
                              objectFit: 'cover',
                              width: '100%',
                              height: { xs: '150px', sm: '180px', md: '200px' },
                              minHeight: '150px',
                              maxHeight: '200px',
                              maxWidth: {
                                xs: '150px',
                                sm: '180px',
                                md: '200px',
                              },
                              display: 'block',
                              margin: '0 auto',
                            }}
                          />
                          <CardContent
                            sx={{
                              flexGrow: 1,
                              display: 'flex',
                              flexDirection: 'column',
                            }}
                          >
                            <Typography
                              variant='h6'
                              component='h3'
                              gutterBottom
                              noWrap
                            >
                              {product.title}
                            </Typography>

                            {product.description && (
                              <Typography
                                variant='body2'
                                color='text.secondary'
                                sx={{
                                  mb: 2,
                                  display: '-webkit-box',
                                  WebkitLineClamp: 2,
                                  WebkitBoxOrient: 'vertical',
                                  overflow: 'hidden',
                                }}
                              >
                                {htmlToText(product.description)}
                              </Typography>
                            )}

                            <Box
                              sx={{
                                display: 'flex',
                                gap: 1,
                                mb: 2,
                                flexWrap: 'wrap',
                              }}
                            >
                              {product.tags.slice(0, 3).map((tag, index) => (
                                <Chip
                                  key={index}
                                  label={tag}
                                  size='small'
                                  variant='outlined'
                                />
                              ))}
                              {product.tags.length > 3 && (
                                <Chip
                                  label={`+${product.tags.length - 3}`}
                                  size='small'
                                  variant='outlined'
                                />
                              )}
                            </Box>

                            <Box
                              sx={{
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'center',
                                mb: 2,
                              }}
                            >
                              <Typography variant='h6' color='primary'>
                                {getProductPriceRange(product)}
                              </Typography>
                              <Box
                                sx={{
                                  display: 'flex',
                                  alignItems: 'center',
                                  gap: 0.5,
                                  color: 'text.secondary',
                                }}
                              >
                                <InventoryIcon
                                  fontSize='small'
                                  color='action'
                                />
                                <Typography
                                  variant='caption'
                                  color='text.secondary'
                                >
                                  {getVariantSummary(product)}
                                </Typography>
                              </Box>
                            </Box>

                            <Box sx={{ display: 'flex', gap: 1, mt: 'auto' }}>
                              <Button
                                variant='contained'
                                size='small'
                                startIcon={<SyncIcon />}
                                onClick={() => handleSyncProduct(product)}
                                disabled={syncing}
                              >
                                同步到本地
                              </Button>
                              <Button
                                variant='outlined'
                                size='small'
                                startIcon={<ViewIcon />}
                                onClick={() => handleViewProduct(product)}
                              >
                                查看详情
                              </Button>
                              <Button
                                variant='outlined'
                                size='small'
                                startIcon={<OpenInNewIcon />}
                                onClick={() =>
                                  window.open(
                                    getPrintifyProductUrl(product.id),
                                    '_blank',
                                    'noopener,noreferrer'
                                  )
                                }
                              >
                                打开 Printify
                              </Button>
                            </Box>
                          </CardContent>
                        </Card>
                      </Box>
                    ))}
                  </Box>

                  {/* 分页 */}
                  {totalPages > 1 && (
                    <Box
                      sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}
                    >
                      <Pagination
                        count={totalPages}
                        page={page}
                        onChange={(_, value) => setPage(value)}
                        color='primary'
                        size='large'
                      />
                    </Box>
                  )}
                </>
              )}
            </>
          )}

          {/* 商品详情对话框 */}
          <Dialog
            open={openProductDialog}
            onClose={() => setOpenProductDialog(false)}
            maxWidth='md'
            fullWidth
          >
            <DialogTitle>{selectedProduct?.title}</DialogTitle>
            <DialogContent>
              {selectedProduct && (
                <Box>
                  {/* 商品图片轮播（左右切换） */}
                  <Box sx={{ mb: 3 }}>
                    <Box
                      sx={{
                        position: 'relative',
                        borderRadius: 2,
                        overflow: 'hidden',
                        border: '1px solid',
                        borderColor: 'divider',
                        backgroundColor: '#fafafa',
                      }}
                    >
                      <Box ref={emblaRef} sx={{ overflow: 'hidden' }}>
                        <Box sx={{ display: 'flex' }}>
                          {selectedProductImages.map((img, index) => (
                            <Box
                              key={`${img.src}-${index}`}
                              sx={{
                                flex: '0 0 100%',
                                minWidth: 0,
                                display: 'flex',
                                justifyContent: 'center',
                                alignItems: 'center',
                                py: 2,
                                px: 1,
                              }}
                            >
                              <img
                                src={img.src}
                                alt={`${selectedProduct.title}-${index + 1}`}
                                style={{
                                  maxWidth: '100%',
                                  maxHeight: '300px',
                                  objectFit: 'contain',
                                }}
                              />
                            </Box>
                          ))}
                        </Box>
                      </Box>
                      <Button
                        size='small'
                        variant='contained'
                        onClick={() => emblaApi?.scrollPrev()}
                        sx={{
                          minWidth: 0,
                          position: 'absolute',
                          top: '50%',
                          left: 8,
                          transform: 'translateY(-50%)',
                        }}
                      >
                        <ChevronLeftIcon />
                      </Button>
                      <Button
                        size='small'
                        variant='contained'
                        onClick={() => emblaApi?.scrollNext()}
                        sx={{
                          minWidth: 0,
                          position: 'absolute',
                          top: '50%',
                          right: 8,
                          transform: 'translateY(-50%)',
                        }}
                      >
                        <ChevronRightIcon />
                      </Button>
                    </Box>
                    <Typography
                      variant='caption'
                      color='text.secondary'
                      sx={{ mt: 1, display: 'block', textAlign: 'center' }}
                    >
                      图片 {selectedImageIndex + 1} /{' '}
                      {selectedProductImages.length || 1}
                    </Typography>
                  </Box>

                  {/* 商品信息 */}
                  <Box
                    sx={{
                      display: 'grid',
                      gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' },
                      gap: 2,
                    }}
                  >
                    <Box>
                      <Typography variant='h6' gutterBottom>
                        基本信息
                      </Typography>
                      <Typography
                        variant='body2'
                        color='text.secondary'
                        paragraph
                        sx={{ maxHeight: 260, overflow: 'auto' }}
                      >
                        {htmlToText(selectedProduct.description) || '暂无描述'}
                      </Typography>
                      <Button
                        size='small'
                        variant='outlined'
                        startIcon={<ArticleIcon />}
                        onClick={() => setOpenHtmlDialog(true)}
                        disabled={!selectedProduct.description}
                        sx={{ mb: 2 }}
                      >
                        预览 HTML 效果（已安全过滤）
                      </Button>

                      <Typography variant='subtitle2' gutterBottom>
                        标签:
                      </Typography>
                      <Box
                        sx={{
                          display: 'flex',
                          gap: 1,
                          flexWrap: 'wrap',
                          mb: 2,
                        }}
                      >
                        {selectedProduct.tags.map((tag, index) => (
                          <Chip key={index} label={tag} size='small' />
                        ))}
                      </Box>
                    </Box>

                    <Box>
                      <Typography variant='h6' gutterBottom>
                        变体信息
                      </Typography>
                      <TableContainer
                        component={Paper}
                        variant='outlined'
                        sx={{ maxHeight: 320, overflow: 'auto' }}
                      >
                        <Table size='small'>
                          <TableHead>
                            <TableRow>
                              <TableCell>变体规格</TableCell>
                              <TableCell>价格</TableCell>
                              <TableCell>库存</TableCell>
                              <TableCell>状态</TableCell>
                            </TableRow>
                          </TableHead>
                          <TableBody>
                            {enabledVariants.map(variant => (
                              <TableRow key={variant.id}>
                                <TableCell>
                                  {variant.title || `Variant #${variant.id}`}
                                </TableCell>
                                <TableCell>
                                  ${(variant.price / 100).toFixed(2)}
                                </TableCell>
                                <TableCell>
                                  <Chip
                                    label={
                                      variant.is_available ? '有库存' : '缺货'
                                    }
                                    color={
                                      variant.is_available
                                        ? 'success'
                                        : 'warning'
                                    }
                                    size='small'
                                  />
                                </TableCell>
                                <TableCell>
                                  <Chip
                                    label='启用'
                                    color='success'
                                    size='small'
                                  />
                                </TableCell>
                              </TableRow>
                            ))}
                            {enabledVariants.length === 0 && (
                              <TableRow>
                                <TableCell colSpan={4} align='center'>
                                  暂无启用的变体
                                </TableCell>
                              </TableRow>
                            )}
                          </TableBody>
                        </Table>
                      </TableContainer>
                    </Box>
                  </Box>
                </Box>
              )}
            </DialogContent>
            <DialogActions>
              <Button
                variant='outlined'
                startIcon={<OpenInNewIcon />}
                onClick={() => {
                  if (!selectedProduct) return;
                  window.open(
                    getPrintifyProductUrl(selectedProduct.id),
                    '_blank',
                    'noopener,noreferrer'
                  );
                }}
                disabled={!selectedProduct}
                sx={{ mr: 1 }}
              >
                打开 Printify 商品页
              </Button>
              <Button
                variant='outlined'
                startIcon={
                  loadingProductJson ? (
                    <CircularProgress size={16} color='inherit' />
                  ) : (
                    <RefreshIcon />
                  )
                }
                onClick={() =>
                  selectedProduct && fetchPrintifyProductJson(selectedProduct)
                }
                disabled={loadingProductJson || !selectedProduct}
                sx={{ mr: 1 }}
              >
                {loadingProductJson ? '读取中…' : '重新读取商品 JSON'}
              </Button>
              <Button
                variant='outlined'
                startIcon={<DataObjectIcon />}
                onClick={() =>
                  selectedProduct &&
                  fetchPrintifyProductJson(selectedProduct, true)
                }
                disabled={loadingProductJson || !selectedProduct}
                sx={{ mr: 1 }}
              >
                查看 JSON
              </Button>
              <Button
                variant='outlined'
                startIcon={
                  comparingWithLocal ? (
                    <CircularProgress size={16} color='inherit' />
                  ) : (
                    <CompareArrowsIcon />
                  )
                }
                onClick={handleCompareWithLocal}
                disabled={comparingWithLocal || !selectedProduct}
                sx={{ mr: 1 }}
              >
                {comparingWithLocal ? '比较中…' : '与本地数据库比较'}
              </Button>
              <Button
                variant='outlined'
                startIcon={
                  syncing ? (
                    <CircularProgress size={16} color='inherit' />
                  ) : (
                    <SyncIcon />
                  )
                }
                onClick={() => handleSyncProduct(selectedProduct!)}
                disabled={syncing}
                color='primary'
                sx={{ mr: 1 }}
              >
                {syncing ? '同步中…' : '同步到本地'}
              </Button>
              <Button
                variant='outlined'
                startIcon={<LinkIcon />}
                onClick={() => setOpenMappingDialog(true)}
                sx={{ mr: 1 }}
              >
                映射到核心商品
              </Button>
              <Button onClick={() => setOpenProductDialog(false)}>关闭</Button>
            </DialogActions>
          </Dialog>

          {/* 商品映射对话框 */}
          <ProductMappingDialog
            open={openMappingDialog}
            onClose={() => setOpenMappingDialog(false)}
            printifyProduct={selectedProduct}
            onMappingCreated={mapping => {
              frontendLogger.info('✅ 商品映射创建成功', mapping);
              setOpenMappingDialog(false);
            }}
          />

          <Dialog
            open={openHtmlDialog}
            onClose={() => setOpenHtmlDialog(false)}
            maxWidth='md'
            fullWidth
          >
            <DialogTitle>HTML 预览（安全过滤）</DialogTitle>
            <DialogContent>
              <Box
                sx={{
                  mt: 1,
                  p: 2,
                  border: '1px solid',
                  borderColor: 'divider',
                  borderRadius: 1,
                  maxHeight: '70vh',
                  overflow: 'auto',
                }}
                dangerouslySetInnerHTML={{
                  __html: sanitizeHtml(selectedProduct?.description),
                }}
              />
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setOpenHtmlDialog(false)}>关闭</Button>
            </DialogActions>
          </Dialog>

          <Dialog
            open={openCompareDialog}
            onClose={() => setOpenCompareDialog(false)}
            maxWidth='sm'
            fullWidth
          >
            <DialogTitle>与本地数据库比较</DialogTitle>
            <DialogContent>
              {compareResult ? (
                <Box sx={{ mt: 1, display: 'grid', gap: 1.5 }}>
                  <Alert
                    severity={compareResult.is_in_sync ? 'success' : 'warning'}
                  >
                    {compareResult.is_in_sync
                      ? '远程 Printify 与本地快照一致'
                      : '远程 Printify 与本地快照不一致'}
                  </Alert>
                  <Typography variant='body2'>
                    <strong>远程 updated_at:</strong>{' '}
                    {compareResult.remote?.updated_at || '-'}
                  </Typography>
                  <Typography variant='body2'>
                    <strong>本地 raw_data.updated_at:</strong>{' '}
                    {compareResult.local?.raw_data_updated_at || '-'}
                  </Typography>
                  <Typography variant='body2'>
                    <strong>本地 last_synced_at:</strong>{' '}
                    {compareResult.local?.last_synced_at || '-'}
                  </Typography>
                  <Typography variant='body2'>
                    <strong>本地 DB updated_at:</strong>{' '}
                    {compareResult.local?.updated_at || '-'}
                  </Typography>
                  <Typography variant='body2'>
                    <strong>本地发布状态:</strong>{' '}
                    {compareResult.local?.is_published ? '已发布' : '未发布'}
                  </Typography>
                </Box>
              ) : (
                <Box sx={{ py: 3, textAlign: 'center' }}>
                  <CircularProgress size={24} />
                </Box>
              )}
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setOpenCompareDialog(false)}>关闭</Button>
            </DialogActions>
          </Dialog>

          <JsonViewerDialog
            open={openJsonDialog}
            onClose={() => setOpenJsonDialog(false)}
            title='Printify 商品 JSON'
            subtitle={selectedProduct?.title}
            data={productJson}
            loading={loadingProductJson}
          />
        </Box>
      </DashboardLayout>
    </ProtectedRoute>
  );
}

export default PrintifyProductsPage;
