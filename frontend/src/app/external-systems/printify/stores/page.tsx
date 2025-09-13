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
  Business as PrintifyIcon,
} from '@mui/icons-material';
import { frontendApi } from '@/lib/api';
import { frontendLogger } from '@/lib/frontend-logger';

interface PrintifyStore {
  // 安全原则：前端不接收数据库主键 ID
  id_hashid: string;  // 使用 hashids 作为唯一标识
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

function PrintifyStoresPage() {
  const [stores, setStores] = useState<PrintifyStore[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [openDialog, setOpenDialog] = useState(false);
  const [editingStore, setEditingStore] = useState<PrintifyStore | null>(null);
  const [openProductsDialog, setOpenProductsDialog] = useState(false);
  const [openOrdersDialog, setOpenOrdersDialog] = useState(false);
  const [selectedStore, setSelectedStore] = useState<PrintifyStore | null>(null);
  const [products, setProducts] = useState<any[]>([]);
  const [orders, setOrders] = useState<any[]>([]);
  const [loadingProducts, setLoadingProducts] = useState(false);
  const [loadingOrders, setLoadingOrders] = useState(false);
  const [syncingOrders, setSyncingOrders] = useState<Record<string, boolean>>({});
  const [formData, setFormData] = useState({
    name: '',
    external_id: '',
    base_url: 'https://api.printify.com',
    credentials: {
      access_token: '',
      shop_id: '',
      store_url: '',
      api_key: '',
      api_secret: '',
    },
    settings: {
      api_version: 'v1',
      default_shipping_method: 1,
      send_shipping_notification: true,
      default_status: 'onhold',
    },
    sync_enabled: false,
    webhook_enabled: false,
  });
  const [submitting, setSubmitting] = useState(false);
  const [testResult, setTestResult] = useState<{
    success: boolean;
    message: string;
    details?: any;
  } | null>(null);
  const [testingConnection, setTestingConnection] = useState(false);
  const [forceRender, setForceRender] = useState(0);
  const [showTestResultDialog, setShowTestResultDialog] = useState(false);

  // Mock data for demonstration - using real Printify data
  const mockStores: PrintifyStore[] = [
    {
      id_hashid: 'mock-hashid-1',
      name: 'Impeach Printify Store',
      system_type: 'PRINTIFY',
      external_id: '21704929',
      base_url: 'https://api.printify.com',
      credentials: {
        access_token: 'eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiIzN2Q0YmQzMDM1ZmUxMWU5YTgwM2FiN2VlYjNjY2M5NyIsImp0aSI6ImRmOTFhMmExMWQ4MjMwMDliMmIwNTIyOTI1OGRlOTJlYzdiN2I2MTM4YzgwZmU4MThkZDY3Mzg1OTFiZjkwOGJmZjhhYmEwMjFiY2E5NTdjIiwiaWF0IjoxNzU3MjQxMTAyLjMzNjYzNCwibmJmIjoxNzU3MjQxMTAyLjMzNjYzNiwiZXhwIjoxNzg4Nzc3MTAyLjMyODEyOCwic3ViIjoiMjI3MDE2NDQiLCJzY29wZXMiOlsic2hvcHMubWFuYWdlIiwic2hvcHMucmVhZCIsImNhdGFsb2cucmVhZCIsIm9yZGVycy5yZWFkIiwib3JkZXJzLndyaXRlIiwicHJvZHVjdHMucmVhZCIsInByb2R1Y3RzLndyaXRlIiwid2ViaG9va3MucmVhZCIsIndlYmhvb2tzLndyaXRlIiwidXBsb2Fkcy5yZWFkIiwidXBsb2Fkcy53cml0ZSIsInByaW50X3Byb3ZpZGVycy5yZWFkIiwidXNlci5pbmZvIl19.hyw5rw-PS0qh8EgPAIV9O_2aSAiScYfuXjdLDAJnNfpwbzdfDBq3gkmYPM8kMnUp_X_KZ5flG7qF5iNqdYmlvOvZsUcCtZk7FoTZ7DBVz4Z_gSweY7IwDudPn1NyujWSPoIdu4XE_-5UGsmzYNJaCItJnwG5Uaz0XJeV4tMcKAN_yuYXaDeQHKZtByCru-uGk6JfIy1vooLalFMUXhf6cFCOeeX3YgSX0c9IfC8-vazrdBpgxs119mmIISV1ch1C4KrqE3maIB-GXh26rkDNCSCqoPurOZVsHqGm-ZH7sXTnmx-Lmz0q7GoulqTxpUFYfleS-xBhgPL2vgFnI8Sh2LUBkCmlcWqEnIerLwROp9tRqTr5qJyGkaHjG7fYD2COwlba-hCaS43LlqY571MEia_r7M97KZ8eeZVqY42SYiJP7FXihduU_HyEj5G3GKKUZmsX7xOlsIBqc81V2VYRR6pr0C782TD21QdigMuDlwEKyVXjMhDPVmIf4jXIZB64JDBA-SM4Z7Kqrc5oZoBIueCqbGhzKTYv3aP8bC8pdOWa_U1wm0JX4UsWo7sRtjlhRPR98SvyGMEYVEH0rVeLFwx2bfBrDShgjYqdlYfDaXY8gvbaiOFS_0BlVsY9mCzbchkldIOfry8N2igUycM_-HdH3mt95UCGzUD-RETTaGU',
        shop_id: '21704929',
      },
      settings: {
        api_version: 'v1',
        default_shipping_method: 1,
        send_shipping_notification: true,
        default_status: 'onhold',
      },
      is_active: true,
      sync_enabled: false,
      webhook_enabled: false,
      last_sync_at: undefined,
      created_at: '2025-01-11T00:00:00Z',
    },
  ];

  useEffect(() => {
    fetchStores();
  }, []);

  const fetchStores = async () => {
    try {
      setLoading(true);
      setError(null);
      
      console.log('🚀 开始获取 Printify 店铺列表');
      
      // Call real API to get external systems filtered by PRINTIFY
      const response = await frontendApi.get('/api/external-systems?system_type=printify');
      
      console.log('📦 Printify 店铺列表响应:', response.data);
      
      if (response.data.external_systems) {
        // Debug: Log the first system to check if id_hashid is present
        if (response.data.external_systems.length > 0) {
          const firstSystem = response.data.external_systems[0];
          console.log('🔍 检查后端返回的系统数据:', {
            id: firstSystem.id,
            id_hashid: firstSystem.id_hashid,
            name: firstSystem.name,
            system_type: firstSystem.system_type,
            hasIdHashid: !!firstSystem.id_hashid
          });
        }
        
        // Convert backend format to frontend format
        const printifyStores = response.data.external_systems.map((system: any) => ({
          // 安全原则：前端不接收数据库主键 ID，只使用 hashids
          id_hashid: system.id_hashid,  // 使用 hashids 作为唯一标识
          name: system.name,
          system_type: system.system_type,
          external_id: system.external_system_id,
          base_url: system.base_url,
          credentials: system.credentials || {},
          settings: system.settings || {},
          is_active: system.is_active,
          sync_enabled: system.settings?.sync_enabled || false,
          webhook_enabled: system.settings?.webhook_enabled || false,
          last_sync_at: system.last_sync_at,
          created_at: system.created_at,
        }));
        
        setStores(printifyStores);
        console.log('✅ 成功获取 Printify 店铺列表，数量:', printifyStores.length);
      } else {
        console.log('⚠️ 没有找到 Printify 店铺，使用模拟数据');
        setStores(mockStores);
      }
    } catch (err: any) {
      console.error('❌ 获取 Printify 店铺列表失败:', err);
      setError(err.response?.data?.detail || 'Failed to fetch Printify stores');
      // Use mock data as fallback
      console.log('🔄 使用模拟数据作为备选');
      setStores(mockStores);
    } finally {
      setLoading(false);
    }
  };

  const handleAddStore = () => {
    setEditingStore(null);
    handleResetForm();
    setOpenDialog(true);
  };

  const handleEditStore = (store: PrintifyStore) => {
    setEditingStore(store);
    setFormData({
      name: store.name,
      external_id: store.external_id || '',
      base_url: store.base_url || 'https://api.printify.com',
      credentials: {
        access_token: store.credentials.access_token || '',
        shop_id: store.credentials.shop_id || '',
        store_url: store.credentials.store_url || '',
        api_key: store.credentials.api_key || '',
        api_secret: store.credentials.api_secret || '',
      },
      settings: {
        api_version: store.settings.api_version || 'v1',
        default_shipping_method: store.settings.default_shipping_method || 1,
        send_shipping_notification: store.settings.send_shipping_notification || true,
        default_status: store.settings.default_status || 'onhold',
      },
      sync_enabled: store.sync_enabled,
      webhook_enabled: store.webhook_enabled,
    });
    setTestResult(null);
    setOpenDialog(true);
  };

  const handleDeleteStore = async (storeId: string) => {
    if (window.confirm('确定要删除这个店铺吗？')) {
      try {
        // API call to delete store
        setStores(stores.filter(store => store.id_hashid !== storeId));
      } catch (err) {
        console.error('Failed to delete store:', err);
        setError('删除店铺失败');
      }
    }
  };

  const handleTestConnection = async (store: PrintifyStore) => {
    try {
      setTestResult(null);
      
      // For Printify, we use shop_id from credentials instead of external_id
      const shopId = store.credentials?.shop_id;
      if (!shopId) {
        setError('该店铺未配置 shop_id，无法测试连接。');
        return;
      }
      
      // Call real Printify API test connection
      const response = await frontendApi.post('/api/external-systems/printify/test-connection', {
        access_token: store.credentials.access_token,
        shop_id: shopId,
        base_url: store.base_url,
      });
      
      if (response.data.success) {
        setTestResult({
          success: true,
          message: response.data.message || '连接测试成功！',
          details: {
            shop_id: response.data.shop_id,
            base_url: response.data.base_url,
            shops_count: response.data.shops_count,
            shops: response.data.shops,
          }
        });
        setShowTestResultDialog(true);
      } else {
        setTestResult({
          success: false,
          message: response.data.message || '连接测试失败',
          details: {
            error_code: response.data.error_code,
            error_details: response.data.error_details,
          }
        });
        setShowTestResultDialog(true);
      }
    } catch (err: any) {
      console.error('Printify test connection failed:', err);
      setTestResult({
        success: false,
        message: err.response?.data?.detail || '连接测试失败',
        details: {
          error: err.message,
        }
      });
      setShowTestResultDialog(true);
    }
  };

  const handleViewProducts = async (store: PrintifyStore) => {
    // Use id_hashid instead of shop_id
    const externalSystemHashid = store.id_hashid;
    if (!externalSystemHashid) {
      const errorMsg = '该店铺缺少系统 ID，无法获取商品列表。';
      frontendLogger.error('❌ Printify 商品获取失败 - 缺少系统ID', {
        // 页面和组件信息
        page: 'PrintifyStoresPage',
        component: 'handleViewProducts',
        action: 'view_products',
        button: '查看商品按钮',
        
        // 店铺信息
        storeName: store.name,
        id_hashid: store.id_hashid,
        systemType: store.system_type,
        
        // 错误详情
        error: errorMsg,
        errorType: 'MISSING_SYSTEM_ID',
        
        // 用户操作上下文
        userAction: '点击查看商品按钮',
        scenario: '用户尝试查看Printify店铺的商品列表',
        
        // 技术上下文
        timestamp: new Date().toISOString(),
        userAgent: navigator.userAgent,
        url: window.location.href
      });
      setError(errorMsg);
      return;
    }

    try {
      setLoadingProducts(true);
      setSelectedStore(store);
      
      frontendLogger.info('🚀 开始获取 Printify 商品列表', { 
        storeName: store.name,
        id_hashid: store.id_hashid,
        externalSystemHashid 
      });
      
      // Call real API using hashid
      const response = await frontendApi.get(`/api/external-systems/printify/${externalSystemHashid}/products`);
      
      frontendLogger.info('📦 Printify 商品列表响应', {
        success: response.data.success,
        hasProducts: !!response.data.products,
        productsCount: response.data.products?.length || 0,
        totalCount: response.data.total_count
      });
      
      if (response.data.success) {
        setProducts(response.data.products || []);
        setOpenProductsDialog(true);
        frontendLogger.info('✅ 成功获取商品列表', {
          count: response.data.total_count,
          storeName: store.name
        });
      } else {
        const errorMsg = '获取商品列表失败: ' + response.data.message;
        frontendLogger.error('❌ 获取商品列表失败', {
          storeName: store.name,
          id_hashid: store.id_hashid,
          response: response.data
        });
        setError(errorMsg);
      }
    } catch (err: any) {
      frontendLogger.error('❌ 获取商品列表异常', {
        storeName: store.name,
        id_hashid: store.id_hashid,
        externalSystemHashid,
        error: err.message,
        response: err.response?.data
      });
      setError('获取商品列表失败: ' + (err.response?.data?.detail || err.message));
    } finally {
      setLoadingProducts(false);
    }
  };

  const handleViewOrders = async (store: PrintifyStore) => {
    // For Printify, we use id_hashid for API calls
    const externalSystemHashid = store.id_hashid;
    if (!externalSystemHashid) {
      const errorMsg = '该店铺缺少系统 ID，无法获取订单列表。';
      frontendLogger.error('❌ Printify 订单获取失败 - 缺少系统ID', {
        // 页面和组件信息
        page: 'PrintifyStoresPage',
        component: 'handleViewOrders',
        action: 'view_orders',
        button: '查看订单按钮',
        
        // 店铺信息
        storeName: store.name,
        id_hashid: store.id_hashid,
        systemType: store.system_type,
        
        // 错误详情
        error: errorMsg,
        errorType: 'MISSING_SYSTEM_ID',
        
        // 用户操作上下文
        userAction: '点击查看订单按钮',
        scenario: '用户尝试查看Printify店铺的订单列表',
        
        // 技术上下文
        timestamp: new Date().toISOString(),
        userAgent: navigator.userAgent,
        url: window.location.href
      });
      setError(errorMsg);
      return;
    }

    try {
      setLoadingOrders(true);
      setSelectedStore(store);
      
      frontendLogger.info('🚀 开始获取 Printify 订单列表', { 
        // 页面和组件信息
        page: 'PrintifyStoresPage',
        component: 'handleViewOrders',
        action: 'view_orders',
        button: '查看订单按钮',
        
        // 店铺信息
        storeName: store.name, 
        id_hashid: store.id_hashid,
        externalSystemHashid,
        systemType: store.system_type,
        
        // 用户操作上下文
        userAction: '点击查看订单按钮',
        scenario: '用户查看Printify店铺的订单列表',
        
        // API调用信息
        apiEndpoint: `/api/external-systems/printify/${externalSystemHashid}/orders`,
        requestParams: { limit: 50, page: 1 }
      });
      
      // Call real Printify API
      const response = await frontendApi.get(
        `/api/external-systems/printify/${externalSystemHashid}/orders?limit=50&page=1`
      );
      
      frontendLogger.info('📡 Printify 订单 API 响应', {
        success: response.data.success,
        hasOrders: !!response.data.orders,
        ordersCount: response.data.orders?.length || 0,
        totalCount: response.data.total_count
      });
      
      if (response.data.success && response.data.orders) {
        setOrders(response.data.orders);
        setOpenOrdersDialog(true);
        frontendLogger.info('✅ Printify 订单列表获取成功', { 
          count: response.data.orders.length,
          total: response.data.total_count,
          storeName: store.name
        });
      } else {
        throw new Error(response.data.message || '获取订单列表失败');
      }
    } catch (err: any) {
      frontendLogger.error('❌ 获取 Printify 订单列表失败', {
        // 页面和组件信息
        page: 'PrintifyStoresPage',
        component: 'handleViewOrders',
        action: 'view_orders',
        button: '查看订单按钮',
        
        // 店铺信息
        storeName: store.name,
        id_hashid: store.id_hashid,
        externalSystemHashid,
        systemType: store.system_type,
        
        // 错误详情
        error: err.message,
        errorType: 'API_CALL_FAILED',
        errorCode: err.response?.status,
        response: err.response?.data,
        
        // 用户操作上下文
        userAction: '点击查看订单按钮',
        scenario: '用户查看Printify店铺的订单列表时API调用失败',
        
        // API调用信息
        apiEndpoint: `/api/external-systems/printify/${externalSystemHashid}/orders`,
        requestParams: { limit: 50, page: 1 },
        
        // 技术上下文
        timestamp: new Date().toISOString(),
        userAgent: navigator.userAgent,
        url: window.location.href
      });
      setError('获取订单列表失败: ' + (err.response?.data?.detail || err.message));
    } finally {
      setLoadingOrders(false);
    }
  };

  const handleSyncOrders = async (store: PrintifyStore) => {
    // For Printify, we use shop_id from credentials instead of external_id
    const shopId = store.credentials?.shop_id;
    if (!shopId) {
      setError('该店铺未配置 shop_id，无法同步订单。');
      return;
    }

    try {
      setSyncingOrders(prev => ({ ...prev, [shopId]: true }));
      
      // Mock sync logic
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      // Update last sync time
      setStores(prev => prev.map(s => 
        s.id_hashid === store.id_hashid 
          ? { ...s, last_sync_at: new Date().toISOString() }
          : s
      ));
      
    } catch (err: any) {
      console.error('Failed to sync orders:', err);
      setError('同步订单失败: ' + (err.response?.data?.detail || err.message));
    } finally {
      setSyncingOrders(prev => ({ ...prev, [shopId]: false }));
    }
  };

  const handleCloseDialog = () => {
    setOpenDialog(false);
    setEditingStore(null);
    // Don't reset testResult here - let user see the result
  };

  const handleResetForm = () => {
    setFormData({
      name: '',
      external_id: '',
      base_url: 'https://api.printify.com',
      credentials: {
        access_token: '',
        shop_id: '',
        store_url: '',
        api_key: '',
        api_secret: '',
      },
      settings: {
        api_version: 'v1',
        default_shipping_method: 1,
        send_shipping_notification: true,
        default_status: 'onhold',
      },
      sync_enabled: false,
      webhook_enabled: false,
    });
    setTestResult(null);
  };

  const handleInputChange = (field: string) => (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const value = event.target.type === 'checkbox' 
      ? event.target.checked 
      : event.target.value;
    
    if (field.includes('.')) {
      const [parent, child] = field.split('.');
      setFormData(prev => ({
        ...prev,
        [parent]: {
          ...(prev[parent as keyof typeof prev] as any),
          [child]: value,
        },
      }));
    } else {
      setFormData(prev => ({
        ...prev,
        [field]: value,
      }));
    }
  };

  const handleTestConnectionInDialog = async () => {
    frontendLogger.info('🚀 开始测试 Printify 连接', {
      // 页面和组件信息
      page: 'PrintifyStoresPage',
      component: 'handleTestConnectionInDialog',
      action: 'test_connection',
      button: '测试连接按钮',
      
      // 表单数据信息
      hasAccessToken: !!formData.credentials.access_token,
      hasShopId: !!formData.credentials.shop_id,
      baseUrl: formData.base_url,
      storeName: formData.name,
      
      // 用户操作上下文
      userAction: '点击测试连接按钮',
      scenario: '用户在添加/编辑Printify店铺对话框中测试连接',
      
      // API调用信息
      apiEndpoint: '/api/external-systems/printify/test-connection',
      
      // 技术上下文
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent,
      url: window.location.href
    });
    
    try {
      // Clear previous result and show loading
      setTestResult(null);
      setTestingConnection(true);
      
      // Call real Printify API test connection
      console.log('📡 准备调用 API...');
      const response = await frontendApi.post('/api/external-systems/printify/test-connection', {
        access_token: formData.credentials.access_token,
        shop_id: formData.credentials.shop_id,
        base_url: formData.base_url,
      });
      
      console.log('📡 API 调用完成，响应状态:', response.status);
      console.log('📡 Printify 测试连接响应:', response.data);
      console.log('🔍 response.data.success 值:', response.data.success);
      console.log('🔍 response.data.success 类型:', typeof response.data.success);
      
      if (response.data.success) {
        const newTestResult = {
          success: true,
          message: response.data.message || '连接测试成功！',
          details: {
            shop_id: response.data.shop_id,
            base_url: response.data.base_url,
            shops_count: response.data.shops_count,
            shops: response.data.shops,
          }
        };
        
        console.log('✅ 测试连接成功，设置结果:', newTestResult);
        setTestResult(newTestResult);
        setForceRender(prev => prev + 1);
        setShowTestResultDialog(true);
        console.log('🔍 设置 showTestResultDialog 为 true');
      } else {
        console.log('🔍 进入 else 分支，success 为 false');
        const newTestResult = {
          success: false,
          message: response.data.message || '连接测试失败',
          details: {
            error_code: response.data.error_code,
            error_details: response.data.error_details,
          }
        };
        
        console.log('❌ 测试连接失败:', newTestResult);
        setTestResult(newTestResult);
        setForceRender(prev => prev + 1);
        setShowTestResultDialog(true);
        console.log('🔍 设置 showTestResultDialog 为 true (失败情况)');
      }
    } catch (err: any) {
      frontendLogger.error('❌ Printify 测试连接失败', {
        // 页面和组件信息
        page: 'PrintifyStoresPage',
        component: 'handleTestConnectionInDialog',
        action: 'test_connection',
        button: '测试连接按钮',
        
        // 表单数据信息
        hasAccessToken: !!formData.credentials.access_token,
        hasShopId: !!formData.credentials.shop_id,
        baseUrl: formData.base_url,
        storeName: formData.name,
        
        // 错误详情
        error: err.message,
        errorType: 'TEST_CONNECTION_FAILED',
        errorCode: err.response?.status,
        response: err.response?.data,
        
        // 用户操作上下文
        userAction: '点击测试连接按钮',
        scenario: '用户在添加/编辑Printify店铺对话框中测试连接失败',
        
        // API调用信息
        apiEndpoint: '/api/external-systems/printify/test-connection',
        
        // 技术上下文
        timestamp: new Date().toISOString(),
        userAgent: navigator.userAgent,
        url: window.location.href
      });
      
      const newTestResult = {
        success: false,
        message: err.response?.data?.detail || '连接测试失败',
        details: {
          error: err.message,
        }
      };
      
      setTestResult(newTestResult);
      setForceRender(prev => prev + 1);
      setShowTestResultDialog(true);
      console.log('🔍 设置 showTestResultDialog 为 true (异常情况)');
    } finally {
      setTestingConnection(false);
    }
  };

  const handleSubmit = async () => {
    try {
      setSubmitting(true);
      
      console.log('🚀 开始保存 Printify 店铺', { formData });
      
      // Prepare data for API
      const apiData = {
        system_type: 'printify',
        name: formData.name,
        external_system_id: formData.external_id,
        base_url: formData.base_url,
        credentials: formData.credentials,
        settings: formData.settings,
        webhook_url: null, // Printify doesn't use webhook_url
      };
      
      console.log('📦 API 请求数据:', apiData);
      
      // Call real API
      const response = await frontendApi.post('/api/external-systems', apiData);
      
      console.log('✅ Printify 店铺保存成功:', response.data);
      
      if (editingStore) {
        // Update existing store in local state
        setStores(prev => prev.map(store => 
          store.id_hashid === editingStore.id_hashid 
            ? {
                ...store,
                name: formData.name,
                external_id: formData.external_id,
                base_url: formData.base_url,
                credentials: formData.credentials,
                settings: formData.settings,
                sync_enabled: formData.sync_enabled,
                webhook_enabled: formData.webhook_enabled,
              }
            : store
        ));
      } else {
        // Add new store to local state
        const newStore: PrintifyStore = {
          id_hashid: response.data.id_hashid,
          name: formData.name,
          system_type: 'PRINTIFY',
          external_id: formData.external_id,
          base_url: formData.base_url,
          credentials: formData.credentials,
          settings: formData.settings,
          is_active: true,
          sync_enabled: formData.sync_enabled,
          webhook_enabled: formData.webhook_enabled,
          last_sync_at: undefined,
          created_at: new Date().toISOString(),
        };
        
        setStores(prev => [...prev, newStore]);
      }
      
      handleCloseDialog();
      
    } catch (err: any) {
      console.error('❌ 保存 Printify 店铺失败:', err);
      setError(err.response?.data?.detail || 'Failed to save Printify store');
    } finally {
      setSubmitting(false);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Box display="flex" alignItems="center">
          <PrintifyIcon sx={{ mr: 2, fontSize: 32, color: 'primary.main' }} />
          <Typography variant="h4" component="h1">
            Printify 店铺管理
          </Typography>
        </Box>
        <Box>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={fetchStores}
            sx={{ mr: 2 }}
          >
            刷新
          </Button>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={handleAddStore}
          >
            添加店铺
          </Button>
        </Box>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Box>
        {stores.map((store) => (
          <Box key={store.id_hashid} mb={3}>
            <Card>
              <CardContent>
                <Box display="flex" justifyContent="space-between" alignItems="flex-start" mb={2}>
                  <Box display="flex" alignItems="center">
                    <StoreIcon sx={{ mr: 1, color: 'primary.main' }} />
                    <Typography variant="h6" component="h2">
                      {store.name}
                    </Typography>
                    <Box ml={2}>
                      {store.is_active ? (
                        <ActiveIcon color='success' fontSize='small' />
                      ) : (
                        <InactiveIcon color='error' fontSize='small' />
                      )}
                    </Box>
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
                    disabled={!store.credentials?.access_token || !store.credentials?.shop_id}
                    title={store.credentials?.access_token && store.credentials?.shop_id ? '测试连接' : '该店铺未配置 access_token 或 shop_id，无法测试连接'}
                  >
                    <TestConnectionIcon />
                  </IconButton>
                  <IconButton
                    size='small'
                    onClick={() => handleViewProducts(store)}
                    color='secondary'
                    disabled={!store.id_hashid}
                    title={store.id_hashid ? '查看商品' : '该店铺缺少系统 ID，无法查看商品'}
                  >
                    <InventoryIcon />
                  </IconButton>
                  <IconButton
                    size='small'
                    onClick={() => handleViewOrders(store)}
                    color='warning'
                    disabled={!store.credentials?.shop_id}
                    title={store.credentials?.shop_id ? '查看订单' : '该店铺未配置 shop_id，无法查看订单'}
                  >
                    <ShoppingCartIcon />
                  </IconButton>
                  <IconButton
                    size='small'
                    onClick={() => handleSyncOrders(store)}
                    color='success'
                    disabled={!store.credentials?.shop_id || (store.credentials?.shop_id ? syncingOrders[store.credentials.shop_id] : false)}
                    title={store.credentials?.shop_id ? '同步订单到数据库' : '该店铺未配置 shop_id，无法同步订单'}
                  >
                    {store.credentials?.shop_id && syncingOrders[store.credentials.shop_id] ? (
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
                    onClick={() => handleDeleteStore(store.id_hashid)}
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
            暂无 Printify 店铺
          </Typography>
          <Typography variant='body2' color='text.secondary' mb={3}>
            点击&ldquo;添加店铺&rdquo;按钮来连接您的第一个 Printify 店铺
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
        onClose={handleCloseDialog}
        maxWidth='md'
        fullWidth
      >
        <DialogTitle>
          {editingStore ? '编辑 Printify 店铺' : '添加新 Printify 店铺'}
        </DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2 }}>
            <Grid container spacing={3}>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="店铺名称"
                  value={formData.name}
                  onChange={handleInputChange('name')}
                  placeholder="例如: 我的 Printify 店铺"
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="店铺 ID"
                  value={formData.credentials.shop_id}
                  onChange={handleInputChange('credentials.shop_id')}
                  placeholder="例如: 21704929"
                />
              </Grid>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="API Base URL"
                  value={formData.base_url}
                  onChange={handleInputChange('base_url')}
                  placeholder="https://api.printify.com"
                />
              </Grid>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="Access Token"
                  value={formData.credentials.access_token}
                  onChange={handleInputChange('credentials.access_token')}
                  placeholder="输入您的 Printify Access Token"
                  multiline
                  rows={3}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={formData.sync_enabled}
                      onChange={handleInputChange('sync_enabled')}
                    />
                  }
                  label="启用同步"
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={formData.webhook_enabled}
                      onChange={handleInputChange('webhook_enabled')}
                    />
                  }
                  label="启用 Webhook"
                />
              </Grid>
            </Grid>

            {/* Debug: Show testResult state */}
            {(() => {
              console.log('🔍 当前 testResult 状态:', testResult);
              console.log('🔍 当前 testingConnection 状态:', testingConnection);
              console.log('🔍 当前 forceRender 状态:', forceRender);
              console.log('🔍 当前 showTestResultDialog 状态:', showTestResultDialog);
              return null;
            })()}
            
            {/* Show loading state */}
            {testingConnection && (
              <Box sx={{ mt: 2, p: 2, bgcolor: 'info.light', borderRadius: 1, display: 'flex', alignItems: 'center', gap: 1 }}>
                <CircularProgress size={20} />
                <Typography variant="body2">
                  正在测试连接...
                </Typography>
              </Box>
            )}
            
            {/* Show test result */}
            {testResult && !testingConnection && (
              <Alert 
                severity={testResult.success ? 'success' : 'error'} 
                sx={{ mt: 2 }}
              >
                <Typography variant="h6" sx={{ mb: 1 }}>
                  {testResult.success ? '✅ 连接测试成功！' : '❌ 连接测试失败'}
                </Typography>
                <Typography variant="body2" sx={{ mb: 1 }}>
                  {testResult.message}
                </Typography>
                {testResult.details && (
                  <Box component="pre" sx={{ mt: 1, fontSize: '0.875rem', bgcolor: 'rgba(0,0,0,0.05)', p: 1, borderRadius: 1 }}>
                    {JSON.stringify(testResult.details, null, 2)}
                  </Box>
                )}
              </Alert>
            )}
            
            {/* Debug: Show current state */}
            <Box sx={{ mt: 2, p: 2, bgcolor: 'grey.100', borderRadius: 1 }}>
              <Typography variant="body2" color="text.secondary">
                🔍 Debug: testResult={testResult ? '有值' : 'null'}, testingConnection={testingConnection.toString()}, forceRender={forceRender}, showDialog={showTestResultDialog.toString()}
              </Typography>
            </Box>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>取消</Button>
          <Button 
            onClick={handleTestConnectionInDialog}
            variant="outlined"
            disabled={!formData.credentials.shop_id || !formData.credentials.access_token || testingConnection}
            startIcon={testingConnection ? <CircularProgress size={16} /> : null}
          >
            {testingConnection ? '测试中...' : '测试连接'}
          </Button>
          <Button 
            onClick={handleSubmit}
            variant="contained"
            disabled={submitting || !testResult?.success}
          >
            {submitting ? <CircularProgress size={20} /> : (editingStore ? '更新店铺' : '添加店铺')}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Products Dialog */}
      <Dialog
        open={openProductsDialog}
        onClose={() => setOpenProductsDialog(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          商品列表 - {selectedStore?.name}
        </DialogTitle>
        <DialogContent>
          {loadingProducts ? (
            <Box display="flex" justifyContent="center" py={4}>
              <CircularProgress />
            </Box>
          ) : (
            <Box>
              {products.map((product) => (
                <Card key={product.id} sx={{ mb: 2 }}>
                  <CardContent>
                    <Typography variant="h6">{product.title}</Typography>
                    <Typography variant="body2" color="text.secondary">
                      Handle: {product.handle}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      状态: {product.status}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      创建时间: {formatDate(product.created_at)}
                    </Typography>
                  </CardContent>
                </Card>
              ))}
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
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          订单列表 - {selectedStore?.name}
        </DialogTitle>
        <DialogContent>
          {loadingOrders ? (
            <Box display="flex" justifyContent="center" py={4}>
              <CircularProgress />
            </Box>
          ) : (
            <Box>
              {orders.map((order) => (
                <Card key={order.id} sx={{ mb: 2 }}>
                  <CardContent>
                    <Typography variant="h6">订单 #{order.order_number || order.id || 'N/A'}</Typography>
                    <Typography variant="body2" color="text.secondary">
                      状态: {order.status || '未知'}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      总价: ${order.total_price || '0.00'}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      收货地址: {order.shipping_address ? 
                        `${order.shipping_address.first_name || ''} ${order.shipping_address.last_name || ''}, ${order.shipping_address.address1 || ''}, ${order.shipping_address.city || ''}, ${order.shipping_address.country || ''}`.trim().replace(/^,\s*|,\s*$/g, '') 
                        : '无收货地址信息'}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      创建时间: {order.created_at ? formatDate(order.created_at) : '未知'}
                    </Typography>
                  </CardContent>
                </Card>
              ))}
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
              
              {testResult.details && (
                <Box>
                  <Typography variant="h6" sx={{ mb: 1 }}>
                    详细信息：
                  </Typography>
                  <Box 
                    component="pre" 
                    sx={{ 
                      bgcolor: 'grey.100', 
                      p: 2, 
                      borderRadius: 1, 
                      fontSize: '0.875rem',
                      overflow: 'auto',
                      maxHeight: '300px'
                    }}
                  >
                    {JSON.stringify(testResult.details, null, 2)}
                  </Box>
                </Box>
              )}
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowTestResultDialog(false)}>
            关闭
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default function Page() {
  return (
    <ProtectedRoute>
      <DashboardLayout>
        <PrintifyStoresPage />
      </DashboardLayout>
    </ProtectedRoute>
  );
}