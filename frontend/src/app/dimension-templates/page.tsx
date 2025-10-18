'use client';

import React, { useState } from 'react';
import {
  Box,
  Typography,
  Paper,
  Grid,
  Button,
  Alert,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Add as AddIcon, Settings as SettingsIcon, Refresh as RefreshIcon } from '@mui/icons-material';

import DimensionTemplateList from '@/components/dimension-templates/DimensionTemplateList';
import DimensionTemplateForm from '@/components/dimension-templates/DimensionTemplateForm';
import DimensionValueManager from '@/components/dimension-templates/DimensionValueManager';

interface DimensionTemplate {
  id: string;
  dimensionCode: string;
  dimensionName: string;
  dimensionType: 'select' | 'text' | 'number' | 'boolean';
  description?: string;
  sortOrder: number;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
  dimensionValues: DimensionValue[];
}

interface DimensionValue {
  id: string;
  valueCode: string;
  valueName: string;
  valueType: 'normal' | 'default' | 'not_applicable';
  isDefault: boolean;
  reviewStatus: 'pending' | 'approved' | 'rejected';
  sortOrder: number;
  isActive: boolean;
  createdAt: string;
}

export default function DimensionTemplatesPage() {
  const [selectedTemplate, setSelectedTemplate] =
    useState<DimensionTemplate | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [showValueManager, setShowValueManager] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const handleRefresh = () => {
    setRefreshKey(prev => prev + 1);
  };

  const handleCreateTemplate = () => {
    setSelectedTemplate(null);
    setShowForm(true);
    setShowValueManager(false);
  };

  const handleEditTemplate = (template: DimensionTemplate) => {
    setSelectedTemplate(template);
    setShowForm(true);
    setShowValueManager(false);
  };

  const handleManageValues = (template: DimensionTemplate) => {
    setSelectedTemplate(template);
    setShowForm(false);
    setShowValueManager(true);
  };

  const handleFormClose = () => {
    setShowForm(false);
    setSelectedTemplate(null);
  };

  const handleValueManagerClose = () => {
    setShowValueManager(false);
    setSelectedTemplate(null);
  };

  const handleFormSubmit = async (templateData: Partial<DimensionTemplate>) => {
    setLoading(true);
    setError(null);

    try {
      console.log('提交维度模板数据:', templateData);

      // 获取 JWT token
      const tokenManager = (await import('@/lib/token-manager')).tokenManager;
      const accessToken = await tokenManager.getValidAccessToken();

      console.log('🔍 前端页面调用API:', {
        hasToken: !!accessToken,
        tokenLength: accessToken?.length,
      });

      // 转换字段名为后端期望的格式
      const backendData = {
        dimension_code: templateData.dimensionCode,
        dimension_name: templateData.dimensionName,
        dimension_type: templateData.dimensionType,
        description: templateData.description,
        sort_order: templateData.sortOrder || 0,
      };

      console.log('🔍 转换后的后端数据:', backendData);

      // 调用后端 API 创建维度模板
      const response = await fetch('/api/dimension-templates', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${accessToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(backendData),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || '创建维度模板失败');
      }

      const result = await response.json();
      console.log('✅ 维度模板创建成功:', result);

      setShowForm(false);
      setSelectedTemplate(null);

      // 刷新页面以显示新创建的模板
      window.location.reload();
    } catch (err) {
      console.error('❌ 创建维度模板失败:', err);
      setError(err instanceof Error ? err.message : '操作失败');
    } finally {
      setLoading(false);
    }
  };

  const handleDialogSubmit = async () => {
    // 这里需要触发表单提交
    // 由于表单在子组件中，我们需要通过 ref 或其他方式触发
    // 暂时使用模拟数据
    const mockData: Partial<DimensionTemplate> = {
      dimensionCode: 'test',
      dimensionName: '测试维度',
      dimensionType: 'select',
      description: '测试描述',
      sortOrder: 0,
      isActive: true,
    };

    await handleFormSubmit(mockData);
  };

  const handleValueSubmit = async (values: DimensionValue[]) => {
    setLoading(true);
    setError(null);

    try {
      if (!selectedTemplate) {
        throw new Error('未选择模板');
      }

      const response = await fetch(`/api/dimension-templates/${selectedTemplate.id}/values`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify({ values }),
      });
      
      if (!response.ok) {
        throw new Error('保存维度值失败');
      }
      
      console.log('维度值保存成功');
      setShowValueManager(false);
      setSelectedTemplate(null);
      
      // 刷新模板列表
      await loadTemplates();
    } catch (err) {
      setError(err instanceof Error ? err.message : '操作失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <ProtectedRoute>
      <DashboardLayout>
        <Box sx={{ p: 3 }}>
          {/* 页面标题 */}
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
            <SettingsIcon sx={{ mr: 1, color: 'primary.main' }} />
            <Typography variant='h4' component='h1'>
              维度模板管理
            </Typography>
          </Box>

          {/* 错误提示 */}
          {error && (
            <Alert
              severity='error'
              sx={{ mb: 2 }}
              onClose={() => setError(null)}
            >
              {error}
            </Alert>
          )}

          {/* 操作按钮 */}
          <Box sx={{ mb: 3, display: 'flex', gap: 2 }}>
            <Button
              variant='outlined'
              startIcon={<RefreshIcon />}
              onClick={handleRefresh}
              disabled={loading}
            >
              刷新
            </Button>
            <Button
              variant='contained'
              startIcon={<AddIcon />}
              onClick={handleCreateTemplate}
              disabled={loading}
            >
              新建维度模板
            </Button>
          </Box>

          {/* 主要内容区域 */}
          <Paper sx={{ p: 2, height: 'calc(100vh - 200px)', overflow: 'auto' }}>
            <DimensionTemplateList
              key={refreshKey}
              onEditTemplate={handleEditTemplate}
              onManageValues={handleManageValues}
              loading={loading}
            />
          </Paper>

          {/* 弹窗表单 */}
          {showForm && (
            <Dialog
              open={showForm}
              onClose={handleFormClose}
              maxWidth='md'
              fullWidth
            >
              <DialogTitle>
                {selectedTemplate ? '编辑维度模板' : '新建维度模板'}
              </DialogTitle>
              <DialogContent>
                <DimensionTemplateForm
                  template={selectedTemplate}
                  onSubmit={handleFormSubmit}
                  onClose={handleFormClose}
                  loading={loading}
                />
              </DialogContent>
              <DialogActions>
                <Button
                  variant='outlined'
                  onClick={handleFormClose}
                  disabled={loading}
                >
                  取消
                </Button>
                <Button
                  variant='contained'
                  onClick={handleDialogSubmit}
                  disabled={loading}
                  startIcon={
                    loading ? <CircularProgress size={20} /> : <AddIcon />
                  }
                >
                  {loading ? '保存中...' : selectedTemplate ? '更新' : '创建'}
                </Button>
              </DialogActions>
            </Dialog>
          )}

          {/* 弹窗值管理器 */}
          {showValueManager && selectedTemplate && (
            <Dialog
              open={showValueManager}
              onClose={handleValueManagerClose}
              maxWidth='lg'
              fullWidth
            >
              <DialogTitle>
                管理维度值 - {selectedTemplate.dimensionName}
              </DialogTitle>
              <DialogContent>
                <DimensionValueManager
                  template={selectedTemplate}
                  onSubmit={handleValueSubmit}
                  onClose={handleValueManagerClose}
                  loading={loading}
                />
              </DialogContent>
            </Dialog>
          )}

          {/* 加载指示器 */}
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
