'use client';

import React, { useState, useEffect } from 'react';
import {
  Box,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  FormControlLabel,
  Switch,
  Button,
  Grid,
  Typography,
  Alert,
  CircularProgress,
} from '@mui/material';
import { Save as SaveIcon, Cancel as CancelIcon } from '@mui/icons-material';

interface CategoryFormProps {
  category?: any;
  mode: 'create' | 'edit';
  onSave: (data: any) => void;
  onCancel: () => void;
}

export function CategoryForm({
  category,
  mode,
  onSave,
  onCancel,
}: CategoryFormProps) {
  const [formData, setFormData] = useState({
    name: '',
    code: '',
    description: '',
    isActive: true,
    isRoot: false,
    sortOrder: 0,
  });
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (category && mode === 'edit') {
      setFormData({
        name: category.name || '',
        code: category.code || '',
        description: category.description || '',
        isActive: category.isActive ?? true,
        isRoot: category.isRoot ?? false,
        sortOrder: category.sortOrder || 0,
      });
    }
  }, [category, mode]);

  const handleChange = (field: string, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    // 清除该字段的错误
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: '' }));
    }
  };

  const validateForm = () => {
    const newErrors: Record<string, string> = {};

    if (!formData.name.trim()) {
      newErrors.name = '分类名称不能为空';
    }

    if (!formData.code.trim()) {
      newErrors.code = '分类编码不能为空';
    } else if (!/^[a-zA-Z0-9_-]+$/.test(formData.code)) {
      newErrors.code = '分类编码只能包含字母、数字、下划线和连字符';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    setLoading(true);
    try {
      // TODO: 调用 API 保存分类
      await new Promise(resolve => setTimeout(resolve, 1000));
      onSave(formData);
    } catch (error) {
      console.error('Save category error:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box component='form' onSubmit={handleSubmit} sx={{ mt: 2 }}>
      <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
        <Box sx={{ width: "100%" }} sm={6}>
          <TextField
            fullWidth
            label='分类名称'
            value={formData.name}
            onChange={e => handleChange('name', e.target.value)}
            error={!!errors.name}
            helperText={errors.name}
            required
          />
        </Box>
        <Box sx={{ width: "100%" }} sm={6}>
          <TextField
            fullWidth
            label='分类编码'
            value={formData.code}
            onChange={e => handleChange('code', e.target.value)}
            error={!!errors.code}
            helperText={
              errors.code ||
              '用于系统内部识别，只能包含字母、数字、下划线和连字符'
            }
            required
          />
        </Box>
        <Box sx={{ width: "100%" }}>
          <TextField
            fullWidth
            label='分类描述'
            value={formData.description}
            onChange={e => handleChange('description', e.target.value)}
            multiline
            rows={3}
            helperText='可选，用于描述该分类的用途和特点'
          />
        </Box>
        <Box sx={{ width: "100%" }} sm={6}>
          <TextField
            fullWidth
            label='排序顺序'
            type='number'
            value={formData.sortOrder}
            onChange={e =>
              handleChange('sortOrder', parseInt(e.target.value) || 0)
            }
            helperText='数字越小，排序越靠前'
          />
        </Box>
        <Box sx={{ width: "100%" }} sm={6}>
          <FormControl fullWidth>
            <InputLabel>父分类</InputLabel>
            <Select
              value=''
              onChange={e => console.log('Parent category:', e.target.value)}
              label='父分类'
              disabled={formData.isRoot}
            >
              <MenuItem value=''>无（根分类）</MenuItem>
              <MenuItem value='1'>服装</MenuItem>
              <MenuItem value='2'>电子产品</MenuItem>
            </Select>
          </FormControl>
        </Box>
        <Box sx={{ width: "100%" }}>
          <Box sx={{ display: 'flex', gap: 2 }}>
            <FormControlLabel
              control={
                <Switch
                  checked={formData.isActive}
                  onChange={e => handleChange('isActive', e.target.checked)}
                />
              }
              label='激活状态'
            />
            <FormControlLabel
              control={
                <Switch
                  checked={formData.isRoot}
                  onChange={e => handleChange('isRoot', e.target.checked)}
                />
              }
              label='根分类'
            />
          </Box>
        </Box>
      </Box>

      {Object.keys(errors).length > 0 && (
        <Alert severity='error' sx={{ mt: 2 }}>
          请检查表单中的错误信息
        </Alert>
      )}

      <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 2, mt: 3 }}>
        <Button
          variant='outlined'
          startIcon={<CancelIcon />}
          onClick={onCancel}
          disabled={loading}
        >
          取消
        </Button>
        <Button
          type='submit'
          variant='contained'
          startIcon={loading ? <CircularProgress size={20} /> : <SaveIcon />}
          disabled={loading}
        >
          {loading ? '保存中...' : '保存'}
        </Button>
      </Box>
    </Box>
  );
}
