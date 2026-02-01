'use client';

import React, { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Grid,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Switch,
  FormControlLabel,
  Alert,
  CircularProgress,
  Divider,
  Snackbar,
} from '@mui/material';
import {
  ArrowBack as ArrowBackIcon,
  Save as SaveIcon,
} from '@mui/icons-material';
import { useRouter } from 'next/navigation';
import { frontendApi } from '@/lib/api';

interface ProductCreateData {
  title: string;
  description: string;
  handle: string;
  product_type: string;
  vendor: string;
  status: string;
  is_active: boolean;
  is_available: boolean;
}

export function ProductCreate() {
  const router = useRouter();
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [formData, setFormData] = useState<ProductCreateData>({
    title: '',
    description: '',
    handle: '',
    product_type: '',
    vendor: '',
    status: 'draft',
    is_active: true,
    is_available: true,
  });

  const handleBack = () => {
    router.push('/products');
  };

  const handleInputChange = (field: keyof ProductCreateData, value: any) => {
    setFormData(prev => ({
      ...prev,
      [field]: value,
    }));
  };

  const handleSave = async () => {
    // 验证必填字段
    if (!formData.title.trim()) {
      setError('商品标题不能为空');
      return;
    }

    try {
      setSaving(true);
      setError(null);
      console.log('🔍 开始创建商品:', formData);

      const response = await frontendApi.post('/api/products', formData);

      console.log('✅ 商品创建成功:', response.data);
      setSuccess('商品创建成功');

      // 创建成功后跳转到商品详情页或编辑页
      setTimeout(() => {
        if (response.data.id_hashid) {
          router.push(`/products/${response.data.id_hashid}/edit`);
        } else {
          router.push('/products');
        }
      }, 1000);
    } catch (err: any) {
      console.error('❌ 创建商品失败:', err);
      setError(err.response?.data?.detail || '创建商品失败');
    } finally {
      setSaving(false);
    }
  };

  const handleCloseSnackbar = () => {
    setSuccess(null);
    setError(null);
  };

  return (
    <Box sx={{ p: 3 }}>
      {/* 头部 */}
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          mb: 3,
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Button
            startIcon={<ArrowBackIcon />}
            onClick={handleBack}
            variant="outlined"
          >
            返回
          </Button>
          <Typography variant="h5">创建新商品</Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button
            variant="contained"
            startIcon={saving ? <CircularProgress size={20} /> : <SaveIcon />}
            onClick={handleSave}
            disabled={saving || !formData.title.trim()}
          >
            {saving ? '保存中...' : '创建商品'}
          </Button>
        </Box>
      </Box>

      {/* 错误提示 */}
      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* 基本信息卡片 */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            基本信息
          </Typography>
          <Divider sx={{ mb: 2 }} />

          <Grid container spacing={3}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="商品标题"
                value={formData.title}
                onChange={e => handleInputChange('title', e.target.value)}
                required
                helperText="必填项"
              />
            </Grid>

            <Grid item xs={12}>
              <TextField
                fullWidth
                label="商品描述"
                value={formData.description}
                onChange={e => handleInputChange('description', e.target.value)}
                multiline
                rows={4}
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="商品别名 (Handle)"
                value={formData.handle}
                onChange={e => handleInputChange('handle', e.target.value)}
                helperText="用于 URL 的唯一标识符，留空将自动生成"
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="商品类型"
                value={formData.product_type}
                onChange={e => handleInputChange('product_type', e.target.value)}
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="供应商"
                value={formData.vendor}
                onChange={e => handleInputChange('vendor', e.target.value)}
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <FormControl fullWidth>
                <InputLabel>状态</InputLabel>
                <Select
                  value={formData.status}
                  label="状态"
                  onChange={e => handleInputChange('status', e.target.value)}
                >
                  <MenuItem value="draft">草稿</MenuItem>
                  <MenuItem value="active">已发布</MenuItem>
                  <MenuItem value="archived">已归档</MenuItem>
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12} md={6}>
              <FormControlLabel
                control={
                  <Switch
                    checked={formData.is_active}
                    onChange={e =>
                      handleInputChange('is_active', e.target.checked)
                    }
                  />
                }
                label="启用"
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <FormControlLabel
                control={
                  <Switch
                    checked={formData.is_available}
                    onChange={e =>
                      handleInputChange('is_available', e.target.checked)
                    }
                  />
                }
                label="可售"
              />
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* 提示信息 */}
      <Alert severity="info">
        创建商品后，您可以在编辑页面添加变体、维度和标签等详细信息。
      </Alert>

      {/* 成功/错误 Snackbar */}
      <Snackbar
        open={!!success}
        autoHideDuration={3000}
        onClose={handleCloseSnackbar}
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
      >
        <Alert
          onClose={handleCloseSnackbar}
          severity="success"
          sx={{ width: '100%' }}
        >
          {success}
        </Alert>
      </Snackbar>
    </Box>
  );
}
