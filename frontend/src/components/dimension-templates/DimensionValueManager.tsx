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
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Switch,
  FormControlLabel,
  Alert,
  CircularProgress,
  Tooltip,
  Grid,
  Menu,
  MenuItem as MenuItemComponent,
  ListItemIcon,
  ListItemText,
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  MoreVert as MoreVertIcon,
  Check as CheckIcon,
  Close as CloseIcon,
  Warning as WarningIcon,
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

interface DimensionValueManagerProps {
  template: DimensionTemplate;
  onSubmit: (values: DimensionValue[]) => Promise<void>;
  onClose: () => void;
  loading: boolean;
}

export default function DimensionValueManager({
  template,
  onSubmit,
  onClose,
  loading,
}: DimensionValueManagerProps) {
  const [values, setValues] = useState<DimensionValue[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [editingValue, setEditingValue] = useState<DimensionValue | null>(null);
  const [formData, setFormData] = useState({
    valueCode: '',
    valueName: '',
    valueType: 'normal' as 'normal' | 'default' | 'not_applicable',
    isDefault: false,
    sortOrder: 0,
    isActive: true,
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [selectedValue, setSelectedValue] = useState<DimensionValue | null>(
    null
  );
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setValues(template.dimensionValues || []);
  }, [template]);

  const handleAddValue = () => {
    setEditingValue(null);
    setFormData({
      valueCode: '',
      valueName: '',
      valueType: 'normal',
      isDefault: false,
      sortOrder: values.length,
      isActive: true,
    });
    setErrors({});
    setShowForm(true);
  };

  const handleEditValue = (value: DimensionValue) => {
    setEditingValue(value);
    setFormData({
      valueCode: value.valueCode,
      valueName: value.valueName,
      valueType: value.valueType,
      isDefault: value.isDefault,
      sortOrder: value.sortOrder,
      isActive: value.isActive,
    });
    setErrors({});
    setShowForm(true);
  };

  const handleFormClose = () => {
    setShowForm(false);
    setEditingValue(null);
    setFormData({
      valueCode: '',
      valueName: '',
      valueType: 'normal',
      isDefault: false,
      sortOrder: 0,
      isActive: true,
    });
    setErrors({});
  };

  const handleFormSubmit = () => {
    if (!validateForm()) {
      return;
    }

    const newValue: DimensionValue = {
      id: editingValue?.id || `temp_${Date.now()}`,
      valueCode: formData.valueCode,
      valueName: formData.valueName,
      valueType: formData.valueType,
      isDefault: formData.isDefault,
      reviewStatus: 'approved',
      sortOrder: formData.sortOrder,
      isActive: formData.isActive,
      createdAt: editingValue?.createdAt || new Date().toISOString(),
    };

    if (editingValue) {
      setValues(prev =>
        prev.map(v => (v.id === editingValue.id ? newValue : v))
      );
    } else {
      setValues(prev => [...prev, newValue]);
    }

    handleFormClose();
  };

  const handleDeleteValue = (value: DimensionValue) => {
    setValues(prev => prev.filter(v => v.id !== value.id));
    handleMenuClose();
  };

  const handleMenuOpen = (
    event: React.MouseEvent<HTMLElement>,
    value: DimensionValue
  ) => {
    setAnchorEl(event.currentTarget);
    setSelectedValue(value);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
    setSelectedValue(null);
  };

  const validateForm = () => {
    const newErrors: Record<string, string> = {};

    if (!formData.valueCode.trim()) {
      newErrors.valueCode = '值编码不能为空';
    } else if (!/^[a-zA-Z][a-zA-Z0-9_]*$/.test(formData.valueCode)) {
      newErrors.valueCode =
        '值编码只能包含字母、数字和下划线，且必须以字母开头';
    }

    if (!formData.valueName.trim()) {
      newErrors.valueName = '值名称不能为空';
    }

    if (formData.sortOrder < 0) {
      newErrors.sortOrder = '排序值不能为负数';
    }

    // 检查编码是否重复
    const existingValue = values.find(
      v => v.valueCode === formData.valueCode && v.id !== editingValue?.id
    );
    if (existingValue) {
      newErrors.valueCode = '值编码已存在';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSave = async () => {
    try {
      await onSubmit(values);
    } catch (error) {
      setError(error instanceof Error ? error.message : '保存失败');
    }
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

  const getReviewStatusIcon = (status: string) => {
    switch (status) {
      case 'approved':
        return <CheckIcon color='success' fontSize='small' />;
      case 'rejected':
        return <CloseIcon color='error' fontSize='small' />;
      case 'pending':
        return <WarningIcon color='warning' fontSize='small' />;
      default:
        return null;
    }
  };

  return (
    <Box>
      {/* 标题 */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          mb: 2,
        }}
      >
        <Typography variant='h6'>
          管理维度值 - {template.dimensionName}
        </Typography>
        <Button
          variant='contained'
          startIcon={<AddIcon />}
          onClick={handleAddValue}
          disabled={loading}
        >
          添加维度值
        </Button>
      </Box>

      {/* 错误提示 */}
      {error && (
        <Alert severity='error' sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* 维度值列表 */}
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>值编码</TableCell>
              <TableCell>值名称</TableCell>
              <TableCell>类型</TableCell>
              <TableCell>默认值</TableCell>
              <TableCell>状态</TableCell>
              <TableCell>审核状态</TableCell>
              <TableCell>排序</TableCell>
              <TableCell align='right'>操作</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {values.map(value => (
              <TableRow key={value.id} hover>
                <TableCell>
                  <Typography variant='body2' fontWeight='medium'>
                    {value.valueCode}
                  </Typography>
                </TableCell>
                <TableCell>
                  <Typography variant='body2'>{value.valueName}</Typography>
                </TableCell>
                <TableCell>
                  <Chip
                    label={getValueTypeLabel(value.valueType)}
                    color={getValueTypeColor(value.valueType)}
                    size='small'
                  />
                </TableCell>
                <TableCell>
                  {value.isDefault ? (
                    <Chip label='是' color='success' size='small' />
                  ) : (
                    <Typography variant='body2' color='text.secondary'>
                      否
                    </Typography>
                  )}
                </TableCell>
                <TableCell>
                  <Chip
                    label={value.isActive ? '启用' : '禁用'}
                    color={value.isActive ? 'success' : 'default'}
                    size='small'
                  />
                </TableCell>
                <TableCell>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    {getReviewStatusIcon(value.reviewStatus)}
                    <Typography variant='body2'>
                      {value.reviewStatus === 'approved'
                        ? '已审核'
                        : value.reviewStatus === 'rejected'
                          ? '已拒绝'
                          : '待审核'}
                    </Typography>
                  </Box>
                </TableCell>
                <TableCell>
                  <Typography variant='body2'>{value.sortOrder}</Typography>
                </TableCell>
                <TableCell align='right'>
                  <Tooltip title='更多操作'>
                    <IconButton
                      size='small'
                      onClick={e => handleMenuOpen(e, value)}
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

      {/* 空状态 */}
      {values.length === 0 && (
        <Box sx={{ textAlign: 'center', py: 4 }}>
          <Typography variant='body2' color='text.secondary'>
            暂无维度值，点击"添加维度值"开始创建
          </Typography>
        </Box>
      )}

      {/* 操作菜单 */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleMenuClose}
      >
        <MenuItemComponent
          onClick={() => {
            if (selectedValue) {
              handleEditValue(selectedValue);
            }
            handleMenuClose();
          }}
        >
          <ListItemIcon>
            <EditIcon fontSize='small' />
          </ListItemIcon>
          <ListItemText>编辑</ListItemText>
        </MenuItemComponent>
        <MenuItemComponent
          onClick={() => {
            if (selectedValue) {
              handleDeleteValue(selectedValue);
            }
          }}
        >
          <ListItemIcon>
            <DeleteIcon fontSize='small' />
          </ListItemIcon>
          <ListItemText>删除</ListItemText>
        </MenuItemComponent>
      </Menu>

      {/* 维度值表单对话框 */}
      <Dialog open={showForm} onClose={handleFormClose} maxWidth='sm' fullWidth>
        <DialogTitle>{editingValue ? '编辑维度值' : '添加维度值'}</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 1 }}>
            <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
              <Box sx={{ width: { xs: "100%", sm: "50%" } }}>
                <TextField
                  fullWidth
                  label='值编码'
                  value={formData.valueCode}
                  onChange={e =>
                    setFormData(prev => ({
                      ...prev,
                      valueCode: e.target.value,
                    }))
                  }
                  error={Boolean(errors.valueCode)}
                  helperText={
                    errors.valueCode || '用于系统内部识别，如：red, S'
                  }
                  required
                />
              </Box>

              <Box sx={{ width: { xs: "100%", sm: "50%" } }}>
                <TextField
                  fullWidth
                  label='值名称'
                  value={formData.valueName}
                  onChange={e =>
                    setFormData(prev => ({
                      ...prev,
                      valueName: e.target.value,
                    }))
                  }
                  error={Boolean(errors.valueName)}
                  helperText={
                    errors.valueName || '显示给用户的名称，如：红色, 小号'
                  }
                  required
                />
              </Box>

              <Box sx={{ width: { xs: "100%", sm: "50%" } }}>
                <FormControl fullWidth>
                  <InputLabel>值类型</InputLabel>
                  <Select
                    value={formData.valueType}
                    label='值类型'
                    onChange={e =>
                      setFormData(prev => ({
                        ...prev,
                        valueType: e.target.value as any,
                      }))
                    }
                  >
                    <MenuItem value='normal'>普通</MenuItem>
                    <MenuItem value='default'>默认</MenuItem>
                    <MenuItem value='not_applicable'>不适用</MenuItem>
                  </Select>
                </FormControl>
              </Box>

              <Box sx={{ width: { xs: "100%", sm: "50%" } }}>
                <TextField
                  fullWidth
                  label='排序值'
                  type='number'
                  value={formData.sortOrder}
                  onChange={e =>
                    setFormData(prev => ({
                      ...prev,
                      sortOrder: parseInt(e.target.value) || 0,
                    }))
                  }
                  error={Boolean(errors.sortOrder)}
                  helperText={errors.sortOrder || '数值越小排序越靠前'}
                />
              </Box>

              <Box sx={{ width: "100%" }}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={formData.isDefault}
                      onChange={e =>
                        setFormData(prev => ({
                          ...prev,
                          isDefault: e.target.checked,
                        }))
                      }
                    />
                  }
                  label='设为默认值'
                />
              </Box>

              <Box sx={{ width: "100%" }}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={formData.isActive}
                      onChange={e =>
                        setFormData(prev => ({
                          ...prev,
                          isActive: e.target.checked,
                        }))
                      }
                    />
                  }
                  label='启用'
                />
              </Box>
            </Box>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleFormClose} disabled={loading}>
            取消
          </Button>
          <Button
            onClick={handleFormSubmit}
            variant='contained'
            disabled={loading}
          >
            {editingValue ? '更新' : '添加'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* 底部操作按钮 */}
      <Box sx={{ mt: 3, display: 'flex', gap: 2, justifyContent: 'flex-end' }}>
        <Button variant='outlined' onClick={onClose} disabled={loading}>
          取消
        </Button>
        <Button
          variant='contained'
          onClick={handleSave}
          disabled={loading}
          startIcon={loading ? <CircularProgress size={20} /> : <AddIcon />}
        >
          {loading ? '保存中...' : '保存维度值'}
        </Button>
      </Box>
    </Box>
  );
}
