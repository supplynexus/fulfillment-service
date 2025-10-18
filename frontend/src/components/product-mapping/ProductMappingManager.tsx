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
} from '@mui/material';
import {
  Search as SearchIcon,
  Refresh as RefreshIcon,
  Visibility as ViewIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Add as AddIcon,
  Storefront as ShopifyIcon,
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
  const [filteredMappings, setFilteredMappings] = useState<ProductMapping[]>(
    []
  );
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

  const fetchMappings = async () => {
    try {
      setLoading(true);
      setError(null);

      frontendLogger.info('🔍 开始获取商品映射数据');

      // 获取商品映射数据
      const response = await frontendApi.get('/api/products/mappings', {
        params: {
          page: 1,
          limit: 100,
        },
      });

      const mappingsData = response.data.mappings || [];
      frontendLogger.info('✅ 商品映射数据获取成功', {
        count: mappingsData.length,
      });

      setMappings(mappingsData);
      setFilteredMappings(mappingsData);
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
    fetchMappings();
  }, []);

  // 过滤映射数据
  useEffect(() => {
    let filtered = mappings;

    if (searchFilters.coreProduct) {
      filtered = filtered.filter(mapping =>
        mapping.core_product_title
          .toLowerCase()
          .includes(searchFilters.coreProduct.toLowerCase())
      );
    }

    if (searchFilters.externalSystem) {
      filtered = filtered.filter(mapping =>
        mapping.external_system_name
          .toLowerCase()
          .includes(searchFilters.externalSystem.toLowerCase())
      );
    }

    if (searchFilters.syncStatus) {
      filtered = filtered.filter(
        mapping => mapping.sync_status === searchFilters.syncStatus
      );
    }

    if (searchFilters.mappingType) {
      filtered = filtered.filter(
        mapping => mapping.mapping_type === searchFilters.mappingType
      );
    }

    setFilteredMappings(filtered);
  }, [mappings, searchFilters]);

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

  const handleClearFilters = () => {
    setSearchFilters({
      coreProduct: '',
      externalSystem: '',
      syncStatus: '',
      mappingType: '',
    });
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

      // 刷新数据
      await fetchMappings();
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
            onClick={fetchMappings}
            disabled={loading}
          >
            刷新数据
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
              <TextField
                fullWidth
                label='外部系统'
                value={searchFilters.externalSystem}
                onChange={e =>
                  handleSearchChange('externalSystem', e.target.value)
                }
                placeholder='输入外部系统名称'
                size='small'
              />
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
                  onClick={() => {}} // 过滤逻辑在useEffect中处理
                  size='small'
                >
                  搜索
                </Button>
                <Button
                  variant='text'
                  onClick={handleClearFilters}
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
              映射列表 ({filteredMappings.length} 条)
            </Typography>
          </Box>

          <TableContainer component={Paper} variant='outlined'>
            <Table>
              <TableHead>
                <TableRow>
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
                {filteredMappings.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={9} align='center'>
                      <Typography variant='body2' color='text.secondary'>
                        暂无映射记录
                      </Typography>
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredMappings.map(mapping => (
                    <TableRow key={mapping.id} hover>
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
    </Box>
  );
}
