'use client';

import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  Grid,
  Card,
  CardContent,
  Avatar,
  Chip,
  Divider,
  IconButton,
  Tooltip,
  Alert,
  LinearProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
} from '@mui/material';
import {
  Close as CloseIcon,
  Link as LinkIcon,
  LinkOff as UnlinkIcon,
  Edit as EditIcon,
  Refresh as RefreshIcon,
  Storefront as ShopifyIcon,
  Public as YahooIcon,
  Storefront as RakutenIcon,
} from '@mui/icons-material';

interface CoreProduct {
  id_hashid: string;
  title: string;
  vendor: string;
  product_type: string;
  status: string;
  is_active: boolean;
  is_available: boolean;
  description?: string;
  images?: string[];
  variants?: any[];
  tags?: any[];
  created_at: string;
}

interface ExternalProduct {
  id_hashid: string;
  title: string;
  vendor: string;
  product_type: string;
  status: string;
  price: number;
  compare_at_price?: number;
  inventory_quantity: number;
  sku?: string;
  images?: string[];
  variants?: any[];
  created_at: string;
}

interface ProductMapping {
  id: string;
  core_product_id: string;
  external_product_id: string;
  status: 'active' | 'pending' | 'error';
  created_at: string;
  updated_at?: string;
  sync_status?: string;
  last_synced_at?: string;
  error_message?: string;
}

interface MappingDetailDialogProps {
  open: boolean;
  onClose: () => void;
  mapping: ProductMapping | null;
  coreProduct: CoreProduct | null;
  externalProduct: ExternalProduct | null;
  platform: string;
  onEdit?: (mapping: ProductMapping) => void;
  onDelete?: (mappingId: string) => void;
  onRefresh?: (mappingId: string) => void;
}

export function MappingDetailDialog({
  open,
  onClose,
  mapping,
  coreProduct,
  externalProduct,
  platform,
  onEdit,
  onDelete,
  onRefresh,
}: MappingDetailDialogProps) {
  const [loading, setLoading] = useState(false);

  const getPlatformIcon = (platform: string) => {
    switch (platform.toLowerCase()) {
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

  const getPlatformColor = (platform: string) => {
    switch (platform.toLowerCase()) {
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

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'success';
      case 'pending':
        return 'warning';
      case 'error':
        return 'error';
      default:
        return 'default';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'active':
        return '活跃';
      case 'pending':
        return '待处理';
      case 'error':
        return '错误';
      default:
        return '未知';
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

  const handleRefresh = async () => {
    if (!mapping || !onRefresh) return;

    setLoading(true);
    try {
      await onRefresh(mapping.id);
    } catch (error) {
      console.error('Failed to refresh mapping:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = () => {
    if (mapping && onEdit) {
      onEdit(mapping);
    }
  };

  const handleDelete = () => {
    if (mapping && onDelete) {
      onDelete(mapping.id);
    }
  };

  if (!mapping || !coreProduct || !externalProduct) {
    return null;
  }

  return (
    <Dialog open={open} onClose={onClose} maxWidth='lg' fullWidth>
      <DialogTitle>
        <Box display='flex' justifyContent='space-between' alignItems='center'>
          <Box display='flex' alignItems='center' gap={2}>
            <Avatar sx={{ bgcolor: getPlatformColor(platform) }}>
              {getPlatformIcon(platform)}
            </Avatar>
            <Box>
              <Typography variant='h6'>商品映射详情</Typography>
              <Typography variant='body2' color='text.secondary'>
                {platform} 平台映射关系
              </Typography>
            </Box>
          </Box>
          <Box display='flex' gap={1}>
            <Tooltip title='刷新状态'>
              <IconButton onClick={handleRefresh} disabled={loading}>
                <RefreshIcon />
              </IconButton>
            </Tooltip>
            <Tooltip title='编辑映射'>
              <IconButton onClick={handleEdit}>
                <EditIcon />
              </IconButton>
            </Tooltip>
            <Tooltip title='删除映射'>
              <IconButton onClick={handleDelete} color='error'>
                <UnlinkIcon />
              </IconButton>
            </Tooltip>
            <IconButton onClick={onClose}>
              <CloseIcon />
            </IconButton>
          </Box>
        </Box>
      </DialogTitle>

      <DialogContent>
        {/* 映射状态信息 */}
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }} spacing={2} alignItems='center'>
              <Box sx={{ width: "100%" }} md={3}>
                <Typography variant='subtitle2' color='text.secondary'>
                  映射状态
                </Typography>
                <Chip
                  label={getStatusText(mapping.status)}
                  color={getStatusColor(mapping.status) as any}
                  size='small'
                />
              </Box>
              <Box sx={{ width: "100%" }} md={3}>
                <Typography variant='subtitle2' color='text.secondary'>
                  创建时间
                </Typography>
                <Typography variant='body2'>
                  {formatDate(mapping.created_at)}
                </Typography>
              </Box>
              <Box sx={{ width: "100%" }} md={3}>
                <Typography variant='subtitle2' color='text.secondary'>
                  最后更新
                </Typography>
                <Typography variant='body2'>
                  {mapping.updated_at ? formatDate(mapping.updated_at) : '-'}
                </Typography>
              </Box>
              <Box sx={{ width: "100%" }} md={3}>
                <Typography variant='subtitle2' color='text.secondary'>
                  最后同步
                </Typography>
                <Typography variant='body2'>
                  {mapping.last_synced_at
                    ? formatDate(mapping.last_synced_at)
                    : '-'}
                </Typography>
              </Box>
            </Box>

            {mapping.error_message && (
              <Alert severity='error' sx={{ mt: 2 }}>
                <Typography variant='body2'>
                  <strong>错误信息：</strong>
                  {mapping.error_message}
                </Typography>
              </Alert>
            )}

            {mapping.status === 'pending' && (
              <Box sx={{ mt: 2 }}>
                <Typography variant='body2' color='text.secondary' gutterBottom>
                  同步进度
                </Typography>
                <LinearProgress />
              </Box>
            )}
          </CardContent>
        </Card>

        <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }} spacing={3}>
          {/* 核心商品信息 */}
          <Box sx={{ width: "100%" }} md={6}>
            <Card>
              <CardContent>
                <Typography variant='h6' gutterBottom>
                  核心商品
                </Typography>

                <Box display='flex' alignItems='center' gap={2} mb={2}>
                  {coreProduct.images && coreProduct.images.length > 0 && (
                    <Avatar
                      src={coreProduct.images[0]}
                      variant='rounded'
                      sx={{ width: 60, height: 60 }}
                    />
                  )}
                  <Box>
                    <Typography variant='h6' component='div'>
                      {coreProduct.title}
                    </Typography>
                    <Typography variant='body2' color='text.secondary'>
                      {coreProduct.vendor} • {coreProduct.product_type}
                    </Typography>
                  </Box>
                </Box>

                <Box mb={2}>
                  <Typography
                    variant='subtitle2'
                    color='text.secondary'
                    gutterBottom
                  >
                    商品状态
                  </Typography>
                  <Box display='flex' gap={1}>
                    <Chip
                      label={coreProduct.status}
                      color={coreProduct.is_active ? 'success' : 'default'}
                      size='small'
                    />
                    <Chip
                      label={coreProduct.is_available ? '可用' : '不可用'}
                      color={coreProduct.is_available ? 'success' : 'error'}
                      size='small'
                    />
                  </Box>
                </Box>

                {coreProduct.description && (
                  <Box mb={2}>
                    <Typography
                      variant='subtitle2'
                      color='text.secondary'
                      gutterBottom
                    >
                      商品描述
                    </Typography>
                    <Typography variant='body2'>
                      {coreProduct.description}
                    </Typography>
                  </Box>
                )}

                {coreProduct.tags && coreProduct.tags.length > 0 && (
                  <Box mb={2}>
                    <Typography
                      variant='subtitle2'
                      color='text.secondary'
                      gutterBottom
                    >
                      标签
                    </Typography>
                    <Box display='flex' gap={0.5} flexWrap='wrap'>
                      {coreProduct.tags.map((tag, index) => (
                        <Chip
                          key={index}
                          label={tag.name || tag}
                          size='small'
                          color={tag.is_primary ? 'primary' : 'default'}
                        />
                      ))}
                    </Box>
                  </Box>
                )}

                {coreProduct.variants && coreProduct.variants.length > 0 && (
                  <Box>
                    <Typography
                      variant='subtitle2'
                      color='text.secondary'
                      gutterBottom
                    >
                      变体信息 ({coreProduct.variants.length})
                    </Typography>
                    <TableContainer
                      component={Paper}
                      variant='outlined'
                      sx={{ maxHeight: 200 }}
                    >
                      <Table size='small'>
                        <TableHead>
                          <TableRow>
                            <TableCell>SKU</TableCell>
                            <TableCell>价格</TableCell>
                            <TableCell>库存</TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {coreProduct.variants
                            .slice(0, 3)
                            .map((variant, index) => (
                              <TableRow key={index}>
                                <TableCell>{variant.sku || '-'}</TableCell>
                                <TableCell>${variant.price || 0}</TableCell>
                                <TableCell>
                                  {variant.inventory_quantity || 0}
                                </TableCell>
                              </TableRow>
                            ))}
                        </TableBody>
                      </Table>
                    </TableContainer>
                    {coreProduct.variants.length > 3 && (
                      <Typography variant='caption' color='text.secondary'>
                        还有 {coreProduct.variants.length - 3} 个变体...
                      </Typography>
                    )}
                  </Box>
                )}
              </CardContent>
            </Card>
          </Box>

          {/* 外部商品信息 */}
          <Box sx={{ width: "100%" }} md={6}>
            <Card>
              <CardContent>
                <Typography variant='h6' gutterBottom>
                  {platform} 商品
                </Typography>

                <Box display='flex' alignItems='center' gap={2} mb={2}>
                  {externalProduct.images &&
                    externalProduct.images.length > 0 && (
                      <Avatar
                        src={externalProduct.images[0]}
                        variant='rounded'
                        sx={{ width: 60, height: 60 }}
                      />
                    )}
                  <Box>
                    <Typography variant='h6' component='div'>
                      {externalProduct.title}
                    </Typography>
                    <Typography variant='body2' color='text.secondary'>
                      {externalProduct.vendor} • {externalProduct.product_type}
                    </Typography>
                  </Box>
                </Box>

                <Box mb={2}>
                  <Typography
                    variant='subtitle2'
                    color='text.secondary'
                    gutterBottom
                  >
                    价格信息
                  </Typography>
                  <Box display='flex' gap={2}>
                    <Typography variant='h6' color='primary'>
                      ${externalProduct.price}
                    </Typography>
                    {externalProduct.compare_at_price && (
                      <Typography
                        variant='body2'
                        sx={{
                          textDecoration: 'line-through',
                          color: 'text.secondary',
                        }}
                      >
                        ${externalProduct.compare_at_price}
                      </Typography>
                    )}
                  </Box>
                </Box>

                <Box mb={2}>
                  <Typography
                    variant='subtitle2'
                    color='text.secondary'
                    gutterBottom
                  >
                    库存信息
                  </Typography>
                  <Typography variant='body2'>
                    可用库存: {externalProduct.inventory_quantity}
                  </Typography>
                  {externalProduct.sku && (
                    <Typography variant='body2'>
                      SKU: {externalProduct.sku}
                    </Typography>
                  )}
                </Box>

                <Box mb={2}>
                  <Typography
                    variant='subtitle2'
                    color='text.secondary'
                    gutterBottom
                  >
                    商品状态
                  </Typography>
                  <Chip
                    label={externalProduct.status}
                    color={
                      externalProduct.status === 'active'
                        ? 'success'
                        : 'default'
                    }
                    size='small'
                  />
                </Box>

                {externalProduct.variants &&
                  externalProduct.variants.length > 0 && (
                    <Box>
                      <Typography
                        variant='subtitle2'
                        color='text.secondary'
                        gutterBottom
                      >
                        变体信息 ({externalProduct.variants.length})
                      </Typography>
                      <TableContainer
                        component={Paper}
                        variant='outlined'
                        sx={{ maxHeight: 200 }}
                      >
                        <Table size='small'>
                          <TableHead>
                            <TableRow>
                              <TableCell>SKU</TableCell>
                              <TableCell>价格</TableCell>
                              <TableCell>库存</TableCell>
                            </TableRow>
                          </TableHead>
                          <TableBody>
                            {externalProduct.variants
                              .slice(0, 3)
                              .map((variant, index) => (
                                <TableRow key={index}>
                                  <TableCell>{variant.sku || '-'}</TableCell>
                                  <TableCell>${variant.price || 0}</TableCell>
                                  <TableCell>
                                    {variant.inventory_quantity || 0}
                                  </TableCell>
                                </TableRow>
                              ))}
                          </TableBody>
                        </Table>
                      </TableContainer>
                      {externalProduct.variants.length > 3 && (
                        <Typography variant='caption' color='text.secondary'>
                          还有 {externalProduct.variants.length - 3} 个变体...
                        </Typography>
                      )}
                    </Box>
                  )}
              </CardContent>
            </Card>
          </Box>
        </Box>
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose}>关闭</Button>
        <Button onClick={handleEdit} variant='outlined'>
          编辑映射
        </Button>
        <Button onClick={handleDelete} color='error' variant='outlined'>
          删除映射
        </Button>
      </DialogActions>
    </Dialog>
  );
}
