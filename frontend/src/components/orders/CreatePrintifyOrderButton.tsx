'use client';

import React, { useState, useEffect } from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  CardHeader,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  TextField,
  Typography,
  CircularProgress,
  IconButton,
  Tooltip,
  Stack,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
} from '@mui/material';
import {
  LocalShipping as Package,
  CheckCircle,
  Error as ErrorIcon,
} from '@mui/icons-material';
import {
  printifyApi,
  PrintifyOrderRequest,
  PrintifyOrderResponse,
} from '@/lib/printify-api';
import { frontendLogger } from '@/lib/frontend-logger';
import { frontendApi } from '@/lib/api';

interface CreatePrintifyOrderButtonProps {
  orderId: string;
  orderData?: {
    customer_name?: string;
    customer_email?: string;
    shipping_address?: {
      address1?: string;
      city?: string;
      province?: string;
      state?: string;
      country?: string;
      zip?: string;
      phone?: string;
    };
  };
}

interface PrintifyStore {
  id: number;
  name: string;
  external_system_id: string;
  is_active: boolean;
}

export function CreatePrintifyOrderButton({
  orderId,
  orderData,
}: CreatePrintifyOrderButtonProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<PrintifyOrderResponse | null>(null);
  const [stores, setStores] = useState<PrintifyStore[]>([]);
  const [selectedStoreId, setSelectedStoreId] = useState<string>('');
  const [loadingStores, setLoadingStores] = useState(false);
  const [storeError, setStoreError] = useState<string | null>(null);

  // 表单数据
  const [formData, setFormData] = useState({
    customer_name: orderData?.customer_name || 'Test Customer',
    customer_email: orderData?.customer_email || 'test@example.com',
    address_line1: orderData?.shipping_address?.address1 || '123 Test Street',
    city: orderData?.shipping_address?.city || 'Tokyo',
    state: orderData?.shipping_address?.province || orderData?.shipping_address?.state || 'Tokyo',
    country: orderData?.shipping_address?.country || 'JP',
    zip_code: orderData?.shipping_address?.zip || '100-0001',
    phone: orderData?.shipping_address?.phone || '+81-90-1234-5678',
    quantity: 1,
  });

  // 获取Printify店铺列表
  const fetchStores = async () => {
    try {
      setLoadingStores(true);
      setStoreError(null);
      
      const response = await frontendApi.get('/api/external-systems?system_type=printify');
      const printifyStores = response.data.external_systems.filter(
        (store: any) => store.system_type === 'PRINTIFY' && store.is_active
      );
      
      setStores(printifyStores);
      
      // 如果只有一个店铺，自动选择
      if (printifyStores.length === 1) {
        setSelectedStoreId(printifyStores[0].id_hashid);
      }
      
      frontendLogger.info('✅ Printify店铺列表获取成功', { count: printifyStores.length });
    } catch (error: any) {
      console.error('❌ 获取Printify店铺列表失败:', error);
      setStoreError('获取Printify店铺列表失败，请稍后重试');
      frontendLogger.error('❌ 获取Printify店铺列表失败', { error: error.message });
    } finally {
      setLoadingStores(false);
    }
  };

  // 当对话框打开时获取店铺列表
  useEffect(() => {
    if (isOpen && stores.length === 0) {
      fetchStores();
    }
  }, [isOpen]);

  const handleInputChange = (field: string, value: string | number) => {
    setFormData(prev => ({
      ...prev,
      [field]: value,
    }));
  };

  const handleCreateOrder = async () => {
    if (!selectedStoreId) {
      alert('请选择一个Printify店铺');
      return;
    }

    setIsLoading(true);
    setResult(null);

    try {
      frontendLogger.info('🚀 开始创建Printify订单', { orderId, selectedStoreId });

      const request: PrintifyOrderRequest = {
        order_id: parseInt(orderId),
        ...formData,
      };

      const response = await printifyApi.createOrder(request);

      frontendLogger.info('📋 Printify API响应', { 
        success: response.success, 
        printifyOrderId: response.printify_order_id,
        externalId: response.external_id,
        status: response.status,
        totalPrice: response.total_price,
        message: response.message,
        fullResponse: response
      });

      if (response.success) {
        frontendLogger.info('✅ Printify订单创建成功', { response });
        
        // 创建SCM订单
        try {
          frontendLogger.info('🚀 开始创建SCM订单', { orderId, printifyOrderId: response.printify_order_id });
          
          // 获取订单的Shopify订单ID
          const orderResponse = await frontendApi.get(`/api/orders/${orderId}`);
          const shopifyOrderId = orderResponse.data?.shopify_order_id;
          
          frontendLogger.info('📋 订单信息', { 
            orderId, 
            shopifyOrderId, 
            orderData: orderResponse.data 
          });

          const scmOrderData = {
            source_order_id: parseInt(orderId),
            target_system_type: 'PRINTIFY',
            target_system_id: response.printify_order_id,
            routing_strategy: 'manual',
            line_items: [{
              product_id: 'default',
              variant_id: 'default',
              quantity: formData.quantity,
              price: response.total_price || 0
            }],
            total_amount: response.total_price || 0,
            currency: 'USD',
            customer_email: formData.customer_email,
            customer_name: formData.customer_name,
            customer_phone: formData.phone,
            shipping_address: {
              first_name: formData.customer_name.split(' ')[0] || 'Customer',
              last_name: formData.customer_name.split(' ').slice(1).join(' ') || '',
              address1: formData.address_line1,
              city: formData.city,
              state: formData.state,
              country: formData.country,
              zip: formData.zip_code,
              phone: formData.phone,
            },
            routing_metadata: {
              strategy: 'manual',
              printify_order_id: response.printify_order_id,
              external_id: response.external_id,
            },
            // 添加Shopify订单ID关联（可能为null）
            shopify_order_id: shopifyOrderId,
          };

          frontendLogger.info('📤 发送SCM订单创建请求', { scmOrderData });
          const scmResponse = await frontendApi.post('/api/scm-orders', scmOrderData);
          
          frontendLogger.info('📥 SCM订单创建响应', { scmResponse: scmResponse.data });
          
          if (scmResponse.data) {
            frontendLogger.info('✅ SCM订单创建成功', { scmOrderId: scmResponse.data.id });
            alert(`Printify订单和SCM订单创建成功！\nPrintify订单ID: ${response.printify_order_id}\nSCM订单ID: ${scmResponse.data.id}`);
          } else {
            frontendLogger.warning('⚠️ SCM订单创建失败，但Printify订单已创建', { response: scmResponse.data });
            alert(`Printify订单创建成功！\nPrintify订单ID: ${response.printify_order_id}\n但SCM订单创建失败，请手动创建SCM订单。`);
          }
        } catch (scmError: any) {
          frontendLogger.error('❌ 创建SCM订单时发生错误', { 
            error: scmError.message,
            stack: scmError.stack,
            response: scmError.response?.data 
          });
          alert(`Printify订单创建成功！\nPrintify订单ID: ${response.printify_order_id}\n但SCM订单创建失败，请手动创建SCM订单。\n错误: ${scmError.message}`);
        }
        
        setResult(response);
      } else {
        frontendLogger.error('❌ Printify订单创建失败', { response });
        alert(response.message || '订单创建失败');
      }
    } catch (error: any) {
      frontendLogger.error('❌ 创建Printify订单时发生错误', {
        error: error.message,
      });
      alert('创建订单时发生错误，请稍后重试');
    } finally {
      setIsLoading(false);
    }
  };

  const handleClose = () => {
    setIsOpen(false);
    setResult(null);
    setSelectedStoreId('');
    setStoreError(null);
  };

  return (
    <>
      <Tooltip title='创建Printify发货单'>
        <IconButton onClick={() => setIsOpen(true)} color='primary'>
          <Package />
        </IconButton>
      </Tooltip>

      <Dialog open={isOpen} onClose={handleClose} maxWidth='md' fullWidth>
        <DialogTitle>
          <Box display='flex' alignItems='center' gap={1}>
            <Package />
            创建Printify发货单
          </Box>
        </DialogTitle>

        <DialogContent>
          <Typography variant='body2' color='text.secondary' sx={{ mb: 3 }}>
            为订单 {orderId} 创建Printify发货单。
          </Typography>

          <Stack spacing={3}>
            {/* 店铺选择 */}
            <Card variant='outlined'>
              <CardHeader>
                <Typography variant='h6' component='div' sx={{ p: 2, pb: 0 }}>
                  Printify店铺选择
                </Typography>
              </CardHeader>
              <CardContent>
                {storeError && (
                  <Alert severity='error' sx={{ mb: 2 }}>
                    {storeError}
                  </Alert>
                )}
                
                {loadingStores ? (
                  <Box display='flex' alignItems='center' gap={2}>
                    <CircularProgress size={20} />
                    <Typography variant='body2'>正在加载Printify店铺...</Typography>
                  </Box>
                ) : stores.length === 0 ? (
                  <Alert severity='warning'>
                    没有找到可用的Printify店铺，请先在外部系统管理中配置Printify连接。
                  </Alert>
                ) : (
                  <FormControl fullWidth>
                    <InputLabel>选择Printify店铺 *</InputLabel>
                    <Select
                      value={selectedStoreId}
                      onChange={(e) => setSelectedStoreId(e.target.value)}
                      label='选择Printify店铺 *'
                    >
                      {stores.map((store) => (
                        <MenuItem key={store.id} value={store.id_hashid}>
                          {store.name} ({store.external_system_id})
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                )}
              </CardContent>
            </Card>

            {/* 客户信息 */}
            <Card variant='outlined'>
              <CardHeader>
                <Typography variant='h6' component='div' sx={{ p: 2, pb: 0 }}>
                  客户信息
                </Typography>
              </CardHeader>
              <CardContent>
                <Stack spacing={2}>
                  <Box display='flex' gap={2}>
                    <TextField
                      fullWidth
                      label='客户姓名 *'
                      value={formData.customer_name}
                      onChange={e =>
                        handleInputChange('customer_name', e.target.value)
                      }
                      placeholder='请输入客户姓名'
                    />
                    <TextField
                      fullWidth
                      label='客户邮箱 *'
                      type='email'
                      value={formData.customer_email}
                      onChange={e =>
                        handleInputChange('customer_email', e.target.value)
                      }
                      placeholder='请输入客户邮箱'
                    />
                  </Box>
                  <TextField
                    fullWidth
                    label='电话号码'
                    value={formData.phone}
                    onChange={e => handleInputChange('phone', e.target.value)}
                    placeholder='请输入电话号码'
                  />
                </Stack>
              </CardContent>
            </Card>

            {/* 收货地址 */}
            <Card variant='outlined'>
              <CardHeader>
                <Typography variant='h6' component='div' sx={{ p: 2, pb: 0 }}>
                  收货地址
                </Typography>
              </CardHeader>
              <CardContent>
                <Stack spacing={2}>
                  <TextField
                    fullWidth
                    label='地址第一行 *'
                    value={formData.address_line1}
                    onChange={e =>
                      handleInputChange('address_line1', e.target.value)
                    }
                    placeholder='请输入详细地址'
                  />
                  <Box display='flex' gap={2}>
                    <TextField
                      fullWidth
                      label='城市 *'
                      value={formData.city}
                      onChange={e => handleInputChange('city', e.target.value)}
                      placeholder='请输入城市'
                    />
                    <TextField
                      fullWidth
                      label='州/省 *'
                      value={formData.state}
                      onChange={e => handleInputChange('state', e.target.value)}
                      placeholder='请输入州/省'
                    />
                  </Box>
                  <Box display='flex' gap={2}>
                    <TextField
                      label='国家代码 *'
                      value={formData.country}
                      onChange={e =>
                        handleInputChange('country', e.target.value)
                      }
                      placeholder='如: JP, US'
                    />
                    <TextField
                      label='邮政编码 *'
                      value={formData.zip_code}
                      onChange={e =>
                        handleInputChange('zip_code', e.target.value)
                      }
                      placeholder='请输入邮政编码'
                    />
                    <TextField
                      label='数量'
                      type='number'
                      inputProps={{ min: 1 }}
                      value={formData.quantity}
                      onChange={e =>
                        handleInputChange(
                          'quantity',
                          parseInt(e.target.value) || 1
                        )
                      }
                      placeholder='1'
                    />
                  </Box>
                </Stack>
              </CardContent>
            </Card>

            {/* 结果显示 */}
            {result && (
              <Card variant='outlined'>
                <CardHeader>
                  <Typography
                    variant='h6'
                    component='div'
                    sx={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 1,
                      p: 2,
                      pb: 0,
                    }}
                  >
                    {result.success ? (
                      <CheckCircle color='success' />
                    ) : (
                      <ErrorIcon color='error' />
                    )}
                    创建结果
                  </Typography>
                </CardHeader>
                <CardContent>
                  <Stack spacing={1}>
                    <Typography variant='body2'>
                      <strong>状态:</strong> {result.success ? '成功' : '失败'}
                    </Typography>
                    <Typography variant='body2'>
                      <strong>消息:</strong> {result.message}
                    </Typography>
                    {result.printify_order_id && (
                      <Typography variant='body2'>
                        <strong>Printify订单ID:</strong>{' '}
                        {result.printify_order_id}
                      </Typography>
                    )}
                    {result.external_id && (
                      <Typography variant='body2'>
                        <strong>外部ID:</strong> {result.external_id}
                      </Typography>
                    )}
                    {result.status && (
                      <Typography variant='body2'>
                        <strong>订单状态:</strong> {result.status}
                      </Typography>
                    )}
                    {result.total_price && (
                      <Typography variant='body2'>
                        <strong>总价:</strong> ${result.total_price.toFixed(2)}
                      </Typography>
                    )}
                  </Stack>
                </CardContent>
              </Card>
            )}
          </Stack>
        </DialogContent>

        <DialogActions>
          <Button onClick={handleClose}>关闭</Button>
          <Button
            onClick={handleCreateOrder}
            disabled={isLoading}
            variant='contained'
            startIcon={isLoading ? <CircularProgress size={20} /> : <Package />}
          >
            创建Printify订单
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}
