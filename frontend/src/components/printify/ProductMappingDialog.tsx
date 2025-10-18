'use client';

import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
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
  Checkbox,
  Alert,
  CircularProgress,
  Grid,
  Card,
  CardContent,
  Divider,
} from '@mui/material';
import {
  Search as SearchIcon,
  Link as LinkIcon,
  Storefront as StorefrontIcon,
  Inventory as InventoryIcon,
} from '@mui/icons-material';
import { frontendApi } from '@/lib/api';
import { frontendLogger } from '@/lib/frontend-logger';

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

interface PrintifyProduct {
  id: string;
  title: string;
  description?: string;
  tags: string[];
  variants: PrintifyVariant[];
  images: Array<{
    src: string;
    variant_ids: number[];
    position: string;
    is_default: boolean;
  }>;
}

interface CoreProduct {
  id_hashid: string;
  title: string;
  vendor: string;
  product_type: string;
  status: string;
  is_active: boolean;
  is_available: boolean;
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

interface ProductMappingDialogProps {
  open: boolean;
  onClose: () => void;
  printifyProduct: PrintifyProduct | null;
  onMappingCreated?: (mapping: any) => void;
}

export function ProductMappingDialog({
  open,
  onClose,
  printifyProduct,
  onMappingCreated,
}: ProductMappingDialogProps) {
  const [coreProducts, setCoreProducts] = useState<CoreProduct[]>([]);
  const [selectedCoreProduct, setSelectedCoreProduct] =
    useState<CoreProduct | null>(null);
  const [selectedCoreVariant, setSelectedCoreVariant] =
    useState<CoreVariant | null>(null);
  const [selectedPrintifyVariant, setSelectedPrintifyVariant] =
    useState<PrintifyVariant | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [creatingMapping, setCreatingMapping] = useState(false);

  // 获取核心商品列表
  const fetchCoreProducts = async () => {
    try {
      setLoading(true);
      setError(null);

      frontendLogger.info('🔍 开始获取核心商品列表');

      const response = await frontendApi.get('/api/products', {
        params: {
          page: 1,
          limit: 100,
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
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (open) {
      fetchCoreProducts();
    }
  }, [open]);

  // 过滤核心商品
  const filteredCoreProducts = coreProducts.filter(
    product =>
      product.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      product.vendor.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // 创建映射
  const handleCreateMapping = async () => {
    if (
      !selectedCoreProduct ||
      !selectedCoreVariant ||
      !selectedPrintifyVariant
    ) {
      setError('请选择要映射的商品和变体');
      return;
    }

    try {
      setCreatingMapping(true);
      setError(null);
      setSuccess(null);

      frontendLogger.info('🔗 开始创建商品映射', {
        coreProduct: selectedCoreProduct.title,
        coreVariant: selectedCoreVariant.sku,
        printifyVariant: selectedPrintifyVariant.sku,
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
        core_variant_id_hashid: selectedCoreVariant.id_hashid,
        external_system_id_hashid: printifySystem.id_hashid,
        external_product_id: printifyProduct?.id,
        external_variant_id: selectedPrintifyVariant.sku,
        mapping_type: 'manual',
        sync_direction: 'bidirectional',
        sync_status: 'active',
      };

      // 调用后端API创建映射
      const response = await frontendApi.post(
        '/api/products/mappings/',
        mappingData
      );

      frontendLogger.info('✅ 商品映射创建成功', {
        coreProduct: selectedCoreProduct.title,
        printifyVariant: selectedPrintifyVariant.sku,
      });

      setSuccess('商品映射创建成功！');

      if (onMappingCreated) {
        onMappingCreated(mappingData);
      }

      // 3秒后关闭对话框
      setTimeout(() => {
        onClose();
        setSuccess(null);
        setSelectedCoreProduct(null);
        setSelectedCoreVariant(null);
        setSelectedPrintifyVariant(null);
      }, 3000);
    } catch (error) {
      frontendLogger.error('❌ 创建商品映射失败', {
        error: String(error),
      });
      setError('创建商品映射失败');
    } finally {
      setCreatingMapping(false);
    }
  };

  const handleClose = () => {
    onClose();
    setError(null);
    setSuccess(null);
    setSelectedCoreProduct(null);
    setSelectedCoreVariant(null);
    setSelectedPrintifyVariant(null);
    setSearchTerm('');
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth='lg' fullWidth>
      <DialogTitle>
        <Box display='flex' alignItems='center' gap={2}>
          <LinkIcon color='primary' />
          <Typography variant='h6'>商品映射</Typography>
        </Box>
      </DialogTitle>

      <DialogContent>
        {error && (
          <Alert severity='error' sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {success && (
          <Alert severity='success' sx={{ mb: 2 }}>
            {success}
          </Alert>
        )}

        {printifyProduct && (
          <Box>
            {/* Printify商品信息 */}
            <Card sx={{ mb: 3 }}>
              <CardContent>
                <Box display='flex' alignItems='center' gap={2} mb={2}>
                  <StorefrontIcon color='primary' />
                  <Typography variant='h6'>Printify商品</Typography>
                </Box>

                <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }} spacing={2}>
                  <Box sx={{ width: { xs: "100%", md: "50%" } }}>
                    <Typography variant='subtitle1' fontWeight='medium'>
                      {printifyProduct.title}
                    </Typography>
                    <Typography
                      variant='body2'
                      color='text.secondary'
                      paragraph
                    >
                      {printifyProduct.description || '暂无描述'}
                    </Typography>

                    <Box display='flex' gap={1} flexWrap='wrap' mb={2}>
                      {printifyProduct.tags.slice(0, 3).map((tag, index) => (
                        <Chip key={index} label={tag} size='small' />
                      ))}
                    </Box>
                  </Box>

                  <Box sx={{ width: { xs: "100%", md: "50%" } }}>
                    <Typography variant='subtitle2' gutterBottom>
                      选择要映射的变体
                    </Typography>
                    <TableContainer
                      component={Paper}
                      variant='outlined'
                      sx={{ maxHeight: 200 }}
                    >
                      <Table size='small'>
                        <TableHead>
                          <TableRow>
                            <TableCell padding='checkbox'>选择</TableCell>
                            <TableCell>SKU</TableCell>
                            <TableCell>价格</TableCell>
                            <TableCell>状态</TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {printifyProduct.variants
                            .slice(0, 10)
                            .map(variant => (
                              <TableRow key={variant.id} hover>
                                <TableCell padding='checkbox'>
                                  <Checkbox
                                    checked={
                                      selectedPrintifyVariant?.id === variant.id
                                    }
                                    onChange={() =>
                                      setSelectedPrintifyVariant(variant)
                                    }
                                  />
                                </TableCell>
                                <TableCell>
                                  <Typography
                                    variant='body2'
                                    fontWeight='medium'
                                  >
                                    {variant.sku}
                                  </Typography>
                                </TableCell>
                                <TableCell>
                                  <Typography variant='body2'>
                                    ${variant.price}
                                  </Typography>
                                </TableCell>
                                <TableCell>
                                  <Chip
                                    label={variant.is_enabled ? '启用' : '禁用'}
                                    color={
                                      variant.is_enabled ? 'success' : 'default'
                                    }
                                    size='small'
                                  />
                                </TableCell>
                              </TableRow>
                            ))}
                        </TableBody>
                      </Table>
                    </TableContainer>
                  </Box>
                </Box>
              </CardContent>
            </Card>

            <Divider sx={{ my: 2 }} />

            {/* 核心商品选择 */}
            <Card>
              <CardContent>
                <Box display='flex' alignItems='center' gap={2} mb={2}>
                  <InventoryIcon color='primary' />
                  <Typography variant='h6'>选择核心商品</Typography>
                </Box>

                <TextField
                  fullWidth
                  placeholder='搜索核心商品...'
                  value={searchTerm}
                  onChange={e => setSearchTerm(e.target.value)}
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position='start'>
                        <SearchIcon />
                      </InputAdornment>
                    ),
                  }}
                  sx={{ mb: 2 }}
                />

                {loading ? (
                  <Box display='flex' justifyContent='center' py={4}>
                    <CircularProgress />
                  </Box>
                ) : (
                  <TableContainer
                    component={Paper}
                    variant='outlined'
                    sx={{ maxHeight: 300 }}
                  >
                    <Table stickyHeader>
                      <TableHead>
                        <TableRow>
                          <TableCell padding='checkbox'>选择</TableCell>
                          <TableCell>商品名称</TableCell>
                          <TableCell>供应商</TableCell>
                          <TableCell>状态</TableCell>
                          <TableCell>变体数量</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {filteredCoreProducts.map(product => (
                          <TableRow key={product.id_hashid} hover>
                            <TableCell padding='checkbox'>
                              <Checkbox
                                checked={
                                  selectedCoreProduct?.id_hashid ===
                                  product.id_hashid
                                }
                                onChange={() => {
                                  setSelectedCoreProduct(product);
                                  setSelectedCoreVariant(null);
                                }}
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
                                color={
                                  product.is_active ? 'success' : 'default'
                                }
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
                )}

                {/* 核心商品变体选择 */}
                {selectedCoreProduct && selectedCoreProduct.variants && (
                  <Box mt={2}>
                    <Typography variant='subtitle2' gutterBottom>
                      选择核心商品变体
                    </Typography>
                    <TableContainer
                      component={Paper}
                      variant='outlined'
                      sx={{ maxHeight: 200 }}
                    >
                      <Table size='small'>
                        <TableHead>
                          <TableRow>
                            <TableCell padding='checkbox'>选择</TableCell>
                            <TableCell>SKU</TableCell>
                            <TableCell>名称</TableCell>
                            <TableCell>价格</TableCell>
                            <TableCell>状态</TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {selectedCoreProduct.variants.map(variant => (
                            <TableRow key={variant.id_hashid} hover>
                              <TableCell padding='checkbox'>
                                <Checkbox
                                  checked={
                                    selectedCoreVariant?.id_hashid ===
                                    variant.id_hashid
                                  }
                                  onChange={() =>
                                    setSelectedCoreVariant(variant)
                                  }
                                />
                              </TableCell>
                              <TableCell>
                                <Typography variant='body2' fontWeight='medium'>
                                  {variant.sku}
                                </Typography>
                              </TableCell>
                              <TableCell>
                                <Typography variant='body2'>
                                  {variant.name}
                                </Typography>
                              </TableCell>
                              <TableCell>
                                <Typography variant='body2'>
                                  ${variant.price}
                                </Typography>
                              </TableCell>
                              <TableCell>
                                <Chip
                                  label={variant.is_active ? '启用' : '禁用'}
                                  color={
                                    variant.is_active ? 'success' : 'default'
                                  }
                                  size='small'
                                />
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </TableContainer>
                  </Box>
                )}
              </CardContent>
            </Card>
          </Box>
        )}
      </DialogContent>

      <DialogActions>
        <Button onClick={handleClose} disabled={creatingMapping}>
          取消
        </Button>
        <Button
          onClick={handleCreateMapping}
          variant='contained'
          disabled={
            !selectedCoreProduct ||
            !selectedCoreVariant ||
            !selectedPrintifyVariant ||
            creatingMapping
          }
          startIcon={
            creatingMapping ? <CircularProgress size={16} /> : <LinkIcon />
          }
        >
          {creatingMapping ? '创建中...' : '创建映射'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
