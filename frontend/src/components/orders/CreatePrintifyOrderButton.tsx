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
  Checkbox,
  FormControlLabel,
  FormGroup,
  Chip,
  Divider,
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
  id_hashid: string;
  name: string;
  external_system_id: string;
  is_active: boolean;
}

interface OrderLineItem {
  id: string;
  title: string;
  variant_title?: string;
  sku?: string;
  quantity: number;
  price: number;
  product_id?: string;
  variant_id?: string;
}

interface SelectedProduct {
  lineItem: OrderLineItem;
  quantity: number;
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

  // 商品选择相关状态
  const [orderLineItems, setOrderLineItems] = useState<OrderLineItem[]>([]);
  const [selectedProducts, setSelectedProducts] = useState<SelectedProduct[]>(
    []
  );
  const [loadingProducts, setLoadingProducts] = useState(false);
  const [productsError, setProductsError] = useState<string | null>(null);

  // 表单数据
  const [formData, setFormData] = useState({
    customer_name: orderData?.customer_name || 'Test Customer',
    customer_email: orderData?.customer_email || 'test@example.com',
    address_line1: orderData?.shipping_address?.address1 || '123 Test Street',
    city: orderData?.shipping_address?.city || 'Tokyo',
    state:
      orderData?.shipping_address?.province ||
      orderData?.shipping_address?.state ||
      'Tokyo',
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

      const response = await frontendApi.get(
        '/api/external-systems?system_type=printify'
      );
      const printifyStores = response.data.external_systems.filter(
        (store: any) => store.system_type === 'PRINTIFY' && store.is_active
      );

      setStores(printifyStores);

      // 如果只有一个店铺，自动选择
      if (printifyStores.length === 1) {
        setSelectedStoreId(printifyStores[0].id_hashid);
      }

      frontendLogger.info('✅ Printify店铺列表获取成功', {
        count: printifyStores.length,
      });
    } catch (error: any) {
      console.error('❌ 获取Printify店铺列表失败:', error);
      setStoreError('获取Printify店铺列表失败，请稍后重试');
      frontendLogger.error('❌ 获取Printify店铺列表失败', {
        error: error.message,
      });
    } finally {
      setLoadingStores(false);
    }
  };

  // 获取订单商品信息
  const fetchOrderProducts = async () => {
    try {
      setLoadingProducts(true);
      setProductsError(null);

      const response = await frontendApi.get(`/api/orders/${orderId}`);
      const orderData = response.data;

      if (orderData?.line_items && Array.isArray(orderData.line_items)) {
        const lineItems: OrderLineItem[] = orderData.line_items.map(
          (item: any, index: number) => ({
            id: item.id || `item-${index}`,
            title: item.title || item.name || 'Unknown Product',
            variant_title: item.variant_title || item.variant_name,
            sku: item.sku,
            quantity: item.quantity || 1,
            price: item.price || 0,
            product_id: item.product_id,
            variant_id: item.variant_id,
          })
        );

        setOrderLineItems(lineItems);
        frontendLogger.info('📦 获取订单商品信息成功', {
          orderId,
          lineItemsCount: lineItems.length,
          lineItems,
        });
      } else {
        setOrderLineItems([]);
        frontendLogger.info('📦 订单没有商品信息', { orderId });
      }
    } catch (error: any) {
      console.error('获取订单商品信息失败:', error);
      setProductsError('获取订单商品信息失败，请稍后重试');
      frontendLogger.error('❌ 获取订单商品信息失败', {
        orderId,
        error: error.message,
      });
    } finally {
      setLoadingProducts(false);
    }
  };

  // 当对话框打开时获取店铺列表和商品信息
  useEffect(() => {
    if (isOpen) {
      if (stores.length === 0) {
        fetchStores();
      }
      if (orderLineItems.length === 0) {
        fetchOrderProducts();
      }
    }
  }, [isOpen]);

  const handleInputChange = (field: string, value: string | number) => {
    setFormData(prev => ({
      ...prev,
      [field]: value,
    }));
  };

  // 处理商品选择
  const handleProductSelect = (
    lineItem: OrderLineItem,
    isSelected: boolean
  ) => {
    if (isSelected) {
      // 添加商品到选择列表
      setSelectedProducts(prev => [
        ...prev,
        { lineItem, quantity: lineItem.quantity },
      ]);
    } else {
      // 从选择列表中移除商品
      setSelectedProducts(prev =>
        prev.filter(item => item.lineItem.id !== lineItem.id)
      );
    }
  };

  // 处理商品数量变化
  const handleProductQuantityChange = (
    lineItemId: string,
    quantity: number
  ) => {
    setSelectedProducts(prev =>
      prev.map(item =>
        item.lineItem.id === lineItemId
          ? { ...item, quantity: Math.max(1, quantity) }
          : item
      )
    );
  };

  // 移除选中的商品
  const handleRemoveProduct = (lineItemId: string) => {
    setSelectedProducts(prev =>
      prev.filter(item => item.lineItem.id !== lineItemId)
    );
  };

  const handleCreateOrder = async () => {
    if (!selectedStoreId) {
      alert('请选择一个Printify店铺');
      return;
    }

    if (selectedProducts.length === 0) {
      alert('请至少选择一个商品');
      return;
    }

    setIsLoading(true);
    setResult(null);

    try {
      frontendLogger.info('🚀 开始创建Printify订单', {
        orderId,
        selectedStoreId,
        selectedProductsCount: selectedProducts.length,
        selectedProducts,
      });

      // 获取订单信息
      const orderResponse = await frontendApi.get(`/api/orders/${orderId}`);
      const orderData = orderResponse.data;
      const shopifyOrderId = orderData?.shopify_order_id;

      frontendLogger.info('📋 订单信息', {
        orderId,
        shopifyOrderId,
        orderData,
      });

      const results = [];
      const scmOrderIds = [];

      // 为每个选中的商品创建独立的 Printify 订单和 SCM 订单
      for (let i = 0; i < selectedProducts.length; i++) {
        const selectedProduct = selectedProducts[i];
        try {
          frontendLogger.info(
            `🚀 开始创建履约 ${i + 1}/${selectedProducts.length}`,
            {
              fulfillmentIndex: i,
              totalFulfillments: selectedProducts.length,
              selectedProduct: selectedProduct.lineItem.title,
              quantity: selectedProduct.quantity,
            }
          );

          // 为每个履约创建 Printify 订单
          const request: PrintifyOrderRequest = {
            order_id: parseInt(orderId),
            ...formData,
            // 包含选中的商品信息
            line_items: [
              {
                id: selectedProduct.lineItem.id,
                title: selectedProduct.lineItem.title,
                variant_title: selectedProduct.lineItem.variant_title,
                sku: selectedProduct.lineItem.sku,
                quantity: selectedProduct.quantity,
                price: selectedProduct.lineItem.price,
                product_id: selectedProduct.lineItem.product_id,
                variant_id: selectedProduct.lineItem.variant_id,
              },
            ],
            // 为每个履约添加唯一标识
            external_id: `order-${orderId}-fulfillment-${i + 1}`,
          };

          const response = await printifyApi.createOrder(request);

          frontendLogger.info(`📋 履约 ${i + 1} Printify API响应`, {
            fulfillmentIndex: i,
            success: response.success,
            printifyOrderId: response.printify_order_id,
            externalId: response.external_id,
            status: response.status,
            totalPrice: response.total_price,
            message: response.message,
          });

          if (response.success) {
            frontendLogger.info(`✅ 履约 ${i + 1} Printify订单创建成功`, {
              fulfillmentIndex: i,
              printifyOrderId: response.printify_order_id,
            });

            // 为每个履约创建 SCM 订单
            const scmOrderData = {
              source_order_id: parseInt(orderId),
              target_system_type: 'PRINTIFY',
              target_system_id: response.printify_order_id,
              routing_strategy: 'manual',
              line_items: [
                {
                  product_id: 'default',
                  variant_id: 'default',
                  quantity: formData.quantity,
                  price: response.total_price || 0,
                },
              ],
              total_amount: response.total_price || 0,
              currency: 'USD',
              customer_email: formData.customer_email,
              customer_name: formData.customer_name,
              customer_phone: formData.phone,
              shipping_address: {
                first_name: formData.customer_name?.split(' ')[0] || 'Customer',
                last_name:
                  formData.customer_name?.split(' ').slice(1).join(' ') || '',
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
                fulfillment_index: i + 1,
                total_fulfillments: selectedProducts.length,
              },
              // 添加Shopify订单ID关联（可能为null）
              shopify_order_id: shopifyOrderId,
            };

            frontendLogger.info(`📤 发送履约 ${i + 1} SCM订单创建请求`, {
              fulfillmentIndex: i,
              scmOrderData,
            });

            const scmResponse = await frontendApi.post(
              '/api/scm-orders',
              scmOrderData
            );

            frontendLogger.info(`📥 履约 ${i + 1} SCM订单创建响应`, {
              fulfillmentIndex: i,
              scmResponse: scmResponse.data,
            });

            if (scmResponse.data) {
              frontendLogger.info(`✅ 履约 ${i + 1} SCM订单创建成功`, {
                fulfillmentIndex: i,
                scmOrderId: scmResponse.data.id,
              });
              scmOrderIds.push(scmResponse.data.id);
              results.push({
                fulfillmentIndex: i + 1,
                printifyOrderId: response.printify_order_id,
                scmOrderId: scmResponse.data.id,
                success: true,
              });
            } else {
              frontendLogger.info(
                `⚠️ 履约 ${i + 1} SCM订单创建失败，但Printify订单已创建`,
                {
                  fulfillmentIndex: i,
                  response: scmResponse.data,
                }
              );
              results.push({
                fulfillmentIndex: i + 1,
                printifyOrderId: response.printify_order_id,
                scmOrderId: null,
                success: false,
                error: 'SCM订单创建失败',
              });
            }
          } else {
            frontendLogger.error(`❌ 履约 ${i + 1} Printify订单创建失败`, {
              fulfillmentIndex: i,
              response,
            });
            results.push({
              fulfillmentIndex: i + 1,
              printifyOrderId: null,
              scmOrderId: null,
              success: false,
              error: response.message || 'Printify订单创建失败',
            });
          }
        } catch (error: any) {
          frontendLogger.error(`❌ 履约 ${i + 1} 创建失败`, {
            fulfillmentIndex: i,
            error: error.message,
            response: error.response?.data,
          });
          results.push({
            fulfillmentIndex: i + 1,
            printifyOrderId: null,
            scmOrderId: null,
            success: false,
            error: error.message,
          });
        }
      }

      // 汇总结果
      const successCount = results.filter(r => r.success).length;
      const totalCount = results.length;

      frontendLogger.info('📊 履约创建汇总', {
        totalFulfillments: totalCount,
        successCount,
        results,
      });

      // 显示结果
      if (successCount === totalCount) {
        const printifyIds = results
          .filter(r => r.printifyOrderId)
          .map(r => r.printifyOrderId)
          .join(', ');
        const scmIds = results
          .filter(r => r.scmOrderId)
          .map(r => r.scmOrderId)
          .join(', ');
        alert(
          `🎉 所有履约创建成功！\n\n履约数量: ${totalCount}\nPrintify订单ID: ${printifyIds}\nSCM订单ID: ${scmIds}`
        );
      } else if (successCount > 0) {
        const successResults = results.filter(r => r.success);
        const failedResults = results.filter(r => !r.success);
        const printifyIds = successResults
          .map(r => r.printifyOrderId)
          .join(', ');
        const scmIds = successResults.map(r => r.scmOrderId).join(', ');
        alert(
          `⚠️ 部分履约创建成功！\n\n成功: ${successCount}/${totalCount}\nPrintify订单ID: ${printifyIds}\nSCM订单ID: ${scmIds}\n\n失败的履约: ${failedResults.map(r => `履约${r.fulfillmentIndex}(${r.error})`).join(', ')}`
        );
      } else {
        alert(
          `❌ 所有履约创建失败！\n\n失败详情:\n${results.map(r => `履约${r.fulfillmentIndex}: ${r.error}`).join('\n')}`
        );
      }

      setResult({
        success: successCount > 0,
        printify_order_id: results
          .filter(r => r.printifyOrderId)
          .map(r => r.printifyOrderId)
          .join(','),
        message: `创建了 ${successCount}/${totalCount} 个履约`,
        results,
        successCount,
        totalCount,
      } as any);
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
                    <Typography variant='body2'>
                      正在加载Printify店铺...
                    </Typography>
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
                      onChange={e => setSelectedStoreId(e.target.value)}
                      label='选择Printify店铺 *'
                    >
                      {stores.map(store => (
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

            {/* 商品选择 */}
            <Card variant='outlined'>
              <CardHeader>
                <Typography variant='h6' component='div' sx={{ p: 2, pb: 0 }}>
                  选择商品
                </Typography>
              </CardHeader>
              <CardContent>
                {productsError && (
                  <Alert severity='error' sx={{ mb: 2 }}>
                    {productsError}
                  </Alert>
                )}

                {loadingProducts ? (
                  <Box display='flex' alignItems='center' gap={2}>
                    <CircularProgress size={20} />
                    <Typography variant='body2'>正在加载商品信息...</Typography>
                  </Box>
                ) : orderLineItems.length === 0 ? (
                  <Alert severity='warning'>
                    订单没有商品信息，无法创建履约。
                  </Alert>
                ) : (
                  <Box>
                    <Typography
                      variant='body2'
                      color='text.secondary'
                      sx={{ mb: 2 }}
                    >
                      请选择要创建履约的商品（可以选择一个或多个）：
                    </Typography>

                    <FormGroup>
                      {orderLineItems.map(lineItem => {
                        const isSelected = selectedProducts.some(
                          p => p.lineItem.id === lineItem.id
                        );
                        const selectedProduct = selectedProducts.find(
                          p => p.lineItem.id === lineItem.id
                        );

                        return (
                          <Box
                            key={lineItem.id}
                            sx={{
                              mb: 2,
                              p: 2,
                              border: '1px solid',
                              borderColor: 'divider',
                              borderRadius: 1,
                            }}
                          >
                            <FormControlLabel
                              control={
                                <Checkbox
                                  checked={isSelected}
                                  onChange={e =>
                                    handleProductSelect(
                                      lineItem,
                                      e.target.checked
                                    )
                                  }
                                />
                              }
                              label={
                                <Box sx={{ flex: 1 }}>
                                  <Typography
                                    variant='body1'
                                    fontWeight='medium'
                                  >
                                    {lineItem.title}
                                  </Typography>
                                  {lineItem.variant_title && (
                                    <Typography
                                      variant='body2'
                                      color='text.secondary'
                                    >
                                      规格: {lineItem.variant_title}
                                    </Typography>
                                  )}
                                  {lineItem.sku && (
                                    <Typography
                                      variant='body2'
                                      color='text.secondary'
                                    >
                                      SKU: {lineItem.sku}
                                    </Typography>
                                  )}
                                  <Typography
                                    variant='body2'
                                    color='text.secondary'
                                  >
                                    单价: ¥{lineItem.price} | 库存数量:{' '}
                                    {lineItem.quantity}
                                  </Typography>
                                </Box>
                              }
                            />

                            {isSelected && (
                              <Box sx={{ ml: 4, mt: 1 }}>
                                <TextField
                                  size='small'
                                  type='number'
                                  label='履约数量'
                                  value={selectedProduct?.quantity || 1}
                                  onChange={e =>
                                    handleProductQuantityChange(
                                      lineItem.id,
                                      parseInt(e.target.value) || 1
                                    )
                                  }
                                  inputProps={{
                                    min: 1,
                                    max: lineItem.quantity,
                                  }}
                                  sx={{ width: 120 }}
                                />
                              </Box>
                            )}
                          </Box>
                        );
                      })}
                    </FormGroup>

                    {selectedProducts.length > 0 && (
                      <Box sx={{ mt: 2 }}>
                        <Divider sx={{ mb: 2 }} />
                        <Typography variant='h6' gutterBottom>
                          已选择的商品 ({selectedProducts.length})
                        </Typography>
                        <Stack spacing={1}>
                          {selectedProducts.map(selectedProduct => (
                            <Box
                              key={selectedProduct.lineItem.id}
                              sx={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: 1,
                              }}
                            >
                              <Chip
                                label={`${selectedProduct.lineItem.title} x${selectedProduct.quantity}`}
                                color='primary'
                                size='small'
                              />
                              <IconButton
                                size='small'
                                onClick={() =>
                                  handleRemoveProduct(
                                    selectedProduct.lineItem.id
                                  )
                                }
                                color='error'
                              >
                                ×
                              </IconButton>
                            </Box>
                          ))}
                        </Stack>
                      </Box>
                    )}
                  </Box>
                )}
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
