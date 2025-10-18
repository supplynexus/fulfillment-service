'use client';

import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  FormControlLabel,
  Switch,
  Alert,
  CircularProgress,
  Grid,
} from '@mui/material';
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  Check as CheckIcon,
  Close as CloseIcon,
  Settings as SettingsIcon,
} from '@mui/icons-material';

interface CategoryDimension {
  id: string;
  dimensionTemplate: {
    id: string;
    name: string;
    code: string;
    type: string;
  };
  sourceType: 'own' | 'inherited' | 'overridden';
  sourceCategory?: {
    id: string;
    name: string;
  };
  isRequired: boolean;
  isOverridable: boolean;
  sortOrder: number;
  isActive: boolean;
}

interface CategoryDimensionManagerProps {
  category: any;
  onSave: (dimensions: CategoryDimension[]) => void;
  onCancel: () => void;
}

export function CategoryDimensionManager({
  category,
  onSave,
  onCancel,
}: CategoryDimensionManagerProps) {
  const [dimensions, setDimensions] = useState<CategoryDimension[]>([]);
  const [loading, setLoading] = useState(false);
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [editingDimension, setEditingDimension] =
    useState<CategoryDimension | null>(null);
  const [newDimension, setNewDimension] = useState({
    dimensionTemplateId: '',
    isRequired: true,
    isOverridable: true,
    sortOrder: 0,
  });
  const [availableTemplates, setAvailableTemplates] = useState<any[]>([]);

  useEffect(() => {
    if (category) {
      loadDimensions();
      loadAvailableTemplates();
    }
  }, [category]);

  const loadDimensions = async () => {
    setLoading(true);
    try {
      // TODO: 调用 API 获取分类维度
      const mockDimensions: CategoryDimension[] = [
        {
          id: '1',
          dimensionTemplate: {
            id: '1',
            name: '颜色',
            code: 'color',
            type: 'select',
          },
          sourceType: 'own',
          isRequired: true,
          isOverridable: true,
          sortOrder: 0,
          isActive: true,
        },
        {
          id: '2',
          dimensionTemplate: {
            id: '2',
            name: '尺码',
            code: 'size',
            type: 'select',
          },
          sourceType: 'own',
          isRequired: true,
          isOverridable: true,
          sortOrder: 1,
          isActive: true,
        },
        {
          id: '3',
          dimensionTemplate: {
            id: '3',
            name: '材质',
            code: 'material',
            type: 'select',
          },
          sourceType: 'inherited',
          sourceCategory: {
            id: '1',
            name: '服装',
          },
          isRequired: false,
          isOverridable: true,
          sortOrder: 2,
          isActive: true,
        },
      ];
      setDimensions(mockDimensions);
    } catch (error) {
      console.error('Load dimensions error:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadAvailableTemplates = async () => {
    try {
      // TODO: 调用 API 获取可用维度模板
      const mockTemplates = [
        { id: '1', name: '颜色', code: 'color', type: 'select' },
        { id: '2', name: '尺码', code: 'size', type: 'select' },
        { id: '3', name: '材质', code: 'material', type: 'select' },
        { id: '4', name: '品牌', code: 'brand', type: 'select' },
        { id: '5', name: '型号', code: 'model', type: 'text' },
      ];
      setAvailableTemplates(mockTemplates);
    } catch (error) {
      console.error('Load templates error:', error);
    }
  };

  const handleAddDimension = () => {
    if (!newDimension.dimensionTemplateId) return;

    const template = availableTemplates.find(
      t => t.id === newDimension.dimensionTemplateId
    );
    if (!template) return;

    const dimension: CategoryDimension = {
      id: Date.now().toString(),
      dimensionTemplate: template,
      sourceType: 'own',
      isRequired: newDimension.isRequired,
      isOverridable: newDimension.isOverridable,
      sortOrder: newDimension.sortOrder,
      isActive: true,
    };

    setDimensions(prev => [...prev, dimension]);
    setNewDimension({
      dimensionTemplateId: '',
      isRequired: true,
      isOverridable: true,
      sortOrder: 0,
    });
    setShowAddDialog(false);
  };

  const handleEditDimension = (dimension: CategoryDimension) => {
    setEditingDimension(dimension);
    setShowAddDialog(true);
  };

  const handleUpdateDimension = () => {
    if (!editingDimension) return;

    setDimensions(prev =>
      prev.map(d =>
        d.id === editingDimension.id ? { ...d, ...newDimension } : d
      )
    );
    setEditingDimension(null);
    setShowAddDialog(false);
  };

  const handleRemoveDimension = (dimensionId: string) => {
    setDimensions(prev => prev.filter(d => d.id !== dimensionId));
  };

  const handleSave = () => {
    onSave(dimensions);
  };

  const getSourceTypeLabel = (type: string) => {
    switch (type) {
      case 'own':
        return '自有';
      case 'inherited':
        return '继承';
      case 'overridden':
        return '覆盖';
      default:
        return type;
    }
  };

  const getSourceTypeColor = (type: string) => {
    switch (type) {
      case 'own':
        return 'primary';
      case 'inherited':
        return 'success';
      case 'overridden':
        return 'warning';
      default:
        return 'default';
    }
  };

  return (
    <Box>
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          mb: 3,
        }}
      >
        <Typography variant='h6'>分类维度管理 - {category?.name}</Typography>
        <Button
          variant='contained'
          startIcon={<AddIcon />}
          onClick={() => {
            setEditingDimension(null);
            setShowAddDialog(true);
          }}
        >
          添加维度
        </Button>
      </Box>

      {loading ? (
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
      ) : (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>维度名称</TableCell>
                <TableCell>来源类型</TableCell>
                <TableCell>是否必填</TableCell>
                <TableCell>可覆盖</TableCell>
                <TableCell>排序</TableCell>
                <TableCell>状态</TableCell>
                <TableCell align='right'>操作</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {dimensions.map(dimension => (
                <TableRow key={dimension.id}>
                  <TableCell>
                    <Box>
                      <Typography variant='body2' sx={{ fontWeight: 600 }}>
                        {dimension.dimensionTemplate.name}
                      </Typography>
                      <Typography variant='caption' color='text.secondary'>
                        {dimension.dimensionTemplate.code} (
                        {dimension.dimensionTemplate.type})
                      </Typography>
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={getSourceTypeLabel(dimension.sourceType)}
                      color={getSourceTypeColor(dimension.sourceType) as any}
                      size='small'
                    />
                    {dimension.sourceCategory && (
                      <Typography
                        variant='caption'
                        display='block'
                        color='text.secondary'
                      >
                        来自: {dimension.sourceCategory.name}
                      </Typography>
                    )}
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={dimension.isRequired ? '必填' : '可选'}
                      color={dimension.isRequired ? 'error' : 'default'}
                      size='small'
                    />
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={dimension.isOverridable ? '是' : '否'}
                      color={dimension.isOverridable ? 'success' : 'default'}
                      size='small'
                    />
                  </TableCell>
                  <TableCell>{dimension.sortOrder}</TableCell>
                  <TableCell>
                    <Chip
                      label={dimension.isActive ? '激活' : '停用'}
                      color={dimension.isActive ? 'success' : 'error'}
                      size='small'
                    />
                  </TableCell>
                  <TableCell align='right'>
                    <Tooltip title='编辑维度'>
                      <IconButton
                        size='small'
                        onClick={() => handleEditDimension(dimension)}
                      >
                        <EditIcon />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title='删除维度'>
                      <IconButton
                        size='small'
                        onClick={() => handleRemoveDimension(dimension.id)}
                        color='error'
                      >
                        <DeleteIcon />
                      </IconButton>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {dimensions.length === 0 && !loading && (
        <Alert severity='info' sx={{ mt: 2 }}>
          该分类暂无维度数据
        </Alert>
      )}

      {/* 添加/编辑维度对话框 */}
      <Dialog
        open={showAddDialog}
        onClose={() => setShowAddDialog(false)}
        maxWidth='sm'
        fullWidth
      >
        <DialogTitle>{editingDimension ? '编辑维度' : '添加维度'}</DialogTitle>
        <DialogContent>
          <Box sx={{ mt: 2 }}>
            <FormControl fullWidth sx={{ mb: 2 }}>
              <InputLabel>维度模板</InputLabel>
              <Select
                value={newDimension.dimensionTemplateId}
                onChange={e =>
                  setNewDimension(prev => ({
                    ...prev,
                    dimensionTemplateId: e.target.value,
                  }))
                }
                label='维度模板'
                disabled={!!editingDimension}
              >
                {availableTemplates.map(template => (
                  <MenuItem key={template.id} value={template.id}>
                    {template.name} ({template.code}) - {template.type}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
              <Box sx={{ width: "50%" }}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={newDimension.isRequired}
                      onChange={e =>
                        setNewDimension(prev => ({
                          ...prev,
                          isRequired: e.target.checked,
                        }))
                      }
                    />
                  }
                  label='是否必填'
                />
              </Box>
              <Box sx={{ width: "50%" }}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={newDimension.isOverridable}
                      onChange={e =>
                        setNewDimension(prev => ({
                          ...prev,
                          isOverridable: e.target.checked,
                        }))
                      }
                    />
                  }
                  label='可覆盖'
                />
              </Box>
            </Box>
            <TextField
              fullWidth
              label='排序顺序'
              type='number'
              value={newDimension.sortOrder}
              onChange={e =>
                setNewDimension(prev => ({
                  ...prev,
                  sortOrder: parseInt(e.target.value) || 0,
                }))
              }
              helperText='数字越小，排序越靠前'
              sx={{ mt: 2 }}
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowAddDialog(false)}>取消</Button>
          <Button
            onClick={
              editingDimension ? handleUpdateDimension : handleAddDimension
            }
            variant='contained'
            disabled={!newDimension.dimensionTemplateId}
          >
            {editingDimension ? '更新' : '添加'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* 底部操作按钮 */}
      <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 2, mt: 3 }}>
        <Button variant='outlined' startIcon={<CloseIcon />} onClick={onCancel}>
          取消
        </Button>
        <Button
          variant='contained'
          startIcon={<CheckIcon />}
          onClick={handleSave}
        >
          保存
        </Button>
      </Box>
    </Box>
  );
}
