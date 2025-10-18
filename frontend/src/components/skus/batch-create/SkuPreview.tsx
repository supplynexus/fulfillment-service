'use client';

import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Button,
  Alert,
  CircularProgress,
  Chip,
  Divider,
  Grid,
  Card,
  CardContent,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from '@mui/material';
import {
  Preview as PreviewIcon,
  Refresh as RefreshIcon,
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

interface SelectedDimension {
  templateId: string;
  dimensionCode: string;
  dimensionName: string;
  selectedValues: string[];
}

interface DimensionValue {
  id: string;
  valueCode: string;
  valueName: string;
  valueType: 'normal' | 'default' | 'not_applicable';
  isDefault: boolean;
  isActive: boolean;
}

interface PreviewSku {
  id: string;
  sku: string;
  name: string;
  dimensions: Record<string, string>;
  dimensionValues: Record<string, DimensionValue>;
}

interface SkuPreviewProps {
  product: Product | null;
  selectedDimensions: SelectedDimension[];
  onGenerate: (skus: any[]) => void;
  loading: boolean;
}

export default function SkuPreview({
  product,
  selectedDimensions,
  onGenerate,
  loading,
}: SkuPreviewProps) {
  const [previewSkus, setPreviewSkus] = useState<PreviewSku[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);

  // 模拟维度值数据
  const mockDimensionValues: Record<string, DimensionValue[]> = {
    '1': [
      // color
      {
        id: '1',
        valueCode: 'red',
        valueName: '红色',
        valueType: 'normal',
        isDefault: false,
        isActive: true,
      },
      {
        id: '2',
        valueCode: 'blue',
        valueName: '蓝色',
        valueType: 'normal',
        isDefault: false,
        isActive: true,
      },
      {
        id: '3',
        valueCode: 'green',
        valueName: '绿色',
        valueType: 'normal',
        isDefault: false,
        isActive: true,
      },
    ],
    '2': [
      // size
      {
        id: '4',
        valueCode: 'S',
        valueName: '小号',
        valueType: 'normal',
        isDefault: false,
        isActive: true,
      },
      {
        id: '5',
        valueCode: 'M',
        valueName: '中号',
        valueType: 'normal',
        isDefault: false,
        isActive: true,
      },
      {
        id: '6',
        valueCode: 'L',
        valueName: '大号',
        valueType: 'normal',
        isDefault: false,
        isActive: true,
      },
    ],
  };

  const generateCartesianProduct = () => {
    if (!product || selectedDimensions.length === 0) {
      return [];
    }

    // 获取所有维度的值组合
    const dimensionCombinations: string[][] = [];

    selectedDimensions.forEach(dimension => {
      const values = dimension.selectedValues
        .map(valueId => {
          const templateValues =
            mockDimensionValues[dimension.templateId] || [];
          return templateValues.find(v => v.id === valueId);
        })
        .filter(Boolean) as DimensionValue[];

      dimensionCombinations.push(values.map(v => v.id));
    });

    // 生成笛卡尔积
    const combinations: string[][] = [];

    const generateCombinations = (current: string[], remaining: string[][]) => {
      if (remaining.length === 0) {
        combinations.push([...current]);
        return;
      }

      const [first, ...rest] = remaining;
      first.forEach(value => {
        generateCombinations([...current, value], rest);
      });
    };

    generateCombinations([], dimensionCombinations);

    // 生成 SKU 预览
    const skus: PreviewSku[] = combinations.map((combination, index) => {
      const dimensions: Record<string, string> = {};
      const dimensionValues: Record<string, DimensionValue> = {};

      selectedDimensions.forEach((dimension, dimIndex) => {
        const valueId = combination[dimIndex];
        const templateValues = mockDimensionValues[dimension.templateId] || [];
        const value = templateValues.find(v => v.id === valueId);

        if (value) {
          dimensions[dimension.dimensionCode] = value.valueCode;
          dimensionValues[dimension.dimensionCode] = value;
        }
      });

      // 生成 SKU 编码
      const dimensionCodes = Object.values(dimensions).join('-');
      const sku = `${product.code}-${dimensionCodes}`;

      // 生成 SKU 名称
      const dimensionNames = Object.values(dimensionValues)
        .map(v => v.valueName)
        .join(' ');
      const name = `${product.name} ${dimensionNames}`;

      return {
        id: `preview_${index}`,
        sku,
        name,
        dimensions,
        dimensionValues,
      };
    });

    return skus;
  };

  const handleGeneratePreview = async () => {
    setIsGenerating(true);

    try {
      // 模拟生成过程
      await new Promise(resolve => setTimeout(resolve, 1000));

      const skus = generateCartesianProduct();
      setPreviewSkus(skus);

      // 转换为最终格式
      const finalSkus = skus.map(sku => ({
        id: sku.id,
        sku: sku.sku,
        name: sku.name,
        dimensions: sku.dimensions,
        isSelected: true,
      }));

      onGenerate(finalSkus);
    } catch (error) {
      console.error('生成预览失败:', error);
    } finally {
      setIsGenerating(false);
    }
  };

  useEffect(() => {
    if (selectedDimensions.length > 0) {
      const skus = generateCartesianProduct();
      setPreviewSkus(skus);
    } else {
      setPreviewSkus([]);
    }
  }, [product, selectedDimensions]);

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

  if (!product) {
    return <Alert severity='warning'>请先选择一个产品</Alert>;
  }

  if (selectedDimensions.length === 0) {
    return <Alert severity='info'>请先选择维度</Alert>;
  }

  return (
    <Box>
      {/* 标题 */}
      <Typography variant='h6' sx={{ mb: 2 }}>
        SKU 预览
      </Typography>

      {/* 产品信息 */}
      <Paper sx={{ p: 2, mb: 3, bgcolor: 'grey.50' }}>
        <Typography variant='body2' color='text.secondary'>
          产品: {product.name} ({product.code})
        </Typography>
        <Typography variant='body2' color='text.secondary'>
          选择的维度: {selectedDimensions.map(d => d.dimensionName).join(' × ')}
        </Typography>
        <Typography variant='body2' color='text.secondary'>
          预计生成 SKU 数量: {previewSkus.length}
        </Typography>
      </Paper>

      {/* 生成按钮 */}
      <Box sx={{ mb: 3, display: 'flex', gap: 2 }}>
        <Button
          variant='contained'
          startIcon={<PreviewIcon />}
          onClick={handleGeneratePreview}
          disabled={isGenerating || previewSkus.length === 0}
        >
          {isGenerating ? '生成中...' : '生成预览'}
        </Button>

        <Button
          variant='outlined'
          startIcon={<RefreshIcon />}
          onClick={() => setPreviewSkus(generateCartesianProduct())}
          disabled={isGenerating}
        >
          刷新预览
        </Button>
      </Box>

      {/* SKU 预览表格 */}
      {previewSkus.length > 0 && (
        <Paper sx={{ mb: 3 }}>
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>SKU 编码</TableCell>
                  <TableCell>SKU 名称</TableCell>
                  {selectedDimensions.map(dimension => (
                    <TableCell key={dimension.templateId}>
                      {dimension.dimensionName}
                    </TableCell>
                  ))}
                </TableRow>
              </TableHead>
              <TableBody>
                {previewSkus.slice(0, 10).map(sku => (
                  <TableRow key={sku.id}>
                    <TableCell>
                      <Typography variant='body2' fontWeight='medium'>
                        {sku.sku}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant='body2'>{sku.name}</Typography>
                    </TableCell>
                    {selectedDimensions.map(dimension => (
                      <TableCell key={dimension.templateId}>
                        <Chip
                          label={
                            sku.dimensionValues[dimension.dimensionCode]
                              ?.valueName || '-'
                          }
                          size='small'
                          color='primary'
                          variant='outlined'
                        />
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>

          {previewSkus.length > 10 && (
            <Box sx={{ p: 2, textAlign: 'center' }}>
              <Typography variant='body2' color='text.secondary'>
                显示前 10 个 SKU，共 {previewSkus.length} 个
              </Typography>
            </Box>
          )}
        </Paper>
      )}

      {/* 维度组合统计 */}
      {selectedDimensions.length > 0 && (
        <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }} spacing={2}>
          {selectedDimensions.map(dimension => {
            const values = dimension.selectedValues
              .map(valueId => {
                const templateValues =
                  mockDimensionValues[dimension.templateId] || [];
                return templateValues.find(v => v.id === valueId);
              })
              .filter(Boolean) as DimensionValue[];

            return (
              <Grid size={{ xs: 12, sm: 6, md: 4 }} key={dimension.templateId}>
                <Card>
                  <CardContent>
                    <Typography variant='subtitle1' sx={{ mb: 1 }}>
                      {dimension.dimensionName}
                    </Typography>
                    <Typography
                      variant='body2'
                      color='text.secondary'
                      sx={{ mb: 1 }}
                    >
                      选择了 {values.length} 个值
                    </Typography>
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                      {values.map(value => (
                        <Chip
                          key={value.id}
                          label={value.valueName}
                          size='small'
                          color='primary'
                          variant='outlined'
                        />
                      ))}
                    </Box>
                  </CardContent>
                </Card>
              </Box>
            );
          })}
        </Box>
      )}

      {/* 空状态 */}
      {previewSkus.length === 0 && selectedDimensions.length > 0 && (
        <Alert severity='info'>点击"生成预览"按钮查看 SKU 预览</Alert>
      )}
    </Box>
  );
}
