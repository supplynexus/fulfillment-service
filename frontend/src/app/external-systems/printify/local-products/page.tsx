'use client';

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Chip,
  Button,
  Alert,
  CircularProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  InputAdornment,
  FormControl,
  Select,
  MenuItem,
} from '@mui/material';
import {
  Storage as DatabaseIcon,
  Search as SearchIcon,
  Refresh as RefreshIcon,
  Visibility as ViewIcon,
  Link as LinkIcon,
  LinkOff as LinkOffIcon,
  OpenInNew as OpenInNewIcon,
} from '@mui/icons-material';

import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { frontendApi } from '@/lib/api';
import { frontendLogger } from '@/lib/frontend-logger';

const MAPPING_QUERY_LIMIT = 100;
const EXTERNAL_PRODUCT_IDS_BATCH_SIZE = 20;

interface PrintifyStore {
  id_hashid: string;
  name: string;
  system_type: string;
  is_active: boolean;
}

interface LocalPrintifyProduct {
  id: number;
  id_hashid: string;
  printify_product_id: string;
  printify_shop_id?: string;
  title: string;
  description?: string;
  tags?: string[];
  visible: boolean;
  is_locked: boolean;
  is_published?: boolean;
  sync_status: string;
  sync_error?: string;
  last_synced_at?: string;
  updated_at?: string;
  variants?: Array<{ id: number; sku?: string }>;
  sales_channel_properties?: unknown;
  raw_data?: {
    sales_channel_properties?: unknown;
  };
}

interface ProductMapping {
  id_hashid: string;
  external_product_id: string;
  sync_status: string;
  core_product_title: string;
  core_variant_sku: string | null;
}

const hasSalesChannelPublication = (value: unknown): boolean => {
  if (value == null) return false;
  if (Array.isArray(value)) return value.length > 0;
  if (typeof value === 'object') return Object.keys(value as Record<string, unknown>).length > 0;
  return false;
};

const isProductPublished = (product: LocalPrintifyProduct): boolean => {
  const salesChannelProps =
    product.sales_channel_properties ?? product.raw_data?.sales_channel_properties;

  // For Printify + Shopify, real publish signal is whether sales_channel_properties exists and is non-empty.
  if (salesChannelProps !== undefined) {
    return hasSalesChannelPublication(salesChannelProps);
  }

  // Fallback for older/local data shapes.
  if (typeof product.is_published === 'boolean') {
    return product.is_published;
  }
  return Boolean(product.visible);
};

function PrintifyLocalProductsPage() {
  const [stores, setStores] = useState<PrintifyStore[]>([]);
  const [selectedStore, setSelectedStore] = useState<PrintifyStore | null>(null);

  const [products, setProducts] = useState<LocalPrintifyProduct[]>([]);
  const [mappingsByExternalProductId, setMappingsByExternalProductId] = useState<
    Record<string, ProductMapping[]>
  >({});

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [publishedFilter, setPublishedFilter] = useState<
    'all' | 'published' | 'unpublished'
  >('all');
  const [bindingFilter, setBindingFilter] = useState<'all' | 'bound' | 'unbound'>(
    'all'
  );
  const [syncFilter, setSyncFilter] = useState<
    'all' | 'success' | 'failed' | 'pending'
  >('all');

  const [detailOpen, setDetailOpen] = useState(false);
  const [selectedProduct, setSelectedProduct] =
    useState<LocalPrintifyProduct | null>(null);

  const fetchStores = useCallback(async () => {
    const response = await frontendApi.get('/api/external-systems?system_type=printify');
    const printifyStores = (response.data?.external_systems || []).filter(
      (store: any) => store.system_type === 'PRINTIFY' && store.is_active
    ) as PrintifyStore[];
    setStores(printifyStores);
    if (printifyStores.length > 0) {
      setSelectedStore(printifyStores[0]);
    }
  }, []);

  const fetchMappingsForProducts = useCallback(async (externalProductIds: string[]) => {
    if (externalProductIds.length === 0) {
      setMappingsByExternalProductId({});
      return;
    }

    const uniqueExternalProductIds = Array.from(new Set(externalProductIds));
    const allRows: ProductMapping[] = [];

    for (
      let i = 0;
      i < uniqueExternalProductIds.length;
      i += EXTERNAL_PRODUCT_IDS_BATCH_SIZE
    ) {
      const idBatch = uniqueExternalProductIds.slice(
        i,
        i + EXTERNAL_PRODUCT_IDS_BATCH_SIZE
      );
      let page = 1;
      let hasMore = true;

      while (hasMore) {
        const response = await frontendApi.get('/api/products/mappings/', {
          params: {
            page,
            limit: MAPPING_QUERY_LIMIT,
            system_type: 'PRINTIFY',
            external_product_ids: idBatch.join(','),
          },
        });

        const rows = (response.data?.mappings || []) as ProductMapping[];
        allRows.push(...rows);

        const totalPages = Number(response.data?.pagination?.pages || 0);
        if (totalPages > 0) {
          hasMore = page < totalPages;
        } else {
          hasMore = rows.length >= MAPPING_QUERY_LIMIT;
        }
        page += 1;
      }
    }

    const grouped: Record<string, ProductMapping[]> = {};
    allRows.forEach(row => {
      if (!grouped[row.external_product_id]) {
        grouped[row.external_product_id] = [];
      }
      grouped[row.external_product_id].push(row);
    });
    setMappingsByExternalProductId(grouped);
  }, []);

  const fetchProducts = useCallback(
    async (store: PrintifyStore) => {
      const productResponse = await frontendApi.get('/api/printify-products/', {
        params: {
          external_system_id: store.id_hashid,
          limit: 100,
          offset: 0,
          visible_only: true,
        },
      });

      const list = (productResponse.data?.products || []) as LocalPrintifyProduct[];
      setProducts(list);

      await fetchMappingsForProducts(list.map(p => p.printify_product_id));
    },
    [fetchMappingsForProducts]
  );

  const loadAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      await fetchStores();
    } catch (e) {
      frontendLogger.error('❌ 初始化 Printify 本地商品页面失败', {
        error: String(e),
      });
      setError('初始化失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  }, [fetchStores]);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  useEffect(() => {
    if (!selectedStore) return;
    const run = async () => {
      setLoading(true);
      setError(null);
      try {
        await fetchProducts(selectedStore);
      } catch (e) {
        frontendLogger.error('❌ 获取 Printify 本地商品失败', {
          error: String(e),
          storeId: selectedStore.id_hashid,
        });
        setError('获取本地商品失败');
      } finally {
        setLoading(false);
      }
    };
    run();
  }, [selectedStore, fetchProducts]);

  const handleRefresh = useCallback(async () => {
    if (!selectedStore) return;
    setRefreshing(true);
    setError(null);
    try {
      await fetchProducts(selectedStore);
    } catch (e) {
      frontendLogger.error('❌ 刷新 Printify 本地商品失败', {
        error: String(e),
        storeId: selectedStore.id_hashid,
      });
      setError('刷新失败');
    } finally {
      setRefreshing(false);
    }
  }, [selectedStore, fetchProducts]);

  const filteredProducts = useMemo(() => {
    const kw = searchTerm.trim().toLowerCase();
    let list = [...products];

    if (kw) {
      list = list.filter(
        p =>
          p.title.toLowerCase().includes(kw) ||
          p.printify_product_id.toLowerCase().includes(kw) ||
          (p.tags || []).some(tag => tag.toLowerCase().includes(kw))
      );
    }

    if (publishedFilter === 'published') {
      list = list.filter(p => isProductPublished(p));
    } else if (publishedFilter === 'unpublished') {
      list = list.filter(p => !isProductPublished(p));
    }

    if (bindingFilter === 'bound') {
      list = list.filter(p => (mappingsByExternalProductId[p.printify_product_id] || []).length > 0);
    } else if (bindingFilter === 'unbound') {
      list = list.filter(p => (mappingsByExternalProductId[p.printify_product_id] || []).length === 0);
    }

    if (syncFilter !== 'all') {
      list = list.filter(p => (p.sync_status || '').toLowerCase() === syncFilter);
    }

    return list;
  }, [
    products,
    searchTerm,
    publishedFilter,
    bindingFilter,
    syncFilter,
    mappingsByExternalProductId,
  ]);

  const mappingCount = (product: LocalPrintifyProduct) =>
    mappingsByExternalProductId[product.printify_product_id]?.length || 0;

  const hasBinding = (product: LocalPrintifyProduct) => mappingCount(product) > 0;

  const getRealtimeDetailPath = (product: LocalPrintifyProduct) => {
    if (!selectedStore) return '';
    return `/external-systems/printify/products/${selectedStore.id_hashid}/${product.printify_product_id}`;
  };

  const getExternalPrintifyProductUrl = (product: LocalPrintifyProduct) =>
    `https://printify.com/app/product-details/${product.printify_product_id}?fromProductsPage=1`;

  return (
    <ProtectedRoute>
      <DashboardLayout>
        <Box sx={{ p: 3 }}>
          <Box
            sx={{
              mb: 3,
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              gap: 2,
              flexWrap: 'wrap',
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <DatabaseIcon color='primary' />
              <Box>
                <Typography variant='h4' component='h1'>
                  Printify 本地商品（数据库）
                </Typography>
                <Typography variant='body2' color='text.secondary'>
                  查看已落库的 Printify 商品，并检查与核心商品绑定情况
                </Typography>
              </Box>
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

          {stores.length > 0 && (
            <Card sx={{ mb: 2 }}>
              <CardContent>
                <Typography variant='h6' gutterBottom>
                  选择店铺
                </Typography>
                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                  {stores.map(store => (
                    <Chip
                      key={store.id_hashid}
                      label={store.name}
                      onClick={() => setSelectedStore(store)}
                      color={
                        selectedStore?.id_hashid === store.id_hashid
                          ? 'primary'
                          : 'default'
                      }
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

          <Card sx={{ mb: 2 }}>
            <CardContent>
              <Box
                sx={{
                  display: 'flex',
                  gap: 2,
                  flexWrap: 'wrap',
                  alignItems: 'center',
                }}
              >
                <TextField
                  sx={{ flex: 1, minWidth: 260 }}
                  placeholder='按标题 / Printify Product ID / 标签检索'
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
                <FormControl size='small' sx={{ minWidth: 120 }}>
                  <Select
                    value={publishedFilter}
                    onChange={e =>
                      setPublishedFilter(
                        e.target.value as 'all' | 'published' | 'unpublished'
                      )
                    }
                  >
                    <MenuItem value='all'>发布：全部</MenuItem>
                    <MenuItem value='published'>发布：已发布</MenuItem>
                    <MenuItem value='unpublished'>发布：未发布</MenuItem>
                  </Select>
                </FormControl>
                <FormControl size='small' sx={{ minWidth: 120 }}>
                  <Select
                    value={bindingFilter}
                    onChange={e =>
                      setBindingFilter(e.target.value as 'all' | 'bound' | 'unbound')
                    }
                  >
                    <MenuItem value='all'>绑定：全部</MenuItem>
                    <MenuItem value='bound'>绑定：已绑定</MenuItem>
                    <MenuItem value='unbound'>绑定：未绑定</MenuItem>
                  </Select>
                </FormControl>
                <FormControl size='small' sx={{ minWidth: 120 }}>
                  <Select
                    value={syncFilter}
                    onChange={e =>
                      setSyncFilter(
                        e.target.value as 'all' | 'success' | 'failed' | 'pending'
                      )
                    }
                  >
                    <MenuItem value='all'>同步：全部</MenuItem>
                    <MenuItem value='success'>同步：成功</MenuItem>
                    <MenuItem value='pending'>同步：待处理</MenuItem>
                    <MenuItem value='failed'>同步：失败</MenuItem>
                  </Select>
                </FormControl>
              </Box>
            </CardContent>
          </Card>

          {error && (
            <Alert severity='error' sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          {loading ? (
            <Box sx={{ py: 6, display: 'flex', justifyContent: 'center' }}>
              <CircularProgress />
            </Box>
          ) : (
            <Card>
              <CardContent>
                <Typography variant='h6' sx={{ mb: 2 }}>
                  本地商品列表（{filteredProducts.length}）
                </Typography>
                <TableContainer component={Paper} variant='outlined'>
                  <Table size='small'>
                    <TableHead>
                      <TableRow>
                        <TableCell>标题</TableCell>
                        <TableCell>序号</TableCell>
                        <TableCell>同步状态</TableCell>
                        <TableCell>发布状态</TableCell>
                        <TableCell>核心绑定</TableCell>
                        <TableCell>链接</TableCell>
                        <TableCell>操作</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {filteredProducts.map((product, index) => (
                        <TableRow key={product.id_hashid} hover>
                          <TableCell>
                            <Typography variant='body2' fontWeight={600}>
                              {product.title}
                            </Typography>
                            <Typography variant='caption' color='text.secondary'>
                              变体数：{product.variants?.length || 0}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Typography variant='body2'>#{index + 1}</Typography>
                          </TableCell>
                          <TableCell>
                            <Chip
                              size='small'
                              label={product.sync_status || 'unknown'}
                              color={
                                product.sync_status === 'success'
                                  ? 'success'
                                  : product.sync_status === 'failed'
                                    ? 'error'
                                    : 'default'
                              }
                            />
                          </TableCell>
                          <TableCell>
                            <Chip
                              size='small'
                              label={isProductPublished(product) ? '已发布' : '未发布'}
                              color={isProductPublished(product) ? 'success' : 'default'}
                              variant={isProductPublished(product) ? 'filled' : 'outlined'}
                            />
                          </TableCell>
                          <TableCell>
                            {hasBinding(product) ? (
                              <Chip
                                size='small'
                                icon={<LinkIcon />}
                                label={`已绑定 ${mappingCount(product)} 条`}
                                color='success'
                                variant='outlined'
                              />
                            ) : (
                              <Chip
                                size='small'
                                icon={<LinkOffIcon />}
                                label='未绑定'
                                variant='outlined'
                              />
                            )}
                          </TableCell>
                          <TableCell>
                            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                              <Button
                                size='small'
                                variant='outlined'
                                component='a'
                                href={getExternalPrintifyProductUrl(product)}
                                target='_blank'
                                rel='noopener noreferrer'
                                startIcon={<OpenInNewIcon />}
                              >
                                外部 Printify
                              </Button>
                              <Button
                                size='small'
                                variant='outlined'
                                component='a'
                                href={getRealtimeDetailPath(product)}
                                disabled={!selectedStore}
                                startIcon={<LinkIcon />}
                              >
                                系统详情页
                              </Button>
                              <Button
                                size='small'
                                variant='contained'
                                component='a'
                                href={`/product-mapping/printify?printify_product_id=${encodeURIComponent(product.printify_product_id)}`}
                                startIcon={<LinkIcon />}
                              >
                                去绑定
                              </Button>
                            </Box>
                          </TableCell>
                          <TableCell>
                            <Button
                              size='small'
                              variant='outlined'
                              startIcon={<ViewIcon />}
                              onClick={() => {
                                setSelectedProduct(product);
                                setDetailOpen(true);
                              }}
                            >
                              查看详情
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                      {filteredProducts.length === 0 && (
                        <TableRow>
                          <TableCell colSpan={7} align='center'>
                            暂无数据
                          </TableCell>
                        </TableRow>
                      )}
                    </TableBody>
                  </Table>
                </TableContainer>
              </CardContent>
            </Card>
          )}

          <Dialog
            open={detailOpen}
            onClose={() => setDetailOpen(false)}
            maxWidth='md'
            fullWidth
          >
            <DialogTitle>本地商品详情</DialogTitle>
            <DialogContent>
              {selectedProduct && (
                <Box sx={{ mt: 1, display: 'grid', gap: 1.5 }}>
                  <Typography variant='subtitle1' fontWeight={700}>
                    {selectedProduct.title}
                  </Typography>
                  <Typography variant='body2'>
                    <strong>Printify Product ID：</strong>
                    {selectedProduct.printify_product_id}
                  </Typography>
                  <Typography variant='body2'>
                    <strong>同步状态：</strong>
                    {selectedProduct.sync_status || '-'}
                  </Typography>
                  <Typography variant='body2'>
                    <strong>最后同步时间：</strong>
                    {selectedProduct.last_synced_at || '-'}
                  </Typography>

                  <Box sx={{ mt: 1 }}>
                    <Typography variant='subtitle2' sx={{ mb: 1 }}>
                      核心商品绑定信息
                    </Typography>
                    {(mappingsByExternalProductId[selectedProduct.printify_product_id] || [])
                      .length === 0 ? (
                      <Alert severity='warning'>当前商品未绑定核心商品</Alert>
                    ) : (
                      <TableContainer component={Paper} variant='outlined'>
                        <Table size='small'>
                          <TableHead>
                            <TableRow>
                              <TableCell>核心商品</TableCell>
                              <TableCell>核心变体 SKU</TableCell>
                              <TableCell>映射状态</TableCell>
                            </TableRow>
                          </TableHead>
                          <TableBody>
                            {(
                              mappingsByExternalProductId[
                                selectedProduct.printify_product_id
                              ] || []
                            ).map(mapping => (
                              <TableRow key={mapping.id_hashid}>
                                <TableCell>{mapping.core_product_title}</TableCell>
                                <TableCell>
                                  {mapping.core_variant_sku || '-'}
                                </TableCell>
                                <TableCell>{mapping.sync_status}</TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      </TableContainer>
                    )}
                  </Box>
                </Box>
              )}
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setDetailOpen(false)}>关闭</Button>
            </DialogActions>
          </Dialog>
        </Box>
      </DashboardLayout>
    </ProtectedRoute>
  );
}

export default PrintifyLocalProductsPage;
