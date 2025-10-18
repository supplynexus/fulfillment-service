'use client';

import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Grid,
  Button,
  Alert,
  CircularProgress,
  Stepper,
  Step,
  StepLabel,
  StepContent,
} from '@mui/material';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import {
  Add as AddIcon,
  Preview as PreviewIcon,
  Save as SaveIcon,
  ArrowBack as ArrowBackIcon,
} from '@mui/icons-material';

import ProductSelector from '@/components/skus/batch-create/ProductSelector';
import DimensionSelector from '@/components/skus/batch-create/DimensionSelector';
import SkuPreview from '@/components/skus/batch-create/SkuPreview';
import SkuGenerator from '@/components/skus/batch-create/SkuGenerator';

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

interface GeneratedSku {
  id: string;
  sku: string;
  name: string;
  dimensions: Record<string, string>;
  isSelected: boolean;
}

const steps = ['选择产品', '选择维度', '预览 SKU', '生成 SKU'];

export default function SkuBatchCreatePage() {
  const [activeStep, setActiveStep] = useState(0);
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
  const [selectedDimensions, setSelectedDimensions] = useState<
    SelectedDimension[]
  >([]);
  const [generatedSkus, setGeneratedSkus] = useState<GeneratedSku[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // 模拟数据
  const mockProducts: Product[] = [
    {
      id: '1',
      name: '基础 T 恤',
      code: 'basic-tshirt',
      description: '经典基础款 T 恤',
      categoryId: '1',
      categoryName: '服装',
      isActive: true,
    },
    {
      id: '2',
      name: '运动裤',
      code: 'sports-pants',
      description: '舒适运动裤',
      categoryId: '2',
      categoryName: '运动装',
      isActive: true,
    },
  ];

  const mockDimensionTemplates: DimensionTemplate[] = [
    {
      id: '1',
      dimensionCode: 'color',
      dimensionName: '颜色',
      dimensionType: 'select',
      description: '产品颜色',
      isActive: true,
      dimensionValues: [
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
    },
    {
      id: '2',
      dimensionCode: 'size',
      dimensionName: '尺码',
      dimensionType: 'select',
      description: '产品尺码',
      isActive: true,
      dimensionValues: [
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
    },
  ];

  const handleNext = () => {
    setActiveStep(prevActiveStep => prevActiveStep + 1);
  };

  const handleBack = () => {
    setActiveStep(prevActiveStep => prevActiveStep - 1);
  };

  const handleReset = () => {
    setActiveStep(0);
    setSelectedProduct(null);
    setSelectedDimensions([]);
    setGeneratedSkus([]);
    setError(null);
    setSuccess(null);
  };

  const handleProductSelect = (product: Product) => {
    setSelectedProduct(product);
    setError(null);
  };

  const handleDimensionSelect = (dimensions: SelectedDimension[]) => {
    setSelectedDimensions(dimensions);
    setError(null);
  };

  const handleGenerateSkus = (skus: GeneratedSku[]) => {
    setGeneratedSkus(skus);
    setError(null);
  };

  const handleCreateSkus = async () => {
    if (generatedSkus.length === 0) {
      setError('没有可创建的 SKU');
      return;
    }

    const selectedSkus = generatedSkus.filter(sku => sku.isSelected);
    if (selectedSkus.length === 0) {
      setError('请至少选择一个 SKU 进行创建');
      return;
    }

    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      console.log('创建 SKU:', selectedSkus);

      // 批量创建SKU
      const createPromises = selectedSkus.map(sku => 
        fetch('/api/product-variants', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('token')}`,
          },
          body: JSON.stringify(sku),
        })
      );

      const responses = await Promise.all(createPromises);
      
      // 检查所有响应
      const failedResponses = responses.filter(response => !response.ok);
      if (failedResponses.length > 0) {
        throw new Error(`有 ${failedResponses.length} 个 SKU 创建失败`);
      }

      setSuccess(`成功创建 ${selectedSkus.length} 个 SKU`);
      setActiveStep(0);
      handleReset();
    } catch (err) {
      setError(err instanceof Error ? err.message : '创建失败');
    } finally {
      setLoading(false);
    }
  };

  const canProceedToNext = () => {
    switch (activeStep) {
      case 0:
        return selectedProduct !== null;
      case 1:
        return selectedDimensions.length > 0;
      case 2:
        return generatedSkus.length > 0;
      case 3:
        return generatedSkus.some(sku => sku.isSelected);
      default:
        return false;
    }
  };

  const getStepContent = (step: number) => {
    switch (step) {
      case 0:
        return (
          <ProductSelector
            products={mockProducts}
            selectedProduct={selectedProduct}
            onProductSelect={handleProductSelect}
            loading={loading}
          />
        );
      case 1:
        return (
          <DimensionSelector
            product={selectedProduct}
            dimensionTemplates={mockDimensionTemplates}
            selectedDimensions={selectedDimensions}
            onDimensionSelect={handleDimensionSelect}
            loading={loading}
          />
        );
      case 2:
        return (
          <SkuPreview
            product={selectedProduct}
            selectedDimensions={selectedDimensions}
            onGenerate={handleGenerateSkus}
            loading={loading}
          />
        );
      case 3:
        return (
          <SkuGenerator
            product={selectedProduct}
            generatedSkus={generatedSkus}
            onSkuToggle={(skuId, isSelected) => {
              setGeneratedSkus(prev =>
                prev.map(sku =>
                  sku.id === skuId ? { ...sku, isSelected } : sku
                )
              );
            }}
            onSelectAll={isSelected => {
              setGeneratedSkus(prev =>
                prev.map(sku => ({ ...sku, isSelected }))
              );
            }}
            onCreateSkus={handleCreateSkus}
            loading={loading}
          />
        );
      default:
        return null;
    }
  };

  return (
    <ProtectedRoute>
      <DashboardLayout>
        <Box sx={{ p: 3 }}>
          {/* 页面标题 */}
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
            <Button
              startIcon={<ArrowBackIcon />}
              onClick={() => window.history.back()}
              sx={{ mr: 2 }}
            >
              返回
            </Button>
            <Typography variant='h4' component='h1'>
              SKU 批量创建
            </Typography>
          </Box>

          {/* 错误和成功提示 */}
          {error && (
            <Alert
              severity='error'
              sx={{ mb: 2 }}
              onClose={() => setError(null)}
            >
              {error}
            </Alert>
          )}

          {success && (
            <Alert
              severity='success'
              sx={{ mb: 2 }}
              onClose={() => setSuccess(null)}
            >
              {success}
            </Alert>
          )}

          {/* 步骤指示器 */}
          <Paper sx={{ p: 3, mb: 3 }}>
            <Stepper activeStep={activeStep} orientation='horizontal'>
              {steps.map((label, index) => (
                <Step key={label}>
                  <StepLabel>{label}</StepLabel>
                </Step>
              ))}
            </Stepper>
          </Paper>

          {/* 步骤内容 */}
          <Paper sx={{ p: 3 }}>{getStepContent(activeStep)}</Paper>

          {/* 步骤导航 */}
          <Box sx={{ mt: 3, display: 'flex', justifyContent: 'space-between' }}>
            <Button disabled={activeStep === 0} onClick={handleBack}>
              上一步
            </Button>

            <Box sx={{ display: 'flex', gap: 2 }}>
              {activeStep < steps.length - 1 ? (
                <Button
                  variant='contained'
                  onClick={handleNext}
                  disabled={!canProceedToNext() || loading}
                  startIcon={
                    loading ? <CircularProgress size={20} /> : undefined
                  }
                >
                  {loading ? '处理中...' : '下一步'}
                </Button>
              ) : (
                <Button
                  variant='contained'
                  onClick={handleCreateSkus}
                  disabled={!canProceedToNext() || loading}
                  startIcon={
                    loading ? <CircularProgress size={20} /> : <SaveIcon />
                  }
                >
                  {loading ? '创建中...' : '创建 SKU'}
                </Button>
              )}

              <Button
                variant='outlined'
                onClick={handleReset}
                disabled={loading}
              >
                重新开始
              </Button>
            </Box>
          </Box>

          {/* 加载遮罩 */}
          {loading && (
            <Box
              sx={{
                position: 'fixed',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                backgroundColor: 'rgba(0, 0, 0, 0.5)',
                zIndex: 9999,
              }}
            >
              <CircularProgress />
            </Box>
          )}
        </Box>
      </DashboardLayout>
    </ProtectedRoute>
  );
}
