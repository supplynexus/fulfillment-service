'use client';

import React, { useState } from 'react';
import {
  Box,
  Typography,
  Grid,
  Card,
  CardContent,
  CardActions,
  Button,
  Chip,
  TextField,
  InputAdornment,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
  CircularProgress,
  Radio,
  RadioGroup,
  FormControlLabel,
  FormLabel,
} from '@mui/material';
import {
  Search as SearchIcon,
  Category as CategoryIcon,
  CheckCircle as CheckCircleIcon,
} from '@mui/icons-material';

interface Product {
  id: string;
  name: string;
  code: string;
  description?: string;
  categoryId: string;
  categoryName: string;
  isActive: boolean;
}

interface ProductSelectorProps {
  products: Product[];
  selectedProduct: Product | null;
  onProductSelect: (product: Product) => void;
  loading: boolean;
}

export default function ProductSelector({
  products,
  selectedProduct,
  onProductSelect,
  loading,
}: ProductSelectorProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  // 获取所有分类
  const categories = Array.from(
    new Set(products.map(p => p.categoryName))
  ).sort();

  // 筛选产品
  const filteredProducts = products.filter(product => {
    const matchesSearch =
      product.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      product.code.toLowerCase().includes(searchTerm.toLowerCase()) ||
      product.description?.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesCategory =
      categoryFilter === 'all' || product.categoryName === categoryFilter;

    const matchesStatus =
      statusFilter === 'all' ||
      (statusFilter === 'active' ? product.isActive : !product.isActive);

    return matchesSearch && matchesCategory && matchesStatus;
  });

  const handleProductSelect = (product: Product) => {
    onProductSelect(product);
  };

  if (loading) {
    return (
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          height: 200,
        }}
      >
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      {/* 标题 */}
      <Typography variant='h6' sx={{ mb: 3 }}>
        选择要创建 SKU 的产品
      </Typography>

      {/* 搜索和筛选 */}
      <Box sx={{ mb: 3, display: 'flex', gap: 2, flexWrap: 'wrap' }}>
        <TextField
          size='small'
          placeholder='搜索产品...'
          value={searchTerm}
          onChange={e => setSearchTerm(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position='start'>
                <SearchIcon />
              </InputAdornment>
            ),
          }}
          sx={{ minWidth: 200 }}
        />

        <FormControl size='small' sx={{ minWidth: 120 }}>
          <InputLabel>分类</InputLabel>
          <Select
            value={categoryFilter}
            label='分类'
            onChange={e => setCategoryFilter(e.target.value)}
          >
            <MenuItem value='all'>全部分类</MenuItem>
            {categories.map(category => (
              <MenuItem key={category} value={category}>
                {category}
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        <FormControl size='small' sx={{ minWidth: 120 }}>
          <InputLabel>状态</InputLabel>
          <Select
            value={statusFilter}
            label='状态'
            onChange={e => setStatusFilter(e.target.value)}
          >
            <MenuItem value='all'>全部状态</MenuItem>
            <MenuItem value='active'>启用</MenuItem>
            <MenuItem value='inactive'>禁用</MenuItem>
          </Select>
        </FormControl>
      </Box>

      {/* 产品列表 */}
      <Grid container spacing={2}>
        {filteredProducts.map(product => (
          <Grid item xs={12} sm={6} md={4} key={product.id}>
            <Card
              sx={{
                cursor: 'pointer',
                border: selectedProduct?.id === product.id ? 2 : 1,
                borderColor:
                  selectedProduct?.id === product.id
                    ? 'primary.main'
                    : 'divider',
                '&:hover': {
                  boxShadow: 3,
                },
              }}
              onClick={() => handleProductSelect(product)}
            >
              <CardContent>
                <Box
                  sx={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    justifyContent: 'space-between',
                    mb: 1,
                  }}
                >
                  <Typography variant='h6' component='div' sx={{ flexGrow: 1 }}>
                    {product.name}
                  </Typography>
                  {selectedProduct?.id === product.id && (
                    <CheckCircleIcon color='primary' />
                  )}
                </Box>

                <Typography
                  variant='body2'
                  color='text.secondary'
                  sx={{ mb: 1 }}
                >
                  编码: {product.code}
                </Typography>

                {product.description && (
                  <Typography
                    variant='body2'
                    color='text.secondary'
                    sx={{ mb: 2 }}
                  >
                    {product.description}
                  </Typography>
                )}

                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                  <Chip
                    icon={<CategoryIcon />}
                    label={product.categoryName}
                    size='small'
                    color='primary'
                    variant='outlined'
                  />
                  <Chip
                    label={product.isActive ? '启用' : '禁用'}
                    size='small'
                    color={product.isActive ? 'success' : 'default'}
                  />
                </Box>
              </CardContent>

              <CardActions>
                <Button
                  size='small'
                  variant={
                    selectedProduct?.id === product.id
                      ? 'contained'
                      : 'outlined'
                  }
                  onClick={e => {
                    e.stopPropagation();
                    handleProductSelect(product);
                  }}
                >
                  {selectedProduct?.id === product.id ? '已选择' : '选择'}
                </Button>
              </CardActions>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* 空状态 */}
      {filteredProducts.length === 0 && (
        <Box sx={{ textAlign: 'center', py: 4 }}>
          <Typography variant='body2' color='text.secondary'>
            {searchTerm || categoryFilter !== 'all' || statusFilter !== 'all'
              ? '没有找到匹配的产品'
              : '暂无产品'}
          </Typography>
        </Box>
      )}

      {/* 选择提示 */}
      {selectedProduct && (
        <Alert severity='success' sx={{ mt: 2 }}>
          已选择产品: <strong>{selectedProduct.name}</strong>
        </Alert>
      )}
    </Box>
  );
}
