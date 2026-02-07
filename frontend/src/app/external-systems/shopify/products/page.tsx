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
  Stack,
  Divider,
  MenuItem,
  FormControl,
  Select,
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
  Store as StoreIcon,
  TrendingUp as TrendingUpIcon,
  LocalShipping as ShippingIcon,
  CheckCircle as ActiveIcon,
  Cancel as InactiveIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Sync as SyncIcon,
  Link as LinkIcon,
} from '@mui/icons-material';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { frontendApi } from '@/lib/api';
import { frontendLogger } from '@/lib/frontend-logger';

interface ShopifyProduct {
  id: string;
  title: string;
  handle: string;
  status: string;
  created_at: string;
  updated_at: string;
  total_inventory: number;
  price: string;
  currency: string;
  vendor?: string;
  product_type?: string;
  published_at?: string;
  tags?: string;
  variants?: ShopifyVariant[];
  image?: {
    id: string;
    url: string;
    alt_text?: string;
    width?: number;
    height?: number;
  };
  variant?: {
    id: string;
    title: string;
    price: string;
    inventory_quantity: number;
    image?: {
      id: string;
      url: string;
      alt_text?: string;
    };
  };
}

interface ShopifyVariant {
  id: string; // GraphQL ID like "gid://shopify/ProductVariant/45663476547684"
  title: string;
  sku: string;
  barcode?: string;
  price: string;
  compareAtPrice?: string;
  inventoryQuantity: number;
  inventoryPolicy: string;
  selectedOptions: Array<{
    name: string;
    value: string;
  }>;
  taxable: boolean;
  taxCode: string;
  position: number;
  createdAt: string;
  updatedAt: string;
  weight?: number;
  weightUnit?: string;
  image?: {
    id: string;
    url: string;
    altText?: string;
    width?: number;
    height?: number;
  };
}

interface ShopifyOption {
  id: number;
  product_id: number;
  name: string;
  position: number;
  values: string[];
}

interface ShopifyImage {
  id: number;
  shopify_id: string;
  product_id: number;
  position: number;
  created_at: string;
  updated_at: string;
  alt: string;
  width: number;
  height: number;
  src: string;
  variant_ids: number[];
  admin_graphql_api_id: string;
}

interface ShopifyStore {
  id: number;
  id_hashid: string;
  name: string;
  external_system_id: string;
  shop_domain: string;
  access_token: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

const ShopifyProductsPage: React.FC = () => {
  const [products, setProducts] = useState<ShopifyProduct[]>([]);
  const [stores, setStores] = useState<ShopifyStore[]>([]);
  const [selectedStore, setSelectedStore] = useState<ShopifyStore | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [selectedProduct, setSelectedProduct] = useState<ShopifyProduct | null>(
    null
  );
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [jsonModalOpen, setJsonModalOpen] = useState(false);
  const [productJson, setProductJson] = useState<any>(null);
  const [loadingJson, setLoadingJson] = useState(false);
  const [sortBy, setSortBy] = useState<
    'title' | 'created_at' | 'updated_at' | 'price'
  >('title');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [syncingToDatabase, setSyncingToDatabase] = useState(false);
  const [syncSuccess, setSyncSuccess] = useState(false);
  const [checkingMapping, setCheckingMapping] = useState(false);
  const [mappingResult, setMappingResult] = useState<any>(null);
  const [syncingAll, setSyncingAll] = useState(false);
  const [syncAllProgress, setSyncAllProgress] = useState<string | null>(null);
  /** IDs of Shopify products that are already in external_products (gid://shopify/Product/...) */
  const [syncedProductIds, setSyncedProductIds] = useState<Set<string>>(new Set());

  // 获取当前店铺已同步到数据库的商品 ID 列表（用于卡片显示「已同步」）
  const fetchSyncedProductIds = useCallback(async (store: ShopifyStore | null) => {
    if (!store) {
      setSyncedProductIds(new Set());
      return;
    }
    try {
      const ids = new Set<string>();
      const limit = 100;
      let pageNum = 1;
      let total = 0;
      do {
        const res = await frontendApi.get('/api/external-products/', {
          params: { external_system_id: store.id, page: pageNum, limit },
        });
        const list = res.data?.products ?? [];
        total = res.data?.total ?? 0;
        list.forEach((p: { external_product_id?: string }) => {
          if (p.external_product_id) ids.add(p.external_product_id);
        });
        pageNum += 1;
      } while ((pageNum - 1) * limit < total);
      setSyncedProductIds(ids);
    } catch (_) {
      setSyncedProductIds(new Set());
    }
  }, []);

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

  // 获取 Shopify 商品完整 JSON 数据
  const fetchProductJson = useCallback(
    async (productId: string, showJsonModal: boolean = true) => {
      if (!selectedStore) return;

      try {
        setLoadingJson(true);

        // 从 GraphQL ID 中提取纯数字 ID (例如: gid://shopify/Product/8040175042660 -> 8040175042660)
        const numericProductId = productId.replace(
          'gid://shopify/Product/',
          ''
        );

        frontendLogger.info('🔄 获取 Shopify 商品完整 JSON 数据', {
          originalId: productId,
          numericId: numericProductId,
          storeId: selectedStore.id_hashid,
          storeName: selectedStore.name,
        });

        const response = await frontendApi.get(
          `/api/external-systems/shopify/products/${numericProductId}/json?external_system_hashid=${selectedStore.id_hashid}`
        );

        frontendLogger.info('✅ Shopify 商品 JSON 数据获取成功', {
          productId,
          hasData: !!response.data,
        });

        // 设置完整的商品JSON数据
        setProductJson(response.data);

        // 更新selectedProduct的变体数据
        if (response.data?.product?.variants?.edges) {
          const variants = response.data.product.variants.edges.map(
            (edge: any) => edge.node
          );
          setSelectedProduct(prev =>
            prev
              ? {
                  ...prev,
                  variants: variants,
                }
              : null
          );

          frontendLogger.info('✅ 商品变体数据已更新', {
            variantCount: variants.length,
            variants: variants.map((v: any) => ({ id: v.id, title: v.title })),
          });
        }

        if (showJsonModal) {
          setJsonModalOpen(true);
        }
      } catch (error: any) {
        frontendLogger.error('❌ 获取 Shopify 商品 JSON 数据失败', {
          error: error.message,
          productId,
        });
        setError(`获取商品 JSON 数据失败: ${error.message}`);
      } finally {
        setLoadingJson(false);
      }
    },
    [selectedStore]
  );

  // 检查商品映射
  const checkProductMapping = useCallback(async () => {
    if (!selectedProduct || !selectedStore) return;

    try {
      setCheckingMapping(true);
      setMappingResult(null);

      frontendLogger.info('🔍 检查Shopify商品映射', {
        productId: selectedProduct.id,
        productName: selectedProduct.title,
        storeId: selectedStore.id_hashid,
      });

      // 从 GraphQL ID 中提取纯数字 ID
      const numericProductId = selectedProduct.id.replace(
        'gid://shopify/Product/',
        ''
      );

      const response = await frontendApi.get(
        `/api/external-systems/shopify/${selectedStore.id_hashid}/products/${numericProductId}/check-mapping`
      );

      frontendLogger.info('✅ 商品映射检查完成', {
        productId: selectedProduct.id,
        isMapped: response.data.is_mapped,
        mappingCount: response.data.mapping_count,
        fullResponse: response.data,
      });

      setMappingResult(response.data);
      setError(null);

      // 调试信息
      frontendLogger.info('🔍 设置映射结果状态', {
        mappingResult: response.data,
        isMapped: response.data.is_mapped,
        message: response.data.message,
      });
    } catch (error: any) {
      frontendLogger.error('❌ 检查商品映射失败', {
        error: error.message,
        productId: selectedProduct.id,
      });
      setError(error.message || '检查商品映射失败');
    } finally {
      setCheckingMapping(false);
    }
  }, [selectedProduct, selectedStore]);

  // 同步商品到数据库
  const syncProductToDatabase = useCallback(async () => {
    if (!selectedProduct || !selectedStore) return;

    try {
      setSyncingToDatabase(true);

      frontendLogger.info('🔄 同步 Shopify 商品到数据库', {
        productId: selectedProduct.id,
        productName: selectedProduct.title,
        storeId: selectedStore.id_hashid,
      });

      let productToSync = selectedProduct;
      let rawDataToSync = productJson ?? {};

      // 若弹窗内没有变体数据，先拉取完整商品再保存
      if (!productToSync.variants?.length && selectedStore.id_hashid) {
        const numericProductId = productToSync.id.replace('gid://shopify/Product/', '');
        const res = await frontendApi.get(
          `/api/external-systems/shopify/products/${numericProductId}/json?external_system_hashid=${selectedStore.id_hashid}`
        );
        rawDataToSync = res.data ?? {};
        if (res.data?.product?.variants?.edges?.length) {
          productToSync = {
            ...productToSync,
            variants: res.data.product.variants.edges.map((edge: any) => edge.node),
          };
        }
      }

      const productData = {
        external_system_id: selectedStore.id,
        external_product_id: productToSync.id,
        product_name: productToSync.title,
        product_type: productToSync.product_type || '',
        vendor: productToSync.vendor || '',
        status: productToSync.status,
        tags: productToSync.tags
          ? productToSync.tags.split(',').map((tag: string) => tag.trim())
          : [],
        raw_data: rawDataToSync,
        variants:
          productToSync.variants?.map((variant: ShopifyVariant) => ({
            external_variant_id: variant.id,
            title: variant.title,
            // 避免空 SKU：Shopify 未填时用变体 ID 占位，防止 (tenant_id, sku) 唯一约束冲突
            sku:
              variant.sku?.trim() ||
              variant.id?.replace('gid://shopify/ProductVariant/', '') ||
              `VAR-${productToSync.id?.replace('gid://shopify/Product/', '')}-${variant.id?.replace('gid://shopify/ProductVariant/', '')}`,
            price: parseFloat(variant.price) || 0,
            compare_at_price: variant.compareAtPrice
              ? parseFloat(variant.compareAtPrice)
              : null,
            inventory_quantity: variant.inventoryQuantity || 0,
            inventory_policy: variant.inventoryPolicy || 'deny',
            weight: variant.weight || 0,
            weight_unit: variant.weightUnit || 'kg',
            taxable: variant.taxable || false,
            tax_code: variant.taxCode || '',
            position: variant.position || 0,
            created_at: variant.createdAt,
            updated_at: variant.updatedAt,
            selected_options: variant.selectedOptions || [],
            image: variant.image
              ? {
                  id: variant.image.id,
                  url: variant.image.url,
                  alt_text: variant.image.altText || '',
                  width: variant.image.width || 0,
                  height: variant.image.height || 0,
                }
              : null,
          })) || [],
      };

      const response = await frontendApi.post(
        '/api/external-products/',
        productData
      );

      frontendLogger.info('✅ Shopify 商品同步到数据库成功', {
        productId: selectedProduct.id,
        savedProductId: response.data.id,
      });

      setError(null);
      setSyncSuccess(true);
      fetchSyncedProductIds(selectedStore);
      setTimeout(() => {
        setSyncSuccess(false);
      }, 3000);
    } catch (error: any) {
      frontendLogger.error('❌ 同步商品到数据库失败', {
        error: error.message,
        productId: selectedProduct.id,
      });
      setError(error.message || '同步商品到数据库失败');
    } finally {
      setSyncingToDatabase(false);
    }
  }, [selectedProduct, selectedStore, productJson, fetchSyncedProductIds]);

  // 全量同步当前店铺商品到数据库（external_products）
  const syncAllProductsToDatabase = useCallback(async () => {
    if (!selectedStore) return;
    try {
      setSyncingAll(true);
      setSyncAllProgress('正在获取商品列表...');
      setError(null);
      const allProducts: ShopifyProduct[] = [];
      let pageNum = 1;
      let totalPages = 1;
      do {
        const response = await frontendApi.get(
          `/api/external-systems/shopify/${selectedStore.id_hashid}/products`,
          {
            params: {
              page: pageNum,
              limit: 100,
              sort_by: sortBy,
              sort_order: sortOrder,
              status: statusFilter !== 'all' ? statusFilter : undefined,
            },
          }
        );
        const list = response.data.products || [];
        allProducts.push(...list);
        totalPages = response.data.pagination?.total_pages || 1;
        pageNum += 1;
      } while (pageNum <= totalPages);

      const total = allProducts.length;
      if (total === 0) {
        setSyncAllProgress('当前无商品可同步');
        setSyncingAll(false);
        return;
      }

      let done = 0;
      let failed = 0;
      for (let i = 0; i < allProducts.length; i++) {
        const product = allProducts[i];
        setSyncAllProgress(`正在同步 ${i + 1}/${total}: ${product.title?.slice(0, 30)}...`);
        try {
          const numericId = product.id.replace('gid://shopify/Product/', '');
          const jsonRes = await frontendApi.get(
            `/api/external-systems/shopify/products/${numericId}/json?external_system_hashid=${selectedStore.id_hashid}`
          );
          const data = jsonRes.data;
          const node = data?.product;
          if (!node) {
            failed += 1;
            continue;
          }
          const edges = node.variants?.edges || [];
          const variants = edges.map((edge: any) => {
            const v = edge.node;
            return {
              external_variant_id: v.id,
              title: v.title,
              sku:
                v.sku?.trim() ||
                v.id?.replace('gid://shopify/ProductVariant/', '') ||
                `VAR-${node.id?.replace('gid://shopify/Product/', '')}-${v.id?.replace('gid://shopify/ProductVariant/', '')}`,
              price: parseFloat(v.price) || 0,
              compare_at_price: v.compareAtPrice ? parseFloat(v.compareAtPrice) : null,
              inventory_quantity: v.inventoryQuantity ?? 0,
              inventory_policy: v.inventoryPolicy || 'deny',
              weight: v.weight || 0,
              weight_unit: v.weightUnit || 'kg',
              taxable: v.taxable ?? false,
              tax_code: v.taxCode || '',
              position: v.position || 0,
              created_at: v.createdAt,
              updated_at: v.updatedAt,
              selected_options: v.selectedOptions || [],
              image: v.image ? { id: v.image.id, url: v.image.url, alt_text: v.image.altText || '', width: v.image.width || 0, height: v.image.height || 0 } : null,
            };
          });
          const productData = {
            external_system_id: selectedStore.id,
            external_product_id: node.id,
            product_name: node.title,
            product_type: node.productType || '',
            vendor: node.vendor || '',
            status: node.status,
            tags: Array.isArray(node.tags) ? node.tags : [],
            raw_data: data,
            variants,
          };
          await frontendApi.post('/api/external-products/', productData);
          done += 1;
        } catch (err) {
          failed += 1;
          frontendLogger.error('全量同步单商品失败', { productId: product.id, error: (err as Error).message });
        }
      }

      setSyncAllProgress(null);
      setError(failed > 0 ? `同步完成：成功 ${done}，失败 ${failed}` : null);
      if (failed === 0) setSyncSuccess(true);
      fetchSyncedProductIds(selectedStore);
      setTimeout(() => setSyncSuccess(false), 3000);
      frontendLogger.info('✅ 全量同步完成', { total, done, failed });
    } catch (err: any) {
      setSyncAllProgress(null);
      setError(err.message || '全量同步失败');
      frontendLogger.error('❌ 全量同步失败', { error: err.message });
    } finally {
      setSyncingAll(false);
    }
  }, [selectedStore, sortBy, sortOrder, statusFilter, fetchSyncedProductIds]);

  // 获取 Shopify 商品列表
  const fetchProducts = useCallback(
    async (store: ShopifyStore, pageNum: number = 1) => {
      if (!store) return;

      setLoading(true);
      setError(null);

      try {
        frontendLogger.info('🔄 获取 Shopify 商品列表', {
          storeId: store.id_hashid,
          page: pageNum,
        });
        const response = await frontendApi.get(
          `/api/external-systems/shopify/${store.id_hashid}/products`,
          {
            params: {
              page: pageNum,
              limit: 20,
              search: searchTerm,
              sort_by: sortBy,
              sort_order: sortOrder,
              status: statusFilter !== 'all' ? statusFilter : undefined,
            },
          }
        );

        setProducts(response.data.products || []);
        setTotalPages(response.data.pagination?.total_pages || 1);
        setPage(pageNum);

        frontendLogger.info('✅ Shopify 商品列表获取成功', {
          count: response.data.products?.length || 0,
          totalPages: response.data.pagination?.total_pages || 1,
        });
      } catch (error: any) {
        frontendLogger.error('❌ 获取 Shopify 商品列表失败', {
          error: error.message,
        });
        setError('获取商品列表失败');
      } finally {
        setLoading(false);
      }
    },
    [searchTerm, sortBy, sortOrder, statusFilter]
  );

  // 初始化
  useEffect(() => {
    fetchStores();
  }, [fetchStores]);

  // 当选择店铺时获取商品
  useEffect(() => {
    if (selectedStore) {
      fetchProducts(selectedStore, 1);
    }
  }, [selectedStore, fetchProducts]);

  // 当选择店铺时拉取已同步到数据库的商品 ID，用于卡片显示「已同步」
  useEffect(() => {
    fetchSyncedProductIds(selectedStore);
  }, [selectedStore, fetchSyncedProductIds]);

  // 搜索处理
  const handleSearch = useCallback(() => {
    if (selectedStore) {
      fetchProducts(selectedStore, 1);
    }
  }, [selectedStore, fetchProducts]);

  // 刷新数据
  const handleRefresh = useCallback(() => {
    if (selectedStore) {
      fetchProducts(selectedStore, page);
    }
  }, [selectedStore, fetchProducts, page]);

  // 查看商品详情
  const handleViewDetails = async (product: ShopifyProduct) => {
    setSelectedProduct(product);
    setDetailsOpen(true);

    // 自动获取完整的商品数据（包括变体）
    if (selectedStore) {
      try {
        frontendLogger.info('🔄 自动获取商品完整数据', {
          productId: product.id,
          storeId: selectedStore.id_hashid,
        });

        await fetchProductJson(product.id, false);
      } catch (error) {
        frontendLogger.error('❌ 自动获取商品数据失败', {
          error: error instanceof Error ? error.message : 'Unknown error',
          productId: product.id,
        });
      }
    }
  };

  // 格式化价格
  const formatPrice = (price: string) => {
    return `$${parseFloat(price).toFixed(2)}`;
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

  // 获取状态颜色
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'success';
      case 'draft':
        return 'warning';
      case 'archived':
        return 'error';
      default:
        return 'default';
    }
  };

  // 获取状态标签
  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'active':
        return '已发布';
      case 'draft':
        return '草稿';
      case 'archived':
        return '已归档';
      default:
        return status;
    }
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
            <Typography
              variant='h4'
              component='h1'
              sx={{ display: 'flex', alignItems: 'center', gap: 1 }}
            >
              <StoreIcon />
              Shopify 商品管理
            </Typography>
            <Button
              variant='contained'
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
              <Typography variant='h6' gutterBottom>
                选择店铺
              </Typography>
              <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                {stores.map(store => (
                  <Box sx={{ width: { xs: "100%", sm: "50%", md: "33.33%" } }} key={store.id}>
                    <Card
                      sx={{
                        cursor: 'pointer',
                        border: selectedStore?.id === store.id ? 2 : 1,
                        borderColor:
                          selectedStore?.id === store.id
                            ? 'primary.main'
                            : 'divider',
                        '&:hover': { borderColor: 'primary.main' },
                      }}
                      onClick={() => setSelectedStore(store)}
                    >
                      <CardContent>
                        <Box
                          sx={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: 1,
                            mb: 1,
                          }}
                        >
                          <StoreIcon />
                          <Typography variant='h6'>{store.name}</Typography>
                          <Chip
                            label={store.is_active ? '活跃' : '非活跃'}
                            color={store.is_active ? 'success' : 'default'}
                            size='small'
                          />
                        </Box>
                        <Typography variant='body2' color='text.secondary'>
                          {store.shop_domain}
                        </Typography>
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
                        placeholder='搜索商品...'
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
                      <TextField
                        select
                        fullWidth
                        label='排序'
                        value={sortBy}
                        onChange={e => setSortBy(e.target.value as any)}
                      >
                        <MenuItem value='title'>标题</MenuItem>
                        <MenuItem value='created_at'>创建时间</MenuItem>
                        <MenuItem value='updated_at'>更新时间</MenuItem>
                        <MenuItem value='price'>价格</MenuItem>
                      </TextField>
                    </Box>
                    <Box sx={{ width: { xs: "100%", md: "16.67%" } }}>
                      <TextField
                        select
                        fullWidth
                        label='状态'
                        value={statusFilter}
                        onChange={e => setStatusFilter(e.target.value)}
                      >
                        <MenuItem value='all'>全部</MenuItem>
                        <MenuItem value='active'>已发布</MenuItem>
                        <MenuItem value='draft'>草稿</MenuItem>
                        <MenuItem value='archived'>已归档</MenuItem>
                      </TextField>
                    </Box>
                    <Box sx={{ width: { xs: "100%", md: "16.67%" } }}>
                      <Button
                        fullWidth
                        variant='outlined'
                        onClick={() =>
                          setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
                        }
                        startIcon={<SortIcon />}
                      >
                        {sortOrder === 'asc' ? '升序' : '降序'}
                      </Button>
                    </Box>
                    <Box sx={{ width: { xs: "100%", md: "16.67%" } }}>
                      <Button
                        fullWidth
                        variant='contained'
                        onClick={handleSearch}
                        startIcon={<SearchIcon />}
                      >
                        搜索
                      </Button>
                    </Box>
                    <Box sx={{ width: { xs: "100%", md: "auto" } }}>
                      <Button
                        variant='outlined'
                        color='secondary'
                        onClick={syncAllProductsToDatabase}
                        disabled={!selectedStore || syncingAll}
                        startIcon={syncingAll ? <CircularProgress size={18} /> : <SyncIcon />}
                      >
                        {syncingAll && syncAllProgress ? syncAllProgress : '同步全部到数据库'}
                      </Button>
                    </Box>
                  </Box>
                  {syncingAll && syncAllProgress && (
                    <Alert severity='info' sx={{ mt: 2 }}>
                      {syncAllProgress}
                    </Alert>
                  )}
                  {selectedStore && syncedProductIds.size >= 0 && (
                    <Typography variant='body2' color='text.secondary' sx={{ mt: 1 }}>
                      已同步 <strong>{syncedProductIds.size}</strong> 个商品到数据库
                    </Typography>
                  )}
                </CardContent>
              </Card>

              {/* 商品列表 */}
              {loading ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
                  <CircularProgress />
                </Box>
              ) : error ? (
                <Alert severity='error' sx={{ mb: 2 }}>
                  {error}
                </Alert>
              ) : products.length === 0 ? (
                <Card>
                  <CardContent sx={{ textAlign: 'center', p: 4 }}>
                    <Typography variant='h6' color='text.secondary'>
                      暂无商品数据
                    </Typography>
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
                    {products.map(product => (
                      <Box key={product.id}>
                        <Card
                          sx={{
                            height: '100%',
                            display: 'flex',
                            flexDirection: 'column',
                          }}
                        >
                          <CardMedia
                            component='img'
                            image={
                              product.image?.url ||
                              product.variant?.image?.url ||
                              '/placeholder-product.png'
                            }
                            alt={
                              product.image?.alt_text ||
                              product.variant?.image?.alt_text ||
                              product.title
                            }
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
                            >
                              {product.title}
                            </Typography>

                            <Box sx={{ mb: 2 }}>
                              <Chip
                                label={getStatusLabel(product.status)}
                                color={getStatusColor(product.status) as any}
                                size='small'
                                sx={{ mb: 1, mr: 0.5 }}
                              />
                              {syncedProductIds.has(product.id) && (
                                <Chip
                                  label='已同步'
                                  color='success'
                                  size='small'
                                  sx={{ mb: 1 }}
                                  icon={<ActiveIcon sx={{ fontSize: 14 }} />}
                                />
                              )}
                              {product.tags && (
                                <Box sx={{ mt: 1 }}>
                                  {product.tags
                                    .split(',')
                                    .slice(0, 3)
                                    .map((tag, index) => (
                                      <Chip
                                        key={index}
                                        label={tag.trim()}
                                        size='small'
                                        variant='outlined'
                                        sx={{ mr: 0.5, mb: 0.5 }}
                                      />
                                    ))}
                                </Box>
                              )}
                            </Box>

                            <Box sx={{ mb: 2 }}>
                              <Typography
                                variant='body2'
                                color='text.secondary'
                                gutterBottom
                              >
                                供应商: {product.vendor}
                              </Typography>
                              <Typography
                                variant='body2'
                                color='text.secondary'
                                gutterBottom
                              >
                                类型: {product.product_type}
                              </Typography>
                              <Typography
                                variant='body2'
                                color='text.secondary'
                              >
                                变体数量: {product.variants?.length || 0}
                              </Typography>
                            </Box>

                            <Box sx={{ mt: 'auto' }}>
                              <Stack direction='row' spacing={1}>
                                <Button
                                  size='small'
                                  startIcon={<ViewIcon />}
                                  onClick={() => handleViewDetails(product)}
                                >
                                  详情
                                </Button>
                                <Button
                                  size='small'
                                  startIcon={<EditIcon />}
                                  color='secondary'
                                >
                                  编辑
                                </Button>
                              </Stack>
                            </Box>
                          </CardContent>
                        </Card>
                      </Box>
                    ))}
                  </Box>

                  {/* 分页 */}
                  {totalPages > 1 && (
                    <Box
                      sx={{ display: 'flex', justifyContent: 'center', mt: 3 }}
                    >
                      <Pagination
                        count={totalPages}
                        page={page}
                        onChange={(_, newPage) =>
                          selectedStore && fetchProducts(selectedStore, newPage)
                        }
                        color='primary'
                      />
                    </Box>
                  )}
                </>
              )}
            </>
          )}

          {/* 商品详情对话框 */}
          <Dialog
            open={detailsOpen}
            onClose={() => setDetailsOpen(false)}
            maxWidth='md'
            fullWidth
          >
            <DialogTitle>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <StoreIcon />
                商品详情
              </Box>
            </DialogTitle>
            <DialogContent>
              {syncSuccess && (
                <Alert severity='success' sx={{ mb: 2 }}>
                  商品已成功同步到数据库！
                </Alert>
              )}
              {selectedProduct && (
                <Box>
                  <Box sx={{ display: 'flex', gap: 3, flexWrap: 'wrap' }}>
                    <Box sx={{ width: { xs: "100%", md: "50%" } }}>
                      <img
                        src={
                          selectedProduct.image?.url ||
                          selectedProduct.variant?.image?.url ||
                          '/placeholder-product.png'
                        }
                        alt={
                          selectedProduct.image?.alt_text ||
                          selectedProduct.variant?.image?.alt_text ||
                          selectedProduct.title
                        }
                        style={{
                          width: '100%',
                          height: 'auto',
                          borderRadius: 8,
                        }}
                      />
                    </Box>
                    <Box sx={{ width: { xs: "100%", md: "50%" } }}>
                      <Typography variant='h5' gutterBottom>
                        {selectedProduct.title}
                      </Typography>

                      <Box sx={{ mb: 2 }}>
                        <Chip
                          label={getStatusLabel(selectedProduct.status)}
                          color={getStatusColor(selectedProduct.status) as any}
                          sx={{ mb: 1 }}
                        />
                      </Box>

                      <Typography variant='body1' paragraph>
                        <strong>供应商:</strong> {selectedProduct.vendor}
                      </Typography>
                      <Typography variant='body1' paragraph>
                        <strong>类型:</strong> {selectedProduct.product_type}
                      </Typography>
                      <Box
                        sx={{ display: 'flex', alignItems: 'center', mb: 1 }}
                      >
                        <Typography variant='body1' component='span'>
                          <strong>Shopify商品ID:</strong>
                        </Typography>
                        <Chip
                          label={selectedProduct.id}
                          color='primary'
                          size='small'
                          sx={{ ml: 1, cursor: 'pointer' }}
                          onClick={() => fetchProductJson(selectedProduct.id)}
                          disabled={loadingJson}
                        />
                        {loadingJson && (
                          <CircularProgress size={16} sx={{ ml: 1 }} />
                        )}
                      </Box>
                      <Typography variant='body1' paragraph>
                        <strong>创建时间:</strong>{' '}
                        {formatDate(selectedProduct.created_at)}
                      </Typography>
                      <Typography variant='body1' paragraph>
                        <strong>更新时间:</strong>{' '}
                        {formatDate(selectedProduct.updated_at)}
                      </Typography>
                      {selectedProduct.published_at && (
                        <Typography variant='body1' paragraph>
                          <strong>发布时间:</strong>{' '}
                          {formatDate(selectedProduct.published_at)}
                        </Typography>
                      )}
                      {selectedProduct.tags && (
                        <Typography variant='body1' paragraph>
                          <strong>标签:</strong> {selectedProduct.tags}
                        </Typography>
                      )}
                    </Box>
                  </Box>

                  <Divider sx={{ my: 3 }} />

                  {/* 变体信息 */}
                  <Typography variant='h6' gutterBottom>
                    商品变体
                  </Typography>
                  <TableContainer component={Paper}>
                    <Table>
                      <TableHead>
                        <TableRow>
                          <TableCell>标题</TableCell>
                          <TableCell>SKU</TableCell>
                          <TableCell>Shopify变体ID</TableCell>
                          <TableCell>价格</TableCell>
                          <TableCell>库存</TableCell>
                          <TableCell>重量</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {selectedProduct.variants?.map(variant => (
                          <TableRow key={variant.id}>
                            <TableCell>{variant.title}</TableCell>
                            <TableCell>{variant.sku || '-'}</TableCell>
                            <TableCell>
                              <Chip
                                label={variant.id}
                                color='secondary'
                                size='small'
                                variant='outlined'
                              />
                            </TableCell>
                            <TableCell>{formatPrice(variant.price)}</TableCell>
                            <TableCell>
                              <Chip
                                label={variant.inventoryQuantity || 0}
                                color={
                                  variant.inventoryQuantity > 0
                                    ? 'success'
                                    : 'error'
                                }
                                size='small'
                              />
                            </TableCell>
                            <TableCell>-</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                </Box>
              )}
            </DialogContent>

            {/* 映射结果显示在按钮上方 */}
            {mappingResult && (
              <Box sx={{ px: 3, pb: 2 }}>
                <Alert
                  severity={mappingResult.is_mapped ? 'success' : 'info'}
                  onClose={() => setMappingResult(null)}
                >
                  <Typography variant='subtitle2' gutterBottom>
                    {mappingResult.message}
                  </Typography>

                  {/* 商品级映射 */}
                  {mappingResult.is_mapped &&
                    mappingResult.mappings &&
                    mappingResult.mappings.length > 0 && (
                      <Box sx={{ mt: 1 }}>
                        <Typography
                          variant='body2'
                          sx={{ fontWeight: 'bold', mb: 1 }}
                        >
                          商品级映射 ({mappingResult.product_mapping_count || 0}
                          ):
                        </Typography>
                        {mappingResult.mappings.map(
                          (mapping: any, index: number) => (
                            <Box
                              key={index}
                              sx={{
                                mt: 1,
                                p: 1,
                                bgcolor: 'background.paper',
                                borderRadius: 1,
                              }}
                            >
                              <Typography variant='body2'>
                                <strong>核心商品:</strong>{' '}
                                {mapping.core_product?.title || 'N/A'}
                              </Typography>
                              <Typography variant='body2'>
                                <strong>类型:</strong>{' '}
                                {mapping.core_product?.product_type || 'N/A'}
                              </Typography>
                              <Typography variant='body2'>
                                <strong>供应商:</strong>{' '}
                                {mapping.core_product?.vendor || 'N/A'}
                              </Typography>
                              <Typography variant='body2'>
                                <strong>映射类型:</strong>{' '}
                                {mapping.mapping_type}
                              </Typography>
                              <Typography variant='body2'>
                                <strong>同步状态:</strong> {mapping.sync_status}
                              </Typography>
                            </Box>
                          )
                        )}
                      </Box>
                    )}

                  {/* 变体级映射 */}
                  {mappingResult.is_mapped &&
                    mappingResult.variant_mappings &&
                    mappingResult.variant_mappings.length > 0 && (
                      <Box sx={{ mt: 2 }}>
                        <Typography
                          variant='body2'
                          sx={{ fontWeight: 'bold', mb: 1 }}
                        >
                          变体级映射 ({mappingResult.variant_mapping_count || 0}
                          ):
                        </Typography>
                        {mappingResult.variant_mappings.map(
                          (mapping: any, index: number) => (
                            <Box
                              key={index}
                              sx={{
                                mt: 1,
                                p: 1,
                                bgcolor: 'background.paper',
                                borderRadius: 1,
                              }}
                            >
                              <Typography variant='body2'>
                                <strong>核心商品:</strong>{' '}
                                {mapping.core_product?.title || 'N/A'}
                              </Typography>
                              <Typography variant='body2'>
                                <strong>核心变体:</strong>{' '}
                                {mapping.core_variant?.title || 'N/A'}
                              </Typography>
                              <Typography variant='body2'>
                                <strong>SKU:</strong>{' '}
                                {mapping.core_variant?.sku || 'N/A'}
                              </Typography>
                              <Typography variant='body2'>
                                <strong>价格:</strong> $
                                {mapping.core_variant?.price || 'N/A'}
                              </Typography>
                              <Typography variant='body2'>
                                <strong>库存:</strong>{' '}
                                {mapping.core_variant?.inventory_quantity ||
                                  'N/A'}
                              </Typography>
                              <Typography variant='body2'>
                                <strong>外部变体ID:</strong>{' '}
                                {mapping.external_variant_id || 'N/A'}
                              </Typography>
                              <Typography variant='body2'>
                                <strong>映射类型:</strong>{' '}
                                {mapping.mapping_type}
                              </Typography>
                              <Typography variant='body2'>
                                <strong>同步状态:</strong> {mapping.sync_status}
                              </Typography>
                            </Box>
                          )
                        )}
                      </Box>
                    )}
                </Alert>
              </Box>
            )}

            <DialogActions>
              <Button
                variant='contained'
                color='primary'
                startIcon={<SyncIcon />}
                onClick={syncProductToDatabase}
                disabled={!selectedProduct || syncingToDatabase}
              >
                {syncingToDatabase ? (
                  <CircularProgress size={20} />
                ) : (
                  '同步到数据库'
                )}
              </Button>
              <Button
                variant='outlined'
                color='secondary'
                startIcon={
                  checkingMapping ? (
                    <CircularProgress size={16} />
                  ) : (
                    <LinkIcon />
                  )
                }
                onClick={checkProductMapping}
                disabled={!selectedProduct || checkingMapping}
              >
                {checkingMapping ? '检查中...' : '检查商品映射'}
              </Button>
              <Button onClick={() => setDetailsOpen(false)}>关闭</Button>
            </DialogActions>
          </Dialog>

          {/* JSON 数据展示模态框 */}
          <Dialog
            open={jsonModalOpen}
            onClose={() => setJsonModalOpen(false)}
            maxWidth='lg'
            fullWidth
          >
            <DialogTitle>
              Shopify 商品完整 JSON 数据
              {selectedProduct && (
                <Typography variant='body2' color='text.secondary'>
                  {selectedProduct.title}
                </Typography>
              )}
            </DialogTitle>
            <DialogContent>
              {productJson ? (
                <Box sx={{ mt: 2 }}>
                  <Typography variant='h6' gutterBottom>
                    商品 JSON 数据
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
                      {JSON.stringify(productJson, null, 2)}
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
              {productJson && (
                <Button
                  onClick={() => {
                    navigator.clipboard.writeText(
                      JSON.stringify(productJson, null, 2)
                    );
                    // 这里可以添加一个提示，表示已复制到剪贴板
                  }}
                  variant='outlined'
                >
                  复制 JSON
                </Button>
              )}
            </DialogActions>
          </Dialog>
        </Box>
      </DashboardLayout>
    </ProtectedRoute>
  );
};

export default ShopifyProductsPage;
