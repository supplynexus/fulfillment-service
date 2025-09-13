'use client';

import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Grid,
  Chip,
  Button,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Alert,
  CircularProgress,
  FormControlLabel,
  Switch,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from '@mui/material';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { frontendLogger } from '@/lib/frontend-logger';
import {
  Store as StoreIcon,
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Refresh as RefreshIcon,
  Wifi as TestConnectionIcon,
  CheckCircle as ActiveIcon,
  Inventory as InventoryIcon,
  ShoppingCart as ShoppingCartIcon,
  Cancel as InactiveIcon,
  ExpandMore as ExpandMoreIcon,
  Security as SecurityIcon,
  Settings as SettingsIcon,
  Sync as SyncIcon,
} from '@mui/icons-material';

interface ShopifyStore {
  id: number;
  name: string;
  system_type: string;
  external_id?: string;
  base_url?: string;
  credentials: {
    access_token?: string;
    shop_id?: string;
    store_url?: string;
    api_key?: string;
    api_secret?: string;
  };
  settings: {
    api_version?: string;
    webhook_topics?: string[];
    [key: string]: any;
  };
  is_active: boolean;
  sync_enabled: boolean;
  webhook_enabled: boolean;
  last_sync_at?: string;
  created_at: string;
}

export default function ShopifyStoresPage() {
  const [stores, setStores] = useState<ShopifyStore[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [openDialog, setOpenDialog] = useState(false);
  const [editingStore, setEditingStore] = useState<ShopifyStore | null>(null);
  const [openProductsDialog, setOpenProductsDialog] = useState(false);
  const [openOrdersDialog, setOpenOrdersDialog] = useState(false);
  const [selectedStore, setSelectedStore] = useState<ShopifyStore | null>(null);
  const [products, setProducts] = useState<any[]>([]);
  const [orders, setOrders] = useState<any[]>([]);
  const [loadingProducts, setLoadingProducts] = useState(false);
  const [loadingOrders, setLoadingOrders] = useState(false);
  const [syncingOrders, setSyncingOrders] = useState<Record<string, boolean>>({});
  const [showTestResultDialog, setShowTestResultDialog] = useState(false);
  const [testResult, setTestResult] = useState<any>(null);
  const [testingConnection, setTestingConnection] = useState(false);
  const [showSyncResultDialog, setShowSyncResultDialog] = useState(false);
  const [syncResult, setSyncResult] = useState<any>(null);
  const [formData, setFormData] = useState({
    name: '',
    external_id: '',
    base_url: '',
    credentials: {
      access_token: '',
      shop_id: '',
      store_url: '',
      api_key: '',
      api_secret: '',
    },
    settings: {
      api_version: '2024-10',
      webhook_topics: ['orders/create', 'orders/updated', 'orders/cancelled'],
    },
    is_active: true,
    sync_enabled: true,
    webhook_enabled: true,
  });

  // Fetch stores data
  const fetchStores = async () => {
    try {
      setLoading(true);
      setError(null);

      // This would be replaced with actual API call
      // For now, using mock data based on database query results
      const mockStores: ShopifyStore[] = [
        {
          id: 1, // Real ID for backend, but we'll use hashid for API calls
          name: 'Impeach Shopify Store',
          system_type: 'SHOPIFY',
          external_id: 'x0ri77-4v',
          base_url: 'https://x0ri77-4v.myshopify.com',
          credentials: {
            access_token: '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',
            shop_id: 'x0ri77-4v',
            store_url: 'https://x0ri77-4v.myshopify.com',
          },
          settings: {
            api_version: 'unstable',
            webhook_topics: [
              'orders/create',
              'orders/updated',
              'orders/cancelled',
            ],
          },
          is_active: true,
          sync_enabled: true,
          webhook_enabled: true,
          last_sync_at: '2025-08-14T09:32:32.017Z',
          created_at: '2025-08-13T08:53:49.702Z',
        },
        {
          id: 2, // Real ID for backend, but we'll use hashid for API calls
          name: 'Test Shopify Store',
          system_type: 'SHOPIFY',
          external_id: undefined, // This store has no external_id in database
          base_url: 'https://test-shop.myshopify.com',
          credentials: {
            api_key:
              'gAAAAABovwPxlPonr0DXaA78dXJfj3whVh8oNuaKJ7uqK2bAWRt-288isrz31TeSLhuIPW6gdeE_wdGPuQ5FcxxYUxb6ehtGig==',
            api_secret:
              'gAAAAABovwPxg9Ef3ik9RSBe40L3Bmcx61DiAaFvx4cW7AxXJEJfdrJrr7ThS-CoANCVs_2-J7vA3EDdHe2r_az7DxjTrtVPvw==',
          },
          settings: {
            test_setting: 'test_value',
          },
          is_active: true,
          sync_enabled: true,
          webhook_enabled: true,
          created_at: '2025-09-08T16:27:29.563Z',
        },
      ];

      setStores(mockStores);
    } catch (err) {
      setError('获取店铺信息失败');
      console.error('Error fetching stores:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStores();
  }, []);

  const handleAddStore = () => {
    setEditingStore(null);
    setFormData({
      name: '',
      external_id: '',
      base_url: '',
      credentials: {
        access_token: '',
        shop_id: '',
        store_url: '',
        api_key: '',
        api_secret: '',
      },
      settings: {
        api_version: '2024-10',
        webhook_topics: ['orders/create', 'orders/updated', 'orders/cancelled'],
      },
      is_active: true,
      sync_enabled: true,
      webhook_enabled: true,
    });
    setOpenDialog(true);
  };

  const handleEditStore = (store: ShopifyStore) => {
    setEditingStore(store);
    setFormData({
      name: store.name,
      external_id: store.external_id || '',
      base_url: store.base_url || '',
      credentials: {
        access_token: store.credentials.access_token || '',
        shop_id: store.credentials.shop_id || '',
        store_url: store.credentials.store_url || '',
        api_key: store.credentials.api_key || '',
        api_secret: store.credentials.api_secret || '',
      },
      settings: {
        api_version: store.settings.api_version || '2024-10',
        webhook_topics: store.settings.webhook_topics || [
          'orders/create',
          'orders/updated',
          'orders/cancelled',
        ],
      },
      is_active: store.is_active,
      sync_enabled: store.sync_enabled,
      webhook_enabled: store.webhook_enabled,
    });
    setOpenDialog(true);
  };

  const handleDeleteStore = async (storeId: number) => {
    if (window.confirm('确定要删除这个店铺吗？')) {
      try {
        // API call to delete store
        setStores(stores.filter(store => store.id !== storeId));
      } catch (err) {
        setError('删除店铺失败');
        console.error('Error deleting store:', err);
      }
    }
  };

  const handleViewProducts = async (store: ShopifyStore) => {
    if (!store.external_id) {
      setError('该店铺未配置 external_id，无法获取商品列表。');
      return;
    }

    try {
      setError(null);
      setSelectedStore(store);
      setLoadingProducts(true);
      setOpenProductsDialog(true);

      const response = await fetch(`/api/external-systems/shopify/${store.external_id}/products`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('access_token')}`,
        },
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }

      const data = await response.json();
      if (data.success) {
        setProducts(data.products || []);
      } else {
        setError(data.message || '获取商品列表失败');
      }
    } catch (err: any) {
      setError(err.message || '获取商品列表失败');
      console.error('Error getting products:', err);
    } finally {
      setLoadingProducts(false);
    }
  };

  const handleViewOrders = async (store: ShopifyStore) => {
    if (!store.external_id) {
      setError('该店铺未配置 external_id，无法获取订单列表。');
      return;
    }

    try {
      setError(null);
      setSelectedStore(store);
      setLoadingOrders(true);
      setOpenOrdersDialog(true);

      const response = await fetch(`/api/external-systems/shopify/${store.external_id}/orders`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('access_token')}`,
        },
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }

      const data = await response.json();
      if (data.success) {
        setOrders(data.orders || []);
      } else {
        setError(data.message || '获取订单列表失败');
      }
    } catch (err: any) {
      setError(err.message || '获取订单列表失败');
      console.error('Error getting orders:', err);
    } finally {
      setLoadingOrders(false);
    }
  };

  const handleSyncOrders = async (store: ShopifyStore) => {
    if (!store.external_id) {
      setError('该店铺未配置 external_id，无法同步订单。');
      return;
    }

    try {
      setError(null);
      setSyncingOrders(prev => ({ ...prev, [store.external_id!]: true }));

      const response = await fetch(`/api/external-systems/shopify/${store.external_id}/sync-orders`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('access_token')}`,
        },
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }

      const data = await response.json();
      if (data.success) {
        // Update the store's last_sync_at timestamp
        setStores(prevStores =>
          prevStores.map(s =>
            s.id === store.id
              ? { ...s, last_sync_at: new Date().toISOString() }
              : s
          )
        );
        
        setSyncResult({
          success: true,
          message: '同步成功！',
          orders_synced: data.orders_synced || 0,
          orders_updated: data.orders_updated || 0,
          total_processed: data.total_processed || 0
        });
        setShowSyncResultDialog(true);
      } else {
        setSyncResult({
          success: false,
          message: data.message || '同步订单失败'
        });
        setShowSyncResultDialog(true);
      }
    } catch (err: any) {
      setSyncResult({
        success: false,
        message: err.message || '同步订单失败'
      });
      setShowSyncResultDialog(true);
      console.error('Error syncing orders:', err);
    } finally {
      setSyncingOrders(prev => ({ ...prev, [store.external_id!]: false }));
    }
  };

  const handleTestConnectionFromForm = async () => {
    try {
      setError(null);

      // Validate required fields - only need shop_id and access_token
      if (!formData.credentials.shop_id) {
        setError('请填写 Shop ID');
        return;
      }
      if (!formData.credentials.access_token) {
        setError('请填写 Access Token');
        return;
      }

      // Prepare request data - only send shop_id and access_token
      const requestData = {
        shop_id: formData.credentials.shop_id,
        access_token: formData.credentials.access_token
      };

      const response = await fetch('/api/external-systems/shopify/test-connection', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('access_token')}`,
        },
        body: JSON.stringify(requestData),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }

      const data = await response.json();

      if (data.success) {
        const shopInfo = data.shop_info;
        setError(null);
        // Show success message
        alert(`连接测试成功！\n店铺名称: ${shopInfo.name}\n邮箱: ${shopInfo.email}\n域名: ${shopInfo.myshopify_domain}`);
      } else {
        setError(data.message || '连接测试失败');
      }
    } catch (err: any) {
      setError(err.message || '连接测试失败');
      console.error('Error testing connection:', err);
    }
  };

  const handleSaveStore = async () => {
    try {
      if (editingStore) {
        // Update existing store
        setStores(
          stores.map(store =>
            store.id === editingStore.id
              ? {
                  ...store,
                  name: formData.name,
                  external_id: formData.external_id,
                  base_url: formData.base_url,
                  credentials: formData.credentials,
                  settings: formData.settings,
                  is_active: formData.is_active,
                  sync_enabled: formData.sync_enabled,
                  webhook_enabled: formData.webhook_enabled,
                }
              : store
          )
        );
      } else {
        // Add new store
        const newStore: ShopifyStore = {
          id: Date.now(), // Temporary ID
          name: formData.name,
          system_type: 'SHOPIFY',
          external_id: formData.external_id,
          base_url: formData.base_url,
          credentials: formData.credentials,
          settings: formData.settings,
          is_active: formData.is_active,
          sync_enabled: formData.sync_enabled,
          webhook_enabled: formData.webhook_enabled,
          created_at: new Date().toISOString(),
        };
        setStores([...stores, newStore]);
      }
      setOpenDialog(false);
    } catch (err) {
      setError('保存店铺失败');
      console.error('Error saving store:', err);
    }
  };

  const handleTestConnection = async (store: ShopifyStore) => {
    try {
      setError(null);
      setTestingConnection(true);

      // Check if external_id exists
      if (!store.external_id) {
        setError('该店铺未配置 external_id，无法测试连接。请先配置店铺的 external_id。');
        return;
      }

      // Use external_id (shop_name) for API call - more user-friendly and secure
      // This ensures tenant isolation while using the public shop_name
      const response = await fetch(
        `/api/external-systems/by-external-id/${store.external_id}/test-connection`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${localStorage.getItem('access_token')}`,
          },
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }

      const data = await response.json();
      
      // 发送前端日志到后端
      frontendLogger.info('🔍 Shopify 测试连接响应数据', { 
        page: 'shopify-stores', 
        component: 'handleTestConnection', 
        action: 'test-connection-response', 
        responseData: data,
        hasShopInfo: !!data.shop_info,
        shopInfoKeys: data.shop_info ? Object.keys(data.shop_info) : []
      });

      if (data.success) {
        const shopInfo = data.shop_info;
        if (!shopInfo) {
          throw new Error('响应数据中缺少店铺信息');
        }
        
        // 设置测试结果并显示对话框
        setTestResult({
          success: true,
          message: '连接测试成功！',
          shop_info: shopInfo
        });
        setShowTestResultDialog(true);
      } else {
        throw new Error(data.message || '连接测试失败');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '连接测试失败';
      setError(`连接测试失败：${errorMessage}`);
      
      // 设置失败结果并显示对话框
      setTestResult({
        success: false,
        message: errorMessage
      });
      setShowTestResultDialog(true);
      
      // 发送错误日志到后端
      frontendLogger.error('❌ Shopify 测试连接失败', { 
        page: 'shopify-stores', 
        component: 'handleTestConnection', 
        action: 'test-connection-error', 
        error: errorMessage,
        errorDetails: err instanceof Error ? err.stack : String(err)
      });
      
      console.error('Error testing connection:', err);
    } finally {
      setTestingConnection(false);
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

  if (loading) {
    return (
      <ProtectedRoute>
        <DashboardLayout>
          <Box
            display='flex'
            justifyContent='center'
            alignItems='center'
            minHeight='400px'
          >
            <CircularProgress />
          </Box>
        </DashboardLayout>
      </ProtectedRoute>
    );
  }

  return (
    <ProtectedRoute>
      <DashboardLayout>
        <Box>
          {/* Header */}
          <Box
            display='flex'
            justifyContent='space-between'
            alignItems='center'
            mb={3}
          >
            <Box>
              <Typography variant='h4' component='h1' gutterBottom>
                Shopify 店铺管理
              </Typography>
              <Typography variant='body1' color='text.secondary'>
                管理您的 Shopify 店铺连接和配置
              </Typography>
            </Box>
            <Box>
              <Button
                variant='outlined'
                startIcon={<RefreshIcon />}
                onClick={fetchStores}
                sx={{ mr: 2 }}
              >
                刷新
              </Button>
              <Button
                variant='contained'
                startIcon={<AddIcon />}
                onClick={handleAddStore}
              >
                添加店铺
              </Button>
            </Box>
          </Box>

          {/* Error Alert */}
          {error && (
            <Alert
              severity='error'
              sx={{ mb: 3 }}
              onClose={() => setError(null)}
            >
              {error}
            </Alert>
          )}

          {/* Stores Grid */}
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 3 }}>
            {stores.map(store => (
              <Box key={store.id} sx={{ flex: '1 1 300px', minWidth: '300px' }}>
                <Card sx={{ height: '100%' }}>
                  <CardContent>
                    <Box
                      display='flex'
                      alignItems='center'
                      justifyContent='space-between'
                      mb={2}
                    >
                      <Box display='flex' alignItems='center'>
                        <StoreIcon color='primary' sx={{ mr: 1 }} />
                        <Typography variant='h6' component='h2'>
                          {store.name}
                        </Typography>
                      </Box>
                      <Box display='flex' alignItems='center'>
                        {store.is_active ? (
                          <ActiveIcon color='success' fontSize='small' />
                        ) : (
                          <InactiveIcon color='error' fontSize='small' />
                        )}
                      </Box>
                    </Box>

                    <Box mb={2}>
                      <Chip
                        label={store.system_type}
                        color='primary'
                        size='small'
                        sx={{ mb: 1, mr: 1 }}
                      />
                      <Chip
                        label={store.sync_enabled ? '同步启用' : '同步禁用'}
                        color={store.sync_enabled ? 'success' : 'default'}
                        size='small'
                        sx={{ mb: 1, mr: 1 }}
                      />
                      <Chip
                        label={
                          store.webhook_enabled ? 'Webhook启用' : 'Webhook禁用'
                        }
                        color={store.webhook_enabled ? 'info' : 'default'}
                        size='small'
                        sx={{ mb: 1 }}
                      />
                    </Box>

                    {store.base_url && (
                      <Typography variant='body2' color='text.secondary' mb={1}>
                        URL: {store.base_url}
                      </Typography>
                    )}

                    {store.external_id && (
                      <Typography variant='body2' color='text.secondary' mb={1}>
                        ID: {store.external_id}
                      </Typography>
                    )}

                    <Typography variant='body2' color='text.secondary' mb={1}>
                      创建时间: {formatDate(store.created_at)}
                    </Typography>

                    {store.last_sync_at && (
                      <Typography variant='body2' color='text.secondary' mb={2}>
                        最后同步: {formatDate(store.last_sync_at)}
                      </Typography>
                    )}

                    <Box display='flex' gap={1} flexWrap='wrap'>
                      <IconButton
                        size='small'
                        onClick={() => handleTestConnection(store)}
                        color='info'
                        disabled={!store.external_id}
                        title={store.external_id ? '测试连接' : '该店铺未配置 external_id，无法测试连接'}
                      >
                        <TestConnectionIcon />
                      </IconButton>
                      <IconButton
                        size='small'
                        onClick={() => handleViewProducts(store)}
                        color='secondary'
                        disabled={!store.external_id}
                        title={store.external_id ? '查看商品' : '该店铺未配置 external_id，无法查看商品'}
                      >
                        <InventoryIcon />
                      </IconButton>
                      <IconButton
                        size='small'
                        onClick={() => handleViewOrders(store)}
                        color='warning'
                        disabled={!store.external_id}
                        title={store.external_id ? '查看订单' : '该店铺未配置 external_id，无法查看订单'}
                      >
                        <ShoppingCartIcon />
                      </IconButton>
                      <IconButton
                        size='small'
                        onClick={() => handleSyncOrders(store)}
                        color='success'
                        disabled={!store.external_id || (store.external_id ? syncingOrders[store.external_id] : false)}
                        title={store.external_id ? '同步订单到数据库' : '该店铺未配置 external_id，无法同步订单'}
                      >
                        {store.external_id && syncingOrders[store.external_id] ? (
                          <CircularProgress size={16} />
                        ) : (
                          <SyncIcon />
                        )}
                      </IconButton>
                      <IconButton
                        size='small'
                        onClick={() => handleEditStore(store)}
                        color='primary'
                        title='编辑'
                      >
                        <EditIcon />
                      </IconButton>
                      <IconButton
                        size='small'
                        onClick={() => handleDeleteStore(store.id)}
                        color='error'
                        title='删除'
                      >
                        <DeleteIcon />
                      </IconButton>
                    </Box>
                  </CardContent>
                </Card>
              </Box>
            ))}
          </Box>

          {/* Empty State */}
          {stores.length === 0 && !loading && (
            <Box textAlign='center' py={8}>
              <StoreIcon
                sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }}
              />
              <Typography variant='h6' color='text.secondary' gutterBottom>
                暂无 Shopify 店铺
              </Typography>
              <Typography variant='body2' color='text.secondary' mb={3}>
                点击&ldquo;添加店铺&rdquo;按钮来连接您的第一个 Shopify 店铺
              </Typography>
              <Button
                variant='contained'
                startIcon={<AddIcon />}
                onClick={handleAddStore}
              >
                添加店铺
              </Button>
            </Box>
          )}

          {/* Add/Edit Dialog */}
          <Dialog
            open={openDialog}
            onClose={() => setOpenDialog(false)}
            maxWidth='md'
            fullWidth
          >
            <DialogTitle>
              {editingStore ? '编辑 Shopify 店铺' : '添加新 Shopify 店铺'}
            </DialogTitle>
            <DialogContent>
              <Box sx={{ mt: 2 }}>
                {/* Basic Information */}
                <Accordion defaultExpanded>
                  <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                    <Typography variant='h6'>基本信息</Typography>
                  </AccordionSummary>
                  <AccordionDetails>
                    <Grid container spacing={2}>
                      <Grid item xs={12}>
                        <TextField
                          fullWidth
                          label='店铺名称'
                          value={formData.name}
                          onChange={e =>
                            setFormData({ ...formData, name: e.target.value })
                          }
                          required
                        />
                      </Grid>
                      <Grid item xs={12} sm={6}>
                        <TextField
                          fullWidth
                          label='外部ID'
                          value={formData.external_id}
                          onChange={e =>
                            setFormData({
                              ...formData,
                              external_id: e.target.value,
                            })
                          }
                          placeholder='例如: x0ri77-4v'
                        />
                      </Grid>
                      <Grid item xs={12} sm={6}>
                        <TextField
                          fullWidth
                          label='店铺URL'
                          value={formData.base_url}
                          onChange={e =>
                            setFormData({
                              ...formData,
                              base_url: e.target.value,
                            })
                          }
                          placeholder='例如: https://x0ri77-4v.myshopify.com'
                        />
                      </Grid>
                    </Grid>
                  </AccordionDetails>
                </Accordion>

                {/* API Credentials */}
                <Accordion>
                  <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                    <Box display='flex' alignItems='center'>
                      <SecurityIcon sx={{ mr: 1 }} />
                      <Typography variant='h6'>API 连接信息</Typography>
                    </Box>
                  </AccordionSummary>
                  <AccordionDetails>
                    <Grid container spacing={2}>
                      <Grid item xs={12}>
                        <TextField
                          fullWidth
                          label='Access Token'
                          type='password'
                          value={formData.credentials.access_token}
                          onChange={e =>
                            setFormData({
                              ...formData,
                              credentials: {
                                ...formData.credentials,
                                access_token: e.target.value,
                              },
                            })
                          }
                          placeholder='shpat_...'
                        />
                      </Grid>
                      <Grid item xs={12} sm={6}>
                        <TextField
                          fullWidth
                          label='Shop ID'
                          value={formData.credentials.shop_id}
                          onChange={e =>
                            setFormData({
                              ...formData,
                              credentials: {
                                ...formData.credentials,
                                shop_id: e.target.value,
                              },
                            })
                          }
                          placeholder='例如: x0ri77-4v'
                        />
                      </Grid>
                      <Grid item xs={12} sm={6}>
                        <TextField
                          fullWidth
                          label='Store URL'
                          value={formData.credentials.store_url}
                          onChange={e =>
                            setFormData({
                              ...formData,
                              credentials: {
                                ...formData.credentials,
                                store_url: e.target.value,
                              },
                            })
                          }
                          placeholder='例如: https://x0ri77-4v.myshopify.com'
                        />
                      </Grid>
                      <Grid item xs={12} sm={6}>
                        <TextField
                          fullWidth
                          label='API Key'
                          type='password'
                          value={formData.credentials.api_key}
                          onChange={e =>
                            setFormData({
                              ...formData,
                              credentials: {
                                ...formData.credentials,
                                api_key: e.target.value,
                              },
                            })
                          }
                        />
                      </Grid>
                      <Grid item xs={12} sm={6}>
                        <TextField
                          fullWidth
                          label='API Secret'
                          type='password'
                          value={formData.credentials.api_secret}
                          onChange={e =>
                            setFormData({
                              ...formData,
                              credentials: {
                                ...formData.credentials,
                                api_secret: e.target.value,
                              },
                            })
                          }
                        />
                      </Grid>
                    </Grid>
                  </AccordionDetails>
                </Accordion>

                {/* Settings */}
                <Accordion>
                  <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                    <Box display='flex' alignItems='center'>
                      <SettingsIcon sx={{ mr: 1 }} />
                      <Typography variant='h6'>配置设置</Typography>
                    </Box>
                  </AccordionSummary>
                  <AccordionDetails>
                    <Grid container spacing={2}>
                      <Grid item xs={12} sm={6}>
                        <FormControl fullWidth>
                          <InputLabel>API 版本</InputLabel>
                          <Select
                            value={formData.settings.api_version}
                            onChange={e =>
                              setFormData({
                                ...formData,
                                settings: {
                                  ...formData.settings,
                                  api_version: e.target.value,
                                },
                              })
                            }
                          >
                            <MenuItem value='2024-10'>2024-10</MenuItem>
                            <MenuItem value='2024-07'>2024-07</MenuItem>
                            <MenuItem value='2024-04'>2024-04</MenuItem>
                            <MenuItem value='unstable'>unstable</MenuItem>
                          </Select>
                        </FormControl>
                      </Grid>
                      <Grid item xs={12} sm={6}>
                        <FormControlLabel
                          control={
                            <Switch
                              checked={formData.is_active}
                              onChange={e =>
                                setFormData({
                                  ...formData,
                                  is_active: e.target.checked,
                                })
                              }
                            />
                          }
                          label='激活状态'
                        />
                      </Grid>
                      <Grid item xs={12} sm={6}>
                        <FormControlLabel
                          control={
                            <Switch
                              checked={formData.sync_enabled}
                              onChange={e =>
                                setFormData({
                                  ...formData,
                                  sync_enabled: e.target.checked,
                                })
                              }
                            />
                          }
                          label='启用同步'
                        />
                      </Grid>
                      <Grid item xs={12} sm={6}>
                        <FormControlLabel
                          control={
                            <Switch
                              checked={formData.webhook_enabled}
                              onChange={e =>
                                setFormData({
                                  ...formData,
                                  webhook_enabled: e.target.checked,
                                })
                              }
                            />
                          }
                          label='启用 Webhook'
                        />
                      </Grid>
                    </Grid>
                  </AccordionDetails>
                </Accordion>
              </Box>
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setOpenDialog(false)}>取消</Button>
              <Button 
                onClick={handleTestConnectionFromForm} 
                variant='outlined'
                color='info'
                disabled={!formData.credentials.shop_id || !formData.credentials.access_token}
                startIcon={<TestConnectionIcon />}
              >
                测试连接
              </Button>
              <Button onClick={handleSaveStore} variant='contained'>
                {editingStore ? '更新' : '添加'}
              </Button>
            </DialogActions>
          </Dialog>

          {/* Products Dialog */}
          <Dialog 
            open={openProductsDialog} 
            onClose={() => setOpenProductsDialog(false)}
            maxWidth="lg"
            fullWidth
          >
            <DialogTitle>
              商品列表 - {selectedStore?.name}
            </DialogTitle>
            <DialogContent>
              {loadingProducts ? (
                <Box display="flex" justifyContent="center" p={3}>
                  <CircularProgress />
                </Box>
              ) : (
                <Box>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    共 {products.length} 个商品
                  </Typography>
                  {products.length > 0 ? (
                    <Box sx={{ maxHeight: 400, overflow: 'auto' }}>
                      {products.map((product, index) => (
                        <Card key={product.id || index} sx={{ mb: 2, p: 2 }}>
                          <Typography variant="h6" gutterBottom>
                            {product.title}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            ID: {product.id}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            状态: {product.status}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            库存: {product.total_inventory}
                          </Typography>
                          {product.price && (
                            <Typography variant="body2" color="text.secondary">
                              价格: {product.price} {product.currency}
                            </Typography>
                          )}
                          <Typography variant="body2" color="text.secondary">
                            创建时间: {new Date(product.created_at).toLocaleString()}
                          </Typography>
                        </Card>
                      ))}
                    </Box>
                  ) : (
                    <Typography variant="body2" color="text.secondary">
                      暂无商品数据
                    </Typography>
                  )}
                </Box>
              )}
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setOpenProductsDialog(false)}>关闭</Button>
            </DialogActions>
          </Dialog>

          {/* Orders Dialog */}
          <Dialog 
            open={openOrdersDialog} 
            onClose={() => setOpenOrdersDialog(false)}
            maxWidth="lg"
            fullWidth
          >
            <DialogTitle>
              订单列表 - {selectedStore?.name}
            </DialogTitle>
            <DialogContent>
              {loadingOrders ? (
                <Box display="flex" justifyContent="center" p={3}>
                  <CircularProgress />
                </Box>
              ) : (
                <Box>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    共 {orders.length} 个订单
                  </Typography>
                  {orders.length > 0 ? (
                    <Box sx={{ maxHeight: 400, overflow: 'auto' }}>
                      {orders.map((order, index) => (
                        <Card key={order.id || index} sx={{ mb: 2, p: 2 }}>
                          <Typography variant="h6" gutterBottom>
                            {order.name}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            ID: {order.id}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            邮箱: {order.email || 'N/A'}
                          </Typography>
                          {order.total_price && (
                            <Typography variant="body2" color="text.secondary">
                              总金额: {order.total_price} {order.currency}
                            </Typography>
                          )}
                          <Typography variant="body2" color="text.secondary">
                            履行状态: {order.fulfillment_status || 'N/A'}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            财务状态: {order.financial_status || 'N/A'}
                          </Typography>
                          {order.customer && (
                            <Typography variant="body2" color="text.secondary">
                              客户: {order.customer.name || order.customer.email}
                            </Typography>
                          )}
                          <Typography variant="body2" color="text.secondary">
                            商品数量: {order.line_items_count}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            创建时间: {new Date(order.created_at).toLocaleString()}
                          </Typography>
                          
                          {/* 发货地址信息 */}
                          {order.shipping_address && (
                            <Box sx={{ mt: 2, p: 1, bgcolor: 'grey.50', borderRadius: 1 }}>
                              <Typography variant="subtitle2" color="primary" gutterBottom>
                                发货地址:
                              </Typography>
                              <Typography variant="body2" color="text.secondary">
                                {order.shipping_address.firstName} {order.shipping_address.lastName}
                              </Typography>
                              {order.shipping_address.company && (
                                <Typography variant="body2" color="text.secondary">
                                  {order.shipping_address.company}
                                </Typography>
                              )}
                              <Typography variant="body2" color="text.secondary">
                                {order.shipping_address.address1}
                              </Typography>
                              {order.shipping_address.address2 && (
                                <Typography variant="body2" color="text.secondary">
                                  {order.shipping_address.address2}
                                </Typography>
                              )}
                              <Typography variant="body2" color="text.secondary">
                                {order.shipping_address.city}, {order.shipping_address.province} {order.shipping_address.zip}
                              </Typography>
                              <Typography variant="body2" color="text.secondary">
                                {order.shipping_address.country}
                              </Typography>
                              {order.shipping_address.phone && (
                                <Typography variant="body2" color="text.secondary">
                                  电话: {order.shipping_address.phone}
                                </Typography>
                              )}
                            </Box>
                          )}
                          
                          {/* 账单地址信息 */}
                          {order.billing_address && (
                            <Box sx={{ mt: 1, p: 1, bgcolor: 'grey.50', borderRadius: 1 }}>
                              <Typography variant="subtitle2" color="primary" gutterBottom>
                                账单地址:
                              </Typography>
                              <Typography variant="body2" color="text.secondary">
                                {order.billing_address.firstName} {order.billing_address.lastName}
                              </Typography>
                              {order.billing_address.company && (
                                <Typography variant="body2" color="text.secondary">
                                  {order.billing_address.company}
                                </Typography>
                              )}
                              <Typography variant="body2" color="text.secondary">
                                {order.billing_address.address1}
                              </Typography>
                              {order.billing_address.address2 && (
                                <Typography variant="body2" color="text.secondary">
                                  {order.billing_address.address2}
                                </Typography>
                              )}
                              <Typography variant="body2" color="text.secondary">
                                {order.billing_address.city}, {order.billing_address.province} {order.billing_address.zip}
                              </Typography>
                              <Typography variant="body2" color="text.secondary">
                                {order.billing_address.country}
                              </Typography>
                              {order.billing_address.phone && (
                                <Typography variant="body2" color="text.secondary">
                                  电话: {order.billing_address.phone}
                                </Typography>
                              )}
                            </Box>
                          )}
                        </Card>
                      ))}
                    </Box>
                  ) : (
                    <Typography variant="body2" color="text.secondary">
                      暂无订单数据
                    </Typography>
                  )}
                </Box>
              )}
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setOpenOrdersDialog(false)}>关闭</Button>
            </DialogActions>
          </Dialog>

          {/* Test Result Dialog */}
          <Dialog
            open={showTestResultDialog}
            onClose={() => setShowTestResultDialog(false)}
            maxWidth="md"
            fullWidth
          >
            <DialogTitle>
              {testResult?.success ? '✅ 连接测试成功' : '❌ 连接测试失败'}
            </DialogTitle>
            <DialogContent>
              {testResult && (
                <Box>
                  <Alert 
                    severity={testResult.success ? 'success' : 'error'} 
                    sx={{ mb: 2 }}
                  >
                    <Typography variant="h6" sx={{ mb: 1 }}>
                      {testResult.success ? '连接测试成功！' : '连接测试失败'}
                    </Typography>
                    <Typography variant="body2">
                      {testResult.message}
                    </Typography>
                  </Alert>
                  
                  {testResult.shop_info && (
                    <Box>
                      <Typography variant="h6" sx={{ mb: 1 }}>
                        店铺信息：
                      </Typography>
                      <Box sx={{ pl: 2 }}>
                        <Typography variant="body2" sx={{ mb: 1 }}>
                          <strong>名称：</strong>{testResult.shop_info.name || 'N/A'}
                        </Typography>
                        <Typography variant="body2" sx={{ mb: 1 }}>
                          <strong>域名：</strong>{testResult.shop_info.myshopify_domain || 'N/A'}
                        </Typography>
                        <Typography variant="body2" sx={{ mb: 1 }}>
                          <strong>邮箱：</strong>{testResult.shop_info.email || 'N/A'}
                        </Typography>
                        <Typography variant="body2" sx={{ mb: 1 }}>
                          <strong>货币：</strong>{testResult.shop_info.currency_code || 'N/A'}
                        </Typography>
                        <Typography variant="body2" sx={{ mb: 1 }}>
                          <strong>计划：</strong>{testResult.shop_info.plan || 'N/A'}
                        </Typography>
                      </Box>
                    </Box>
                  )}
                </Box>
              )}
            </DialogContent>
            <DialogActions>
              <Button 
                onClick={() => setShowTestResultDialog(false)}
                variant="contained"
                color="primary"
              >
                确定
              </Button>
            </DialogActions>
          </Dialog>

          {/* Sync Result Dialog */}
          <Dialog
            open={showSyncResultDialog}
            onClose={() => setShowSyncResultDialog(false)}
            maxWidth="md"
            fullWidth
          >
            <DialogTitle>
              {syncResult?.success ? '✅ 同步成功' : '❌ 同步失败'}
            </DialogTitle>
            <DialogContent>
              {syncResult && (
                <Box>
                  <Alert 
                    severity={syncResult.success ? 'success' : 'error'} 
                    sx={{ mb: 2 }}
                  >
                    <Typography variant="h6" sx={{ mb: 1 }}>
                      {syncResult.success ? '同步成功！' : '同步失败'}
                    </Typography>
                    <Typography variant="body2">
                      {syncResult.message}
                    </Typography>
                  </Alert>
                  
                  {syncResult.success && (
                    <Box>
                      <Typography variant="h6" sx={{ mb: 1 }}>
                        同步统计：
                      </Typography>
                      <Box sx={{ pl: 2 }}>
                        <Typography variant="body2" sx={{ mb: 1 }}>
                          <strong>新增订单：</strong>{syncResult.orders_synced || 0}
                        </Typography>
                        <Typography variant="body2" sx={{ mb: 1 }}>
                          <strong>更新订单：</strong>{syncResult.orders_updated || 0}
                        </Typography>
                        <Typography variant="body2" sx={{ mb: 1 }}>
                          <strong>总处理：</strong>{syncResult.total_processed || 0}
                        </Typography>
                      </Box>
                    </Box>
                  )}
                </Box>
              )}
            </DialogContent>
            <DialogActions>
              <Button 
                onClick={() => setShowSyncResultDialog(false)}
                variant="contained"
                color="primary"
              >
                确定
              </Button>
            </DialogActions>
          </Dialog>
        </Box>
      </DashboardLayout>
    </ProtectedRoute>
  );
}
