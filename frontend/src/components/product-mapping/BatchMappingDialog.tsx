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
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
  LinearProgress,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  Close as CloseIcon,
  Link as LinkIcon,
  Delete as DeleteIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';

interface SelectedProduct {
  id_hashid: string;
  title: string;
  vendor: string;
  product_type: string;
}

interface BatchMappingDialogProps {
  open: boolean;
  onClose: () => void;
  coreProducts: SelectedProduct[];
  externalProducts: SelectedProduct[];
  platform: string;
  onConfirm: (mappings: BatchMapping[], status: 'active' | 'pending') => void;
  onCancel: () => void;
}

interface BatchMapping {
  core_product_id: string;
  external_product_id: string;
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
  const [mappings, setMappings] = useState<BatchMapping[]>([]);
  const [loading, setLoading] = useState(false);

  // 生成所有可能的映射组合
  React.useEffect(() => {
    if (coreProducts.length > 0 && externalProducts.length > 0) {
      const newMappings: BatchMapping[] = [];
      coreProducts.forEach(coreProduct => {
        externalProducts.forEach(externalProduct => {
          newMappings.push({
            core_product_id: coreProduct.id_hashid,
            external_product_id: externalProduct.id_hashid,
          });
        });
      });
      setMappings(newMappings);
    }
  }, [coreProducts, externalProducts]);

  const handleConfirm = async () => {
    setLoading(true);
    try {
      await onConfirm(mappings, mappingStatus);
      onClose();
    } catch (error) {
      console.error('Failed to create batch mappings:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = () => {
    onCancel();
    onClose();
  };

  const getProductTitle = (productId: string, products: SelectedProduct[]) => {
    const product = products.find(p => p.id_hashid === productId);
    return product ? product.title : 'Unknown';
  };

  const getProductVendor = (productId: string, products: SelectedProduct[]) => {
    const product = products.find(p => p.id_hashid === productId);
    return product ? product.vendor : 'Unknown';
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="lg" fullWidth>
      <DialogTitle>
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Typography variant="h6">
            批量创建映射关系
          </Typography>
          <IconButton onClick={onClose}>
            <CloseIcon />
          </IconButton>
        </Box>
      </DialogTitle>

      <DialogContent>
        <Alert severity="info" sx={{ mb: 3 }}>
          <Typography variant="body2">
            您即将创建 {coreProducts.length} 个核心商品与 {externalProducts.length} 个 {platform} 商品的映射关系，
            总共将创建 {mappings.length} 个映射。
          </Typography>
        </Alert>

        {/* 映射状态选择 */}
        <Box mb={3}>
          <FormControl fullWidth>
            <InputLabel>映射状态</InputLabel>
            <Select
              value={mappingStatus}
              onChange={(e) => setMappingStatus(e.target.value as 'active' | 'pending')}
              label="映射状态"
            >
              <MenuItem value="active">活跃 - 立即生效</MenuItem>
              <MenuItem value="pending">待处理 - 需要审核</MenuItem>
            </Select>
          </FormControl>
        </Box>

        {/* 选择的商品预览 */}
        <Grid container spacing={2} mb={3}>
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  核心商品 ({coreProducts.length})
                </Typography>
                <Box display="flex" flexWrap="wrap" gap={1}>
                  {coreProducts.map((product) => (
                    <Chip
                      key={product.id_hashid}
                      label={product.title}
                      size="small"
                      color="primary"
                    />
                  ))}
                </Box>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  {platform} 商品 ({externalProducts.length})
                </Typography>
                <Box display="flex" flexWrap="wrap" gap={1}>
                  {externalProducts.map((product) => (
                    <Chip
                      key={product.id_hashid}
                      label={product.title}
                      size="small"
                      color="secondary"
                    />
                  ))}
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        {/* 映射关系预览 */}
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              映射关系预览 ({mappings.length} 个)
            </Typography>
            
            <TableContainer component={Paper} variant="outlined" sx={{ maxHeight: 400 }}>
              <Table stickyHeader size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>核心商品</TableCell>
                    <TableCell>外部商品</TableCell>
                    <TableCell>状态</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {mappings.slice(0, 10).map((mapping, index) => (
                    <TableRow key={index}>
                      <TableCell>
                        <Box>
                          <Typography variant="body2" fontWeight="medium">
                            {getProductTitle(mapping.core_product_id, coreProducts)}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {getProductVendor(mapping.core_product_id, coreProducts)}
                          </Typography>
                        </Box>
                      </TableCell>
                      <TableCell>
                        <Box>
                          <Typography variant="body2" fontWeight="medium">
                            {getProductTitle(mapping.external_product_id, externalProducts)}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {getProductVendor(mapping.external_product_id, externalProducts)}
                          </Typography>
                        </Box>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={mappingStatus === 'active' ? '活跃' : '待处理'}
                          color={mappingStatus === 'active' ? 'success' : 'warning'}
                          size="small"
                        />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
            
            {mappings.length > 10 && (
              <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                还有 {mappings.length - 10} 个映射关系...
              </Typography>
            )}
          </CardContent>
        </Card>

        {loading && (
          <Box sx={{ mt: 2 }}>
            <LinearProgress />
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              正在创建映射关系...
            </Typography>
          </Box>
        )}
      </DialogContent>

      <DialogActions>
        <Button onClick={handleCancel} disabled={loading}>
          取消
        </Button>
        <Button 
          onClick={handleConfirm} 
          variant="contained" 
          startIcon={<LinkIcon />}
          disabled={loading}
        >
          {loading ? '创建中...' : `确认创建 ${mappings.length} 个映射`}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
