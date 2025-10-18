'use client';

import React, { useState, useEffect } from 'react';
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
} from '@mui/material';
import {
  Search as SearchIcon,
  Refresh as RefreshIcon,
  Link as LinkIcon,
  LinkOff as UnlinkIcon,
  Visibility as ViewIcon,
  Edit as EditIcon,
  Storefront as ShopifyIcon,
  Public as YahooIcon,
  Storefront as RakutenIcon,
  Add as AddIcon,
  Info as InfoIcon,
} from '@mui/icons-material';
import { MappingDetailDialog } from './MappingDetailDialog';
import { BatchMappingDialog } from './BatchMappingDialog';
import { frontendApi } from '@/lib/api';

interface CoreProduct {
  id_hashid: string;
  title: string;
  vendor: string;
  product_type: string;
  status: string;
  is_active: boolean;
  is_available: boolean;
  created_at: string;
}

interface ExternalProduct {
  id_hashid: string;
  title: string;
  vendor: string;
  product_type: string;
  status: string;
  price: number;
  inventory_quantity: number;
  created_at: string;
}

interface ProductMapping {
  id: string;
  core_product_id: string;
  external_product_id: string;
  status: 'active' | 'pending' | 'error';
  created_at: string;
}

interface PlatformMappingProps {
  platform: 'shopify' | 'yahoo' | 'rakuten';
}

export function PlatformMapping({ platform }: PlatformMappingProps) {
  const [coreProducts, setCoreProducts] = useState<CoreProduct[]>([]);
  const [externalProducts, setExternalProducts] = useState<ExternalProduct[]>(
    []
  );
  const [mappings, setMappings] = useState<ProductMapping[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 搜索和筛选状态
  const [coreSearchTerm, setCoreSearchTerm] = useState('');
  const [externalSearchTerm, setExternalSearchTerm] = useState('');
  const [selectedCoreProducts, setSelectedCoreProducts] = useState<string[]>(
    []
  );
  const [selectedExternalProducts, setSelectedExternalProducts] = useState<
    string[]
  >([]);

  // 映射对话框状态
  const [mappingDialogOpen, setMappingDialogOpen] = useState(false);
  const [mappingStatus, setMappingStatus] = useState<'active' | 'pending'>(
    'active'
  );

  // 详情对话框状态
  const [detailDialogOpen, setDetailDialogOpen] = useState(false);
  const [selectedMapping, setSelectedMapping] = useState<ProductMapping | null>(
    null
  );

  // 批量映射对话框状态
  const [batchDialogOpen, setBatchDialogOpen] = useState(false);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);

      // 获取核心商品数据
      const coreProductsResponse = await frontendApi.get('/api/products', {
        params: {
          page: 1,
          limit: 100,
          include_variants: false,
          include_dimensions: false,
          include_tags: false,
          include_mappings: false,
        },
      });

      const coreProductsData = coreProductsResponse.data.products || [];
      const formattedCoreProducts: CoreProduct[] = coreProductsData.map(
        (product: any) => ({
          id_hashid: product.id_hashid,
          title: product.title,
          vendor: product.vendor || 'Unknown',
          product_type: product.product_type || 'Unknown',
          status: product.status,
          is_active: product.is_active,
          is_available: product.is_available,
          created_at: product.created_at,
        })
      );

      // 获取外部商品数据（根据平台类型）
      let externalProductsData: any[] = [];
      if (platform === 'shopify') {
        const externalProductsResponse = await frontendApi.get(
          '/api/external-products',
          {
            params: {
              page: 1,
              limit: 100,
            },
          }
        );
        externalProductsData = externalProductsResponse.data.products || [];
      }

      const formattedExternalProducts: ExternalProduct[] =
        externalProductsData.map((product: any) => ({
          id_hashid: product.id,
          title: product.title,
          vendor: product.vendor || 'Unknown',
          product_type: product.product_type || 'Unknown',
          status: product.status,
          price: product.price || 0,
          inventory_quantity: product.inventory_quantity || 0,
          created_at: product.created_at,
        }));

      // 获取现有映射关系
      const mappings: ProductMapping[] = [];
      // TODO: 实现获取映射关系的 API 调用

      setCoreProducts(formattedCoreProducts);
      setExternalProducts(formattedExternalProducts);
      setMappings(mappings);
    } catch (err: any) {
      console.error('Failed to fetch data:', err);
      setError(
        err.response?.data?.detail || err.message || 'Failed to fetch data'
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [platform]);

  const getPlatformIcon = () => {
    switch (platform) {
      case 'shopify':
        return <ShopifyIcon />;
      case 'yahoo':
        return <YahooIcon />;
      case 'rakuten':
        return <RakutenIcon />;
      default:
        return <LinkIcon />;
    }
  };

  const getPlatformColor = () => {
    switch (platform) {
      case 'shopify':
        return '#96BF47';
      case 'yahoo':
        return '#FF6600';
      case 'rakuten':
        return '#BF0000';
      default:
        return '#1976d2';
    }
  };

  const getPlatformName = () => {
    switch (platform) {
      case 'shopify':
        return 'Shopify';
      case 'yahoo':
        return 'Yahoo';
      case 'rakuten':
        return '乐天';
      default:
        return 'Unknown';
    }
  };

  const isProductMapped = (
    coreProductId: string,
    externalProductId: string
  ) => {
    return mappings.some(
      mapping =>
        mapping.core_product_id === coreProductId &&
        mapping.external_product_id === externalProductId
    );
  };

  const handleCoreProductSelect = (productId: string) => {
    setSelectedCoreProducts(prev =>
      prev.includes(productId)
        ? prev.filter(id => id !== productId)
        : [...prev, productId]
    );
  };

  const handleExternalProductSelect = (productId: string) => {
    setSelectedExternalProducts(prev =>
      prev.includes(productId)
        ? prev.filter(id => id !== productId)
        : [...prev, productId]
    );
  };

  const handleCreateMapping = () => {
    if (
      selectedCoreProducts.length === 0 ||
      selectedExternalProducts.length === 0
    ) {
      setError('请选择要映射的商品');
      return;
    }

    // 如果选择了多个商品，显示批量映射对话框
    if (
      selectedCoreProducts.length > 1 ||
      selectedExternalProducts.length > 1
    ) {
      setBatchDialogOpen(true);
    } else {
      setMappingDialogOpen(true);
    }
  };

  const handleConfirmMapping = async () => {
    try {
      // 创建映射关系
      for (const coreProductId of selectedCoreProducts) {
        for (const externalProductId of selectedExternalProducts) {
          // TODO: 调用 API 创建映射关系
          console.log('Creating mapping:', {
            core_product_id: coreProductId,
            external_product_id: externalProductId,
            status: mappingStatus,
          });
        }
      }

      setMappingDialogOpen(false);
      setSelectedCoreProducts([]);
      setSelectedExternalProducts([]);
      // 刷新数据
      await fetchData();
    } catch (err: any) {
      console.error('Failed to create mapping:', err);
      setError(
        err.response?.data?.detail || err.message || 'Failed to create mapping'
      );
    }
  };

  const handleRemoveMapping = (mappingId: string) => {
    // 这里应该调用 API 删除映射
    console.log('Removing mapping:', mappingId);
    // 刷新数据
    fetchData();
  };

  const handleViewMappingDetail = (mapping: ProductMapping) => {
    setSelectedMapping(mapping);
    setDetailDialogOpen(true);
  };

  const handleEditMapping = (mapping: ProductMapping) => {
    // 这里应该打开编辑对话框
    console.log('Editing mapping:', mapping);
  };

  const handleRefreshMapping = async (mappingId: string) => {
    // 这里应该调用 API 刷新映射状态
    console.log('Refreshing mapping:', mappingId);
    await fetchData();
  };

  const handleBatchMappingConfirm = async (
    mappings: any[],
    status: 'active' | 'pending'
  ) => {
    // 这里应该调用 API 创建批量映射
    console.log('Creating batch mappings:', mappings, status);
    setBatchDialogOpen(false);
    setSelectedCoreProducts([]);
    setSelectedExternalProducts([]);
    await fetchData();
  };

  const handleBatchMappingCancel = () => {
    setSelectedCoreProducts([]);
    setSelectedExternalProducts([]);
  };

  const filteredCoreProducts = coreProducts.filter(
    product =>
      product.title.toLowerCase().includes(coreSearchTerm.toLowerCase()) ||
      product.vendor.toLowerCase().includes(coreSearchTerm.toLowerCase())
  );

  const filteredExternalProducts = externalProducts.filter(
    product =>
      product.title.toLowerCase().includes(externalSearchTerm.toLowerCase()) ||
      product.vendor.toLowerCase().includes(externalSearchTerm.toLowerCase())
  );

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
          <Avatar sx={{ bgcolor: getPlatformColor() }}>
            {getPlatformIcon()}
          </Avatar>
          <Typography variant='h4' component='h1'>
            {getPlatformName()} 商品映射
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

      {/* 映射操作区域 */}
      {selectedCoreProducts.length > 0 &&
        selectedExternalProducts.length > 0 && (
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
                  {selectedExternalProducts.length} 个外部商品
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

      <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }} spacing={3}>
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
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </Box>

        {/* 外部商品列表 */}
        <Box sx={{ width: "100%" }} md={6}>
          <Card>
            <CardContent>
              <Typography variant='h6' component='h2' mb={2}>
                {getPlatformName()} 商品
              </Typography>

              <TextField
                fullWidth
                placeholder={`搜索${getPlatformName()}商品...`}
                value={externalSearchTerm}
                onChange={e => setExternalSearchTerm(e.target.value)}
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
                      <TableCell>库存</TableCell>
                      <TableCell>状态</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {filteredExternalProducts.map(product => (
                      <TableRow key={product.id_hashid} hover>
                        <TableCell padding='checkbox'>
                          <Checkbox
                            checked={selectedExternalProducts.includes(
                              product.id_hashid
                            )}
                            onChange={() =>
                              handleExternalProductSelect(product.id_hashid)
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
                            ${product.price}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Typography variant='body2'>
                            {product.inventory_quantity}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={product.status}
                            color={
                              product.status === 'active'
                                ? 'success'
                                : 'default'
                            }
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
                    <TableCell>外部商品</TableCell>
                    <TableCell>状态</TableCell>
                    <TableCell>创建时间</TableCell>
                    <TableCell>操作</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {mappings.map(mapping => {
                    const coreProduct = coreProducts.find(
                      p => p.id_hashid === mapping.core_product_id
                    );
                    const externalProduct = externalProducts.find(
                      p => p.id_hashid === mapping.external_product_id
                    );

                    return (
                      <TableRow key={mapping.id} hover>
                        <TableCell>
                          <Typography variant='body2' fontWeight='medium'>
                            {coreProduct?.title || 'Unknown'}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Typography variant='body2'>
                            {externalProduct?.title || 'Unknown'}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={
                              mapping.status === 'active'
                                ? '活跃'
                                : mapping.status === 'pending'
                                  ? '待处理'
                                  : '错误'
                            }
                            color={
                              mapping.status === 'active'
                                ? 'success'
                                : mapping.status === 'pending'
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
                            <Tooltip title='编辑映射'>
                              <IconButton
                                size='small'
                                onClick={() => handleEditMapping(mapping)}
                              >
                                <EditIcon />
                              </IconButton>
                            </Tooltip>
                            <Tooltip title='删除映射'>
                              <IconButton
                                size='small'
                                color='error'
                                onClick={() => handleRemoveMapping(mapping.id)}
                              >
                                <UnlinkIcon />
                              </IconButton>
                            </Tooltip>
                          </Box>
                        </TableCell>
                      </TableRow>
                    );
                  })}
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
            您即将创建 {selectedCoreProducts.length} 个核心商品与{' '}
            {selectedExternalProducts.length} 个外部商品的映射关系。
          </Typography>

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
      <MappingDetailDialog
        open={detailDialogOpen}
        onClose={() => setDetailDialogOpen(false)}
        mapping={selectedMapping}
        coreProduct={
          selectedMapping
            ? coreProducts.find(
                p => p.id_hashid === selectedMapping.core_product_id
              ) || null
            : null
        }
        externalProduct={
          selectedMapping
            ? externalProducts.find(
                p => p.id_hashid === selectedMapping.external_product_id
              ) || null
            : null
        }
        platform={platform}
        onEdit={handleEditMapping}
        onDelete={handleRemoveMapping}
        onRefresh={handleRefreshMapping}
      />

      {/* 批量映射对话框 */}
      <BatchMappingDialog
        open={batchDialogOpen}
        onClose={() => setBatchDialogOpen(false)}
        coreProducts={selectedCoreProducts
          .map(id => coreProducts.find(p => p.id_hashid === id)!)
          .filter(Boolean)}
        externalProducts={selectedExternalProducts
          .map(id => externalProducts.find(p => p.id_hashid === id)!)
          .filter(Boolean)}
        platform={getPlatformName()}
        onConfirm={handleBatchMappingConfirm}
        onCancel={handleBatchMappingCancel}
      />
    </Box>
  );
}
