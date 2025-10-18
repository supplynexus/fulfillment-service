'use client';

import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Checkbox,
  Button,
  Chip,
  Alert,
  CircularProgress,
  FormControlLabel,
  Switch,
  Divider,
  Grid,
  Card,
  CardContent,
  CardActions,
} from '@mui/material';
import {
  SelectAll as SelectAllIcon,
  ClearAll as DeselectAllIcon,
  Save as SaveIcon,
  Preview as PreviewIcon,
} from '@mui/icons-material';

interface Product {
  id: string;
  name: string;
  code: string;
  description?: string;
  categoryId: string;
  categoryName: string;
  isActive: boolean;
}

interface GeneratedSku {
  id: string;
  sku: string;
  name: string;
  dimensions: Record<string, string>;
  isSelected: boolean;
}

interface SkuGeneratorProps {
  product: Product | null;
  generatedSkus: GeneratedSku[];
  onSkuToggle: (skuId: string, isSelected: boolean) => void;
  onSelectAll: (isSelected: boolean) => void;
  onCreateSkus: () => void;
  loading: boolean;
}

export default function SkuGenerator({
  product,
  generatedSkus,
  onSkuToggle,
  onSelectAll,
  onCreateSkus,
  loading,
}: SkuGeneratorProps) {
  const [selectAll, setSelectAll] = useState(true);
  const [showPreview, setShowPreview] = useState(false);

  useEffect(() => {
    if (generatedSkus.length > 0) {
      const allSelected = generatedSkus.every(sku => sku.isSelected);
      setSelectAll(allSelected);
    }
  }, [generatedSkus]);

  const handleSelectAllToggle = (isSelected: boolean) => {
    setSelectAll(isSelected);
    onSelectAll(isSelected);
  };

  const handleSkuToggle = (skuId: string, isSelected: boolean) => {
    onSkuToggle(skuId, isSelected);
  };

  const selectedCount = generatedSkus.filter(sku => sku.isSelected).length;
  const totalCount = generatedSkus.length;

  const getDimensionChips = (dimensions: Record<string, string>) => {
    return Object.entries(dimensions).map(([key, value]) => (
      <Chip
        key={key}
        label={`${key}: ${value}`}
        size='small'
        color='primary'
        variant='outlined'
        sx={{ mr: 0.5, mb: 0.5 }}
      />
    ));
  };

  if (loading) {
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

  if (!product) {
    return <Alert severity='warning'>请先选择一个产品</Alert>;
  }

  if (generatedSkus.length === 0) {
    return (
      <Alert severity='info'>没有可生成的 SKU，请返回上一步选择维度和值</Alert>
    );
  }

  return (
    <Box>
      {/* 标题 */}
      <Typography variant='h6' sx={{ mb: 2 }}>
        生成 SKU
      </Typography>

      {/* 产品信息 */}
      <Paper sx={{ p: 2, mb: 3, bgcolor: 'grey.50' }}>
        <Typography variant='body2' color='text.secondary'>
          产品: {product.name} ({product.code})
        </Typography>
        <Typography variant='body2' color='text.secondary'>
          共生成 {totalCount} 个 SKU，已选择 {selectedCount} 个
        </Typography>
      </Paper>

      {/* 批量操作 */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            mb: 2,
          }}
        >
          <Typography variant='subtitle1'>批量操作</Typography>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button
              size='small'
              startIcon={<SelectAllIcon />}
              onClick={() => handleSelectAllToggle(true)}
              disabled={selectAll}
            >
              全选
            </Button>
            <Button
              size='small'
              startIcon={<DeselectAllIcon />}
              onClick={() => handleSelectAllToggle(false)}
              disabled={!selectAll}
            >
              取消全选
            </Button>
          </Box>
        </Box>

        <FormControlLabel
          control={
            <Switch
              checked={selectAll}
              onChange={e => handleSelectAllToggle(e.target.checked)}
            />
          }
          label={`全选所有 SKU (${selectedCount}/${totalCount})`}
        />
      </Paper>

      {/* SKU 列表 */}
      <Paper sx={{ mb: 3 }}>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell padding='checkbox'>
                  <Checkbox
                    checked={selectAll}
                    indeterminate={
                      selectedCount > 0 && selectedCount < totalCount
                    }
                    onChange={e => handleSelectAllToggle(e.target.checked)}
                  />
                </TableCell>
                <TableCell>SKU 编码</TableCell>
                <TableCell>SKU 名称</TableCell>
                <TableCell>维度信息</TableCell>
                <TableCell>状态</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {generatedSkus.map(sku => (
                <TableRow key={sku.id} hover>
                  <TableCell padding='checkbox'>
                    <Checkbox
                      checked={sku.isSelected}
                      onChange={e => handleSkuToggle(sku.id, e.target.checked)}
                    />
                  </TableCell>
                  <TableCell>
                    <Typography variant='body2' fontWeight='medium'>
                      {sku.sku}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant='body2'>{sku.name}</Typography>
                  </TableCell>
                  <TableCell>
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                      {getDimensionChips(sku.dimensions)}
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={sku.isSelected ? '已选择' : '未选择'}
                      color={sku.isSelected ? 'success' : 'default'}
                      size='small'
                    />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>

      {/* 统计信息 */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={4}>
          <Card>
            <CardContent>
              <Typography variant='h6' color='primary'>
                {totalCount}
              </Typography>
              <Typography variant='body2' color='text.secondary'>
                总 SKU 数量
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={4}>
          <Card>
            <CardContent>
              <Typography variant='h6' color='success.main'>
                {selectedCount}
              </Typography>
              <Typography variant='body2' color='text.secondary'>
                已选择数量
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={4}>
          <Card>
            <CardContent>
              <Typography variant='h6' color='warning.main'>
                {totalCount - selectedCount}
              </Typography>
              <Typography variant='body2' color='text.secondary'>
                未选择数量
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* 选择提示 */}
      {selectedCount === 0 && (
        <Alert severity='warning' sx={{ mb: 3 }}>
          请至少选择一个 SKU 进行创建
        </Alert>
      )}

      {/* 创建按钮 */}
      <Box sx={{ display: 'flex', gap: 2, justifyContent: 'flex-end' }}>
        <Button
          variant='outlined'
          startIcon={<PreviewIcon />}
          onClick={() => setShowPreview(!showPreview)}
        >
          {showPreview ? '隐藏' : '显示'} 预览
        </Button>

        <Button
          variant='contained'
          startIcon={<SaveIcon />}
          onClick={onCreateSkus}
          disabled={selectedCount === 0 || loading}
        >
          {loading ? '创建中...' : `创建 ${selectedCount} 个 SKU`}
        </Button>
      </Box>

      {/* 预览模式 */}
      {showPreview && (
        <Paper sx={{ mt: 3, p: 2 }}>
          <Typography variant='subtitle1' sx={{ mb: 2 }}>
            SKU 预览 (前 5 个)
          </Typography>
          <Grid container spacing={2}>
            {generatedSkus.slice(0, 5).map(sku => (
              <Grid item xs={12} sm={6} md={4} key={sku.id}>
                <Card variant='outlined'>
                  <CardContent>
                    <Typography variant='body2' fontWeight='medium'>
                      {sku.sku}
                    </Typography>
                    <Typography variant='caption' color='text.secondary'>
                      {sku.name}
                    </Typography>
                    <Box sx={{ mt: 1 }}>
                      {getDimensionChips(sku.dimensions)}
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
          {generatedSkus.length > 5 && (
            <Typography
              variant='body2'
              color='text.secondary'
              sx={{ mt: 2, textAlign: 'center' }}
            >
              显示前 5 个 SKU，共 {generatedSkus.length} 个
            </Typography>
          )}
        </Paper>
      )}
    </Box>
  );
}
