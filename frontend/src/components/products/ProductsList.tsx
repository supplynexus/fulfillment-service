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
  Grid,
  Badge,
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
  const [total, setTotal] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  
  // 过滤条件
  const [statusFilter, setStatusFilter] = useState('');
  const [productTypeFilter, setProductTypeFilter] = useState('');
  const [vendorFilter, setVendorFilter] = useState('');
  
  // 展开状态
  const [expandedProducts, setExpandedProducts] = useState<Set<string>>(new Set());

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
      setTotal(data.total || 0);
      setTotalPages(Math.ceil((data.total || 0) / ITEMS_PER_PAGE));
      setHasMore(data.has_more || false);
    } catch (err: any) {
      console.error('Failed to fetch products:', err);
      setError(err.response?.data?.detail || 'Failed to fetch products');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProducts();
  }, [currentPage, searchTerm, statusFilter, productTypeFilter, vendorFilter]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSearch = (event: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(event.target.value);
    setCurrentPage(1);
  };

  const handleRefresh = () => {
    fetchProducts();
  };

  const handleViewProduct = (productHashId: string) => {
    router.push(`/products/${productHashId}`);
  };

  const handleCreateProduct = () => {
    router.push('/products/create');
  };

  const handleEditProduct = (productHashId: string) => {
    router.push(`/products/${productHashId}/edit`);
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

      <Card>
        <CardContent>
          <Grid container spacing={2} mb={3}>
            <Grid item xs={12} md={4}>
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
            </Grid>
            <Grid item xs={12} md={2}>
              <FormControl fullWidth>
                <InputLabel>状态</InputLabel>
                <Select
                  value={statusFilter}
                  onChange={(e) => handleFilterChange('status', e.target.value)}
                  label='状态'
                >
                  <MenuItem value=''>全部</MenuItem>
                  <MenuItem value='active'>活跃</MenuItem>
                  <MenuItem value='draft'>草稿</MenuItem>
                  <MenuItem value='archived'>已归档</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} md={2}>
              <FormControl fullWidth>
                <InputLabel>类型</InputLabel>
                <Select
                  value={productTypeFilter}
                  onChange={(e) => handleFilterChange('product_type', e.target.value)}
                  label='类型'
                >
                  <MenuItem value=''>全部</MenuItem>
                  <MenuItem value='clothing'>服装</MenuItem>
                  <MenuItem value='accessories'>配饰</MenuItem>
                  <MenuItem value='home'>家居</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} md={2}>
              <FormControl fullWidth>
                <InputLabel>供应商</InputLabel>
                <Select
                  value={vendorFilter}
                  onChange={(e) => handleFilterChange('vendor', e.target.value)}
                  label='供应商'
                >
                  <MenuItem value=''>全部</MenuItem>
                  <MenuItem value='Nike'>Nike</MenuItem>
                  <MenuItem value='Adidas'>Adidas</MenuItem>
                  <MenuItem value='Uniqlo'>Uniqlo</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} md={2}>
              <Button
                variant='outlined'
                onClick={clearFilters}
                fullWidth
                startIcon={<FilterIcon />}
              >
                清除筛选
              </Button>
            </Grid>
          </Grid>

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
                {products.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={9} align='center'>
                      <Typography variant='body2' color='text.secondary'>
                        {searchTerm || statusFilter || productTypeFilter || vendorFilter 
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
                              src={product.images?.[0]?.url || product.images?.[0]}
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
                            label={product.is_active && product.is_available ? '可用' : '不可用'}
                            color={getAvailabilityColor(product.is_active, product.is_available) as any}
                            size='small'
                          />
                        </TableCell>
                        <TableCell>
                          <Badge badgeContent={product.variants.length} color='primary'>
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
                                onClick={() => handleViewProduct(product.id_hashid)}
                              >
                                <ViewIcon />
                              </IconButton>
                            </Tooltip>
                            <Tooltip title='编辑'>
                              <IconButton
                                size='small'
                                onClick={() => handleEditProduct(product.id_hashid)}
                              >
                                <EditIcon />
                              </IconButton>
                            </Tooltip>
                            <Tooltip title={expandedProducts.has(product.id_hashid) ? '收起' : '展开'}>
                              <IconButton
                                size='small'
                                onClick={() => handleToggleExpand(product.id_hashid)}
                              >
                                {expandedProducts.has(product.id_hashid) ? <ExpandLessIcon /> : <ExpandMoreIcon />}
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
                                    <Card key={variant.id_hashid} variant='outlined' sx={{ p: 1, minWidth: 200 }}>
                                      <Typography variant='caption' display='block'>
                                        SKU: {variant.sku || '-'}
                                      </Typography>
                                      <Typography variant='caption' display='block'>
                                        价格: ${variant.price || 0}
                                      </Typography>
                                      <Typography variant='caption' display='block'>
                                        库存: {variant.inventory_quantity}
                                      </Typography>
                                      {Object.keys(variant.attributes).length > 0 && (
                                        <Typography variant='caption' display='block'>
                                          属性: {Object.entries(variant.attributes).map(([k, v]) => `${k}: ${v}`).join(', ')}
                                        </Typography>
                                      )}
                                    </Card>
                                  ))}
                                </Box>
                              ) : (
                                <Typography variant='body2' color='text.secondary'>
                                  暂无变体
                                </Typography>
                              )}
                            </Box>
                          </TableCell>
                        </TableRow>
                      )}
                    </React.Fragment>
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
    </Box>
  );
}
