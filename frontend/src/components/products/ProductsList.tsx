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
} from '@mui/material';
import {
  Search as SearchIcon,
  Refresh as RefreshIcon,
  Visibility as ViewIcon,
  FilterList as FilterIcon,
  Inventory as ProductIcon,
  Sync as SyncIcon,
} from '@mui/icons-material';
import { useRouter } from 'next/navigation';
import { frontendApi } from '@/lib/api';

const ITEMS_PER_PAGE = 10;

interface Product {
  id: number;
  shopify_product_id: string;
  printify_product_id?: string;
  title: string;
  vendor?: string;
  product_type?: string;
  status: string;
  sync_status: string;
  created_at: string;
  updated_at?: string;
  variants_count?: number;
  images?: string[];
}

export function ProductsList() {
  const router = useRouter();
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  const fetchProducts = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await frontendApi.get('/api/products', {
        params: {
          page: currentPage,
          limit: ITEMS_PER_PAGE,
          search: searchTerm || undefined,
        },
      });

      setProducts(response.data.items || []);
      setTotalPages(Math.ceil((response.data.total || 0) / ITEMS_PER_PAGE));
    } catch (err: any) {
      console.error('Failed to fetch products:', err);
      setError(err.response?.data?.detail || 'Failed to fetch products');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProducts();
  }, [currentPage, searchTerm]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSearch = (event: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(event.target.value);
    setCurrentPage(1);
  };

  const handleRefresh = () => {
    fetchProducts();
  };

  const handleViewProduct = (productId: number) => {
    router.push(`/products/${productId}`);
  };

  const handleSyncProducts = () => {
    router.push('/products/sync');
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

  const getSyncStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'synced':
        return 'success';
      case 'pending':
        return 'warning';
      case 'failed':
        return 'error';
      case 'not_synced':
        return 'default';
      default:
        return 'default';
    }
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
            variant='outlined'
            startIcon={<SyncIcon />}
            onClick={handleSyncProducts}
          >
            同步商品
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
          <Box display='flex' gap={2} mb={3}>
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
            <Button variant='outlined' startIcon={<FilterIcon />} disabled>
              筛选
            </Button>
          </Box>

          <TableContainer component={Paper} variant='outlined'>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>商品</TableCell>
                  <TableCell>供应商</TableCell>
                  <TableCell>类型</TableCell>
                  <TableCell>状态</TableCell>
                  <TableCell>同步状态</TableCell>
                  <TableCell>变体数量</TableCell>
                  <TableCell>创建时间</TableCell>
                  <TableCell>操作</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {products.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={8} align='center'>
                      <Typography variant='body2' color='text.secondary'>
                        {searchTerm ? '没有找到匹配的商品' : '暂无商品数据'}
                      </Typography>
                    </TableCell>
                  </TableRow>
                ) : (
                  products.map(product => (
                    <TableRow key={product.id} hover>
                      <TableCell>
                        <Box display='flex' alignItems='center' gap={2}>
                          <Avatar
                            src={product.images?.[0]}
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
                              ID: {product.shopify_product_id}
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
                          label={product.sync_status}
                          color={getSyncStatusColor(product.sync_status) as any}
                          size='small'
                        />
                      </TableCell>
                      <TableCell>
                        <Typography variant='body2'>
                          {product.variants_count || 0}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant='body2'>
                          {formatDate(product.created_at)}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Tooltip title='查看详情'>
                          <IconButton
                            size='small'
                            onClick={() => handleViewProduct(product.id)}
                          >
                            <ViewIcon />
                          </IconButton>
                        </Tooltip>
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
    </Box>
  );
}
