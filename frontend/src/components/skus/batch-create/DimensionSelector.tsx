'use client';

import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Grid,
  Card,
  CardContent,
  CardActions,
  Button,
  Chip,
  Checkbox,
  FormControl,
  FormLabel,
  FormGroup,
  FormControlLabel,
  Alert,
  CircularProgress,
  Divider,
  Tooltip,
  IconButton,
} from '@mui/material';
import {
  Info as InfoIcon,
  CheckCircle as CheckCircleIcon,
  Warning as WarningIcon,
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

interface DimensionTemplate {
  id: string;
  dimensionCode: string;
  dimensionName: string;
  dimensionType: 'select' | 'text' | 'number' | 'boolean';
  description?: string;
  isActive: boolean;
  dimensionValues: DimensionValue[];
}

interface DimensionValue {
  id: string;
  valueCode: string;
  valueName: string;
  valueType: 'normal' | 'default' | 'not_applicable';
  isDefault: boolean;
  isActive: boolean;
}

interface SelectedDimension {
  templateId: string;
  dimensionCode: string;
  dimensionName: string;
  selectedValues: string[];
}

interface DimensionSelectorProps {
  product: Product | null;
  dimensionTemplates: DimensionTemplate[];
  selectedDimensions: SelectedDimension[];
  onDimensionSelect: (dimensions: SelectedDimension[]) => void;
  loading: boolean;
}

export default function DimensionSelector({
  product,
  dimensionTemplates,
  selectedDimensions,
  onDimensionSelect,
  loading,
}: DimensionSelectorProps) {
  const [localSelectedDimensions, setLocalSelectedDimensions] = useState<
    SelectedDimension[]
  >([]);

  useEffect(() => {
    setLocalSelectedDimensions(selectedDimensions);
  }, [selectedDimensions]);

  const handleDimensionToggle = (
    template: DimensionTemplate,
    isSelected: boolean
  ) => {
    if (isSelected) {
      // 添加维度
      const newDimension: SelectedDimension = {
        templateId: template.id,
        dimensionCode: template.dimensionCode,
        dimensionName: template.dimensionName,
        selectedValues: template.dimensionValues
          .filter(v => v.isActive)
          .map(v => v.id),
      };
      setLocalSelectedDimensions(prev => [...prev, newDimension]);
    } else {
      // 移除维度
      setLocalSelectedDimensions(prev =>
        prev.filter(d => d.templateId !== template.id)
      );
    }
  };

  const handleValueToggle = (
    templateId: string,
    valueId: string,
    isSelected: boolean
  ) => {
    setLocalSelectedDimensions(prev =>
      prev.map(dimension => {
        if (dimension.templateId === templateId) {
          if (isSelected) {
            return {
              ...dimension,
              selectedValues: [...dimension.selectedValues, valueId],
            };
          } else {
            return {
              ...dimension,
              selectedValues: dimension.selectedValues.filter(
                id => id !== valueId
              ),
            };
          }
        }
        return dimension;
      })
    );
  };

  const handleSelectAllValues = (templateId: string, isSelected: boolean) => {
    const template = dimensionTemplates.find(t => t.id === templateId);
    if (!template) return;

    setLocalSelectedDimensions(prev =>
      prev.map(dimension => {
        if (dimension.templateId === templateId) {
          return {
            ...dimension,
            selectedValues: isSelected
              ? template.dimensionValues.filter(v => v.isActive).map(v => v.id)
              : [],
          };
        }
        return dimension;
      })
    );
  };

  const handleApply = () => {
    onDimensionSelect(localSelectedDimensions);
  };

  const getSelectedDimension = (templateId: string) => {
    return localSelectedDimensions.find(d => d.templateId === templateId);
  };

  const isDimensionSelected = (templateId: string) => {
    return localSelectedDimensions.some(d => d.templateId === templateId);
  };

  const getDimensionTypeLabel = (type: string) => {
    const typeMap: Record<string, string> = {
      select: '选择',
      text: '文本',
      number: '数字',
      boolean: '布尔',
    };
    return typeMap[type] || type;
  };

  const getDimensionTypeColor = (type: string) => {
    const colorMap: Record<
      string,
      'default' | 'primary' | 'secondary' | 'success' | 'warning' | 'error'
    > = {
      select: 'primary',
      text: 'secondary',
      number: 'success',
      boolean: 'warning',
    };
    return colorMap[type] || 'default';
  };

  const getValueTypeLabel = (type: string) => {
    const typeMap: Record<string, string> = {
      normal: '普通',
      default: '默认',
      not_applicable: '不适用',
    };
    return typeMap[type] || type;
  };

  const getValueTypeColor = (type: string) => {
    const colorMap: Record<
      string,
      'default' | 'primary' | 'secondary' | 'success' | 'warning' | 'error'
    > = {
      normal: 'default',
      default: 'success',
      not_applicable: 'warning',
    };
    return colorMap[type] || 'default';
  };

  const calculateSkuCount = () => {
    if (localSelectedDimensions.length === 0) return 0;

    return localSelectedDimensions.reduce((total, dimension) => {
      return total * Math.max(dimension.selectedValues.length, 1);
    }, 1);
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

  if (!product) {
    return <Alert severity='warning'>请先选择一个产品</Alert>;
  }

  return (
    <Box>
      {/* 标题 */}
      <Typography variant='h6' sx={{ mb: 2 }}>
        为产品 "{product.name}" 选择维度
      </Typography>

      {/* 产品信息 */}
      <Paper sx={{ p: 2, mb: 3, bgcolor: 'grey.50' }}>
        <Typography variant='body2' color='text.secondary'>
          产品编码: {product.code} | 分类: {product.categoryName}
        </Typography>
      </Paper>

      {/* 维度模板列表 */}
      <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }} spacing={2}>
        {dimensionTemplates.map(template => {
          const isSelected = isDimensionSelected(template.id);
          const selectedDimension = getSelectedDimension(template.id);
          const activeValues = template.dimensionValues.filter(v => v.isActive);

          return (
            <Box sx={{ width: { xs: "100%", md: "50%" } }} key={template.id}>
              <Card sx={{ height: '100%' }}>
                <CardContent>
                  <Box
                    sx={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      mb: 2,
                    }}
                  >
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Typography variant='h6'>
                        {template.dimensionName}
                      </Typography>
                      <Chip
                        label={getDimensionTypeLabel(template.dimensionType)}
                        color={getDimensionTypeColor(template.dimensionType)}
                        size='small'
                      />
                      {isSelected && <CheckCircleIcon color='success' />}
                    </Box>

                    <Tooltip title={template.description || '无描述'}>
                      <IconButton size='small'>
                        <InfoIcon />
                      </IconButton>
                    </Tooltip>
                  </Box>

                  <Typography
                    variant='body2'
                    color='text.secondary'
                    sx={{ mb: 2 }}
                  >
                    编码: {template.dimensionCode}
                  </Typography>

                  {/* 维度选择开关 */}
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={isSelected}
                        onChange={e =>
                          handleDimensionToggle(template, e.target.checked)
                        }
                      />
                    }
                    label={`使用 ${template.dimensionName} 维度`}
                  />

                  {/* 维度值选择 */}
                  {isSelected && (
                    <Box sx={{ mt: 2 }}>
                      <Divider sx={{ mb: 2 }} />

                      <Box
                        sx={{
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          mb: 1,
                        }}
                      >
                        <Typography variant='subtitle2'>选择维度值:</Typography>
                        <Button
                          size='small'
                          onClick={() =>
                            handleSelectAllValues(template.id, true)
                          }
                        >
                          全选
                        </Button>
                      </Box>

                      <FormGroup>
                        {activeValues.map(value => (
                          <FormControlLabel
                            key={value.id}
                            control={
                              <Checkbox
                                checked={
                                  selectedDimension?.selectedValues.includes(
                                    value.id
                                  ) || false
                                }
                                onChange={e =>
                                  handleValueToggle(
                                    template.id,
                                    value.id,
                                    e.target.checked
                                  )
                                }
                              />
                            }
                            label={
                              <Box
                                sx={{
                                  display: 'flex',
                                  alignItems: 'center',
                                  gap: 1,
                                }}
                              >
                                <Typography variant='body2'>
                                  {value.valueName}
                                </Typography>
                                <Typography
                                  variant='caption'
                                  color='text.secondary'
                                >
                                  ({value.valueCode})
                                </Typography>
                                {value.isDefault && (
                                  <Chip
                                    label='默认'
                                    size='small'
                                    color='success'
                                    variant='outlined'
                                  />
                                )}
                                <Chip
                                  label={getValueTypeLabel(value.valueType)}
                                  size='small'
                                  color={getValueTypeColor(value.valueType)}
                                  variant='outlined'
                                />
                              </Box>
                            }
                          />
                        ))}
                      </FormGroup>

                      {selectedDimension &&
                        selectedDimension.selectedValues.length === 0 && (
                          <Alert severity='warning' sx={{ mt: 1 }}>
                            请至少选择一个维度值
                          </Alert>
                        )}
                    </Box>
                  )}
                </CardContent>
              </Card>
            </Box>
          );
        })}
      </Box>

      {/* SKU 数量预览 */}
      {localSelectedDimensions.length > 0 && (
        <Paper
          sx={{
            p: 2,
            mt: 3,
            bgcolor: 'primary.light',
            color: 'primary.contrastText',
          }}
        >
          <Typography
            variant='h6'
            sx={{ display: 'flex', alignItems: 'center', gap: 1 }}
          >
            <InfoIcon />
            预计生成 SKU 数量: {calculateSkuCount()}
          </Typography>
          <Typography variant='body2' sx={{ mt: 1 }}>
            选择的维度:{' '}
            {localSelectedDimensions.map(d => d.dimensionName).join(' × ')}
          </Typography>
        </Paper>
      )}

      {/* 选择提示 */}
      {localSelectedDimensions.length === 0 && (
        <Alert severity='info' sx={{ mt: 2 }}>
          请至少选择一个维度来生成 SKU
        </Alert>
      )}

      {/* 应用按钮 */}
      <Box sx={{ mt: 3, display: 'flex', justifyContent: 'flex-end' }}>
        <Button
          variant='contained'
          onClick={handleApply}
          disabled={localSelectedDimensions.length === 0}
        >
          应用选择
        </Button>
      </Box>
    </Box>
  );
}
