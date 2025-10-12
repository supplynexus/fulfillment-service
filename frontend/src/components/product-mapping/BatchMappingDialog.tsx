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
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
  CircularProgress,
  Grid,
  Card,
  CardContent,
  Divider,
} from '@mui/material';
import {
  Link as LinkIcon,
  Warning as WarningIcon,
  CheckCircle as CheckIcon,
} from '@mui/icons-material';
import { frontendApi } from '@/lib/api';
import { frontendLogger } from '@/lib/frontend-logger';

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

interface ExternalProduct {
  id: string;
  title: string;
  description?: string;
  tags: string[];
  variants: any[];
  created_at: string;
  updated_at: string;
  visible: boolean;
}

interface BatchMapping {
  core_product_id: string;
  core_product_title: string;
  external_product_id: string;
  external_product_title: string;
  mapping_type: string;
  sync_direction: string;
  sync_status: string;
}

interface BatchMappingDialogProps {
  open: boolean;
  onClose: () => void;
  coreProducts: CoreProduct[];
  externalProducts: ExternalProduct[];
  platform: string;
  onConfirm: (mappings: BatchMapping[], status: 'active' | 'pending') => void;
  onCancel: () => void;
}

export function BatchMappingDialog({
  open,
  onClose,
  coreProducts,
  externalProducts,
  platform,
  onConfirm,
  onCancel,
}: BatchMappingDialogProps) {
  const [mappingStatus, setMappingStatus] = useState<'active' | 'pending'>('active');
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 生成所有可能的映射组合
  const generateMappings = (): BatchMapping[] => {
    const mappings: BatchMapping[] = [];
    
    for (const coreProduct of coreProducts) {
      for (const externalProduct of externalProducts) {
        mappings.push({
          core_product_id: coreProduct.id_hashid,
          core_product_title: coreProduct.title,
          external_product_id: externalProduct.id,
          external_product_title: externalProduct.title,
          mapping_type: 'manual',
          sync_direction: 'bidirectional',
          sync_status: mappingStatus,
        });
      }
    }
    
    return mappings;
  };

  const mappings = generateMappings();

  const handleConfirm = async () => {
    if (mappings.length === 0) {
      setError('没有可创建的映射');
      return;
    }

    try {
      setCreating(true);
      setError(null);

      frontendLogger.info('🔗 开始创建批量映射', {
        count: mappings.length,
        platform,
      });

      // 获取外部系统ID
      const externalSystemsResponse = await frontendApi.get('/api/external-systems', {
        params: { system_type: platform.toUpperCase() }
      });
      
      const externalSystem = externalSystemsResponse.data.external_systems?.[0];
      if (!externalSystem) {
        throw new Error(`未找到${platform}外部系统配置`);
      }

      // 批量创建映射
      const createPromises = mappings.map(async (mapping) => {
        const mappingData = {
          core_product_id_hashid: mapping.core_product_id,
          core_variant_id_hashid: null, // 暂时不映射变体
          external_system_id_hashid: externalSystem.id_hashid,
          external_product_id: mapping.external_product_id,
          external_variant_id: null, // 暂时不映射变体
          mapping_type: mapping.mapping_type,
          sync_direction: mapping.sync_direction,
          sync_status: mapping.sync_status,
        };

        return frontendApi.post('/api/products/mappings/', mappingData);
      });

      await Promise.all(createPromises);

      frontendLogger.info('✅ 批量映射创建成功', {
        count: mappings.length,
        platform,
      });

      onConfirm(mappings, mappingStatus);
    } catch (error) {
      frontendLogger.error('❌ 批量映射创建失败', {
        error: String(error),
        platform,
      });
      setError('批量映射创建失败');
    } finally {
      setCreating(false);
    }
  };

  const handleClose = () => {
    onClose();
    setError(null);
    setMappingStatus('active');
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="lg" fullWidth>
      <DialogTitle>
        <Box display="flex" alignItems="center" gap={2}>
          <LinkIcon color="primary" />
          <Typography variant="h6">批量创建映射</Typography>
        </Box>
      </DialogTitle>
      
      <DialogContent>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        <Box mb={3}>
          <Typography variant="body2" color="text.secondary" paragraph>
            您即将创建 {coreProducts.length} 个核心商品与 {externalProducts.length} 个 {platform} 商品的映射关系，
            总共将创建 {mappings.length} 个映射。
          </Typography>
          
          <Alert severity="warning" sx={{ mb: 2 }}>
            <Typography variant="body2">
              注意：这将创建所有可能的映射组合。如果某些商品已经存在映射，可能会创建重复的映射关系。
            </Typography>
          </Alert>
        </Box>

        <Grid container spacing={2} sx={{ mb: 3 }}>
          <Grid item xs={12} md={6}>
            <Card variant="outlined">
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  核心商品 ({coreProducts.length})
                </Typography>
                <Box sx={{ maxHeight: 200, overflow: 'auto' }}>
                  {coreProducts.map((product) => (
                    <Box key={product.id_hashid} sx={{ mb: 1 }}>
                      <Typography variant="body2" fontWeight="medium">
                        {product.title}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {product.vendor} • {product.variants?.length || 0} 变体
                      </Typography>
                    </Box>
                  ))}
                </Box>
              </CardContent>
            </Card>
          </Grid>
          
          <Grid item xs={12} md={6}>
            <Card variant="outlined">
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  {platform} 商品 ({externalProducts.length})
                </Typography>
                <Box sx={{ maxHeight: 200, overflow: 'auto' }}>
                  {externalProducts.map((product) => (
                    <Box key={product.id} sx={{ mb: 1 }}>
                      <Typography variant="body2" fontWeight="medium">
                        {product.title}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {product.variants?.length || 0} 变体
                      </Typography>
                    </Box>
                  ))}
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        <Divider sx={{ my: 2 }} />

        <FormControl fullWidth sx={{ mb: 2 }}>
          <InputLabel>映射状态</InputLabel>
          <Select
            value={mappingStatus}
            onChange={(e) => setMappingStatus(e.target.value as 'active' | 'pending')}
            label="映射状态"
          >
            <MenuItem value="active">活跃</MenuItem>
            <MenuItem value="pending">待处理</MenuItem>
          </Select>
        </FormControl>

        <Typography variant="h6" gutterBottom>
          即将创建的映射 ({mappings.length})
        </Typography>
        
        <TableContainer component={Paper} variant="outlined" sx={{ maxHeight: 300 }}>
          <Table size="small" stickyHeader>
            <TableHead>
              <TableRow>
                <TableCell>核心商品</TableCell>
                <TableCell>{platform} 商品</TableCell>
                <TableCell>状态</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {mappings.slice(0, 50).map((mapping, index) => (
                <TableRow key={index}>
                  <TableCell>
                    <Typography variant="body2" fontWeight="medium">
                      {mapping.core_product_title}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">
                      {mapping.external_product_title}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={mapping.sync_status === 'active' ? '活跃' : '待处理'}
                      color={mapping.sync_status === 'active' ? 'success' : 'warning'}
                      size="small"
                    />
                  </TableCell>
                </TableRow>
              ))}
              {mappings.length > 50 && (
                <TableRow>
                  <TableCell colSpan={3} align="center">
                    ... 还有 {mappings.length - 50} 个映射
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </DialogContent>
      
      <DialogActions>
        <Button onClick={handleClose} disabled={creating}>
          取消
        </Button>
        <Button
          onClick={handleConfirm}
          variant="contained"
          disabled={creating || mappings.length === 0}
          startIcon={creating ? <CircularProgress size={16} /> : <CheckIcon />}
        >
          {creating ? '创建中...' : `确认创建 ${mappings.length} 个映射`}
        </Button>
      </DialogActions>
    </Dialog>
  );
}