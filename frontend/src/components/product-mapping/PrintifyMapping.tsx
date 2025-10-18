'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Button,
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
  Avatar,
  IconButton,
  Tooltip,
  Alert,
  CircularProgress,
  Checkbox,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Badge,
  Stack,
  Divider,
  CardMedia,
  Pagination,
} from '@mui/material';
import {
  Search as SearchIcon,
  Refresh as RefreshIcon,
  Link as LinkIcon,
  LinkOff as UnlinkIcon,
  Visibility as ViewIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Add as AddIcon,
  Print as PrintifyIcon,
  Inventory as InventoryIcon,
  Storefront as StorefrontIcon,
  Sync as SyncIcon,
  CheckCircle as ActiveIcon,
  Cancel as InactiveIcon,
  Warning as WarningIcon,
} from '@mui/icons-material';
import { frontendApi } from '@/lib/api';
import { frontendLogger } from '@/lib/frontend-logger';
import { VariantMappingDialog } from './VariantMappingDialog';
import { BatchMappingDialog } from './BatchMappingDialog';

interface CoreProduct {
  id_hashid: string;
  title: string;
  vendor: string;
  product_type: string;
  status: string;
  is_active: boolean;
  is_available: boolean;
  created_at: string;
  variants: CoreVariant[];
}

interface CoreVariant {
  id_hashid: string;
  sku: string;
  name: string;
  price: number;
  is_active: boolean;
  is_available: boolean;
  attributes: Record<string, any>;
}

interface PrintifyProduct {
  id: number;
  id_hashid: string;
  tenant_id: number;
  external_system_id: number;
  printify_product_id: string;
  printify_shop_id?: string;
  title: string;
  description?: string;
  tags?: string[];
  visible: boolean;
  is_locked: boolean;
  external?: {
    id: string;
    handle: string;
    sku: string;
  };
  user_id?: number;
  print_provider_id?: number;
  options?: Array<{
    name: string;
    type: string;
    values: Array<{
      id: number;
      title: string;
    }>;
  }>;
  variants?: PrintifyVariant[];
  images?: Array<{
    src: string;
    variant_ids: number[];
    position: string;
    is_default: boolean;
  }>;
  print_areas?: Array<{
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
  raw_data?: any;
  last_synced_at?: string;
  sync_status: string;
  sync_error?: string;
  created_at: string;
  updated_at?: string;
}

interface PrintifyVariant {
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
}

interface PrintifyStore {
  id_hashid: string;
  name: string;
  system_type: string;
  external_id?: string;
  is_active: boolean;
}

interface ProductMapping {
  id: string;
  id_hashid: string;
  core_product_id: number;
  core_variant_id: number | null;
  external_system_id: number;
  external_product_id: string;
  external_variant_id: string | null;
  mapping_type: string;
  sync_direction: string;
  sync_status: string;
  created_at: string;
  updated_at: string;
  core_product_title: string;
  core_variant_sku: string | null;
  external_system_name: string;
  system_type: string;
  printify_product_title: string;
  printify_variant_sku: string | null;
}

export function PrintifyMapping() {
  const [coreProducts, setCoreProducts] = useState<CoreProduct[]>([]);
  const [printifyProducts, setPrintifyProducts] = useState<PrintifyProduct[]>(
    []
  );
  const [printifyStores, setPrintifyStores] = useState<PrintifyStore[]>([]);
  const [selectedStore, setSelectedStore] = useState<PrintifyStore | null>(
    null
  );
  const [mappings, setMappings] = useState<ProductMapping[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 搜索和筛选状态
  const [coreSearchTerm, setCoreSearchTerm] = useState('');
  const [printifySearchTerm, setPrintifySearchTerm] = useState('');
  const [selectedCoreProducts, setSelectedCoreProducts] = useState<string[]>(
    []
  );
  const [selectedPrintifyProducts, setSelectedPrintifyProducts] = useState<
    number[]
  >([]);

  // 映射对话框状态
  const [mappingDialogOpen, setMappingDialogOpen] = useState(false);
  const [mappingStatus, setMappingStatus] = useState<'active' | 'pending'>(
    'active'
  );
  const [selectedCoreProduct, setSelectedCoreProduct] =
    useState<CoreProduct | null>(null);
  const [selectedPrintifyProduct, setSelectedPrintifyProduct] =
    useState<PrintifyProduct | null>(null);

  // 详情对话框状态
  const [detailDialogOpen, setDetailDialogOpen] = useState(false);
  const [selectedMapping, setSelectedMapping] = useState<ProductMapping | null>(
    null
  );

  // 变体映射对话框状态
  const [variantMappingDialogOpen, setVariantMappingDialogOpen] =
    useState(false);
  const [printifySystemId, setPrintifySystemId] = useState<string>('');

  // 批量映射对话框状态
  const [batchDialogOpen, setBatchDialogOpen] = useState(false);

  // 同步状态
  const [syncing, setSyncing] = useState(false);
  const [syncStatus, setSyncStatus] = useState<any>(null);

  // 分页状态
  const [corePage, setCorePage] = useState(1);
  const [printifyPage, setPrintifyPage] = useState(1);
  const [mappingPage, setMappingPage] = useState(1);
  const [itemsPerPage] = useState(10);

  // 获取核心商品数据
  const fetchCoreProducts = useCallback(async () => {
    try {
      frontendLogger.info('🔍 开始获取核心商品列表');

      const response = await frontendApi.get('/api/products', {
        params: {
          page: corePage,
          limit: itemsPerPage,
          include_variants: true,
          include_dimensions: false,
          include_tags: false,
          include_mappings: false,
        },
      });

      if (response.data && response.data.products) {
        setCoreProducts(response.data.products);
        frontendLogger.info('✅ 核心商品列表获取成功', {
          count: response.data.products.length,
        });
      } else {
        throw new Error('获取核心商品列表失败：响应数据格式不正确');
      }
    } catch (error) {
      frontendLogger.error('❌ 获取核心商品列表失败', {
        error: String(error),
      });
      setError('获取核心商品列表失败');
    }
  }, [corePage, itemsPerPage]);

  // 获取 Printify 店铺列表
  const fetchPrintifyStores = useCallback(async () => {
    try {
      frontendLogger.info('🔍 开始获取 Printify 店铺列表');

      const response = await frontendApi.get('/api/external-systems', {
        params: { system_type: 'PRINTIFY' },
      });

      if (response.data && response.data.external_systems) {
        const printifyStores = response.data.external_systems.filter(
          (store: any) => store.system_type === 'PRINTIFY' && store.is_active
        );
        setPrintifyStores(printifyStores);
        frontendLogger.info('✅ Printify 店铺列表获取成功', {
          count: printifyStores.length,
        });

        // 如果有店铺，默认选择第一个
        if (printifyStores.length > 0) {
          setSelectedStore(printifyStores[0]);
          setPrintifySystemId(printifyStores[0].id_hashid);
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

  // 获取 Printify 商品数据（从本地数据库）
  const fetchPrintifyProducts = useCallback(async (store: PrintifyStore) => {
    if (!store) return;

    try {
      frontendLogger.info('🔍 开始获取 Printify 商品列表（本地数据库）', {
        storeId: store.id_hashid,
        storeName: store.name,
      });

      const response = await frontendApi.get('/api/printify-products/', {
        params: {
          external_system_id: store.id_hashid,
          limit: 100,
          offset: 0,
          visible_only: true,
        },
      });

      if (response.data && response.data.products) {
        const productsData = response.data.products || [];
        setPrintifyProducts(productsData);
        frontendLogger.info('✅ Printify 商品列表获取成功（本地数据库）', {
          count: productsData.length,
          storeName: store.name,
        });
      } else {
        throw new Error('获取商品列表失败：响应数据格式不正确');
      }
    } catch (error) {
      frontendLogger.error('❌ 获取 Printify 商品列表失败（本地数据库）', {
        error: String(error),
        storeId: store.id_hashid,
      });
      setError('获取商品列表失败');
    }
  }, []);

  // 获取映射关系
  const fetchMappings = useCallback(async () => {
    try {
      frontendLogger.info('🔍 开始获取商品映射关系');

      const response = await frontendApi.get('/api/products/mappings/', {
        params: {
          page: mappingPage,
          limit: itemsPerPage,
          system_type: 'PRINTIFY',
        },
      });

      if (response.data && response.data.mappings) {
        setMappings(response.data.mappings);
        frontendLogger.info('✅ 商品映射关系获取成功', {
          count: response.data.mappings.length,
        });
      } else {
        throw new Error('获取映射关系失败：响应数据格式不正确');
      }
    } catch (error) {
      frontendLogger.error('❌ 获取商品映射关系失败', {
        error: String(error),
      });
      setError('获取映射关系失败');
    }
  }, [mappingPage, itemsPerPage]);

  // 初始化数据
  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      await Promise.all([
        fetchCoreProducts(),
        fetchPrintifyStores(),
        fetchMappings(),
      ]);
    } catch (err: any) {
      frontendLogger.error('❌ 初始化数据失败', { error: err.message });
      setError(err.response?.data?.detail || err.message || '初始化数据失败');
    } finally {
      setLoading(false);
    }
  }, [fetchCoreProducts, fetchPrintifyStores, fetchMappings]);

  // 当选择店铺时获取商品和同步状态
  useEffect(() => {
    if (selectedStore) {
      fetchPrintifyProducts(selectedStore);
      fetchSyncStatus();
    }
  }, [selectedStore, fetchPrintifyProducts]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // 过滤商品
  const filteredCoreProducts = coreProducts.filter(
    product =>
      product.title.toLowerCase().includes(coreSearchTerm.toLowerCase()) ||
      product.vendor.toLowerCase().includes(coreSearchTerm.toLowerCase())
  );

  const filteredPrintifyProducts = printifyProducts.filter(
    product =>
      product.title.toLowerCase().includes(printifySearchTerm.toLowerCase()) ||
      (product.description &&
        product.description
          .toLowerCase()
          .includes(printifySearchTerm.toLowerCase())) ||
      product.tags.some(tag =>
        tag.toLowerCase().includes(printifySearchTerm.toLowerCase())
      )
  );

  // 检查商品是否已映射
  const isProductMapped = (
    coreProductId: string,
    printifyProductId: string
  ) => {
    return mappings.some(
      mapping =>
        mapping.core_product_id.toString() === coreProductId &&
        mapping.external_product_id === printifyProductId
    );
  };

  // 选择商品
  const handleCoreProductSelect = (productId: string) => {
    setSelectedCoreProducts(prev =>
      prev.includes(productId)
        ? prev.filter(id => id !== productId)
        : [...prev, productId]
    );
  };

  const handlePrintifyProductSelect = (productId: number) => {
    setSelectedPrintifyProducts(prev =>
      prev.includes(productId)
        ? prev.filter(id => id !== productId)
        : [...prev, productId]
    );
  };

  // 创建映射
  const handleCreateMapping = () => {
    if (
      selectedCoreProducts.length === 0 ||
      selectedPrintifyProducts.length === 0
    ) {
      setError('请选择要映射的商品');
      return;
    }

    // 如果选择了多个商品，显示批量映射对话框
    if (
      selectedCoreProducts.length > 1 ||
      selectedPrintifyProducts.length > 1
    ) {
      setBatchDialogOpen(true);
    } else {
      const coreProduct = coreProducts.find(
        p => p.id_hashid === selectedCoreProducts[0]
      );
      const printifyProduct = printifyProducts.find(
        p => p.id === selectedPrintifyProducts[0]
      );

      if (coreProduct && printifyProduct) {
        setSelectedCoreProduct(coreProduct);
        setSelectedPrintifyProduct(printifyProduct);

        // 检查是否有变体，如果有则显示变体映射对话框
        if (
          coreProduct.variants &&
          coreProduct.variants.length > 0 &&
          printifyProduct.variants &&
          printifyProduct.variants.length > 0
        ) {
          setVariantMappingDialogOpen(true);
        } else {
          setMappingDialogOpen(true);
        }
      }
    }
  };

  // 确认创建映射
  const handleConfirmMapping = async () => {
    if (!selectedCoreProduct || !selectedPrintifyProduct) return;

    try {
      frontendLogger.info('🔗 开始创建商品映射', {
        coreProduct: selectedCoreProduct.title,
        printifyProduct: selectedPrintifyProduct.title,
      });

      // 获取Printify外部系统ID
      const externalSystemsResponse = await frontendApi.get(
        '/api/external-systems',
        {
          params: { system_type: 'PRINTIFY' },
        }
      );

      const printifySystem = externalSystemsResponse.data.external_systems?.[0];
      if (!printifySystem) {
        throw new Error('未找到Printify外部系统配置');
      }

      const mappingData = {
        core_product_id_hashid: selectedCoreProduct.id_hashid,
        core_variant_id_hashid: null, // 暂时不映射变体
        external_system_id_hashid: printifySystem.id_hashid,
        external_product_id: selectedPrintifyProduct.printify_product_id,
        external_variant_id: null, // 暂时不映射变体
        mapping_type: 'manual',
        sync_direction: 'bidirectional',
        sync_status: mappingStatus,
      };

      // 调用后端API创建映射
      const response = await frontendApi.post(
        '/api/products/mappings/',
        mappingData
      );

      frontendLogger.info('✅ 商品映射创建成功', {
        coreProduct: selectedCoreProduct.title,
        printifyProduct: selectedPrintifyProduct.title,
      });

      // 刷新数据
      await fetchData();

      setMappingDialogOpen(false);
      setSelectedCoreProducts([]);
      setSelectedPrintifyProducts([]);
      setSelectedCoreProduct(null);
      setSelectedPrintifyProduct(null);
    } catch (error) {
      frontendLogger.error('❌ 创建商品映射失败', {
        error: String(error),
      });
      setError('创建商品映射失败');
    }
  };

  // 确认变体映射
  const handleConfirmVariantMapping = async (mappings: any[]) => {
    try {
      frontendLogger.info('✅ 变体映射创建成功', {
        coreProduct: selectedCoreProduct?.title,
        printifyProduct: selectedPrintifyProduct?.title,
        mappingCount: mappings.length,
      });

      // 刷新数据
      await fetchData();

      setVariantMappingDialogOpen(false);
      setSelectedCoreProducts([]);
      setSelectedPrintifyProducts([]);
      setSelectedCoreProduct(null);
      setSelectedPrintifyProduct(null);
    } catch (error) {
      frontendLogger.error('❌ 变体映射处理失败', {
        error: String(error),
      });
      setError('变体映射处理失败');
    }
  };

  // 删除映射
  const handleRemoveMapping = async (mappingId: string) => {
    try {
      frontendLogger.info('🗑️ 开始删除商品映射', { mappingId });

      await frontendApi.delete(`/api/products/mappings/${mappingId}`);

      frontendLogger.info('✅ 商品映射删除成功', { mappingId });

      // 刷新数据
      await fetchData();
    } catch (error) {
      frontendLogger.error('❌ 删除商品映射失败', {
        error: String(error),
        mappingId,
      });
      setError('删除商品映射失败');
    }
  };

  // 查看映射详情
  const handleViewMappingDetail = (mapping: ProductMapping) => {
    setSelectedMapping(mapping);
    setDetailDialogOpen(true);
  };

  // 批量映射确认
  const handleBatchMappingConfirm = async (
    mappings: any[],
    status: 'active' | 'pending'
  ) => {
    try {
      frontendLogger.info('🔗 开始批量创建映射', {
        count: mappings.length,
        status,
      });

      // 刷新数据
      await fetchData();

      setBatchDialogOpen(false);
      setSelectedCoreProducts([]);
      setSelectedPrintifyProducts([]);

      frontendLogger.info('✅ 批量映射创建成功', {
        count: mappings.length,
      });
    } catch (error) {
      frontendLogger.error('❌ 批量映射创建失败', {
        error: String(error),
      });
      setError('批量映射创建失败');
    }
  };

  // 批量映射取消
  const handleBatchMappingCancel = () => {
    setSelectedCoreProducts([]);
    setSelectedPrintifyProducts([]);
    setBatchDialogOpen(false);
  };

  // 更新映射状态
  const handleUpdateMappingStatus = async (
    mappingId: string,
    newStatus: string
  ) => {
    try {
      frontendLogger.info('🔄 开始更新映射状态', {
        mappingId,
        newStatus,
      });

      await frontendApi.patch(`/api/products/mappings/${mappingId}`, {
        sync_status: newStatus,
      });

      frontendLogger.info('✅ 映射状态更新成功', {
        mappingId,
        newStatus,
      });

      // 刷新数据
      await fetchData();
    } catch (error) {
      frontendLogger.error('❌ 更新映射状态失败', {
        error: String(error),
        mappingId,
      });
      setError('更新映射状态失败');
    }
  };

  // 同步映射
  const handleSyncMapping = async (mappingId: string) => {
    try {
      frontendLogger.info('🔄 开始同步映射', { mappingId });

      await frontendApi.post(`/api/products/mappings/${mappingId}/sync`);

      frontendLogger.info('✅ 映射同步成功', { mappingId });

      // 刷新数据
      await fetchData();
    } catch (error) {
      frontendLogger.error('❌ 映射同步失败', {
        error: String(error),
        mappingId,
      });
      setError('映射同步失败');
    }
  };

  // 同步 Printify 商品到本地数据库
  const handleSyncPrintifyProducts = async () => {
    if (!selectedStore) {
      setError('请先选择店铺');
      return;
    }

    try {
      setSyncing(true);
      setError(null);

      frontendLogger.info('🔄 开始同步 Printify 商品到本地数据库', {
        storeId: selectedStore.id_hashid,
        storeName: selectedStore.name,
      });

      const response = await frontendApi.post(
        '/api/printify-sync/sync-products',
        {
          external_system_id_hashid: selectedStore.id_hashid,
        }
      );

      frontendLogger.info('✅ Printify 商品同步成功', response.data);

      // 刷新商品列表
      await fetchPrintifyProducts(selectedStore);

      // 获取同步状态
      await fetchSyncStatus();
    } catch (error) {
      frontendLogger.error('❌ Printify 商品同步失败', {
        error: String(error),
        storeId: selectedStore.id_hashid,
      });
      setError('同步 Printify 商品失败');
    } finally {
      setSyncing(false);
    }
  };

  // 获取同步状态
  const fetchSyncStatus = async () => {
    if (!selectedStore) return;

    try {
      const response = await frontendApi.get('/api/printify-sync/sync-status', {
        params: {
          external_system_id_hashid: selectedStore.id_hashid,
        },
      });

      setSyncStatus(response.data);
    } catch (error) {
      frontendLogger.error('❌ 获取同步状态失败', {
        error: String(error),
      });
    }
  };

  // 获取商品主图
  const getProductImage = (product: PrintifyProduct) => {
    const defaultImage = product.images.find(img => img.is_default);
    return (
      defaultImage?.src || product.images[0]?.src || '/placeholder-product.png'
    );
  };

  // 获取商品价格范围
  const getProductPriceRange = (product: PrintifyProduct) => {
    const prices = product.variants.map(v => v.price).filter(p => p > 0);
    if (prices.length === 0) return 'N/A';
    if (prices.length === 1) return `$${prices[0]}`;
    const min = Math.min(...prices);
    const max = Math.max(...prices);
    return min === max ? `$${min}` : `$${min} - $${max}`;
  };

  if (loading) {
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
        <Box display='flex' alignItems='center' gap={2}>
          <Avatar sx={{ bgcolor: '#96BF47' }}>
            <PrintifyIcon />
          </Avatar>
          <Typography variant='h4' component='h1'>
            Printify 商品映射
          </Typography>
        </Box>
        <Button
          variant='outlined'
          startIcon={<RefreshIcon />}
          onClick={fetchData}
          disabled={loading}
        >
          刷新数据
        </Button>
      </Box>

      {error && (
        <Alert severity='error' sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {/* 店铺选择 */}
      {printifyStores.length > 0 && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Box
              sx={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                mb: 2,
              }}
            >
              <Typography variant='h6'>选择 Printify 店铺</Typography>
              {selectedStore && (
                <Button
                  variant='outlined'
                  startIcon={<SyncIcon />}
                  onClick={handleSyncPrintifyProducts}
                  disabled={syncing}
                  color='primary'
                >
                  {syncing ? '同步中...' : '同步商品到本地'}
                </Button>
              )}
            </Box>
            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
              {printifyStores.map(store => (
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
            {syncStatus && (
              <Box sx={{ mt: 2, p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
                <Typography variant='subtitle2' gutterBottom>
                  同步状态
                </Typography>
                <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                  <Chip
                    label={`总计: ${syncStatus.total_products}`}
                    size='small'
                  />
                  <Chip
                    label={`已同步: ${syncStatus.synced_products}`}
                    size='small'
                    color='success'
                  />
                  <Chip
                    label={`待处理: ${syncStatus.pending_products}`}
                    size='small'
                    color='warning'
                  />
                  <Chip
                    label={`错误: ${syncStatus.error_products}`}
                    size='small'
                    color='error'
                  />
                  <Chip
                    label={`同步率: ${syncStatus.sync_rate}%`}
                    size='small'
                    color='info'
                  />
                </Box>
              </Box>
            )}
          </CardContent>
        </Card>
      )}

      {/* 映射操作区域 */}
      {selectedCoreProducts.length > 0 &&
        selectedPrintifyProducts.length > 0 && (
          <Card
            sx={{
              mb: 3,
              bgcolor: 'primary.light',
              color: 'primary.contrastText',
            }}
          >
            <CardContent>
              <Box
                display='flex'
                justifyContent='space-between'
                alignItems='center'
              >
                <Typography variant='h6'>
                  已选择 {selectedCoreProducts.length} 个核心商品 和{' '}
                  {selectedPrintifyProducts.length} 个 Printify 商品
                </Typography>
                <Button
                  variant='contained'
                  startIcon={<LinkIcon />}
                  onClick={handleCreateMapping}
                  sx={{ bgcolor: 'white', color: 'primary.main' }}
                >
                  创建映射
                </Button>
              </Box>
            </CardContent>
          </Card>
        )}

      <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
        {/* 核心商品列表 */}
        <Box sx={{ width: "100%" }} md={6}>
          <Card>
            <CardContent>
              <Typography variant='h6' component='h2' mb={2}>
                核心商品
              </Typography>

              <TextField
                fullWidth
                placeholder='搜索核心商品...'
                value={coreSearchTerm}
                onChange={e => setCoreSearchTerm(e.target.value)}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position='start'>
                      <SearchIcon />
                    </InputAdornment>
                  ),
                }}
                sx={{ mb: 2 }}
              />

              <TableContainer
                component={Paper}
                variant='outlined'
                sx={{ maxHeight: 400 }}
              >
                <Table stickyHeader>
                  <TableHead>
                    <TableRow>
                      <TableCell padding='checkbox'>选择</TableCell>
                      <TableCell>商品名称</TableCell>
                      <TableCell>供应商</TableCell>
                      <TableCell>状态</TableCell>
                      <TableCell>变体数</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {filteredCoreProducts.map(product => (
                      <TableRow key={product.id_hashid} hover>
                        <TableCell padding='checkbox'>
                          <Checkbox
                            checked={selectedCoreProducts.includes(
                              product.id_hashid
                            )}
                            onChange={() =>
                              handleCoreProductSelect(product.id_hashid)
                            }
                          />
                        </TableCell>
                        <TableCell>
                          <Typography variant='body2' fontWeight='medium'>
                            {product.title}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Typography variant='body2'>
                            {product.vendor}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={product.status}
                            color={product.is_active ? 'success' : 'default'}
                            size='small'
                          />
                        </TableCell>
                        <TableCell>
                          <Typography variant='body2'>
                            {product.variants?.length || 0}
                          </Typography>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </Box>

        {/* Printify 商品列表 */}
        <Box sx={{ width: "100%" }} md={6}>
          <Card>
            <CardContent>
              <Typography variant='h6' component='h2' mb={2}>
                Printify 商品
              </Typography>

              <TextField
                fullWidth
                placeholder='搜索 Printify 商品...'
                value={printifySearchTerm}
                onChange={e => setPrintifySearchTerm(e.target.value)}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position='start'>
                      <SearchIcon />
                    </InputAdornment>
                  ),
                }}
                sx={{ mb: 2 }}
              />

              <TableContainer
                component={Paper}
                variant='outlined'
                sx={{ maxHeight: 400 }}
              >
                <Table stickyHeader>
                  <TableHead>
                    <TableRow>
                      <TableCell padding='checkbox'>选择</TableCell>
                      <TableCell>商品名称</TableCell>
                      <TableCell>价格</TableCell>
                      <TableCell>变体数</TableCell>
                      <TableCell>状态</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {filteredPrintifyProducts.map(product => (
                      <TableRow key={product.id} hover>
                        <TableCell padding='checkbox'>
                          <Checkbox
                            checked={selectedPrintifyProducts.includes(
                              product.id
                            )}
                            onChange={() =>
                              handlePrintifyProductSelect(product.id)
                            }
                          />
                        </TableCell>
                        <TableCell>
                          <Typography variant='body2' fontWeight='medium'>
                            {product.title}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Typography variant='body2'>
                            {getProductPriceRange(product)}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Typography variant='body2'>
                            {product.variants.length}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={product.visible ? '可见' : '隐藏'}
                            color={product.visible ? 'success' : 'default'}
                            size='small'
                          />
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </Box>
      </Box>

      {/* 现有映射列表 */}
      {mappings.length > 0 && (
        <Card sx={{ mt: 3 }}>
          <CardContent>
            <Typography variant='h6' component='h2' mb={2}>
              现有映射关系
            </Typography>

            <TableContainer component={Paper} variant='outlined'>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>核心商品</TableCell>
                    <TableCell>Printify 商品</TableCell>
                    <TableCell>状态</TableCell>
                    <TableCell>创建时间</TableCell>
                    <TableCell>操作</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {mappings.map(mapping => (
                    <TableRow key={mapping.id} hover>
                      <TableCell>
                        <Typography variant='body2' fontWeight='medium'>
                          {mapping.core_product_title}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant='body2'>
                          {mapping.printify_product_title}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={
                            mapping.sync_status === 'active'
                              ? '活跃'
                              : mapping.sync_status === 'pending'
                                ? '待处理'
                                : '错误'
                          }
                          color={
                            mapping.sync_status === 'active'
                              ? 'success'
                              : mapping.sync_status === 'pending'
                                ? 'warning'
                                : 'error'
                          }
                          size='small'
                        />
                      </TableCell>
                      <TableCell>
                        <Typography variant='body2'>
                          {new Date(mapping.created_at).toLocaleDateString(
                            'zh-CN'
                          )}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Box display='flex' gap={1}>
                          <Tooltip title='查看详情'>
                            <IconButton
                              size='small'
                              onClick={() => handleViewMappingDetail(mapping)}
                            >
                              <ViewIcon />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title='同步映射'>
                            <IconButton
                              size='small'
                              onClick={() =>
                                handleSyncMapping(mapping.id_hashid)
                              }
                            >
                              <SyncIcon />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title='更新状态'>
                            <IconButton
                              size='small'
                              onClick={() => {
                                const newStatus =
                                  mapping.sync_status === 'active'
                                    ? 'pending'
                                    : 'active';
                                handleUpdateMappingStatus(
                                  mapping.id_hashid,
                                  newStatus
                                );
                              }}
                            >
                              {mapping.sync_status === 'active' ? (
                                <InactiveIcon />
                              ) : (
                                <ActiveIcon />
                              )}
                            </IconButton>
                          </Tooltip>
                          <Tooltip title='删除映射'>
                            <IconButton
                              size='small'
                              color='error'
                              onClick={() =>
                                handleRemoveMapping(mapping.id_hashid)
                              }
                            >
                              <DeleteIcon />
                            </IconButton>
                          </Tooltip>
                        </Box>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>
      )}

      {/* 映射确认对话框 */}
      <Dialog
        open={mappingDialogOpen}
        onClose={() => setMappingDialogOpen(false)}
        maxWidth='sm'
        fullWidth
      >
        <DialogTitle>确认创建映射</DialogTitle>
        <DialogContent>
          <Typography variant='body2' mb={2}>
            您即将创建核心商品与 Printify 商品的映射关系。
          </Typography>

          {selectedCoreProduct && (
            <Box mb={2}>
              <Typography variant='subtitle2' gutterBottom>
                核心商品：
              </Typography>
              <Typography variant='body2'>
                {selectedCoreProduct.title}
              </Typography>
            </Box>
          )}

          {selectedPrintifyProduct && (
            <Box mb={2}>
              <Typography variant='subtitle2' gutterBottom>
                Printify 商品：
              </Typography>
              <Typography variant='body2'>
                {selectedPrintifyProduct.title}
              </Typography>
            </Box>
          )}

          <FormControl fullWidth sx={{ mt: 2 }}>
            <InputLabel>映射状态</InputLabel>
            <Select
              value={mappingStatus}
              onChange={e =>
                setMappingStatus(e.target.value as 'active' | 'pending')
              }
              label='映射状态'
            >
              <MenuItem value='active'>活跃</MenuItem>
              <MenuItem value='pending'>待处理</MenuItem>
            </Select>
          </FormControl>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setMappingDialogOpen(false)}>取消</Button>
          <Button onClick={handleConfirmMapping} variant='contained'>
            确认创建
          </Button>
        </DialogActions>
      </Dialog>

      {/* 映射详情对话框 */}
      <Dialog
        open={detailDialogOpen}
        onClose={() => setDetailDialogOpen(false)}
        maxWidth='md'
        fullWidth
      >
        <DialogTitle>映射详情</DialogTitle>
        <DialogContent>
          {selectedMapping && (
            <Box>
              <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
                <Box sx={{ width: "100%" }} md={6}>
                  <Card variant='outlined'>
                    <CardContent>
                      <Typography variant='h6' gutterBottom>
                        核心商品
                      </Typography>
                      <Typography variant='body2' fontWeight='medium'>
                        {selectedMapping.core_product_title}
                      </Typography>
                      <Typography variant='body2' color='text.secondary'>
                        SKU: {selectedMapping.core_variant_sku || 'N/A'}
                      </Typography>
                    </CardContent>
                  </Card>
                </Box>
                <Box sx={{ width: "100%" }} md={6}>
                  <Card variant='outlined'>
                    <CardContent>
                      <Typography variant='h6' gutterBottom>
                        Printify 商品
                      </Typography>
                      <Typography variant='body2' fontWeight='medium'>
                        {selectedMapping.printify_product_title}
                      </Typography>
                      <Typography variant='body2' color='text.secondary'>
                        SKU: {selectedMapping.printify_variant_sku || 'N/A'}
                      </Typography>
                    </CardContent>
                  </Card>
                </Box>
              </Box>

              <Box mt={2}>
                <Typography variant='h6' gutterBottom>
                  映射信息
                </Typography>
                <TableContainer component={Paper} variant='outlined'>
                  <Table size='small'>
                    <TableBody>
                      <TableRow>
                        <TableCell>映射类型</TableCell>
                        <TableCell>{selectedMapping.mapping_type}</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell>同步方向</TableCell>
                        <TableCell>{selectedMapping.sync_direction}</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell>同步状态</TableCell>
                        <TableCell>
                          <Chip
                            label={selectedMapping.sync_status}
                            color={
                              selectedMapping.sync_status === 'active'
                                ? 'success'
                                : 'warning'
                            }
                            size='small'
                          />
                        </TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell>创建时间</TableCell>
                        <TableCell>
                          {new Date(selectedMapping.created_at).toLocaleString(
                            'zh-CN'
                          )}
                        </TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell>更新时间</TableCell>
                        <TableCell>
                          {new Date(selectedMapping.updated_at).toLocaleString(
                            'zh-CN'
                          )}
                        </TableCell>
                      </TableRow>
                    </TableBody>
                  </Table>
                </TableContainer>
              </Box>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => {
              if (selectedMapping) {
                const newStatus =
                  selectedMapping.sync_status === 'active'
                    ? 'pending'
                    : 'active';
                handleUpdateMappingStatus(selectedMapping.id_hashid, newStatus);
              }
            }}
            startIcon={
              selectedMapping?.sync_status === 'active' ? (
                <InactiveIcon />
              ) : (
                <ActiveIcon />
              )
            }
          >
            {selectedMapping?.sync_status === 'active'
              ? '设为待处理'
              : '设为活跃'}
          </Button>
          <Button
            onClick={() => {
              if (selectedMapping) {
                handleSyncMapping(selectedMapping.id_hashid);
              }
            }}
            startIcon={<SyncIcon />}
            variant='outlined'
          >
            同步映射
          </Button>
          <Button onClick={() => setDetailDialogOpen(false)}>关闭</Button>
        </DialogActions>
      </Dialog>

      {/* 批量映射对话框 */}
      <BatchMappingDialog
        open={batchDialogOpen}
        onClose={() => setBatchDialogOpen(false)}
        coreProducts={selectedCoreProducts
          .map(id => coreProducts.find(p => p.id_hashid === id)!)
          .filter(Boolean)}
        externalProducts={selectedPrintifyProducts
          .map(id => printifyProducts.find(p => p.id === id)!)
          .filter(Boolean)}
        platform='Printify'
        onConfirm={handleBatchMappingConfirm}
        onCancel={handleBatchMappingCancel}
      />

      {/* 变体映射对话框 */}
      {selectedCoreProduct && selectedPrintifyProduct && (
        <VariantMappingDialog
          open={variantMappingDialogOpen}
          onClose={() => setVariantMappingDialogOpen(false)}
          onConfirm={handleConfirmVariantMapping}
          coreProduct={selectedCoreProduct}
          printifyProduct={selectedPrintifyProduct}
          printifySystemId={printifySystemId}
        />
      )}
    </Box>
  );
}
