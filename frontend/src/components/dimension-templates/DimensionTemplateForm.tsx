'use client';

import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Switch,
  FormControlLabel,
  Button,
  Grid,
  Paper,
  Divider,
  Alert,
  CircularProgress,
} from '@mui/material';
import { Save as SaveIcon, Cancel as CancelIcon } from '@mui/icons-material';

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

interface DimensionTemplateFormProps {
  template?: DimensionTemplate | null;
  onSubmit: (templateData: Partial<DimensionTemplate>) => Promise<void>;
  onClose: () => void;
  loading: boolean;
}

export default function DimensionTemplateForm({
  template,
  onSubmit,
  onClose,
  loading,
}: DimensionTemplateFormProps) {
  const [formData, setFormData] = useState({
    dimensionCode: '',
    dimensionName: '',
    dimensionType: 'select' as 'select' | 'text' | 'number' | 'boolean',
    description: '',
    sortOrder: 0,
    isActive: true,
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  const isEdit = Boolean(template);

  useEffect(() => {
    if (template) {
      setFormData({
        dimensionCode: template.dimensionCode,
        dimensionName: template.dimensionName,
        dimensionType: template.dimensionType,
        description: template.description || '',
        sortOrder: template.sortOrder,
        isActive: template.isActive,
      });
    }
  }, [template]);

  const handleChange = (field: string, value: any) => {
    setFormData(prev => ({
      ...prev,
      [field]: value,
    }));

    // 清除相关错误
    if (errors[field]) {
      setErrors(prev => ({
        ...prev,
        [field]: '',
      }));
    }
  };

  const validateForm = () => {
    const newErrors: Record<string, string> = {};

    if (!formData.dimensionCode.trim()) {
      newErrors.dimensionCode = '维度编码不能为空';
    } else if (!/^[a-zA-Z][a-zA-Z0-9_]*$/.test(formData.dimensionCode)) {
      newErrors.dimensionCode =
        '维度编码只能包含字母、数字和下划线，且必须以字母开头';
    }

    if (!formData.dimensionName.trim()) {
      newErrors.dimensionName = '维度名称不能为空';
    }

    if (formData.dimensionType === 'select' && !formData.description.trim()) {
      newErrors.description = '选择类型维度必须填写描述';
    }

    if (formData.sortOrder < 0) {
      newErrors.sortOrder = '排序值不能为负数';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    try {
      await onSubmit(formData);
    } catch (error) {
      console.error('提交失败:', error);
    }
  };

  const getTypeDescription = (type: string) => {
    const descriptions: Record<string, string> = {
      select: '选择类型：用户从预定义的值中选择',
      text: '文本类型：用户输入任意文本',
      number: '数字类型：用户输入数字',
      boolean: '布尔类型：用户选择是/否',
    };
    return descriptions[type] || '';
  };

  return (
    <Box>
      {/* 表单 */}
      <form onSubmit={handleSubmit}>
        <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
          {/* 基本信息 */}
          <Box sx={{ width: "100%" }}>
            <Paper sx={{ p: 2 }}>
              <Typography variant='subtitle1' sx={{ mb: 2 }}>
                基本信息
              </Typography>

              <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
                <Box sx={{ width: { xs: "100%", sm: "50%" } }}>
                  <TextField
                    fullWidth
                    label='维度编码'
                    value={formData.dimensionCode}
                    onChange={e =>
                      handleChange('dimensionCode', e.target.value)
                    }
                    error={Boolean(errors.dimensionCode)}
                    helperText={
                      errors.dimensionCode ||
                      '用于系统内部识别，如：color, size'
                    }
                    disabled={isEdit} // 编辑时不允许修改编码
                    required
                  />
                </Box>

                <Box sx={{ width: { xs: "100%", sm: "50%" } }}>
                  <TextField
                    fullWidth
                    label='维度名称'
                    value={formData.dimensionName}
                    onChange={e =>
                      handleChange('dimensionName', e.target.value)
                    }
                    error={Boolean(errors.dimensionName)}
                    helperText={
                      errors.dimensionName || '显示给用户的名称，如：颜色, 尺码'
                    }
                    required
                  />
                </Box>

                <Box sx={{ width: { xs: "100%", sm: "50%" } }}>
                  <FormControl fullWidth required>
                    <InputLabel>维度类型</InputLabel>
                    <Select
                      value={formData.dimensionType}
                      label='维度类型'
                      onChange={e =>
                        handleChange('dimensionType', e.target.value)
                      }
                    >
                      <MenuItem value='select'>选择</MenuItem>
                      <MenuItem value='text'>文本</MenuItem>
                      <MenuItem value='number'>数字</MenuItem>
                      <MenuItem value='boolean'>布尔</MenuItem>
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
                      handleChange('sortOrder', parseInt(e.target.value) || 0)
                    }
                    error={Boolean(errors.sortOrder)}
                    helperText={errors.sortOrder || '数值越小排序越靠前'}
                  />
                </Box>

                <Box sx={{ width: "100%" }}>
                  <TextField
                    fullWidth
                    label='描述'
                    value={formData.description}
                    onChange={e => handleChange('description', e.target.value)}
                    error={Boolean(errors.description)}
                    helperText={
                      errors.description ||
                      getTypeDescription(formData.dimensionType)
                    }
                    multiline
                    rows={2}
                  />
                </Box>
              </Box>
            </Paper>
          </Box>

          {/* 状态设置 */}
          <Box sx={{ width: "100%" }}>
            <Paper sx={{ p: 2 }}>
              <Typography variant='subtitle1' sx={{ mb: 2 }}>
                状态设置
              </Typography>

              <FormControlLabel
                control={
                  <Switch
                    checked={formData.isActive}
                    onChange={e => handleChange('isActive', e.target.checked)}
                  />
                }
                label='启用维度模板'
              />
            </Paper>
          </Box>

          {/* 错误提示 */}
          {Object.keys(errors).length > 0 && (
            <Box sx={{ width: "100%" }}>
              <Alert severity='error'>请检查表单中的错误信息</Alert>
            </Box>
          )}
        </Box>
      </form>
    </Box>
  );
}
