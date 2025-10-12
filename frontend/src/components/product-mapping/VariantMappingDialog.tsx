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
  CircularProgress,
  Chip,
  Grid,
  Card,
  CardContent,
  Divider,
} from '@mui/material';
import { frontendApi } from '@/lib/api';
import { frontendLogger } from '@/lib/frontend-logger';

interface Variant {
  id: string;
  id_hashid: string;
  sku: string;
  title: string;
  price: number;
  inventory_quantity: number;
  option1?: string;
  option2?: string;
  option3?: string;
}

interface VariantMappingDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: (mappings: VariantMapping[]) => void;
  coreProduct: {
    id_hashid: string;
    title: string;
    variants: Variant[];
  };
  printifyProduct: {
    printify_product_id: string;
    title: string;
    variants: Variant[];
  };
  printifySystemId: string;
}

interface VariantMapping {
  core_variant_id: string;
  external_variant_id: string;
  core_variant_sku: string;
  external_variant_sku: string;
  core_variant_title: string;
  external_variant_title: string;
}

export function VariantMappingDialog({
  open,
  onClose,
  onConfirm,
  coreProduct,
  printifyProduct,
  printifySystemId,
}: VariantMappingDialogProps) {
  const [mappings, setMappings] = useState<VariantMapping[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 初始化映射
  useEffect(() => {
    if (open && coreProduct.variants && printifyProduct.variants) {
      console.log('核心商品变体:', coreProduct.variants);
      console.log('Printify 变体:', printifyProduct.variants);
      
      // 调试：检查变体数据结构
      if (coreProduct.variants.length > 0) {
        console.log('第一个核心商品变体的结构:', coreProduct.variants[0]);
        console.log('第一个核心商品变体的 id_hashid:', coreProduct.variants[0].id_hashid);
      }
      
      const initialMappings: VariantMapping[] = coreProduct.variants.map((coreVariant, index) => {
        // 使用 index 作为 ID，因为 coreVariant.id 可能是 undefined
        const variantId = coreVariant.id || `variant-${index}`;
        return {
          core_variant_id: variantId,
          external_variant_id: '', // 用户需要手动选择
          core_variant_sku: coreVariant.sku,
          external_variant_sku: '',
          core_variant_title: coreVariant.title,
          external_variant_title: '',
        };
      });
      console.log('初始映射:', initialMappings);
      setMappings(initialMappings);
    }
  }, [open, coreProduct, printifyProduct]);

  const handleVariantMappingChange = (coreVariantId: string, externalVariantId: string) => {
    console.log('变体映射变化:', { coreVariantId, externalVariantId });
    
    const externalVariant = printifyProduct.variants.find(v => v.id === externalVariantId);
    
    setMappings(prev => {
      const newMappings = prev.map(mapping => 
        mapping.core_variant_id === coreVariantId
          ? {
              ...mapping,
              external_variant_id: externalVariantId,
              external_variant_sku: externalVariant?.sku || '',
              external_variant_title: externalVariant?.title || '',
            }
          : mapping
      );
      console.log('新的映射状态:', newMappings);
      return newMappings;
    });
  };

  const handleConfirm = async () => {
    try {
      setLoading(true);
      setError(null);

      // 检查是否所有变体都已映射
      const unmappedVariants = mappings.filter(m => !m.external_variant_id);
      if (unmappedVariants.length > 0) {
        setError(`还有 ${unmappedVariants.length} 个变体未映射`);
        return;
      }

      // 检查是否有重复映射
      const mappedExternalIds = mappings.map(m => m.external_variant_id);
      const uniqueExternalIds = new Set(mappedExternalIds);
      if (mappedExternalIds.length !== uniqueExternalIds.size) {
        setError('存在重复的 Printify 变体映射');
        return;
      }

      frontendLogger.info('🔗 开始创建变体映射', {
        coreProduct: coreProduct.title,
        printifyProduct: printifyProduct.title,
        mappingCount: mappings.length,
      });

      // 创建变体映射
      const createPromises = mappings.map(async (mapping, index) => {
        // 找到对应的核心商品变体，获取其真正的 hashid
        const coreVariant = coreProduct.variants[index];
        
        console.log('创建映射数据:', {
          coreVariant,
          coreVariantHashid: coreVariant.id_hashid,
          coreVariantId: coreVariant.id,
          mapping,
          mappingData: {
            core_product_id_hashid: coreProduct.id_hashid,
            core_variant_id_hashid: coreVariant.id_hashid || coreVariant.id,
            external_system_id_hashid: printifySystemId,
            external_product_id: printifyProduct.printify_product_id,
            external_variant_id: mapping.external_variant_id?.toString(),
            mapping_type: 'manual',
            sync_direction: 'bidirectional',
            sync_status: 'active',
          }
        });
        
        const mappingData = {
          core_product_id_hashid: coreProduct.id_hashid,
          core_variant_id_hashid: coreVariant.id_hashid || coreVariant.id,
          external_system_id_hashid: printifySystemId,
          external_product_id: printifyProduct.printify_product_id,
          external_variant_id: mapping.external_variant_id?.toString(),
          mapping_type: 'manual',
          sync_direction: 'bidirectional',
          sync_status: 'active',
        };

        return frontendApi.post('/api/products/mappings/', mappingData);
      });

      await Promise.all(createPromises);

      frontendLogger.info('✅ 变体映射创建成功', {
        coreProduct: coreProduct.title,
        printifyProduct: printifyProduct.title,
        mappingCount: mappings.length,
      });

      onConfirm(mappings);
    } catch (error) {
      frontendLogger.error('❌ 变体映射创建失败', {
        error: String(error),
        coreProduct: coreProduct.title,
        printifyProduct: printifyProduct.title,
      });
      setError('变体映射创建失败');
    } finally {
      setLoading(false);
    }
  };

  const getAvailablePrintifyVariants = (coreVariantId: string, currentMappings: VariantMapping[]) => {
    const currentMapping = currentMappings.find(m => m.core_variant_id === coreVariantId);
    const usedExternalIds = currentMappings
      .filter(m => m.core_variant_id !== coreVariantId && m.external_variant_id)
      .map(m => m.external_variant_id);
    
    const availableVariants = printifyProduct.variants.filter(v => 
      !usedExternalIds.includes(v.id) || v.id === currentMapping?.external_variant_id
    );
    
    console.log(`变体 ${coreVariantId} 的可用选项:`, {
      coreVariantId,
      currentMapping,
      usedExternalIds,
      availableVariants: availableVariants.map(v => ({ id: v.id, title: v.title }))
    });
    
    return availableVariants;
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="lg" fullWidth>
      <DialogTitle>
        变体映射 - {coreProduct.title} → {printifyProduct.title}
      </DialogTitle>
      
      <DialogContent>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        <Grid container spacing={3}>
          {/* 核心商品变体 */}
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  核心商品变体 ({coreProduct.variants.length})
                </Typography>
                <TableContainer component={Paper} variant="outlined">
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>SKU</TableCell>
                        <TableCell>标题</TableCell>
                        <TableCell>价格</TableCell>
                        <TableCell>库存</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {coreProduct.variants.map((variant) => (
                        <TableRow key={variant.id}>
                          <TableCell>{variant.sku}</TableCell>
                          <TableCell>{variant.title}</TableCell>
                          <TableCell>${variant.price}</TableCell>
                          <TableCell>{variant.inventory_quantity}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </CardContent>
            </Card>
          </Grid>

          {/* Printify 变体 */}
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Printify 变体 ({printifyProduct.variants.length})
                </Typography>
                <TableContainer component={Paper} variant="outlined">
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>SKU</TableCell>
                        <TableCell>标题</TableCell>
                        <TableCell>价格</TableCell>
                        <TableCell>库存</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {printifyProduct.variants.map((variant) => (
                        <TableRow key={variant.id}>
                          <TableCell>{variant.sku}</TableCell>
                          <TableCell>{variant.title}</TableCell>
                          <TableCell>${variant.price}</TableCell>
                          <TableCell>{variant.inventory_quantity}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        <Divider sx={{ my: 3 }} />

        {/* 映射配置 */}
        <Box>
          <Typography variant="h6" gutterBottom>
            变体映射配置
          </Typography>
          <TableContainer component={Paper} variant="outlined">
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>核心变体</TableCell>
                  <TableCell>Printify 变体</TableCell>
                  <TableCell>状态</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {mappings.map((mapping, index) => {
                  const availableVariants = getAvailablePrintifyVariants(mapping.core_variant_id, mappings);
                  const isMapped = !!mapping.external_variant_id;
                  
                  return (
                    <TableRow key={`mapping-${index}-${mapping.core_variant_sku}`}>
                      <TableCell>
                        <Box>
                          <Typography variant="body2" fontWeight="medium">
                            {mapping.core_variant_title}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            SKU: {mapping.core_variant_sku}
                          </Typography>
                        </Box>
                      </TableCell>
                      <TableCell>
                        <FormControl fullWidth size="small">
                          <Select
                            value={mapping.external_variant_id || ''}
                            onChange={(e) => handleVariantMappingChange(mapping.core_variant_id, e.target.value)}
                            displayEmpty
                          >
                            <MenuItem value="">
                              <em>选择 Printify 变体</em>
                            </MenuItem>
                            {availableVariants.map((variant) => (
                              <MenuItem key={variant.id} value={variant.id}>
                                <Box>
                                  <Typography variant="body2">
                                    {variant.title}
                                  </Typography>
                                  <Typography variant="caption" color="text.secondary">
                                    SKU: {variant.sku}
                                  </Typography>
                                </Box>
                              </MenuItem>
                            ))}
                          </Select>
                        </FormControl>
                      </TableCell>
                      <TableCell>
                        {isMapped ? (
                          <Chip label="已映射" color="success" size="small" />
                        ) : (
                          <Chip label="未映射" color="default" size="small" />
                        )}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </TableContainer>
        </Box>
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose} disabled={loading}>
          取消
        </Button>
        <Button
          onClick={handleConfirm}
          variant="contained"
          disabled={loading || mappings.some(m => !m.external_variant_id)}
        >
          {loading ? <CircularProgress size={20} /> : '确认映射'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
