'use client';

import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Button,
  Alert,
  Grid,
  Card,
  CardContent,
  CardActions,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  CircularProgress,
} from '@mui/material';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Visibility as ViewIcon,
  Refresh as RefreshIcon,
  Category as CategoryIcon,
  Link as LinkIcon,
  Settings as SettingsIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
} from '@mui/icons-material';

import { CategoryTree } from '@/components/product-categories/CategoryTree';
import { CategoryForm } from '@/components/product-categories/CategoryForm';
import { CategoryRelationManager } from '@/components/product-categories/CategoryRelationManager';
import { CategoryDimensionManager } from '@/components/product-categories/CategoryDimensionManager';

export default function ProductCategoriesPage() {
  const [categories, setCategories] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<any>(null);
  const [showCategoryForm, setShowCategoryForm] = useState(false);
  const [showRelationManager, setShowRelationManager] = useState(false);
  const [showDimensionManager, setShowDimensionManager] = useState(false);
  const [formMode, setFormMode] = useState<'create' | 'edit'>('create');

  // 加载产品分类数据
  const loadCategories = async () => {
    try {
      setLoading(true);
      setError(null);
      const { frontendApi } = await import('@/lib/api');
      const data = await frontendApi.get('/api/product-categories');
      setCategories(data);
    } catch (err: any) {
      console.error('加载产品分类失败:', err);
      setError(err.message || '加载产品分类失败');
      // 使用mock数据作为fallback
      setCategories([
        {
          id: '1',
          name: '电子产品',
          code: 'electronics',
          description: '电子设备及相关产品',
          parent_id: null,
          level: 0,
          path: '/electronics',
          is_active: true,
          created_at: '2025-01-01T00:00:00Z',
        },
        {
          id: '2',
          name: '服装',
          code: 'clothing',
          description: '服装及相关产品',
          parent_id: null,
          level: 0,
          path: '/clothing',
          is_active: true,
          created_at: '2025-01-01T00:00:00Z',
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCategories();
  }, []);

  const handleRefresh = () => {
    loadCategories();
  };

  const handleCreateCategory = () => {
    setFormMode('create');
    setSelectedCategory(null);
    setShowCategoryForm(true);
  };

  const handleEditCategory = (category: any) => {
    setFormMode('edit');
    setSelectedCategory(category);
    setShowCategoryForm(true);
  };

  const handleDeleteCategory = async (category: any) => {
    try {
      setLoading(true);
      const { frontendApi } = await import('@/lib/api');
      await frontendApi.delete(`/api/product-categories/${category.id}`);
      
      // 刷新分类列表
      await loadCategories();
      console.log('产品分类删除成功');
    } catch (err: any) {
      console.error('删除产品分类失败:', err);
      setError(err.message || '删除产品分类失败');
    } finally {
      setLoading(false);
    }
  };

  const handleManageRelations = (category: any) => {
    setSelectedCategory(category);
    setShowRelationManager(true);
  };

  const handleManageDimensions = (category: any) => {
    setSelectedCategory(category);
    setShowDimensionManager(true);
  };

  const handleCategoryFormSubmit = async (formData: any) => {
    try {
      setLoading(true);
      setError(null);
      
      // 转换前端字段名到后端期望的字段名
      const backendData = {
        category_name: formData.name,
        category_code: formData.code,
        description: formData.description,
        is_root: formData.isRoot,
        sort_order: formData.sortOrder,
        parent_category_ids: formData.parentCategoryIds || null,
      };
      
      const { frontendApi } = await import('@/lib/api');
      
      if (formMode === 'create') {
        await frontendApi.post('/api/product-categories', backendData);
      } else {
        await frontendApi.put(`/api/product-categories/${selectedCategory.id}`, backendData);
      }
      
      // 刷新分类列表
      await loadCategories();
      setShowCategoryForm(false);
      console.log(`产品分类${formMode === 'create' ? '创建' : '更新'}成功`);
    } catch (err: any) {
      console.error('保存产品分类失败:', err);
      setError(err.message || '保存产品分类失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <ProtectedRoute>
      <DashboardLayout>
        <Box sx={{ p: 3 }}>
          {/* 页面标题和操作 */}
          <Box
            sx={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              mb: 3,
            }}
          >
            <Typography variant='h4' component='h1' sx={{ fontWeight: 600 }}>
              产品分类管理
            </Typography>
            <Box sx={{ display: 'flex', gap: 2 }}>
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
                onClick={handleCreateCategory}
              >
                创建分类
              </Button>
            </Box>
          </Box>

          {/* 错误提示 */}
          {error && (
            <Alert
              severity='error'
              sx={{ mb: 3 }}
              onClose={() => setError(null)}
            >
              {error}
            </Alert>
          )}

          {/* 分类树和详情 */}
          <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
            {/* 分类树 */}
            <Box sx={{ width: { xs: "100%", md: "50%" } }}>
              <Paper sx={{ p: 2, height: 600 }}>
                <Box
                  sx={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    mb: 2,
                  }}
                >
                  <Typography variant='h6'>分类树</Typography>
                  <Tooltip title='展开/收起所有'>
                    <IconButton size='small'>
                      <ExpandMoreIcon />
                    </IconButton>
                  </Tooltip>
                </Box>
                {loading ? (
                  <Box
                    sx={{
                      display: 'flex',
                      justifyContent: 'center',
                      alignItems: 'center',
                      height: 400,
                    }}
                  >
                    <CircularProgress />
                  </Box>
                ) : (
                  <CategoryTree
                    categories={categories}
                    onCategorySelect={setSelectedCategory}
                    onCategoryEdit={handleEditCategory}
                    onCategoryDelete={handleDeleteCategory}
                    onManageRelations={handleManageRelations}
                    onManageDimensions={handleManageDimensions}
                  />
                )}
              </Paper>
            </Box>

            {/* 分类详情 */}
            <Box sx={{ width: { xs: "100%", md: "50%" } }}>
              <Paper sx={{ p: 2, height: 600 }}>
                <Typography variant='h6' sx={{ mb: 2 }}>
                  分类详情
                </Typography>
                {selectedCategory ? (
                  <Box>
                    <Card sx={{ mb: 2 }}>
                      <CardContent>
                        <Typography variant='h6' gutterBottom>
                          {selectedCategory.name}
                        </Typography>
                        <Typography
                          variant='body2'
                          color='text.secondary'
                          sx={{ mb: 2 }}
                        >
                          {selectedCategory.description || '暂无描述'}
                        </Typography>
                        <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
                          <Chip
                            label={`编码: ${selectedCategory.code}`}
                            size='small'
                          />
                          <Chip
                            label={selectedCategory.isActive ? '激活' : '停用'}
                            color={
                              selectedCategory.isActive ? 'success' : 'error'
                            }
                            size='small'
                          />
                          {selectedCategory.isRoot && (
                            <Chip label='根分类' color='primary' size='small' />
                          )}
                        </Box>
                        <Typography variant='body2' sx={{ mb: 1 }}>
                          <strong>父分类:</strong>{' '}
                          {selectedCategory.parents?.length || 0} 个
                        </Typography>
                        <Typography variant='body2' sx={{ mb: 1 }}>
                          <strong>子分类:</strong>{' '}
                          {selectedCategory.children?.length || 0} 个
                        </Typography>
                        <Typography variant='body2' sx={{ mb: 1 }}>
                          <strong>维度数量:</strong>{' '}
                          {selectedCategory.dimensions?.length || 0} 个
                        </Typography>
                        <Typography variant='body2' sx={{ mb: 1 }}>
                          <strong>产品数量:</strong>{' '}
                          {selectedCategory.productCount || 0} 个
                        </Typography>
                      </CardContent>
                      <CardActions>
                        <Button
                          size='small'
                          startIcon={<EditIcon />}
                          onClick={() => handleEditCategory(selectedCategory)}
                        >
                          编辑
                        </Button>
                        <Button
                          size='small'
                          startIcon={<LinkIcon />}
                          onClick={() =>
                            handleManageRelations(selectedCategory)
                          }
                        >
                          管理关系
                        </Button>
                        <Button
                          size='small'
                          startIcon={<SettingsIcon />}
                          onClick={() =>
                            handleManageDimensions(selectedCategory)
                          }
                        >
                          管理维度
                        </Button>
                      </CardActions>
                    </Card>
                  </Box>
                ) : (
                  <Box
                    sx={{
                      display: 'flex',
                      justifyContent: 'center',
                      alignItems: 'center',
                      height: 400,
                    }}
                  >
                    <Typography variant='body1' color='text.secondary'>
                      请选择一个分类查看详情
                    </Typography>
                  </Box>
                )}
              </Paper>
            </Box>
          </Box>

          {/* 分类表单对话框 */}
          <Dialog
            open={showCategoryForm}
            onClose={() => setShowCategoryForm(false)}
            maxWidth='md'
            fullWidth
          >
            <DialogTitle>
              {formMode === 'create' ? '创建分类' : '编辑分类'}
            </DialogTitle>
            <DialogContent>
              <CategoryForm
                category={selectedCategory}
                mode={formMode}
                onSave={handleCategoryFormSubmit}
                onCancel={() => setShowCategoryForm(false)}
              />
            </DialogContent>
          </Dialog>

          {/* 关系管理对话框 */}
          <Dialog
            open={showRelationManager}
            onClose={() => setShowRelationManager(false)}
            maxWidth='lg'
            fullWidth
          >
            <DialogTitle>管理分类关系</DialogTitle>
            <DialogContent>
              <CategoryRelationManager
                category={selectedCategory}
                onSave={relations => {
                  console.log('Save relations:', relations);
                  setShowRelationManager(false);
                }}
                onCancel={() => setShowRelationManager(false)}
              />
            </DialogContent>
          </Dialog>

          {/* 维度管理对话框 */}
          <Dialog
            open={showDimensionManager}
            onClose={() => setShowDimensionManager(false)}
            maxWidth='lg'
            fullWidth
          >
            <DialogTitle>管理分类维度</DialogTitle>
            <DialogContent>
              <CategoryDimensionManager
                category={selectedCategory}
                onSave={dimensions => {
                  console.log('Save dimensions:', dimensions);
                  setShowDimensionManager(false);
                }}
                onCancel={() => setShowDimensionManager(false)}
              />
            </DialogContent>
          </Dialog>
        </Box>
      </DashboardLayout>
    </ProtectedRoute>
  );
}
