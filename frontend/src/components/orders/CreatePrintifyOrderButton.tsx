'use client';

import React, { useState } from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
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

interface CreatePrintifyOrderButtonProps {
  orderId: string;
  orderData?: {
    customer_name?: string;
    customer_email?: string;
    shipping_address?: {
      address1?: string;
      city?: string;
      state?: string;
      country?: string;
      zip?: string;
      phone?: string;
    };
  };
}

export function CreatePrintifyOrderButton({
  orderId,
  orderData,
}: CreatePrintifyOrderButtonProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<PrintifyOrderResponse | null>(null);

  // 表单数据
  const [formData, setFormData] = useState({
    customer_name: orderData?.customer_name || 'Test Customer',
    customer_email: orderData?.customer_email || 'test@example.com',
    address_line1: orderData?.shipping_address?.address1 || '123 Test Street',
    city: orderData?.shipping_address?.city || 'Tokyo',
    state: orderData?.shipping_address?.state || 'Tokyo',
    country: orderData?.shipping_address?.country || 'JP',
    zip_code: orderData?.shipping_address?.zip || '100-0001',
    phone: orderData?.shipping_address?.phone || '+81-90-1234-5678',
    quantity: 1,
  });

  const handleInputChange = (field: string, value: string | number) => {
    setFormData(prev => ({
      ...prev,
      [field]: value,
    }));
  };

  const handleCreateOrder = async () => {
    setIsLoading(true);
    setResult(null);

    try {
      frontendLogger.info('🚀 开始创建Printify订单', { orderId });

      const request: PrintifyOrderRequest = {
        order_id: parseInt(orderId),
        ...formData,
      };

      const response = await printifyApi.createOrder(request);

      setResult(response);
      if (response.success) {
        frontendLogger.info('✅ Printify订单创建成功', { response });
        alert('Printify订单创建成功！');
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
            {/* 客户信息 */}
            <Card variant='outlined'>
              <CardHeader>
                <CardTitle variant='h6'>客户信息</CardTitle>
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
                <CardTitle variant='h6'>收货地址</CardTitle>
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
                  <CardTitle
                    variant='h6'
                    sx={{ display: 'flex', alignItems: 'center', gap: 1 }}
                  >
                    {result.success ? (
                      <CheckCircle color='success' />
                    ) : (
                      <ErrorIcon color='error' />
                    )}
                    创建结果
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <Stack spacing={1}>
                    <Typography variant='body2'>
                      <strong>状态:</strong> {result.success ? '成功' : '失败'}
                    </Typography>
                    <Typography variant='body2'>
                      <strong>消息:</strong> {result.message}
                      {' '}
                    </Typography>
                    {result.printify_order_id && (
                      <Typography variant='body2'>
                        <strong>Printify订单ID:</strong> {result.printify_order_id}
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
