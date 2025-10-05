'use client';

import React, { useState, useEffect } from 'react';
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
  Tabs,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  Tooltip,
  Chip,
  Divider,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Snackbar,
} from '@mui/material';
import {
  ArrowBack as ArrowBackIcon,
  Save as SaveIcon,
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';
import { useRouter } from 'next/navigation';
import { frontendApi } from '@/lib/api';
import { Product } from '@/types/product';

interface ProductEditProps {
  productHashId: string;
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`product-edit-tabpanel-${index}`}
      aria-labelledby={`product-edit-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

export function ProductEdit({ productHashId }: ProductEditProps) {
  const router = useRouter();
  const [product, setProduct] = useState<Product | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [tabValue, setTabValue] = useState(0);

  // 编辑状态
  const [editData, setEditData] = useState<Partial<Product>>({});
  const [hasChanges, setHasChanges] = useState(false);

  // 变体编辑状态
  const [editingVariant, setEditingVariant] = useState<string | null>(null);
  const [variantDialogOpen, setVariantDialogOpen] = useState(false);
  const [newVariant, setNewVariant] = useState<any>({});

  // 维度编辑状态
  const [editingDimension, setEditingDimension] = useState<string | null>(null);
  const [dimensionDialogOpen, setDimensionDialogOpen] = useState(false);
  const [newDimension, setNewDimension] = useState<any>({});

  const fetchProduct = async () => {
    try {
      setLoading(true);
      setError(null);
      console.log('🔍 开始获取商品详情:', productHashId);

      const response = await frontendApi.get(`/api/products/${productHashId}`, {
        params: {
          include_variants: true,
          include_dimensions: true,
          include_tags: true,
          include_mappings: true,
        },
      });

      console.log('✅ 商品详情获取成功:', response.data);
      setProduct(response.data);
      setEditData(response.data);
    } catch (err: any) {
      console.error('❌ 获取商品详情失败:', err);
      setError(err.response?.data?.detail || 'Failed to fetch product');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProduct();
  }, [productHashId]);

  const handleBack = () => {
    router.push('/products');
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      setError(null);
      console.log('🔍 开始保存商品信息:', editData);

      const response = await frontendApi.put(`/api/products/${productHashId}`, editData);
      
      console.log('✅ 商品信息保存成功:', response.data);
      setSuccess('商品信息已保存');
      setHasChanges(false);
      
      // 刷新数据
      await fetchProduct();
    } catch (err: any) {
      console.error('❌ 保存商品信息失败:', err);
      setError(err.response?.data?.detail || 'Failed to save product');
    } finally {
      setSaving(false);
    }
  };

  const handleInputChange = (field: string, value: any) => {
    console.log('🔍 字段值变化:', field, value);
    setEditData(prev => ({
      ...prev,
      [field]: value
    }));
    setHasChanges(true);
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleAddVariant = () => {
    setNewVariant({
      sku: '',
      attributes: {},
      price: 0,
      inventory_quantity: 0,
      is_active: true,
      is_available: true,
    });
    setVariantDialogOpen(true);
  };

  const handleEditVariant = (variantHashId: string) => {
    const variant = product?.variants.find(v => v.id_hashid === variantHashId);
    if (variant) {
      setNewVariant(variant);
      setEditingVariant(variantHashId);
      setVariantDialogOpen(true);
    }
  };

  const handleSaveVariant = async () => {
    try {
      console.log('🔍 保存变体:', newVariant);
      // TODO: 实现变体保存逻辑
      setVariantDialogOpen(false);
      setEditingVariant(null);
      setNewVariant({});
    } catch (err: any) {
      console.error('❌ 保存变体失败:', err);
      setError('Failed to save variant');
    }
  };

  const handleAddDimension = () => {
    setNewDimension({
      dimension_name: '',
      dimension_type: 'select',
      display_name: '',
      options: [],
      is_required: true,
      is_active: true,
    });
    setDimensionDialogOpen(true);
  };

  const handleEditDimension = (dimensionHashId: string) => {
    const dimension = product?.dimensions.find(d => d.id_hashid === dimensionHashId);
    if (dimension) {
      setNewDimension(dimension);
      setEditingDimension(dimensionHashId);
      setDimensionDialogOpen(true);
    }
  };

  const handleSaveDimension = async () => {
    try {
      console.log('🔍 保存维度:', newDimension);
      // TODO: 实现维度保存逻辑
      setDimensionDialogOpen(false);
      setEditingDimension(null);
      setNewDimension({});
    } catch (err: any) {
      console.error('❌ 保存维度失败:', err);
      setError('Failed to save dimension');
    }
  };

  const handleCloseSnackbar = () => {
    setSuccess(null);
    setError(null);
  };

  if (loading) {
    return (
      <Box
        display="flex"
        justifyContent="center"
        alignItems="center"
        minHeight="400px"
      >
        <CircularProgress />
      </Box>
    );
  }

  if (error && !product) {
    return (
      <Box>
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
        <Button
          variant="outlined"
          startIcon={<ArrowBackIcon />}
          onClick={handleBack}
        >
          返回商品列表
        </Button>
      </Box>
    );
  }

  if (!product) {
    return (
      <Box>
        <Alert severity="error" sx={{ mb: 2 }}>
          Product not found
        </Alert>
        <Button
          variant="outlined"
          startIcon={<ArrowBackIcon />}
          onClick={handleBack}
        >
          返回商品列表
        </Button>
      </Box>
    );
  }

  return (
    <Box>
      {/* 头部操作栏 */}
      <Box
        display="flex"
        justifyContent="space-between"
        alignItems="center"
        mb={3}
      >
        <Box display="flex" alignItems="center" gap={2}>
          <Button
            variant="outlined"
            startIcon={<ArrowBackIcon />}
            onClick={handleBack}
          >
            返回
          </Button>
          <Typography variant="h4" component="h1">
            编辑商品: {product.title}
          </Typography>
        </Box>
        <Box display="flex" gap={2}>
          <Button
            variant="contained"
            startIcon={<SaveIcon />}
            onClick={handleSave}
            disabled={saving || !hasChanges}
          >
            {saving ? '保存中...' : '保存'}
          </Button>
        </Box>
      </Box>

      {/* 错误和成功提示 */}
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {/* 基本信息编辑 */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            基本信息
          </Typography>
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="商品标题"
                value={editData.title || ''}
                onChange={(e) => handleInputChange('title', e.target.value)}
                variant="outlined"
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Handle"
                value={editData.handle || ''}
                onChange={(e) => handleInputChange('handle', e.target.value)}
                variant="outlined"
                helperText="URL友好的标识符"
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="商品描述"
                value={editData.description || ''}
                onChange={(e) => handleInputChange('description', e.target.value)}
                variant="outlined"
                multiline
                rows={3}
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <TextField
                fullWidth
                label="商品类型"
                value={editData.product_type || ''}
                onChange={(e) => handleInputChange('product_type', e.target.value)}
                variant="outlined"
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <TextField
                fullWidth
                label="供应商"
                value={editData.vendor || ''}
                onChange={(e) => handleInputChange('vendor', e.target.value)}
                variant="outlined"
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <FormControl fullWidth>
                <InputLabel>状态</InputLabel>
                <Select
                  value={editData.status || 'draft'}
                  onChange={(e) => handleInputChange('status', e.target.value)}
                  label="状态"
                >
                  <MenuItem value="draft">草稿</MenuItem>
                  <MenuItem value="active">活跃</MenuItem>
                  <MenuItem value="archived">已归档</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} md={6}>
              <FormControlLabel
                control={
                  <Switch
                    checked={editData.is_active || false}
                    onChange={(e) => handleInputChange('is_active', e.target.checked)}
                  />
                }
                label="商品激活"
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <FormControlLabel
                control={
                  <Switch
                    checked={editData.is_available || false}
                    onChange={(e) => handleInputChange('is_available', e.target.checked)}
                  />
                }
                label="商品可用"
              />
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* 详细信息标签页 */}
      <Card>
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs value={tabValue} onChange={handleTabChange}>
            <Tab label={`变体 (${product.variants.length})`} />
            <Tab label={`维度 (${product.dimensions.length})`} />
            <Tab label={`标签 (${product.tags.length})`} />
          </Tabs>
        </Box>

        {/* 变体标签页 */}
        <TabPanel value={tabValue} index={0}>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="h6">
              商品变体
            </Typography>
            <Button
              variant="outlined"
              startIcon={<AddIcon />}
              onClick={handleAddVariant}
            >
              添加变体
            </Button>
          </Box>
          
          {product.variants.length > 0 ? (
            <TableContainer component={Paper} variant="outlined">
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>SKU</TableCell>
                    <TableCell>属性</TableCell>
                    <TableCell>价格</TableCell>
                    <TableCell>库存</TableCell>
                    <TableCell>状态</TableCell>
                    <TableCell>操作</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {product.variants.map(variant => (
                    <TableRow key={variant.id_hashid} hover>
                      <TableCell>
                        <Typography variant="body2">
                          {variant.sku || '-'}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Box display="flex" gap={0.5} flexWrap="wrap">
                          {Object.entries(variant.attributes).map(([key, value]) => (
                            <Chip
                              key={key}
                              label={`${key}: ${value}`}
                              size="small"
                              variant="outlined"
                            />
                          ))}
                        </Box>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">
                          ${variant.price || 0}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">
                          {variant.inventory_quantity}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={variant.is_active ? '活跃' : '非活跃'}
                          color={variant.is_active ? 'success' : 'default'}
                          size="small"
                        />
                      </TableCell>
                      <TableCell>
                        <Tooltip title="编辑变体">
                          <IconButton
                            size="small"
                            onClick={() => handleEditVariant(variant.id_hashid)}
                          >
                            <EditIcon />
                          </IconButton>
                        </Tooltip>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          ) : (
            <Typography variant="body2" color="text.secondary">
              暂无变体，点击"添加变体"创建第一个变体
            </Typography>
          )}
        </TabPanel>

        {/* 维度标签页 */}
        <TabPanel value={tabValue} index={1}>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="h6">
              商品维度
            </Typography>
            <Button
              variant="outlined"
              startIcon={<AddIcon />}
              onClick={handleAddDimension}
            >
              添加维度
            </Button>
          </Box>
          
          {product.dimensions.length > 0 ? (
            <TableContainer component={Paper} variant="outlined">
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>维度名称</TableCell>
                    <TableCell>显示名称</TableCell>
                    <TableCell>类型</TableCell>
                    <TableCell>选项</TableCell>
                    <TableCell>必需</TableCell>
                    <TableCell>状态</TableCell>
                    <TableCell>操作</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {product.dimensions.map(dimension => (
                    <TableRow key={dimension.id_hashid} hover>
                      <TableCell>
                        <Typography variant="body2">
                          {dimension.dimension_name}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">
                          {dimension.display_name || '-'}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={dimension.dimension_type}
                          size="small"
                          variant="outlined"
                        />
                      </TableCell>
                      <TableCell>
                        <Box display="flex" gap={0.5} flexWrap="wrap">
                          {dimension.options?.slice(0, 3).map(option => (
                            <Chip
                              key={option}
                              label={option}
                              size="small"
                            />
                          ))}
                          {dimension.options && dimension.options.length > 3 && (
                            <Chip
                              label={`+${dimension.options.length - 3}`}
                              size="small"
                              variant="outlined"
                            />
                          )}
                        </Box>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={dimension.is_required ? '是' : '否'}
                          color={dimension.is_required ? 'primary' : 'default'}
                          size="small"
                        />
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={dimension.is_active ? '活跃' : '非活跃'}
                          color={dimension.is_active ? 'success' : 'default'}
                          size="small"
                        />
                      </TableCell>
                      <TableCell>
                        <Tooltip title="编辑维度">
                          <IconButton
                            size="small"
                            onClick={() => handleEditDimension(dimension.id_hashid)}
                          >
                            <EditIcon />
                          </IconButton>
                        </Tooltip>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          ) : (
            <Typography variant="body2" color="text.secondary">
              暂无维度，点击"添加维度"创建第一个维度
            </Typography>
          )}
        </TabPanel>

        {/* 标签标签页 */}
        <TabPanel value={tabValue} index={2}>
          <Typography variant="h6" gutterBottom>
            商品标签
          </Typography>
          {product.tags.length > 0 ? (
            <Box display="flex" gap={1} flexWrap="wrap">
              {product.tags.map(tag => (
                <Chip
                  key={tag.id_hashid}
                  label={tag.name}
                  color={tag.is_primary ? 'primary' : 'default'}
                  variant={tag.is_primary ? 'filled' : 'outlined'}
                />
              ))}
            </Box>
          ) : (
            <Typography variant="body2" color="text.secondary">
              暂无标签
            </Typography>
          )}
        </TabPanel>
      </Card>

      {/* 变体编辑对话框 */}
      <Dialog
        open={variantDialogOpen}
        onClose={() => setVariantDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          {editingVariant ? '编辑变体' : '添加变体'}
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="SKU"
                value={newVariant.sku || ''}
                onChange={(e) => setNewVariant(prev => ({ ...prev, sku: e.target.value }))}
                variant="outlined"
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="条码"
                value={newVariant.barcode || ''}
                onChange={(e) => setNewVariant(prev => ({ ...prev, barcode: e.target.value }))}
                variant="outlined"
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <TextField
                fullWidth
                label="价格"
                type="number"
                value={newVariant.price || 0}
                onChange={(e) => setNewVariant(prev => ({ ...prev, price: parseFloat(e.target.value) }))}
                variant="outlined"
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <TextField
                fullWidth
                label="对比价格"
                type="number"
                value={newVariant.compare_at_price || 0}
                onChange={(e) => setNewVariant(prev => ({ ...prev, compare_at_price: parseFloat(e.target.value) }))}
                variant="outlined"
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <TextField
                fullWidth
                label="库存数量"
                type="number"
                value={newVariant.inventory_quantity || 0}
                onChange={(e) => setNewVariant(prev => ({ ...prev, inventory_quantity: parseInt(e.target.value) }))}
                variant="outlined"
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <FormControlLabel
                control={
                  <Switch
                    checked={newVariant.is_active || false}
                    onChange={(e) => setNewVariant(prev => ({ ...prev, is_active: e.target.checked }))}
                  />
                }
                label="变体激活"
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <FormControlLabel
                control={
                  <Switch
                    checked={newVariant.is_available || false}
                    onChange={(e) => setNewVariant(prev => ({ ...prev, is_available: e.target.checked }))}
                  />
                }
                label="变体可用"
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setVariantDialogOpen(false)}>
            取消
          </Button>
          <Button onClick={handleSaveVariant} variant="contained">
            保存
          </Button>
        </DialogActions>
      </Dialog>

      {/* 维度编辑对话框 */}
      <Dialog
        open={dimensionDialogOpen}
        onClose={() => setDimensionDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          {editingDimension ? '编辑维度' : '添加维度'}
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="维度名称"
                value={newDimension.dimension_name || ''}
                onChange={(e) => setNewDimension(prev => ({ ...prev, dimension_name: e.target.value }))}
                variant="outlined"
                helperText="如: color, size, material"
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="显示名称"
                value={newDimension.display_name || ''}
                onChange={(e) => setNewDimension(prev => ({ ...prev, display_name: e.target.value }))}
                variant="outlined"
                helperText="如: 颜色, 尺寸, 材质"
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <FormControl fullWidth>
                <InputLabel>维度类型</InputLabel>
                <Select
                  value={newDimension.dimension_type || 'select'}
                  onChange={(e) => setNewDimension(prev => ({ ...prev, dimension_type: e.target.value }))}
                  label="维度类型"
                >
                  <MenuItem value="select">选择</MenuItem>
                  <MenuItem value="text">文本</MenuItem>
                  <MenuItem value="number">数字</MenuItem>
                  <MenuItem value="boolean">布尔</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} md={6}>
              <FormControlLabel
                control={
                  <Switch
                    checked={newDimension.is_required || false}
                    onChange={(e) => setNewDimension(prev => ({ ...prev, is_required: e.target.checked }))}
                  />
                }
                label="必需维度"
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="维度描述"
                value={newDimension.description || ''}
                onChange={(e) => setNewDimension(prev => ({ ...prev, description: e.target.value }))}
                variant="outlined"
                multiline
                rows={2}
              />
            </Grid>
            <Grid item xs={12}>
              <FormControlLabel
                control={
                  <Switch
                    checked={newDimension.is_active || false}
                    onChange={(e) => setNewDimension(prev => ({ ...prev, is_active: e.target.checked }))}
                  />
                }
                label="维度激活"
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDimensionDialogOpen(false)}>
            取消
          </Button>
          <Button onClick={handleSaveDimension} variant="contained">
            保存
          </Button>
        </DialogActions>
      </Dialog>

      {/* 成功/错误提示 */}
      <Snackbar
        open={!!success || !!error}
        autoHideDuration={6000}
        onClose={handleCloseSnackbar}
        anchorOrigin={{ vertical: 'top', horizontal: 'right' }}
      >
        <Alert
          onClose={handleCloseSnackbar}
          severity={success ? 'success' : 'error'}
          sx={{ width: '100%' }}
        >
          {success || error}
        </Alert>
      </Snackbar>
    </Box>
  );
}