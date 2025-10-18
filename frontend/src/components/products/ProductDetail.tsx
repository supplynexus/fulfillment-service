'use client';

import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Grid,
  Chip,
  Avatar,
  Alert,
  CircularProgress,
  Tabs,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  Tooltip,
  Badge,
  Divider,
} from '@mui/material';
import {
  ArrowBack as ArrowBackIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Inventory as ProductIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';
import { useRouter } from 'next/navigation';
import { frontendApi } from '@/lib/api';
import { Product } from '@/types/product';

interface ProductDetailProps {
  productHashId: string;
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role='tabpanel'
      hidden={value !== index}
      id={`product-tabpanel-${index}`}
      aria-labelledby={`product-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

export function ProductDetail({ productHashId }: ProductDetailProps) {
  const router = useRouter();
  const [product, setProduct] = useState<Product | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tabValue, setTabValue] = useState(0);
  const [expandedVariants, setExpandedVariants] = useState<Set<string>>(
    new Set()
  );

  const fetchProduct = async (isRefresh = false) => {
    try {
      if (isRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }
      setError(null);

      const response = await frontendApi.get(`/api/products/${productHashId}`, {
        params: {
          include_variants: true,
          include_dimensions: true,
          include_tags: true,
          include_mappings: true,
        },
      });

      setProduct(response.data);
    } catch (err: any) {
      console.error('Failed to fetch product:', err);
      setError(err.response?.data?.detail || 'Failed to fetch product');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchProduct();
  }, [productHashId]);

  const handleBack = () => {
    router.push('/products');
  };

  const handleEdit = () => {
    router.push(`/products/${productHashId}/edit`);
  };

  const handleDelete = () => {
    // TODO: 实现删除功能
    console.log('Delete product:', productHashId);
  };

  const handleRefresh = () => {
    fetchProduct(true);
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleToggleVariant = (variantHashId: string) => {
    const newExpanded = new Set(expandedVariants);
    if (newExpanded.has(variantHashId)) {
      newExpanded.delete(variantHashId);
    } else {
      newExpanded.add(variantHashId);
    }
    setExpandedVariants(newExpanded);
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

  if (error || !product) {
    return (
      <Box>
        <Alert severity='error' sx={{ mb: 2 }}>
          {error || 'Product not found'}
        </Alert>
        <Button
          variant='outlined'
          startIcon={<ArrowBackIcon />}
          onClick={handleBack}
        >
          返回商品列表
        </Button>
      </Box>
    );
  }

  return (
    <Box>
      {/* 头部操作栏 */}
      <Box
        display='flex'
        justifyContent='space-between'
        alignItems='center'
        mb={3}
      >
        <Box display='flex' alignItems='center' gap={2}>
          <Button
            variant='outlined'
            startIcon={<ArrowBackIcon />}
            onClick={handleBack}
          >
            返回
          </Button>
          <Typography variant='h4' component='h1'>
            {product.title}
          </Typography>
        </Box>
        <Box display='flex' gap={2}>
          <Tooltip title='刷新商品数据'>
            <IconButton
              onClick={handleRefresh}
              disabled={refreshing}
              color='primary'
              sx={{
                animation: refreshing ? 'spin 1s linear infinite' : 'none',
                '@keyframes spin': {
                  '0%': { transform: 'rotate(0deg)' },
                  '100%': { transform: 'rotate(360deg)' },
                },
              }}
            >
              <RefreshIcon />
            </IconButton>
          </Tooltip>
          <Button
            variant='outlined'
            startIcon={<EditIcon />}
            onClick={handleEdit}
          >
            编辑
          </Button>
          <Button
            variant='outlined'
            color='error'
            startIcon={<DeleteIcon />}
            onClick={handleDelete}
          >
            删除
          </Button>
        </Box>
      </Box>

      {/* 商品基本信息 */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
            <Box sx={{ width: "100%" }} md={3}>
              <Box display='flex' justifyContent='center'>
                <Avatar
                  src={product.images?.[0]?.url || product.images?.[0]}
                  variant='rounded'
                  sx={{ width: 120, height: 120 }}
                >
                  <ProductIcon sx={{ fontSize: 60 }} />
                </Avatar>
              </Box>
            </Box>
            <Box sx={{ width: "100%" }} md={9}>
              <Typography variant='h5' gutterBottom>
                {product.title}
              </Typography>
              <Typography variant='body1' color='text.secondary' paragraph>
                {product.description || '暂无描述'}
              </Typography>

              <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }} sx={{ mb: 2 }}>
                <Box sx={{ width: "50%" }} sm={3}>
                  <Typography variant='caption' color='text.secondary'>
                    状态
                  </Typography>
                  <Box>
                    <Chip
                      label={product.status}
                      color={getStatusColor(product.status) as any}
                      size='small'
                    />
                  </Box>
                </Box>
                <Box sx={{ width: "50%" }} sm={3}>
                  <Typography variant='caption' color='text.secondary'>
                    可用性
                  </Typography>
                  <Box>
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
                  </Box>
                </Box>
                <Box sx={{ width: "50%" }} sm={3}>
                  <Typography variant='caption' color='text.secondary'>
                    类型
                  </Typography>
                  <Typography variant='body2'>
                    {product.product_type || '-'}
                  </Typography>
                </Box>
                <Box sx={{ width: "50%" }} sm={3}>
                  <Typography variant='caption' color='text.secondary'>
                    供应商
                  </Typography>
                  <Typography variant='body2'>
                    {product.vendor || '-'}
                  </Typography>
                </Box>
              </Box>

              <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
                <Box sx={{ width: "50%" }} sm={3}>
                  <Typography variant='caption' color='text.secondary'>
                    Handle
                  </Typography>
                  <Typography variant='body2'>
                    {product.handle || '-'}
                  </Typography>
                </Box>
                <Box sx={{ width: "50%" }} sm={3}>
                  <Typography variant='caption' color='text.secondary'>
                    变体数量
                  </Typography>
                  <Typography variant='body2'>
                    {product.variants.length}
                  </Typography>
                </Box>
                <Box sx={{ width: "50%" }} sm={3}>
                  <Typography variant='caption' color='text.secondary'>
                    标签数量
                  </Typography>
                  <Typography variant='body2'>{product.tags.length}</Typography>
                </Box>
                <Box sx={{ width: "50%" }} sm={3}>
                  <Typography variant='caption' color='text.secondary'>
                    映射数量
                  </Typography>
                  <Typography variant='body2'>
                    {product.mappings.length}
                  </Typography>
                </Box>
              </Box>
            </Box>
          </Box>
        </CardContent>
      </Card>

      {/* 标签显示 */}
      {product.tags.length > 0 && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant='h6' gutterBottom>
              商品标签
            </Typography>
            <Box display='flex' gap={1} flexWrap='wrap'>
              {product.tags.map(tag => (
                <Chip
                  key={tag.id_hashid}
                  label={tag.name}
                  color={tag.is_primary ? 'primary' : 'default'}
                  variant={tag.is_primary ? 'filled' : 'outlined'}
                />
              ))}
            </Box>
          </CardContent>
        </Card>
      )}

      {/* 详细信息标签页 */}
      <Card>
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs value={tabValue} onChange={handleTabChange}>
            <Tab label={`变体 (${product.variants.length})`} />
            <Tab label={`维度 (${product.dimensions.length})`} />
            <Tab label={`映射 (${product.mappings.length})`} />
          </Tabs>
        </Box>

        {/* 变体标签页 */}
        <TabPanel value={tabValue} index={0}>
          <Typography variant='h6' gutterBottom>
            商品变体
          </Typography>
          {product.variants.length > 0 ? (
            <TableContainer component={Paper} variant='outlined'>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>SKU</TableCell>
                    <TableCell>属性</TableCell>
                    <TableCell>价格</TableCell>
                    <TableCell>库存</TableCell>
                    <TableCell>状态</TableCell>
                    <TableCell>操作</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {product.variants.map(variant => (
                    <React.Fragment key={variant.id_hashid}>
                      <TableRow hover>
                        <TableCell>
                          <Typography variant='body2'>
                            {variant.sku || '-'}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Box display='flex' gap={0.5} flexWrap='wrap'>
                            {Object.entries(variant.attributes).map(
                              ([key, value]) => (
                                <Chip
                                  key={key}
                                  label={`${key}: ${value}`}
                                  size='small'
                                  variant='outlined'
                                />
                              )
                            )}
                          </Box>
                        </TableCell>
                        <TableCell>
                          <Typography variant='body2'>
                            ${variant.price || 0}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Typography variant='body2'>
                            {variant.inventory_quantity}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={variant.is_active ? '活跃' : '非活跃'}
                            color={variant.is_active ? 'success' : 'default'}
                            size='small'
                          />
                        </TableCell>
                        <TableCell>
                          <Tooltip
                            title={
                              expandedVariants.has(variant.id_hashid)
                                ? '收起'
                                : '展开'
                            }
                          >
                            <IconButton
                              size='small'
                              onClick={() =>
                                handleToggleVariant(variant.id_hashid)
                              }
                            >
                              {expandedVariants.has(variant.id_hashid) ? (
                                <ExpandLessIcon />
                              ) : (
                                <ExpandMoreIcon />
                              )}
                            </IconButton>
                          </Tooltip>
                        </TableCell>
                      </TableRow>

                      {/* 展开的变体详情 */}
                      {expandedVariants.has(variant.id_hashid) && (
                        <TableRow>
                          <TableCell colSpan={6} sx={{ py: 0 }}>
                            <Box sx={{ pl: 4, pr: 2, pb: 2 }}>
                              <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
                                <Box sx={{ width: "50%" }} sm={3}>
                                  <Typography
                                    variant='caption'
                                    color='text.secondary'
                                  >
                                    条码
                                  </Typography>
                                  <Typography variant='body2'>
                                    {variant.barcode || '-'}
                                  </Typography>
                                </Box>
                                <Box sx={{ width: "50%" }} sm={3}>
                                  <Typography
                                    variant='caption'
                                    color='text.secondary'
                                  >
                                    对比价格
                                  </Typography>
                                  <Typography variant='body2'>
                                    ${variant.compare_at_price || 0}
                                  </Typography>
                                </Box>
                                <Box sx={{ width: "50%" }} sm={3}>
                                  <Typography
                                    variant='caption'
                                    color='text.secondary'
                                  >
                                    成本价格
                                  </Typography>
                                  <Typography variant='body2'>
                                    ${variant.cost_price || 0}
                                  </Typography>
                                </Box>
                                <Box sx={{ width: "50%" }} sm={3}>
                                  <Typography
                                    variant='caption'
                                    color='text.secondary'
                                  >
                                    重量
                                  </Typography>
                                  <Typography variant='body2'>
                                    {variant.weight || '-'} kg
                                  </Typography>
                                </Box>
                                {/* 外部变体ID显示 */}
                                {product.mappings.length > 0 && (
                                  <Box sx={{ width: "100%" }}>
                                    <Typography
                                      variant='caption'
                                      color='text.secondary'
                                    >
                                      外部系统映射
                                    </Typography>
                                    <Box sx={{ mt: 1 }}>
                                      {product.mappings
                                        .filter(
                                          mapping => mapping.external_variant_id
                                        )
                                        .map(mapping => (
                                          <Chip
                                            key={mapping.id_hashid}
                                            label={`${mapping.external_system_name}: ${mapping.external_variant_id}`}
                                            size='small'
                                            variant='outlined'
                                            sx={{ mr: 1, mb: 1 }}
                                          />
                                        ))}
                                    </Box>
                                  </Box>
                                )}
                              </Box>
                            </Box>
                          </TableCell>
                        </TableRow>
                      )}
                    </React.Fragment>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          ) : (
            <Typography variant='body2' color='text.secondary'>
              暂无变体
            </Typography>
          )}
        </TabPanel>

        {/* 维度标签页 */}
        <TabPanel value={tabValue} index={1}>
          <Typography variant='h6' gutterBottom>
            商品维度
          </Typography>
          {product.dimensions.length > 0 ? (
            <TableContainer component={Paper} variant='outlined'>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>维度名称</TableCell>
                    <TableCell>显示名称</TableCell>
                    <TableCell>类型</TableCell>
                    <TableCell>选项</TableCell>
                    <TableCell>必需</TableCell>
                    <TableCell>状态</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {product.dimensions.map(dimension => (
                    <TableRow key={dimension.id_hashid} hover>
                      <TableCell>
                        <Typography variant='body2'>
                          {dimension.dimension_name}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant='body2'>
                          {dimension.display_name || '-'}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={dimension.dimension_type}
                          size='small'
                          variant='outlined'
                        />
                      </TableCell>
                      <TableCell>
                        <Box display='flex' gap={0.5} flexWrap='wrap'>
                          {dimension.options?.slice(0, 3).map(option => (
                            <Chip key={option} label={option} size='small' />
                          ))}
                          {dimension.options &&
                            dimension.options.length > 3 && (
                              <Chip
                                label={`+${dimension.options.length - 3}`}
                                size='small'
                                variant='outlined'
                              />
                            )}
                        </Box>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={dimension.is_required ? '是' : '否'}
                          color={dimension.is_required ? 'primary' : 'default'}
                          size='small'
                        />
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={dimension.is_active ? '活跃' : '非活跃'}
                          color={dimension.is_active ? 'success' : 'default'}
                          size='small'
                        />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          ) : (
            <Typography variant='body2' color='text.secondary'>
              暂无维度
            </Typography>
          )}
        </TabPanel>

        {/* 映射标签页 */}
        <TabPanel value={tabValue} index={2}>
          <Typography variant='h6' gutterBottom>
            外部系统映射
          </Typography>
          {product.mappings.length > 0 ? (
            <TableContainer component={Paper} variant='outlined'>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>外部系统</TableCell>
                    <TableCell>外部商品ID</TableCell>
                    <TableCell>外部变体ID</TableCell>
                    <TableCell>映射类型</TableCell>
                    <TableCell>同步方向</TableCell>
                    <TableCell>同步状态</TableCell>
                    <TableCell>最后同步</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {product.mappings.map(mapping => (
                    <TableRow key={mapping.id_hashid} hover>
                      <TableCell>
                        <Typography variant='body2'>
                          {mapping.external_system_name}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant='body2'>
                          {mapping.external_product_id}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant='body2'>
                          {mapping.external_variant_id || '-'}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={mapping.mapping_type}
                          size='small'
                          variant='outlined'
                        />
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={mapping.sync_direction}
                          size='small'
                          variant='outlined'
                        />
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={mapping.sync_status}
                          color={
                            mapping.sync_status === 'synced'
                              ? 'success'
                              : 'default'
                          }
                          size='small'
                        />
                      </TableCell>
                      <TableCell>
                        <Typography variant='body2'>
                          {mapping.last_synced_at
                            ? formatDate(mapping.last_synced_at)
                            : '-'}
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          ) : (
            <Typography variant='body2' color='text.secondary'>
              暂无映射
            </Typography>
          )}
        </TabPanel>
      </Card>
    </Box>
  );
}
