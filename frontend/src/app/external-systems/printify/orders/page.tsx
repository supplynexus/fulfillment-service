'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Grid,
  Alert,
  CircularProgress,
  Tooltip,
  Pagination,
  Stack,
  Checkbox,
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  Visibility as ViewIcon,
  Search as SearchIcon,
  FilterList as FilterIcon,
  ShoppingCart as OrderIcon,
  Store as StoreIcon,
  CalendarToday as DateIcon,
  AttachMoney as PriceIcon,
  LocalShipping as ShippingIcon,
  CheckCircle as StatusIcon,
  Error as ErrorIcon,
  Info as InfoIcon,
  Save as SaveIcon,
} from '@mui/icons-material';
import { frontendApi } from '@/lib/api';
import { frontendLogger } from '@/lib/frontend-logger';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { DashboardLayout } from '@/components/layout/DashboardLayout';

// 订单状态类型
type OrderStatus = 'pending' | 'processing' | 'shipped' | 'delivered' | 'cancelled' | 'on_hold';

// Printify 订单接口
interface PrintifyOrder {
  id: string;
  app_order_id: string;
  shop_id: number;
  address_to: {
    first_name: string;
    last_name: string;
    email: string;
    phone?: string;
    country: string;
    region: string;
    city: string;
    address1: string;
    address2?: string;
    zip: string;
    company?: string;
  };
  line_items: Array<{
    id: string;
    variant_id: string;
    quantity: number;
    product_id: string;
    blueprint_id: number;
    print_provider_id: number;
    shipping_cost: number;
    cost: number;
    status: string;
    metadata: {
      title: string;
      price: number;
      variant_label: string;
      sku: string;
      country: string;
    };
  }>;
  metadata: {
    order_type: string;
    shop_order_id: string;
    shop_order_label: string;
  };
  total_price: number;
  total_shipping: number;
  total_tax: number;
  status: OrderStatus;
  shipping_method: number;
  created_at: string;
  fulfilment_type: string;
  printify_connect?: {
    url: string;
    id: string;
  };
  sales_channel_type_id: number;
  // 发货信息
  tracking_number?: string;
  tracking_url?: string;
  tracking_company?: string;
  shipped_at?: string;
  delivered_at?: string;
  fulfillment_status?: string;
  shipments?: Array<{
    carrier: string;
    number: string;
    url: string;
    delivered_at: string | null;
    shipped_at: string;
  }>;
}

// Printify 店铺接口
interface PrintifyStore {
  id_hashid: string;
  name: string;
  system_type: string;
  external_id: string;
  is_active: boolean;
}

function PrintifyOrdersPage() {
  const [orders, setOrders] = useState<PrintifyOrder[]>([]);
  const [stores, setStores] = useState<PrintifyStore[]>([]);
  const [selectedStore, setSelectedStore] = useState<PrintifyStore | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<OrderStatus | 'all'>('all');
  const [selectedOrder, setSelectedOrder] = useState<PrintifyOrder | null>(null);
  const [openOrderDialog, setOpenOrderDialog] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const [loadingOrders, setLoadingOrders] = useState(false);
  const [savingToDatabase, setSavingToDatabase] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  
  // 多选相关状态
  const [selectedOrders, setSelectedOrders] = useState<Set<string>>(new Set());
  const [updatingTracking, setUpdatingTracking] = useState(false);

  // 通过 Printify 订单 ID 查找对应的 SCM 订单
  const findScmOrderByPrintifyOrderId = async (printifyOrderId: string, customerEmail?: string, customerName?: string): Promise<number | null> => {
    try {
      frontendLogger.info('🔍 尝试查找对应的 SCM 订单', { printifyOrderId });
      
      // 通过 Printify 订单 ID 查找 SCM 订单
      // 这里我们通过订单号模式来匹配，比如 "SCM-68" 这样的模式
      const response = await frontendApi.get('/api/scm-orders/', {
        params: {
          limit: 100, // 获取更多订单以便搜索
        }
      });
      
      if (response.data && response.data.scm_orders) {
        // 查找包含 Printify 订单 ID 的 SCM 订单
        // 通过多种方式匹配：订单号、客户邮箱、客户姓名等
        const matchingOrder = response.data.scm_orders.find((order: any) => {
          // 1. 直接匹配 Printify 订单 ID
          if (order.printify_order_id === printifyOrderId || order.printify_shop_id === printifyOrderId) {
            return true;
          }
          
          // 2. 通过订单号模式匹配（SCM-68-xxx 格式）
          if (order.scm_order_number?.includes(printifyOrderId)) {
            return true;
          }
          
          // 3. 通过客户信息匹配（如果 Printify 订单有客户信息）
          if (customerEmail && order.customer_email === customerEmail) {
            return true;
          }
          if (customerName && order.customer_name === customerName) {
            return true;
          }
          
          return false;
        });
        
        if (matchingOrder) {
          frontendLogger.info('✅ 找到对应的 SCM 订单', { 
            scmOrderId: matchingOrder.id,
            scmOrderNumber: matchingOrder.scm_order_number 
          });
          return matchingOrder.id;
        }
      }
      
      frontendLogger.info('ℹ️ 未找到对应的 SCM 订单', { printifyOrderId });
      return null;
    } catch (error) {
      frontendLogger.error('❌ 查找 SCM 订单失败', { 
        error: String(error),
        printifyOrderId 
      });
      return null;
    }
  };

  // 获取店铺列表
  const fetchStores = useCallback(async () => {
    try {
      frontendLogger.info('🔍 开始获取 Printify 店铺列表');
      const response = await frontendApi.get(
        '/api/external-systems?system_type=printify'
      );

      if (response.data && response.data.external_systems) {
        const printifyStores = response.data.external_systems.filter(
          (store: any) => store.system_type === 'PRINTIFY' && store.is_active
        );
        setStores(printifyStores);
        frontendLogger.info('✅ Printify 店铺列表获取成功', {
          count: printifyStores.length,
        });

        // 如果有店铺，默认选择第一个
        if (printifyStores.length > 0) {
          setSelectedStore(printifyStores[0]);
        }
      } else {
        throw new Error('获取店铺列表失败：响应数据格式不正确');
      }
    } catch (error) {
      frontendLogger.error('❌ 获取 Printify 店铺列表失败', {
        error: String(error),
      });
      setError('获取店铺列表失败');
    }
  }, []);

  // 获取订单列表
  const fetchOrders = useCallback(async (store: PrintifyStore, page: number = 1) => {
    if (!store) return;

    try {
      setLoadingOrders(true);
      setError(null);

      frontendLogger.info('🔍 开始获取 Printify 订单列表', {
        storeId: store.id_hashid,
        storeName: store.name,
        page: page,
      });

      const response = await frontendApi.get(
        `/api/external-systems/printify/${store.id_hashid}/orders?limit=20&page=${page}`
      );

      if (response.data.success && response.data.orders) {
        const ordersData = response.data.orders || [];
        setOrders(ordersData);
        setTotalCount(response.data.total_count || 0);
        setTotalPages(Math.ceil((response.data.total_count || 0) / 20));
        setCurrentPage(page);
        frontendLogger.info('✅ Printify 订单列表获取成功', {
          count: ordersData.length,
          total: response.data.total_count,
          storeName: store.name,
        });
      } else {
        throw new Error(response.data.message || '获取订单列表失败');
      }
    } catch (error) {
      frontendLogger.error('❌ 获取 Printify 订单列表失败', {
        error: String(error),
        storeId: store.id_hashid,
      });
      setError('获取订单列表失败');
    } finally {
      setLoadingOrders(false);
    }
  }, []);

  // 刷新订单列表
  const handleRefresh = useCallback(async () => {
    if (!selectedStore) return;

    setRefreshing(true);
    try {
      await fetchOrders(selectedStore, currentPage);
      frontendLogger.info('✅ 订单列表刷新成功');
    } catch (error) {
      frontendLogger.error('❌ 订单列表刷新失败', { error: String(error) });
    } finally {
      setRefreshing(false);
    }
  }, [selectedStore, currentPage, fetchOrders]);

  // 搜索过滤
  const filteredOrders = orders.filter((order) => {
    const matchesSearch = 
      (order.app_order_id || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (order.metadata?.shop_order_id || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (order.address_to?.first_name || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (order.address_to?.last_name || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (order.address_to?.email || '').toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesStatus = statusFilter === 'all' || order.status === statusFilter;
    
    return matchesSearch && matchesStatus;
  });

  // 获取状态颜色
  const getStatusColor = (status: OrderStatus | string) => {
    switch (status) {
      case 'pending':
        return 'warning';
      case 'processing':
        return 'info';
      case 'shipped':
        return 'primary';
      case 'delivered':
        return 'success';
      case 'cancelled':
        return 'error';
      case 'on_hold':
        return 'default';
      case 'fulfilled':
        return 'success';
      case 'unfulfilled':
        return 'warning';
      case 'partial':
        return 'info';
      default:
        return 'default';
    }
  };

  // 获取状态图标
  const getStatusIcon = (status: OrderStatus) => {
    switch (status) {
      case 'pending':
        return <InfoIcon />;
      case 'processing':
        return <RefreshIcon />;
      case 'shipped':
        return <ShippingIcon />;
      case 'delivered':
        return <StatusIcon />;
      case 'cancelled':
        return <ErrorIcon />;
      case 'on_hold':
        return <InfoIcon />;
      default:
        return <InfoIcon />;
    }
  };

  // 格式化日期
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  // 格式化价格
  const formatPrice = (price: number, currency: string = 'USD') => {
    return new Intl.NumberFormat('zh-CN', {
      style: 'currency',
      currency: currency,
    }).format(price);
  };

  // 多选处理函数
  const handleSelectOrder = (orderId: string) => {
    const newSelected = new Set(selectedOrders);
    if (newSelected.has(orderId)) {
      newSelected.delete(orderId);
    } else {
      newSelected.add(orderId);
    }
    setSelectedOrders(newSelected);
  };

  const handleSelectAll = () => {
    if (selectedOrders.size === orders.length) {
      setSelectedOrders(new Set());
    } else {
      setSelectedOrders(new Set(orders.map(order => order.id.toString())));
    }
  };

  // 更新物流信息到本地
  const handleUpdateTrackingInfo = async () => {
    if (selectedOrders.size === 0) {
      setError('请选择要更新的订单');
      return;
    }

    if (!selectedStore) {
      setError('请先选择一个店铺');
      return;
    }

    try {
      setUpdatingTracking(true);
      setError(null);

      frontendLogger.info('🔄 开始更新物流信息到本地', {
        selectedOrders: Array.from(selectedOrders),
        count: selectedOrders.size
      });

      // 批量更新选中的订单
      let successCount = 0;
      let failCount = 0;

      for (const orderId of selectedOrders) {
        const order = orders.find(o => o.id.toString() === orderId);
        if (!order) {
          frontendLogger.error(`❌ 未找到订单: orderId=${orderId}`);
          continue;
        }

        frontendLogger.info(`🔍 准备更新订单物流信息`, {
          selectedOrderId: orderId,
          orderId: order.id,
          appOrderId: order.app_order_id,
          trackingNumber: order.tracking_number,
          carrier: order.tracking_company
        });

        try {
          // 调用后端API更新单个订单的物流信息
          const updateData = {
            external_order_id: order.id, // 使用 order.id 匹配数据库中的 external_order_id（Printify 订单的唯一 ID）
            external_system_id: selectedStore.id_hashid,
            tracking_number: order.tracking_number || null, // 确保不是 undefined
            tracking_url: order.tracking_url || null,
            carrier: order.tracking_company || null,
            shipped_at: order.shipped_at || null,
            delivered_at: order.delivered_at || null,
            status: order.status || null
          };

          frontendLogger.info(`🔍 发送更新请求`, {
            orderId: order.id,
            appOrderId: order.app_order_id,
            updateData
          });

          console.log('🔍 发送更新请求到 Next.js API 路由', {
            url: '/api/printify-orders/',
            method: 'POST',
            data: updateData
          });

          let response;
          try {
            console.log('🔍 开始调用 frontendApi.post');
            response = await frontendApi.post('/api/printify-orders/', updateData);
            console.log('✅ Next.js API 路由响应成功', response.data);
          } catch (error) {
            console.error('❌ Next.js API 路由响应失败', error);
            console.error('❌ 错误详情', {
              message: error.message,
              status: error.response?.status,
              statusText: error.response?.statusText,
              data: error.response?.data
            });
            failCount++;
            console.error(`订单 ${order.id} 更新失败:`, error);
            continue;
          }

          if (response.data.success) {
            successCount++;
            frontendLogger.info(`✅ 订单 ${order.id} 物流信息更新成功`);
          } else {
            failCount++;
            console.error(`订单 ${order.id} 更新失败:`, response.data.message);
          }
        } catch (error) {
          failCount++;
          console.error(`订单 ${order.id} 更新失败:`, error);
        }
      }

      frontendLogger.info('✅ 批量更新完成', { successCount, failCount });
      
      if (successCount > 0) {
        setError(null);
        // 刷新订单列表
        if (selectedStore) {
          await fetchOrders(selectedStore, currentPage);
        }
        // 清空选择
        setSelectedOrders(new Set());
        // 显示成功消息
        alert(`成功更新 ${successCount} 个订单的物流信息${failCount > 0 ? `，${failCount} 个失败` : ''}`);
      } else {
        setError('所有订单更新失败');
      }
    } catch (error: any) {
      console.error('❌ 更新物流信息失败:', error);
      setError(error.response?.data?.detail || '更新失败，请稍后重试');
    } finally {
      setUpdatingTracking(false);
    }
  };

  // 批量保存订单到本地数据库
  const handleBatchSaveToDatabase = async () => {
    if (selectedOrders.size === 0) {
      setError('请选择要保存的订单');
      return;
    }

    if (!selectedStore) {
      setError('请先选择一个店铺');
      return;
    }

    try {
      setSavingToDatabase(true);
      setError(null);

      frontendLogger.info('🔄 开始批量保存订单到本地数据库', {
        selectedOrders: Array.from(selectedOrders),
        count: selectedOrders.size
      });

      // 批量保存选中的订单
      let successCount = 0;
      let failCount = 0;

      for (const orderId of selectedOrders) {
        const order = orders.find(o => o.id.toString() === orderId);
        if (!order) {
          frontendLogger.error(`❌ 未找到订单: orderId=${orderId}`);
          continue;
        }

        try {
          // 构建订单数据
          const orderData = {
            external_system_id: selectedStore.id_hashid,
            external_order_id: order.id, // 使用 order.id 作为 external_order_id（Printify 订单的唯一 ID）
            status: order.status,
            total_price: order.total_price,
            currency: order.currency,
            customer_email: order.address_to?.email || '',
            customer_name: `${order.address_to?.first_name || ''} ${order.address_to?.last_name || ''}`.trim(),
            shipping_address: order.address_to ? {
              first_name: order.address_to.first_name,
              last_name: order.address_to.last_name,
              email: order.address_to.email,
              phone: order.address_to.phone,
              country: order.address_to.country,
              region: order.address_to.region,
              city: order.address_to.city,
              zip: order.address_to.zip,
              address1: order.address_to.address1,
              address2: order.address_to.address2,
            } : null,
            billing_address: order.address_billing ? {
              first_name: order.address_billing.first_name,
              last_name: order.address_billing.last_name,
              email: order.address_billing.email,
              phone: order.address_billing.phone,
              country: order.address_billing.country,
              region: order.address_billing.region,
              city: order.address_billing.city,
              zip: order.address_billing.zip,
              address1: order.address_billing.address1,
              address2: order.address_billing.address2,
            } : null,
            printify_data: order, // 完整的 Printify 订单数据
            external_data: order, // 直接使用完整的订单对象
            // 尝试关联 SCM 订单（如果存在）
            scm_order_id: await findScmOrderByPrintifyOrderId(
              order.id, // 使用 order.id 而不是 app_order_id
              order.address_to?.email,
              `${order.address_to?.first_name || ''} ${order.address_to?.last_name || ''}`.trim()
            ),
          };

          // 调用后端 API 保存订单
          const response = await frontendApi.post('/api/printify-orders/', orderData);

          frontendLogger.info('✅ Printify 订单保存到数据库成功', {
            orderId: order.id,
            appOrderId: order.app_order_id,
            savedOrderId: response.data.id,
          });

          successCount++;

        } catch (error: any) {
          failCount++;
          frontendLogger.error(`❌ 保存订单 ${order.id} (app_order_id: ${order.app_order_id}) 失败`, {
            error: String(error),
            errorMessage: error.message,
            errorResponse: error.response?.data,
          });
        }
      }

      // 显示结果
      if (successCount > 0) {
        alert(`成功保存 ${successCount} 个订单到本地数据库${failCount > 0 ? `，${failCount} 个失败` : ''}`);
      } else {
        setError('所有订单保存失败');
      }

    } catch (error: any) {
      console.error('❌ 批量保存订单失败:', error);
      setError(error.response?.data?.detail || '保存失败，请稍后重试');
    } finally {
      setSavingToDatabase(false);
    }
  };

  // 查看订单详情
  const handleViewOrder = async (order: PrintifyOrder) => {
    if (!selectedStore) return;
    
    try {
      frontendLogger.info('🔍 开始获取 Printify 订单详情', {
        orderId: order.id,
        appOrderId: order.app_order_id,
        storeId: selectedStore.id_hashid,
      });

      const response = await frontendApi.get(
        `/api/external-systems/printify/${selectedStore.id_hashid}/orders/${order.id}`
      );

      if (response.data.success && response.data.order) {
        const orderDetails = response.data.order;
        setSelectedOrder(orderDetails);
        setOpenOrderDialog(true);
        // 重置保存状态
        setSaveSuccess(false);
        setSaveError(null);
        frontendLogger.info('✅ Printify 订单详情获取成功', {
          orderId: order.id,
          appOrderId: order.app_order_id,
          hasShippingInfo: !!(orderDetails.tracking_number || orderDetails.tracking_url),
        });
      } else {
        throw new Error(response.data.message || '获取订单详情失败');
      }
    } catch (error) {
      frontendLogger.error('❌ 获取 Printify 订单详情失败', {
        error: String(error),
        orderId: order.id,
        appOrderId: order.app_order_id,
        storeId: selectedStore.id_hashid,
      });
      // 如果 API 调用失败，仍然显示基本订单信息
      setSelectedOrder(order);
      setOpenOrderDialog(true);
    }
  };

  // 分页处理
  const handlePageChange = (event: React.ChangeEvent<unknown>, page: number) => {
    if (selectedStore) {
      fetchOrders(selectedStore, page);
    }
  };

  // 保存订单到数据库
  const handleSaveToDatabase = async () => {
    if (!selectedOrder || !selectedStore) return;

    try {
      setSavingToDatabase(true);
      setSaveError(null);
      setSaveSuccess(false);

      frontendLogger.info('🔍 开始保存 Printify 订单到数据库', {
        orderId: selectedOrder.id,
        appOrderId: selectedOrder.app_order_id,
        storeId: selectedStore.id_hashid,
      });

      // 构建保存到数据库的订单数据
      const orderData = {
        external_order_id: selectedOrder.id, // 使用 order.id 作为 external_order_id（Printify 订单的唯一 ID）
        external_system_id: selectedStore.id_hashid, // 使用店铺的 hashid
        status: selectedOrder.status,
        total_price: (selectedOrder.total_price / 100).toString(), // 转换为美元
        currency: 'USD',
        customer_email: selectedOrder.address_to?.email || '',
        customer_name: `${selectedOrder.address_to?.first_name || ''} ${selectedOrder.address_to?.last_name || ''}`.trim(),
        shipping_address: selectedOrder.address_to, // 直接使用对象
        billing_address: selectedOrder.address_to, // 直接使用对象
        printify_data: selectedOrder, // 直接使用完整的订单对象
        external_data: selectedOrder, // 直接使用完整的订单对象
        // 尝试关联 SCM 订单（如果存在）
        scm_order_id: await findScmOrderByPrintifyOrderId(
          selectedOrder.id, // 使用 order.id 而不是 app_order_id
          selectedOrder.address_to?.email,
          `${selectedOrder.address_to?.first_name || ''} ${selectedOrder.address_to?.last_name || ''}`.trim()
        ),
      };

      // 调用后端 API 保存订单
      const response = await frontendApi.post('/api/printify-orders/', orderData);

      frontendLogger.info('✅ Printify 订单保存到数据库成功', {
        orderId: selectedOrder.id,
        appOrderId: selectedOrder.app_order_id,
        savedOrderId: response.data.id,
      });

      // 显示成功消息
      setSaveSuccess(true);
      setSaveError(null);

      // 3秒后自动隐藏成功消息
      setTimeout(() => {
        setSaveSuccess(false);
      }, 3000);

    } catch (error: any) {
      frontendLogger.error('❌ 保存 Printify 订单到数据库失败', {
        error: String(error),
        errorMessage: error.message,
        errorResponse: error.response?.data,
      });

      setSaveError(
        error.response?.data?.detail || 
        error.message || 
        '保存订单失败，请稍后重试'
      );
    } finally {
      setSavingToDatabase(false);
    }
  };

  // 店铺选择处理
  const handleStoreChange = (store: PrintifyStore) => {
    setSelectedStore(store);
    setCurrentPage(1);
    fetchOrders(store, 1);
  };

  // 初始化
  useEffect(() => {
    const initialize = async () => {
      setLoading(true);
      try {
        await fetchStores();
      } finally {
        setLoading(false);
      }
    };
    initialize();
  }, [fetchStores]);

  // 当选择店铺时获取订单
  useEffect(() => {
    if (selectedStore) {
      fetchOrders(selectedStore, 1);
    }
  }, [selectedStore, fetchOrders]);

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  if (error && !orders.length) {
    return (
      <Box p={3}>
        <Alert severity="error" action={
          <Button color="inherit" size="small" onClick={handleRefresh}>
            重试
          </Button>
        }>
          {error}
        </Alert>
      </Box>
    );
  }

  return (
    <ProtectedRoute>
      <DashboardLayout>
        <Box p={3}>
          {/* 页面标题 */}
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
            <Box display="flex" alignItems="center" gap={2}>
              <OrderIcon color="primary" />
              <Typography variant="h4" component="h1">
                Printify 实时订单
              </Typography>
            </Box>
            <Box display="flex" gap={2}>
              {selectedOrders.size > 0 && (
                <Button
                  variant="contained"
                  color="secondary"
                  startIcon={updatingTracking ? <CircularProgress size={16} /> : <ShippingIcon />}
                  onClick={handleUpdateTrackingInfo}
                  disabled={updatingTracking || refreshing || !selectedStore}
                >
                  {updatingTracking ? '更新中...' : `更新物流信息 (${selectedOrders.size})`}
                </Button>
              )}
              {selectedOrders.size > 0 && (
                <Button
                  variant="contained"
                  color="primary"
                  startIcon={savingToDatabase ? <CircularProgress size={16} /> : <SaveIcon />}
                  onClick={handleBatchSaveToDatabase}
                  disabled={savingToDatabase || refreshing || !selectedStore}
                >
                  {savingToDatabase ? '保存中...' : `批量保存到本地 (${selectedOrders.size})`}
                </Button>
              )}
              <Button
                variant="contained"
                startIcon={<RefreshIcon />}
                onClick={handleRefresh}
                disabled={refreshing || !selectedStore}
              >
                {refreshing ? '刷新中...' : '刷新'}
              </Button>
            </Box>
          </Box>

      {/* 店铺选择 */}
      {stores.length > 0 && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              选择店铺
            </Typography>
            <Grid container spacing={2}>
              {stores.map((store) => (
                <Grid key={store.id_hashid} size={{ xs: 12, sm: 6, md: 4 }}>
                  <Card
                    variant={selectedStore?.id_hashid === store.id_hashid ? 'elevation' : 'outlined'}
                    sx={{
                      cursor: 'pointer',
                      border: selectedStore?.id_hashid === store.id_hashid ? 2 : 1,
                      borderColor: selectedStore?.id_hashid === store.id_hashid ? 'primary.main' : 'divider',
                    }}
                    onClick={() => handleStoreChange(store)}
                  >
                    <CardContent>
                      <Box display="flex" alignItems="center" gap={2}>
                        <StoreIcon color="primary" />
                        <Box>
                          <Typography variant="h6">{store.name}</Typography>
                          <Typography variant="body2" color="text.secondary">
                            ID: {store.external_id}
                          </Typography>
                        </Box>
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          </CardContent>
        </Card>
      )}

      {/* 搜索和过滤 */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Grid container spacing={2} alignItems="center">
            <Grid size={{ xs: 12, sm: 6, md: 4 }}>
              <TextField
                fullWidth
                label="搜索订单"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                InputProps={{
                  startAdornment: <SearchIcon sx={{ mr: 1, color: 'text.secondary' }} />,
                }}
                placeholder="订单ID、客户姓名或邮箱"
              />
            </Grid>
            <Grid size={{ xs: 12, sm: 6, md: 4 }}>
              <FormControl fullWidth>
                <InputLabel>订单状态</InputLabel>
                <Select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value as OrderStatus | 'all')}
                  label="订单状态"
                >
                  <MenuItem value="all">全部状态</MenuItem>
                  <MenuItem value="pending">待处理</MenuItem>
                  <MenuItem value="processing">处理中</MenuItem>
                  <MenuItem value="shipped">已发货</MenuItem>
                  <MenuItem value="delivered">已送达</MenuItem>
                  <MenuItem value="cancelled">已取消</MenuItem>
                  <MenuItem value="on_hold">暂停</MenuItem>
                </Select>
              </FormControl>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* 订单列表 */}
      <Card>
        <CardContent>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="h6">
              订单列表 {totalCount > 0 && `(${totalCount} 个订单)`}
            </Typography>
            {loadingOrders && <CircularProgress size={24} />}
          </Box>

          {filteredOrders.length === 0 ? (
            <Box textAlign="center" py={4}>
              <OrderIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
              <Typography variant="h6" color="text.secondary">
                {searchTerm || statusFilter !== 'all' ? '没有找到符合条件的订单' : '暂无订单'}
              </Typography>
            </Box>
          ) : (
            <>
              <TableContainer component={Paper} variant="outlined">
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell padding="checkbox">
                        <Checkbox
                          indeterminate={selectedOrders.size > 0 && selectedOrders.size < orders.length}
                          checked={orders.length > 0 && selectedOrders.size === orders.length}
                          onChange={handleSelectAll}
                        />
                      </TableCell>
                      <TableCell>订单ID</TableCell>
                      <TableCell>客户信息</TableCell>
                      <TableCell>商品</TableCell>
                      <TableCell>状态</TableCell>
                      <TableCell>总价</TableCell>
                      <TableCell>创建时间</TableCell>
                      <TableCell>操作</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {filteredOrders.map((order) => (
                      <TableRow key={order.id} hover>
                        <TableCell padding="checkbox">
                          <Checkbox
                            checked={selectedOrders.has(order.id.toString())}
                            onChange={() => handleSelectOrder(order.id.toString())}
                          />
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" fontFamily="monospace">
                            {order.app_order_id}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {order.metadata?.shop_order_id}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Box>
                            <Typography variant="body2" fontWeight="medium">
                              {order.address_to?.first_name || 'N/A'} {order.address_to?.last_name || ''}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              {order.address_to?.email || 'N/A'}
                            </Typography>
                            <br />
                            <Typography variant="caption" color="text.secondary">
                              {order.address_to?.city || 'N/A'}, {order.address_to?.country || 'N/A'}
                            </Typography>
                          </Box>
                        </TableCell>
                        <TableCell>
                          <Box>
                            {order.line_items.slice(0, 2).map((item, index) => (
                              <Typography key={index} variant="caption" display="block">
                                {item.metadata?.title || 'Unknown Product'} x{item.quantity}
                              </Typography>
                            ))}
                            {order.line_items.length > 2 && (
                              <Typography variant="caption" color="text.secondary">
                                +{order.line_items.length - 2} 更多
                              </Typography>
                            )}
                          </Box>
                        </TableCell>
                        <TableCell>
                          <Chip
                            icon={getStatusIcon(order.status)}
                            label={order.status}
                            color={getStatusColor(order.status) as any}
                            size="small"
                          />
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" fontWeight="medium">
                            {formatPrice(order.total_price / 100, 'USD')}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Typography variant="caption">
                            {formatDate(order.created_at)}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Tooltip title="查看详情">
                            <IconButton
                              size="small"
                              onClick={() => handleViewOrder(order)}
                            >
                              <ViewIcon />
                            </IconButton>
                          </Tooltip>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>

              {/* 分页 */}
              {totalPages > 1 && (
                <Box display="flex" justifyContent="center" mt={3}>
                  <Pagination
                    count={totalPages}
                    page={currentPage}
                    onChange={handlePageChange}
                    color="primary"
                    disabled={loadingOrders}
                  />
                </Box>
              )}
            </>
          )}
        </CardContent>
      </Card>

      {/* 订单详情对话框 */}
      <Dialog
        open={openOrderDialog}
        onClose={() => setOpenOrderDialog(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          <Box display="flex" alignItems="center" gap={2}>
            <OrderIcon color="primary" />
            订单详情
          </Box>
        </DialogTitle>
        <DialogContent>
          {selectedOrder && (
            <Box>
              {/* 保存状态提示 */}
              {saveError && (
                <Alert severity="error" sx={{ mb: 2 }}>
                  {saveError}
                </Alert>
              )}

              {saveSuccess && (
                <Alert severity="success" sx={{ mb: 2 }}>
                  订单已成功保存到数据库！
                </Alert>
              )}
              {/* 订单基本信息 */}
              <Card sx={{ mb: 2 }}>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    订单信息
                  </Typography>
                  <Grid container spacing={2}>
                    <Grid size={{ xs: 12, sm: 6 }}>
                      <Typography variant="body2" color="text.secondary">
                        订单ID
                      </Typography>
                      <Typography variant="body1" fontFamily="monospace">
                        {selectedOrder.app_order_id}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {selectedOrder.metadata?.shop_order_id}
                      </Typography>
                    </Grid>
                    <Grid size={{ xs: 12, sm: 6 }}>
                      <Typography variant="body2" color="text.secondary">
                        状态
                      </Typography>
                      <Chip
                        icon={getStatusIcon(selectedOrder.status)}
                        label={selectedOrder.status}
                        color={getStatusColor(selectedOrder.status) as any}
                        size="small"
                      />
                    </Grid>
                    <Grid size={{ xs: 12, sm: 6 }}>
                      <Typography variant="body2" color="text.secondary">
                        总价
                      </Typography>
                      <Typography variant="h6" color="primary">
                        {formatPrice(selectedOrder.total_price / 100, 'USD')}
                      </Typography>
                    </Grid>
                    <Grid size={{ xs: 12, sm: 6 }}>
                      <Typography variant="body2" color="text.secondary">
                        创建时间
                      </Typography>
                      <Typography variant="body1">
                        {formatDate(selectedOrder.created_at)}
                      </Typography>
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>

              {/* 商品列表 */}
              <Card sx={{ mb: 2 }}>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    商品列表
                  </Typography>
                  {selectedOrder.line_items.map((item, index) => (
                    <Box key={index} display="flex" alignItems="center" gap={2} mb={2}>
                      <Box flex={1}>
                        <Typography variant="body1" fontWeight="medium">
                          {item.metadata?.title || 'Unknown Product'}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          数量: {item.quantity} | SKU: {item.metadata?.sku || 'N/A'}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          规格: {item.metadata?.variant_label || 'N/A'}
                        </Typography>
                      </Box>
                      <Typography variant="body1" fontWeight="medium">
                        {formatPrice(item.cost / 100, 'USD')}
                      </Typography>
                    </Box>
                  ))}
                </CardContent>
              </Card>

              {/* 收货地址 */}
              <Card sx={{ mb: 2 }}>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    收货地址
                  </Typography>
                  <Typography variant="body1">
                    {selectedOrder.address_to?.first_name || 'N/A'} {selectedOrder.address_to?.last_name || ''}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {selectedOrder.address_to?.email || 'N/A'}
                    {selectedOrder.address_to?.phone && ` | ${selectedOrder.address_to.phone}`}
                  </Typography>
                  <Typography variant="body2">
                    {selectedOrder.address_to?.address1 || 'N/A'}
                    {selectedOrder.address_to?.address2 && `, ${selectedOrder.address_to.address2}`}
                  </Typography>
                  <Typography variant="body2">
                    {selectedOrder.address_to?.city || 'N/A'}, {selectedOrder.address_to?.region || 'N/A'} {selectedOrder.address_to?.zip || 'N/A'}
                  </Typography>
                  <Typography variant="body2">
                    {selectedOrder.address_to?.country || 'N/A'}
                  </Typography>
                </CardContent>
              </Card>

              {/* 发货信息 */}
              {(selectedOrder.shipments && selectedOrder.shipments.length > 0) && (
                <Card sx={{ mb: 2 }}>
                  <CardContent>
                    <Typography variant="h6" gutterBottom>
                      发货信息
                    </Typography>
                    {selectedOrder.shipments.map((shipment, index) => (
                      <Box key={index} sx={{ mb: 2, p: 2, border: '1px solid #e0e0e0', borderRadius: 1 }}>
                        <Typography variant="subtitle2" gutterBottom>
                          包裹 {index + 1}
                        </Typography>
                        <Grid container spacing={2}>
                          <Grid size={{ xs: 12, sm: 6 }}>
                            <Typography variant="body2" color="text.secondary">
                              追踪号
                            </Typography>
                            <Typography variant="body1" fontFamily="monospace">
                              {shipment.number}
                            </Typography>
                          </Grid>
                          <Grid size={{ xs: 12, sm: 6 }}>
                            <Typography variant="body2" color="text.secondary">
                              物流公司
                            </Typography>
                            <Typography variant="body1">
                              {shipment.carrier}
                            </Typography>
                          </Grid>
                          <Grid size={{ xs: 12 }}>
                            <Typography variant="body2" color="text.secondary">
                              追踪链接
                            </Typography>
                            <Button
                              size="small"
                              href={shipment.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              variant="outlined"
                            >
                              查看物流状态
                            </Button>
                          </Grid>
                          <Grid size={{ xs: 12, sm: 6 }}>
                            <Typography variant="body2" color="text.secondary">
                              发货时间
                            </Typography>
                            <Typography variant="body1">
                              {formatDate(shipment.shipped_at)}
                            </Typography>
                          </Grid>
                          <Grid size={{ xs: 12, sm: 6 }}>
                            <Typography variant="body2" color="text.secondary">
                              送达时间
                            </Typography>
                            <Typography variant="body1">
                              {shipment.delivered_at ? formatDate(shipment.delivered_at) : '未送达'}
                            </Typography>
                          </Grid>
                        </Grid>
                      </Box>
                    ))}
                    {selectedOrder.fulfillment_status && (
                      <Box sx={{ mt: 2 }}>
                        <Typography variant="body2" color="text.secondary">
                          履行状态
                        </Typography>
                        <Chip
                          label={selectedOrder.fulfillment_status}
                          color={getStatusColor(selectedOrder.fulfillment_status) as any}
                          size="small"
                        />
                      </Box>
                    )}
                  </CardContent>
                </Card>
              )}

            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button 
            variant="contained" 
            color="primary"
            onClick={handleSaveToDatabase}
            disabled={savingToDatabase || !selectedOrder}
            startIcon={savingToDatabase ? <CircularProgress size={20} /> : undefined}
          >
            {savingToDatabase ? '保存中...' : '保存到数据库'}
          </Button>
          <Button onClick={() => setOpenOrderDialog(false)}>
            关闭
          </Button>
        </DialogActions>
      </Dialog>
        </Box>
      </DashboardLayout>
    </ProtectedRoute>
  );
}

export default PrintifyOrdersPage;
