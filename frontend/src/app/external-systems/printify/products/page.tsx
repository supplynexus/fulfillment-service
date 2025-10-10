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
} from '@mui/icons-material';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { frontendApi } from '@/lib/api';
import { frontendLogger } from '@/lib/frontend-logger';
import { ProductMappingDialog } from '@/components/printify/ProductMappingDialog';

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

  // 搜索过滤
  useEffect(() => {
    if (!searchTerm) {
      setFilteredProducts(products);
    } else {
      const filtered = products.filter(
        product =>
          product.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
          product.description
            ?.toLowerCase()
            .includes(searchTerm.toLowerCase()) ||
          product.tags.some(tag =>
            tag.toLowerCase().includes(searchTerm.toLowerCase())
          )
      );
      setFilteredProducts(filtered);
    }
    setPage(1); // 重置到第一页
  }, [searchTerm, products]);

  // 初始化
  useEffect(() => {
    const initialize = async () => {
      await fetchStores();
    };
    initialize();
  }, [fetchStores]);

  // 当选择店铺时获取商品
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

  // 获取商品价格范围
  const getProductPriceRange = (product: PrintifyProduct) => {
    const prices = product.variants.map(v => v.price).filter(p => p > 0);
    if (prices.length === 0) return 'N/A';
    if (prices.length === 1) return `$${prices[0]}`;
    const min = Math.min(...prices);
    const max = Math.max(...prices);
    return min === max ? `$${min}` : `$${min} - $${max}`;
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
              </Box>
            </CardContent>
          </Card>

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
                        xs: '1fr',
                        sm: 'repeat(2, 1fr)',
                        md: 'repeat(3, 1fr)',
                        lg: 'repeat(4, 1fr)',
                      },
                      gap: 3,
                    }}
                  >
                    {currentProducts.map(product => (
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
                            height='200'
                            image={getProductImage(product)}
                            alt={product.title}
                            sx={{ objectFit: 'cover' }}
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
                              .slice(0, 10)
                              .map(variant => (
                                <TableRow key={variant.id}>
                                  <TableCell>{variant.sku}</TableCell>
                                  <TableCell>${variant.price}</TableCell>
                                  <TableCell>
                                    <Chip
                                      label={
                                        variant.is_enabled ? '启用' : '禁用'
                                      }
                                      color={
                                        variant.is_enabled
                                          ? 'success'
                                          : 'default'
                                      }
                                      size='small'
                                    />
                                  </TableCell>
                                </TableRow>
                              ))}
                            {selectedProduct.variants.length > 10 && (
                              <TableRow>
                                <TableCell colSpan={3} align='center'>
                                  ... 还有{' '}
                                  {selectedProduct.variants.length - 10} 个变体
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
                variant="outlined" 
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
            onMappingCreated={(mapping) => {
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
