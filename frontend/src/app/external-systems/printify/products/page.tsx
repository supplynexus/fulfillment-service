'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  CardMedia,
  Chip,
  Button,
  IconButton,
  Alert,
  CircularProgress,
  LinearProgress,
  Grid,
  Pagination,
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
  Tooltip,
  Badge,
  Checkbox,
} from '@mui/material';
import {
  Search as SearchIcon,
  Refresh as RefreshIcon,
  Visibility as ViewIcon,
  ShoppingCart as CartIcon,
  Image as ImageIcon,
  Inventory as InventoryIcon,
  AttachMoney as PriceIcon,
  Category as CategoryIcon,
  FilterList as FilterIcon,
  Sort as SortIcon,
  Link as LinkIcon,
  Sync as SyncIcon,
  CheckBox as CheckBoxIcon,
  CheckBoxOutlineBlank as CheckBoxOutlineBlankIcon,
} from '@mui/icons-material';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import toast from 'react-hot-toast';
import { frontendApi } from '@/lib/api';
import { frontendLogger } from '@/lib/frontend-logger';
import { ProductMappingDialog } from '@/components/printify/ProductMappingDialog';

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

function PrintifyProductsPage() {
  const [products, setProducts] = useState<PrintifyProduct[]>([]);
  const [stores, setStores] = useState<PrintifyStore[]>([]);
  const [selectedStore, setSelectedStore] = useState<PrintifyStore | null>(
    null
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  /** 发布状态筛选: 'all' | 'published' | 'unpublished' */
  const [publishedFilter, setPublishedFilter] = useState<'all' | 'published' | 'unpublished'>('all');
  const [filteredProducts, setFilteredProducts] = useState<PrintifyProduct[]>(
    []
  );
  const [page, setPage] = useState(1);
  const [productsPerPage] = useState(12);
  const [selectedProduct, setSelectedProduct] =
    useState<PrintifyProduct | null>(null);
  const [openProductDialog, setOpenProductDialog] = useState(false);
  const [openMappingDialog, setOpenMappingDialog] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [syncing, setSyncing] = useState(false);
  /** 列表勾选中的 Printify 商品 id，用于批量同步到本地 */
  const [selectedProductIds, setSelectedProductIds] = useState<Set<string>>(
    () => new Set()
  );
  const [batchSyncing, setBatchSyncing] = useState(false);
  /** 当前批量同步的数量（用于同步中展示「正在同步 N 个」） */
  const [batchSyncCount, setBatchSyncCount] = useState(0);

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

  // 获取商品列表
  const fetchProducts = useCallback(async (store: PrintifyStore) => {
    if (!store) return;

    try {
      setLoading(true);
      setError(null);

      frontendLogger.info('🔍 开始获取 Printify 商品列表', {
        storeId: store.id_hashid,
        storeName: store.name,
      });

      const response = await frontendApi.get(
        `/api/external-systems/printify/${store.id_hashid}/products`
      );

      if (response.data.success) {
        const productsData = response.data.products || [];
        setProducts(productsData);
        setFilteredProducts(productsData);
        frontendLogger.info('✅ Printify 商品列表获取成功', {
          count: productsData.length,
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
  }, []);

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

  // 搜索 + 发布状态筛选
  useEffect(() => {
    let list = products;
    if (searchTerm) {
      list = list.filter(
        product =>
          product.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
          product.description
            ?.toLowerCase()
            .includes(searchTerm.toLowerCase()) ||
          product.tags.some(tag =>
            tag.toLowerCase().includes(searchTerm.toLowerCase())
          )
      );
    }
    if (publishedFilter === 'published') {
      list = list.filter(p => p.is_published === true);
    } else if (publishedFilter === 'unpublished') {
      list = list.filter(p => p.is_published !== true);
    }
    setFilteredProducts(list);
    setPage(1);
  }, [searchTerm, publishedFilter, products]);

  // 初始化
  useEffect(() => {
    const initialize = async () => {
      await fetchStores();
    };
    initialize();
  }, [fetchStores]);

  // 当选择店铺时获取商品和同步状态
  useEffect(() => {
    if (selectedStore) {
      fetchProducts(selectedStore);
    }
  }, [selectedStore, fetchProducts]);

  // 分页计算
  const totalPages = Math.ceil(filteredProducts.length / productsPerPage);
  const startIndex = (page - 1) * productsPerPage;
  const endIndex = startIndex + productsPerPage;
  const currentProducts = filteredProducts.slice(startIndex, endIndex);

  // 获取商品主图
  const getProductImage = (product: PrintifyProduct) => {
    const defaultImage = product.images.find(img => img.is_default);
    return (
      defaultImage?.src || product.images[0]?.src || '/placeholder-product.png'
    );
  };

  // 获取商品价格范围（Printify API 返回分为单位，显示时除以 100 转为元）
  const getProductPriceRange = (product: PrintifyProduct) => {
    const prices = product.variants.map(v => v.price / 100).filter(p => p > 0);
    if (prices.length === 0) return 'N/A';
    if (prices.length === 1) return `$${prices[0].toFixed(2)}`;
    const min = Math.min(...prices);
    const max = Math.max(...prices);
    return min === max ? `$${min.toFixed(2)}` : `$${min.toFixed(2)} - $${max.toFixed(2)}`;
  };

  // 获取商品变体数量
  const getVariantCount = (product: PrintifyProduct) => {
    return product.variants.filter(v => v.is_enabled).length;
  };

  // 查看商品详情
  const handleViewProduct = (product: PrintifyProduct) => {
    setSelectedProduct(product);
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
    setSelectedProductIds(new Set(filteredProducts.map(p => p.id)));
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
                      onClick={() => setSelectedStore(store)}
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

          {/* 搜索和过滤 */}
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                <TextField
                  fullWidth
                  placeholder='搜索商品名称、描述或标签...'
                  value={searchTerm}
                  onChange={e => setSearchTerm(e.target.value)}
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position='start'>
                        <SearchIcon />
                      </InputAdornment>
                    ),
                  }}
                />
                <Chip
                  icon={<FilterIcon />}
                  label={`${filteredProducts.length} 个商品`}
                  color='primary'
                  variant='outlined'
                />
                <Typography variant='body2' color='text.secondary' sx={{ whiteSpace: 'nowrap' }}>
                  发布状态:
                </Typography>
                <Chip
                  label='全部'
                  size='small'
                  onClick={() => setPublishedFilter('all')}
                  color={publishedFilter === 'all' ? 'primary' : 'default'}
                  variant={publishedFilter === 'all' ? 'filled' : 'outlined'}
                />
                <Chip
                  label='已发布'
                  size='small'
                  onClick={() => setPublishedFilter('published')}
                  color={publishedFilter === 'published' ? 'primary' : 'default'}
                  variant={publishedFilter === 'published' ? 'filled' : 'outlined'}
                />
                <Chip
                  label='未发布'
                  size='small'
                  onClick={() => setPublishedFilter('unpublished')}
                  color={publishedFilter === 'unpublished' ? 'primary' : 'default'}
                  variant={publishedFilter === 'unpublished' ? 'filled' : 'outlined'}
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
                    全选全部（{filteredProducts.length} 个）
                  </Button>
                  <Button
                    size='small'
                    variant='outlined'
                    onClick={clearSelection}
                    disabled={
                      selectedProductIds.size === 0 || batchSyncing
                    }
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
                    disabled={
                      batchSyncing || selectedProductIds.size === 0
                    }
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
                      {searchTerm ? '没有找到匹配的商品' : '该店铺暂无商品'}
                    </Typography>
                    {searchTerm && (
                      <Button
                        variant='outlined'
                        onClick={() => setSearchTerm('')}
                        sx={{ mt: 2 }}
                      >
                        清除搜索条件
                      </Button>
                    )}
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
                            }}
                          >
                            <Chip
                              label={product.is_published ? '已发布' : '未发布'}
                              size='small'
                              color={product.is_published ? 'success' : 'default'}
                              variant='filled'
                              sx={{ opacity: 0.95 }}
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
                              sx={{ bgcolor: 'background.paper', borderRadius: 1 }}
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
                              maxWidth: { xs: '150px', sm: '180px', md: '200px' },
                              display: 'block',
                              margin: '0 auto'
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
                                {product.description}
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
                              <Badge
                                badgeContent={getVariantCount(product)}
                                color='secondary'
                              >
                                <InventoryIcon color='action' />
                              </Badge>
                            </Box>

                            <Box sx={{ display: 'flex', gap: 1, mt: 'auto' }}>
                              <Button
                                variant='outlined'
                                size='small'
                                startIcon={<ViewIcon />}
                                onClick={() => handleViewProduct(product)}
                                fullWidth
                              >
                                查看详情
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
                  {/* 商品图片 */}
                  <Box sx={{ mb: 3, textAlign: 'center' }}>
                    <img
                      src={getProductImage(selectedProduct)}
                      alt={selectedProduct.title}
                      style={{
                        maxWidth: '100%',
                        maxHeight: '300px',
                        objectFit: 'contain',
                        borderRadius: '8px',
                      }}
                    />
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
                      >
                        {selectedProduct.description || '暂无描述'}
                      </Typography>

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
                      <TableContainer component={Paper} variant='outlined'>
                        <Table size='small'>
                          <TableHead>
                            <TableRow>
                              <TableCell>SKU</TableCell>
                              <TableCell>价格</TableCell>
                              <TableCell>状态</TableCell>
                            </TableRow>
                          </TableHead>
                          <TableBody>
                            {selectedProduct.variants
                              .filter(variant => variant.is_enabled)
                              .slice(0, 10)
                              .map(variant => (
                                <TableRow key={variant.id}>
                                  <TableCell>{variant.sku}</TableCell>
                                  <TableCell>${(variant.price / 100).toFixed(2)}</TableCell>
                                  <TableCell>
                                    <Chip
                                      label='启用'
                                      color='success'
                                      size='small'
                                    />
                                  </TableCell>
                                </TableRow>
                              ))}
                            {selectedProduct.variants.filter(v => v.is_enabled)
                              .length > 10 && (
                              <TableRow>
                                <TableCell colSpan={3} align='center'>
                                  ... 还有{' '}
                                  {selectedProduct.variants.filter(
                                    v => v.is_enabled
                                  ).length - 10}{' '}
                                  个启用的变体
                                </TableCell>
                              </TableRow>
                            )}
                            {selectedProduct.variants.filter(v => v.is_enabled)
                              .length === 0 && (
                              <TableRow>
                                <TableCell colSpan={3} align='center'>
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
        </Box>
      </DashboardLayout>
    </ProtectedRoute>
  );
}

export default PrintifyProductsPage;
