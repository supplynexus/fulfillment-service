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
  Alert,
  CircularProgress,
} from '@mui/material';
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  Link as LinkIcon,
  Check as CheckIcon,
  Close as CloseIcon,
} from '@mui/icons-material';

interface CategoryRelation {
  id: string;
  parentCategory: {
    id: string;
    name: string;
    code: string;
  };
  childCategory: {
    id: string;
    name: string;
    code: string;
  };
  relationType: 'parent_child' | 'related';
  sortOrder: number;
  createdAt: string;
}

interface CategoryRelationManagerProps {
  category: any;
  onSave: (relations: CategoryRelation[]) => void;
  onCancel: () => void;
}

export function CategoryRelationManager({
  category,
  onSave,
  onCancel,
}: CategoryRelationManagerProps) {
  const [relations, setRelations] = useState<CategoryRelation[]>([]);
  const [loading, setLoading] = useState(false);
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [newRelation, setNewRelation] = useState({
    targetCategoryId: '',
    relationType: 'parent_child' as 'parent_child' | 'related',
    sortOrder: 0,
  });
  const [availableCategories, setAvailableCategories] = useState<any[]>([]);

  useEffect(() => {
    if (category) {
      loadRelations();
      loadAvailableCategories();
    }
  }, [category]);

  const loadRelations = async () => {
    setLoading(true);
    try {
      // TODO: 调用 API 获取分类关系
      const mockRelations: CategoryRelation[] = [
        {
          id: '1',
          parentCategory: {
            id: '1',
            name: '服装',
            code: 'clothing',
          },
          childCategory: {
            id: '2',
            name: '男装',
            code: 'mens-clothing',
          },
          relationType: 'parent_child',
          sortOrder: 0,
          createdAt: '2024-01-15T10:00:00Z',
        },
        {
          id: '2',
          parentCategory: {
            id: '1',
            name: '服装',
            code: 'clothing',
          },
          childCategory: {
            id: '5',
            name: '女装',
            code: 'womens-clothing',
          },
          relationType: 'parent_child',
          sortOrder: 1,
          createdAt: '2024-01-15T10:00:00Z',
        },
      ];
      setRelations(mockRelations);
    } catch (error) {
      console.error('Load relations error:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadAvailableCategories = async () => {
    try {
      // TODO: 调用 API 获取可用分类
      const mockCategories = [
        { id: '1', name: '服装', code: 'clothing' },
        { id: '7', name: '电子产品', code: 'electronics' },
        { id: '10', name: '配饰', code: 'accessories' },
      ];
      setAvailableCategories(mockCategories);
    } catch (error) {
      console.error('Load categories error:', error);
    }
  };

  const handleAddRelation = () => {
    if (!newRelation.targetCategoryId) return;

    const targetCategory = availableCategories.find(
      c => c.id === newRelation.targetCategoryId
    );
    if (!targetCategory) return;

    const relation: CategoryRelation = {
      id: Date.now().toString(),
      parentCategory: category,
      childCategory: targetCategory,
      relationType: newRelation.relationType,
      sortOrder: newRelation.sortOrder,
      createdAt: new Date().toISOString(),
    };

    setRelations(prev => [...prev, relation]);
    setNewRelation({
      targetCategoryId: '',
      relationType: 'parent_child',
      sortOrder: 0,
    });
    setShowAddDialog(false);
  };

  const handleRemoveRelation = (relationId: string) => {
    setRelations(prev => prev.filter(r => r.id !== relationId));
  };

  const handleSave = () => {
    onSave(relations);
  };

  const getRelationTypeLabel = (type: string) => {
    switch (type) {
      case 'parent_child':
        return '父子关系';
      case 'related':
        return '关联关系';
      default:
        return type;
    }
  };

  const getRelationTypeColor = (type: string) => {
    switch (type) {
      case 'parent_child':
        return 'primary';
      case 'related':
        return 'secondary';
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
        <Typography variant='h6'>分类关系管理 - {category?.name}</Typography>
        <Button
          variant='contained'
          startIcon={<AddIcon />}
          onClick={() => setShowAddDialog(true)}
        >
          添加关系
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
                <TableCell>关系类型</TableCell>
                <TableCell>目标分类</TableCell>
                <TableCell>排序</TableCell>
                <TableCell>创建时间</TableCell>
                <TableCell align='right'>操作</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {relations.map(relation => (
                <TableRow key={relation.id}>
                  <TableCell>
                    <Chip
                      label={getRelationTypeLabel(relation.relationType)}
                      color={getRelationTypeColor(relation.relationType) as any}
                      size='small'
                    />
                  </TableCell>
                  <TableCell>
                    <Box>
                      <Typography variant='body2' sx={{ fontWeight: 600 }}>
                        {relation.childCategory.name}
                      </Typography>
                      <Typography variant='caption' color='text.secondary'>
                        {relation.childCategory.code}
                      </Typography>
                    </Box>
                  </TableCell>
                  <TableCell>{relation.sortOrder}</TableCell>
                  <TableCell>
                    {new Date(relation.createdAt).toLocaleDateString()}
                  </TableCell>
                  <TableCell align='right'>
                    <Tooltip title='删除关系'>
                      <IconButton
                        size='small'
                        onClick={() => handleRemoveRelation(relation.id)}
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

      {relations.length === 0 && !loading && (
        <Alert severity='info' sx={{ mt: 2 }}>
          该分类暂无关系数据
        </Alert>
      )}

      {/* 添加关系对话框 */}
      <Dialog
        open={showAddDialog}
        onClose={() => setShowAddDialog(false)}
        maxWidth='sm'
        fullWidth
      >
        <DialogTitle>添加分类关系</DialogTitle>
        <DialogContent>
          <Box sx={{ mt: 2 }}>
            <FormControl fullWidth sx={{ mb: 2 }}>
              <InputLabel>目标分类</InputLabel>
              <Select
                value={newRelation.targetCategoryId}
                onChange={e =>
                  setNewRelation(prev => ({
                    ...prev,
                    targetCategoryId: e.target.value,
                  }))
                }
                label='目标分类'
              >
                {availableCategories.map(cat => (
                  <MenuItem key={cat.id} value={cat.id}>
                    {cat.name} ({cat.code})
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <FormControl fullWidth sx={{ mb: 2 }}>
              <InputLabel>关系类型</InputLabel>
              <Select
                value={newRelation.relationType}
                onChange={e =>
                  setNewRelation(prev => ({
                    ...prev,
                    relationType: e.target.value as any,
                  }))
                }
                label='关系类型'
              >
                <MenuItem value='parent_child'>父子关系</MenuItem>
                <MenuItem value='related'>关联关系</MenuItem>
              </Select>
            </FormControl>
            <TextField
              fullWidth
              label='排序顺序'
              type='number'
              value={newRelation.sortOrder}
              onChange={e =>
                setNewRelation(prev => ({
                  ...prev,
                  sortOrder: parseInt(e.target.value) || 0,
                }))
              }
              helperText='数字越小，排序越靠前'
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowAddDialog(false)}>取消</Button>
          <Button
            onClick={handleAddRelation}
            variant='contained'
            disabled={!newRelation.targetCategoryId}
          >
            添加
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
