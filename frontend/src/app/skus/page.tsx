'use client';

import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Button,
  Chip,
  CircularProgress,
  Alert,
  Grid,
  Card,
  CardContent,
  CardActions,
  IconButton,
  Tooltip,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import {
  Add as AddIcon,
  Refresh as RefreshIcon,
  FilterList as FilterIcon,
  Sort as SortIcon,
  MoreVert as MoreVertIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Visibility as ViewIcon,
  Download as DownloadIcon,
} from '@mui/icons-material';

import { SkuList } from '@/components/skus/SkuList';
import { SkuFilters } from '@/components/skus/SkuFilters';
import { SkuBulkActions } from '@/components/skus/SkuBulkActions';
import { AdvancedSearch } from '@/components/common/AdvancedSearch';
import { DynamicTable } from '@/components/common/DynamicTable';

export default function SkusPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [skus, setSkus] = useState<any[]>([]);
  const [selectedSkus, setSelectedSkus] = useState<string[]>([]);
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [searchFilters, setSearchFilters] = useState<any[]>([]);
  const [columns, setColumns] = useState<any[]>([]);

  // 弹窗状态管理
  const [showSkuForm, setShowSkuForm] = useState(false);
  const [selectedSku, setSelectedSku] = useState<any>(null);
  const [formMode, setFormMode] = useState<'create' | 'edit'>('create');

  // 加载SKU数据
  const loadSkus = async () => {
    try {
      setLoading(true);
      setError(null);
      const { frontendApi } = await import('@/lib/api');
      const data = await frontendApi.get('/api/product-variants');
      setSkus(data);
    } catch (err: any) {
      console.error('加载SKU列表失败:', err);
      setError(err.message || '加载SKU列表失败');
      // 使用mock数据作为fallback
      setSkus([
        {
          id: '1',
          sku: 'IMP-BSC-BLK-L',
          name: 'IMPEACH BASIC BLACK - L',
          product_id: '1',
          attributes: { color: 'Black', size: 'L' },
          price: 29.99,
          cost: 15.00,
          stock: 100,
          is_active: true,
          created_at: '2025-01-01T00:00:00Z',
        },
        {
          id: '2',
          sku: 'IMP-BSC-BLK-M',
          name: 'IMPEACH BASIC BLACK - M',
          product_id: '1',
          attributes: { color: 'Black', size: 'M' },
          price: 29.99,
          cost: 15.00,
          stock: 50,
          is_active: true,
          created_at: '2025-01-01T00:00:00Z',
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSkus();
    
    // 初始化列配置
    const initialColumns = [
      { id: 'sku', label: 'SKU', field: 'sku', type: 'text', sortable: true, filterable: true },
      { id: 'name', label: '名称', field: 'name', type: 'text', sortable: true, filterable: true },
      { id: 'product_id', label: '产品ID', field: 'product_id', type: 'text', sortable: true, filterable: true },
      { id: 'attributes', label: '属性', field: 'attributes', type: 'chip', sortable: false, filterable: false },
      { id: 'price', label: '价格', field: 'price', type: 'number', sortable: true, filterable: true },
      { id: 'cost', label: '成本', field: 'cost', type: 'number', sortable: true, filterable: true },
      { id: 'stock', label: '库存', field: 'stock', type: 'number', sortable: true, filterable: true },
      { id: 'is_active', label: '状态', field: 'is_active', type: 'boolean', sortable: true, filterable: true },
      { id: 'created_at', label: '创建时间', field: 'created_at', type: 'date', sortable: true, filterable: true },
    ];
    setColumns(initialColumns);
  }, []);

  const handleRefresh = () => {
    loadSkus();
  };

  const handleBulkAction = (action: string) => {
    console.log('Bulk action:', action, selectedSkus);
    // TODO: 实现批量操作
  };

  // 高级搜索处理
  const handleAdvancedSearch = (filters: any[]) => {
    setSearchFilters(filters);
    // TODO: 实现高级搜索逻辑
    console.log('Advanced search filters:', filters);
  };

  const handleClearSearch = () => {
    setSearchFilters([]);
    loadSkus();
  };

  // 动态列配置
  const handleColumnConfig = (newColumns: any[]) => {
    setColumns(newColumns);
  };

  // 排序处理
  const handleSort = (field: string, direction: 'asc' | 'desc') => {
    console.log('Sort:', field, direction);
    // TODO: 实现排序逻辑
  };

  // 行选择处理
  const handleRowSelect = (selectedRows: any[]) => {
    setSelectedSkus(selectedRows.map(row => row.id));
  };

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  // 弹窗处理函数
  const handleCreateSku = () => {
    setFormMode('create');
    setSelectedSku(null);
    setShowSkuForm(true);
  };

  const handleEditSku = (sku: any) => {
    setFormMode('edit');
    setSelectedSku(sku);
    setShowSkuForm(true);
  };

  const handleSkuFormClose = () => {
    setShowSkuForm(false);
    setSelectedSku(null);
  };

  const handleSkuAction = async (action: string, skuId: string) => {
    try {
      setLoading(true);
      setError(null);
      
      if (action === 'edit') {
        // 编辑SKU
        const sku = skus.find(s => s.id === skuId);
        if (sku) {
          setFormMode('edit');
          setSelectedSku(sku);
          setShowSkuForm(true);
        }
      } else if (action === 'delete') {
        // 删除SKU
        const response = await fetch(`/api/product-variants/${skuId}`, {
          method: 'DELETE',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`,
          },
        });
        
        if (!response.ok) {
          throw new Error('删除SKU失败');
        }
        
        console.log('SKU删除成功');
        // 刷新列表
        handleRefresh();
      }
    } catch (err: any) {
      console.error('SKU操作失败:', err);
      setError(err.message || '操作失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSkuFormSubmit = async (skuData: any) => {
    setLoading(true);
    try {
      const url = formMode === 'create' 
        ? '/api/product-variants'
        : `/api/product-variants/${selectedSku.id}`;
      
      const method = formMode === 'create' ? 'POST' : 'PUT';
      
      const response = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify(skuData),
      });
      
      if (!response.ok) {
        throw new Error(`${formMode === 'create' ? '创建' : '更新'}SKU失败`);
      }
      
      console.log(`SKU ${formMode === 'create' ? '创建' : '更新'}成功`);
      setShowSkuForm(false);
      setSelectedSku(null);
      // 刷新列表
      handleRefresh();
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
              SKU 列表
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
                onClick={handleCreateSku}
              >
                创建 SKU
              </Button>
              <IconButton onClick={handleMenuOpen}>
                <MoreVertIcon />
              </IconButton>
              <Menu
                anchorEl={anchorEl}
                open={Boolean(anchorEl)}
                onClose={handleMenuClose}
              >
                <MenuItem onClick={handleMenuClose}>
                  <ListItemIcon>
                    <DownloadIcon />
                  </ListItemIcon>
                  <ListItemText>导出数据</ListItemText>
                </MenuItem>
              </Menu>
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

          {/* 高级搜索 */}
          <AdvancedSearch
            fields={[
              { key: 'sku', label: 'SKU', type: 'text' },
              { key: 'name', label: '名称', type: 'text' },
              { key: 'product_id', label: '产品ID', type: 'text' },
              { key: 'price', label: '价格', type: 'number', min: 0, max: 10000 },
              { key: 'cost', label: '成本', type: 'number', min: 0, max: 10000 },
              { key: 'stock', label: '库存', type: 'number', min: 0, max: 10000 },
              { key: 'is_active', label: '状态', type: 'boolean' },
              { key: 'created_at', label: '创建时间', type: 'date' },
            ]}
            onSearch={handleAdvancedSearch}
            onClear={handleClearSearch}
            loading={loading}
          />

          {/* 筛选器 */}
          <Paper sx={{ p: 2, mb: 3 }}>
            <SkuFilters
              onFiltersChange={filters => console.log('Filters:', filters)}
            />
          </Paper>

          {/* 批量操作 */}
          {selectedSkus.length > 0 && (
            <SkuBulkActions
              selectedCount={selectedSkus.length}
              onBulkAction={handleBulkAction}
              onClearSelection={() => setSelectedSkus([])}
            />
          )}

          {/* SKU 动态表格 */}
          <Paper sx={{ minHeight: 400 }}>
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
              <DynamicTable
                columns={columns}
                data={skus}
                loading={loading}
                onSort={handleSort}
                onRowSelect={handleRowSelect}
                onColumnConfig={handleColumnConfig}
                selectable={true}
                sortable={true}
                filterable={true}
                exportable={true}
              />
            )}
          </Paper>

          {/* SKU 表单弹窗 */}
          {showSkuForm && (
            <Dialog
              open={showSkuForm}
              onClose={handleSkuFormClose}
              maxWidth='md'
              fullWidth
            >
              <DialogTitle>
                {formMode === 'create' ? '创建 SKU' : '编辑 SKU'}
              </DialogTitle>
              <DialogContent>
                {/* TODO: 这里需要添加 SKU 表单组件 */}
                <Box sx={{ p: 2 }}>
                  <Typography variant='body1'>
                    SKU 表单组件将在这里显示
                  </Typography>
                  <Typography
                    variant='body2'
                    color='text.secondary'
                    sx={{ mt: 1 }}
                  >
                    模式: {formMode === 'create' ? '创建' : '编辑'}
                  </Typography>
                  {selectedSku && (
                    <Typography
                      variant='body2'
                      color='text.secondary'
                      sx={{ mt: 1 }}
                    >
                      选中的 SKU: {selectedSku.id || 'N/A'}
                    </Typography>
                  )}
                </Box>
              </DialogContent>
              <DialogActions>
                <Button
                  variant='outlined'
                  onClick={handleSkuFormClose}
                  disabled={loading}
                >
                  取消
                </Button>
                <Button
                  variant='contained'
                  onClick={() => handleSkuFormSubmit({})}
                  disabled={loading}
                  startIcon={
                    loading ? <CircularProgress size={20} /> : <AddIcon />
                  }
                >
                  {loading
                    ? '保存中...'
                    : formMode === 'create'
                      ? '创建'
                      : '更新'}
                </Button>
              </DialogActions>
            </Dialog>
          )}
        </Box>
      </DashboardLayout>
    </ProtectedRoute>
  );
}
