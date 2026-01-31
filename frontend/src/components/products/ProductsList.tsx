'use client';

import React, { useState, useEffect } from 'react';
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
  Pagination,
  IconButton,
  Tooltip,
  Alert,
  CircularProgress,
  Avatar,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Badge,
  Tabs,
  Tab,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItemText,
  ListItemButton,
  Divider,
  Snackbar,
} from '@mui/material';
import {
  Search as SearchIcon,
  Refresh as RefreshIcon,
  Visibility as ViewIcon,
  FilterList as FilterIcon,
  Inventory as ProductIcon,
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Link as LinkIcon,
} from '@mui/icons-material';
import { useRouter } from 'next/navigation';
import { frontendApi } from '@/lib/api';
import { Product, ProductListResponse } from '@/types/product';

const ITEMS_PER_PAGE = 10;

export function ProductsList() {
  const router = useRouter();
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [hasMore, setHasMore] = useState(false);

  // 过滤条件
  const [statusFilter, setStatusFilter] = useState('');
  const [productTypeFilter, setProductTypeFilter] = useState('');
  const [vendorFilter, setVendorFilter] = useState('');

  // 展开状态
  const [expandedProducts, setExpandedProducts] = useState<Set<string>>(
    new Set()
  );

  // 标签页状态
  const [activeTab, setActiveTab] = useState(0);

  // 外部商品状态
  const [externalProducts, setExternalProducts] = useState<any[]>([]);
  const [externalLoading, setExternalLoading] = useState(false);
  const [externalError, setExternalError] = useState<string | null>(null);

  // 从外部商品创建对话框状态
  const [createFromExternalDialogOpen, setCreateFromExternalDialogOpen] =
    useState(false);
  const [availableExternalProducts, setAvailableExternalProducts] = useState<
    any[]
  >([]);
  const [selectedExternalProduct, setSelectedExternalProduct] =
    useState<any>(null);
  const [creatingFromExternal, setCreatingFromExternal] = useState(false);

  // Snackbar 状态
  const [snackbarOpen, setSnackbarOpen] = useState(false);
  const [snackbarMessage, setSnackbarMessage] = useState('');
  const [snackbarSeverity, setSnackbarSeverity] = useState<
    'success' | 'error' | 'warning' | 'info'
  >('success');

  // 删除状态
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [productToDelete, setProductToDelete] = useState<{
    id: string;
    title: string;
  } | null>(null);
  const [deleting, setDeleting] = useState(false);

  // 显示消息的函数
  const showMessage = (
    message: string,
    severity: 'success' | 'error' | 'warning' | 'info' = 'success'
  ) => {
    setSnackbarMessage(message);
    setSnackbarSeverity(severity);
    setSnackbarOpen(true);
  };

  const handleSnackbarClose = () => {
    setSnackbarOpen(false);
  };

  const fetchProducts = async () => {
    try {
      setLoading(true);
      setError(null);

      const params: Record<string, any> = {
        page: currentPage,
        limit: ITEMS_PER_PAGE,
        include_variants: true,
        include_dimensions: true,
        include_tags: true,
        include_mappings: true,
      };

      if (searchTerm) params.search = searchTerm;
      if (statusFilter) params.status = statusFilter;
      if (productTypeFilter) params.product_type = productTypeFilter;
      if (vendorFilter) params.vendor = vendorFilter;

      const response = await frontendApi.get('/api/products', { params });

      const data: ProductListResponse = response.data;
      setProducts(data.products || []);
      setTotalPages(Math.ceil((data.total || 0) / ITEMS_PER_PAGE));
      setHasMore(data.has_more || false);
    } catch (err: any) {
      console.error('Failed to fetch products:', err);
      setError(err.response?.data?.detail || 'Failed to fetch products');
    } finally {
      setLoading(false);
    }
  };

  const fetchExternalProducts = async () => {
    try {
      setExternalLoading(true);
      setExternalError(null);

      const response = await frontendApi.get('/api/external-products', {
        params: {
          page: currentPage,
          limit: ITEMS_PER_PAGE,
          include_mappings: true,
        },
      });

      setExternalProducts(response.data.products || []);
    } catch (err: any) {
      console.error('Failed to fetch external products:', err);
      setExternalError(
        err.response?.data?.detail || 'Failed to fetch external products'
      );
    } finally {
      setExternalLoading(false);
    }
  };

  const fetchAvailableExternalProducts = async () => {
    try {
      const response = await frontendApi.get('/api/external-products', {
        params: {
          page: 1,
          limit: 100, // 获取更多数据用于选择
        },
      });

      setAvailableExternalProducts(response.data.products || []);
    } catch (err: any) {
      console.error('Failed to fetch available external products:', err);
    }
  };

  const handleCreateFromExternal = async () => {
    if (!selectedExternalProduct) return;

    try {
      setCreatingFromExternal(true);

      const response = await frontendApi.post(
        '/api/products/create-from-external',
        {
          external_product_id: selectedExternalProduct.id,
        }
      );

      console.log('✅ 从外部商品创建核心商品成功:', response.data);

      // 关闭对话框
      setCreateFromExternalDialogOpen(false);
      setSelectedExternalProduct(null);

      // 刷新核心商品列表
      await fetchProducts();

      // 显示成功消息
      showMessage('核心商品创建成功！', 'success');
    } catch (err: any) {
      console.error('❌ 从外部商品创建核心商品失败:', err);
      showMessage(
        `创建失败: ${err.response?.data?.detail || err.message}`,
        'error'
      );
    } finally {
      setCreatingFromExternal(false);
    }
  };

  useEffect(() => {
    if (activeTab === 0) {
      fetchProducts();
    } else if (activeTab === 1) {
      fetchExternalProducts();
    }
  }, [
    activeTab,
    currentPage,
    searchTerm,
    statusFilter,
    productTypeFilter,
    vendorFilter,
  ]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSearch = (event: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(event.target.value);
    setCurrentPage(1);
  };

  const handleRefresh = () => {
    if (activeTab === 0) {
      fetchProducts();
    } else if (activeTab === 1) {
      fetchExternalProducts();
    }
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
    setCurrentPage(1);
  };

  const handleViewProduct = (productHashId: string) => {
    router.push(`/products/${productHashId}`);
  };

  const handleCreateProduct = () => {
    router.push('/products/create');
  };

  const handleCreateFromExternalClick = () => {
    setCreateFromExternalDialogOpen(true);
    fetchAvailableExternalProducts();
  };

  const handleEditProduct = (productHashId: string) => {
    router.push(`/products/${productHashId}/edit`);
  };

  const handleDeleteProduct = (productHashId: string, productTitle: string) => {
    console.log('🔍 准备删除商品:', { productHashId, productTitle });
    setProductToDelete({ id: productHashId, title: productTitle });
    setDeleteDialogOpen(true);
  };

  const handleConfirmDelete = async () => {
    if (!productToDelete) return;

    try {
      setDeleting(true);
      console.log('🔍 开始删除商品:', productToDelete);

      const response = await frontendApi.delete(
        `/api/products/${productToDelete.id}`
      );

      console.log('✅ 商品删除成功:', response.data);

      // 关闭对话框
      setDeleteDialogOpen(false);
      setProductToDelete(null);

      // 刷新商品列表
      await fetchProducts();

      // 显示成功消息
      showMessage('商品删除成功！', 'success');
    } catch (err: any) {
      console.error('❌ 删除商品失败:', err);
      showMessage(
        `删除失败: ${err.response?.data?.detail || err.message}`,
        'error'
      );
    } finally {
      setDeleting(false);
    }
  };

  const handleCancelDelete = () => {
    setDeleteDialogOpen(false);
    setProductToDelete(null);
  };

  const handleToggleExpand = (productHashId: string) => {
    const newExpanded = new Set(expandedProducts);
    if (newExpanded.has(productHashId)) {
      newExpanded.delete(productHashId);
    } else {
      newExpanded.add(productHashId);
    }
    setExpandedProducts(newExpanded);
  };

  const handleFilterChange = (filterType: string, value: string) => {
    switch (filterType) {
      case 'status':
        setStatusFilter(value);
        break;
      case 'product_type':
        setProductTypeFilter(value);
        break;
      case 'vendor':
        setVendorFilter(value);
        break;
    }
    setCurrentPage(1);
  };

  const clearFilters = () => {
    setStatusFilter('');
    setProductTypeFilter('');
    setVendorFilter('');
    setSearchTerm('');
    setCurrentPage(1);
  };

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
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

  const getAvailabilityColor = (isActive: boolean, isAvailable: boolean) => {
    if (isActive && isAvailable) return 'success';
    if (isActive && !isAvailable) return 'warning';
    return 'error';
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

  if (loading && products.length === 0) {
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
          商品管理
        </Typography>
        <Box display='flex' gap={2}>
          <Button
            variant='contained'
            startIcon={<AddIcon />}
            onClick={handleCreateProduct}
          >
            创建商品
          </Button>
          <Button
            variant='outlined'
            startIcon={<LinkIcon />}
            onClick={handleCreateFromExternalClick}
          >
            从外部商品创建
          </Button>
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
        <Alert severity='error' sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {externalError && (
        <Alert severity='error' sx={{ mb: 2 }}>
          {externalError}
        </Alert>
      )}

      <Card>
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs
            value={activeTab}
            onChange={handleTabChange}
            aria-label='商品管理标签页'
          >
            <Tab label='核心商品' />
            <Tab label='外部商品映射' />
          </Tabs>
        </Box>
        <CardContent>
          <Box display='flex' flexWrap='wrap' gap={2} mb={3}>
            <Box flex='1' minWidth='300px'>
              <TextField
                fullWidth
                placeholder='搜索商品标题、供应商或类型...'
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
            </Box>
            <Box minWidth='150px'>
              <FormControl fullWidth>
                <InputLabel>状态</InputLabel>
                <Select
                  value={statusFilter}
                  onChange={e => handleFilterChange('status', e.target.value)}
                  label='状态'
                >
                  <MenuItem value=''>全部</MenuItem>
                  <MenuItem value='active'>活跃</MenuItem>
                  <MenuItem value='draft'>草稿</MenuItem>
                  <MenuItem value='archived'>已归档</MenuItem>
                </Select>
              </FormControl>
            </Box>
            <Box minWidth='150px'>
              <FormControl fullWidth>
                <InputLabel>类型</InputLabel>
                <Select
                  value={productTypeFilter}
                  onChange={e =>
                    handleFilterChange('product_type', e.target.value)
                  }
                  label='类型'
                >
                  <MenuItem value=''>全部</MenuItem>
                  <MenuItem value='clothing'>服装</MenuItem>
                  <MenuItem value='accessories'>配饰</MenuItem>
                  <MenuItem value='home'>家居</MenuItem>
                </Select>
              </FormControl>
            </Box>
            <Box minWidth='150px'>
              <FormControl fullWidth>
                <InputLabel>供应商</InputLabel>
                <Select
                  value={vendorFilter}
                  onChange={e => handleFilterChange('vendor', e.target.value)}
                  label='供应商'
                >
                  <MenuItem value=''>全部</MenuItem>
                  <MenuItem value='Nike'>Nike</MenuItem>
                  <MenuItem value='Adidas'>Adidas</MenuItem>
                  <MenuItem value='Uniqlo'>Uniqlo</MenuItem>
                </Select>
              </FormControl>
            </Box>
            <Box minWidth='150px'>
              <Button
                variant='outlined'
                onClick={clearFilters}
                fullWidth
                startIcon={<FilterIcon />}
              >
                清除筛选
              </Button>
            </Box>
          </Box>

          <TableContainer component={Paper} variant='outlined'>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>商品</TableCell>
                  <TableCell>供应商</TableCell>
                  <TableCell>类型</TableCell>
                  <TableCell>状态</TableCell>
                  <TableCell>可用性</TableCell>
                  <TableCell>变体数量</TableCell>
                  <TableCell>标签</TableCell>
                  <TableCell>创建时间</TableCell>
                  <TableCell>操作</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {activeTab === 0 ? (
                  // 核心商品标签页
                  products.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={9} align='center'>
                        <Typography variant='body2' color='text.secondary'>
                          {searchTerm ||
                          statusFilter ||
                          productTypeFilter ||
                          vendorFilter
                            ? '没有找到匹配的商品'
                            : '暂无商品数据'}
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ) : (
                    products.map(product => (
                      <React.Fragment key={product.id_hashid}>
                        <TableRow hover>
                          <TableCell>
                            <Box display='flex' alignItems='center' gap={2}>
                              <Avatar
                                src={
                                  product.images?.[0]?.url ||
                                  product.images?.[0]
                                }
                                variant='rounded'
                                sx={{ width: 40, height: 40 }}
                              >
                                <ProductIcon />
                              </Avatar>
                              <Box>
                                <Typography variant='body2' fontWeight='medium'>
                                  {product.title}
                                </Typography>
                                <Typography
                                  variant='caption'
                                  color='text.secondary'
                                >
                                  Handle: {product.handle || '-'}
                                </Typography>
                              </Box>
                            </Box>
                          </TableCell>
                          <TableCell>
                            <Typography variant='body2'>
                              {product.vendor || '-'}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Typography variant='body2'>
                              {product.product_type || '-'}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Chip
                              label={product.status}
                              color={getStatusColor(product.status) as any}
                              size='small'
                            />
                          </TableCell>
                          <TableCell>
                            <Chip
                              label={
                                product.is_active && product.is_available
                                  ? '可用'
                                  : '不可用'
                              }
                              color={
                                getAvailabilityColor(
                                  product.is_active,
                                  product.is_available
                                ) as any
                              }
                              size='small'
                            />
                          </TableCell>
                          <TableCell>
                            <Badge
                              badgeContent={product.variants.length}
                              color='primary'
                            >
                              <Typography variant='body2'>
                                {product.variants.length}
                              </Typography>
                            </Badge>
                          </TableCell>
                          <TableCell>
                            <Box display='flex' gap={0.5} flexWrap='wrap'>
                              {product.tags.slice(0, 2).map(tag => (
                                <Chip
                                  key={tag.id_hashid}
                                  label={tag.name}
                                  size='small'
                                  color={tag.is_primary ? 'primary' : 'default'}
                                />
                              ))}
                              {product.tags.length > 2 && (
                                <Chip
                                  label={`+${product.tags.length - 2}`}
                                  size='small'
                                  variant='outlined'
                                />
                              )}
                            </Box>
                          </TableCell>
                          <TableCell>
                            <Typography variant='body2'>
                              {formatDate(product.created_at)}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Box display='flex' gap={1}>
                              <Tooltip title='查看详情'>
                                <IconButton
                                  size='small'
                                  onClick={() =>
                                    handleViewProduct(product.id_hashid)
                                  }
                                >
                                  <ViewIcon />
                                </IconButton>
                              </Tooltip>
                              <Tooltip title='编辑'>
                                <IconButton
                                  size='small'
                                  onClick={() =>
                                    handleEditProduct(product.id_hashid)
                                  }
                                >
                                  <EditIcon />
                                </IconButton>
                              </Tooltip>
                              <Tooltip title='删除'>
                                <IconButton
                                  size='small'
                                  color='error'
                                  onClick={() =>
                                    handleDeleteProduct(
                                      product.id_hashid,
                                      product.title
                                    )
                                  }
                                >
                                  <DeleteIcon />
                                </IconButton>
                              </Tooltip>
                              <Tooltip
                                title={
                                  expandedProducts.has(product.id_hashid)
                                    ? '收起'
                                    : '展开'
                                }
                              >
                                <IconButton
                                  size='small'
                                  onClick={() =>
                                    handleToggleExpand(product.id_hashid)
                                  }
                                >
                                  {expandedProducts.has(product.id_hashid) ? (
                                    <ExpandLessIcon />
                                  ) : (
                                    <ExpandMoreIcon />
                                  )}
                                </IconButton>
                              </Tooltip>
                            </Box>
                          </TableCell>
                        </TableRow>

                        {/* 展开的变体信息 */}
                        {expandedProducts.has(product.id_hashid) && (
                          <TableRow>
                            <TableCell colSpan={9} sx={{ py: 0 }}>
                              <Box sx={{ pl: 4, pr: 2, pb: 2 }}>
                                <Typography variant='subtitle2' gutterBottom>
                                  商品变体 ({product.variants.length})
                                </Typography>
                                {product.variants.length > 0 ? (
                                  <Box display='flex' flexWrap='wrap' gap={1}>
                                    {product.variants.map(variant => (
                                      <Card
                                        key={variant.id_hashid}
                                        variant='outlined'
                                        sx={{ p: 1, minWidth: 200 }}
                                      >
                                        <Typography
                                          variant='caption'
                                          display='block'
                                        >
                                          SKU: {variant.sku || '-'}
                                        </Typography>
                                        <Typography
                                          variant='caption'
                                          display='block'
                                        >
                                          价格: ${variant.price || 0}
                                        </Typography>
                                        <Typography
                                          variant='caption'
                                          display='block'
                                        >
                                          库存: {variant.inventory_quantity}
                                        </Typography>
                                        {Object.keys(variant.attributes)
                                          .length > 0 && (
                                          <Typography
                                            variant='caption'
                                            display='block'
                                          >
                                            属性:{' '}
                                            {Object.entries(variant.attributes)
                                              .map(([k, v]) => `${k}: ${v}`)
                                              .join(', ')}
                                          </Typography>
                                        )}
                                      </Card>
                                    ))}
                                  </Box>
                                ) : (
                                  <Typography
                                    variant='body2'
                                    color='text.secondary'
                                  >
                                    暂无变体
                                  </Typography>
                                )}
                              </Box>
                            </TableCell>
                          </TableRow>
                        )}
                      </React.Fragment>
                    ))
                  )
                ) : // 外部商品标签页
                externalProducts.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={9} align='center'>
                      <Typography variant='body2' color='text.secondary'>
                        {externalLoading ? '加载中...' : '暂无外部商品数据'}
                      </Typography>
                    </TableCell>
                  </TableRow>
                ) : (
                  externalProducts.map(externalProduct => (
                    <TableRow key={externalProduct.id} hover>
                      <TableCell>
                        <Box display='flex' alignItems='center' gap={2}>
                          <Avatar
                            variant='rounded'
                            sx={{ width: 40, height: 40 }}
                          >
                            <ProductIcon />
                          </Avatar>
                          <Box>
                            <Typography variant='body2' fontWeight='medium'>
                              {externalProduct.title}
                            </Typography>
                            <Typography
                              variant='caption'
                              color='text.secondary'
                            >
                              外部ID: {externalProduct.external_product_id}
                            </Typography>
                          </Box>
                        </Box>
                      </TableCell>
                      <TableCell>
                        <Typography variant='body2'>
                          {externalProduct.vendor || '-'}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant='body2'>
                          {externalProduct.product_type || '-'}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={externalProduct.status}
                          color={getStatusColor(externalProduct.status) as any}
                          size='small'
                        />
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={
                            externalProduct.mappings &&
                            externalProduct.mappings.length > 0
                              ? '已映射'
                              : '未映射'
                          }
                          color={
                            externalProduct.mappings &&
                            externalProduct.mappings.length > 0
                              ? 'success'
                              : 'warning'
                          }
                          size='small'
                        />
                      </TableCell>
                      <TableCell>
                        <Typography variant='body2'>
                          {externalProduct.variants
                            ? externalProduct.variants.length
                            : 0}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Box display='flex' gap={0.5} flexWrap='wrap'>
                          {externalProduct.tags &&
                            externalProduct.tags
                              .slice(0, 2)
                              .map((tag: any, index: number) => (
                                <Chip
                                  key={index}
                                  label={tag}
                                  size='small'
                                  variant='outlined'
                                />
                              ))}
                        </Box>
                      </TableCell>
                      <TableCell>
                        <Typography variant='body2'>
                          {formatDate(externalProduct.created_at)}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Box display='flex' gap={1}>
                          <Tooltip title='创建核心商品'>
                            <Button
                              size='small'
                              variant='outlined'
                              color='primary'
                              onClick={() => {
                                // TODO: 实现创建核心商品功能
                                console.log(
                                  '创建核心商品:',
                                  externalProduct.id
                                );
                              }}
                            >
                              创建核心商品
                            </Button>
                          </Tooltip>
                          <Tooltip title='查看映射'>
                            <Button
                              size='small'
                              variant='outlined'
                              color='secondary'
                              onClick={() => {
                                // TODO: 实现查看映射功能
                                console.log('查看映射:', externalProduct.id);
                              }}
                            >
                              查看映射
                            </Button>
                          </Tooltip>
                        </Box>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </TableContainer>

          {totalPages > 1 && (
            <Box display='flex' justifyContent='center' mt={3}>
              <Pagination
                count={totalPages}
                page={currentPage}
                onChange={(_, page) => setCurrentPage(page)}
                color='primary'
              />
            </Box>
          )}
        </CardContent>
      </Card>

      {/* 从外部商品创建对话框 */}
      <Dialog
        open={createFromExternalDialogOpen}
        onClose={() => setCreateFromExternalDialogOpen(false)}
        maxWidth='md'
        fullWidth
      >
        <DialogTitle>从外部商品创建核心商品</DialogTitle>
        <DialogContent>
          <Typography variant='body2' color='text.secondary' sx={{ mb: 2 }}>
            选择一个外部商品来创建对应的核心商品：
          </Typography>
          <List>
            {availableExternalProducts.map((product, index) => (
              <React.Fragment key={product.id}>
                <ListItemButton
                  selected={selectedExternalProduct?.id === product.id}
                  onClick={() => setSelectedExternalProduct(product)}
                >
                  <ListItemText
                    primary={product.title}
                    secondary={`外部系统: ${product.external_system_name || 'Unknown'} | 店铺: ${product.shop_name || 'Unknown'} | 供应商: ${product.vendor || '-'} | 类型: ${product.product_type || '-'} | 外部ID: ${product.external_product_id}`}
                  />
                </ListItemButton>
                {index < availableExternalProducts.length - 1 && <Divider />}
              </React.Fragment>
            ))}
          </List>
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => setCreateFromExternalDialogOpen(false)}
            disabled={creatingFromExternal}
          >
            取消
          </Button>
          <Button
            onClick={handleCreateFromExternal}
            variant='contained'
            disabled={!selectedExternalProduct || creatingFromExternal}
            startIcon={
              creatingFromExternal ? (
                <CircularProgress size={16} />
              ) : (
                <LinkIcon />
              )
            }
          >
            {creatingFromExternal ? '创建中...' : '创建核心商品'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* 删除确认对话框 */}
      <Dialog
        open={deleteDialogOpen}
        onClose={handleCancelDelete}
        maxWidth='sm'
        fullWidth
      >
        <DialogTitle>确认删除商品</DialogTitle>
        <DialogContent>
          <Alert severity='warning' sx={{ mb: 2 }}>
            <Typography variant='body2' fontWeight='medium'>
              警告：此操作将永久删除商品及其相关数据！
            </Typography>
          </Alert>
          <Typography variant='body1' gutterBottom>
            您确定要删除以下商品吗？
          </Typography>
          <Typography variant='h6' color='error' gutterBottom>
            {productToDelete?.title}
          </Typography>
          <Typography variant='body2' color='text.secondary'>
            此操作将删除：
          </Typography>
          <Box component='ul' sx={{ pl: 2, mt: 1 }}>
            <Typography component='li' variant='body2' color='text.secondary'>
              商品基本信息
            </Typography>
            <Typography component='li' variant='body2' color='text.secondary'>
              所有商品变体
            </Typography>
            <Typography component='li' variant='body2' color='text.secondary'>
              所有映射关系
            </Typography>
            <Typography component='li' variant='body2' color='text.secondary'>
              所有标签关联
            </Typography>
          </Box>
          <Typography
            variant='body2'
            color='error'
            sx={{ mt: 2, fontWeight: 'medium' }}
          >
            此操作不可撤销！
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCancelDelete} disabled={deleting}>
            取消
          </Button>
          <Button
            onClick={handleConfirmDelete}
            variant='contained'
            color='error'
            disabled={deleting}
            startIcon={
              deleting ? <CircularProgress size={16} /> : <DeleteIcon />
            }
          >
            {deleting ? '删除中...' : '确认删除'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Snackbar 消息提示 */}
      <Snackbar
        open={snackbarOpen}
        autoHideDuration={6000}
        onClose={handleSnackbarClose}
        anchorOrigin={{ vertical: 'top', horizontal: 'right' }}
      >
        <Alert
          onClose={handleSnackbarClose}
          severity={snackbarSeverity}
          sx={{ width: '100%' }}
        >
          {snackbarMessage}
        </Alert>
      </Snackbar>
    </Box>
  );
}
