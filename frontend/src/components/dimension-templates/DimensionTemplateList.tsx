'use client';

import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  Chip,
  Tooltip,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
  CircularProgress,
  Alert,
  TextField,
  InputAdornment,
  FormControl,
  InputLabel,
  Select,
  MenuItem as SelectMenuItem,
  Checkbox,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
} from '@mui/material';
import {
  MoreVert as MoreVertIcon,
  Edit as EditIcon,
  Settings as SettingsIcon,
  Search as SearchIcon,
  FilterList as FilterIcon,
  Visibility as VisibilityIcon,
  VisibilityOff as VisibilityOffIcon,
  Refresh as RefreshIcon,
  Delete as DeleteIcon,
} from '@mui/icons-material';

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

interface DimensionTemplateListProps {
  onEditTemplate: (template: DimensionTemplate) => void;
  onManageValues: (template: DimensionTemplate) => void;
  loading: boolean;
}

export default function DimensionTemplateList({
  onEditTemplate,
  onManageValues,
  loading: externalLoading,
}: DimensionTemplateListProps) {
  const [templates, setTemplates] = useState<DimensionTemplate[]>([]);
  const [filteredTemplates, setFilteredTemplates] = useState<
    DimensionTemplate[]
  >([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [loading, setLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [selectedTemplate, setSelectedTemplate] =
    useState<DimensionTemplate | null>(null);
  const [error, setError] = useState<string | null>(null);

  // 批量删除相关状态
  const [selectedTemplates, setSelectedTemplates] = useState<Set<string>>(
    new Set()
  );
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [bulkDeleting, setBulkDeleting] = useState(false);

  // 模拟数据
  const mockTemplates: DimensionTemplate[] = [
    {
      id: '1',
      dimensionCode: 'color',
      dimensionName: '颜色',
      dimensionType: 'select',
      description: '产品颜色维度',
      sortOrder: 1,
      isActive: true,
      createdAt: '2024-01-01T00:00:00Z',
      updatedAt: '2024-01-01T00:00:00Z',
      dimensionValues: [
        {
          id: '1',
          valueCode: 'red',
          valueName: '红色',
          valueType: 'normal',
          isDefault: false,
          reviewStatus: 'approved',
          sortOrder: 1,
          isActive: true,
          createdAt: '2024-01-01T00:00:00Z',
        },
        {
          id: '2',
          valueCode: 'blue',
          valueName: '蓝色',
          valueType: 'normal',
          isDefault: false,
          reviewStatus: 'approved',
          sortOrder: 2,
          isActive: true,
          createdAt: '2024-01-01T00:00:00Z',
        },
        {
          id: '3',
          valueCode: 'green',
          valueName: '绿色',
          valueType: 'normal',
          isDefault: false,
          reviewStatus: 'approved',
          sortOrder: 3,
          isActive: true,
          createdAt: '2024-01-01T00:00:00Z',
        },
      ],
    },
    {
      id: '2',
      dimensionCode: 'size',
      dimensionName: '尺码',
      dimensionType: 'select',
      description: '产品尺码维度',
      sortOrder: 2,
      isActive: true,
      createdAt: '2024-01-01T00:00:00Z',
      updatedAt: '2024-01-01T00:00:00Z',
      dimensionValues: [
        {
          id: '4',
          valueCode: 'S',
          valueName: '小号',
          valueType: 'normal',
          isDefault: false,
          reviewStatus: 'approved',
          sortOrder: 1,
          isActive: true,
          createdAt: '2024-01-01T00:00:00Z',
        },
        {
          id: '5',
          valueCode: 'M',
          valueName: '中号',
          valueType: 'normal',
          isDefault: false,
          reviewStatus: 'approved',
          sortOrder: 2,
          isActive: true,
          createdAt: '2024-01-01T00:00:00Z',
        },
        {
          id: '6',
          valueCode: 'L',
          valueName: '大号',
          valueType: 'normal',
          isDefault: false,
          reviewStatus: 'approved',
          sortOrder: 3,
          isActive: true,
          createdAt: '2024-01-01T00:00:00Z',
        },
      ],
    },
    {
      id: '3',
      dimensionCode: 'material',
      dimensionName: '材质',
      dimensionType: 'select',
      description: '产品材质维度',
      sortOrder: 3,
      isActive: true,
      createdAt: '2024-01-01T00:00:00Z',
      updatedAt: '2024-01-01T00:00:00Z',
      dimensionValues: [
        {
          id: '7',
          valueCode: 'cotton',
          valueName: '棉质',
          valueType: 'normal',
          isDefault: false,
          reviewStatus: 'approved',
          sortOrder: 1,
          isActive: true,
          createdAt: '2024-01-01T00:00:00Z',
        },
        {
          id: '8',
          valueCode: 'polyester',
          valueName: '聚酯纤维',
          valueType: 'normal',
          isDefault: false,
          reviewStatus: 'approved',
          sortOrder: 2,
          isActive: true,
          createdAt: '2024-01-01T00:00:00Z',
        },
      ],
    },
  ];

  useEffect(() => {
    loadTemplates();
  }, []);

  const loadTemplates = async () => {
    try {
      setLoading(true);

      // 获取 JWT token
      const tokenManager = (await import('@/lib/token-manager')).tokenManager;
      const accessToken = await tokenManager.getValidAccessToken();

      console.log('🔍 前端组件调用API:', {
        hasToken: !!accessToken,
        tokenLength: accessToken?.length,
      });

      const response = await fetch('/api/dimension-templates', {
        headers: {
          Authorization: `Bearer ${accessToken}`,
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        const data = await response.json();
        // 转换后端返回的 snake_case 字段名为前端期望的 camelCase 格式
        const transformedData = data.map((template: any) => ({
          id: template.id.toString(),
          dimensionCode: template.dimension_code,
          dimensionName: template.dimension_name,
          dimensionType: template.dimension_type,
          description: template.description,
          sortOrder: template.sort_order,
          isActive: template.is_active,
          createdAt: template.created_at,
          updatedAt: template.updated_at,
          dimensionValues: template.dimension_values || [],
        }));
        setTemplates(transformedData);
        setFilteredTemplates(transformedData);
      } else {
        console.error('加载维度模板失败');
        // 如果 API 失败，使用模拟数据
        setTemplates(mockTemplates);
        setFilteredTemplates(mockTemplates);
      }
    } catch (error) {
      console.error('加载维度模板异常:', error);
      // 如果 API 失败，使用模拟数据
      setTemplates(mockTemplates);
      setFilteredTemplates(mockTemplates);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // 应用筛选
    let filtered = templates;

    // 搜索筛选
    if (searchTerm) {
      filtered = filtered.filter(
        template =>
          template.dimensionName
            .toLowerCase()
            .includes(searchTerm.toLowerCase()) ||
          template.dimensionCode
            .toLowerCase()
            .includes(searchTerm.toLowerCase()) ||
          template.description?.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    // 类型筛选
    if (typeFilter !== 'all') {
      filtered = filtered.filter(
        template => template.dimensionType === typeFilter
      );
    }

    // 状态筛选
    if (statusFilter !== 'all') {
      filtered = filtered.filter(template =>
        statusFilter === 'active' ? template.isActive : !template.isActive
      );
    }

    setFilteredTemplates(filtered);
  }, [templates, searchTerm, typeFilter, statusFilter]);

  const handleMenuOpen = (
    event: React.MouseEvent<HTMLElement>,
    template: DimensionTemplate
  ) => {
    setAnchorEl(event.currentTarget);
    setSelectedTemplate(template);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
    setSelectedTemplate(null);
  };

  const handleEdit = () => {
    if (selectedTemplate) {
      onEditTemplate(selectedTemplate);
    }
    handleMenuClose();
  };

  const handleManageValues = (template?: DimensionTemplate) => {
    const targetTemplate = template || selectedTemplate;
    if (targetTemplate) {
      onManageValues(targetTemplate);
    }
    handleMenuClose();
  };

  // 刷新功能
  const handleRefresh = () => {
    setLoading(true);
    // 这里可以调用 API 重新获取数据
    setTimeout(() => {
      setLoading(false);
    }, 1000);
  };

  // 选择模板
  const handleSelectTemplate = (templateId: string, checked: boolean) => {
    setSelectedTemplates(prev => {
      const newSet = new Set(prev);
      if (checked) {
        newSet.add(templateId);
      } else {
        newSet.delete(templateId);
      }
      return newSet;
    });
  };

  // 全选/取消全选
  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedTemplates(new Set(filteredTemplates.map(t => t.id)));
    } else {
      setSelectedTemplates(new Set());
    }
  };

  // 批量删除确认
  const handleConfirmDelete = () => {
    if (selectedTemplates.size === 0) {
      setError('请先选择要删除的维度模板');
      return;
    }
    setDeleteDialogOpen(true);
  };

  // 执行批量删除
  const handleBulkDelete = async () => {
    if (selectedTemplates.size === 0) {
      setError('请先选择要删除的维度模板');
      return;
    }

    setBulkDeleting(true);

    try {
      console.log('批量删除维度模板:', Array.from(selectedTemplates));

      // 获取 JWT token
      const tokenManager = (await import('@/lib/token-manager')).tokenManager;
      const accessToken = await tokenManager.getValidAccessToken();

      // 调用删除 API
      const deletePromises = Array.from(selectedTemplates).map(async (templateId) => {
        const response = await fetch(`/api/dimension-templates/${templateId}`, {
          method: 'DELETE',
          headers: {
            Authorization: `Bearer ${accessToken}`,
            'Content-Type': 'application/json',
          },
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.error || `删除维度模板 ${templateId} 失败`);
        }

        return response.json();
      });

      await Promise.all(deletePromises);

      // 删除成功后更新前端状态
      setTemplates(prev => prev.filter(t => !selectedTemplates.has(t.id)));
      setFilteredTemplates(prev =>
        prev.filter(t => !selectedTemplates.has(t.id))
      );
      setSelectedTemplates(new Set());
      setDeleteDialogOpen(false);
      setBulkDeleting(false);

      console.log('✅ 批量删除成功');
    } catch (error: any) {
      console.error('❌ 批量删除失败:', error);
      setError(`批量删除失败：${error.message || '网络错误'}`);
      setBulkDeleting(false);
    }
  };

  const getTypeLabel = (type: string) => {
    const typeMap: Record<string, string> = {
      select: '选择',
      text: '文本',
      number: '数字',
      boolean: '布尔',
    };
    return typeMap[type] || type;
  };

  const getTypeColor = (type: string) => {
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

  if (loading || externalLoading) {
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

  return (
    <Box>
      {/* 标题 */}
      <Typography variant='h6' sx={{ mb: 2 }}>
        维度模板列表
      </Typography>

      {/* 搜索和筛选 */}
      <Box sx={{ mb: 2, display: 'flex', gap: 2, flexWrap: 'wrap' }}>
        <TextField
          size='small'
          placeholder='搜索维度模板...'
          value={searchTerm}
          onChange={e => setSearchTerm(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position='start'>
                <SearchIcon />
              </InputAdornment>
            ),
          }}
          sx={{ minWidth: 200 }}
        />

        <FormControl size='small' sx={{ minWidth: 120 }}>
          <InputLabel>类型</InputLabel>
          <Select
            value={typeFilter}
            label='类型'
            onChange={e => setTypeFilter(e.target.value)}
          >
            <SelectMenuItem value='all'>全部</SelectMenuItem>
            <SelectMenuItem value='select'>选择</SelectMenuItem>
            <SelectMenuItem value='text'>文本</SelectMenuItem>
            <SelectMenuItem value='number'>数字</SelectMenuItem>
            <SelectMenuItem value='boolean'>布尔</SelectMenuItem>
          </Select>
        </FormControl>

        <FormControl size='small' sx={{ minWidth: 120 }}>
          <InputLabel>状态</InputLabel>
          <Select
            value={statusFilter}
            label='状态'
            onChange={e => setStatusFilter(e.target.value)}
          >
            <SelectMenuItem value='all'>全部</SelectMenuItem>
            <SelectMenuItem value='active'>启用</SelectMenuItem>
            <SelectMenuItem value='inactive'>禁用</SelectMenuItem>
          </Select>
        </FormControl>

        <Button
          variant='outlined'
          startIcon={<RefreshIcon />}
          onClick={handleRefresh}
          disabled={loading || externalLoading}
        >
          刷新
        </Button>
      </Box>

      {/* 批量操作区域 */}
      {selectedTemplates.size > 0 && (
        <Box sx={{ mb: 2, display: 'flex', gap: 1, alignItems: 'center' }}>
          <Button
            variant='contained'
            color='error'
            startIcon={
              bulkDeleting ? <CircularProgress size={16} /> : <DeleteIcon />
            }
            onClick={handleConfirmDelete}
            disabled={bulkDeleting}
          >
            {bulkDeleting
              ? '删除中...'
              : `删除模板 (${selectedTemplates.size})`}
          </Button>
          <Button
            variant='outlined'
            onClick={() => setSelectedTemplates(new Set())}
          >
            取消选择
          </Button>
          <Typography variant='body2' color='text.secondary'>
            已选择 {selectedTemplates.size} 个模板
          </Typography>
        </Box>
      )}

      {/* 错误提示 */}
      {error && (
        <Alert severity='error' sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* 表格 */}
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell padding='checkbox'>
                <Checkbox
                  indeterminate={
                    selectedTemplates.size > 0 &&
                    selectedTemplates.size < filteredTemplates.length
                  }
                  checked={
                    filteredTemplates.length > 0 &&
                    selectedTemplates.size === filteredTemplates.length
                  }
                  onChange={e => handleSelectAll(e.target.checked)}
                />
              </TableCell>
              <TableCell>维度名称</TableCell>
              <TableCell>维度编码</TableCell>
              <TableCell>类型</TableCell>
              <TableCell>描述</TableCell>
              <TableCell>操作</TableCell>
              <TableCell>状态</TableCell>
              <TableCell>创建时间</TableCell>
              <TableCell align='right'>操作</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filteredTemplates.map(template => (
              <TableRow key={template.id} hover>
                <TableCell padding='checkbox'>
                  <Checkbox
                    checked={selectedTemplates.has(template.id)}
                    onChange={e =>
                      handleSelectTemplate(template.id, e.target.checked)
                    }
                  />
                </TableCell>
                <TableCell>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Typography variant='body2' fontWeight='medium'>
                      {template.dimensionName}
                    </Typography>
                    {template.isActive ? (
                      <VisibilityIcon color='success' fontSize='small' />
                    ) : (
                      <VisibilityOffIcon color='disabled' fontSize='small' />
                    )}
                  </Box>
                </TableCell>
                <TableCell>
                  <Typography variant='body2' color='text.secondary'>
                    {template.dimensionCode}
                  </Typography>
                </TableCell>
                <TableCell>
                  <Chip
                    label={getTypeLabel(template.dimensionType)}
                    color={getTypeColor(template.dimensionType)}
                    size='small'
                  />
                </TableCell>
                <TableCell>
                  <Typography variant='body2' color='text.secondary'>
                    {template.description || '-'}
                  </Typography>
                </TableCell>
                <TableCell>
                  <Tooltip title='管理维度值'>
                    <IconButton
                      size='small'
                      onClick={() => handleManageValues(template)}
                    >
                      <SettingsIcon fontSize='small' />
                    </IconButton>
                  </Tooltip>
                </TableCell>
                <TableCell>
                  <Chip
                    label={template.isActive ? '启用' : '禁用'}
                    color={template.isActive ? 'success' : 'default'}
                    size='small'
                  />
                </TableCell>
                <TableCell>
                  <Typography variant='body2' color='text.secondary'>
                    {new Date(template.createdAt).toLocaleDateString()}
                  </Typography>
                </TableCell>
                <TableCell align='right'>
                  <Tooltip title='更多操作'>
                    <IconButton
                      size='small'
                      onClick={e => handleMenuOpen(e, template)}
                    >
                      <MoreVertIcon />
                    </IconButton>
                  </Tooltip>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      {/* 操作菜单 */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleMenuClose}
      >
        <MenuItem onClick={handleEdit}>
          <ListItemIcon>
            <EditIcon fontSize='small' />
          </ListItemIcon>
          <ListItemText>编辑模板</ListItemText>
        </MenuItem>
        <MenuItem onClick={() => handleManageValues()}>
          <ListItemIcon>
            <SettingsIcon fontSize='small' />
          </ListItemIcon>
          <ListItemText>管理维度值</ListItemText>
        </MenuItem>
      </Menu>

      {/* 空状态 */}
      {filteredTemplates.length === 0 && (
        <Box sx={{ textAlign: 'center', py: 4 }}>
          <Typography variant='body2' color='text.secondary'>
            {searchTerm || typeFilter !== 'all' || statusFilter !== 'all'
              ? '没有找到匹配的维度模板'
              : '暂无维度模板'}
          </Typography>
        </Box>
      )}

      {/* 删除确认对话框 */}
      <Dialog
        open={deleteDialogOpen}
        onClose={() => setDeleteDialogOpen(false)}
      >
        <DialogTitle>确认删除维度模板</DialogTitle>
        <DialogContent>
          <Typography variant='body1' gutterBottom>
            您确定要删除选中的 {selectedTemplates.size} 个维度模板吗？
          </Typography>
          <Typography variant='body2' color='text.secondary'>
            此操作不可撤销，删除的维度模板将从数据库中永久移除。
          </Typography>
          <Box sx={{ mt: 2 }}>
            <Typography variant='subtitle2' gutterBottom>
              将要删除的维度模板：
            </Typography>
            <Box sx={{ maxHeight: '200px', overflow: 'auto' }}>
              {Array.from(selectedTemplates).map(templateId => {
                const template = filteredTemplates.find(
                  t => t.id === templateId
                );
                return template ? (
                  <Typography
                    key={templateId}
                    variant='body2'
                    color='text.secondary'
                  >
                    • {template.dimensionName} ({template.dimensionCode})
                  </Typography>
                ) : null;
              })}
            </Box>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)}>取消</Button>
          <Button
            variant='contained'
            color='error'
            startIcon={
              bulkDeleting ? <CircularProgress size={16} /> : <DeleteIcon />
            }
            onClick={handleBulkDelete}
            disabled={bulkDeleting}
          >
            {bulkDeleting ? '删除中...' : '确认删除'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
