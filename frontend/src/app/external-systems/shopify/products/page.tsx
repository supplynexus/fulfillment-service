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
  id: string;  // GraphQL ID like "gid://shopify/ProductVariant/45663476547684"
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
  const [selectedProduct, setSelectedProduct] = useState<ShopifyProduct | null>(null);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [jsonModalOpen, setJsonModalOpen] = useState(false);
  const [productJson, setProductJson] = useState<any>(null);
  const [loadingJson, setLoadingJson] = useState(false);
  const [sortBy, setSortBy] = useState<'title' | 'created_at' | 'updated_at' | 'price'>('title');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');
  const [statusFilter, setStatusFilter] = useState<string>('all');

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

  // 获取 Shopify 商品完整 JSON 数据
  const fetchProductJson = useCallback(async (productId: string, showJsonModal: boolean = true) => {
    if (!selectedStore) return;
    
    try {
      setLoadingJson(true);
      
      // 从 GraphQL ID 中提取纯数字 ID (例如: gid://shopify/Product/8040175042660 -> 8040175042660)
      const numericProductId = productId.replace('gid://shopify/Product/', '');
      
      frontendLogger.info('🔄 获取 Shopify 商品完整 JSON 数据', { 
        originalId: productId,
        numericId: numericProductId,
        storeId: selectedStore,
        storeIdType: typeof selectedStore,
        storeIdLength: selectedStore?.length
      });
      
      const response = await frontendApi.get(
        `/api/external-systems/shopify/products/${numericProductId}/json?external_system_hashid=${selectedStore.id_hashid}`
      );
      
      frontendLogger.info('✅ Shopify 商品 JSON 数据获取成功', { 
        productId, 
        hasData: !!response.data 
      });
      
      // 设置完整的商品JSON数据
      setProductJson(response.data);
      
      // 更新selectedProduct的变体数据
      if (response.data?.product?.variants?.edges) {
        const variants = response.data.product.variants.edges.map((edge: any) => edge.node);
        setSelectedProduct(prev => prev ? {
          ...prev,
          variants: variants
        } : null);
        
        frontendLogger.info('✅ 商品变体数据已更新', { 
          variantCount: variants.length,
          variants: variants.map((v: any) => ({ id: v.id, title: v.title }))
        });
      }
      
      if (showJsonModal) {
        setJsonModalOpen(true);
      }
      
    } catch (error: any) {
      frontendLogger.error('❌ 获取 Shopify 商品 JSON 数据失败', { 
        error: error.message,
        productId 
      });
      setError(`获取商品 JSON 数据失败: ${error.message}`);
    } finally {
      setLoadingJson(false);
    }
  }, [selectedStore]);

  // 获取 Shopify 商品列表
  const fetchProducts = useCallback(async (store: ShopifyStore, pageNum: number = 1) => {
    if (!store) return;
    
    setLoading(true);
    setError(null);
    
    try {
      frontendLogger.info('🔄 获取 Shopify 商品列表', { storeId: store.id_hashid, page: pageNum });
      const response = await frontendApi.get(`/api/external-systems/shopify/${store.id_hashid}/products`, {
        params: {
          page: pageNum,
          limit: 20,
          search: searchTerm,
          sort_by: sortBy,
          sort_order: sortOrder,
          status: statusFilter !== 'all' ? statusFilter : undefined,
        },
      });
      
      setProducts(response.data.products || []);
      setTotalPages(response.data.pagination?.total_pages || 1);
      setPage(pageNum);
      
      frontendLogger.info('✅ Shopify 商品列表获取成功', { 
        count: response.data.products?.length || 0,
        totalPages: response.data.pagination?.total_pages || 1
      });
    } catch (error: any) {
      frontendLogger.error('❌ 获取 Shopify 商品列表失败', { error: error.message });
      setError('获取商品列表失败');
    } finally {
      setLoading(false);
    }
  }, [searchTerm, sortBy, sortOrder, statusFilter]);

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
          storeId: selectedStore.id_hashid 
        });
        
        await fetchProductJson(product.id, false);
      } catch (error) {
        frontendLogger.error('❌ 自动获取商品数据失败', { 
          error: error instanceof Error ? error.message : 'Unknown error',
          productId: product.id 
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
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
            <Typography variant="h4" component="h1" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <StoreIcon />
              Shopify 商品管理
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
                        border: selectedStore?.id === store.id ? 2 : 1,
                        borderColor: selectedStore?.id === store.id ? 'primary.main' : 'divider',
                        '&:hover': { borderColor: 'primary.main' },
                      }}
                      onClick={() => setSelectedStore(store)}
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
                    <Grid item xs={12} md={4}>
                      <TextField
                        fullWidth
                        placeholder="搜索商品..."
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
                      <TextField
                        select
                        fullWidth
                        label="排序"
                        value={sortBy}
                        onChange={(e) => setSortBy(e.target.value as any)}
                      >
                        <MenuItem value="title">标题</MenuItem>
                        <MenuItem value="created_at">创建时间</MenuItem>
                        <MenuItem value="updated_at">更新时间</MenuItem>
                        <MenuItem value="price">价格</MenuItem>
                      </TextField>
                    </Grid>
                    <Grid item xs={12} md={2}>
                      <TextField
                        select
                        fullWidth
                        label="状态"
                        value={statusFilter}
                        onChange={(e) => setStatusFilter(e.target.value)}
                      >
                        <MenuItem value="all">全部</MenuItem>
                        <MenuItem value="active">已发布</MenuItem>
                        <MenuItem value="draft">草稿</MenuItem>
                        <MenuItem value="archived">已归档</MenuItem>
                      </TextField>
                    </Grid>
                    <Grid item xs={12} md={2}>
                      <Button
                        fullWidth
                        variant="outlined"
                        onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
                        startIcon={<SortIcon />}
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

              {/* 商品列表 */}
              {loading ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
                  <CircularProgress />
                </Box>
              ) : error ? (
                <Alert severity="error" sx={{ mb: 2 }}>
                  {error}
                </Alert>
              ) : products.length === 0 ? (
                <Card>
                  <CardContent sx={{ textAlign: 'center', p: 4 }}>
                    <Typography variant="h6" color="text.secondary">
                      暂无商品数据
                    </Typography>
                  </CardContent>
                </Card>
              ) : (
                <>
                  <Grid container spacing={3}>
                    {products.map((product) => (
                      <Grid item xs={12} sm={6} md={4} lg={3} key={product.id}>
                        <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                          <CardMedia
                            component="img"
                            height="200"
                            image={product.image?.url || product.variant?.image?.url || '/placeholder-product.png'}
                            alt={product.image?.alt_text || product.variant?.image?.alt_text || product.title}
                            sx={{ objectFit: 'cover' }}
                          />
                          <CardContent sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
                            <Typography variant="h6" component="h3" gutterBottom>
                              {product.title}
                            </Typography>
                            
                            <Box sx={{ mb: 2 }}>
                              <Chip
                                label={getStatusLabel(product.status)}
                                color={getStatusColor(product.status) as any}
                                size="small"
                                sx={{ mb: 1 }}
                              />
                              {product.tags && (
                                <Box sx={{ mt: 1 }}>
                                  {product.tags.split(',').slice(0, 3).map((tag, index) => (
                                    <Chip
                                      key={index}
                                      label={tag.trim()}
                                      size="small"
                                      variant="outlined"
                                      sx={{ mr: 0.5, mb: 0.5 }}
                                    />
                                  ))}
                                </Box>
                              )}
                            </Box>

                            <Box sx={{ mb: 2 }}>
                              <Typography variant="body2" color="text.secondary" gutterBottom>
                                供应商: {product.vendor}
                              </Typography>
                              <Typography variant="body2" color="text.secondary" gutterBottom>
                                类型: {product.product_type}
                              </Typography>
                              <Typography variant="body2" color="text.secondary">
                                变体数量: {product.variants?.length || 0}
                              </Typography>
                            </Box>

                            <Box sx={{ mt: 'auto' }}>
                              <Stack direction="row" spacing={1}>
                                <Button
                                  size="small"
                                  startIcon={<ViewIcon />}
                                  onClick={() => handleViewDetails(product)}
                                >
                                  详情
                                </Button>
                                <Button
                                  size="small"
                                  startIcon={<EditIcon />}
                                  color="secondary"
                                >
                                  编辑
                                </Button>
                              </Stack>
                            </Box>
                          </CardContent>
                        </Card>
                      </Grid>
                    ))}
                  </Grid>

                  {/* 分页 */}
                  {totalPages > 1 && (
                    <Box sx={{ display: 'flex', justifyContent: 'center', mt: 3 }}>
                      <Pagination
                        count={totalPages}
                        page={page}
                        onChange={(_, newPage) => selectedStore && fetchProducts(selectedStore, newPage)}
                        color="primary"
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
            maxWidth="md"
            fullWidth
          >
            <DialogTitle>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <StoreIcon />
                商品详情
              </Box>
            </DialogTitle>
            <DialogContent>
              {selectedProduct && (
                <Box>
                  <Grid container spacing={3}>
                    <Grid item xs={12} md={6}>
                      <img
                        src={selectedProduct.image?.url || selectedProduct.variant?.image?.url || '/placeholder-product.png'}
                        alt={selectedProduct.image?.alt_text || selectedProduct.variant?.image?.alt_text || selectedProduct.title}
                        style={{ width: '100%', height: 'auto', borderRadius: 8 }}
                      />
                    </Grid>
                    <Grid item xs={12} md={6}>
                      <Typography variant="h5" gutterBottom>
                        {selectedProduct.title}
                      </Typography>
                      
                      <Box sx={{ mb: 2 }}>
                        <Chip
                          label={getStatusLabel(selectedProduct.status)}
                          color={getStatusColor(selectedProduct.status) as any}
                          sx={{ mb: 1 }}
                        />
                      </Box>

                      <Typography variant="body1" paragraph>
                        <strong>供应商:</strong> {selectedProduct.vendor}
                      </Typography>
                      <Typography variant="body1" paragraph>
                        <strong>类型:</strong> {selectedProduct.product_type}
                      </Typography>
                      <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                        <Typography variant="body1" component="span">
                          <strong>Shopify商品ID:</strong>
                        </Typography>
                        <Chip 
                          label={selectedProduct.id} 
                          color="primary" 
                          size="small" 
                          sx={{ ml: 1, cursor: 'pointer' }}
                          onClick={() => fetchProductJson(selectedProduct.id)}
                          disabled={loadingJson}
                        />
                        {loadingJson && <CircularProgress size={16} sx={{ ml: 1 }} />}
                      </Box>
                      <Typography variant="body1" paragraph>
                        <strong>创建时间:</strong> {formatDate(selectedProduct.created_at)}
                      </Typography>
                      <Typography variant="body1" paragraph>
                        <strong>更新时间:</strong> {formatDate(selectedProduct.updated_at)}
                      </Typography>
                      {selectedProduct.published_at && (
                        <Typography variant="body1" paragraph>
                          <strong>发布时间:</strong> {formatDate(selectedProduct.published_at)}
                        </Typography>
                      )}
                      {selectedProduct.tags && (
                        <Typography variant="body1" paragraph>
                          <strong>标签:</strong> {selectedProduct.tags}
                        </Typography>
                      )}
                    </Grid>
                  </Grid>

                  <Divider sx={{ my: 3 }} />

                  {/* 变体信息 */}
                  <Typography variant="h6" gutterBottom>
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
                        {selectedProduct.variants?.map((variant) => (
                          <TableRow key={variant.id}>
                            <TableCell>{variant.title}</TableCell>
                            <TableCell>{variant.sku || '-'}</TableCell>
                            <TableCell>
                              <Chip 
                                label={variant.id} 
                                color="secondary" 
                                size="small"
                                variant="outlined"
                              />
                            </TableCell>
                            <TableCell>{formatPrice(variant.price)}</TableCell>
                            <TableCell>
                              <Chip
                                label={variant.inventoryQuantity || 0}
                                color={variant.inventoryQuantity > 0 ? 'success' : 'error'}
                                size="small"
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
            <DialogActions>
              <Button onClick={() => setDetailsOpen(false)}>关闭</Button>
            </DialogActions>
          </Dialog>

          {/* JSON 数据展示模态框 */}
          <Dialog
            open={jsonModalOpen}
            onClose={() => setJsonModalOpen(false)}
            maxWidth="lg"
            fullWidth
          >
            <DialogTitle>
              Shopify 商品完整 JSON 数据
              {selectedProduct && (
                <Typography variant="body2" color="text.secondary">
                  {selectedProduct.title}
                </Typography>
              )}
            </DialogTitle>
            <DialogContent>
              {productJson ? (
                <Box sx={{ mt: 2 }}>
                  <Typography variant="h6" gutterBottom>
                    商品 JSON 数据
                  </Typography>
                  <Paper 
                    sx={{ 
                      p: 2, 
                      backgroundColor: '#f5f5f5', 
                      maxHeight: '60vh', 
                      overflow: 'auto',
                      fontFamily: 'monospace',
                      fontSize: '0.875rem'
                    }}
                  >
                    <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
                      {JSON.stringify(productJson, null, 2)}
                    </pre>
                  </Paper>
                </Box>
              ) : (
                <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '200px' }}>
                  <CircularProgress />
                </Box>
              )}
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setJsonModalOpen(false)}>关闭</Button>
              {productJson && (
                <Button 
                  onClick={() => {
                    navigator.clipboard.writeText(JSON.stringify(productJson, null, 2));
                    // 这里可以添加一个提示，表示已复制到剪贴板
                  }}
                  variant="outlined"
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
