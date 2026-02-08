'use client';

import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  Chip,
  Avatar,
  Alert,
  CircularProgress,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Tooltip,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Grid,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  DialogContentText,
  Checkbox,
  TablePagination,
} from '@mui/material';
import {
  Search as SearchIcon,
  Refresh as RefreshIcon,
  Visibility as ViewIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Add as AddIcon,
  Storefront as ShopifyIcon,
  Storefront as StorefrontIcon,
  Print as PrintifyIcon,
  Public as YahooIcon,
  Storefront as RakutenIcon,
} from '@mui/icons-material';
import { frontendApi } from '@/lib/api';
import { frontendLogger } from '@/lib/frontend-logger';

interface ProductMapping {
  id: number;
  id_hashid: string;
  core_product_id: number;
  core_variant_id: number | null;
  external_system_id: number;
  external_product_id: string;
  external_variant_id: string | null;
  mapping_type: string;
  sync_direction: string;
  sync_status: string;
  created_at: string;
  core_product_title: string;
  core_variant_sku: string | null;
  external_system_name: string;
  system_type: string;
}

interface SearchFilters {
  coreProduct: string;
  externalSystem: string;
  syncStatus: string;
  mappingType: string;
}

export function ProductMappingManager() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [mappings, setMappings] = useState<ProductMapping[]>([]);
  const [searchFilters, setSearchFilters] = useState<SearchFilters>({
    coreProduct: '',
    externalSystem: '',
    syncStatus: '',
    mappingType: '',
  });
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [mappingToDelete, setMappingToDelete] = useState<ProductMapping | null>(
    null
  );
  const [selectedMappingIds, setSelectedMappingIds] = useState<string[]>([]);
  const [batchDeleteDialogOpen, setBatchDeleteDialogOpen] = useState(false);
  const [batchDeleting, setBatchDeleting] = useState(false);
  const [deleteByFilterDialogOpen, setDeleteByFilterDialogOpen] = useState(false);
  const [deleteByFiltering, setDeleteByFiltering] = useState(false);
  const [page, setPage] = useState(0); // 0-based for MUI TablePagination
  const [rowsPerPage, setRowsPerPage] = useState(20);
  const [totalCount, setTotalCount] = useState(0);
  /** 已应用到请求的筛选条件（点击「搜索」时更新），翻页时沿用 */
  const [appliedFilters, setAppliedFilters] = useState<SearchFilters>({
    coreProduct: '',
    externalSystem: '',
    syncStatus: '',
    mappingType: '',
  });

  const fetchMappings = async (
    pageNum?: number,
    limitNum?: number,
    filters?: SearchFilters
  ) => {
    const p = pageNum ?? page + 1;
    const l = limitNum ?? rowsPerPage;
    const f = filters ?? appliedFilters;
    try {
      setLoading(true);
      setError(null);

      const params: Record<string, string | number> = {
        page: p,
        limit: l,
      };
      if (f.coreProduct?.trim()) {
        params.core_product_title = f.coreProduct.trim();
      }
      if (f.externalSystem?.trim()) {
        params.system_type = f.externalSystem.trim();
      }
      if (f.syncStatus?.trim()) {
        params.sync_status = f.syncStatus.trim();
      }
      if (f.mappingType?.trim()) {
        params.mapping_type = f.mappingType.trim();
      }

      frontendLogger.info('🔍 开始获取商品映射数据', { page: p, limit: l, params });

      const response = await frontendApi.get('/api/products/mappings', {
        params,
      });

      const mappingsData = response.data.mappings || [];
      const total =
        response.data.pagination?.total ??
        response.data.total ??
        0;
      frontendLogger.info('✅ 商品映射数据获取成功', {
        count: mappingsData.length,
        total,
      });

      setMappings(mappingsData);
      setTotalCount(total);
    } catch (err: any) {
      frontendLogger.error('❌ 获取商品映射数据失败', {
        error: err.response?.data?.detail || err.message,
      });
      setError(
        err.response?.data?.detail || err.message || 'Failed to fetch mappings'
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMappings(page + 1, rowsPerPage, appliedFilters);
  }, [page, rowsPerPage, appliedFilters.coreProduct, appliedFilters.externalSystem, appliedFilters.syncStatus, appliedFilters.mappingType]);

  /** 点击「搜索」：应用当前筛选并跳到第 1 页（useEffect 会带 appliedFilters 请求） */
  const handleSearch = () => {
    setAppliedFilters(searchFilters);
    setPage(0);
    setSelectedMappingIds([]);
  };

  /** 点击「清空」：清除筛选并跳到第 1 页 */
  const handleClearFiltersAndSearch = () => {
    const empty: SearchFilters = {
      coreProduct: '',
      externalSystem: '',
      syncStatus: '',
      mappingType: '',
    };
    setSearchFilters(empty);
    setAppliedFilters(empty);
    setPage(0);
    setSelectedMappingIds([]);
  };

  const getSystemIcon = (systemType: string) => {
    switch (systemType) {
      case 'SHOPIFY':
        return <ShopifyIcon />;
      case 'PRINTIFY':
        return <PrintifyIcon />;
      case 'YAHOO':
        return <YahooIcon />;
      case 'RAKUTEN':
        return <RakutenIcon />;
      default:
        return <StorefrontIcon />;
    }
  };

  const getSystemColor = (systemType: string) => {
    switch (systemType) {
      case 'SHOPIFY':
        return '#96BF47';
      case 'PRINTIFY':
        return '#FF6600';
      case 'YAHOO':
        return '#FF6600';
      case 'RAKUTEN':
        return '#BF0000';
      default:
        return '#1976d2';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'success';
      case 'synced':
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
      case 'synced':
        return '已同步';
      case 'pending':
        return '待处理';
      case 'error':
        return '错误';
      default:
        return status;
    }
  };

  const getMappingTypeText = (type: string) => {
    switch (type) {
      case 'manual':
        return '手动';
      case 'sync':
        return '同步';
      case 'product':
        return '商品';
      case 'variant':
        return '变体';
      default:
        return type;
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

  const handleSearchChange = (field: keyof SearchFilters, value: string) => {
    setSearchFilters(prev => ({
      ...prev,
      [field]: value,
    }));
  };


  const handleViewMapping = (mapping: ProductMapping) => {
    frontendLogger.info('👁️ 查看商品映射详情', { mappingId: mapping.id });
    // TODO: 实现查看映射详情的功能
    console.log('View mapping:', mapping);
  };

  const handleEditMapping = (mapping: ProductMapping) => {
    frontendLogger.info('✏️ 编辑商品映射', { mappingId: mapping.id });
    // TODO: 实现编辑映射的功能
    console.log('Edit mapping:', mapping);
  };

  const handleDeleteMapping = (mapping: ProductMapping) => {
    setMappingToDelete(mapping);
    setDeleteDialogOpen(true);
  };

  const toggleSelectAll = () => {
    if (selectedMappingIds.length >= mappings.length) {
      setSelectedMappingIds([]);
    } else {
      setSelectedMappingIds(mappings.map(m => m.id_hashid));
    }
  };

  const toggleSelectOne = (idHashid: string) => {
    setSelectedMappingIds(prev =>
      prev.includes(idHashid)
        ? prev.filter(id => id !== idHashid)
        : [...prev, idHashid]
    );
  };

  /** 当前是否有任意筛选条件已应用（用于「按条件全部删除」） */
  const hasAppliedFilter = Boolean(
    appliedFilters.coreProduct?.trim() ||
      appliedFilters.externalSystem?.trim() ||
      appliedFilters.syncStatus?.trim() ||
      appliedFilters.mappingType?.trim()
  );

  const handleBatchDelete = () => {
    if (selectedMappingIds.length === 0) return;
    setBatchDeleteDialogOpen(true);
  };

  const handleDeleteByFilter = () => {
    if (!hasAppliedFilter) return;
    setDeleteByFilterDialogOpen(true);
  };

  const confirmDeleteByFilter = async () => {
    if (!hasAppliedFilter) return;
    try {
      setDeleteByFiltering(true);
      setError(null);
      const body: Record<string, string | undefined> = {};
      if (appliedFilters.coreProduct?.trim()) body.core_product_title = appliedFilters.coreProduct.trim();
      if (appliedFilters.externalSystem?.trim()) body.system_type = appliedFilters.externalSystem.trim();
      if (appliedFilters.syncStatus?.trim()) body.sync_status = appliedFilters.syncStatus.trim();
      if (appliedFilters.mappingType?.trim()) body.mapping_type = appliedFilters.mappingType.trim();
      const res = await frontendApi.post('/api/products/mappings/batch-delete-by-filter', body);
      frontendLogger.info('✅ 按条件全部删除成功', res.data);
      setDeleteByFilterDialogOpen(false);
      setPage(0);
      setSelectedMappingIds([]);
      await fetchMappings(1, rowsPerPage, appliedFilters);
    } catch (err: any) {
      frontendLogger.error('❌ 按条件全部删除失败', {
        error: err.response?.data?.detail || err.message,
      });
      setError(
        err.response?.data?.detail || err.message || '按条件删除失败'
      );
    } finally {
      setDeleteByFiltering(false);
    }
  };

  const confirmBatchDelete = async () => {
    if (selectedMappingIds.length === 0) return;
    try {
      setBatchDeleting(true);
      setError(null);
      const res = await frontendApi.post('/api/products/mappings/batch-delete', {
        mapping_id_hashids: selectedMappingIds,
      });
      frontendLogger.info('✅ 批量删除映射成功', res.data);
      setSelectedMappingIds([]);
      setBatchDeleteDialogOpen(false);
      await fetchMappings(page + 1, rowsPerPage);
    } catch (err: any) {
      frontendLogger.error('❌ 批量删除映射失败', {
        error: err.response?.data?.detail || err.message,
      });
      setError(
        err.response?.data?.detail || err.message || '批量删除失败'
      );
    } finally {
      setBatchDeleting(false);
    }
  };

  const confirmDeleteMapping = async () => {
    if (!mappingToDelete) return;

    try {
      frontendLogger.info('🗑️ 开始删除商品映射', {
        mappingId: mappingToDelete.id,
      });

      await frontendApi.delete(
        `/api/products/mappings/${mappingToDelete.id_hashid}`
      );

      frontendLogger.info('✅ 商品映射删除成功', {
        mappingId: mappingToDelete.id,
      });

      // 刷新数据（沿用当前筛选）
      await fetchMappings(page + 1, rowsPerPage, appliedFilters);
      setDeleteDialogOpen(false);
      setMappingToDelete(null);
    } catch (err: any) {
      frontendLogger.error('❌ 删除商品映射失败', {
        error: err.response?.data?.detail || err.message,
        mappingId: mappingToDelete.id,
      });
      setError(
        err.response?.data?.detail || err.message || 'Failed to delete mapping'
      );
    }
  };

  const handleCreateMapping = () => {
    frontendLogger.info('➕ 创建新商品映射');
    // TODO: 实现创建映射的功能
    console.log('Create new mapping');
  };

  if (loading) {
    return (
      <Box
        display='flex'
        justifyContent='center'
        alignItems='center'
        minHeight='400px'
      >
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Box
        display='flex'
        justifyContent='space-between'
        alignItems='center'
        mb={3}
      >
        <Typography variant='h4' component='h1'>
          商品映射管理
        </Typography>
        <Box display='flex' gap={2}>
          <Button
            variant='outlined'
            startIcon={<RefreshIcon />}
            onClick={() => fetchMappings(page + 1, rowsPerPage, appliedFilters)}
            disabled={loading}
          >
            刷新数据
          </Button>
          <Button
            variant='outlined'
            color='error'
            startIcon={<DeleteIcon />}
            onClick={handleBatchDelete}
            disabled={selectedMappingIds.length === 0}
          >
            批量删除{selectedMappingIds.length > 0 ? ` (${selectedMappingIds.length})` : ''}
          </Button>
          <Button
            variant='outlined'
            color='error'
            startIcon={<DeleteIcon />}
            onClick={handleDeleteByFilter}
            disabled={!hasAppliedFilter || totalCount === 0 || loading}
            title={!hasAppliedFilter ? '请先设置筛选条件并点击「搜索」' : `删除符合当前条件的共 ${totalCount} 条映射`}
          >
            按条件全部删除{totalCount > 0 ? ` (${totalCount})` : ''}
          </Button>
          <Button
            variant='contained'
            startIcon={<AddIcon />}
            onClick={handleCreateMapping}
          >
            新建映射
          </Button>
        </Box>
      </Box>

      {error && (
        <Alert severity='error' sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {/* 搜索条件 */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant='h6' component='h2' mb={2}>
            搜索条件
          </Typography>
          <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
            <Box sx={{ width: "100%" }} md={3}>
              <TextField
                fullWidth
                label='核心商品'
                value={searchFilters.coreProduct}
                onChange={e =>
                  handleSearchChange('coreProduct', e.target.value)
                }
                placeholder='输入核心商品名称'
                size='small'
              />
            </Box>
            <Box sx={{ width: "100%" }} md={3}>
              <FormControl fullWidth size='small'>
                <InputLabel>外部系统</InputLabel>
                <Select
                  value={searchFilters.externalSystem}
                  onChange={e =>
                    handleSearchChange('externalSystem', e.target.value)
                  }
                  label='外部系统'
                >
                  <MenuItem value=''>全部</MenuItem>
                  <MenuItem value='SHOPIFY'>Shopify</MenuItem>
                  <MenuItem value='PRINTIFY'>Printify</MenuItem>
                  <MenuItem value='YAHOO'>Yahoo</MenuItem>
                  <MenuItem value='RAKUTEN'>乐天</MenuItem>
                </Select>
              </FormControl>
            </Box>
            <Box sx={{ width: "100%" }} md={2}>
              <FormControl fullWidth size='small'>
                <InputLabel>同步状态</InputLabel>
                <Select
                  value={searchFilters.syncStatus}
                  onChange={e =>
                    handleSearchChange('syncStatus', e.target.value)
                  }
                  label='同步状态'
                >
                  <MenuItem value=''>全部</MenuItem>
                  <MenuItem value='active'>活跃</MenuItem>
                  <MenuItem value='synced'>已同步</MenuItem>
                  <MenuItem value='pending'>待处理</MenuItem>
                  <MenuItem value='error'>错误</MenuItem>
                </Select>
              </FormControl>
            </Box>
            <Box sx={{ width: "100%" }} md={2}>
              <FormControl fullWidth size='small'>
                <InputLabel>映射类型</InputLabel>
                <Select
                  value={searchFilters.mappingType}
                  onChange={e =>
                    handleSearchChange('mappingType', e.target.value)
                  }
                  label='映射类型'
                >
                  <MenuItem value=''>全部</MenuItem>
                  <MenuItem value='manual'>手动</MenuItem>
                  <MenuItem value='sync'>同步</MenuItem>
                  <MenuItem value='product'>商品</MenuItem>
                  <MenuItem value='variant'>变体</MenuItem>
                </Select>
              </FormControl>
            </Box>
            <Box sx={{ width: "100%" }} md={2}>
              <Box display='flex' gap={1}>
                <Button
                  variant='outlined'
                  startIcon={<SearchIcon />}
                  onClick={handleSearch}
                  size='small'
                >
                  搜索
                </Button>
                <Button
                  variant='text'
                  onClick={handleClearFiltersAndSearch}
                  size='small'
                >
                  清空
                </Button>
              </Box>
            </Box>
          </Box>
        </CardContent>
      </Card>

      {/* 映射列表 */}
      <Card>
        <CardContent>
          <Box
            display='flex'
            justifyContent='space-between'
            alignItems='center'
            mb={2}
          >
            <Typography variant='h6' component='h2'>
              映射列表（共 {totalCount} 条，本页 {mappings.length} 条）
              {selectedMappingIds.length > 0 && (
                <Typography component='span' variant='body2' color='text.secondary' sx={{ ml: 1 }}>
                  已选 {selectedMappingIds.length} 条
                </Typography>
              )}
            </Typography>
          </Box>

          <TableContainer component={Paper} variant='outlined'>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell padding='checkbox'>
                    <Checkbox
                      indeterminate={
                        selectedMappingIds.length > 0 &&
                        selectedMappingIds.length < mappings.length
                      }
                      checked={
                        mappings.length > 0 &&
                        selectedMappingIds.length === mappings.length
                      }
                      onChange={toggleSelectAll}
                      aria-label='全选'
                    />
                  </TableCell>
                  <TableCell>核心商品</TableCell>
                  <TableCell>核心变体</TableCell>
                  <TableCell>外部系统</TableCell>
                  <TableCell>外部商品ID</TableCell>
                  <TableCell>外部变体ID</TableCell>
                  <TableCell>映射类型</TableCell>
                  <TableCell>同步状态</TableCell>
                  <TableCell>创建时间</TableCell>
                  <TableCell>操作</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {mappings.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={10} align='center'>
                      <Typography variant='body2' color='text.secondary'>
                        暂无映射记录
                      </Typography>
                    </TableCell>
                  </TableRow>
                ) : (
                  mappings.map(mapping => (
                    <TableRow key={mapping.id} hover>
                      <TableCell padding='checkbox'>
                        <Checkbox
                          checked={selectedMappingIds.includes(mapping.id_hashid)}
                          onChange={() => toggleSelectOne(mapping.id_hashid)}
                          onClick={e => e.stopPropagation()}
                          aria-label={`选择 ${mapping.core_product_title}`}
                        />
                      </TableCell>
                      <TableCell>
                        <Typography variant='body2' fontWeight='medium'>
                          {mapping.core_product_title}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant='body2'>
                          {mapping.core_variant_sku || '-'}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Box display='flex' alignItems='center'>
                          <Avatar
                            sx={{
                              bgcolor: getSystemColor(mapping.system_type),
                              width: 24,
                              height: 24,
                              mr: 1,
                            }}
                          >
                            {getSystemIcon(mapping.system_type)}
                          </Avatar>
                          <Typography variant='body2'>
                            {mapping.external_system_name}
                          </Typography>
                        </Box>
                      </TableCell>
                      <TableCell>
                        <Typography
                          variant='body2'
                          sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}
                        >
                          {mapping.external_product_id.length > 20
                            ? `${mapping.external_product_id.substring(0, 20)}...`
                            : mapping.external_product_id}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography
                          variant='body2'
                          sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}
                        >
                          {mapping.external_variant_id
                            ? mapping.external_variant_id.length > 20
                              ? `${mapping.external_variant_id.substring(0, 20)}...`
                              : mapping.external_variant_id
                            : '-'}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={getMappingTypeText(mapping.mapping_type)}
                          size='small'
                          variant='outlined'
                        />
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={getStatusText(mapping.sync_status)}
                          color={getStatusColor(mapping.sync_status) as any}
                          size='small'
                        />
                      </TableCell>
                      <TableCell>
                        <Typography variant='body2'>
                          {formatDate(mapping.created_at)}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Box display='flex' gap={1}>
                          <Tooltip title='查看详情'>
                            <IconButton
                              size='small'
                              onClick={() => handleViewMapping(mapping)}
                            >
                              <ViewIcon />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title='编辑'>
                            <IconButton
                              size='small'
                              onClick={() => handleEditMapping(mapping)}
                            >
                              <EditIcon />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title='删除'>
                            <IconButton
                              size='small'
                              color='error'
                              onClick={() => handleDeleteMapping(mapping)}
                            >
                              <DeleteIcon />
                            </IconButton>
                          </Tooltip>
                        </Box>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </TableContainer>
          <TablePagination
            component='div'
            count={totalCount}
            page={page}
            onPageChange={(_, newPage) => {
              setPage(newPage);
              setSelectedMappingIds([]);
            }}
            rowsPerPage={rowsPerPage}
            onRowsPerPageChange={e => {
              setRowsPerPage(parseInt(e.target.value, 10));
              setPage(0);
              setSelectedMappingIds([]);
            }}
            rowsPerPageOptions={[10, 20, 50, 100]}
            labelRowsPerPage='每页'
            labelDisplayedRows={({ from, to, count }) =>
              `${from}–${to} / 共 ${count !== -1 ? count : `${to} 以上`} 条`
            }
          />
        </CardContent>
      </Card>

      {/* 删除确认对话框 */}
      <Dialog
        open={deleteDialogOpen}
        onClose={() => setDeleteDialogOpen(false)}
        aria-labelledby='delete-dialog-title'
        aria-describedby='delete-dialog-description'
      >
        <DialogTitle id='delete-dialog-title'>确认删除映射</DialogTitle>
        <DialogContent>
          <DialogContentText id='delete-dialog-description'>
            您确定要删除以下商品映射吗？此操作不可撤销。
            {mappingToDelete && (
              <Box mt={2}>
                <Typography variant='body2' color='text.secondary'>
                  <strong>核心商品:</strong>{' '}
                  {mappingToDelete.core_product_title}
                  <br />
                  <strong>外部系统:</strong>{' '}
                  {mappingToDelete.external_system_name}
                  <br />
                  <strong>外部商品ID:</strong>{' '}
                  {mappingToDelete.external_product_id}
                </Typography>
              </Box>
            )}
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)}>取消</Button>
          <Button onClick={confirmDeleteMapping} color='error' autoFocus>
            删除
          </Button>
        </DialogActions>
      </Dialog>

      {/* 批量删除确认对话框 */}
      <Dialog
        open={batchDeleteDialogOpen}
        onClose={() => !batchDeleting && setBatchDeleteDialogOpen(false)}
        aria-labelledby='batch-delete-dialog-title'
      >
        <DialogTitle id='batch-delete-dialog-title'>确认批量删除</DialogTitle>
        <DialogContent>
          <DialogContentText>
            确定要删除选中的 <strong>{selectedMappingIds.length}</strong> 条映射吗？此操作不可撤销。
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setBatchDeleteDialogOpen(false)} disabled={batchDeleting}>
            取消
          </Button>
          <Button onClick={confirmBatchDelete} color='error' disabled={batchDeleting}>
            {batchDeleting ? '删除中…' : '全部删除'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* 按条件全部删除确认对话框 */}
      <Dialog
        open={deleteByFilterDialogOpen}
        onClose={() => !deleteByFiltering && setDeleteByFilterDialogOpen(false)}
        aria-labelledby='delete-by-filter-dialog-title'
      >
        <DialogTitle id='delete-by-filter-dialog-title'>按条件全部删除</DialogTitle>
        <DialogContent>
          <DialogContentText>
            将删除符合<strong>当前筛选条件</strong>的共 <strong>{totalCount}</strong> 条映射（如：外部系统=Shopify 时删除全部 Shopify 映射）。此操作不可撤销，确定继续？
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteByFilterDialogOpen(false)} disabled={deleteByFiltering}>
            取消
          </Button>
          <Button onClick={confirmDeleteByFilter} color='error' disabled={deleteByFiltering}>
            {deleteByFiltering ? '删除中…' : '确定删除'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
